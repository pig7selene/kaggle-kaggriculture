"""Resumable triage and serious validation for distilled Top-50 candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import run_super_replay_search as engine
from run_top50_parent_league import BASELINE, _jobs, _paired


ROOT = Path(__file__).resolve().parent
CANDIDATES = {
    "dmitry_safe": "agents/top50_distilled/top50_dmitry_safe.py",
    "hanserong_safe": "agents/top50_distilled/top50_hanserong_safe.py",
    "redblack_safe": "agents/top50_distilled/top50_redblack_safe.py",
    "observable_portfolio": "agents/top50_distilled/top50_observable_portfolio.py",
}


def _sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("cheap", "serious"), default="cheap")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--names", default="")
    args = parser.parse_args()
    candidates = dict(CANDIDATES)
    if args.names:
        wanted = {value for value in args.names.split(",") if value}
        candidates = {name: path for name, path in candidates.items() if name in wanted}
    all_candidates = {"V2_baseline": BASELINE, **candidates}
    output = ROOT / f"experiments/top50_candidate_{args.mode}_guard3.json"
    engine.PARTIAL = output.with_suffix(output.suffix + ".partial")
    games = engine._run_jobs(_jobs(all_candidates, args.mode), args.workers)
    payload = {
        "schema_version": 1, "mode": args.mode, "baseline": BASELINE,
        "candidates": candidates, "source_hashes": {name: _sha(path) for name, path in candidates.items()},
        "games": games, "summary": engine._summaries(games), "paired_vs_v2": _paired(games, BASELINE),
    }
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(output)
    for path, paired in sorted(payload["paired_vs_v2"].items(), key=lambda pair: pair[1]["paired_own_money_delta_mean"] or -1e99, reverse=True):
        summary = payload["summary"][path]
        print(path, paired["pairs"], paired["paired_wins"], paired["paired_losses"], round(paired["paired_own_money_delta_mean"], 1), round(paired["paired_own_money_delta_p10"], 1), round(summary["average_advantage"], 1), summary["livestock_losses"], summary["meaningful_stranding_games"], summary["runtime_failures"], summary["semantic_failures"])


if __name__ == "__main__":
    main()
