"""Diagnose deployed V2 public games against the frozen JALKARNA route."""

from pathlib import Path

import analyze_v2_real_kaggle as base


ROOT = Path(__file__).resolve().parent


def main():
    base.MANIFEST = ROOT / "experiments/v3_real_v2_replays/manifest.json"
    base.EXPECTED_BANK = ROOT / "experiments/v2_route_executor.json"
    base.OUTPUT = ROOT / "experiments/v3_v2_failure_clusters.json"
    base.REPORT = ROOT / "experiments/v3_v2_failure_clusters.md"
    base.ROUTE_ID = "super_raw_55463387"
    base.main()


if __name__ == "__main__":
    main()
