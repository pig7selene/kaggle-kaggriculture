"""Controlled debt-aware watering ablations and validation."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from analyze_predictive_watering import watering_metrics
from run_replant_pipeline_experiments import (
    HARD_POOL, LOSS_EPISODES, REAL_NAMES, REPLAY_DIR, ROOT,
    _independent_shop_schedule, _load_opponent, _recorded_shop_schedule,
    _run_fixed, _source_replay, _trace_spec,
)
from run_replant_pipeline_experiments import _run as _base_run


CANDIDATES = {
    "W0": "agents/watering_w0_frozen.py",
    "W1": "agents/watering_w1_cow6.py",
    "W2": "agents/watering_w2_cow9_predictive.py",
    "W3": "agents/watering_w3_cow6_predictive.py",
    "W4": "agents/watering_w4_cow6_sweep.py",
    "W3b": "agents/watering_w3b_cow6_local.py",
    "W4b": "agents/watering_w4b_cow6_local_sweep.py",
    "W3c": "agents/watering_w3c_cow6_protected_borrow.py",
    "W4c": "agents/watering_w4c_cow6_sweep_only.py",
    "W2d": "agents/watering_w2d_cow9_deadline.py",
    "W3d": "agents/watering_w3d_cow6_deadline.py",
    "W3e": "agents/watering_w3e_cow6_late_guard.py",
    "W3d7": "agents/watering_w3d_cow7_deadline.py",
    "W3d8": "agents/watering_w3d_cow8_deadline.py",
    "W3dG": "agents/watering_w3d_guarded.py",
}


def _run(job):
    *_, seat, _ = job
    row, replay = _base_run((*job, True))
    row["watering"] = watering_metrics(replay, seat)
    return row


def _percentile(values, fraction):
    values = sorted(values)
    if not values:
        return None
    point = fraction * (len(values) - 1)
    lo = int(point)
    hi = min(lo + 1, len(values) - 1)
    weight = point - lo
    return values[lo] * (1 - weight) + values[hi] * weight


def _summary(games):
    advantages = [row["advantage"] for row in games]
    paired = defaultdict(list)
    for row in games:
        paired[(row["opponent"], row["seed"])].append(row["advantage"])
    mean = lambda fn: statistics.fmean(fn(row) for row in games)
    crop_turns = mean(lambda row: row["crop_worker_turns"])
    animal_turns = mean(lambda row: row["animal_service_worker_turns"])
    crop_revenue = mean(lambda row: row["economics"]["full"]["crop_revenue"])
    animal_revenue = mean(lambda row: row["economics"]["full"]["animal_revenue"])
    return {
        "games": len(games),
        "wins": sum(value > 0 for value in advantages),
        "losses": sum(value < 0 for value in advantages),
        "ties": sum(value == 0 for value in advantages),
        "average_money": mean(lambda row: row["money"]),
        "average_advantage": statistics.fmean(advantages),
        "p10_paired_advantage": _percentile([statistics.fmean(v) for v in paired.values()], 0.1),
        "money_stddev": statistics.pstdev(row["money"] for row in games),
        "average_watering_debt": mean(lambda row: row["watering"]["average_watering_debt_actions"]),
        "peak_watering_debt": mean(lambda row: row["watering"]["peak_watering_debt_actions"]),
        "average_watering_debt_value": mean(lambda row: row["watering"]["average_watering_debt_value"]),
        "peak_watering_debt_value": mean(lambda row: row["watering"]["peak_watering_debt_value"]),
        "average_near_critical_crops": mean(lambda row: row["watering"]["average_near_critical_crops"]),
        "peak_near_critical_crops": mean(lambda row: row["watering"]["peak_near_critical_crops"]),
        "average_critical_crops": mean(lambda row: row["watering"]["average_critical_crops"]),
        "peak_critical_crops": mean(lambda row: row["watering"]["peak_critical_crops"]),
        "critical_watering_miss_rate": mean(lambda row: row["watering"]["critical_watering_miss_rate"]),
        "emergency_water_actions": mean(lambda row: row["watering"]["emergency_water_actions"]),
        "inherited_emergency_water_actions": mean(lambda row: row["watering"]["inherited_emergency_water_actions"]),
        "planting_day_water_actions": mean(lambda row: row["watering"]["planting_day_water_actions"]),
        "proactive_water_actions": mean(lambda row: row["watering"]["proactive_water_actions"]),
        "proactive_water_fraction": mean(lambda row: row["watering"]["proactive_water_fraction"]),
        "watering_movement": mean(lambda row: row["watering"]["watering_movement"]),
        "average_water_travel": mean(lambda row: row["watering"]["average_water_travel"]),
        "average_watering_cohort": mean(lambda row: row["watering"]["average_watering_cohort"]),
        "territory_crossings": mean(lambda row: row["watering"]["territory_crossings"]),
        "average_harvest_backlog": mean(lambda row: row["watering"]["average_harvest_backlog"]),
        "peak_harvest_backlog": mean(lambda row: row["watering"]["peak_harvest_backlog"]),
        "average_harvest_delay": mean(lambda row: row["lifecycle_day10_20"]["average_harvest_delay_turns"] or 0),
        "crop_harvests": mean(lambda row: row["lifecycle_day10_20"]["total_harvest_actions"] + row["lifecycle_day21_29"]["total_harvest_actions"]),
        "strawberry_harvests": mean(lambda row: row["lifecycle_day10_20"]["harvest_actions"].get("STRAWBERRY", 0) + row["lifecycle_day21_29"]["harvest_actions"].get("STRAWBERRY", 0)),
        "average_replant_latency": mean(lambda row: row["replant"]["average_delay"] or 0),
        "median_replant_latency": statistics.median(row["replant"]["median_delay"] or 0 for row in games),
        "p90_replant_latency": mean(lambda row: row["replant"]["p90_delay"] or 0),
        "crop_worker_turns": crop_turns,
        "animal_service_worker_turns": animal_turns,
        "movement_turns": mean(lambda row: row["movement_actions"]),
        "productive_turns": mean(lambda row: row["watering"]["productive_actions"]),
        "completed_cycles_per_worker_day": mean(lambda row: row["lifecycle_day10_20"]["completed_cycles_per_worker_day"]),
        "crop_revenue": crop_revenue,
        "animal_revenue": animal_revenue,
        "crop_revenue_day10_20": mean(lambda row: row["economics"]["day10_20"]["crop_revenue"]),
        "crop_revenue_day20_29": mean(lambda row: row["economics"]["day20_29"]["crop_revenue"]),
        "crop_revenue_day21_29": mean(lambda row: row["economics"]["day21_29"]["crop_revenue"]),
        "crop_revenue_per_crop_worker_turn": crop_revenue / max(1, crop_turns),
        "animal_revenue_per_animal_service_turn": animal_revenue / max(1, animal_turns),
        "total_invalid_actions": sum(row["invalid_actions"] for row in games),
        "total_livestock_losses": sum(sum(row["livestock_losses"].values()) for row in games),
        "max_stranded_value": max(row["stranded_value"] for row in games),
    }


def _candidate_rows(games, candidates):
    controls = {(g["group"], g["opponent"], g["seed"], g["seat"]): g for g in games if g["candidate"] == "W0"}
    output = []
    for candidate in candidates:
        selected = [g for g in games if g["candidate"] == candidate]
        groups = {name: _summary([g for g in selected if g["group"] == name]) for name in sorted({g["group"] for g in selected})}
        matchups = {name: _summary([g for g in selected if g["opponent"] == name]) for name in sorted({g["opponent"] for g in selected})}
        deltas = defaultdict(list)
        for row in selected:
            key = (row["group"], row["opponent"], row["seed"], row["seat"])
            if key in controls:
                deltas[row["group"]].append(row["money"] - controls[key]["money"])
        output.append({
            "candidate": candidate, "path": CANDIDATES[candidate],
            "overall": _summary(selected), "groups": groups, "matchups": matchups,
            "paired_own_money_delta_vs_W0": {name: statistics.fmean(values) for name, values in deltas.items()},
        })
    return output


def _jobs(stage, candidates, seeds):
    jobs = []
    def add(candidate, group, opponent, spec, seed, schedule):
        for seat in (0, 1):
            jobs.append((candidate, CANDIDATES[candidate], group, opponent, spec, seed, seat, schedule))
    if stage == "rng":
        for candidate in candidates:
            for seed in seeds:
                add(candidate, "rng_fixed", "current_fixed", "agents/lifecycle_lc_combined.py", seed, _independent_shop_schedule(seed))
                add(candidate, "rng_natural", "current_natural", "agents/lifecycle_lc_combined.py", seed, None)
        return jobs
    if stage == "redteam":
        # Fixed, deliberately stressful opponents.  These cover crop waves,
        # mixed maturities, animal-service spikes, aggressive reinvestment,
        # distant deployment, and dense three-quadrant production without
        # changing any candidate parameters.
        pool = {
            "strawberry_wave": "agents/replay_archetypes/aggressive_strawberry_scaler.py",
            "mixed_maturity": "agents/router_meta_mixed_throughout.py",
            "animal_spike_4_to_8": "agents/adversaries/red_stage_4_to_8_day15.py",
            "animal_spike_bank_gate": "agents/adversaries/red_c8_bank11000.py",
            "far_workers_fast_land": "agents/replay_archetypes/fast_land_high_labor.py",
            "low_cash_reinvestment": "agents/replay_archetypes/rapid_sell_reinvestment.py",
            "phased_crop_waves": "agents/proxies/phased_rotation.py",
            "dense_sheep_cow": "agents/router_meta_sheep_to_cow.py",
        }
        for candidate in candidates:
            for opponent, spec in pool.items():
                for seed in seeds:
                    add(candidate, "redteam", opponent, spec, seed, _independent_shop_schedule(seed))
        return jobs
    for candidate in candidates:
        for episode in LOSS_EPISODES:
            replay = _source_replay(episode)
            add(candidate, "real_losses", REAL_NAMES[episode], _trace_spec(episode), int(replay["info"]["seed"]), _recorded_shop_schedule(replay))
        if stage in {"selection", "final"}:
            direct_n = 3 if stage == "selection" else 8
            pool_n = 1 if stage == "selection" else 2
            pool = {k: v for k, v in HARD_POOL.items() if k in {
                "aggressive_strawberry", "fast_land_high_labor", "top_meta_mixed",
                "top_meta_sheep_cow", "epic_jay_wave", "epic_pedro_trader",
                "livestock_crop", "high_labor", "land_expander",
            }}
            for seed in seeds[:direct_n]:
                add(candidate, "direct", "current_best", "agents/lifecycle_lc_combined.py", seed, _independent_shop_schedule(seed))
            for opponent, spec in pool.items():
                for seed in seeds[:pool_n]:
                    add(candidate, "hard_pool", opponent, spec, seed, _independent_shop_schedule(seed))
    return jobs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("screen", "selection", "final", "rng", "redteam"), default="screen")
    parser.add_argument("--candidates", default="W0,W1,W2,W3,W4")
    parser.add_argument("--workers", type=int, default=5)
    parser.add_argument("--seed-start", type=int, default=1010000)
    parser.add_argument("--seed-count", type=int, default=8)
    parser.add_argument("--output")
    args = parser.parse_args()
    candidates = tuple(value for value in args.candidates.split(",") if value)
    seeds = tuple(range(args.seed_start, args.seed_start + args.seed_count))
    jobs = _jobs(args.stage, candidates, seeds)
    games = []
    if args.workers <= 1:
        for index, job in enumerate(jobs, 1):
            games.append(_run(job))
            if index % 20 == 0 or index == len(jobs):
                print(f"{args.stage}: {index}/{len(jobs)}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = [executor.submit(_run, job) for job in jobs]
            for index, future in enumerate(as_completed(futures), 1):
                games.append(future.result())
                if index % 20 == 0 or index == len(jobs):
                    print(f"{args.stage}: {index}/{len(jobs)}", flush=True)
    payload = {
        "schema_version": 1, "stage": args.stage,
        "candidates": _candidate_rows(games, candidates), "games": games,
    }
    output = Path(args.output) if args.output else ROOT / "experiments" / f"predictive_watering_{args.stage}.json"
    output.write_text(json.dumps(payload, indent=2) + "\n")
    print(output)
    for row in payload["candidates"]:
        s = row["overall"]
        print(row["candidate"], f"{s['wins']}/{s['losses']}/{s['ties']}", f"money={s['average_money']:.0f}", f"adv={s['average_advantage']:+.0f}", f"debt={s['average_watering_debt']:.1f}", f"critical={s['critical_watering_miss_rate']:.2%}", f"emerg={s['emergency_water_actions']:.0f}", f"harvest={s['crop_harvests']:.1f}", f"backlog={s['average_harvest_backlog']:.1f}", f"replant={s['average_replant_latency']:.1f}", f"crop={s['crop_revenue']:.0f}")


if __name__ == "__main__":
    main()
