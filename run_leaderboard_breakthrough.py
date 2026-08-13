"""Replay-weighted validation for leaderboard economic mechanisms."""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from run_epic_experiments import (
    CANDIDATES, ROOT, _candidate_rows, _independent_shop_schedule,
    _recorded_shop_schedule, _run,
)


REPLAY_CASES = {
    "Jayveer_melon_burst": (92008833, "experiments/leaderboard_replays/submission_55435253/replays/episode-92008833-replay.json", 0),
    "Pedro_wheat_turnover": (92010768, "experiments/leaderboard_replays/submission_55435253/replays/episode-92010768-replay.json", 1),
    "Lucas_four_quadrant": (92009080, "experiments/leaderboard_replays/submission_55435253/replays/episode-92009080-replay.json", 1),
    "Alexander_cow_melon": (92011750, "experiments/leaderboard_replays/submission_55435253/replays/episode-92011750-replay.json", 0),
    "Teddy_top_template": (92092507, "experiments/leaderboard_replays/submission_55435253/replays/episode-92092507-replay.json", 1),
    "Sagar_top_template": (92180626, "experiments/leaderboard_replays/submission_55438811/replays/episode-92180626-replay.json", 1),
    "Victor_top_template": (91869963, "experiments/top_player_replays/replays/episode-91869963-replay.json", 0),
    "Hak_top_template": (91853240, "experiments/top_player_replays/replays/episode-91853240-replay.json", 1),
}

HELDOUT_REPLAY_CASES = {
    "Prashant_crop_scaler": (92015550, "experiments/leaderboard_replays/submission_55435253/replays/episode-92015550-replay.json", 1),
    "David_four_quadrant": (92018382, "experiments/leaderboard_replays/submission_55435253/replays/episode-92018382-replay.json", 0),
    "Okome_strawberry_sheep": (92024051, "experiments/leaderboard_replays/submission_55435253/replays/episode-92024051-replay.json", 0),
    "Ayuma_crop_livestock": (92031656, "experiments/leaderboard_replays/submission_55435253/replays/episode-92031656-replay.json", 0),
    "Filip_top_template": (92075718, "experiments/leaderboard_replays/submission_55438811/replays/episode-92075718-replay.json", 1),
    "Amer_high_scale": (92057764, "experiments/leaderboard_replays/submission_55438811/replays/episode-92057764-replay.json", 1),
    "Yankang_wheat_close": (92177850, "experiments/leaderboard_replays/submission_55435253/replays/episode-92177850-replay.json", 0),
    "Garigariyong_strawberry": (92180707, "experiments/leaderboard_replays/submission_55438811/replays/episode-92180707-replay.json", 1),
}

RED_TEAM = {
    "melon_pressure": "agents/proxies/melon_heavy.py",
    "livestock_pressure": "agents/proxies/livestock_crop.py",
    "wheat_turnover_pressure": "agents/adversaries/epic_pedro_demand_trader.py",
    "crop_capital_pressure": "agents/adversaries/epic_jay_capital_wave.py",
}


def _trace_spec(path, player):
    return f"trace:{ROOT / path}:{player}"


def _source(path):
    return json.loads((ROOT / path).read_text())


def _validate_trace_proxies(cases):
    rows = []
    for name, (episode, path, player) in cases.items():
        replay = _source(path)
        mismatches = []
        from run_post_opening_validation import _load_opponent
        proxy = _load_opponent(_trace_spec(path, player))
        for step in range(719):
            obs = json.loads(json.dumps(replay["steps"][step][0]["observation"]))
            obs["player"] = player
            private = replay["steps"][step][player].get("observation", {}).get("private")
            if private is not None:
                obs["private"] = json.loads(json.dumps(private))
            requested = proxy(obs)
            expected = replay["steps"][step + 1][player].get("action") or {}
            normalized = {
                "farmer": expected.get("farmer", ["PASS"]),
                "hands": list(expected.get("hands", []))[:len(obs["farms"][player].get("hands", []))],
                "market": expected.get("market", []),
            }
            if requested != normalized:
                mismatches.append(step)
        rows.append({
            "archetype": name, "episode_id": episode, "source_player": player,
            "source_team": replay["info"]["TeamNames"][player],
            "actions_compared": 719, "action_mismatches": len(mismatches),
            "source_final_money": float(replay["steps"][-1][player]["reward"]),
        })
    return rows


def _jobs(candidates, seed_start, seed_count, heldout=False):
    jobs = []
    replay_cases = HELDOUT_REPLAY_CASES if heldout else REPLAY_CASES
    for candidate in candidates:
        path = CANDIDATES[candidate]
        for opponent, (_, replay_path, player) in replay_cases.items():
            replay = _source(replay_path)
            seed = int(replay["info"]["seed"])
            schedule = _recorded_shop_schedule(replay)
            for seat in (0, 1):
                jobs.append((candidate, path, "real_replay", opponent, _trace_spec(replay_path, player), seed, seat, schedule))
        for seed in range(seed_start, seed_start + seed_count):
            for seat in (0, 1):
                jobs.append((candidate, path, "direct_fixed", "R0_803_fixed", CANDIDATES["R0_803"], seed, seat, _independent_shop_schedule(seed)))
                jobs.append((candidate, path, "direct_natural", "R0_803_natural", CANDIDATES["R0_803"], seed, seat, None))
        # Historical programmable opponents are deliberately low weight and
        # serve only as mechanism-specific red teams.
        red_seeds = range(seed_start + 100, seed_start + 100 + (3 if heldout else 1))
        for opponent, spec in RED_TEAM.items():
            for seed in red_seeds:
                for seat in (0, 1):
                    jobs.append((candidate, path, "red_team", opponent, spec, seed, seat, _independent_shop_schedule(seed)))
    return jobs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", default="R0_803,L798,R2_capital,R3_c6_capital,R4_capital_value")
    parser.add_argument("--seed-start", type=int, default=961000)
    parser.add_argument("--seed-count", type=int, default=3)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--heldout", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    candidates = tuple(value for value in args.candidates.split(",") if value)
    jobs = _jobs(candidates, args.seed_start, args.seed_count, args.heldout)
    games = []
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(_run, job) for job in jobs]
        for index, future in enumerate(as_completed(futures), 1):
            games.append(future.result())
            if index % 40 == 0 or index == len(jobs):
                print(f"games {index}/{len(jobs)}", flush=True)
    payload = {
        "schema_version": 1,
        "stage": "heldout" if args.heldout else "selection",
        "seed_partition": {"start": args.seed_start, "count": args.seed_count},
        "trace_proxy_validation": _validate_trace_proxies(
            HELDOUT_REPLAY_CASES if args.heldout else REPLAY_CASES
        ),
        "candidates": _candidate_rows(games, candidates),
        "games": games,
    }
    output = Path(args.output)
    output.write_text(json.dumps(payload, indent=2) + "\n")
    for row in payload["candidates"]:
        s = row["overall"]
        print(row["candidate"], f"{s['wins']}/{s['losses']}/{s['ties']}", f"money={s['average_money']:.0f}", f"adv={s['average_advantage']:+.0f}", f"P10={s['p10_paired_advantage']:+.0f}")


if __name__ == "__main__":
    main()
