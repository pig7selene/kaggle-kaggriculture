"""Paired validation of oracle-selected complete economic routes.

Each route is run from turn 0 against the same fresh seed/opponent/seat as the
frozen observable portfolio.  The comparison is causal at the complete-route
level: no mid-episode route splicing or state takeover occurs.
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
CANDIDATES = {
    "current_best": BASELINE,
    "route_55885628": "agents/autonomous_next/complete_route_55885628.py",
    "route_55909034": "agents/autonomous_next/complete_route_55909034.py",
    "route_55906837": "agents/autonomous_next/complete_route_55906837.py",
}
OPPONENTS = {
    "current_best": BASELINE,
    "tetsuya": "agents/top3_tuned/raw_rank1_tetsuya.py",
    "crop_dusta": "agents/top3_tuned/raw_rank2_crop_dusta.py",
    "oceanmix": "agents/top3_tuned/raw_rank3_oceanmix.py",
}
OUT = ROOT / "experiments/autonomous_complete_route_validation.json"
PARTIAL = ROOT / "experiments/autonomous_complete_route_validation.partial.json"


def _jobs(seeds):
    return [
        (candidate, CANDIDATES[candidate], opponent, OPPONENTS[opponent], int(seed), int(seat))
        for candidate in CANDIDATES for opponent in OPPONENTS
        for seed in seeds for seat in (0, 1)
    ]


def _stats(rows):
    valid = [r for r in rows if not r.get("runtime_error") and r.get("own_money") is not None]
    adv = [float(r["advantage"]) for r in valid]
    return {
        "games": len(valid), "wins": sum(v > 0 for v in adv), "losses": sum(v < 0 for v in adv), "ties": sum(v == 0 for v in adv),
        "win_rate": sum(v > 0 for v in adv) / len(adv) if adv else 0.0,
        "average_money": statistics.fmean(r["own_money"] for r in valid) if valid else None,
        "average_opponent_money": statistics.fmean(r["opponent_money"] for r in valid) if valid else None,
        "average_advantage": statistics.fmean(adv) if adv else None,
        "median_advantage": statistics.median(adv) if adv else None,
        "p10_advantage": sorted(adv)[max(0, int(len(adv) * .10) - 1)] if adv else None,
        "p5_advantage": sorted(adv)[max(0, int(len(adv) * .05) - 1)] if adv else None,
        "worst_advantage": min(adv) if adv else None,
        "variance_advantage": statistics.pvariance(adv) if len(adv) > 1 else 0.0,
        "runtime_failures": sum(bool(r.get("runtime_error")) for r in rows),
        "semantic_failures": sum(len(r.get("semantic_failures", [])) for r in rows),
        "animal_loss_games": sum(bool(r.get("livestock_loss")) for r in valid),
        "mean_terminal_value": statistics.fmean(r.get("terminal", {}).get("value", 0.0) for r in valid) if valid else None,
    }


def _paired(rows):
    grouped = defaultdict(dict)
    for row in rows:
        grouped[(row["opponent"], int(row["seed"]), int(row["seat"]))][row["candidate"]] = row
    out = {}
    for candidate in CANDIDATES:
        if candidate == "current_best":
            continue
        pairs = []
        for key, values in grouped.items():
            if candidate not in values or "current_best" not in values:
                continue
            c, b = values[candidate], values["current_best"]
            if c.get("own_money") is None or b.get("own_money") is None:
                continue
            pairs.append({"opponent": key[0], "seed": key[1], "seat": key[2],
                          "own_delta": float(c["own_money"]) - float(b["own_money"]),
                          "advantage_delta": float(c["advantage"]) - float(b["advantage"]),
                          "candidate_advantage": float(c["advantage"])})
        own = [p["own_delta"] for p in pairs]
        out[candidate] = {
            "games": len(pairs), "mean_own_delta": statistics.fmean(own) if own else None,
            "median_own_delta": statistics.median(own) if own else None,
            "p10_own_delta": sorted(own)[max(0, int(len(own) * .10) - 1)] if own else None,
            "p5_own_delta": sorted(own)[max(0, int(len(own) * .05) - 1)] if own else None,
            "worst_own_delta": min(own) if own else None,
            "negative_own_rate": sum(v < 0 for v in own) / len(own) if own else None,
            "mean_advantage_delta": statistics.fmean(p["advantage_delta"] for p in pairs) if pairs else None,
            "by_opponent": {
                opponent: {
                    "games": sum(p["opponent"] == opponent for p in pairs),
                    "mean_own_delta": statistics.fmean([p["own_delta"] for p in pairs if p["opponent"] == opponent]) if any(p["opponent"] == opponent for p in pairs) else None,
                    "mean_advantage_delta": statistics.fmean([p["advantage_delta"] for p in pairs if p["opponent"] == opponent]) if any(p["opponent"] == opponent for p in pairs) else None,
                } for opponent in OPPONENTS
            },
        }
    return out


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", nargs="+", type=int, default=list(range(56310, 56318)))
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    jobs = _jobs(args.seeds)
    rows = []
    if PARTIAL.is_file():
        try:
            rows = json.loads(PARTIAL.read_text()).get("rows", [])
        except Exception:
            rows = []
    done = {(r.get("candidate"), r.get("opponent"), int(r.get("seed", -1)), int(r.get("seat", -1))) for r in rows}
    todo = [job for job in jobs if (job[0], job[2], job[4], job[5]) not in done]
    print(f"running {len(todo)} validation games ({len(rows)} cached)", flush=True)
    with ProcessPoolExecutor(max_workers=max(1, int(args.workers))) as pool:
        futures = [pool.submit(_run_game, job) for job in todo]
        for index, future in enumerate(as_completed(futures), 1):
            rows.append(future.result())
            if index % 16 == 0 or index == len(futures):
                PARTIAL.write_text(json.dumps({"schema_version": 1, "rows": rows}, indent=2, sort_keys=True) + "\n")
                print(f"{index}/{len(futures)} complete", flush=True)
    rows.sort(key=lambda r: (r.get("candidate", ""), r.get("opponent", ""), r.get("seed", 0), r.get("seat", 0)))
    summaries = {name: _stats([r for r in rows if r.get("candidate") == name]) for name in CANDIDATES}
    payload = {
        "schema_version": 1,
        "design": "complete route candidates versus frozen portfolio and Top-3 frontier; fresh seeds, both seats, whole routes only",
        "seeds": [int(s) for s in args.seeds], "candidates": CANDIDATES, "opponents": OPPONENTS,
        "rows": rows, "summaries": summaries, "paired_vs_current_best": _paired(rows),
    }
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(OUT)
    for name, row in summaries.items():
        print(name, row["games"], row["wins"], row["losses"], round(row["average_money"], 1) if row["average_money"] is not None else None, round(row["average_advantage"], 1) if row["average_advantage"] is not None else None, row["animal_loss_games"])
    print(json.dumps(payload["paired_vs_current_best"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
