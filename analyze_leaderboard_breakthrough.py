"""Replay-first economic trajectory analysis for leaderboard development."""

from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from kaggle_environments.envs.kaggriculture import kaggriculture as game

from analyze_epic_next_stage import _action_effects, _inventory_snapshot, _snapshot
from analyze_top_player_replays import _transition_ledger


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "experiments" / "leaderboard_breakthrough_analysis.json"
CHECKPOINTS = (2, 4, 6, 8, 10, 11, 12, 15, 20, 25, 29)
CROPS = tuple(game.CROPS)
ANIMAL_PRODUCTS = ("EGG", "MILK", "WOOL", "FERTILIZER")

SUBMISSIONS = {
    "router_709_6": {
        "id": 55429527,
        "score": 709.6,
        "path": ROOT / "experiments/leaderboard_replays/submission_55429527/replays",
        "source": "agents/router_replay_hands12.py",
        "source_sha256": "bac81a2099f3c4b7f97670a4e25d8cb0cc1c22fd23a41310096dd792b2f8f99b",
        "submission_sha256": "edacba210dd55e9094e505e14fb57003610be92c43028007c31dbbabc1d78505",
    },
    "opening_803_5": {
        "id": 55435253,
        "score": 803.5,
        "path": ROOT / "experiments/leaderboard_replays/submission_55435253/replays",
        "source": "agents/opening_public_front_cow8_day6.py",
        "source_sha256": "3ede0041921010b0136abb538395faa5951e9af1fb9b76be41467246885da6a8",
        "submission_sha256": "3196b73fc2f46e25284b773136b530e2aacbaad2ba8a9dffdfce66472fe2a0fb",
    },
    "lifecycle_798_0": {
        "id": 55438811,
        "score": 798.0,
        "path": ROOT / "experiments/leaderboard_replays/submission_55438811/replays",
        "source": "agents/lifecycle_lc_combined.py",
        "source_sha256": "db12d32912843e012c3dfd7e84c2c384ce998694bf02b98fc7e1fe9189c17e78",
        "submission_sha256": "d0fbf1205a7e27f8294f1f9a06afd581cfb3e926f8ab88acc0b7f7a8b72620cf",
    },
}


def _plain(counter):
    return {key: counter[key] for key in sorted(counter) if counter[key]}


def _sum_products(values, products):
    return sum(values.get(product, 0) for product in products)


def _flatten_inventory(state):
    private = state["observation"]["private"]
    total = Counter(private.get("shed", {}))
    for inventory in private.get("inventories", []):
        total.update(inventory)
    return _plain(total)


def _daily_row(day):
    return {
        "day": day,
        "bank_start": None,
        "bank_end": None,
        "farm": {},
        "inventory": {},
        "max_hands": 0,
        "revenue": Counter(),
        "spending": Counter(),
        "sales": Counter(),
        "harvests": Counter(),
        "plantings": Counter(),
        "animal_purchases": Counter(),
        "land_purchases": 0,
        "hires": 0,
        "successful_actions": Counter(),
        "sale_events": [],
        "investment_events": [],
    }


def _serialize(row):
    result = dict(row)
    # Checkpoints retain composition, maturity and cohorts; exact tile records
    # and worker coordinates are redundant with the source replays and made
    # the machine-readable artifact hundreds of megabytes larger.
    result["farm"] = {
        key: value for key, value in result["farm"].items()
        if key not in {"tiles", "workers", "unlocked_quadrants", "watered_crops"}
    }
    for key in (
        "revenue", "spending", "sales", "harvests", "plantings",
        "animal_purchases", "successful_actions",
    ):
        result[key] = _plain(result[key])
    result["crop_revenue"] = _sum_products(result["revenue"], CROPS)
    result["animal_revenue"] = _sum_products(result["revenue"], ANIMAL_PRODUCTS)
    result["total_revenue"] = sum(result["revenue"].values())
    result["total_spending"] = sum(result["spending"].values())
    result["harvest_actions"] = result["successful_actions"].get("HARVEST", 0)
    return result


def _first_durable(gaps, key, threshold=0):
    for index, row in enumerate(gaps):
        if row[key] > threshold and all(later[key] > threshold for later in gaps[index:]):
            return row["day"]
    return None


def _analyze_player(replay, player):
    steps = replay["steps"]
    configuration = replay.get("configuration", {})
    names = replay["info"]["TeamNames"]
    daily = [_daily_row(day) for day in range(30)]
    mismatches = []
    for index, states in enumerate(steps):
        obs = states[0]["observation"]
        day = min(29, int(obs.get("day", index // 24)))
        farm = obs["farms"][player]
        row = daily[day]
        if row["bank_start"] is None:
            row["bank_start"] = float(farm["money"])
        row["bank_end"] = float(farm["money"])
        row["farm"] = _snapshot(obs, player)
        row["inventory"] = _flatten_inventory(states[player])
        row["max_hands"] = max(row["max_hands"], len(farm.get("hands", [])))
    for index in range(1, len(steps)):
        previous = steps[index - 1]
        current = steps[index]
        obs = previous[0]["observation"]
        day = min(29, int(obs.get("day", (index - 1) // 24)))
        hour = int(obs.get("hour", (index - 1) % 24))
        row = daily[day]
        ledgers, errors = _transition_ledger(previous, current, configuration)
        for error in errors:
            mismatches.append({"step": index, **error})
        ledger = ledgers[player]
        effects = _action_effects(previous, current, player, configuration)
        for product, amount in ledger["sale_revenue"].items():
            row["revenue"][product] += amount
            row["sales"][product] += ledger["sale_quantity"][product]
            row["sale_events"].append({
                "step": int(obs.get("step", index - 1)), "day": day, "hour": hour,
                "product": product, "quantity": ledger["sale_quantity"][product],
                "revenue": amount,
                "average_price": statistics.fmean(ledger["sale_prices"][product]),
            })
        row["harvests"].update(ledger["harvest_quantity"])
        row["plantings"].update(ledger["plant_quantity"])
        row["animal_purchases"].update(ledger["animal_quantity"])
        row["land_purchases"] += ledger["land_count"]
        row["hires"] += ledger["hire_count"]
        for op, count in effects["ops"].items():
            if op in {"HARVEST", "PLANT", "WATER", "FERTILIZE", "FEED", "CARE", "COLLECT_FERTILIZER"}:
                row["successful_actions"][op] += sum(
                    event["op"] == op for event in effects["events"]
                )
        spending = {
            "seed": sum(ledger["seed_spend"].values()),
            "feed": sum(ledger["product_spend"].values()),
            "animals": sum(ledger["animal_spend"].values()),
            "land": ledger["land_spend"],
            "labor": ledger["labor_spend"],
        }
        row["spending"].update(spending)
        investment = spending["animals"] + spending["land"]
        if investment:
            row["investment_events"].append({
                "step": int(obs.get("step", index - 1)), "day": day, "hour": hour,
                "bank_before": float(obs["farms"][player]["money"]),
                "bank_after": float(current[0]["observation"]["farms"][player]["money"]),
                "land_spending": spending["land"],
                "animal_spending": spending["animals"],
                "animals": _plain(ledger["animal_quantity"]),
            })
    timeline = [_serialize(row) for row in daily]
    cumulative_revenue = Counter()
    cumulative_spending = Counter()
    for row in timeline:
        cumulative_revenue.update(row["revenue"])
        cumulative_spending.update(row["spending"])
        row["cumulative_revenue_by_product"] = _plain(cumulative_revenue)
        row["cumulative_revenue"] = sum(cumulative_revenue.values())
        row["cumulative_crop_revenue"] = _sum_products(cumulative_revenue, CROPS)
        row["cumulative_animal_revenue"] = _sum_products(cumulative_revenue, ANIMAL_PRODUCTS)
        row["cumulative_spending"] = sum(cumulative_spending.values())
    major_sales = sorted(
        [event for row in timeline for event in row["sale_events"]],
        key=lambda event: event["revenue"], reverse=True,
    )[:20]
    return {
        "player": player,
        "team": names[player],
        "opponent": names[1 - player],
        "final_money": float(steps[-1][player]["reward"]),
        "opponent_money": float(steps[-1][1 - player]["reward"]),
        "result": "win" if steps[-1][player]["reward"] > steps[-1][1 - player]["reward"] else "loss" if steps[-1][player]["reward"] < steps[-1][1 - player]["reward"] else "tie",
        "financial_reconstruction_mismatches": mismatches,
        "land_days": [row["day"] for row in timeline for _ in range(row["land_purchases"])],
        "max_hands": max(row["max_hands"] for row in timeline),
        "max_productive_tiles": max(row["farm"].get("productive_tiles", 0) for row in timeline),
        "peak_crops": _plain(Counter({crop: max(row["farm"].get("crops", {}).get(crop, 0) for row in timeline) for crop in CROPS})),
        "peak_animals": _plain(Counter({animal: max(row["farm"].get("animals", {}).get(animal, 0) for row in timeline) for animal in game.ANIMALS})),
        "major_sales": major_sales,
        "investment_events": [event for row in timeline for event in row["investment_events"]],
        "timeline": timeline,
    }


def _loss_diagnosis(ours, opponent):
    gaps = []
    for day in range(30):
        me = ours["timeline"][day]
        rival = opponent["timeline"][day]
        gaps.append({
            "day": day,
            "bank_gap": rival["bank_end"] - me["bank_end"],
            "revenue_gap": rival["cumulative_revenue"] - me["cumulative_revenue"],
            "crop_revenue_gap": rival["cumulative_crop_revenue"] - me["cumulative_crop_revenue"],
            "animal_revenue_gap": rival["cumulative_animal_revenue"] - me["cumulative_animal_revenue"],
            "spending_gap": rival["cumulative_spending"] - me["cumulative_spending"],
            "productive_tile_gap": rival["farm"].get("productive_tiles", 0) - me["farm"].get("productive_tiles", 0),
            "harvest_gap": sum(r["harvest_actions"] for r in opponent["timeline"][:day + 1]) - sum(r["harvest_actions"] for r in ours["timeline"][:day + 1]),
        })
    return {
        "first_durable_bank_lead": _first_durable(gaps, "bank_gap"),
        "first_durable_revenue_lead": _first_durable(gaps, "revenue_gap"),
        "first_durable_2500_revenue_lead": _first_durable(gaps, "revenue_gap", 2500),
        "first_durable_crop_revenue_lead": _first_durable(gaps, "crop_revenue_gap"),
        "first_durable_productive_tile_lead": _first_durable(gaps, "productive_tile_gap"),
        "gaps": gaps,
    }


def _checkpoints(appearance):
    result = {}
    for day in CHECKPOINTS:
        row = appearance["timeline"][day]
        result[str(day)] = {
            "bank": row["bank_end"],
            "cumulative_revenue": row["cumulative_revenue"],
            "cumulative_spending": row["cumulative_spending"],
            "crop_revenue": row["cumulative_crop_revenue"],
            "animal_revenue": row["cumulative_animal_revenue"],
            "quadrants": row["farm"].get("quadrants"),
            "hands": row["max_hands"],
            "productive_tiles": row["farm"].get("productive_tiles"),
            "crops": row["farm"].get("crops", {}),
            "mature_crops": row["farm"].get("mature_crops", {}),
            "animals": row["farm"].get("animals", {}),
            "harvest_actions": sum(value["harvest_actions"] for value in appearance["timeline"][:day + 1]),
            "inventory": row["inventory"],
        }
    return result


def _aggregate(appearances):
    if not appearances:
        return {}
    return {
        "appearances": len(appearances),
        "wins": sum(row["result"] == "win" for row in appearances),
        "losses": sum(row["result"] == "loss" for row in appearances),
        "ties": sum(row["result"] == "tie" for row in appearances),
        "average_final_money": statistics.fmean(row["final_money"] for row in appearances),
        "average_advantage": statistics.fmean(row["final_money"] - row["opponent_money"] for row in appearances),
        "median_land_days": [
            statistics.median(days) for index in range(2)
            if (days := [row["land_days"][index] for row in appearances if len(row["land_days"]) > index])
        ],
        "median_max_hands": statistics.median(row["max_hands"] for row in appearances),
        "median_max_productive_tiles": statistics.median(row["max_productive_tiles"] for row in appearances),
        "checkpoint_medians": {
            str(day): {
                key: statistics.median(row["checkpoints"][str(day)][key] for row in appearances)
                for key in ("bank", "cumulative_revenue", "cumulative_spending", "crop_revenue", "animal_revenue", "quadrants", "hands", "productive_tiles", "harvest_actions")
            }
            for day in CHECKPOINTS
        },
    }


def analyze():
    payload = {"schema_version": 1, "submissions": {}, "top_public": {}}
    for key, metadata in SUBMISSIONS.items():
        appearances = []
        games = []
        for path in sorted(metadata["path"].glob("episode-*-replay.json")):
            replay = json.loads(path.read_text())
            names = replay["info"]["TeamNames"]
            if "Selene" not in names:
                continue
            our_player = names.index("Selene")
            ours = _analyze_player(replay, our_player)
            opponent = _analyze_player(replay, 1 - our_player)
            ours["checkpoints"] = _checkpoints(ours)
            opponent["checkpoints"] = _checkpoints(opponent)
            diagnosis = _loss_diagnosis(ours, opponent) if ours["result"] == "loss" else None
            appearances.append(ours)
            games.append({
                "episode_id": int(replay["info"]["EpisodeId"]),
                "seed": replay["info"].get("seed"),
                "our_player": our_player,
                "ours": ours,
                "opponent": opponent,
                "loss_diagnosis": diagnosis,
            })
        payload["submissions"][key] = {
            **{name: value for name, value in metadata.items() if name != "path"},
            "replays_analyzed": len(games),
            "aggregate": _aggregate(appearances),
            "games": games,
        }
    manifest = json.loads((ROOT / "experiments/top_player_replays/manifest.json").read_text())
    selected = {row["team_name"]: row for row in manifest["players"]}
    top_appearances = []
    top_games = []
    for path in sorted((ROOT / "experiments/top_player_replays/replays").glob("episode-*-replay.json")):
        replay = json.loads(path.read_text())
        game_row = {"episode_id": int(replay["info"]["EpisodeId"]), "appearances": []}
        for player, name in enumerate(replay["info"]["TeamNames"]):
            if name not in selected:
                continue
            appearance = _analyze_player(replay, player)
            appearance["checkpoints"] = _checkpoints(appearance)
            appearance["leaderboard_score"] = selected[name]["leaderboard_score"]
            top_appearances.append(appearance)
            game_row["appearances"].append(appearance)
        top_games.append(game_row)
    payload["top_public"] = {
        "unique_replays": len(top_games),
        "appearances": len(top_appearances),
        "aggregate": _aggregate(top_appearances),
        "games": top_games,
    }
    mismatches = []
    for submission in payload["submissions"].values():
        for replay in submission["games"]:
            for side in ("ours", "opponent"):
                mismatches.extend(replay[side]["financial_reconstruction_mismatches"])
    for replay in top_games:
        for appearance in replay["appearances"]:
            mismatches.extend(appearance["financial_reconstruction_mismatches"])
    payload["financial_reconstruction_mismatches"] = mismatches
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote {OUTPUT}")
    print(f"financial reconstruction mismatches: {len(mismatches)}")
    for key, submission in payload["submissions"].items():
        print(key, submission["aggregate"])
    print("top_public", payload["top_public"]["aggregate"])
    return payload


if __name__ == "__main__":
    analyze()
