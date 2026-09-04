"""Read-only, resumable collector for the current Kaggriculture Top-50.

This intentionally reuses the audited Top-100 collector while redirecting all
artifacts to the isolated ``experiments/top50_corpus`` namespace.  It exposes
no submission or upload operation.
"""

from pathlib import Path

import collect_super_replays as collector


ROOT = Path(__file__).resolve().parent
collector.CORPUS = ROOT / "experiments/top50_corpus"
collector.REPLAYS = collector.CORPUS / "replays"
collector.PARTIAL = ROOT / "experiments/top50_corpus_manifest.json.partial"
collector.OUTPUT = ROOT / "experiments/top50_corpus_manifest.json"


if __name__ == "__main__":
    collector.main()
