"""Cheap, resumable diagnostics for the next architectural hypothesis.

The script intentionally keeps the frozen Top-50 portfolio in the league.  It
compares complete-route alternatives with a state-driven crop executor on a
small unseen seed panel before any larger search is opened.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import statistics
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from runpy import run_path

from kaggle_environments import make


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "experiments" / "autonomous_breakthrough_diagnostics.json"
SELLABLE = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")

AGENTS = {
    "current_best": str(ROOT / "agents/top50_distilled/top50_observable_portfolio.py"),
    "family01_medoid": str(ROOT / "agents/autonomous_next/top50_family01_medoid.py"),
    "raw_55899537": str(ROOT / "agents/autonomous_next/top50_raw_55899537.py"),
    "goal_executor": str(ROOT / "agents/autonomous_next/goal_executor_v1.py"),
    "goal_executor_safe": str(ROOT / "agents/autonomous_next/goal_executor_safe_v1.py"),
}

OPPONENTS = {
    "current_best": AGENTS["current_best"],
    "livestock": str(ROOT / "agents/proxies/livestock_crop.py"),
    "land_expander": str(ROOT / "agents/proxies/land_expander.py"),
    "high_labor": str(ROOT / "agents/proxies/high_labor.py"),
    "phased_rotation": str(ROOT / "agents/proxies/phased_rotation.py"),
    "inventory_holder": str(ROOT / "agents/proxies/inventory_holder.py"),
    "mixed_crop": str(ROOT / "agents/proxies/mixed_crop.py"),
}


def _load(path):
    name = "autonomous_" + hashlib.sha256(str(path).encode()).hexdigest()[:12]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.agent


def _animal_count(farm):
    return sum(
        1
        for row in farm["tiles"]
        for tile in row
        if isinstance(tile, dict) and tile.get("animal")
    )


def _stranded_value(observation):
    private = observation["private"]
    prices = observation.get("market", {}).get("prices", {})
    value = 0.0
    units = 0
    for item in SELLABLE:
        count = int(private.get("shed", {}).get(item, 0))
        count += sum(int(inv.get(item, 0)) for inv in private.get("inventories", []))
        units += count
        value += count * float(prices.get(item, 1))
    farm = observation["farms"][observation["player"]]
    for row in farm["tiles"]:
        for tile in row:
            if isinstance(tile, dict) and tile.get("animal"):
                count = int(tile.get("yield_units", 0))
                units += count
                product = {"COW": "MILK", "SHEEP": "WOOL", "GOOSE": "EGG"}.get(tile.get("animal"), "")
                value += count * float(prices.get(product, 1))
    return units, value


def _run(job):
    candidate_name, candidate_path, opponent_name, opponent_path, seed, seat = job
    candidate = _load(candidate_path)
    opponent = _load(opponent_path)
    pair = [opponent, opponent]
    pair[seat] = candidate
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": int(seed)}, debug=True)
    runtime_error = None
    try:
        env.run(pair)
    except Exception as exc:  # preserve a failed job for diagnosis
        runtime_error = repr(exc)
    if runtime_error or not env.steps:
        return {
            "candidate": candidate_name, "opponent": opponent_name, "seed": seed,
            "seat": seat, "runtime_error": runtime_error or "no_steps",
        }
    final = env.steps[-1]
    own = final[seat]
    other = final[1 - seat]
    max_animals = 0
    own_harvestes = 0
    for state in env.steps:
        farm = state[seat].observation["farms"][seat]
        max_animals = max(max_animals, _animal_count(farm))
    units, value = _stranded_value(own.observation)
    return {
        "candidate": candidate_name, "opponent": opponent_name, "seed": seed,
        "seat": seat, "final_money": float(own.reward), "opponent_money": float(other.reward),
        "advantage": float(own.reward) - float(other.reward),
        "max_animals": max_animals, "final_animals": _animal_count(own.observation["farms"][seat]),
        "possible_animal_loss": max_animals > _animal_count(own.observation["farms"][seat]),
        "stranded_units": units, "stranded_value": value,
        "runtime_error": None,
    }


def _summary(rows):
    ok = [row for row in rows if not row.get("runtime_error")]
    adv = [row["advantage"] for row in ok]
    wins = sum(value > 0 for value in adv)
    losses = sum(value < 0 for value in adv)
    return {
        "games": len(ok), "wins": wins, "losses": losses,
        "ties": len(ok) - wins - losses,
        "win_rate": wins / len(ok) if ok else 0.0,
        "average_money": statistics.fmean(row["final_money"] for row in ok) if ok else None,
        "average_opponent_money": statistics.fmean(row["opponent_money"] for row in ok) if ok else None,
        "average_advantage": statistics.fmean(adv) if adv else None,
        "median_advantage": statistics.median(adv) if adv else None,
        "p10_advantage": sorted(adv)[max(0, int(len(adv) * 0.10) - 1)] if adv else None,
        "variance_advantage": statistics.pvariance(adv) if len(adv) > 1 else 0.0,
        "animal_loss_games": sum(row.get("possible_animal_loss", False) for row in ok),
        "stranded_value_mean": statistics.fmean(row.get("stranded_value", 0.0) for row in ok) if ok else None,
        "runtime_errors": [row for row in rows if row.get("runtime_error")],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", nargs="+", type=int, default=[15000, 15001])
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    jobs = [
        (candidate, AGENTS[candidate], opponent, OPPONENTS[opponent], seed, seat)
        for candidate in AGENTS
        for opponent in OPPONENTS
        for seed in args.seeds
        for seat in (0, 1)
    ]
    rows = []
    with ProcessPoolExecutor(max_workers=max(1, args.workers)) as pool:
        for index, row in enumerate(pool.map(_run, jobs), 1):
            rows.append(row)
            print(f"{index}/{len(jobs)} {row['candidate']} vs {row['opponent']} seed={row['seed']} seat={row['seat']}", flush=True)
    summaries = {}
    for candidate in AGENTS:
        candidate_rows = [row for row in rows if row["candidate"] == candidate]
        summaries[candidate] = _summary(candidate_rows)
        for opponent in OPPONENTS:
            subset = [row for row in candidate_rows if row["opponent"] == opponent]
            summaries[candidate].setdefault("matchups", {})[opponent] = _summary(subset)
    payload = {
        "schema_version": 1,
        "seed_panel": args.seeds,
        "agents": AGENTS,
        "opponents": OPPONENTS,
        "rows": rows,
        "summaries": summaries,
    }
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(OUT)
    for candidate, summary in summaries.items():
        print(candidate, summary["wins"], summary["losses"], summary["ties"], f"adv={summary['average_advantage']}", "animal_loss_games", summary["animal_loss_games"])


if __name__ == "__main__":
    main()
