"""Read-only current Top-3 collector for adaptive-policy distillation."""

from pathlib import Path

import collect_super_replays as collector


ROOT = Path(__file__).resolve().parent
# Reuse already-validated replay files from the forensic stage and download only
# newly selected current-version episodes.  The adaptive manifest is separate.
collector.CORPUS = ROOT / "experiments/top3_corpus"
collector.REPLAYS = collector.CORPUS / "replays"
collector.PARTIAL = ROOT / "experiments/top3_adaptive_corpus_manifest.json.partial"
collector.OUTPUT = ROOT / "experiments/top3_adaptive_corpus_manifest.json"


if __name__ == "__main__":
    collector.main()
