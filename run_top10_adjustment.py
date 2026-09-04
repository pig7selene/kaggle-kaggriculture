"""Small paired league for the Top-10-informed parent adjustment."""

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
BASELINE = "agents/top50_distilled/top50_observable_portfolio.py"
CANDIDATE = "agents/autonomous_next/top10_lowbank_hanserong_v1.py"
TOP10 = [f"agents/super_replay_v3/v3_raw_{sid}.py" for sid in (
    55425101, 55435941, 55463387, 55463671, 55470275,
    55445174, 55468815, 55474695, 55469248, 55476469,
)]
HARD = [
    "agents/top3_tuned/raw_rank1_tetsuya.py",
    "agents/top3_tuned/raw_rank2_crop_dusta.py",
    "agents/top3_tuned/raw_rank3_oceanmix.py",
    "agents/proxies/livestock_crop.py",
    "agents/proxies/land_expander.py",
    "agents/proxies/high_labor.py",
    "agents/proxies/phased_rotation.py",
]


def _jobs(candidates, seeds):
    opponents = [(f"top10_{sid}", path) for sid, path in zip(
        (55425101, 55435941, 55463387, 55463671, 55470275,
         55445174, 55468815, 55474695, 55469248, 55476469), TOP10)]
    opponents += [(Path(path).stem, path) for path in HARD]
    jobs = []
    for name, path in candidates.items():
        for opponent_name, opponent_path in opponents:
            for seed in seeds:
                for seat in (0, 1):
                    for mode, schedule in (("fixed", _independent_shop_schedule(seed)), ("natural", None)):
                        key = f"{name}|{opponent_name}|{mode}|{seed}|{seat}"
                        jobs.append((key, path, "top10_adjustment", opponent_name, opponent_path, seed, seat, schedule, {}))
    return jobs, opponents


def _percentile(values, p):
    if not values:
        return 0.0
    values = sorted(values)
    pos = p * (len(values) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)


def _summaries(rows):
    output = {}
    for name in sorted({row["candidate"] for row in rows}):
        valid = [row for row in rows if row["candidate"] == name and not row.get("runtime_error")]
        adv = [float(row["advantage"]) for row in valid]
        output[name] = {
            "games": len(valid),
            "wins": sum(v > 0 for v in adv),
            "losses": sum(v < 0 for v in adv),
            "ties": sum(v == 0 for v in adv),
            "win_rate": sum(v > 0 for v in adv) / len(adv) if adv else 0.0,
            "average_money": statistics.fmean(row["money"] for row in valid) if valid else 0.0,
            "average_advantage": statistics.fmean(adv) if adv else 0.0,
            "median_advantage": statistics.median(adv) if adv else 0.0,
            "p10_advantage": _percentile(adv, 0.10),
            "p5_advantage": _percentile(adv, 0.05),
            "worst_advantage": min(adv) if adv else 0.0,
            "variance_advantage": statistics.pvariance(adv) if len(adv) > 1 else 0.0,
            "runtime_failures": sum(bool(row.get("runtime_error")) for row in rows if row["candidate"] == name),
            "semantic_failures": sum(len(row.get("semantic_failures", [])) for row in rows if row["candidate"] == name),
            "livestock_losses": sum(sum(row.get("livestock_losses", {}).values()) for row in valid),
            "stranding_games": sum(row.get("stranded_value", 0) > 500 for row in valid),
            "jalkarna_selections": sum(row.get("portfolio_parent") == "jalkarna" for row in valid),
        }
        by_opp = {}
        for opp in sorted({row["opponent"] for row in valid}):
            subset = [row for row in valid if row["opponent"] == opp]
            values = [float(row["advantage"]) for row in subset]
            by_opp[opp] = {
                "games": len(subset), "wins": sum(v > 0 for v in values),
                "losses": sum(v < 0 for v in values), "ties": sum(v == 0 for v in values),
                "average_money": statistics.fmean(row["money"] for row in subset),
                "average_advantage": statistics.fmean(values), "p10_advantage": _percentile(values, .10),
                "jalkarna_selections": sum(row.get("portfolio_parent") == "jalkarna" for row in subset),
            }
        output[name]["by_opponent"] = by_opp
    return output


def _paired(rows, baseline):
    groups = defaultdict(dict)
    for row in rows:
        if not row.get("runtime_error"):
            condition = "|".join(row["key"].split("|")[1:])
            groups[condition][row["candidate"]] = row
    values, advantages = [], []
    candidate_path = CANDIDATE
    baseline_path = BASELINE
    for group in groups.values():
        if candidate_path in group and baseline_path in group:
            values.append(group[candidate_path]["money"] - group[baseline_path]["money"])
            advantages.append(group[candidate_path]["advantage"] - group[baseline_path]["advantage"])
    return {
        "pairs": len(values), "wins": sum(v > 0 for v in values),
        "losses": sum(v < 0 for v in values), "ties": sum(v == 0 for v in values),
        "own_money_delta_mean": statistics.fmean(values) if values else 0.0,
        "own_money_delta_median": statistics.median(values) if values else 0.0,
        "own_money_delta_p10": _percentile(values, .10),
        "advantage_delta_mean": statistics.fmean(advantages) if advantages else 0.0,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", nargs="+", type=int, default=[57900, 57901])
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--output", default="experiments/top10_adjustment_screen.json")
    args = parser.parse_args()
    candidates = {"current_best": BASELINE, "top10_lowbank_hanserong_v1": CANDIDATE}
    jobs, opponents = _jobs(candidates, args.seeds)
    rows = []
    errors = []
    print(f"Running {len(jobs)} games", flush=True)
    with ProcessPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(engine._run, job): job for job in jobs}
        for index, future in enumerate(as_completed(futures), 1):
            try:
                rows.append(future.result())
            except Exception as exc:
                errors.append({"job": futures[future][0], "error": repr(exc)})
            if index % 20 == 0 or index == len(jobs):
                print(f"completed {index}/{len(jobs)}", flush=True)
    rows.sort(key=lambda row: row["key"])
    payload = {
        "schema_version": 1,
        "design": "Top-10-informed low-bank/four-hand signature routed to the proven Hanserong complete parent; all other decisions frozen",
        "seeds": [int(seed) for seed in args.seeds],
        "candidates": candidates,
        "opponents": [name for name, _ in opponents],
        "summaries": _summaries(rows),
        "paired_vs_current_best": _paired(rows, BASELINE),
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
