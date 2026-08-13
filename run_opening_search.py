"""Cheap deterministic day-10 screen for replay-derived opening controls."""

from __future__ import annotations

import argparse
import json
import os
import statistics
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from runpy import run_path

from kaggle_environments import make


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "experiments" / "opening_day10_screen.json"
MARKDOWN = ROOT / "experiments" / "opening_day10_screen.md"
EPISODE_STEPS = 288
SEEDS = (14200, 14201, 14202, 14203)
CANDIDATES = {
    "frozen_current": "agents/router_replay_hands12.py",
    "public_template": "agents/opening_public_hybrid_land_first.py",
    "public_no_land_priority": "agents/opening_public_hybrid_feed.py",
    "public_daily_feed": "agents/opening_public_daily_feed.py",
    "public_survival_feed": "agents/opening_public_template.py",
    "public_two_day_feed": "agents/opening_public_two_day_feed.py",
    "wheat4_melon6": "agents/opening_public_wheat4_melon6.py",
    "wheat6_melon4": "agents/opening_public_wheat6_melon4.py",
    "cow1_ramp": "agents/opening_cow1_ramp.py",
    "cow5_ramp": "agents/opening_cow5_ramp.py",
    "wool_delay_day7": "agents/opening_public_wool_delay.py",
    "fertilizer_delay_day3": "agents/opening_public_fertilizer_delay.py",
    "lean_day0_hires": "agents/opening_public_lean_hires.py",
    "front_day0_hires": "agents/opening_public_front_hires.py",
    "early_wheat_age2": "agents/opening_public_early_wheat.py",
}
OPPONENTS = {
    "frozen_current": "agents/router_replay_hands12.py",
    "public_template": "agents/opening_public_hybrid_land_first.py",
    "early_cow_proxy": "agents/adversaries/gen_cow6_d8.py",
}
_CACHE = {}


def _agent(path):
    if path not in _CACHE:
        _CACHE[path] = run_path(path)["agent"]
    return _CACHE[path]


def _farm_metrics(farm):
    crops = 0
    animals = {"COW": 0, "SHEEP": 0, "GOOSE": 0}
    productive = 0
    for row in farm["tiles"]:
        for tile in row:
            if not isinstance(tile, dict):
                continue
            if tile.get("kind") == "PLANT":
                crops += 1
                productive += 1
            if tile.get("animal"):
                animals[tile["animal"]] += 1
                productive += 1
    return {
        "money": float(farm["money"]),
        "productive_tiles": productive,
        "crop_tiles": crops,
        "animals": animals,
        "quadrants": len(farm["unlocked_quadrants"]),
    }


def _run(job):
    candidate_name, candidate_path, opponent_name, opponent_path, seed, seat = job
    agents = [_agent(opponent_path), _agent(opponent_path)]
    agents[seat] = _agent(candidate_path)
    env = make(
        "kaggriculture",
        configuration={"episodeSteps": EPISODE_STEPS, "seed": seed},
        debug=True,
    )
    env.run(agents)
    statuses = [state.status for state in env.steps[-1]]
    if len(env.steps) != EPISODE_STEPS or statuses != ["DONE", "DONE"]:
        raise RuntimeError(
            f"opening failure {candidate_name}/{opponent_name}/{seed}/seat{seat}: "
            f"steps={len(env.steps)} statuses={statuses}"
        )
    checkpoints = {}
    max_hands = {day: 0 for day in range(11)}
    escaped = 0
    previous_animals = 0
    first_land = None
    second_land = None
    previous_quadrants = 1
    for states in env.steps:
        obs = states[seat]["observation"]
        day = int(obs["day"])
        farm = obs["farms"][seat]
        if day <= 10:
            max_hands[day] = max(max_hands[day], len(farm.get("hands", [])))
        metrics = _farm_metrics(farm)
        animal_count = sum(metrics["animals"].values())
        if animal_count < previous_animals:
            escaped += previous_animals - animal_count
        previous_animals = animal_count
        if metrics["quadrants"] > previous_quadrants:
            if first_land is None:
                first_land = {"day": day, "hour": int(obs["hour"])}
            elif second_land is None:
                second_land = {"day": day, "hour": int(obs["hour"])}
            previous_quadrants = metrics["quadrants"]
        if day in {5, 7, 9, 11} and int(obs["hour"]) == 0:
            completed_day = day - 1
            checkpoints[str(completed_day)] = metrics
    for day in (4, 6, 8, 10):
        if str(day) not in checkpoints:
            raise RuntimeError(f"missing checkpoint day {day}")
        checkpoints[str(day)]["max_hands"] = max_hands[day]
    return {
        "candidate": candidate_name,
        "opponent": opponent_name,
        "seed": seed,
        "seat": seat,
        "checkpoints": checkpoints,
        "first_land": first_land,
        "second_land": second_land,
        "escaped_animals": escaped,
    }


def _mean(games, day, field):
    return statistics.fmean(game["checkpoints"][str(day)][field] for game in games)


def _summary(games, mixed):
    def rate(predicate):
        return sum(predicate(game) for game in games) / len(games)

    schedule_success = rate(
        lambda game: (
            game["checkpoints"]["6"]["quadrants"] >= 2
            and game["checkpoints"]["10"]["quadrants"] >= 3
            and game["checkpoints"]["8"]["animals"]["COW"] >= 8
            and (not mixed or game["checkpoints"]["8"]["animals"]["SHEEP"] >= 4)
            and game["escaped_animals"] == 0
        )
    )
    return {
        "games": len(games),
        "average_bank_after_day_4": _mean(games, 4, "money"),
        "average_bank_after_day_6": _mean(games, 6, "money"),
        "average_productive_tiles_after_day_6": _mean(games, 6, "productive_tiles"),
        "average_bank_after_day_8": _mean(games, 8, "money"),
        "average_cows_after_day_8": statistics.fmean(
            game["checkpoints"]["8"]["animals"]["COW"] for game in games
        ),
        "average_sheep_after_day_8": statistics.fmean(
            game["checkpoints"]["8"]["animals"]["SHEEP"] for game in games
        ),
        "average_bank_after_day_10": _mean(games, 10, "money"),
        "average_productive_tiles_after_day_10": _mean(games, 10, "productive_tiles"),
        "average_quadrants_after_day_10": _mean(games, 10, "quadrants"),
        "average_hands_day_10": _mean(games, 10, "max_hands"),
        "land_1_by_day_6_rate": rate(lambda game: game["checkpoints"]["6"]["quadrants"] >= 2),
        "eight_cows_by_day_8_rate": rate(
            lambda game: game["checkpoints"]["8"]["animals"]["COW"] >= 8
        ),
        "land_2_by_day_10_rate": rate(lambda game: game["checkpoints"]["10"]["quadrants"] >= 3),
        "zero_escape_rate": rate(lambda game: game["escaped_animals"] == 0),
        "schedule_success_rate": schedule_success,
        "total_escaped_animals": sum(game["escaped_animals"] for game in games),
    }


def _write_markdown(payload):
    lines = [
        "# Day-10 opening search",
        "",
        "Checkpoints are observed at hour 0 of the next day, after all actions and refresh for the named day. Results use fixed search seeds against the same three opening opponents in both seats.",
        "",
        "| Candidate | Games | Bank d4 | Bank d6 | Tiles d6 | Bank d8 | Cows/sheep d8 | Bank d10 | Q d10 | Hands d10 | Land6 | Cows8 | Land10 | No escape | Full template |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload["candidates"]:
        s = row["overall"]
        lines.append(
            f"| {row['candidate']} | {s['games']} | {s['average_bank_after_day_4']:.0f} | "
            f"{s['average_bank_after_day_6']:.0f} | {s['average_productive_tiles_after_day_6']:.1f} | "
            f"{s['average_bank_after_day_8']:.0f} | {s['average_cows_after_day_8']:.1f}/{s['average_sheep_after_day_8']:.1f} | "
            f"{s['average_bank_after_day_10']:.0f} | {s['average_quadrants_after_day_10']:.2f} | "
            f"{s['average_hands_day_10']:.1f} | {s['land_1_by_day_6_rate']:.0%} | "
            f"{s['eight_cows_by_day_8_rate']:.0%} | {s['land_2_by_day_10_rate']:.0%} | "
            f"{s['zero_escape_rate']:.0%} | {s['schedule_success_rate']:.0%} |"
        )
    MARKDOWN.write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=min(4, os.cpu_count() or 1))
    args = parser.parse_args()
    jobs = [
        (candidate, str((ROOT / path).resolve()), opponent, str((ROOT / opponent_path).resolve()), seed, seat)
        for candidate, path in CANDIDATES.items()
        for opponent, opponent_path in OPPONENTS.items()
        for seed in SEEDS
        for seat in (0, 1)
    ]
    games = []
    if args.workers <= 1:
        for index, job in enumerate(jobs, 1):
            games.append(_run(job))
            if index % 40 == 0 or index == len(jobs):
                print(f"opening screen {index}/{len(jobs)}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(_run, job) for job in jobs]
            for index, future in enumerate(as_completed(futures), 1):
                games.append(future.result())
                if index % 40 == 0 or index == len(futures):
                    print(f"opening screen {index}/{len(futures)}", flush=True)
    candidates = []
    for name, path in CANDIDATES.items():
        selected = [game for game in games if game["candidate"] == name]
        mixed = name not in {"frozen_current", "cow1_ramp", "cow5_ramp"}
        by_opponent = {
            opponent: _summary(
                [game for game in selected if game["opponent"] == opponent], mixed
            )
            for opponent in OPPONENTS
        }
        candidates.append(
            {
                "candidate": name,
                "path": path,
                "overall": _summary(selected, mixed),
                "by_opponent": by_opponent,
            }
        )
    candidates.sort(
        key=lambda row: (
            row["overall"]["schedule_success_rate"],
            row["overall"]["land_2_by_day_10_rate"],
            row["overall"]["average_bank_after_day_10"],
        ),
        reverse=True,
    )
    payload = {
        "schema_version": 1,
        "experiment": "opening_day10_controlled_screen",
        "episode_steps": EPISODE_STEPS,
        "seeds": list(SEEDS),
        "both_seats": True,
        "opponents": OPPONENTS,
        "candidates": candidates,
        "games": games,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n")
    _write_markdown(payload)
    print(OUTPUT)
    for row in candidates:
        s = row["overall"]
        print(
            row["candidate"],
            f"template={s['schedule_success_rate']:.1%}",
            f"land6={s['land_1_by_day_6_rate']:.1%}",
            f"cows8={s['eight_cows_by_day_8_rate']:.1%}",
            f"land10={s['land_2_by_day_10_rate']:.1%}",
            f"bank10={s['average_bank_after_day_10']:.0f}",
        )


if __name__ == "__main__":
    main()
