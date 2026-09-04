"""Normalize only the current, version-pure Kaggriculture Top-3 corpus."""

from pathlib import Path

import analyze_super_replays as analyzer


ROOT = Path(__file__).resolve().parent
analyzer.CORPUS_MANIFEST = ROOT / "experiments/top3_corpus_manifest.json"
analyzer.STABILITY_OUT = ROOT / "experiments/top3_route_stability.json"
analyzer.FAMILIES_OUT = ROOT / "experiments/top3_route_families.json"
analyzer.WAVES_OUT = ROOT / "experiments/top3_economic_waves.json"
analyzer.CONFIDENCE_OUT = ROOT / "experiments/top3_action_confidence.json"
analyzer.ROUTE_BANK_OUT = ROOT / "experiments/top3_route_bank.json"
analyzer.CACHE = ROOT / "experiments/top3_analysis_cache.json.partial"


if __name__ == "__main__":
    analyzer.main()
