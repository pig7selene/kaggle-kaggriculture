"""Small isolated validation for the day-29 animal-harvest cutoff ablation."""

import json
import statistics
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from kaggle_environments import make

from analyze_top_player_replays import _transition_ledger
from benchmark import EPISODE_STEPS, ROOT, _load_agent
from test_economic_agents import _validate_action


SOURCE = ROOT / "agents" / "router_replay_hands12.py"
FIX = ROOT / "agents" / "router_replay_endgame_fix.py"
OUTPUT = ROOT / "experiments" / "opponent_endgame_bugfix_ablation.json"
SEEDS = tuple(range(16000, 16008))


def _run(job):
    label, candidate_path, seed, seat = job
    candidate = _load_agent(candidate_path)
    opponent = _load_agent(str(SOURCE))
    agents = [opponent, opponent]
    agents[seat] = candidate
    env = make(
        "kaggriculture",
        configuration={"episodeSteps": EPISODE_STEPS, "seed": seed},
        debug=True,
    )
    env.run(agents)
    if len(env.steps) != 720 or [row.status for row in env.steps[-1]] != ["DONE", "DONE"]:
        raise RuntimeError(f"failed {label}, seed={seed}, seat={seat}")
    invalid = 0
    cows_bought = 0
    for index in range(1, len(env.steps)):
        obs = env.steps[index - 1][seat]["observation"]
        action = env.steps[index][seat].get("action") or {}
        try:
            _validate_action(obs, action)
        except AssertionError:
            invalid += 1
        ledgers, mismatches = _transition_ledger(
            env.steps[index - 1], env.steps[index], dict(env.configuration)
        )
        if mismatches:
            raise RuntimeError(mismatches)
        cows_bought += ledgers[seat]["animal_quantity"]["COW"]
    final = env.steps[-1][seat]["observation"]
    farm = final["farms"][seat]
    private = final["private"]
    placed_cows = sum(
        isinstance(tile, dict) and tile.get("animal") == "COW"
        for row in farm["tiles"] for tile in row
    )
    owned_cows = (
        placed_cows
        + private["shed"].get("COW", 0)
        + sum(inventory.get("COW", 0) for inventory in private["inventories"])
    )
    milk = private["shed"].get("MILK", 0)
    milk += sum(inventory.get("MILK", 0) for inventory in private["inventories"])
    milk += sum(
        int(tile.get("yield_units", 0))
        for row in farm["tiles"] for tile in row
        if isinstance(tile, dict) and tile.get("animal") == "COW"
    )
    return {
        "label": label,
        "seed": seed,
        "seat": seat,
        "money": float(env.steps[-1][seat].reward),
        "opponent_money": float(env.steps[-1][1 - seat].reward),
        "advantage": float(env.steps[-1][seat].reward - env.steps[-1][1 - seat].reward),
        "invalid_actions": invalid,
        "cows_bought": cows_bought,
        "final_cows_owned": owned_cows,
        "cow_losses_or_replacements": max(0, cows_bought - owned_cows),
        "stranded_milk": milk,
    }


def main():
    jobs = [
        (label, str(path), seed, seat)
        for label, path in (("source", SOURCE), ("endgame_fix", FIX))
        for seed in SEEDS for seat in (0, 1)
    ]
    games = []
    with ProcessPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(_run, job) for job in jobs]
        for index, future in enumerate(as_completed(futures), 1):
            games.append(future.result())
            if index % 8 == 0:
                print(f"completed {index}/{len(jobs)}", flush=True)
    games.sort(key=lambda row: (row["label"], row["seed"], row["seat"]))
    summaries = {}
    for label in ("source", "endgame_fix"):
        rows = [row for row in games if row["label"] == label]
        summaries[label] = {
            "games": len(rows),
            "average_money": statistics.fmean(row["money"] for row in rows),
            "average_advantage": statistics.fmean(row["advantage"] for row in rows),
            "total_invalid_actions": sum(row["invalid_actions"] for row in rows),
            "total_stranded_milk": sum(row["stranded_milk"] for row in rows),
            "max_stranded_milk": max(row["stranded_milk"] for row in rows),
            "total_cow_losses_or_replacements": sum(row["cow_losses_or_replacements"] for row in rows),
            "max_cow_losses_or_replacements": max(row["cow_losses_or_replacements"] for row in rows),
        }
    source_by_key = {(row["seed"], row["seat"]): row for row in games if row["label"] == "source"}
    deltas = [
        row["money"] - source_by_key[(row["seed"], row["seat"])]["money"]
        for row in games if row["label"] == "endgame_fix"
    ]
    result = {
        "schema_version": 1,
        "experiment": "isolated_endgame_milk_fix",
        "seeds": list(SEEDS),
        "both_seats": True,
        "source": str(SOURCE.relative_to(ROOT)),
        "candidate": str(FIX.relative_to(ROOT)),
        "summaries": summaries,
        "paired_average_money_delta": statistics.fmean(deltas),
        "paired_money_delta_range": [min(deltas), max(deltas)],
        "games": games,
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"summaries": summaries, "paired_average_money_delta": result["paired_average_money_delta"]}, indent=2))
    print(f"Saved {OUTPUT}")


if __name__ == "__main__":
    main()
