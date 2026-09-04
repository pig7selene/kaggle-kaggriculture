"""Collect post-lock unused episodes for the 11 refined Top-50 families.

Read-only Kaggle API usage only; this module has no submission/upload path.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from kaggle.api.kaggle_api_extended import KaggleApi

from collect_super_replays import _plain, _retry, _validate_replay


ROOT = Path(__file__).resolve().parent
CORPUS = ROOT / "experiments/top50_corpus_manifest.json"
FAMILIES = ROOT / "experiments/top50_strategy_families.json"
LOCK = ROOT / "experiments/top50_finalist_lock.json"
OUTDIR = ROOT / "experiments/top50_unseen/replays"
PARTIAL = ROOT / "experiments/top50_unseen_manifest.json.partial"
OUTPUT = ROOT / "experiments/top50_unseen_manifest.json"


def _write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def main():
    if not LOCK.exists():
        raise SystemExit("finalist must be locked before unseen episodes are queried")
    corpus = json.loads(CORPUS.read_text())
    families = json.loads(FAMILIES.read_text())["families"]
    used = {int(value) for value in corpus["selected_episode_ids"]}
    submissions = {int(row["selected_submission_id"]): row for row in corpus["submissions"]}
    targets = []
    for family in families:
        submission_id = int(family["medoid_submission"])
        target = submissions[submission_id]
        targets.append({
            "family_id": family["family_id"], "submission_id": submission_id,
            "rank": target["rank"], "team_name": target["team_name"],
        })
    payload = json.loads(PARTIAL.read_text()) if PARTIAL.exists() else {
        "schema_version": 1, "captured_at": datetime.now(timezone.utc).isoformat(),
        "selection": "two most recent completed public episodes per refined family medoid not present in the six-appearance mining corpus",
        "finalist_lock_sha256": hashlib.sha256(LOCK.read_bytes()).hexdigest(),
        "episodes": [], "errors": [],
    }
    done = {(row["submission_id"], row["episode_id"]) for row in payload["episodes"]}
    api = KaggleApi(); api.authenticate(); OUTDIR.mkdir(parents=True, exist_ok=True)
    for target in targets:
        submission_id = target["submission_id"]
        try:
            values = [_plain(value) for value in _retry(lambda: api.competition_list_episodes(submission_id), f"top50 unseen {submission_id}")]
            values = [row for row in values if row.get("state") == "COMPLETED" and row.get("type") == "EPISODE_TYPE_PUBLIC" and int(row["id"]) not in used]
            values.sort(key=lambda row: (row.get("endTime", ""), int(row["id"])), reverse=True)
            for meta in values[:2]:
                episode_id = int(meta["id"])
                if (submission_id, episode_id) in done:
                    continue
                path = OUTDIR / f"episode-{episode_id}-replay.json"
                if not path.exists():
                    _retry(lambda: api.competition_episode_replay(episode_id, path=str(OUTDIR), quiet=True), f"top50 unseen replay {episode_id}")
                audit = _validate_replay(path)
                if not audit["valid"]:
                    raise RuntimeError(f"invalid replay {episode_id}: {audit['reason']}")
                player = next(index for index, agent in enumerate(meta["agents"]) if int(agent["submissionId"]) == submission_id)
                payload["episodes"].append({
                    **target, "episode_id": episode_id, "player": player, "seed": audit["seed"],
                    "replay_path": str(path.relative_to(ROOT)), "file_sha256": audit["file_sha256"],
                    "final_money": audit["final_money"][player], "opponent_money": audit["final_money"][1-player],
                })
                done.add((submission_id, episode_id)); used.add(episode_id); _write(PARTIAL, payload)
                print(f"{target['family_id']} rank {target['rank']}: episode {episode_id}", flush=True)
        except Exception as error:
            payload["errors"].append({**target, "error": repr(error)})
            _write(PARTIAL, payload)
    payload["summary"] = {
        "families_targeted": len(targets), "episodes": len(payload["episodes"]), "errors": len(payload["errors"]),
        "families_represented": len({row["family_id"] for row in payload["episodes"]}),
    }
    _write(OUTPUT, payload)
    print(OUTPUT, payload["summary"])


if __name__ == "__main__":
    main()
