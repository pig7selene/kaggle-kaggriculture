"""Read-only, resumable collector for the current Kaggriculture Top 3 only."""

from pathlib import Path

import collect_super_replays as collector


ROOT = Path(__file__).resolve().parent
collector.CORPUS = ROOT / "experiments/top3_corpus"
collector.REPLAYS = collector.CORPUS / "replays"
collector.PARTIAL = ROOT / "experiments/top3_corpus_manifest.json.partial"
collector.OUTPUT = ROOT / "experiments/top3_corpus_manifest.json"


if __name__ == "__main__":
    collector.main()
