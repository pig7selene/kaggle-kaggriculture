"""Causal screen of the 0911 non-Yarn routes on V233H online losses."""

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
from run_smaller_v233h_fixed_icecream_probe import fixed_schedule


ROOT = Path(__file__).resolve().parent
# Authoritative source is the in-repo manifest distilled by
# build_replay_seed_manifests.py.  REPLAYS is the original corpus; when it still
# exists the manifest is verified against it, otherwise it is simply unused.
SEED_MANIFEST = ROOT / "experiments" / "v233h_online_replay_seed_manifest.json"
REPLAYS = Path("/private/tmp/kaggriculture_v233h_online")
ONLINE = ROOT / "experiments" / "smaller_v233h_online_submission.json"
CANDIDATE = ROOT / "agents" / "smaller_market_shock_v233h_non_yarn_0911" / "main.py"
BASELINE = ROOT / "agents" / "smaller_market_shock_v233h_safe" / "main.py"
OUTPUT = ROOT / "experiments" / "smaller_v233h_non_yarn_0911_screen.json"
BUILD_RECEIPT = ROOT / "experiments" / "smaller_v233h_non_yarn_0911_build.json"


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def episode_seeds():
    """Read the manifest, and verify it whenever the original corpus is present."""
    if not SEED_MANIFEST.is_file():
        raise RuntimeError(
            f"{SEED_MANIFEST} is missing; regenerate it with build_replay_seed_manifests.py"
        )
    seeds = {
        int(row["episode_id"]): int(row["seed"])
        for row in json.loads(SEED_MANIFEST.read_text())["seeds"]
    }
    if REPLAYS.is_dir():
        for path in sorted(REPLAYS.glob("episode-*-replay.json")):
            info = json.loads(path.read_text())["info"]
            episode_id = int(info["EpisodeId"])
            if seeds.get(episode_id) != int(info["seed"]):
                raise RuntimeError(
                    f"seed manifest disagrees with the original replay corpus at {episode_id}"
                )
    return seeds


def sources(scope="losses"):
    online = json.loads(ONLINE.read_text())
    receipt = json.loads(BUILD_RECEIPT.read_text())
    enabled_pairs = {
        tuple(pair) for pair in receipt["added_non_yarn_pairs"]
    }
    seeds = episode_seeds()
    selected = online["summary"]["losses"] if scope == "losses" else online["games"]
    rows = []
    for game in selected:
        episode_id = int(game["episode_id"])
        if episode_id not in seeds:
            raise RuntimeError(f"no recorded seed for episode {episode_id}")
        rows.append({
            "episode_id": episode_id,
            "seed": seeds[episode_id],
            "shops": list(game["shops"]),
            "online_opponent": game["opponent"],
            "online_margin": float(game["margin"]),
            "online_outcome": game["outcome"],
            "route_changed": tuple(game["shops"][:2]) in enabled_pairs,
        })
    return rows


def run_game(job):
    source, candidate_seat = job
    candidate = load_agent(
        CANDIDATE, f"non_yarn_candidate_{source['episode_id']}_{candidate_seat}"
    )
    baseline = load_agent(
        BASELINE, f"non_yarn_baseline_{source['episode_id']}_{candidate_seat}"
    )
    semantic_failures = []
    exceptions = [[], []]

    def checked(agent, seat, validate=False):
        def wrapper(obs, configuration=None):
            try:
                action = call(agent, obs, configuration)
                if validate:
                    try:
                        semantic_check(obs, action)
                    except Exception as exc:
                        semantic_failures.append({
                            "step": int(obs.get("step", -1)), "error": repr(exc)
                        })
                return action
            except Exception as exc:
                exceptions[seat].append({
                    "step": int(obs.get("step", -1)), "error": repr(exc)
                })
                raise
        return wrapper

    players = [None, None]
    players[candidate_seat] = checked(candidate, candidate_seat, validate=True)
    players[1 - candidate_seat] = checked(baseline, 1 - candidate_seat)
    env = make(
        "kaggriculture",
        configuration={"episodeSteps": 720, "seed": source["seed"]},
        debug=False,
    )
    runtime_error = None
    try:
        _run_with_fixed_shops(env, players, fixed_schedule(source["shops"]))
    except Exception as exc:
        runtime_error = repr(exc)
    if len(getattr(env, "steps", [])) != 720:
        return {
            **source,
            "candidate_seat": candidate_seat,
            "runtime_error": runtime_error or "incomplete",
            "agent_error": True,
            "semantic_failures": semantic_failures,
            "exceptions_by_seat": exceptions,
        }
    final = env.steps[-1]
    own = float(final[candidate_seat].reward)
    other = float(final[1 - candidate_seat].reward)
    statuses = [str(final[index].status) for index in range(2)]
    realized = list(final[candidate_seat].observation["town"]["unlocked_shops"])
    return {
        **source,
        "candidate_seat": candidate_seat,
        "realized_shops": realized,
        "shop_schedule_exact": realized == source["shops"],
        "outcome": "win" if own > other else "loss" if own < other else "tie",
        "candidate_money": own,
        "baseline_money": other,
        "advantage": own - other,
        "runtime_error": runtime_error,
        "agent_error": (
            any(status not in {"DONE", "Status.DONE"} for status in statuses)
            or any(exceptions)
        ),
        "semantic_failures": semantic_failures,
        "exceptions_by_seat": exceptions,
        "candidate_livestock_escapes": animal_escapes(env.steps, candidate_seat),
        "baseline_livestock_escapes": animal_escapes(env.steps, 1 - candidate_seat),
        "candidate_telemetry": deepcopy(getattr(candidate, "telemetry", {})),
    }


def summarize(rows):
    valid = [row for row in rows if row.get("outcome")]
    counts = Counter(row["outcome"] for row in valid)
    margins = [row["advantage"] for row in valid]
    return {
        "games": len(rows),
        "wins": counts["win"],
        "losses": counts["loss"],
        "ties": counts["tie"],
        "gsr": (counts["win"] + 0.5 * counts["tie"]) / len(valid) if valid else None,
        "mean_advantage": statistics.fmean(margins) if margins else None,
        "median_advantage": statistics.median(margins) if margins else None,
        "worst_advantage": min(margins) if margins else None,
        "mean_candidate_money": statistics.fmean(
            row["candidate_money"] for row in valid
        ) if valid else None,
        "runtime_errors": sum(bool(row.get("runtime_error")) for row in rows),
        "agent_errors": sum(bool(row.get("agent_error")) for row in rows),
        "semantic_failures": sum(len(row.get("semantic_failures", [])) for row in rows),
        "agent_exceptions": sum(
            len(errors) for row in rows for errors in row.get("exceptions_by_seat", [])
        ),
        "candidate_livestock_escapes": sum(
            len(row.get("candidate_livestock_escapes", [])) for row in rows
        ),
        "baseline_livestock_escapes": sum(
            len(row.get("baseline_livestock_escapes", [])) for row in rows
        ),
        "shop_schedule_mismatches": sum(
            not row.get("shop_schedule_exact", False) for row in valid
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--scope", choices=("losses", "all"), default="losses")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    source_rows = sources(args.scope)
    frozen_before = frozen_identity()
    identities_before = {
        "candidate_main": _sha(CANDIDATE),
        "candidate_router": _sha(CANDIDATE.parent / "router.py"),
        "candidate_actions": _sha(CANDIDATE.parent / "actions.json"),
        "baseline_main": _sha(BASELINE),
        "baseline_router": _sha(BASELINE.parent / "router.py"),
        "baseline_actions": _sha(BASELINE.parent / "actions.json"),
    }
    jobs = [(source, seat) for source in source_rows for seat in (0, 1)]
    rows = []
    started = time.time()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_game, job) for job in jobs]
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            print(
                f"{len(rows)}/{len(jobs)} ep={row['episode_id']} "
                f"seat={row['candidate_seat']} {row.get('outcome', 'ERROR')}",
                flush=True,
            )
    rows.sort(key=lambda row: (row["episode_id"], row["candidate_seat"]))
    frozen_after = frozen_identity()
    identities_after = {
        "candidate_main": _sha(CANDIDATE),
        "candidate_router": _sha(CANDIDATE.parent / "router.py"),
        "candidate_actions": _sha(CANDIDATE.parent / "actions.json"),
        "baseline_main": _sha(BASELINE),
        "baseline_router": _sha(BASELINE.parent / "router.py"),
        "baseline_actions": _sha(BASELINE.parent / "actions.json"),
    }
    changed = [row for row in rows if row["route_changed"]]
    controls = [row for row in rows if not row["route_changed"]]
    pair_names = sorted({tuple(row["shops"][:2]) for row in rows})
    by_episode = {
        str(source["episode_id"]): summarize([
            row for row in rows if row["episode_id"] == source["episode_id"]
        ])
        for source in source_rows
    }
    artifact = {
        "schema_version": 1,
        "purpose": f"causal 0911 non-Yarn suffix screen on V233H online {args.scope} schedules",
        "scope": args.scope,
        "local_only": True,
        "kaggle_submission_made": False,
        "candidate": str(CANDIDATE.relative_to(ROOT)),
        "baseline": str(BASELINE.relative_to(ROOT)),
        "source_online_submission": 56183575,
        "source_schedules": source_rows,
        "identities_before": identities_before,
        "identities_after": identities_after,
        "candidate_and_baseline_unchanged": identities_before == identities_after,
        "frozen_before": frozen_before,
        "frozen_after": frozen_after,
        "frozen_unchanged": frozen_before == frozen_after,
        "summary": {
            "overall": summarize(rows),
            "changed_non_yarn_routes": summarize(changed),
            "unchanged_yarn_controls": summarize(controls),
            "by_first_two_shops": {
                " + ".join(pair): summarize([
                    row for row in rows if tuple(row["shops"][:2]) == pair
                ])
                for pair in pair_names
            },
            "by_episode": by_episode,
        },
        "rows": rows,
        "elapsed_seconds": time.time() - started,
    }
    args.output.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(artifact["summary"], indent=2, ensure_ascii=False))
    print(args.output)


if __name__ == "__main__":
    main()
