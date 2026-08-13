"""Checkpointed exact bank-transition audit for every elite corpus replay."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path

from analyze_top_player_replays import _transition_ledger


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "experiments/super_replay_corpus_manifest.json"
OUTPUT = ROOT / "experiments/super_replay_financial_audit.json"
PARTIAL = ROOT / "experiments/super_replay_financial_audit.json.partial"


def _audit(path):
    replay = json.loads(Path(path).read_text())
    mismatches = []
    totals = [
        {"sale_revenue": 0, "seed_spend": 0, "product_spend": 0, "animal_spend": 0, "land_spend": 0, "labor_spend": 0}
        for _ in range(2)
    ]
    for index in range(1, len(replay["steps"])):
        ledgers, errors = _transition_ledger(replay["steps"][index - 1], replay["steps"][index], replay.get("configuration", {}))
        mismatches.extend({"step": index, **error} for error in errors)
        for player, ledger in enumerate(ledgers):
            totals[player]["sale_revenue"] += sum(ledger["sale_revenue"].values())
            totals[player]["seed_spend"] += sum(ledger["seed_spend"].values())
            totals[player]["product_spend"] += sum(ledger["product_spend"].values())
            totals[player]["animal_spend"] += sum(ledger["animal_spend"].values())
            totals[player]["land_spend"] += ledger["land_spend"]
            totals[player]["labor_spend"] += ledger["labor_spend"]
    return {
        "episode_id": int(replay["info"]["EpisodeId"]), "replay_path": str(Path(path).relative_to(ROOT)),
        "steps": len(replay["steps"]), "mismatch_count": len(mismatches), "mismatches": mismatches,
        "financial_totals": totals,
        "final_money": [float(value["reward"]) for value in replay["steps"][-1]],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text())
    paths = [ROOT / row["replay_path"] for row in manifest["episodes"] if row["replay_valid"] and row["duplicate_status"] == "unique"]
    rows = json.loads(PARTIAL.read_text()).get("episodes", []) if PARTIAL.is_file() else []
    done = {row["episode_id"] for row in rows}
    todo = [path for path in paths if int(path.stem.split("-")[1]) not in done]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(_audit, path) for path in todo]
        for index, future in enumerate(as_completed(futures), 1):
            rows.append(future.result())
            if index % 10 == 0 or index == len(futures):
                PARTIAL.write_text(json.dumps({"schema_version": 1, "episodes": rows}) + "\n")
                print(f"episodes {index}/{len(futures)}", flush=True)
    rows.sort(key=lambda row: row["episode_id"])
    payload = {
        "schema_version": 1, "audited_unique_replays": len(rows),
        "total_bank_transition_mismatches": sum(row["mismatch_count"] for row in rows),
        "episodes_with_mismatches": sum(row["mismatch_count"] > 0 for row in rows),
        "episodes": rows,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(OUTPUT, payload["audited_unique_replays"], payload["total_bank_transition_mismatches"])


if __name__ == "__main__":
    main()
