"""Audit whether complete Top-50 routes can be resumed from one another.

This is a cheap falsification before attempting a checkpoint-resumable
executor.  It compares observable economic commitments in the route-bank
expected states.  It does not splice actions or alter any strategy.
"""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ROUTE_BANK = ROOT / "experiments/top50_route_bank.json"
DEFAULT_OUTPUT = ROOT / "experiments/autonomous_checkpoint_compatibility.json"
CHECKPOINTS = (24, 48, 72, 120, 168, 240, 360, 480, 600, 718)

# These fields are coupled commitments: matching only land and animal counts
# is insufficient to safely enter a continuation.
STRICT_FIELDS = (
    "quadrants", "crops", "crop_cohorts", "animals", "structures", "productive",
    "crop_geometry_hash", "animal_geometry_hash", "hand_count", "seeds", "shed",
    "inventories",
)


def _compatible(a, b):
    return all(a.get(key) == b.get(key) for key in STRICT_FIELDS)


def _summary(routes):
    ordered = list(itertools.permutations(routes, 2))
    output = {}
    for step in CHECKPOINTS:
        geometry = 0
        strict = 0
        components = {"land": 0, "hands": 0, "animals": 0, "crop_geometry": 0, "inventory": 0}
        examples = []
        for source, target in ordered:
            a = source["expected_state"][step]
            b = target["expected_state"][step]
            if a.get("crop_geometry_hash") == b.get("crop_geometry_hash") and a.get("animal_geometry_hash") == b.get("animal_geometry_hash"):
                geometry += 1
            if a.get("quadrants") == b.get("quadrants"):
                components["land"] += 1
            if a.get("hand_count") == b.get("hand_count"):
                components["hands"] += 1
            if a.get("animals") == b.get("animals"):
                components["animals"] += 1
            if a.get("crop_geometry_hash") == b.get("crop_geometry_hash") and a.get("animal_geometry_hash") == b.get("animal_geometry_hash"):
                components["crop_geometry"] += 1
            if a.get("seeds") == b.get("seeds") and a.get("shed") == b.get("shed") and a.get("inventories") == b.get("inventories"):
                components["inventory"] += 1
            if _compatible(a, b):
                strict += 1
                if len(examples) < 8:
                    examples.append({"source": source["route_id"], "target": target["route_id"]})
        total = len(ordered)
        output[str(step)] = {
            "ordered_pairs": total,
            "geometry_compatible": geometry,
            "strict_compatible": strict,
            "strict_rate": strict / total if total else 0.0,
            "component_match_counts": components,
            "examples": examples,
        }
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    routes = json.loads(ROUTE_BANK.read_text())["routes"]
    payload = {
        "schema_version": 1,
        "design": "pairwise complete-route checkpoint compatibility; no action splicing",
        "route_count": len(routes), "checkpoints": list(CHECKPOINTS),
        "strict_fields": list(STRICT_FIELDS), "summary": _summary(routes),
    }
    output = (ROOT / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(output)
    for step, row in payload["summary"].items():
        print(step, "geometry", row["geometry_compatible"], "strict", row["strict_compatible"], "rate", round(row["strict_rate"], 4))


if __name__ == "__main__":
    main()
