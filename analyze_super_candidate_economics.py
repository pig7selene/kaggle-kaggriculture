"""Exact matched-game economic attribution for the promoted super backbone."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from runpy import run_path

from kaggle_environments import make

from analyze_top_player_replays import _farm_snapshot, _transition_ledger
from run_epic_experiments import _independent_shop_schedule, _run_with_fixed_shops


ROOT = Path(__file__).resolve().parent
K3 = "agents/v27_replay_weed_guard.py"
CANDIDATE = "agents/super_replay/super_raw_55459817.py"
OUTPUT = ROOT / "experiments/super_replay_candidate_economics.json"


def _plain(counter):
    return {key: counter[key] for key in sorted(counter) if counter[key]}


def _game(seed, candidate_seat):
    candidate = run_path(str(ROOT / CANDIDATE))["agent"]
    k3 = run_path(str(ROOT / K3))["agent"]
    agents = [k3, k3]
    agents[candidate_seat] = candidate
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=True)
    _run_with_fixed_shops(env, agents, _independent_shop_schedule(seed))
    replay = env.toJSON()
    totals = []
    for _ in range(2):
        totals.append({
            "sale_revenue": Counter(), "sale_quantity": Counter(), "harvest_quantity": Counter(),
            "seed_spend": Counter(), "feed_spend": Counter(), "animal_spend": Counter(),
            "land_spend": 0, "labor_spend": 0, "hires": 0, "land_buys": 0,
        })
    timeline = [[], []]
    mismatches = []
    for step in range(1, 720):
        ledgers, errors = _transition_ledger(replay["steps"][step - 1], replay["steps"][step], replay.get("configuration", {}))
        mismatches.extend({"step": step, **error} for error in errors)
        for player, ledger in enumerate(ledgers):
            value = totals[player]
            value["sale_revenue"].update(ledger["sale_revenue"])
            value["sale_quantity"].update(ledger["sale_quantity"])
            value["harvest_quantity"].update(ledger["harvest_quantity"])
            value["seed_spend"].update(ledger["seed_spend"])
            value["feed_spend"].update(ledger["product_spend"])
            value["animal_spend"].update(ledger["animal_spend"])
            value["land_spend"] += ledger["land_spend"]
            value["labor_spend"] += ledger["labor_spend"]
            value["hires"] += ledger["hire_count"]
            value["land_buys"] += ledger["land_count"]
        if step % 24 == 0 or step == 719:
            obs = replay["steps"][step][0]["observation"]
            for player in range(2):
                snapshot = _farm_snapshot(obs["farms"][player])
                timeline[player].append({
                    "step": step, "day": int(obs["day"]), "money": float(obs["farms"][player]["money"]),
                    **snapshot,
                })
    rows = []
    for player, value in enumerate(totals):
        row = {
            "role": "candidate" if player == candidate_seat else "K3", "seat": player,
            "final_money": float(replay["steps"][-1][player]["reward"]),
            "sale_revenue": _plain(value["sale_revenue"]),
            "sale_quantity": _plain(value["sale_quantity"]),
            "harvest_quantity": _plain(value["harvest_quantity"]),
            "seed_spend": _plain(value["seed_spend"]), "feed_spend": _plain(value["feed_spend"]),
            "animal_spend": _plain(value["animal_spend"]), "land_spend": value["land_spend"],
            "labor_spend": value["labor_spend"], "hires": value["hires"], "land_buys": value["land_buys"],
            "total_sale_revenue": sum(value["sale_revenue"].values()),
            "total_recorded_spend": sum(value["seed_spend"].values()) + sum(value["feed_spend"].values()) + sum(value["animal_spend"].values()) + value["land_spend"] + value["labor_spend"],
            "timeline": timeline[player],
        }
        rows.append(row)
    return {
        "seed": seed, "candidate_seat": candidate_seat,
        "financial_mismatches": mismatches, "players": rows,
        "candidate_advantage": rows[candidate_seat]["final_money"] - rows[1 - candidate_seat]["final_money"],
    }


def main():
    games = [_game(seed, seat) for seed in range(996800, 996804) for seat in (0, 1)]
    candidates = [next(value for value in game["players"] if value["role"] == "candidate") for game in games]
    baselines = [next(value for value in game["players"] if value["role"] == "K3") for game in games]
    products = sorted({key for row in candidates + baselines for key in row["sale_revenue"]})
    aggregate = {
        "games": len(games),
        "average_final_money_delta": sum(game["candidate_advantage"] for game in games) / len(games),
        "average_total_sale_revenue_delta": sum(left["total_sale_revenue"] - right["total_sale_revenue"] for left, right in zip(candidates, baselines)) / len(games),
        "average_total_recorded_spend_delta": sum(left["total_recorded_spend"] - right["total_recorded_spend"] for left, right in zip(candidates, baselines)) / len(games),
        "average_land_spend_delta": sum(left["land_spend"] - right["land_spend"] for left, right in zip(candidates, baselines)) / len(games),
        "average_labor_spend_delta": sum(left["labor_spend"] - right["labor_spend"] for left, right in zip(candidates, baselines)) / len(games),
        "average_animal_spend_delta": sum(sum(left["animal_spend"].values()) - sum(right["animal_spend"].values()) for left, right in zip(candidates, baselines)) / len(games),
        "average_feed_spend_delta": sum(sum(left["feed_spend"].values()) - sum(right["feed_spend"].values()) for left, right in zip(candidates, baselines)) / len(games),
        "average_seed_spend_delta": sum(sum(left["seed_spend"].values()) - sum(right["seed_spend"].values()) for left, right in zip(candidates, baselines)) / len(games),
        "average_revenue_delta_by_product": {
            product: sum(left["sale_revenue"].get(product, 0) - right["sale_revenue"].get(product, 0) for left, right in zip(candidates, baselines)) / len(games)
            for product in products
        },
    }
    OUTPUT.write_text(json.dumps({
        "schema_version": 1, "candidate": CANDIDATE, "baseline": K3,
        "design": "same fixed seed and shop schedule, both seats; exact transition-ledger reconstruction",
        "games": games, "aggregate": aggregate,
        "total_financial_mismatches": sum(len(row["financial_mismatches"]) for row in games),
    }, indent=2, sort_keys=True) + "\n")
    print(OUTPUT)


if __name__ == "__main__":
    main()
