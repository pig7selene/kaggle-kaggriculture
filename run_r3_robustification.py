"""Focused screening and validation for replay-grounded R3 tail guards."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from run_epic_experiments import CANDIDATES, ROOT, _candidate_rows, _independent_shop_schedule, _run
from run_leaderboard_breakthrough import (
    HELDOUT_REPLAY_CASES, RED_TEAM, REPLAY_CASES, _recorded_shop_schedule,
    _source, _trace_spec,
)


PRIMARY_REGRESSION = {
    name: REPLAY_CASES[name]
    for name in (
        "Jayveer_melon_burst", "Pedro_wheat_turnover",
        "Lucas_four_quadrant", "Alexander_cow_melon",
    )
}
TOP_TAIL = dict(HELDOUT_REPLAY_CASES)
NEW_ADVERSARIES = {
    "early_cash_burst": "agents/adversaries/r3_early_cash_burst.py",
    "delayed_melon_scaler": "agents/adversaries/r3_delayed_melon_scaler.py",
    "crop_heavy_scaler": "agents/adversaries/r3_crop_heavy_scaler.py",
}


def _percentile(values, fraction):
    ordered = sorted(values)
    if not ordered:
        return None
    point = fraction * (len(ordered) - 1)
    lower, upper = int(point), min(len(ordered) - 1, int(point) + 1)
    weight = point - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _add_trace(jobs, candidate, group, name, case):
    _, replay_path, player = case
    replay = _source(replay_path)
    seed = int(replay["info"]["seed"])
    schedule = _recorded_shop_schedule(replay)
    for seat in (0, 1):
        jobs.append((candidate, CANDIDATES[candidate], group, name, _trace_spec(replay_path, player), seed, seat, schedule))


def _jobs(stage, candidates, seed_start, seed_count):
    jobs = []
    for candidate in candidates:
        # Every stage retains the four mandatory real regression traces and all
        # eight unseen tail templates because they are the research target.
        for name, case in PRIMARY_REGRESSION.items():
            _add_trace(jobs, candidate, "real_regression", name, case)
        for name, case in TOP_TAIL.items():
            _add_trace(jobs, candidate, "unseen_top", name, case)

        seeds = range(seed_start, seed_start + seed_count)
        for seed in seeds:
            schedule = _independent_shop_schedule(seed)
            for seat in (0, 1):
                jobs.append((candidate, CANDIDATES[candidate], "direct_r3_fixed", "R3_fixed", CANDIDATES["R3_c6_capital"], seed, seat, schedule))
                jobs.append((candidate, CANDIDATES[candidate], "direct_803_fixed", "R0_803_fixed", CANDIDATES["R0_803"], seed, seat, schedule))
                jobs.append((candidate, CANDIDATES[candidate], "direct_r3_natural", "R3_natural", CANDIDATES["R3_c6_capital"], seed, seat, None))
                jobs.append((candidate, CANDIDATES[candidate], "direct_803_natural", "R0_803_natural", CANDIDATES["R0_803"], seed, seat, None))
                for name, spec in NEW_ADVERSARIES.items():
                    jobs.append((candidate, CANDIDATES[candidate], "new_adversary", name, spec, seed, seat, schedule))
                if stage == "final":
                    for name, spec in RED_TEAM.items():
                        jobs.append((candidate, CANDIDATES[candidate], "historical_red", name, spec, seed, seat, schedule))
    return jobs


def _paired_candidate_metrics(games, candidates):
    controls = {
        (row["group"], row["opponent"], row["seed"], row["seat"]): row
        for row in games if row["candidate"] == "R3_c6_capital"
    }
    output = []
    for candidate in candidates:
        selected = [row for row in games if row["candidate"] == candidate]
        deltas = []
        by_group = {}
        for row in selected:
            key = (row["group"], row["opponent"], row["seed"], row["seat"])
            if key in controls:
                deltas.append(row["money"] - controls[key]["money"])
        for group in sorted({row["group"] for row in selected}):
            group_deltas = []
            for row in selected:
                if row["group"] != group:
                    continue
                key = (row["group"], row["opponent"], row["seed"], row["seat"])
                if key in controls:
                    group_deltas.append(row["money"] - controls[key]["money"])
            by_group[group] = {
                "games": len(group_deltas),
                "average_delta_vs_R3": statistics.fmean(group_deltas) if group_deltas else None,
                "p10_delta_vs_R3": _percentile(group_deltas, .10),
                "p5_delta_vs_R3": _percentile(group_deltas, .05),
            }
        output.append({
            "candidate": candidate,
            "paired_games": len(deltas),
            "average_delta_vs_R3": statistics.fmean(deltas) if deltas else None,
            "median_delta_vs_R3": statistics.median(deltas) if deltas else None,
            "p25_delta_vs_R3": _percentile(deltas, .25),
            "p10_delta_vs_R3": _percentile(deltas, .10),
            "p5_delta_vs_R3": _percentile(deltas, .05),
            "worst_delta_vs_R3": min(deltas) if deltas else None,
            "groups": by_group,
        })
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("screen", "final"), default="screen")
    parser.add_argument("--candidates", default="R3_c6_capital,G2_market_harvest,G4_milk_annuity,G5_late_crop_floor,G6_combined")
    parser.add_argument("--seed-start", type=int, default=963100)
    parser.add_argument("--seed-count", type=int, default=2)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    candidates = tuple(value for value in args.candidates.split(",") if value)
    jobs = _jobs(args.stage, candidates, args.seed_start, args.seed_count)
    games = []
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(_run, job) for job in jobs]
        for index, future in enumerate(as_completed(futures), 1):
            games.append(future.result())
            if index % 40 == 0 or index == len(jobs):
                print(f"{args.stage} {index}/{len(jobs)}", flush=True)
    payload = {
        "schema_version": 1, "stage": args.stage,
        "seed_partition": {"start": args.seed_start, "count": args.seed_count},
        "candidates": _candidate_rows(games, candidates),
        "paired_vs_R3": _paired_candidate_metrics(games, candidates),
        "games": games,
    }
    Path(args.output).write_text(json.dumps(payload, indent=2) + "\n")
    for row in payload["candidates"]:
        summary = row["overall"]
        paired = next(value for value in payload["paired_vs_R3"] if value["candidate"] == row["candidate"])
        print(row["candidate"], f"{summary['wins']}/{summary['losses']}/{summary['ties']}", f"money={summary['average_money']:.0f}", f"adv={summary['average_advantage']:+.0f}", f"dR3={paired['average_delta_vs_R3']:+.0f}", f"P10d={paired['p10_delta_vs_R3']:+.0f}")


if __name__ == "__main__":
    main()
