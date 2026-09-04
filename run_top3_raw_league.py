"""Controlled local league for Top-3 public medoids, CurrentBest, and V2."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics

from run_epic_experiments import _independent_shop_schedule
import run_super_replay_search as engine


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "experiments/top3_raw_parent_league.json"
PARTIAL = ROOT / "experiments/top3_raw_parent_league.json.partial"
CANDIDATES = {
    "Rank1_public_medoid": "agents/top3_tuned/raw_rank1_tetsuya.py",
    "Rank2_public_medoid": "agents/top3_tuned/raw_rank2_crop_dusta.py",
    "Rank3_public_medoid": "agents/top3_tuned/raw_rank3_oceanmix.py",
    "CurrentBest": "agents/top50_distilled/top50_observable_portfolio.py",
    "V2": "agents/super_replay_v2/super_backbone_v2.py",
}
HARD = {
    "K3": "agents/v27_replay_weed_guard.py",
    "Lifecycle": "agents/lifecycle_lc_combined.py",
    "PublicOpening": "agents/opening_public_front_cow8_day6.py",
}


def percentile(values, fraction):
    values = sorted(values)
    point = fraction * (len(values) - 1)
    lo = int(point)
    weight = point - lo
    return values[lo] * (1 - weight) + values[min(lo + 1, len(values) - 1)] * weight


def jobs():
    output = []
    all_opponents = {**CANDIDATES, **HARD}
    for candidate_name, candidate_path in CANDIDATES.items():
        for opponent_name, opponent_path in all_opponents.items():
            if opponent_name == candidate_name:
                continue
            group = "top3_controlled_h2h" if opponent_name in CANDIDATES else "legacy_robustness_only"
            for mode, seeds in (("fixed", (1260100, 1260101)), ("natural", (1260200, 1260201))):
                for seed in seeds:
                    for seat in (0, 1):
                        schedule = _independent_shop_schedule(seed) if mode == "fixed" else None
                        key = f"raw|{candidate_name}|{opponent_name}|{mode}|{seed}|{seat}"
                        output.append((key, candidate_path, group, opponent_name, opponent_path, seed, seat, schedule, {}))
    return output


def grouped_summary(games):
    output = {}
    for candidate_name, candidate_path in CANDIDATES.items():
        rows = [row for row in games if row["candidate"] == candidate_path and not row.get("runtime_error")]
        by_opponent = {}
        for opponent in sorted({row["opponent"] for row in rows}):
            subset = [row for row in rows if row["opponent"] == opponent]
            advantage = [row["advantage"] for row in subset]
            by_opponent[opponent] = {
                "games": len(subset), "wins": sum(value > 0 for value in advantage),
                "losses": sum(value < 0 for value in advantage), "ties": sum(value == 0 for value in advantage),
                "average_money": statistics.fmean(row["money"] for row in subset),
                "average_advantage": statistics.fmean(advantage),
                "p10_advantage": percentile(advantage, .10), "p5_advantage": percentile(advantage, .05),
            }
        advantage = [row["advantage"] for row in rows]
        output[candidate_name] = {
            "path": candidate_path, "games": len(rows), "wins": sum(value > 0 for value in advantage),
            "losses": sum(value < 0 for value in advantage), "ties": sum(value == 0 for value in advantage),
            "average_money": statistics.fmean(row["money"] for row in rows),
            "average_advantage": statistics.fmean(advantage),
            "p10_advantage": percentile(advantage, .10), "p5_advantage": percentile(advantage, .05),
            "worst_advantage": min(advantage), "by_opponent": by_opponent,
            "runtime_failures": sum(bool(row.get("runtime_error")) for row in games if row["candidate"] == candidate_path),
            "semantic_failures": sum(len(row.get("semantic_failures", [])) for row in games if row["candidate"] == candidate_path),
            "livestock_escapes": sum(sum(row.get("actual_livestock_escapes", {}).values()) for row in rows),
            "meaningful_stranding_games": sum(row.get("stranded_value", 0) > 500 for row in rows),
            "route_fidelity": sum(row["route_matches"] for row in rows) / max(1, sum(row["route_requests"] for row in rows)),
        }
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    engine.PARTIAL = PARTIAL
    games = engine._run_jobs(jobs(), args.workers)
    summary = grouped_summary(games)
    payload = {
        "schema_version": 1,
        "design": "Top3 public medoid routes, CurrentBest and V2; identical fresh fixed/natural seeds, both seats, ordered H2H plus legacy safety panel. Public medoids are route reconstructions, not claims about hidden adaptive source.",
        "development_seeds": {"fixed": [1260100, 1260101], "natural": [1260200, 1260201]},
        "games": games, "summary": summary,
        "controlled_h2h_matrix": {
            candidate: {opponent: summary[candidate]["by_opponent"][opponent] for opponent in CANDIDATES if opponent != candidate}
            for candidate in CANDIDATES
        },
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(OUTPUT)
    for name, row in sorted(summary.items(), key=lambda item: item[1]["average_advantage"], reverse=True):
        print(name, row["games"], f"{row['wins']}/{row['losses']}/{row['ties']}", round(row["average_money"], 1), round(row["average_advantage"], 1), round(row["p10_advantage"], 1), round(row["route_fidelity"], 4))


if __name__ == "__main__":
    main()
