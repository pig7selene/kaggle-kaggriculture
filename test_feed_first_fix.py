"""Small isolated validation for feed-before-herd-expansion scheduling."""

import json
import statistics
from concurrent.futures import ProcessPoolExecutor, as_completed

from benchmark import ROOT
from test_endgame_fix import SEEDS, SOURCE, _run


FIX = ROOT / "agents" / "router_replay_feed_first_fix.py"
OUTPUT = ROOT / "experiments" / "opponent_feed_first_bugfix_ablation.json"


def main():
    jobs = [
        (label, str(path), seed, seat)
        for label, path in (("source", SOURCE), ("feed_first_fix", FIX))
        for seed in SEEDS for seat in (0, 1)
    ]
    games = []
    with ProcessPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(_run, job) for job in jobs]
        for index, future in enumerate(as_completed(futures), 1):
            games.append(future.result())
            if index % 8 == 0:
                print(f"completed {index}/{len(jobs)}", flush=True)
    games.sort(key=lambda row: (row["label"], row["seed"], row["seat"]))
    summaries = {}
    for label in ("source", "feed_first_fix"):
        rows = [row for row in games if row["label"] == label]
        summaries[label] = {
            "games": len(rows),
            "average_money": statistics.fmean(row["money"] for row in rows),
            "average_advantage": statistics.fmean(row["advantage"] for row in rows),
            "total_invalid_actions": sum(row["invalid_actions"] for row in rows),
            "total_stranded_milk": sum(row["stranded_milk"] for row in rows),
            "max_stranded_milk": max(row["stranded_milk"] for row in rows),
            "total_cow_losses_or_replacements": sum(row["cow_losses_or_replacements"] for row in rows),
            "max_cow_losses_or_replacements": max(row["cow_losses_or_replacements"] for row in rows),
        }
    control = {(row["seed"], row["seat"]): row for row in games if row["label"] == "source"}
    deltas = [
        row["money"] - control[(row["seed"], row["seat"])]["money"]
        for row in games if row["label"] == "feed_first_fix"
    ]
    result = {
        "schema_version": 1,
        "experiment": "isolated_feed_first_fix",
        "seeds": list(SEEDS),
        "both_seats": True,
        "source": str(SOURCE.relative_to(ROOT)),
        "candidate": str(FIX.relative_to(ROOT)),
        "summaries": summaries,
        "paired_average_money_delta": statistics.fmean(deltas),
        "paired_money_delta_range": [min(deltas), max(deltas)],
        "games": games,
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"summaries": summaries, "paired_average_money_delta": result["paired_average_money_delta"]}, indent=2))
    print(f"Saved {OUTPUT}")


if __name__ == "__main__":
    main()
