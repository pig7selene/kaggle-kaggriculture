"""Collect a post-finalist-lock unseen replay split (read-only Kaggle API)."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from kaggle.api.kaggle_api_extended import KaggleApi

from collect_super_replays import _plain, _retry, _validate_replay


ROOT = Path(__file__).resolve().parent
CORPUS = ROOT / "experiments/super_replay_corpus_manifest.json"
OUTDIR = ROOT / "experiments/super_replay_unseen/replays"
PARTIAL = ROOT / "experiments/super_replay_unseen_manifest.json.partial"
OUTPUT = ROOT / "experiments/super_replay_unseen_manifest.json"
LOCK = ROOT / "experiments/super_replay_unseen_finalists_lock.json"

FINALISTS = {
    "K3": "agents/v27_replay_weed_guard.py",
    "family02": "agents/super_replay/super_family_02_medoid.py",
    "raw_ricardo": "agents/super_replay/super_raw_55459817.py",
}


def _write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main():
    if not LOCK.exists():
        _write(LOCK, {
            "locked_at": datetime.now(timezone.utc).isoformat(),
            "finalists": FINALISTS,
            "selection_result_sha256": hashlib.sha256(
                (ROOT / "experiments/super_replay_selection_results.json").read_bytes()
            ).hexdigest(),
            "policy": "No candidate additions or tuning after this lock; only these finalists see the new episodes.",
        })

    corpus = json.loads(CORPUS.read_text())
    used = {int(value) for value in corpus["selected_episode_ids"]}
    targets = [row for row in corpus["submissions"] if 86 <= row["rank"] <= 100]
    payload = json.loads(PARTIAL.read_text()) if PARTIAL.exists() else {
        "schema_version": 1, "captured_at": datetime.now(timezone.utc).isoformat(),
        "selection": "one most-recent completed public episode per rank 86-100 submission not present in the development corpus",
        "finalists_lock": str(LOCK.relative_to(ROOT)), "episodes": [], "errors": [],
    }
    done = {row["submission_id"] for row in payload["episodes"]}
    api = KaggleApi(); api.authenticate(); OUTDIR.mkdir(parents=True, exist_ok=True)
    for target in targets:
        submission_id = int(target["selected_submission_id"])
        if submission_id in done:
            continue
        try:
            candidates = [_plain(value) for value in _retry(
                lambda: api.competition_list_episodes(submission_id), f"unseen submission {submission_id}"
            )]
            candidates = [row for row in candidates if row.get("state") == "COMPLETED" and row.get("type") == "EPISODE_TYPE_PUBLIC" and int(row["id"]) not in used]
            candidates.sort(key=lambda row: (row.get("endTime", ""), int(row["id"])), reverse=True)
            if not candidates:
                raise RuntimeError("no unused completed public replay")
            meta = candidates[0]; episode_id = int(meta["id"])
            path = OUTDIR / f"episode-{episode_id}-replay.json"
            if not path.exists():
                _retry(lambda: api.competition_episode_replay(episode_id, path=str(OUTDIR), quiet=True), f"unseen episode {episode_id}")
            audit = _validate_replay(path)
            if not audit["valid"]:
                raise RuntimeError(f"invalid replay: {audit['reason']}")
            player = next(index for index, agent in enumerate(meta["agents"]) if int(agent["submissionId"]) == submission_id)
            payload["episodes"].append({
                "rank": target["rank"], "submission_id": submission_id,
                "team_name": target["team_name"], "episode_id": episode_id,
                "player": player, "seed": audit["seed"],
                "final_money": audit["final_money"][player],
                "opponent_money": audit["final_money"][1 - player],
                "replay_path": str(path.relative_to(ROOT)),
                "file_sha256": audit["file_sha256"], "steps": 720, "actions": 719,
            })
            used.add(episode_id)
            _write(PARTIAL, payload)
            print(f"rank {target['rank']}: episode {episode_id}", flush=True)
        except Exception as error:
            payload["errors"].append({"rank": target["rank"], "submission_id": submission_id, "error": repr(error)})
            _write(PARTIAL, payload)
    payload["summary"] = {
        "episodes": len(payload["episodes"]), "errors": len(payload["errors"]),
        "rank_min": min((row["rank"] for row in payload["episodes"]), default=None),
        "rank_max": max((row["rank"] for row in payload["episodes"]), default=None),
    }
    _write(OUTPUT, payload)
    print(OUTPUT, payload["summary"])


if __name__ == "__main__":
    main()
