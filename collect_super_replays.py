"""Checkpointed read-only collector for the elite Kaggriculture replay corpus.

The script only calls public leaderboard/submission/episode/replay read APIs.
It contains no submission or upload operation.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import time

from kaggle.api.kaggle_api_extended import KaggleApi


ROOT = Path(__file__).resolve().parent
CORPUS = ROOT / "experiments/super_replay_corpus"
REPLAYS = CORPUS / "replays"
PARTIAL = ROOT / "experiments/super_replay_corpus_manifest.json.partial"
OUTPUT = ROOT / "experiments/super_replay_corpus_manifest.json"


def _plain(value):
    return value.to_dict() if hasattr(value, "to_dict") else dict(vars(value))


def _retry(call, label, attempts=9):
    for attempt in range(attempts):
        try:
            value = call()
            # Keep the public API well below its burst limit when callers use
            # low concurrency. Jitter prevents synchronized retries.
            time.sleep(0.8 + random.random() * 0.4)
            return value
        except Exception as error:
            code = getattr(getattr(error, "response", None), "status_code", None)
            transient = code in {429, 500, 502, 503, 504} or code is None
            if attempt + 1 == attempts or not transient:
                raise
            delay = min(60, 5 * (2 ** attempt)) + random.random() * 2
            print(f"retry {label}: status={code} attempt={attempt + 1} wait={delay:.1f}s", flush=True)
            time.sleep(delay)


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _normalize_action(replay, player, step):
    action = deepcopy(replay["steps"][step + 1][player].get("action") or {})
    obs = replay["steps"][step][player]["observation"]
    count = len(obs["farms"][player].get("hands", []))
    hands = list(action.get("hands", []))
    hands.extend([["PASS"]] * max(0, count - len(hands)))
    return {
        "farmer": action.get("farmer", ["PASS"]),
        "hands": hands[:count],
        "market": list(action.get("market", []))[:10],
    }


def _validate_replay(path):
    try:
        replay = json.loads(path.read_text())
    except Exception as error:
        return {"valid": False, "reason": f"json:{error!r}"}
    steps = replay.get("steps", [])
    names = replay.get("info", {}).get("TeamNames", [])
    if len(steps) != 720 or len(names) != 2:
        return {"valid": False, "reason": f"shape:steps={len(steps)} teams={len(names)}"}
    if any(len(states) != 2 for states in steps):
        return {"valid": False, "reason": "shape:non-two-player-step"}
    actions = []
    appearance_hashes = []
    for player in (0, 1):
        normalized = [_normalize_action(replay, player, step) for step in range(719)]
        actions.append(normalized)
        appearance_hashes.append(hashlib.sha256(_canonical(normalized).encode()).hexdigest())
    trajectory_hash = hashlib.sha256(_canonical(actions).encode()).hexdigest()
    final = steps[-1]
    final_money = [float(final[player].get("reward", 0)) for player in (0, 1)]
    statuses = [final[player].get("status") for player in (0, 1)]
    if statuses != ["DONE", "DONE"]:
        return {"valid": False, "reason": f"statuses:{statuses}"}
    return {
        "valid": True,
        "reason": None,
        "episode_id": int(replay["info"].get("EpisodeId", replay.get("id"))),
        "seed": int(replay["info"].get("seed", replay.get("configuration", {}).get("seed", 0))),
        "team_names": list(names),
        "final_money": final_money,
        "winner": None if final_money[0] == final_money[1] else int(final_money[1] > final_money[0]),
        "statuses": statuses,
        "action_counts": [719, 719],
        "appearance_action_hashes": appearance_hashes,
        "trajectory_hash": trajectory_hash,
        "file_sha256": _sha256(path),
        "size_bytes": path.stat().st_size,
    }


def _select_submission(team):
    api = KaggleApi()
    api.authenticate()
    submissions = [_plain(value) for value in (_retry(
        lambda: api.competition_team_submissions(int(team["team_id"])),
        f"team {team['team_id']}",
    ) or [])]
    for row in submissions:
        row["public_score_numeric"] = float(row.get("publicScore") or "-inf")
    submissions.sort(key=lambda row: (row["public_score_numeric"], row.get("dateSubmitted", "")), reverse=True)
    selected = submissions[0] if submissions else None
    return team["team_id"], submissions, selected


def _episodes(submission):
    api = KaggleApi()
    api.authenticate()
    values = [_plain(value) for value in (_retry(
        lambda: api.competition_list_episodes(int(submission["id"])),
        f"submission {submission['id']}",
    ) or [])]
    values = [
        row for row in values
        if row.get("state") == "COMPLETED" and row.get("type") == "EPISODE_TYPE_PUBLIC"
    ]
    values.sort(key=lambda row: (row.get("endTime", ""), int(row["id"])), reverse=True)
    return int(submission["id"]), values


def _download(episode_id):
    path = REPLAYS / f"episode-{episode_id}-replay.json"
    if path.is_file() and _validate_replay(path).get("valid"):
        return int(episode_id), "existing", None
    api = KaggleApi()
    api.authenticate()
    try:
        _retry(
            lambda: api.competition_episode_replay(int(episode_id), path=str(REPLAYS), quiet=True),
            f"episode {episode_id}",
        )
        audit = _validate_replay(path)
        if not audit.get("valid"):
            return int(episode_id), "invalid", audit.get("reason")
        return int(episode_id), "downloaded", None
    except Exception as error:
        return int(episode_id), "failed", repr(error)


def _write(payload):
    PARTIAL.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def _collect_metadata(top_n, episodes_per_submission, workers):
    api = KaggleApi()
    api.authenticate()
    leaderboard = [_plain(value) for value in (_retry(
        lambda: api.competition_leaderboard_view("kaggriculture", page_size=top_n),
        "leaderboard",
    ) or [])]
    teams = [
        {
            "rank": index + 1,
            "team_id": int(row["teamId"]),
            "team_name": row["teamName"],
            "leaderboard_score": float(row["score"]),
            "leaderboard_submission_date": row.get("submissionDate"),
        }
        for index, row in enumerate(leaderboard[:top_n])
    ]
    payload = {
        "schema_version": 1,
        "competition": "kaggriculture",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "selection_rule": (
            f"Top {top_n} public leaderboard teams; highest-public-score active submission per team; "
            f"{episodes_per_submission} most recent completed public appearances per selected submission"
        ),
        "target_top_n": top_n,
        "episodes_per_submission_target": episodes_per_submission,
        "leaderboard": teams,
        "submissions": [],
        "selected_episode_ids": [],
        "download_status": {},
        "episodes": [],
        "corpus_summary": {},
    }
    _write(payload)

    submission_map = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_select_submission, team): team for team in teams}
        for index, future in enumerate(as_completed(futures), 1):
            team_id, submissions, selected = future.result()
            submission_map[team_id] = (submissions, selected)
            if index % 10 == 0 or index == len(futures):
                print(f"team submissions {index}/{len(futures)}", flush=True)
    for team in teams:
        submissions, selected = submission_map.get(team["team_id"], ([], None))
        row = dict(team)
        row["active_public_submissions"] = submissions
        row["selected_submission_id"] = int(selected["id"]) if selected else None
        row["selected_submission_score"] = selected.get("public_score_numeric") if selected else None
        row["score_matches_leaderboard"] = bool(
            selected and abs(float(selected["public_score_numeric"]) - float(team["leaderboard_score"])) < 1e-6
        )
        row["repeated_submission_versions"] = max(0, len(submissions) - 1)
        payload["submissions"].append(row)
    _write(payload)

    return _complete_episode_metadata(payload, episodes_per_submission, workers)


def _complete_episode_metadata(payload, episodes_per_submission, workers):
    selected_submissions = []
    for row in payload["submissions"]:
        if not row.get("selected_submission_id") or row.get("episode_metadata_complete"):
            continue
        match = next(
            (value for value in row.get("active_public_submissions", []) if int(value["id"]) == int(row["selected_submission_id"])),
            None,
        )
        if match:
            selected_submissions.append(match)

    episode_map = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_episodes, submission): submission for submission in selected_submissions}
        for index, future in enumerate(as_completed(futures), 1):
            submission = futures[future]
            try:
                submission_id, episodes = future.result()
                episode_map[submission_id] = episodes
                row = next(value for value in payload["submissions"] if value.get("selected_submission_id") == submission_id)
                row["available_completed_public_episodes"] = len(episodes)
                row["selected_episode_metadata"] = episodes[:episodes_per_submission]
                row["selected_episode_ids"] = [int(value["id"]) for value in row["selected_episode_metadata"]]
                row["episode_metadata_complete"] = True
                row.pop("episode_metadata_error", None)
            except Exception as error:
                row = next(value for value in payload["submissions"] if value.get("selected_submission_id") == int(submission["id"]))
                row["episode_metadata_error"] = repr(error)
            if index % 5 == 0 or index == len(futures):
                _write(payload)
                print(f"submission episodes {index}/{len(futures)}", flush=True)
    selected_episode_ids = [episode_id for row in payload["submissions"] for episode_id in row.get("selected_episode_ids", [])]
    payload["selected_episode_ids"] = sorted(set(selected_episode_ids))
    payload["corpus_summary"] = {
        "leaderboard_teams": len(payload["leaderboard"]),
        "selected_submissions": sum(bool(row.get("selected_submission_id")) for row in payload["submissions"]),
        "episode_metadata_complete_submissions": sum(bool(row.get("episode_metadata_complete")) for row in payload["submissions"]),
        "episode_metadata_failed_submissions": sum(bool(row.get("episode_metadata_error")) for row in payload["submissions"]),
        "requested_appearances_before_episode_dedup": len(selected_episode_ids),
        "unique_episode_ids_selected": len(payload["selected_episode_ids"]),
        "duplicate_episode_references": len(selected_episode_ids) - len(set(selected_episode_ids)),
    }
    _write(payload)
    return payload


def _finalize(payload):
    leaderboard = {int(row["team_id"]): row for row in payload["submissions"]}
    submission_to_team = {
        int(row["selected_submission_id"]): row for row in payload["submissions"] if row.get("selected_submission_id")
    }
    episode_meta = {}
    for submission in payload["submissions"]:
        for row in submission.get("selected_episode_metadata", []):
            episode_meta[int(row["id"])] = row
    records = []
    trajectory_owner = {}
    appearance_owner = {}
    for episode_id in payload["selected_episode_ids"]:
        path = REPLAYS / f"episode-{episode_id}-replay.json"
        audit = _validate_replay(path) if path.is_file() else {"valid": False, "reason": "missing"}
        metadata = episode_meta.get(int(episode_id), {})
        agents = metadata.get("agents", [])
        appearances = []
        for player, agent in enumerate(agents):
            submission_id = int(agent.get("submissionId", 0))
            team_id = int(agent.get("teamId", 0))
            top = leaderboard.get(team_id)
            action_hash = audit.get("appearance_action_hashes", [None, None])[player] if audit.get("valid") else None
            duplicate = appearance_owner.get(action_hash) if action_hash else None
            if action_hash and not duplicate:
                appearance_owner[action_hash] = {"episode_id": int(episode_id), "seat": player}
            appearances.append({
                "seat": player,
                "submission_id": submission_id,
                "team_id": team_id,
                "team_name": agent.get("teamName"),
                "leaderboard_rank": top.get("rank") if top else None,
                "leaderboard_score": top.get("leaderboard_score") if top else None,
                "is_selected_elite_submission": submission_id in submission_to_team,
                "reward": float(agent.get("reward", audit.get("final_money", [0, 0])[player] if audit.get("valid") else 0)),
                "action_count": audit.get("action_counts", [None, None])[player] if audit.get("valid") else None,
                "action_hash": action_hash,
                "identical_action_trajectory_duplicate_of": duplicate,
            })
        trajectory_hash = audit.get("trajectory_hash")
        duplicate_episode = trajectory_owner.get(trajectory_hash) if trajectory_hash else None
        if trajectory_hash and not duplicate_episode:
            trajectory_owner[trajectory_hash] = int(episode_id)
        records.append({
            "episode_id": int(episode_id),
            "source_identifier": f"kaggle competitions replay {episode_id}",
            "replay_path": str(path.relative_to(ROOT)) if path.is_file() else None,
            "replay_valid": bool(audit.get("valid")),
            "invalid_reason": audit.get("reason"),
            "seed": audit.get("seed"),
            "team_names": audit.get("team_names"),
            "final_money": audit.get("final_money"),
            "winner_seat": audit.get("winner"),
            "file_sha256": audit.get("file_sha256"),
            "size_bytes": audit.get("size_bytes"),
            "trajectory_hash": trajectory_hash,
            "duplicate_status": "identical_full_trajectory" if duplicate_episode else "unique",
            "duplicate_of_episode_id": duplicate_episode,
            "appearances": appearances,
            "route_family_metadata": None,
        })
    payload["episodes"] = records
    valid = [row for row in records if row["replay_valid"]]
    elite_appearances = [
        appearance for row in valid for appearance in row["appearances"]
        if appearance["is_selected_elite_submission"]
    ]
    payload["corpus_summary"].update({
        "downloads_complete": sum(payload["download_status"].get(str(value), {}).get("status") in {"existing", "downloaded"} for value in payload["selected_episode_ids"]),
        "download_failures": sum(payload["download_status"].get(str(value), {}).get("status") == "failed" for value in payload["selected_episode_ids"]),
        "valid_unique_replay_episodes": sum(row["replay_valid"] and row["duplicate_status"] == "unique" for row in records),
        "invalid_or_missing_replays": sum(not row["replay_valid"] for row in records),
        "selected_elite_appearances": len(elite_appearances),
        "unique_selected_submission_ids_in_appearances": len({row["submission_id"] for row in elite_appearances}),
        "rank_min": min((row["leaderboard_rank"] for row in elite_appearances if row["leaderboard_rank"]), default=None),
        "rank_max": max((row["leaderboard_rank"] for row in elite_appearances if row["leaderboard_rank"]), default=None),
        "identical_full_trajectory_duplicates": sum(row["duplicate_status"] != "unique" for row in records),
        "identical_single_agent_action_trajectory_duplicates": sum(bool(row["identical_action_trajectory_duplicate_of"]) for row in elite_appearances),
    })
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=100)
    parser.add_argument("--episodes-per-submission", type=int, default=4)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--metadata-only", action="store_true")
    args = parser.parse_args()
    CORPUS.mkdir(parents=True, exist_ok=True)
    REPLAYS.mkdir(parents=True, exist_ok=True)
    if PARTIAL.is_file():
        payload = json.loads(PARTIAL.read_text())
        compatible = (
            payload.get("target_top_n") == args.top
            and payload.get("episodes_per_submission_target") == args.episodes_per_submission
            and len(payload.get("leaderboard", [])) == args.top
            and len(payload.get("submissions", [])) == args.top
        )
        if compatible:
            print(f"resuming {PARTIAL}", flush=True)
            payload = _complete_episode_metadata(payload, args.episodes_per_submission, args.workers)
        else:
            payload = _collect_metadata(args.top, args.episodes_per_submission, args.workers)
    else:
        payload = _collect_metadata(args.top, args.episodes_per_submission, args.workers)
    if args.metadata_only:
        print(PARTIAL)
        print(json.dumps(payload["corpus_summary"], indent=2, ensure_ascii=False))
        return

    todo = [
        episode_id for episode_id in payload["selected_episode_ids"]
        if payload["download_status"].get(str(episode_id), {}).get("status") not in {"downloaded", "existing"}
        or not (REPLAYS / f"episode-{episode_id}-replay.json").is_file()
    ]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(_download, episode_id): episode_id for episode_id in todo}
        for index, future in enumerate(as_completed(futures), 1):
            episode_id, status, error = future.result()
            payload["download_status"][str(episode_id)] = {"status": status, "error": error}
            if index % 10 == 0 or index == len(futures):
                _write(payload)
                print(f"replays {index}/{len(futures)}", flush=True)
    payload = _finalize(payload)
    _write(payload)
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    print(OUTPUT)
    print(json.dumps(payload["corpus_summary"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
