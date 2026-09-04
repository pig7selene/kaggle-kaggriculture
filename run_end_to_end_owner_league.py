"""Held-out hard-opponent confirmation for the end-to-end owner probe."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
import statistics

from run_end_to_end_owner import CANDIDATE, BASELINE, _run


ROOT = Path(__file__).resolve().parent
OPPONENTS = {
    "tetsuya": "agents/top3_tuned/raw_rank1_tetsuya.py",
    "crop_dusta": "agents/top3_tuned/raw_rank2_crop_dusta.py",
    "oceanmix": "agents/top3_tuned/raw_rank3_oceanmix.py",
    "livestock_crop": "agents/proxies/livestock_crop.py",
    "land_expander": "agents/proxies/land_expander.py",
    "high_labor": "agents/proxies/high_labor.py",
}


def _job(job):
    name, opponent, seed, seat = job
    baseline = _run(BASELINE, opponent, seed, seat)
    candidate = _run(CANDIDATE, opponent, seed, seat)
    row = {"opponent": name, "seed": int(seed), "seat": int(seat), "baseline": baseline, "candidate": candidate}
    if baseline.get("own_money") is not None and candidate.get("own_money") is not None:
        row["own_money_delta"] = candidate["own_money"] - baseline["own_money"]
        row["advantage_delta"] = candidate["advantage"] - baseline["advantage"]
    return row


def _stats(rows):
    valid = [r for r in rows if "own_money_delta" in r]
    deltas = [float(r["own_money_delta"]) for r in valid]
    return {
        "games": len(valid),
        "mean_own_money_delta": statistics.fmean(deltas) if deltas else None,
        "median_own_money_delta": statistics.median(deltas) if deltas else None,
        "p10_own_money_delta": sorted(deltas)[max(0, int((len(deltas) - 1) * .10))] if deltas else None,
        "mean_advantage_delta": statistics.fmean(float(r["advantage_delta"]) for r in valid) if valid else None,
        "candidate_wins": sum(float(r["candidate"]["advantage"]) > 0 for r in valid),
        "candidate_losses": sum(float(r["candidate"]["advantage"]) < 0 for r in valid),
        "candidate_ties": sum(float(r["candidate"]["advantage"]) == 0 for r in valid),
        "runtime_failures": sum(bool(r["baseline"].get("runtime_error") or r["candidate"].get("runtime_error")) for r in rows),
        "semantic_failures": sum(len(r["baseline"].get("semantic_failures", [])) + len(r["candidate"].get("semantic_failures", [])) for r in rows),
        "animal_loss_conditions": sum(bool(r["candidate"].get("animal_loss")) for r in valid),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", nargs="+", type=int, default=[57510, 57511])
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--output", default="experiments/end_to_end_owner_league.json")
    args = parser.parse_args()
    jobs = [(name, path, int(seed), int(seat)) for name, path in OPPONENTS.items() for seed in args.seeds for seat in (0, 1)]
    rows = []
    with ProcessPoolExecutor(max_workers=max(1, int(args.workers))) as pool:
        futures = [pool.submit(_job, job) for job in jobs]
        for i, future in enumerate(as_completed(futures), 1):
            rows.append(future.result())
            if i % 8 == 0 or i == len(futures):
                print(f"{i}/{len(futures)} complete", flush=True)
    rows.sort(key=lambda r: (r["opponent"], r["seed"], r["seat"]))
    by_opponent = {name: _stats([r for r in rows if r["opponent"] == name]) for name in OPPONENTS}
    payload = {
        "schema_version": 1,
        "design": "candidate and frozen complete route versus hard opponent pool; paired held-out seeds, both seats",
        "baseline": BASELINE, "candidate": CANDIDATE, "opponents": OPPONENTS,
        "seeds": [int(s) for s in args.seeds], "rows": rows, "by_opponent": by_opponent, "overall": _stats(rows),
    }
    output = (ROOT / args.output).resolve(); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(output)
    print(json.dumps({"overall": payload["overall"], "by_opponent": by_opponent}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
