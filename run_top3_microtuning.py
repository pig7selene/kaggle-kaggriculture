"""Fresh-split ablation and validation for the narrow Top-3-informed candidates."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics

from run_epic_experiments import _independent_shop_schedule
import run_super_replay_search as engine


ROOT = Path(__file__).resolve().parent
BASELINE = "agents/top50_distilled/top50_observable_portfolio.py"
CANDIDATES = {
    "CurrentBest": BASELINE,
    "A_rank3_swap": "agents/top3_tuned/top3_tuned_a_rank3_swap.py",
    "B_k3_swap": "agents/top3_tuned/top3_tuned_b_k3_swap.py",
    "C_combined": "agents/top3_tuned/top3_tuned_c_combined.py",
}
OPPONENTS = {
    "Rank1_public_medoid": "agents/top3_tuned/raw_rank1_tetsuya.py",
    "Rank2_public_medoid": "agents/top3_tuned/raw_rank2_crop_dusta.py",
    "Rank3_public_medoid": "agents/top3_tuned/raw_rank3_oceanmix.py",
    "K3": "agents/v27_replay_weed_guard.py",
    "V2": "agents/super_replay_v2/super_backbone_v2.py",
    "CurrentBest_H2H": BASELINE,
}
SPLITS = {
    "development": {
        "fixed": (1261100, 1261101), "natural": (1261200, 1261201),
        "opponents": tuple(OPPONENTS),
        "output": "top3_ablation_results.json",
    },
    "validation": {
        "fixed": (1262100, 1262101, 1262102, 1262103),
        "natural": (1262200, 1262201, 1262202, 1262203),
        "opponents": tuple(OPPONENTS),
        "output": "top3_validation_results.json",
    },
    "selection": {
        "fixed": tuple(range(1263100, 1263108)),
        "natural": tuple(range(1263200, 1263208)),
        "opponents": tuple(OPPONENTS),
        "output": "top3_selection_results.json",
    },
    "final": {
        "fixed": tuple(range(1264100, 1264112)),
        "natural": tuple(range(1264200, 1264212)),
        "opponents": tuple(OPPONENTS),
        "output": "top3_final_validation.json",
    },
}


def percentile(values, fraction):
    values = sorted(values)
    if not values:
        return None
    point = fraction * (len(values) - 1)
    lo = int(point)
    weight = point - lo
    return values[lo] * (1 - weight) + values[min(lo + 1, len(values) - 1)] * weight


def conditions(split):
    config = SPLITS[split]
    output = []
    for opponent in config["opponents"]:
        path = OPPONENTS[opponent]
        for mode in ("fixed", "natural"):
            for seed in config[mode]:
                for seat in (0, 1):
                    schedule = _independent_shop_schedule(seed) if mode == "fixed" else None
                    output.append((opponent, path, mode, seed, seat, schedule))
    return output


def jobs(split, candidates):
    output = []
    for candidate, path in candidates.items():
        for opponent, opponent_path, mode, seed, seat, schedule in conditions(split):
            key = f"{split}|{candidate}|{opponent}|{mode}|{seed}|{seat}"
            group = "direct_current_best" if opponent == "CurrentBest_H2H" else "top3_frontier" if opponent.startswith("Rank") else "robustness_control"
            output.append((key, path, group, opponent, opponent_path, seed, seat, schedule, {}))
    return output


def condition_key(row):
    parts = row["key"].split("|")
    return "|".join(parts[2:])


def summary(games, candidates):
    paths = {path: name for name, path in candidates.items()}
    output = {}
    for path, name in paths.items():
        rows = [row for row in games if row["candidate"] == path and not row.get("runtime_error")]
        advantages = [row["advantage"] for row in rows]
        output[name] = {
            "path": path, "games": len(rows), "wins": sum(value > 0 for value in advantages),
            "losses": sum(value < 0 for value in advantages), "ties": sum(value == 0 for value in advantages),
            "average_money": statistics.fmean(row["money"] for row in rows),
            "average_advantage": statistics.fmean(advantages),
            "p25_advantage": percentile(advantages, .25), "p10_advantage": percentile(advantages, .10),
            "p5_advantage": percentile(advantages, .05), "worst_advantage": min(advantages),
            "variance": statistics.pvariance(advantages),
            "runtime_failures": sum(bool(row.get("runtime_error")) for row in games if row["candidate"] == path),
            "semantic_failures": sum(len(row.get("semantic_failures", [])) for row in games if row["candidate"] == path),
            "actual_livestock_escapes": sum(sum(row.get("actual_livestock_escapes", {}).values()) for row in rows),
            "meaningful_stranding_games": sum(row.get("stranded_value", 0) > 500 for row in rows),
            "route_fidelity": sum(row["route_matches"] for row in rows) / max(1, sum(row["route_requests"] for row in rows)),
            "parent_distribution": dict(sorted(__import__("collections").Counter(row.get("portfolio_parent") for row in rows).items())),
            "by_opponent": {},
        }
        for opponent in sorted({row["opponent"] for row in rows}):
            subset = [row for row in rows if row["opponent"] == opponent]
            values = [row["advantage"] for row in subset]
            output[name]["by_opponent"][opponent] = {
                "games": len(subset), "wins": sum(value > 0 for value in values),
                "losses": sum(value < 0 for value in values), "ties": sum(value == 0 for value in values),
                "average_money": statistics.fmean(row["money"] for row in subset),
                "average_advantage": statistics.fmean(values),
                "p10_advantage": percentile(values, .10), "p5_advantage": percentile(values, .05),
            }
    return output


def paired(games, candidates):
    baseline_rows = {
        condition_key(row): row for row in games
        if row["candidate"] == BASELINE and not row.get("runtime_error")
    }
    output = {}
    for name, path in candidates.items():
        rows = {condition_key(row): row for row in games if row["candidate"] == path and not row.get("runtime_error")}
        own, advantage = [], []
        by_opponent = defaultdict(list)
        for key in sorted(rows.keys() & baseline_rows.keys()):
            own_delta = rows[key]["money"] - baseline_rows[key]["money"]
            advantage_delta = rows[key]["advantage"] - baseline_rows[key]["advantage"]
            own.append(own_delta); advantage.append(advantage_delta)
            by_opponent[rows[key]["opponent"]].append((own_delta, advantage_delta))
        output[name] = {
            "pairs": len(own), "own_wins": sum(value > 0 for value in own),
            "own_losses": sum(value < 0 for value in own), "own_ties": sum(value == 0 for value in own),
            "own_money_delta_mean": statistics.fmean(own), "own_money_delta_median": statistics.median(own),
            "own_money_delta_p10": percentile(own, .10), "own_money_delta_p5": percentile(own, .05),
            "own_money_delta_worst": min(own), "advantage_delta_mean": statistics.fmean(advantage),
            "by_opponent": {
                opponent: {
                    "pairs": len(values), "own_money_delta_mean": statistics.fmean(value[0] for value in values),
                    "advantage_delta_mean": statistics.fmean(value[1] for value in values),
                    "own_wins": sum(value[0] > 0 for value in values), "own_losses": sum(value[0] < 0 for value in values),
                }
                for opponent, values in sorted(by_opponent.items())
            },
        }
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=tuple(SPLITS), required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--candidate", action="append", default=[])
    args = parser.parse_args()
    candidates = CANDIDATES
    if args.candidate:
        wanted = set(args.candidate) | {"CurrentBest"}
        candidates = {name: path for name, path in CANDIDATES.items() if name in wanted}
    partial = ROOT / f"experiments/top3_{args.split}_results.json.partial"
    engine.PARTIAL = partial
    games = engine._run_jobs(jobs(args.split, candidates), args.workers)
    payload = {
        "schema_version": 1, "split": args.split,
        "design": "Narrow Top3-evidenced parent substitutions only; identical fresh fixed/natural seeds, both seats, Top3 medoids, CurrentBest H2H and K3/V2 controls.",
        "seeds": {mode: list(SPLITS[args.split][mode]) for mode in ("fixed", "natural")},
        "candidates": candidates, "games": games,
        "summary": summary(games, candidates), "paired_vs_current_best": paired(games, candidates),
    }
    target = ROOT / "experiments" / SPLITS[args.split]["output"]
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(target)
    for name, row in sorted(payload["paired_vs_current_best"].items(), key=lambda item: item[1]["own_money_delta_mean"], reverse=True):
        overall = payload["summary"][name]
        print(name, row["pairs"], f"{row['own_wins']}/{row['own_losses']}/{row['own_ties']}", round(row["own_money_delta_mean"], 1), round(row["own_money_delta_p10"], 1), round(overall["average_money"], 1), round(overall["p10_advantage"], 1), overall["actual_livestock_escapes"])


if __name__ == "__main__":
    main()
