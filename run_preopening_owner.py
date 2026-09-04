"""Paired screen for the bounded pre-opening owner probe."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics

from run_end_to_end_owner import _run, BASELINE


ROOT = Path(__file__).resolve().parent
CANDIDATE = "agents/autonomous_next/preopening_owner_wheat_v1.py"


def _summary(rows):
    valid = [r for r in rows if r["baseline"].get("own_money") is not None and r["candidate"].get("own_money") is not None]
    deltas = [float(r["candidate"]["own_money"]) - float(r["baseline"]["own_money"]) for r in valid]
    return {
        "conditions": len(rows),
        "valid": len(valid),
        "runtime_failures": sum(bool(r["baseline"].get("runtime_error") or r["candidate"].get("runtime_error")) for r in rows),
        "schema_failures": sum(len(r["baseline"].get("semantic_failures", [])) + len(r["candidate"].get("semantic_failures", [])) for r in rows),
        "animal_loss_conditions": sum(bool(r["candidate"].get("animal_loss")) for r in valid),
        "mean_own_money_delta": statistics.fmean(deltas) if deltas else None,
        "median_own_money_delta": statistics.median(deltas) if deltas else None,
        "p10_own_money_delta": sorted(deltas)[max(0, int((len(deltas) - 1) * 0.10))] if deltas else None,
        "mean_advantage_delta": statistics.fmean(float(r["candidate"]["advantage"]) - float(r["baseline"]["advantage"]) for r in valid) if valid else None,
        "admissions": sum(int(r["candidate"].get("telemetry", {}).get("admissions", 0)) for r in valid),
        "seed_requests": sum(int(r["candidate"].get("telemetry", {}).get("seed_requests", 0)) for r in valid),
        "plant_actions": sum(int(r["candidate"].get("telemetry", {}).get("plant_actions", 0)) for r in valid),
        "water_actions": sum(int(r["candidate"].get("telemetry", {}).get("water_actions", 0)) for r in valid),
        "harvest_actions": sum(int(r["candidate"].get("telemetry", {}).get("harvest_actions", 0)) for r in valid),
        "sell_requests": sum(int(r["candidate"].get("telemetry", {}).get("sell_requests", 0)) for r in valid),
        "terminal_inventory_value_mean": statistics.fmean(float(r["candidate"].get("terminal_inventory_value", 0.0)) for r in valid) if valid else None,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", nargs="+", type=int, default=[57700, 57701, 57702, 57703])
    parser.add_argument("--output", default="experiments/preopening_owner_wheat_screen.json")
    args = parser.parse_args()
    rows = []
    for seed in args.seeds:
        for seat in (0, 1):
            baseline = _run(BASELINE, BASELINE, seed, seat)
            candidate = _run(CANDIDATE, BASELINE, seed, seat)
            rows.append({"seed": int(seed), "seat": int(seat), "baseline": baseline, "candidate": candidate})
            print(f"seed={seed} seat={seat} done", flush=True)
    payload = {
        "schema_version": 1,
        "design": "day-0 reserved tail worker and two-tile wheat owner versus frozen portfolio",
        "baseline": BASELINE,
        "candidate": CANDIDATE,
        "seeds": [int(s) for s in args.seeds],
        "rows": rows,
        "summary": _summary(rows),
    }
    output = (ROOT / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(output)
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

