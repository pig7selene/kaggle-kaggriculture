"""Resumable, read-only replay collection for Super Replay Backbone V2.

This script has no submission or upload operation.  It collects every public
episode for the deployed V1 submission and a deep current Top-20 corpus.
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
V1_SUBMISSION_ID = 55467403
V1_DIR = ROOT / "experiments/v2_real_kaggle_replays"
V1_REPLAYS = V1_DIR / "replays"
V1_PARTIAL = V1_DIR / "manifest.json.partial"
V1_MANIFEST = V1_DIR / "manifest.json"
TOP20_DIR = ROOT / "experiments/v2_top20_corpus"
TOP20_REPLAYS = TOP20_DIR / "replays"
TOP20_PARTIAL = ROOT / "experiments/v2_top20_corpus_manifest.json.partial"
TOP20_MANIFEST = ROOT / "experiments/v2_top20_corpus_manifest.json"


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


def collect_v1(workers):
    V1_REPLAYS.mkdir(parents=True, exist_ok=True)
    api = KaggleApi()
    api.authenticate()
    episodes = [base._plain(value) for value in base._retry(
        lambda: api.competition_list_episodes(V1_SUBMISSION_ID),
        f"V1 submission {V1_SUBMISSION_ID}",
    )]
    episodes = [
        row for row in episodes
        if row.get("state") == "COMPLETED" and row.get("type") == "EPISODE_TYPE_PUBLIC"
    ]
    episodes.sort(key=lambda row: (row.get("endTime", ""), int(row["id"])))
    existing = json.loads(V1_PARTIAL.read_text()) if V1_PARTIAL.exists() else {}
    payload = {
        "schema_version": 1,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "submission_id": V1_SUBMISSION_ID,
        "selection": "all currently available completed public episodes",
        "episode_metadata": episodes,
        "episode_ids": [int(row["id"]) for row in episodes],
        "download_status": existing.get("download_status", {}),
        "episodes": [],
    }
    _write(V1_PARTIAL, payload)
    todo = [
        episode_id for episode_id in payload["episode_ids"]
        if not (V1_REPLAYS / f"episode-{episode_id}-replay.json").exists()
        or payload["download_status"].get(str(episode_id), {}).get("status") not in {"existing", "downloaded"}
    ]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_download_one, episode_id, V1_REPLAYS): episode_id for episode_id in todo}
        for index, future in enumerate(as_completed(futures), 1):
            episode_id, status, error = future.result()
            payload["download_status"][str(episode_id)] = {"status": status, "error": error}
            if index % 10 == 0 or index == len(futures):
                _write(V1_PARTIAL, payload)
                print(f"V1 replays {index}/{len(futures)}", flush=True)
    metadata = {int(row["id"]): row for row in episodes}
    records = []
    for episode_id in payload["episode_ids"]:
        path = V1_REPLAYS / f"episode-{episode_id}-replay.json"
        audit = base._validate_replay(path) if path.exists() else {"valid": False, "reason": "missing"}
        meta = metadata[episode_id]
        agents = meta.get("agents", [])
        seat = next(
            (index for index, row in enumerate(agents) if int(row.get("submissionId", 0)) == V1_SUBMISSION_ID),
            None,
        )
        records.append({
            "episode_id": episode_id,
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
    _write(V1_PARTIAL, payload)
    _write(V1_MANIFEST, payload)
    print(V1_MANIFEST, payload["summary"])


def collect_top20(workers, episodes_per_submission):
    TOP20_DIR.mkdir(parents=True, exist_ok=True)
    TOP20_REPLAYS.mkdir(parents=True, exist_ok=True)
    base.CORPUS = TOP20_DIR
    base.REPLAYS = TOP20_REPLAYS
    base.PARTIAL = TOP20_PARTIAL
    base.OUTPUT = TOP20_MANIFEST
    if TOP20_PARTIAL.exists():
        payload = json.loads(TOP20_PARTIAL.read_text())
        compatible = (
            payload.get("target_top_n") == 20
            and payload.get("episodes_per_submission_target") == episodes_per_submission
            and len(payload.get("leaderboard", [])) == 20
            and len(payload.get("submissions", [])) == 20
        )
        if compatible:
            print(f"resuming {TOP20_PARTIAL}", flush=True)
            payload = base._complete_episode_metadata(payload, episodes_per_submission, workers)
        else:
            payload = base._collect_metadata(20, episodes_per_submission, workers)
    else:
        payload = base._collect_metadata(20, episodes_per_submission, workers)
    todo = [
        episode_id for episode_id in payload["selected_episode_ids"]
        if payload["download_status"].get(str(episode_id), {}).get("status") not in {"downloaded", "existing"}
        or not (TOP20_REPLAYS / f"episode-{episode_id}-replay.json").exists()
    ]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(base._download, episode_id): episode_id for episode_id in todo}
        for index, future in enumerate(as_completed(futures), 1):
            episode_id, status, error = future.result()
            payload["download_status"][str(episode_id)] = {"status": status, "error": error}
            if index % 10 == 0 or index == len(futures):
                _write(TOP20_PARTIAL, payload)
                print(f"Top20 replays {index}/{len(futures)}", flush=True)
    payload = base._finalize(payload)
    # The newest two appearances per selected submission are held out from all
    # route extraction and tuning.  They remain recorded for locked final use.
    holdout = set()
    for row in payload["submissions"]:
        ids = list(row.get("selected_episode_ids", []))
        holdout.update(ids[:2])
    for episode in payload["episodes"]:
        episode["split"] = "final_holdout" if episode["episode_id"] in holdout else "development"
    payload["splits"] = {
        "policy": "two newest selected appearances per submission held untouched until finalists lock",
        "development_episode_ids": [row["episode_id"] for row in payload["episodes"] if row["split"] == "development"],
        "final_holdout_episode_ids": [row["episode_id"] for row in payload["episodes"] if row["split"] == "final_holdout"],
    }
    _write(TOP20_PARTIAL, payload)
    _write(TOP20_MANIFEST, payload)
    print(TOP20_MANIFEST)
    print(json.dumps({**payload["corpus_summary"], "split_counts": {
        "development": len(payload["splits"]["development_episode_ids"]),
        "final_holdout": len(payload["splits"]["final_holdout_episode_ids"]),
    }}, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--episodes-per-submission", type=int, default=12)
    parser.add_argument("--only", choices=("v1", "top20", "all"), default="all")
    args = parser.parse_args()
    if args.only in {"v1", "all"}:
        collect_v1(args.workers)
    if args.only in {"top20", "all"}:
        collect_top20(args.workers, args.episodes_per_submission)


if __name__ == "__main__":
    main()
