"""Resumable read-only corpus collector for Super Replay Backbone V3.

There is deliberately no submission or upload operation in this module.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path

from kaggle.api.kaggle_api_extended import KaggleApi

import collect_super_replays as base


ROOT = Path(__file__).resolve().parent
V2_SUBMISSION_ID = 55473991
V2_DIR = ROOT / "experiments/v3_real_v2_replays"
V2_REPLAYS = V2_DIR / "replays"
V2_PARTIAL = V2_DIR / "manifest.json.partial"
V2_MANIFEST = V2_DIR / "manifest.json"

TOP10_DIR = ROOT / "experiments/v3_top10_corpus"
TOP10_REPLAYS = TOP10_DIR / "replays"
TOP10_PARTIAL = ROOT / "experiments/v3_top10_corpus_manifest.json.partial"
TOP10_MANIFEST = ROOT / "experiments/v3_top10_corpus_manifest.json"


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def _download_one(episode_id, replay_dir):
    old = base.REPLAYS
    try:
        base.REPLAYS = replay_dir
        return base._download(episode_id)
    finally:
        base.REPLAYS = old


def collect_v2(workers):
    V2_REPLAYS.mkdir(parents=True, exist_ok=True)
    api = KaggleApi()
    api.authenticate()
    episodes = [base._plain(value) for value in base._retry(
        lambda: api.competition_list_episodes(V2_SUBMISSION_ID),
        f"V2 submission {V2_SUBMISSION_ID}",
    )]
    episodes = [row for row in episodes if row.get("state") == "COMPLETED" and row.get("type") == "EPISODE_TYPE_PUBLIC"]
    episodes.sort(key=lambda row: (row.get("endTime", ""), int(row["id"])))
    existing = json.loads(V2_PARTIAL.read_text()) if V2_PARTIAL.exists() else {}
    payload = {
        "schema_version": 1,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "submission_id": V2_SUBMISSION_ID,
        "deployment_identification": (
            "latest completed user submission after V2 package creation; inferred deployed V2 "
            "from submission timestamp and repository packaging history"
        ),
        "selection": "all currently available completed public episodes",
        "episode_metadata": episodes,
        "episode_ids": [int(row["id"]) for row in episodes],
        "download_status": existing.get("download_status", {}),
        "episodes": [],
    }
    _write(V2_PARTIAL, payload)
    todo = [
        eid for eid in payload["episode_ids"]
        if not (V2_REPLAYS / f"episode-{eid}-replay.json").exists()
        or payload["download_status"].get(str(eid), {}).get("status") not in {"existing", "downloaded"}
    ]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_download_one, eid, V2_REPLAYS): eid for eid in todo}
        for index, future in enumerate(as_completed(futures), 1):
            eid, status, error = future.result()
            payload["download_status"][str(eid)] = {"status": status, "error": error}
            if index % 10 == 0 or index == len(futures):
                _write(V2_PARTIAL, payload)
                print(f"V2 replays {index}/{len(futures)}", flush=True)
    metadata = {int(row["id"]): row for row in episodes}
    records = []
    for eid in payload["episode_ids"]:
        path = V2_REPLAYS / f"episode-{eid}-replay.json"
        audit = base._validate_replay(path) if path.exists() else {"valid": False, "reason": "missing"}
        meta = metadata[eid]
        agents = meta.get("agents", [])
        seat = next((i for i, row in enumerate(agents) if int(row.get("submissionId", 0)) == V2_SUBMISSION_ID), None)
        records.append({
            "episode_id": eid,
            "replay_path": str(path.relative_to(ROOT)) if path.exists() else None,
            "valid": bool(audit.get("valid")),
            "invalid_reason": audit.get("reason"),
            "seed": audit.get("seed"),
            "seat": seat,
            "team_names": audit.get("team_names"),
            "final_money": audit.get("final_money"),
            "winner_seat": audit.get("winner"),
            "file_sha256": audit.get("file_sha256"),
            "agents": agents,
            "create_time": meta.get("createTime"),
            "end_time": meta.get("endTime"),
        })
    payload["episodes"] = records
    payload["summary"] = {
        "available_public_episodes": len(episodes),
        "valid_replays": sum(row["valid"] for row in records),
        "invalid_or_missing": sum(not row["valid"] for row in records),
        "seat_identified": sum(row["seat"] in (0, 1) for row in records),
    }
    _write(V2_PARTIAL, payload)
    _write(V2_MANIFEST, payload)
    print(V2_MANIFEST, payload["summary"])


def _apply_splits(payload, final_count=4, selection_count=3):
    """Freeze per-submission splits; globally choose the most protected tier."""
    episode_tiers = {}
    priority = {"development": 0, "selection": 1, "final_holdout": 2}
    appearance_splits = []
    for submission in payload["submissions"]:
        ids = list(submission.get("selected_episode_ids", []))
        tiers = {}
        for index, eid in enumerate(ids):
            tier = "final_holdout" if index < final_count else "selection" if index < final_count + selection_count else "development"
            tiers[str(eid)] = tier
            if priority[tier] > priority.get(episode_tiers.get(eid, "development"), 0) or eid not in episode_tiers:
                episode_tiers[eid] = tier
            appearance_splits.append({
                "selected_submission_id": submission.get("selected_submission_id"),
                "team_id": submission.get("team_id"),
                "team_name": submission.get("team_name"),
                "rank": submission.get("rank"),
                "episode_id": eid,
                "recency_index": index,
                "split": tier,
            })
        submission["appearance_splits"] = tiers
    for episode in payload.get("episodes", []):
        episode["split"] = episode_tiers.get(episode["episode_id"], "development")
    payload["splits"] = {
        "frozen_before_action_analysis": True,
        "policy": (
            f"per selected submission: newest {final_count} final holdout, next {selection_count} selection, "
            "remaining development; overlapping episodes receive most protected global tier"
        ),
        "appearance_splits": appearance_splits,
        "development_episode_ids": sorted(eid for eid, tier in episode_tiers.items() if tier == "development"),
        "selection_episode_ids": sorted(eid for eid, tier in episode_tiers.items() if tier == "selection"),
        "final_holdout_episode_ids": sorted(eid for eid, tier in episode_tiers.items() if tier == "final_holdout"),
    }
    return payload


def collect_top10(workers, episodes_per_submission):
    TOP10_DIR.mkdir(parents=True, exist_ok=True)
    TOP10_REPLAYS.mkdir(parents=True, exist_ok=True)
    base.CORPUS, base.REPLAYS, base.PARTIAL, base.OUTPUT = TOP10_DIR, TOP10_REPLAYS, TOP10_PARTIAL, TOP10_MANIFEST
    if TOP10_PARTIAL.exists():
        payload = json.loads(TOP10_PARTIAL.read_text())
        compatible = (
            payload.get("target_top_n") == 10
            and payload.get("episodes_per_submission_target") == episodes_per_submission
            and len(payload.get("leaderboard", [])) == 10
            and len(payload.get("submissions", [])) == 10
        )
        payload = base._complete_episode_metadata(payload, episodes_per_submission, workers) if compatible else base._collect_metadata(10, episodes_per_submission, workers)
    else:
        payload = base._collect_metadata(10, episodes_per_submission, workers)

    # The split is established from episode metadata before replay actions are
    # analyzed. Downloading held-out files does not reveal them to development.
    payload = _apply_splits(payload)
    _write(TOP10_PARTIAL, payload)
    todo = [
        eid for eid in payload["selected_episode_ids"]
        if payload["download_status"].get(str(eid), {}).get("status") not in {"downloaded", "existing"}
        or not (TOP10_REPLAYS / f"episode-{eid}-replay.json").exists()
    ]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(base._download, eid): eid for eid in todo}
        for index, future in enumerate(as_completed(futures), 1):
            eid, status, error = future.result()
            payload["download_status"][str(eid)] = {"status": status, "error": error}
            if index % 10 == 0 or index == len(futures):
                _write(TOP10_PARTIAL, payload)
                print(f"Top10 replays {index}/{len(futures)}", flush=True)
    payload = base._finalize(payload)
    payload = _apply_splits(payload)
    payload["corpus_summary"]["split_unique_episode_counts"] = {
        key.removesuffix("_episode_ids"): len(value)
        for key, value in payload["splits"].items() if key.endswith("_episode_ids")
    }
    _write(TOP10_PARTIAL, payload)
    _write(TOP10_MANIFEST, payload)
    print(TOP10_MANIFEST)
    print(json.dumps(payload["corpus_summary"], indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--episodes-per-submission", type=int, default=16)
    parser.add_argument("--only", choices=("v2", "top10", "all"), default="all")
    args = parser.parse_args()
    if args.only in {"v2", "all"}:
        collect_v2(args.workers)
    if args.only in {"top10", "all"}:
        collect_top10(args.workers, args.episodes_per_submission)


if __name__ == "__main__":
    main()
