"""Normalize the current Top-50 corpus with the audited replay analyzer.

The richer strategy-family and distillation artifacts are built by
``mine_top50_strategies.py``.  This pass produces the lossless normalized
routes, state anchors, stability measurements, and economic ledgers used by
that miner.
"""

from pathlib import Path

import analyze_super_replays as analyzer


ROOT = Path(__file__).resolve().parent
analyzer.CORPUS_MANIFEST = ROOT / "experiments/top50_corpus_manifest.json"
analyzer.STABILITY_OUT = ROOT / "experiments/top50_route_stability.json"
analyzer.FAMILIES_OUT = ROOT / "experiments/top50_route_families_raw.json"
analyzer.WAVES_OUT = ROOT / "experiments/top50_economic_waves.json"
analyzer.CONFIDENCE_OUT = ROOT / "experiments/top50_action_confidence.json"
analyzer.ROUTE_BANK_OUT = ROOT / "experiments/top50_route_bank.json"
analyzer.CACHE = ROOT / "experiments/top50_analysis_cache.json.partial"


if __name__ == "__main__":
    analyzer.main()
