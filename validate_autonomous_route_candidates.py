"""Held-out validation for the route-family challenger.

This is deliberately separate from the broad diagnostic screen: candidates are
compared against the frozen portfolio and several replay-era strong controls on
fresh seeds, with both seats and no sequential promotion.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import statistics
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from kaggle_environments import make


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "experiments" / "autonomous_route_validation.json"
CANDIDATES = {
    "current_best": ROOT / "agents/top50_distilled/top50_observable_portfolio.py",
    "family01_medoid": ROOT / "agents/autonomous_next/top50_family01_medoid.py",
    "raw_55899537": ROOT / "agents/autonomous_next/top50_raw_55899537.py",
}
OPPONENTS = {
    "current_best": ROOT / "agents/top50_distilled/top50_observable_portfolio.py",
    "family01_medoid": ROOT / "agents/autonomous_next/top50_family01_medoid.py",
    "super_v2": ROOT / "agents/super_replay_v2/super_backbone_v2.py",
    "v27": ROOT / "agents/v27_replay_weed_guard.py",
    "lifecycle": ROOT / "agents/lifecycle_lc_combined.py",
    "router_hands12": ROOT / "agents/router_replay_hands12.py",
    "high_labor": ROOT / "agents/proxies/high_labor.py",
    "livestock": ROOT / "agents/proxies/livestock_crop.py",
}
SELLABLE = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")


def _load(path):
    name = "route_validation_" + hashlib.sha256(str(path).encode()).hexdigest()[:12]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.agent


def _animal_count(farm):
    return sum(1 for row in farm["tiles"] for tile in row if isinstance(tile, dict) and tile.get("animal"))


def _stranded_value(obs):
    prices = obs.get("market", {}).get("prices", {})
    private = obs["private"]
    units = 0
    value = 0.0
    for item in SELLABLE:
        count = int(private.get("shed", {}).get(item, 0))
        count += sum(int(inv.get(item, 0)) for inv in private.get("inventories", []))
        units += count
        value += count * float(prices.get(item, 1))
    return units, value


def _run(job):
    candidate_name, candidate_path, opponent_name, opponent_path, seed, seat = job
    candidate = _load(candidate_path)
    opponent = _load(opponent_path)
    pair = [opponent, opponent]
    pair[seat] = candidate
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": int(seed)}, debug=True)
    error = None
    try:
        env.run(pair)
    except Exception as exc:
        error = repr(exc)
    if error:
        return {"candidate": candidate_name, "opponent": opponent_name, "seed": seed, "seat": seat, "error": error}
    final = env.steps[-1]
    own = final[seat]
    other = final[1 - seat]
    animal_counts = [_animal_count(state[seat].observation["farms"][seat]) for state in env.steps]
    units, value = _stranded_value(own.observation)
    return {
        "candidate": candidate_name, "opponent": opponent_name, "seed": seed, "seat": seat,
        "own_money": float(own.reward), "opponent_money": float(other.reward),
        "advantage": float(own.reward) - float(other.reward),
        "max_animals": max(animal_counts), "final_animals": animal_counts[-1],
        "animal_loss": animal_counts[-1] < max(animal_counts),
        "stranded_units": units, "stranded_value": value, "error": None,
    }


def _summary(rows):
    valid = [row for row in rows if not row.get("error")]
    adv = [row["advantage"] for row in valid]
    wins = sum(value > 0 for value in adv)
    return {
        "games": len(valid), "wins": wins, "losses": sum(value < 0 for value in adv),
        "ties": sum(value == 0 for value in adv),
        "win_rate": wins / len(valid) if valid else 0.0,
        "average_money": statistics.fmean(row["own_money"] for row in valid) if valid else None,
        "average_opponent_money": statistics.fmean(row["opponent_money"] for row in valid) if valid else None,
        "average_advantage": statistics.fmean(adv) if adv else None,
        "median_advantage": statistics.median(adv) if adv else None,
        "p10_advantage": sorted(adv)[max(0, int(len(adv) * 0.10) - 1)] if adv else None,
        "p5_advantage": sorted(adv)[max(0, int(len(adv) * 0.05) - 1)] if adv else None,
        "variance_advantage": statistics.pvariance(adv) if len(adv) > 1 else 0.0,
        "animal_loss_games": sum(row.get("animal_loss", False) for row in valid),
        "mean_stranded_value": statistics.fmean(row.get("stranded_value", 0.0) for row in valid) if valid else None,
        "errors": [row for row in rows if row.get("error")],
    }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", nargs="+", type=int, default=list(range(16000, 16004)))
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    jobs = [
        (candidate, CANDIDATES[candidate], opponent, OPPONENTS[opponent], seed, seat)
        for candidate in CANDIDATES for opponent in OPPONENTS
        for seed in args.seeds for seat in (0, 1)
    ]
    rows = []
    with ProcessPoolExecutor(max_workers=max(1, args.workers)) as pool:
        for index, row in enumerate(pool.map(_run, jobs), 1):
            rows.append(row)
            print(f"{index}/{len(jobs)} {row['candidate']} vs {row['opponent']} seed={row['seed']} seat={row['seat']}", flush=True)
    summaries = {}
    for candidate in CANDIDATES:
        own = [row for row in rows if row["candidate"] == candidate]
        summaries[candidate] = _summary(own)
        summaries[candidate]["matchups"] = {
            opponent: _summary([row for row in own if row["opponent"] == opponent])
            for opponent in OPPONENTS
        }
    OUT.write_text(json.dumps({"schema_version": 1, "seed_panel": args.seeds, "candidates": {k: str(v) for k, v in CANDIDATES.items()}, "opponents": {k: str(v) for k, v in OPPONENTS.items()}, "rows": rows, "summaries": summaries}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(OUT)
    for candidate, summary in summaries.items():
        print(candidate, summary["wins"], summary["losses"], summary["ties"], f"avg_adv={summary['average_advantage']}", f"p10={summary['p10_advantage']}", "animal_loss", summary["animal_loss_games"])


if __name__ == "__main__":
    main()
