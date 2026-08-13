"""Package the frozen Super Replay Backbone using the proven K3 standalone template."""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import zlib

import package_v27_submission as template


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "agents/super_replay/super_backbone_v1.py"
ROUTE_BANK = ROOT / "experiments/super_replay_route_executor.json"
OUTPUT = ROOT / "submission/main.py"
EXPECTED_SOURCE_SHA = "96bd9cefd7c31075e47719ec1f9d1ee9391b467f68b956c65e0dd96478adb516"
ROUTE_ID = "super_raw_55459817"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main():
    source_sha = _sha256(SOURCE)
    if source_sha != EXPECTED_SOURCE_SHA:
        raise SystemExit(f"frozen source hash mismatch: expected {EXPECTED_SOURCE_SHA}, got {source_sha}")

    bank = json.loads(ROUTE_BANK.read_text())
    source_route = next(row for row in bank["routes"] if row["route_id"] == ROUTE_ID)
    minimal_route = {
        "route_id": source_route["route_id"],
        "consensus_actions": source_route["consensus_actions"],
        "expected_state": source_route["expected_state"],
    }
    assert len(minimal_route["consensus_actions"]) == 719
    assert len(minimal_route["expected_state"]) == 719

    # Reuse the already-proven Stage-3 standalone executor byte-for-byte. Only
    # its frozen source gate and embedded route payload change.
    template.SOURCE = SOURCE
    template.MANIFEST = ROUTE_BANK
    template.OUTPUT = OUTPUT
    template.EXPECTED_SOURCE_SHA = EXPECTED_SOURCE_SHA
    template.ROUTE_ID = ROUTE_ID
    template.main()

    text = OUTPUT.read_text()
    text = text.replace(
        "Standalone Kaggriculture agent: frozen Victor V27 route + weed repair.",
        "Standalone Kaggriculture agent: frozen Ricardo elite route + bounded K3 weed repair.",
    ).replace(
        "Generated from agents/v27_replay_weed_guard.py.",
        "Generated from agents/super_replay/super_backbone_v1.py.",
    )
    OUTPUT.write_text(text)

    # Decode the final file without importing it and prove the exact payload.
    packed = base64.b64encode(
        zlib.compress(json.dumps(minimal_route, sort_keys=True, separators=(",", ":")).encode(), 9)
    ).decode()
    if packed not in text.replace('"\n    "', ""):
        raise SystemExit("embedded route payload differs from minimal frozen route")
    print(f"route_actions_sha256={_digest(minimal_route['consensus_actions'])}")
    print(f"route_expected_state_sha256={_digest(minimal_route['expected_state'])}")
    print(f"submission_sha256={_sha256(OUTPUT)}")


if __name__ == "__main__":
    main()
