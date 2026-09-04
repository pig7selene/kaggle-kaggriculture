"""Small hindsight oracle over the existing complete Top-50 route bank.

Every route is executed whole from turn 0 against the frozen CurrentBest on
identical fresh seeds and both seats.  No actions are spliced.  The purpose is
to estimate whether route-family selection still contains material own-money
headroom before investing in a new selector or executor.
"""

from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
import statistics

from run_autonomous_next_route_screen import _run_game

ROOT = Path(__file__).resolve().parent
BASELINE = "agents/top50_distilled/top50_observable_portfolio.py"
INDEX = ROOT / "agents/top50_distilled/raw/index.json"
OUT = ROOT / "experiments/autonomous_complete_route_oracle.json"
PARTIAL = ROOT / "experiments/autonomous_complete_route_oracle.partial.json"


def _jobs(seeds):
    routes = json.loads(INDEX.read_text())
    jobs = []
    for name, path in routes.items():
        for seed in seeds:
            for seat in (0, 1):
                jobs.append((name, path, "current_best", BASELINE, int(seed), int(seat)))
    return jobs


def _stats(rows):
    valid = [r for r in rows if not r.get("runtime_error") and r.get("own_money") is not None]
    adv = [float(r["advantage"]) for r in valid]
    return {
        "games": len(valid),
        "wins": sum(v > 0 for v in adv), "losses": sum(v < 0 for v in adv), "ties": sum(v == 0 for v in adv),
        "average_money": statistics.fmean(r["own_money"] for r in valid) if valid else None,
        "average_advantage": statistics.fmean(adv) if adv else None,
        "median_advantage": statistics.median(adv) if adv else None,
        "p10_advantage": sorted(adv)[max(0, int(len(adv) * .10) - 1)] if adv else None,
        "p5_advantage": sorted(adv)[max(0, int(len(adv) * .05) - 1)] if adv else None,
        "worst_advantage": min(adv) if adv else None,
        "runtime_failures": sum(bool(r.get("runtime_error")) for r in rows),
        "semantic_failures": sum(len(r.get("semantic_failures", [])) for r in rows),
        "animal_loss_games": sum(bool(r.get("livestock_loss")) for r in valid),
    }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", nargs="+", type=int, default=[56300, 56301])
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    jobs = _jobs(args.seeds)
    rows = []
    if PARTIAL.is_file():
        try:
            rows = json.loads(PARTIAL.read_text()).get("rows", [])
        except Exception:
            rows = []
    done = {(r.get("candidate"), int(r.get("seed", -1)), int(r.get("seat", -1))) for r in rows}
    todo = [job for job in jobs if (job[0], job[4], job[5]) not in done]
    print(f"running {len(todo)} route oracle games ({len(rows)} cached)", flush=True)
    with ProcessPoolExecutor(max_workers=max(1, int(args.workers))) as pool:
        futures = [pool.submit(_run_game, job) for job in todo]
        for index, future in enumerate(as_completed(futures), 1):
            rows.append(future.result())
            if index % 16 == 0 or index == len(futures):
                PARTIAL.write_text(json.dumps({"schema_version": 1, "rows": rows}, indent=2, sort_keys=True) + "\n")
                print(f"{index}/{len(futures)} complete", flush=True)
    rows.sort(key=lambda r: (r.get("candidate", ""), r.get("seed", 0), r.get("seat", 0)))
    summaries = {name: _stats([r for r in rows if r.get("candidate") == name]) for name in sorted({r.get("candidate") for r in rows})}
    by_condition = defaultdict(list)
    for row in rows:
        if not row.get("runtime_error"):
            by_condition[(int(row["seed"]), int(row["seat"]))].append(row)
    oracle_rows = []
    for key, values in sorted(by_condition.items()):
        best = max(values, key=lambda r: float(r["own_money"]))
        oracle_rows.append({"seed": key[0], "seat": key[1], "best_route": best["candidate"], "best_money": best["own_money"],
                            "baseline_money": float(values[0]["opponent_money"]), "oracle_delta": float(best["own_money"]) - float(values[0]["opponent_money"])})
    deltas = [r["oracle_delta"] for r in oracle_rows]
    payload = {
        "schema_version": 1,
        "design": "whole-route hindsight oracle: every Top-50 route versus frozen CurrentBest, fresh seeds and both seats",
        "baseline": BASELINE, "seeds": [int(s) for s in args.seeds], "routes": json.loads(INDEX.read_text()),
        "rows": rows, "summaries": summaries,
        "oracle": {"conditions": len(oracle_rows), "mean_delta": statistics.fmean(deltas) if deltas else None,
                    "median_delta": statistics.median(deltas) if deltas else None,
                    "p10_delta": sorted(deltas)[max(0, int(len(deltas) * .10) - 1)] if deltas else None,
                    "p5_delta": sorted(deltas)[max(0, int(len(deltas) * .05) - 1)] if deltas else None,
                    "oracle_rows": oracle_rows},
    }
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(OUT)
    print(json.dumps(payload["oracle"], indent=2, sort_keys=True))
    for name, summary in sorted(summaries.items(), key=lambda kv: kv[1].get("average_money") or -1e99, reverse=True)[:10]:
        print(name, summary["games"], round(summary["average_money"], 1), round(summary["average_advantage"], 1), summary["wins"], summary["losses"], summary["animal_loss_games"])


if __name__ == "__main__":
    main()
