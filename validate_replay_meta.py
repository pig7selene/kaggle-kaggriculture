"""Held-out hard-league validation for replay-inspired policy ablations."""

from __future__ import annotations

import argparse
import json
import statistics
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from kaggle_environments import make

from benchmark import DEFAULT_WORKERS, ROOT, _file_sha256, _load_agent
from test_economic_agents import _validate_action


EPISODE_STEPS = 720
VALUABLE = {
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
    "EGG", "MILK", "WOOL", "FERTILIZER",
}
CANDIDATES = {
    "current_best": ROOT / "agents" / "animal_c8_day12_land_day11.py",
    "third_quadrant": ROOT / "agents" / "replay_meta_third_quadrant.py",
    "replay_land_labor": ROOT / "agents" / "replay_meta_land_labor.py",
    "replay_full_schedule": ROOT / "agents" / "replay_meta_full_schedule.py",
}


def _fib(index):
    a, b = 1, 1
    for _ in range(index):
        a, b = b, a + b
    return a


def _productive_tiles(farm):
    return sum(
        isinstance(tile, dict)
        and (tile.get("kind") == "PLANT" or tile.get("animal") is not None)
        for row in farm["tiles"]
        for tile in row
    )


def _cow_count(farm):
    return sum(
        isinstance(tile, dict) and tile.get("animal") == "COW"
        for row in farm["tiles"]
        for tile in row
    )


def _stranded(state, seat):
    private = state.observation["private"]
    total = sum(private["shed"].get(item, 0) for item in VALUABLE)
    total += sum(
        inventory.get(item, 0)
        for inventory in private["inventories"]
        for item in VALUABLE
    )
    farm = state.observation["farms"][seat]
    total += sum(
        tile.get("yield_units", 0)
        for row in farm["tiles"]
        for tile in row
        if isinstance(tile, dict) and tile.get("animal") is not None
    )
    return total


def _run_game(job):
    candidate_name, candidate_path, opponent_name, opponent_path, seed, seat = job
    base = _load_agent(candidate_path)
    opponent = _load_agent(opponent_path)
    productive = []
    hands = []
    land_days = []
    attempted_land_days = []
    observed_quadrants = 1
    labor_cost = 0
    peak_cows = 0
    escaped_cows = 0

    def checked(obs):
        nonlocal labor_cost, peak_cows, escaped_cows, observed_quadrants
        action = base(obs)
        _validate_action(obs, action)
        me = obs["farms"][obs["player"]]
        quadrants = len(me["unlocked_quadrants"])
        if quadrants > observed_quadrants:
            land_days.extend([obs["day"]] * (quadrants - observed_quadrants))
            observed_quadrants = quadrants
        cows = _cow_count(me)
        if cows < peak_cows:
            escaped_cows = max(escaped_cows, peak_cows - cows)
        peak_cows = max(peak_cows, cows)
        if obs["hour"] == 23:
            productive.append(_productive_tiles(me))
            hands.append(len(me["hands"]))
        next_hire = int(me.get("hires_today", 0))
        for order in action["market"]:
            if order[0] == "HIRE":
                labor_cost += _fib(next_hire)
                next_hire += 1
            elif order[0] == "BUY_LAND":
                attempted_land_days.append(obs["day"])
        return action

    agents = [opponent, opponent]
    agents[seat] = checked
    env = make(
        "kaggriculture",
        configuration={"episodeSteps": EPISODE_STEPS, "seed": int(seed)},
        debug=True,
    )
    env.run(agents)
    final = env.steps[-1]
    statuses = [state.status for state in final]
    if len(env.steps) != EPISODE_STEPS or statuses != ["DONE", "DONE"]:
        raise RuntimeError(
            f"failed {candidate_name} vs {opponent_name} seed={seed} seat={seat}: "
            f"turns={len(env.steps)} statuses={statuses}"
        )
    final_cows = _cow_count(final[seat].observation["farms"][seat])
    escaped_cows = max(escaped_cows, peak_cows - final_cows)
    money = float(final[seat].reward)
    opponent_money = float(final[1 - seat].reward)
    return {
        "candidate": candidate_name,
        "opponent": opponent_name,
        "seed": seed,
        "seat": seat,
        "money": money,
        "opponent_money": opponent_money,
        "advantage": money - opponent_money,
        "average_productive_tiles": statistics.fmean(productive),
        "average_hands": statistics.fmean(hands),
        "labor_cost": labor_cost,
        "land_days": land_days,
        "attempted_land_days": attempted_land_days,
        "peak_cows": peak_cows,
        "escaped_cows": escaped_cows,
        "stranded_units": _stranded(final[seat], seat),
    }


def _percentile(values, fraction):
    ordered = sorted(values)
    index = fraction * (len(ordered) - 1)
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _summary(games):
    advantages = [game["advantage"] for game in games]
    wins = sum(value > 0 for value in advantages)
    losses = sum(value < 0 for value in advantages)
    seed_advantages = {}
    for game in games:
        seed_advantages.setdefault(game["seed"], []).append(game["advantage"])
    land_by_index = {}
    for game in games:
        for index, day in enumerate(game["land_days"], 1):
            land_by_index.setdefault(str(index), []).append(day)
    return {
        "games": len(games),
        "wins": wins,
        "losses": losses,
        "ties": len(games) - wins - losses,
        "win_rate": wins / len(games),
        "score_rate": (wins + 0.5 * (len(games) - wins - losses)) / len(games),
        "average_money": statistics.fmean(game["money"] for game in games),
        "average_opponent_money": statistics.fmean(game["opponent_money"] for game in games),
        "average_advantage": statistics.fmean(advantages),
        "median_advantage": statistics.median(advantages),
        "p10_seed_advantage": _percentile(
            [statistics.fmean(values) for values in seed_advantages.values()], 0.10
        ),
        "advantage_variance": statistics.pvariance(advantages),
        "average_productive_tiles": statistics.fmean(
            game["average_productive_tiles"] for game in games
        ),
        "average_hands": statistics.fmean(game["average_hands"] for game in games),
        "average_labor_cost": statistics.fmean(game["labor_cost"] for game in games),
        "average_land_purchases": statistics.fmean(len(game["land_days"]) for game in games),
        "average_land_day_by_purchase": {
            index: statistics.fmean(days) for index, days in land_by_index.items()
        },
        "average_peak_cows": statistics.fmean(game["peak_cows"] for game in games),
        "max_escaped_cows": max(game["escaped_cows"] for game in games),
        "max_stranded_units": max(game["stranded_units"] for game in games),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--seed-start", type=int, default=12600)
    parser.add_argument("--seeds", type=int, default=8)
    args = parser.parse_args()

    league = json.loads((ROOT / "experiments" / "3h_policy_league.json").read_text())
    opponents = {
        name: str((ROOT / relative).resolve())
        for name, relative in league["retained_adversaries"].items()
    }
    candidate_paths = {name: str(path.resolve()) for name, path in CANDIDATES.items()}
    seeds = list(range(args.seed_start, args.seed_start + args.seeds))
    jobs = [
        (candidate, path, opponent, opponent_path, seed, seat)
        for candidate, path in candidate_paths.items()
        for opponent, opponent_path in opponents.items()
        for seed in seeds
        for seat in (0, 1)
    ]
    games = []
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(_run_game, job) for job in jobs]
        for index, future in enumerate(as_completed(futures), 1):
            games.append(future.result())
            if index % 100 == 0 or index == len(jobs):
                print(f"replay-meta heldout: {index}/{len(jobs)}", flush=True)

    candidates = []
    for name, path in candidate_paths.items():
        selected = [game for game in games if game["candidate"] == name]
        matchups = {
            opponent: _summary([game for game in selected if game["opponent"] == opponent])
            for opponent in opponents
        }
        worst = min(
            matchups,
            key=lambda opponent: (
                matchups[opponent]["score_rate"],
                matchups[opponent]["average_advantage"],
            ),
        )
        candidates.append({
            "candidate": name,
            "path": str(Path(path).relative_to(ROOT)),
            "sha256": _file_sha256(Path(path)),
            "overall": _summary(selected),
            "worst_opponent": worst,
            "matchups": matchups,
        })
    candidates.sort(
        key=lambda row: (
            row["overall"]["score_rate"], row["overall"]["average_advantage"]
        ),
        reverse=True,
    )
    payload = {
        "schema_version": 1,
        "experiment": "top_player_replay_meta_heldout_validation",
        "seed_partition": "fresh held-out; disjoint from prior 11000-11311 searches",
        "seeds": seeds,
        "both_seats": True,
        "opponents": opponents,
        "games_per_candidate": len(opponents) * len(seeds) * 2,
        "candidates": candidates,
        "games": games,
    }
    output = ROOT / "experiments" / "top_player_replay_local_validation.json"
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(output)
    for row in candidates:
        overall = row["overall"]
        print(
            row["candidate"],
            f"{overall['wins']}/{overall['losses']}/{overall['ties']}",
            f"score={overall['score_rate']:.3f}",
            f"money={overall['average_money']:.1f}",
            f"adv={overall['average_advantage']:.1f}",
            f"p10={overall['p10_seed_advantage']:.1f}",
            f"worst={row['worst_opponent']}",
        )


if __name__ == "__main__":
    main()
