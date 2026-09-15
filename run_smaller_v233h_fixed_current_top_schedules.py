"""Validate the locked candidate on exact current top-replay shop schedules."""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import statistics
import time

from kaggle_environments import make

from run_current_meta_fast_league import call, frozen_identity, load_agent
from run_epic_experiments import _run_with_fixed_shops
from run_latest_public_challenger_screen import semantic_check
from run_raw55899537_final_validation import animal_escapes
from run_smaller_v233h_cross_lineage_gauntlet import candidate_identity as locked_candidate_identity
from run_smaller_v233h_fixed_icecream_probe import fixed_schedule


ROOT = Path(__file__).resolve().parent
# Authoritative source is the in-repo manifest distilled by
# build_replay_seed_manifests.py.  REPLAYS is the original corpus; when it still
# exists the manifest is verified against it, otherwise it is simply unused.
SCHEDULE_MANIFEST = ROOT / "experiments/current_top_replay_schedule_manifest.json"
REPLAYS = Path("/private/tmp/kaggriculture_cross_lineage_20260912/replays")
CANDIDATE = ROOT / "agents/smaller_market_shock_v233h_safe/main.py"
OUTPUT = ROOT / "experiments/smaller_v233h_fixed_current_top_schedules.json"
OPPONENTS = {
    "Top50RedBlackSafe": ROOT / "agents/top50_distilled/top50_redblack_safe.py",
    "Top50HanserongSafe": ROOT / "agents/top50_distilled/top50_hanserong_safe.py",
    "EndToEndCohort": ROOT / "agents/autonomous_next/end_to_end_owner_cohort_v1.py",
}


def _schedules_from_replays():
    rows = []
    for path in sorted(REPLAYS.glob("episode-*-replay.json")):
        replay = json.loads(path.read_text())
        rows.append({
            "episode_id": int(replay["info"]["EpisodeId"]),
            "seed": int(replay["info"]["seed"]),
            "teams": list(replay["info"]["TeamNames"]),
            "shops": list(replay["steps"][-1][0]["observation"]["town"]["unlocked_shops"]),
        })
    return sorted(rows, key=lambda row: row["episode_id"])


def replay_schedules():
    """Read the manifest, and verify it whenever the original corpus is present."""
    if not SCHEDULE_MANIFEST.is_file():
        raise RuntimeError(
            f"{SCHEDULE_MANIFEST} is missing; regenerate it with build_replay_seed_manifests.py"
        )
    rows = json.loads(SCHEDULE_MANIFEST.read_text())["schedules"]
    if len(rows) != 15:
        raise RuntimeError(f"expected 15 replays, found {len(rows)}")
    if REPLAYS.is_dir():
        corpus = _schedules_from_replays()
        if corpus and corpus != sorted(rows, key=lambda row: row["episode_id"]):
            raise RuntimeError("schedule manifest disagrees with the original replay corpus")
    return rows


def candidate_identity(path):
    if path == CANDIDATE:
        return locked_candidate_identity()
    members = {
        member.name: hashlib.sha256(member.read_bytes()).hexdigest()
        for member in sorted(path.parent.iterdir()) if member.is_file()
    }
    return {
        "path": str(path.parent),
        "main_sha256": members["main.py"],
        "router_sha256": members["router.py"],
        "members": members,
        "matches_lock": False,
    }


def run_game(job):
    source, opponent_name, seat, candidate_path = job
    candidate = load_agent(candidate_path, f"fixedtop_candidate_{source['episode_id']}_{opponent_name}_{seat}")
    opponent = load_agent(OPPONENTS[opponent_name], f"fixedtop_opponent_{source['episode_id']}_{opponent_name}_{seat}")
    semantic_failures = []
    exceptions = [[], []]

    def checked(agent, index, validate=False):
        def wrapper(obs, configuration=None):
            try:
                action = call(agent, obs, configuration)
                if validate:
                    try:
                        semantic_check(obs, action)
                    except Exception as exc:
                        semantic_failures.append({"step": int(obs.get("step", -1)), "error": repr(exc)})
                return action
            except Exception as exc:
                exceptions[index].append({"step": int(obs.get("step", -1)), "error": repr(exc)})
                raise
        return wrapper

    pair = [None, None]
    pair[seat] = checked(candidate, seat, validate=True)
    pair[1 - seat] = checked(opponent, 1 - seat)
    env = make(
        "kaggriculture", configuration={"episodeSteps": 720, "seed": source["seed"]}, debug=False
    )
    runtime_error = None
    try:
        _run_with_fixed_shops(env, pair, fixed_schedule(source["shops"]))
    except Exception as exc:
        runtime_error = repr(exc)
    if len(getattr(env, "steps", [])) != 720:
        return {
            "source_episode_id": source["episode_id"], "opponent": opponent_name,
            "candidate_seat": seat, "runtime_error": runtime_error or "incomplete",
            "agent_error": True, "semantic_failures": semantic_failures,
            "exceptions_by_seat": exceptions,
        }
    final = env.steps[-1]
    own, other = float(final[seat].reward), float(final[1 - seat].reward)
    statuses = [str(final[index].status) for index in range(2)]
    realized = list(final[seat].observation["town"]["unlocked_shops"])
    return {
        "source_episode_id": source["episode_id"], "source_seed": source["seed"],
        "source_teams": source["teams"], "forced_shops": source["shops"],
        "opponent": opponent_name, "candidate_seat": seat,
        "realized_shops": realized, "shop_schedule_exact": realized == source["shops"],
        "outcome": "win" if own > other else "loss" if own < other else "tie",
        "candidate_money": own, "opponent_money": other, "advantage": own - other,
        "runtime_error": runtime_error,
        "agent_error": any(status not in {"DONE", "Status.DONE"} for status in statuses),
        "semantic_failures": semantic_failures, "exceptions_by_seat": exceptions,
        "candidate_livestock_escapes": animal_escapes(env.steps, seat),
        "opponent_livestock_escapes": animal_escapes(env.steps, 1 - seat),
        "candidate_telemetry": deepcopy(getattr(candidate, "telemetry", {})),
    }


def summarize(rows):
    valid = [row for row in rows if row.get("outcome")]
    counts = Counter(row["outcome"] for row in valid)
    margins = [row["advantage"] for row in valid]
    return {
        "games": len(rows), "wins": counts["win"], "losses": counts["loss"], "ties": counts["tie"],
        "gsr": (counts["win"] + 0.5 * counts["tie"]) / len(valid) if valid else None,
        "mean_advantage": statistics.fmean(margins) if margins else None,
        "median_advantage": statistics.median(margins) if margins else None,
        "worst_advantage": min(margins) if margins else None,
        "mean_candidate_money": statistics.fmean(row["candidate_money"] for row in valid) if valid else None,
        "runtime_errors": sum(bool(row.get("runtime_error")) for row in rows),
        "agent_errors": sum(bool(row.get("agent_error")) for row in rows),
        "semantic_failures": sum(len(row.get("semantic_failures", [])) for row in rows),
        "candidate_livestock_escapes": sum(len(row.get("candidate_livestock_escapes", [])) for row in rows),
        "opponent_livestock_escapes": sum(len(row.get("opponent_livestock_escapes", [])) for row in rows),
        "shop_schedule_mismatches": sum(not row.get("shop_schedule_exact", False) for row in valid),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--candidate", type=Path, default=CANDIDATE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    candidate_path = args.candidate.resolve()
    sources = replay_schedules()
    frozen_before = frozen_identity()
    identity_before = candidate_identity(candidate_path)
    jobs = [
        (source, opponent, seat, candidate_path)
        for source in sources for opponent in OPPONENTS for seat in (0, 1)
    ]
    rows = []
    started = time.time()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_game, job) for job in jobs]
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            print(
                f"{len(rows)}/{len(jobs)} ep={row['source_episode_id']} {row['opponent']} "
                f"s{row['candidate_seat']} {row.get('outcome', 'ERROR')}", flush=True,
            )
    rows.sort(key=lambda row: (row["source_episode_id"], row["opponent"], row["candidate_seat"]))
    frozen_after = frozen_identity()
    identity_after = candidate_identity(candidate_path)
    artifact = {
        "schema_version": 1,
        "purpose": "locked candidate on exact fixed shop schedules from current top-five replays",
        "local_only": True, "kaggle_submission_made": False,
        "source_note": "Shop schedules are exact; local farm/weed trajectories are not replay clones.",
        "candidate_identity_before": identity_before, "candidate_identity_after": identity_after,
        "candidate_unchanged": identity_before == identity_after,
        "frozen_before": frozen_before, "frozen_after": frozen_after,
        "frozen_unchanged": frozen_before == frozen_after,
        "source_schedules": sources, "both_seats": True,
        "opponents": {name: str(path) for name, path in OPPONENTS.items()},
        "summary": {
            "overall": summarize(rows),
            "by_opponent": {
                name: summarize([row for row in rows if row["opponent"] == name])
                for name in OPPONENTS
            },
            "by_source_episode": {
                str(source["episode_id"]): summarize([
                    row for row in rows if row["source_episode_id"] == source["episode_id"]
                ])
                for source in sources
            },
        },
        "rows": rows, "elapsed_seconds": time.time() - started,
    }
    args.output.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(artifact["summary"], indent=2, ensure_ascii=False))
    print(args.output)


if __name__ == "__main__":
    main()
