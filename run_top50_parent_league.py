"""Resumable complete-route league for current Top-50 parent strategies."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics

from run_epic_experiments import _independent_shop_schedule, _recorded_shop_schedule
import run_super_replay_search as engine


ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "agents/top50_distilled/raw/index.json"
BANK = ROOT / "experiments/top50_route_bank.json"
BASELINE = "agents/super_replay_v2/super_backbone_v2.py"
OUTPUT = ROOT / "experiments/top50_raw_parent_league.json"
PARTIAL = ROOT / "experiments/top50_raw_parent_league.json.partial"


def _trace(path, player):
    return f"trace:{ROOT / path}:{int(player)}"


def _percentile(values, fraction):
    values = sorted(values)
    point = fraction * (len(values) - 1)
    lower = int(point)
    weight = point - lower
    return values[lower] * (1 - weight) + values[min(lower + 1, len(values) - 1)] * weight


def _conditions(mode):
    routes = json.loads(BANK.read_text())["routes"]
    medoids = [row for row in routes if row["route_id"].endswith("_medoid")]
    if mode == "cheap":
        medoids = medoids[:]
        seeds = range(1105100, 1105102)
    else:
        seeds = range(1105200, 1105208)
    conditions = []
    for seed in seeds:
        for seat in (0, 1):
            conditions.append((f"v2f|{seed}|{seat}", "direct_v2_fixed", "V2", BASELINE, seed, seat, _independent_shop_schedule(seed)))
            conditions.append((f"v2n|{seed}|{seat}", "direct_v2_natural", "V2", BASELINE, seed, seat, None))
    for route in medoids:
        replay = json.loads((ROOT / route["source_replay_path"]).read_text())
        for seat in (0, 1):
            conditions.append((
                f"trace|{route['route_id']}|{route['source_seed']}|{seat}", "top50_family_trace", route["route_id"],
                _trace(route["source_replay_path"], route["source_player"]), route["source_seed"], seat,
                _recorded_shop_schedule(replay),
            ))
    return conditions


def _jobs(candidates, mode):
    jobs = []
    for name, path in candidates.items():
        for condition, group, opponent, spec, seed, seat, schedule in _conditions(mode):
            jobs.append((f"{mode}|{name}|{condition}", path, group, opponent, spec, seed, seat, schedule, {}))
    return jobs


def _paired(games, baseline_path):
    by_condition = defaultdict(dict)
    for row in games:
        if row.get("runtime_error"):
            continue
        condition = "|".join(row["key"].split("|")[2:])
        by_condition[condition][row["candidate"]] = row
    output = {}
    paths = sorted({row["candidate"] for row in games})
    for path in paths:
        values, advantage_deltas = [], []
        for rows in by_condition.values():
            if path in rows and baseline_path in rows:
                values.append(rows[path]["money"] - rows[baseline_path]["money"])
                advantage_deltas.append(rows[path]["advantage"] - rows[baseline_path]["advantage"])
        output[path] = {
            "pairs": len(values), "paired_wins": sum(value > 0 for value in values),
            "paired_losses": sum(value < 0 for value in values), "paired_ties": sum(value == 0 for value in values),
            "paired_own_money_delta_mean": statistics.fmean(values) if values else None,
            "paired_own_money_delta_median": statistics.median(values) if values else None,
            "paired_own_money_delta_p10": _percentile(values, .10) if values else None,
            "paired_own_money_delta_p5": _percentile(values, .05) if values else None,
            "paired_own_money_delta_worst": min(values) if values else None,
            "net_advantage_delta_mean": statistics.fmean(advantage_deltas) if advantage_deltas else None,
        }
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--mode", choices=("cheap", "serious"), default="cheap")
    parser.add_argument("--names", default="")
    args = parser.parse_args()
    index = json.loads(INDEX.read_text())
    if args.names:
        wanted = {value for value in args.names.split(",") if value}
        index = {name: path for name, path in index.items() if name in wanted}
    candidates = {"V2_baseline": BASELINE, **index}
    engine.PARTIAL = PARTIAL if args.mode == "cheap" else ROOT / "experiments/top50_raw_parent_league_serious.json.partial"
    games = engine._run_jobs(_jobs(candidates, args.mode), args.workers)
    payload = {
        "schema_version": 1, "mode": args.mode, "baseline": BASELINE,
        "design": "complete Top-50 routes and V2 on identical fixed/natural V2 and all economic-family trace conditions; both seats",
        "games": games, "summary": engine._summaries(games), "paired_vs_v2": _paired(games, BASELINE),
    }
    target = OUTPUT if args.mode == "cheap" else ROOT / "experiments/top50_raw_parent_league_serious.json"
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(target)
    for path, row in sorted(payload["paired_vs_v2"].items(), key=lambda pair: pair[1]["paired_own_money_delta_mean"] or -1e99, reverse=True):
        summary = payload["summary"].get(path, {})
        print(path, row["pairs"], row["paired_wins"], round(row["paired_own_money_delta_mean"], 1), round(row["paired_own_money_delta_p10"], 1), round(summary.get("average_money", 0), 1), summary.get("livestock_losses"))


if __name__ == "__main__":
    main()
