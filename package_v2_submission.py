"""Reproducibly package frozen Super Replay Backbone V2 as one standalone file."""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import zlib

import package_v27_submission as template


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "agents/super_replay_v2/super_backbone_v2.py"
ROUTE_BANK = ROOT / "experiments/v2_route_executor.json"
OUTPUT = ROOT / "submission/main.py"
EXPECTED_SOURCE_SHA = "c39d82b4f796271603e32ea8cb4b70261fbbe3d4e17940886caf5f5a6bd9adef"
ROUTE_ID = "super_raw_55463387"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _digest(value):
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def main():
    source_sha = _sha256(SOURCE)
    if source_sha != EXPECTED_SOURCE_SHA:
        raise SystemExit(
            f"frozen source hash mismatch: expected {EXPECTED_SOURCE_SHA}, got {source_sha}"
        )

    source_route = next(
        row for row in json.loads(ROUTE_BANK.read_text())["routes"]
        if row["route_id"] == ROUTE_ID
    )
    minimal_route = {
        "route_id": source_route["route_id"],
        "consensus_actions": source_route["consensus_actions"],
        "expected_state": source_route["expected_state"],
    }
    assert len(minimal_route["consensus_actions"]) == 719
    assert len(minimal_route["expected_state"]) == 719

    # The frozen V2 executor calls the same stage-3 builder as V1. Reuse the
    # proven standalone K3 executor byte-for-byte and replace only its route.
    template.SOURCE = SOURCE
    template.MANIFEST = ROUTE_BANK
    template.OUTPUT = OUTPUT
    template.EXPECTED_SOURCE_SHA = EXPECTED_SOURCE_SHA
    template.ROUTE_ID = ROUTE_ID
    template.main()

    text = OUTPUT.read_text()
    text = text.replace(
        "Standalone Kaggriculture agent: frozen Victor V27 route + weed repair.",
        "Standalone Kaggriculture agent: frozen JALKARNA V2 route + bounded K3 weed repair.",
    ).replace(
        "Generated from agents/v27_replay_weed_guard.py.",
        "Generated from agents/super_replay_v2/super_backbone_v2.py.",
    )
    OUTPUT.write_text(text)

    canonical = json.dumps(minimal_route, sort_keys=True, separators=(",", ":")).encode()
    packed = base64.b64encode(zlib.compress(canonical, 9)).decode()
    if packed not in text.replace('"\n    "', ""):
        raise SystemExit("embedded route payload differs from minimal frozen V2 route")

    print(f"route_actions_sha256={_digest(minimal_route['consensus_actions'])}")
    print(f"route_expected_state_sha256={_digest(minimal_route['expected_state'])}")
    print(f"canonical_route_bytes={len(canonical)}")
    print(f"compressed_route_bytes={len(zlib.compress(canonical, 9))}")
    print(f"submission_sha256={_sha256(OUTPUT)}")


if __name__ == "__main__":
    main()
