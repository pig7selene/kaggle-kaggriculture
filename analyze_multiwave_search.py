"""Meta-analysis and local economic derivatives for multi-wave search."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path


def _mean(rows, fn):
    values = [fn(row) for row in rows]
    return statistics.fmean(values) if values else None


def analyze(results_path, configs_path):
    results = json.loads(Path(results_path).read_text())
    registry = json.loads(Path(configs_path).read_text())
    generation = results["stage"]
    configs = registry[generation]
    games_by_candidate = defaultdict(list)
    for row in results["games"]:
        games_by_candidate[row["candidate"]].append(row)

    family = defaultdict(list)
    traits = defaultdict(lambda: defaultdict(list))
    derivative_rows = []
    for summary in results["candidates"]:
        candidate = summary["candidate"]
        config = configs[candidate]["config"]
        rows = games_by_candidate[candidate]
        top_rows = [row for row in rows if row["group"].startswith("top_")]
        waves = [row["cash_waves"] for row in rows]
        record = {
            "candidate": candidate,
            "family": configs[candidate]["family"],
            "score": summary["real_transfer_score"],
            "top_win_rate": summary["top_template_win_rate"],
            "top_advantage": summary["top_template_average_advantage"],
            "direct_r3_advantage": summary["direct_r3_average_advantage"],
            "average_money": summary["overall"]["average_money"],
            "average_crop_revenue": summary["overall"]["average_crop_revenue"],
            "d10_crop_count": _mean(top_rows, lambda row: sum(row["checkpoints"]["10"]["crops"].values())),
            "d10_melon_count": _mean(top_rows, lambda row: row["checkpoints"]["10"]["crops"].get("MELON", 0)),
            "d15_productive_tiles": _mean(top_rows, lambda row: row["checkpoints"]["15"]["productive_tiles"]),
            "d20_crop_count": _mean(top_rows, lambda row: sum(row["checkpoints"]["20"]["crops"].values())),
            "wave1_liquidation": _mean(waves, lambda value: value["wave1"]["major_liquidation_revenue"]),
            "wave1_idle_turns": _mean(waves, lambda value: value["wave1"]["cash_idle_turns"] or 0),
            "wave1_reinvest_fraction": _mean(waves, lambda value: value["wave1"]["reinvestment_fraction_6_turns"]),
            "wave2_liquidation": _mean(waves, lambda value: value["wave2"]["major_liquidation_revenue"]),
            "wave2_idle_turns": _mean(waves, lambda value: value["wave2"]["cash_idle_turns"] or 0),
            "wave2_reinvest_fraction": _mean(waves, lambda value: value["wave2"]["reinvestment_fraction_6_turns"]),
            "wave1_mix": config["wave1_mix"],
            "wave2_mix": config["wave2_mix"],
            "opening_mix": config["opening_extension_mix"],
            "wave1_structure": config["wave1_structure"],
            "wave2_structure": config["wave2_structure"],
            "liquidation_mode": config["liquidation_mode"],
            "seed_reinvestment_fraction": config["seed_reinvestment_fraction"],
            "cash_reserve_wave1": config["cash_reserve_wave1"],
            "cash_reserve_wave2": config["cash_reserve_wave2"],
        }
        derivative_rows.append(record)
        family[record["family"]].append(record)
        for key in (
            "wave1_structure", "wave2_structure", "liquidation_mode",
            "seed_reinvestment_fraction", "cash_reserve_wave1", "cash_reserve_wave2",
        ):
            traits[key][str(record[key])].append(record)

    top = derivative_rows[:]
    top.sort(key=lambda row: row["score"], reverse=True)
    survivors = top[: max(10, len(top) // 5)]
    output = {
        "schema_version": 1, "stage": generation,
        "candidate_count": len(top),
        "families": {
            name: {
                "count": len(rows),
                "average_score": _mean(rows, lambda row: row["score"]),
                "best_score": max(row["score"] for row in rows),
                "average_top_advantage": _mean(rows, lambda row: row["top_advantage"]),
                "average_direct_r3_advantage": _mean(rows, lambda row: row["direct_r3_advantage"]),
            }
            for name, rows in sorted(family.items())
        },
        "traits": {
            trait: {
                value: {
                    "count": len(rows),
                    "average_score": _mean(rows, lambda row: row["score"]),
                    "average_top_advantage": _mean(rows, lambda row: row["top_advantage"]),
                    "average_direct_r3_advantage": _mean(rows, lambda row: row["direct_r3_advantage"]),
                }
                for value, rows in sorted(values.items())
            }
            for trait, values in traits.items()
        },
        "top_candidates": top[:20],
        "survivor_common_traits": {
            "opening_melon_share": _mean(survivors, lambda row: row["opening_mix"].get("MELON", 0)),
            "wave1_melon_share": _mean(survivors, lambda row: row["wave1_mix"].get("MELON", 0)),
            "wave1_strawberry_share": _mean(survivors, lambda row: row["wave1_mix"].get("STRAWBERRY", 0)),
            "wave2_strawberry_share": _mean(survivors, lambda row: row["wave2_mix"].get("STRAWBERRY", 0)),
            "d10_crop_count": _mean(survivors, lambda row: row["d10_crop_count"]),
            "d10_melon_count": _mean(survivors, lambda row: row["d10_melon_count"]),
            "d15_productive_tiles": _mean(survivors, lambda row: row["d15_productive_tiles"]),
            "d20_crop_count": _mean(survivors, lambda row: row["d20_crop_count"]),
            "wave1_liquidation": _mean(survivors, lambda row: row["wave1_liquidation"]),
            "wave1_idle_turns": _mean(survivors, lambda row: row["wave1_idle_turns"]),
            "wave2_liquidation": _mean(survivors, lambda row: row["wave2_liquidation"]),
            "wave2_idle_turns": _mean(survivors, lambda row: row["wave2_idle_turns"]),
            "structures": Counter(row["wave1_structure"] for row in survivors),
            "liquidation_modes": Counter(row["liquidation_mode"] for row in survivors),
        },
        "candidate_metrics": derivative_rows,
    }
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("results")
    parser.add_argument("--configs", default="experiments/multiwave_candidate_configs.json")
    parser.add_argument("--output")
    args = parser.parse_args()
    payload = analyze(args.results, args.configs)
    output = Path(args.output) if args.output else Path(args.results).with_name(Path(args.results).stem + "_analysis.json")
    output.write_text(json.dumps(payload, indent=2, default=dict) + "\n")
    print(output)


if __name__ == "__main__":
    main()

