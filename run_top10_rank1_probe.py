"""Paired fixed-seed screen for the Top-10 Rank-1 opening signature probe."""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
import statistics

import run_super_replay_search as engine
from run_epic_experiments import _independent_shop_schedule


ROOT = Path(__file__).resolve().parent
BASE = "agents/top50_distilled/top50_observable_portfolio.py"
CANDIDATE = "agents/autonomous_next/top10_rank1_signature_v1.py"
TOP10 = [
    (f"top10_{sid}", f"agents/super_replay_v3/v3_raw_{sid}.py")
    for sid in (
        55425101, 55435941, 55463387, 55463671, 55470275,
        55445174, 55468815, 55474695, 55469248, 55476469,
    )
]
HARD = [
    ("raw_rank1_tetsuya", "agents/top3_tuned/raw_rank1_tetsuya.py"),
    ("raw_rank2_crop_dusta", "agents/top3_tuned/raw_rank2_crop_dusta.py"),
    ("raw_rank3_oceanmix", "agents/top3_tuned/raw_rank3_oceanmix.py"),
    ("livestock_crop", "agents/proxies/livestock_crop.py"),
    ("land_expander", "agents/proxies/land_expander.py"),
    ("high_labor", "agents/proxies/high_labor.py"),
    ("phased_rotation", "agents/proxies/phased_rotation.py"),
]


def _jobs(seeds):
    opponents = TOP10 + HARD
    jobs = []
    for name, path in (("current_best", BASE), ("rank1_signature", CANDIDATE)):
        for opponent, opponent_path in opponents:
            for seed in seeds:
                for seat in (0, 1):
                    for mode, schedule in (
                        ("fixed", _independent_shop_schedule(seed)),
                        ("natural", None),
                    ):
                        key = f"{name}|{opponent}|{mode}|{seed}|{seat}"
                        jobs.append((
                            key, path, "top10_rank1_probe", opponent,
                            opponent_path, int(seed), seat, schedule, {},
                        ))
    return jobs


def _pct(values, fraction):
    if not values:
        return 0.0
    values = sorted(values)
    point = fraction * (len(values) - 1)
    lo = int(point)
    hi = min(lo + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (point - lo)


def _summaries(rows):
    result = {}
    for candidate in sorted({row["candidate"] for row in rows}):
        valid = [row for row in rows if row["candidate"] == candidate and not row.get("runtime_error")]
        adv = [float(row["advantage"]) for row in valid]
        result[candidate] = {
            "games": len(valid),
            "wins": sum(value > 0 for value in adv),
            "losses": sum(value < 0 for value in adv),
            "ties": sum(value == 0 for value in adv),
            "win_rate": sum(value > 0 for value in adv) / len(adv) if adv else 0.0,
            "average_money": statistics.fmean(row["money"] for row in valid) if valid else 0.0,
            "average_advantage": statistics.fmean(adv) if adv else 0.0,
            "median_advantage": statistics.median(adv) if adv else 0.0,
            "p10_advantage": _pct(adv, 0.10),
            "p5_advantage": _pct(adv, 0.05),
            "worst_advantage": min(adv) if adv else 0.0,
            "variance_advantage": statistics.pvariance(adv) if len(adv) > 1 else 0.0,
            "runtime_failures": sum(bool(row.get("runtime_error")) for row in rows if row["candidate"] == candidate),
            "semantic_failures": sum(len(row.get("semantic_failures", [])) for row in rows if row["candidate"] == candidate),
            "livestock_losses": sum(sum(row.get("livestock_losses", {}).values()) for row in valid),
            "actual_livestock_escapes": sum(sum(row.get("actual_livestock_escapes", {}).values()) for row in valid),
            "stranding_games": sum(row.get("stranded_value", 0) > 500 for row in valid),
            "rank1_selections": sum(row.get("portfolio_parent") == "rank1" for row in valid),
            "by_opponent": {},
        }
        for opponent in sorted({row["opponent"] for row in valid}):
            subset = [row for row in valid if row["opponent"] == opponent]
            values = [float(row["advantage"]) for row in subset]
            result[candidate]["by_opponent"][opponent] = {
                "games": len(subset),
                "wins": sum(value > 0 for value in values),
                "losses": sum(value < 0 for value in values),
                "ties": sum(value == 0 for value in values),
                "average_money": statistics.fmean(row["money"] for row in subset),
                "average_advantage": statistics.fmean(values),
                "p10_advantage": _pct(values, 0.10),
                "rank1_selections": sum(row.get("portfolio_parent") == "rank1" for row in subset),
            }
    return result


def _paired(rows):
    grouped = defaultdict(dict)
    for row in rows:
        if not row.get("runtime_error"):
            condition = "|".join(row["key"].split("|")[1:])
            grouped[condition][row["candidate"]] = row
    deltas = []
    advantages = []
    for pair in grouped.values():
        if BASE in pair and CANDIDATE in pair:
            deltas.append(pair[CANDIDATE]["money"] - pair[BASE]["money"])
            advantages.append(pair[CANDIDATE]["advantage"] - pair[BASE]["advantage"])
    return {
        "pairs": len(deltas),
        "wins": sum(value > 0 for value in deltas),
        "losses": sum(value < 0 for value in deltas),
        "ties": sum(value == 0 for value in deltas),
        "own_money_delta_mean": statistics.fmean(deltas) if deltas else 0.0,
        "own_money_delta_median": statistics.median(deltas) if deltas else 0.0,
        "own_money_delta_p10": _pct(deltas, 0.10),
        "own_money_delta_p5": _pct(deltas, 0.05),
        "advantage_delta_mean": statistics.fmean(advantages) if advantages else 0.0,
        "advantage_delta_p10": _pct(advantages, 0.10),
    }


def main():
    global CANDIDATE
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", nargs="+", type=int, default=[57910])
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--output", default="experiments/top10_rank1_probe.json")
    parser.add_argument("--candidate", default=CANDIDATE)
    args = parser.parse_args()
    CANDIDATE = args.candidate
    jobs = _jobs(args.seeds)
    rows, errors = [], []
    print(f"Running {len(jobs)} games", flush=True)
    with ProcessPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(engine._run, job): job for job in jobs}
        for index, future in enumerate(as_completed(futures), 1):
            try:
                rows.append(future.result())
            except Exception as error:
                errors.append({"job": futures[future][0], "error": repr(error)})
            if index % 20 == 0 or index == len(jobs):
                print(f"completed {index}/{len(jobs)}", flush=True)
    rows.sort(key=lambda row: row["key"])
    payload = {
        "schema_version": 1,
        "design": "complete Top-10 Rank-1 route selected only on public step-1 five-hand/pasture/low-bank signature",
        "seeds": [int(seed) for seed in args.seeds],
        "candidates": {"current_best": BASE, "rank1_signature": CANDIDATE},
        "opponents": [name for name, _ in TOP10 + HARD],
        "summaries": _summaries(rows),
        "paired_vs_current_best": _paired(rows),
        "games": rows,
        "errors": errors,
    }
    output = (ROOT / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(output)
    print(json.dumps({"paired": payload["paired_vs_current_best"], "summaries": payload["summaries"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
