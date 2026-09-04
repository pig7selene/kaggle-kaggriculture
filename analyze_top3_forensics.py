"""Forensic reconstruction of the current, version-pure Kaggriculture Top 3.

This script consumes only the already-downloaded public replay corpus.  It keeps
all 30 current-version appearances per team (including identical action routes
played into different markets), reconciles accounting against observed bank
deltas, and writes compact evidence artifacts rather than deployable policy.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import statistics

from analyze_top_player_replays import _transition_ledger
from analyze_v27_routes import normalized_action
from mine_top50_strategies import _inventory, _tile_counts


ROOT = Path(__file__).resolve().parent
EXP = ROOT / "experiments"
MANIFEST = EXP / "top3_corpus_manifest.json"
CORE = EXP / "top3_forensic_core.json"
VERSION = EXP / "top3_version_audit.json"
ADAPTIVE = EXP / "top3_adaptive_divergence_map.json"
DIRECT = EXP / "top3_direct_comparison.json"
SHARED = EXP / "top3_shared_core.json"
RANK1 = EXP / "top3_rank1_unique_analysis.json"

PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
CROPS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")
ANIMALS = ("GOOSE", "COW", "SHEEP")
ANIMAL_PRODUCT = {"GOOSE": "EGG", "COW": "MILK", "SHEEP": "WOOL"}
MOVE = {"NORTH", "SOUTH", "EAST", "WEST"}
CROP_OPS = {"PLANT", "WATER", "HARVEST", "FERTILIZE"}
ANIMAL_OPS = {"BUILD_PASTURE", "BUILD_COOP", "FEED", "CARE", "COLLECT_FERTILIZER", "PLACE"}
PHASE_WINDOWS = {
    "opening": (0, 120),
    "first_reinvestment": (120, 216),
    "second_reinvestment": (216, 336),
    "scaled_midgame": (336, 552),
    "late_production": (552, 672),
    "liquidation": (672, 719),
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def sha(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def percentile(values, fraction):
    values = sorted(float(value) for value in values)
    if not values:
        return None
    point = fraction * (len(values) - 1)
    lo = int(point)
    weight = point - lo
    return values[lo] * (1 - weight) + values[min(lo + 1, len(values) - 1)] * weight


def median(values):
    values = [value for value in values if value is not None]
    return statistics.median(values) if values else None


def mean(values):
    values = [value for value in values if value is not None]
    return statistics.fmean(values) if values else None


def plain(counter):
    return {key: counter[key] for key in sorted(counter) if counter[key]}


def request_components(action):
    field = [action["farmer"], *action["hands"]]
    crop = [request for request in field if request and request[0] in CROP_OPS]
    animal = [request for request in field if request and request[0] in ANIMAL_OPS]
    market = action["market"]
    return {
        "farmer": action["farmer"],
        "hands": action["hands"],
        "market": market,
        "purchases": [order for order in market if order and order[0] != "SELL"],
        "sells": [order for order in market if order and order[0] == "SELL"],
        "crop": crop,
        "animal": animal,
        "full": action,
    }


def state_features(obs, player):
    own = obs["farms"][player]
    other = obs["farms"][1 - player]
    own_counts = _tile_counts(own)
    other_counts = _tile_counts(other)
    private = obs["private"]
    inventory = Counter(private.get("shed", {}))
    for carried in private.get("inventories", []):
        inventory.update(carried)
    prices = obs["market"]["prices"]
    quantities = obs["market"]["inventory"]
    shops = Counter(obs["town"].get("unlocked_shops", []))
    return {
        "own_bank": float(own["money"]),
        "opponent_bank": float(other["money"]),
        "own_hands": len(own.get("hands", [])),
        "opponent_hands": len(other.get("hands", [])),
        "own_quadrants": len(own["unlocked_quadrants"]),
        "opponent_quadrants": len(other["unlocked_quadrants"]),
        "own_productive": own_counts["productive"],
        "opponent_productive": other_counts["productive"],
        "own_cows": own_counts["animals"].get("COW", 0),
        "own_sheep": own_counts["animals"].get("SHEEP", 0),
        "opponent_cows": other_counts["animals"].get("COW", 0),
        "opponent_sheep": other_counts["animals"].get("SHEEP", 0),
        "opponent_melon": other_counts["crops"].get("MELON", 0),
        "opponent_strawberry": other_counts["crops"].get("STRAWBERRY", 0),
        "own_inventory_total": sum(inventory.values()),
        "own_milk_inventory": inventory.get("MILK", 0),
        "own_wool_inventory": inventory.get("WOOL", 0),
        "own_strawberry_inventory": inventory.get("STRAWBERRY", 0),
        "price_milk": prices.get("MILK", 0),
        "price_wool": prices.get("WOOL", 0),
        "price_melon": prices.get("MELON", 0),
        "price_strawberry": prices.get("STRAWBERRY", 0),
        "price_fertilizer": prices.get("FERTILIZER", 0),
        "market_total": sum(quantities.values()),
        "market_milk": quantities.get("MILK", 0),
        "market_wool": quantities.get("WOOL", 0),
        "market_melon": quantities.get("MELON", 0),
        "market_strawberry": quantities.get("STRAWBERRY", 0),
        "shop_instances": sum(shops.values()),
        "shop_signature": sha(sorted(shops.items()))[:12],
    }


def new_day(day):
    return {
        "day": day, "bank_start": None, "bank_end": None,
        "sales": Counter(), "sale_revenue": Counter(), "sale_events": [],
        "seed_purchases": Counter(), "seed_spending": Counter(),
        "feed_purchases": Counter(), "feed_spending": Counter(),
        "animal_purchases": Counter(), "animal_spending": Counter(),
        "land_purchases": 0, "land_spending": 0,
        "hires": 0, "labor_spending": 0,
        "harvests": Counter(), "plantings": Counter(),
        "structures_built": Counter(), "animals_placed": Counter(),
        "feed_actions": 0, "care_actions": 0, "fertilizer_collected": 0,
        "reconciliation": 0.0, "farm": {}, "inventory": {},
    }


def add_ledger(row, ledger, before, after, step):
    spend = (
        sum(ledger["seed_spend"].values()) + sum(ledger["product_spend"].values())
        + sum(ledger["animal_spend"].values()) + ledger["land_spend"] + ledger["labor_spend"]
    )
    predicted = sum(ledger["sale_revenue"].values())
    exact_revenue = after - before + spend
    residual = exact_revenue - predicted
    adjusted = Counter(ledger["sale_revenue"])
    if residual and adjusted:
        total = sum(adjusted.values())
        remaining = residual
        items = sorted(adjusted)
        for item in items[:-1]:
            share = residual * adjusted[item] / total if total else 0
            adjusted[item] += share
            remaining -= share
        adjusted[items[-1]] += remaining
    row["reconciliation"] += residual
    for target, source in (
        ("sales", "sale_quantity"), ("seed_purchases", "seed_quantity"),
        ("seed_spending", "seed_spend"), ("feed_purchases", "product_quantity"),
        ("feed_spending", "product_spend"), ("animal_purchases", "animal_quantity"),
        ("animal_spending", "animal_spend"), ("harvests", "harvest_quantity"),
        ("plantings", "plant_quantity"), ("structures_built", "structures_built"),
        ("animals_placed", "animals_placed"),
    ):
        row[target].update(ledger[source])
    row["sale_revenue"].update(adjusted)
    row["land_purchases"] += ledger["land_count"]
    row["land_spending"] += ledger["land_spend"]
    row["hires"] += ledger["hire_count"]
    row["labor_spending"] += ledger["labor_spend"]
    row["feed_actions"] += ledger["feed_actions"]
    row["care_actions"] += ledger["care_actions"]
    row["fertilizer_collected"] += ledger["fertilizer_collected"]
    for item, quantity in ledger["sale_quantity"].items():
        prices = ledger["sale_prices"].get(item, [])
        row["sale_events"].append({
            "step": step, "day": step // 24, "hour": step % 24,
            "product": item, "quantity": quantity,
            "revenue": adjusted[item],
            "average_price": adjusted[item] / quantity if quantity else 0,
            "locally_replayed_price": statistics.fmean(prices) if prices else None,
        })


def serialize_day(row):
    output = dict(row)
    for key in (
        "sales", "sale_revenue", "seed_purchases", "seed_spending",
        "feed_purchases", "feed_spending", "animal_purchases", "animal_spending",
        "harvests", "plantings", "structures_built", "animals_placed",
    ):
        output[key] = plain(output[key])
    output["total_sale_revenue"] = sum(output["sale_revenue"].values())
    output["total_spending"] = (
        sum(output["seed_spending"].values()) + sum(output["feed_spending"].values())
        + sum(output["animal_spending"].values()) + output["land_spending"]
        + output["labor_spending"]
    )
    return output


def economic_timelines(replay):
    players = len(replay["steps"][0])
    daily = [[new_day(day) for day in range(30)] for _ in range(players)]
    mismatches = []
    for state in replay["steps"]:
        obs = state[0]["observation"]
        day = min(29, int(obs.get("day", obs.get("step", 0) // 24)))
        for player in range(players):
            farm = obs["farms"][player]
            row = daily[player][day]
            money = float(farm["money"])
            row["bank_start"] = money if row["bank_start"] is None else row["bank_start"]
            row["bank_end"] = money
            counts = _tile_counts(farm)
            row["farm"] = {
                "money": money, "quadrants": len(farm["unlocked_quadrants"]),
                "hands": len(farm.get("hands", [])), **counts,
            }
            private = state[player]["observation"]["private"]
            carried = Counter(private.get("shed", {}))
            for inventory in private.get("inventories", []):
                carried.update(inventory)
            row["inventory"] = plain(carried)
    for index in range(1, len(replay["steps"])):
        previous = replay["steps"][index - 1]
        current = replay["steps"][index]
        obs = previous[0]["observation"]
        day = min(29, int(obs.get("day", (index - 1) // 24)))
        ledgers, errors = _transition_ledger(previous, current, replay.get("configuration", {}))
        for error in errors:
            mismatches.append({"step": index - 1, **error})
        for player, ledger in enumerate(ledgers):
            before = float(previous[player]["observation"]["farms"][player]["money"])
            after = float(current[player]["observation"]["farms"][player]["money"])
            add_ledger(daily[player][day], ledger, before, after, index - 1)
    return [[serialize_day(row) for row in timeline] for timeline in daily], mismatches


def crop_and_worker_forensics(replay, player, actions):
    cohorts = defaultdict(lambda: {
        "crop": None, "planted_day": None, "plant_steps": [], "water_actions": 0,
        "fertilize_actions": 0, "harvest_steps": [], "harvest_units": 0,
        "worker_turns": 0,
    })
    roles = Counter()
    animal_service = Counter()
    total_moves = 0
    last_plant_step = None
    last_harvest_step = None
    for step, action in enumerate(actions):
        obs = replay["steps"][step][player]["observation"]
        farm = obs["farms"][player]
        positions = [farm["farmer"], *farm.get("hands", [])]
        requests = [action["farmer"], *action["hands"]]
        for position, request in zip(positions, requests):
            op = request[0] if request else "PASS"
            roles[op] += 1
            if op in MOVE:
                total_moves += 1
                continue
            x, y = position
            tile = farm["tiles"][y][x]
            if op == "PLANT":
                crop = request[1]
                key = f"{crop}:{obs['day']}"
                cohort = cohorts[key]
                cohort["crop"] = crop
                cohort["planted_day"] = int(obs["day"])
                cohort["plant_steps"].append(step)
                cohort["worker_turns"] += 1
                last_plant_step = step
            elif op in {"WATER", "FERTILIZE", "HARVEST"} and isinstance(tile, dict) and tile.get("kind") == "PLANT":
                crop = tile.get("crop")
                planted_day = int(tile.get("planted_day", obs["day"]))
                key = f"{crop}:{planted_day}"
                cohort = cohorts[key]
                cohort["crop"] = crop
                cohort["planted_day"] = planted_day
                cohort["worker_turns"] += 1
                if op == "WATER":
                    cohort["water_actions"] += 1
                elif op == "FERTILIZE":
                    cohort["fertilize_actions"] += 1
                else:
                    cohort["harvest_steps"].append(step)
                    cohort["harvest_units"] += int(tile.get("yield_units", 0))
                    last_harvest_step = step
            if op in ANIMAL_OPS and isinstance(tile, dict):
                animal = tile.get("animal") or "UNPLACED"
                animal_service[f"{animal}:{op}"] += 1
    output = []
    for key, cohort in sorted(cohorts.items(), key=lambda item: (item[1]["planted_day"], item[1]["crop"])):
        planted = cohort["plant_steps"]
        harvested = cohort["harvest_steps"]
        cohort["tiles_planted"] = len(planted)
        cohort["plant_window"] = [min(planted), max(planted)] if planted else None
        cohort["harvest_window"] = [min(harvested), max(harvested)] if harvested else None
        cohort["movement_share_proxy"] = total_moves * cohort["worker_turns"] / max(1, sum(value["worker_turns"] for value in cohorts.values()))
        output.append({"cohort_id": key, **cohort})
    return {
        "cohorts": output,
        "field_actions": plain(roles),
        "animal_service": plain(animal_service),
        "movement_actions": total_moves,
        "movement_per_harvest_action": total_moves / max(1, roles["HARVEST"]),
        "last_plant_step": last_plant_step,
        "last_harvest_step": last_harvest_step,
    }


def summarize_appearance(meta, replay, timeline, opponent_timeline, actions, features, forensics):
    player = meta["seat"]
    other = 1 - player
    sale_quantity, sale_revenue, harvests = Counter(), Counter(), Counter()
    seeds, seed_spend, feed, feed_spend = Counter(), Counter(), Counter(), Counter()
    animals, animal_spend = Counter(), Counter()
    land_steps, hire_steps, animal_events = [], [], []
    sale_events = []
    for row in timeline:
        sale_quantity.update(row["sales"]); sale_revenue.update(row["sale_revenue"])
        harvests.update(row["harvests"]); seeds.update(row["seed_purchases"])
        seed_spend.update(row["seed_spending"]); feed.update(row["feed_purchases"])
        feed_spend.update(row["feed_spending"]); animals.update(row["animal_purchases"])
        animal_spend.update(row["animal_spending"]); sale_events.extend(row["sale_events"])
    for step, action in enumerate(actions):
        for order in action["market"]:
            if not order:
                continue
            if order[0] == "BUY_LAND":
                land_steps.append(step)
            elif order[0] == "HIRE":
                hire_steps.append(step)
            elif order[0] == "BUY_ANIMAL":
                animal_events.append({"step": step, "day": step / 24, "animal": order[1], "quantity": order[2]})
    daily_counts = [row["farm"] for row in timeline]
    peak_animals = {animal: max((row.get("animals", {}).get(animal, 0) for row in daily_counts), default=0) for animal in ANIMALS}
    peak_crops = {crop: max((row.get("crops", {}).get(crop, 0) for row in daily_counts), default=0) for crop in CROPS}
    terminal_obs = replay["steps"][-1][player]["observation"]
    terminal_inventory = plain(_inventory(terminal_obs))
    total_revenue = sum(sale_revenue.values())
    opponent_sale_quantity, opponent_sale_revenue = Counter(), Counter()
    for opponent_row in opponent_timeline:
        opponent_sale_quantity.update(opponent_row["sales"])
        opponent_sale_revenue.update(opponent_row["sale_revenue"])
    market_impacts = defaultdict(list)
    overlap_events = Counter()
    for event in sale_events:
        step = event["step"]
        item = event["product"]
        before_obs = replay["steps"][step][player]["observation"]
        after_obs = replay["steps"][min(step + 1, 719)][player]["observation"]
        before_price = float(before_obs["market"]["prices"].get(item, 0))
        after_price = float(after_obs["market"]["prices"].get(item, 0))
        before_inventory = float(before_obs["market"]["inventory"].get(item, 0))
        after_inventory = float(after_obs["market"]["inventory"].get(item, 0))
        opponent_action = normalized_action(replay, other, step)
        opponent_same_turn = sum(
            int(order[2]) for order in opponent_action["market"]
            if order and order[0] == "SELL" and order[1] == item
        )
        overlap_events[item] += int(opponent_same_turn > 0)
        market_impacts[item].append({
            "step": step, "own_requested_or_executed_quantity": event["quantity"],
            "opponent_same_turn_requested_quantity": opponent_same_turn,
            "price_before": before_price, "price_after": after_price,
            "price_delta": after_price - before_price,
            "inventory_before": before_inventory, "inventory_after": after_inventory,
            "inventory_delta": after_inventory - before_inventory,
        })
    holds = {}
    for item in PRODUCTS:
        harvested = sum(row["day"] * row["harvests"].get(item, 0) for row in timeline)
        harvested_n = sum(row["harvests"].get(item, 0) for row in timeline)
        sold = sum(row["day"] * row["sales"].get(item, 0) for row in timeline)
        sold_n = sum(row["sales"].get(item, 0) for row in timeline)
        holds[item] = {
            "weighted_harvest_day": harvested / harvested_n if harvested_n else None,
            "weighted_sale_day": sold / sold_n if sold_n else None,
            "weighted_hold_days": sold / sold_n - harvested / harvested_n if sold_n and harvested_n else None,
        }
    return {
        "episode_id": meta["episode_id"], "seed": int(replay["info"]["seed"]),
        "seat": player, "opponent": replay["info"]["TeamNames"][other],
        "final_money": float(replay["steps"][-1][player]["reward"]),
        "opponent_money": float(replay["steps"][-1][other]["reward"]),
        "advantage": float(replay["steps"][-1][player]["reward"] - replay["steps"][-1][other]["reward"]),
        "action_hash": sha(actions), "land_steps": land_steps,
        "hire_steps": hire_steps, "animal_purchase_events": animal_events,
        "max_hands": max((row.get("hands", 0) for row in daily_counts), default=0),
        "peak_animals": peak_animals, "peak_crops": peak_crops,
        "max_productive": max((row.get("productive", 0) for row in daily_counts), default=0),
        "sale_quantity": plain(sale_quantity), "sale_revenue": plain(sale_revenue),
        "average_realized_price": {item: sale_revenue[item] / sale_quantity[item] for item in sale_quantity if sale_quantity[item]},
        "total_sale_revenue": total_revenue, "harvests": plain(harvests),
        "seed_purchases": plain(seeds), "seed_spending": plain(seed_spend),
        "feed_purchases": plain(feed), "feed_spending": plain(feed_spend),
        "animal_purchases": plain(animals), "animal_spending": plain(animal_spend),
        "land_spending": sum(row["land_spending"] for row in timeline),
        "labor_spending": sum(row["labor_spending"] for row in timeline),
        "sale_events": sale_events, "holding": holds,
        "opponent_sale_quantity": plain(opponent_sale_quantity),
        "opponent_sale_revenue": plain(opponent_sale_revenue),
        "market_impacts": {item: values for item, values in sorted(market_impacts.items())},
        "same_turn_sale_overlap_events": plain(overlap_events),
        "daily": timeline, "features": features, "forensics": forensics,
        "terminal_inventory": terminal_inventory,
        "last_plant_step": forensics["last_plant_step"],
        "last_harvest_step": forensics["last_harvest_step"],
    }


def aggregate_counter(rows, field):
    keys = sorted({key for row in rows for key in row[field]})
    return {key: mean([row[field].get(key, 0) for row in rows]) for key in keys}


def aggregate_submission(team, rows, rank, submission_id, score):
    money = [row["final_money"] for row in rows]
    advantage = [row["advantage"] for row in rows]
    land_n = max((len(row["land_steps"]) for row in rows), default=0)
    land = {
        str(index + 1): {
            "median_step": median([row["land_steps"][index] for row in rows if len(row["land_steps"]) > index]),
            "range_steps": [
                min(row["land_steps"][index] for row in rows if len(row["land_steps"]) > index),
                max(row["land_steps"][index] for row in rows if len(row["land_steps"]) > index),
            ],
        }
        for index in range(land_n)
    }
    daily = []
    for day in range(30):
        farms = [row["daily"][day]["farm"] for row in rows]
        daily.append({
            "day": day,
            "bank_start_median": median([row["daily"][day]["bank_start"] for row in rows]),
            "bank_end_median": median([row["daily"][day]["bank_end"] for row in rows]),
            "sale_revenue_mean": mean([row["daily"][day]["total_sale_revenue"] for row in rows]),
            "spending_mean": mean([row["daily"][day]["total_spending"] for row in rows]),
            "labor_spending_mean": mean([row["daily"][day]["labor_spending"] for row in rows]),
            "land_spending_mean": mean([row["daily"][day]["land_spending"] for row in rows]),
            "hands_median": median([farm.get("hands", 0) for farm in farms]),
            "quadrants_median": median([farm.get("quadrants", 0) for farm in farms]),
            "productive_median": median([farm.get("productive", 0) for farm in farms]),
            "crops_median": {crop: median([farm.get("crops", {}).get(crop, 0) for farm in farms]) for crop in CROPS},
            "animals_median": {animal: median([farm.get("animals", {}).get(animal, 0) for farm in farms]) for animal in ANIMALS},
            "sales_mean": {item: mean([row["daily"][day]["sales"].get(item, 0) for row in rows]) for item in PRODUCTS},
            "sale_revenue_by_product_mean": {item: mean([row["daily"][day]["sale_revenue"].get(item, 0) for row in rows]) for item in PRODUCTS},
        })
    medoid = min(rows, key=lambda left: sum(
        sum(a == b for a, b in zip(left["action_components"], right["action_components"]))
        * -1 for right in rows
    ))
    commodity = {}
    for item in PRODUCTS:
        quantity = [row["sale_quantity"].get(item, 0) for row in rows]
        revenue = [row["sale_revenue"].get(item, 0) for row in rows]
        first = [min((event["step"] for event in row["sale_events"] if event["product"] == item), default=None) for row in rows]
        last = [max((event["step"] for event in row["sale_events"] if event["product"] == item), default=None) for row in rows]
        commodity[item] = {
            "mean_sold": mean(quantity), "mean_revenue": mean(revenue),
            "mean_realized_price": sum(revenue) / sum(quantity) if sum(quantity) else None,
            "median_first_sale_step": median(first), "median_last_sale_step": median(last),
            "median_hold_days": median([row["holding"][item]["weighted_hold_days"] for row in rows]),
        }
    externality = {}
    for item in PRODUCTS:
        impacts = [impact for row in rows for impact in row["market_impacts"].get(item, [])]
        own_quantity = sum(row["sale_quantity"].get(item, 0) for row in rows)
        opponent_quantity = sum(row["opponent_sale_quantity"].get(item, 0) for row in rows)
        externality[item] = {
            "mean_own_quantity": own_quantity / len(rows),
            "mean_opponent_quantity": opponent_quantity / len(rows),
            "mean_opponent_realized_price": (
                sum(row["opponent_sale_revenue"].get(item, 0) for row in rows) / opponent_quantity
                if opponent_quantity else None
            ),
            "mean_immediate_price_delta_on_own_sale_steps": mean([impact["price_delta"] for impact in impacts]),
            "mean_immediate_inventory_delta_on_own_sale_steps": mean([impact["inventory_delta"] for impact in impacts]),
            "same_turn_opponent_sale_overlap_rate": (
                sum(impact["opponent_same_turn_requested_quantity"] > 0 for impact in impacts) / len(impacts)
                if impacts else None
            ),
            "interpretation": "Observed joint-market response; town consumption and simultaneous opponent orders prevent assigning the full delta causally to our sale.",
        }
    return {
        "rank": rank, "team": team, "submission_id": submission_id, "leaderboard_score": score,
        "episodes": len(rows), "episode_ids": sorted(row["episode_id"] for row in rows),
        "seat_distribution": plain(Counter(row["seat"] for row in rows)),
        "wins": sum(row["advantage"] > 0 for row in rows), "losses": sum(row["advantage"] < 0 for row in rows),
        "money": {"mean": mean(money), "median": median(money), "p10": percentile(money, .10), "p5": percentile(money, .05), "range": [min(money), max(money)]},
        "advantage": {"mean": mean(advantage), "median": median(advantage), "p10": percentile(advantage, .10), "p5": percentile(advantage, .05)},
        "land_purchase_timing": land,
        "max_hands": {"median": median([row["max_hands"] for row in rows]), "range": [min(row["max_hands"] for row in rows), max(row["max_hands"] for row in rows)]},
        "peak_animals": {animal: {"median": median([row["peak_animals"][animal] for row in rows]), "range": [min(row["peak_animals"][animal] for row in rows), max(row["peak_animals"][animal] for row in rows)]} for animal in ANIMALS},
        "peak_crops": {crop: {"median": median([row["peak_crops"][crop] for row in rows]), "range": [min(row["peak_crops"][crop] for row in rows), max(row["peak_crops"][crop] for row in rows)]} for crop in CROPS},
        "max_productive": {"median": median([row["max_productive"] for row in rows]), "range": [min(row["max_productive"] for row in rows), max(row["max_productive"] for row in rows)]},
        "mean_sale_quantity": aggregate_counter(rows, "sale_quantity"),
        "mean_sale_revenue": aggregate_counter(rows, "sale_revenue"),
        "mean_harvests": aggregate_counter(rows, "harvests"),
        "mean_seed_purchases": aggregate_counter(rows, "seed_purchases"),
        "mean_seed_spending": aggregate_counter(rows, "seed_spending"),
        "mean_feed_purchases": aggregate_counter(rows, "feed_purchases"),
        "mean_feed_spending": aggregate_counter(rows, "feed_spending"),
        "mean_animal_purchases": aggregate_counter(rows, "animal_purchases"),
        "mean_animal_spending": aggregate_counter(rows, "animal_spending"),
        "mean_land_spending": mean([row["land_spending"] for row in rows]),
        "mean_labor_spending": mean([row["labor_spending"] for row in rows]),
        "mean_total_sale_revenue": mean([row["total_sale_revenue"] for row in rows]),
        "labor_efficiency_proxy": {
            "revenue_per_peak_hand": mean([row["total_sale_revenue"] / max(1, row["max_hands"]) for row in rows]),
            "revenue_per_labor_coin": mean([row["total_sale_revenue"] / max(1, row["labor_spending"]) for row in rows]),
        },
        "commodity": commodity, "market_externality": externality, "daily": daily,
        "representative": {
            "episode_id": medoid["episode_id"], "seat": medoid["seat"], "action_hash": medoid["action_hash"],
            "cohorts": medoid["forensics"]["cohorts"], "field_actions": medoid["forensics"]["field_actions"],
            "animal_service": medoid["forensics"]["animal_service"], "movement_actions": medoid["forensics"]["movement_actions"],
            "movement_per_harvest_action": medoid["forensics"]["movement_per_harvest_action"],
            "animal_purchase_events": medoid["animal_purchase_events"], "sale_events": medoid["sale_events"],
            "terminal_inventory": medoid["terminal_inventory"], "last_plant_step": medoid["last_plant_step"],
            "last_harvest_step": medoid["last_harvest_step"],
        },
    }


def agreement(rows, lo, hi, component):
    scores = []
    for step in range(lo, hi):
        values = Counter(canonical(row["action_components"][step][component]) for row in rows)
        scores.append(values.most_common(1)[0][1] / len(rows))
    return statistics.fmean(scores)


def variance(values):
    return statistics.pvariance(values) if len(values) > 1 else 0.0


def divergence_map(team, rows):
    per_step = []
    components = ("farmer", "hands", "market", "purchases", "sells", "crop", "animal", "full")
    numeric = [key for key, value in rows[0]["features"][0].items() if isinstance(value, (int, float))]
    for step in range(719):
        agreements = {}
        for component in components:
            values = Counter(canonical(row["action_components"][step][component]) for row in rows)
            agreements[component] = values.most_common(1)[0][1] / len(rows)
        features = {key: [row["features"][step][key] for row in rows] for key in numeric}
        per_step.append({
            "step": step, "day": step // 24, "hour": step % 24,
            "agreement": agreements,
            "variance": {
                "bank": variance(features["own_bank"]),
                "inventory": variance(features["own_inventory_total"]),
                "market": mean([variance(features[key]) for key in numeric if key.startswith("market_")]),
                "opponent_state": mean([variance(features[key]) for key in numeric if key.startswith("opponent_")]),
            },
        })
    divergence = []
    for row in sorted(per_step, key=lambda value: (value["agreement"]["full"], value["step"]))[:60]:
        step = row["step"]
        variants = defaultdict(list)
        for appearance in rows:
            variants[canonical(appearance["action_components"][step]["full"])].append(appearance)
        variant_rows = []
        for action_key, members in sorted(variants.items(), key=lambda item: -len(item[1]))[:4]:
            variant_rows.append({
                "count": len(members), "action": json.loads(action_key),
                "observable_state_medians": {
                    key: median([member["features"][step][key] for member in members])
                    for key in numeric
                },
                "episodes": [member["episode_id"] for member in members],
            })
        divergence.append({**row, "action_variants": variant_rows})
    phase = {
        name: {component: agreement(rows, lo, hi, component) for component in components[:-1]}
        for name, (lo, hi) in PHASE_WINDOWS.items()
    }
    full_mean = mean([row["agreement"]["full"] for row in per_step])
    unique_hashes = len({row["action_hash"] for row in rows})
    duplicate_fraction = 1 - unique_hashes / len(rows)
    if full_mean >= .94:
        classification = "FIXED"
    elif full_mean >= .75 and duplicate_fraction >= .30:
        classification = "BOUNDED_ADAPTIVE"
    elif duplicate_fraction >= .25 or mean([phase[name]["market"] for name in phase]) >= .70:
        classification = "PHASE_ADAPTIVE"
    else:
        classification = "STRONGLY_ADAPTIVE"
    return {
        "team": team, "episodes": len(rows), "unique_action_trajectories": unique_hashes,
        "identical_route_fraction": duplicate_fraction, "classification": classification,
        "component_agreement_by_phase": phase, "per_step": per_step,
        "highest_divergence_observable_branches": divergence,
        "first_any_full_action_divergence": next((row["step"] for row in per_step if row["agreement"]["full"] < 1), None),
        "interpretation_note": "Action variation is descriptive. A branch is considered deployable evidence only after a current-observation trigger and paired causal test; replay id, seed and future state are excluded.",
    }


def markdown_dossier(summary, adaptive):
    rank = summary["rank"]
    lines = [
        f"# Rank {rank} strategy dossier — {summary['team']}", "",
        f"Current submission `{summary['submission_id']}`; public score {summary['leaderboard_score']}; {summary['episodes']} current-version episodes.", "",
        "## Economic thesis", "",
    ]
    if rank == 1:
        lines.append("This economy converts an unusually labor-heavy sheep opening into early wool/fertilizer cash, then spends that cash on two land waves and a diversified wheat/melon/strawberry crop engine. It accepts a later first land purchase than Rank 2, but compensates with earlier labor and much larger wool realization. The result is not a single fixed route: purchase and field timing branch materially with the visible market and opponent state.")
    elif rank == 2:
        lines.append("This economy prioritizes the earliest land schedule of the Top 3, ramps cows quickly, and uses the resulting milk/fertilizer stream to support a fast three-quadrant crop build. Its field and market route is strongly state-dependent after the opening, so the medoid is an economic example rather than a complete reconstruction of the policy.")
    else:
        lines.append("This economy uses a repeatable mixed-animal opening, a day-6 first expansion and a melon-funded day-11 second expansion. Several episodes share an exact action route, but later crop and market phases still branch; it is best described as phase-adaptive rather than fixed.")
    lines += [
        "", "## Outcome and scale", "",
        f"- Final money: mean {summary['money']['mean']:.0f}, median {summary['money']['median']:.0f}, P10 {summary['money']['p10']:.0f}, range {summary['money']['range'][0]:.0f}–{summary['money']['range'][1]:.0f}.",
        f"- Land purchase steps: {summary['land_purchase_timing']}.",
        f"- Peak hands: median {summary['max_hands']['median']}; peak productive tiles: median {summary['max_productive']['median']}.",
        f"- Peak livestock medians: cows {summary['peak_animals']['COW']['median']}, sheep {summary['peak_animals']['SHEEP']['median']}, geese {summary['peak_animals']['GOOSE']['median']}.",
        "", "## Discovered phases", "",
        "| Phase | Objective | Capital and assets | Market exposure / transition |", "|---|---|---|---|",
    ]
    first_land = summary["land_purchase_timing"].get("1", {}).get("median_step")
    second_land = summary["land_purchase_timing"].get("2", {}).get("median_step")
    lines.extend([
        f"| Opening (0–{int(first_land or 120)}) | Build feed plus first premium crop and service initial livestock | Initial seeds, animals and early hands; preserves enough liquidity for land | Early wheat/fertilizer/animal-product sales; transitions when first land is affordable |",
        f"| First reinvestment ({int(first_land or 120)}–{int(second_land or 240)}) | Turn first animal/crop cash into 50-tile capacity | First land, additional animals, larger daily labor | Milk/wool/fertilizer realization funds expansion; transitions on second-land cash |",
        f"| Second reinvestment ({int(second_land or 240)}–336) | Populate three quadrants without starving animal service | Second land, wheat/melon/strawberry cohorts, hand ramp | First large melon/premium wave recycles into seeds and labor |",
        "| Scaled midgame (336–552) | Maintain simultaneous crop cohorts and indefinite animal production | High productive-tile count; recurring feed/care/harvest | Diversified selling reduces dependence on any one glut |",
        "| Late production (552–672) | Finish profitable recurring and short-cycle crops | New planting narrows; existing livestock continues | Premium products are staggered rather than held for the whole season |",
        "| Liquidation (672–719) | Convert all remaining harvestable value to bank | Planting stops, harvesting/shed logistics dominate | Last sales cluster near step 718; terminal inventory is audited |",
    ])
    lines += ["", "## Day-by-day median economy", "", "| Day | Bank end | Revenue | Spend | Q | Hands | Productive | Wheat | Melon | Strawberry | Cows | Sheep |", "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for row in summary["daily"]:
        lines.append(
            f"| {row['day']} | {row['bank_end_median']:.0f} | {row['sale_revenue_mean']:.0f} | {row['spending_mean']:.0f} | {row['quadrants_median']:.0f} | {row['hands_median']:.0f} | {row['productive_median']:.0f} | {row['crops_median']['WHEAT']:.0f} | {row['crops_median']['MELON']:.0f} | {row['crops_median']['STRAWBERRY']:.0f} | {row['animals_median']['COW']:.0f} | {row['animals_median']['SHEEP']:.0f} |"
        )
    lines += ["", "## Commodity and cohort forensics", "", "| Product | Mean sold | Mean revenue | Realized price | First/last sale step | Median hold days |", "|---|---:|---:|---:|---:|---:|"]
    for item, row in summary["commodity"].items():
        lines.append(f"| {item} | {row['mean_sold']:.1f} | {row['mean_revenue']:.0f} | {row['mean_realized_price'] or 0:.1f} | {row['median_first_sale_step']} / {row['median_last_sale_step']} | {row['median_hold_days'] if row['median_hold_days'] is not None else 'n/a'} |")
    lines += [
        "", "The representative cohort ledger below links seed/plant windows to maintenance and harvest. Realized sales cannot be uniquely assigned to a single same-product cohort once inventory is pooled, so cohort-specific prices are deliberately not fabricated.", "",
        "| Cohort | Tiles planted | Plant window | Water | Fertilize | Harvest actions | Harvest units | Worker turns |", "|---|---:|---|---:|---:|---:|---:|---:|",
    ]
    for cohort in summary["representative"]["cohorts"]:
        if cohort["tiles_planted"] or cohort["harvest_steps"]:
            lines.append(f"| {cohort['cohort_id']} | {cohort['tiles_planted']} | {cohort['plant_window']} | {cohort['water_actions']} | {cohort['fertilize_actions']} | {len(cohort['harvest_steps'])} | {cohort['harvest_units']} | {cohort['worker_turns']} |")
    lines += [
        "", "## Labor and livestock economics", "",
        f"Mean labor spend is {summary['mean_labor_spending']:.0f}; revenue/peak-hand proxy is {summary['labor_efficiency_proxy']['revenue_per_peak_hand']:.0f} and revenue/labor-coin is {summary['labor_efficiency_proxy']['revenue_per_labor_coin']:.1f}. These are attribution proxies, not marginal causal estimates.",
        f"Representative animal service actions: `{summary['representative']['animal_service']}`. Mean feed purchases: `{summary['mean_feed_purchases']}`; mean animal purchases: `{summary['mean_animal_purchases']}`.",
        "", "## Fixed versus adaptive", "",
        f"Classification: **{adaptive['classification']}**. It produced {adaptive['unique_action_trajectories']} distinct full routes in {adaptive['episodes']} episodes; exact-route duplicate fraction {adaptive['identical_route_fraction']:.1%}.",
        "The divergence artifact lists per-step component agreement and observable-state medians for the largest branches. These branches remain correlational until replay-compatible local counterfactuals reproduce them.",
        "", "## Endgame and uncertainty", "",
        f"Representative last plant step {summary['representative']['last_plant_step']}, last harvest step {summary['representative']['last_harvest_step']}, terminal inventory `{summary['representative']['terminal_inventory']}`.",
        "Public observations prove what was executed, but cannot expose source-code intent. The economic interpretation is therefore separated from causal claims, and exact cohort-to-sale matching is left uncertain when pooled inventory prevents identification.",
        "",
    ]
    return "\n".join(lines)


def main():
    manifest = json.loads(MANIFEST.read_text())
    selected = {int(row["selected_submission_id"]): row for row in manifest["submissions"]}
    meta_by_episode = defaultdict(list)
    for episode in manifest["episodes"]:
        if not episode["replay_valid"]:
            continue
        for appearance in episode["appearances"]:
            submission_id = int(appearance["submission_id"])
            if submission_id in selected and appearance["is_selected_elite_submission"]:
                meta_by_episode[int(episode["episode_id"])].append({
                    "episode_id": int(episode["episode_id"]), "seat": int(appearance["seat"]),
                    "submission_id": submission_id, "team": appearance["team_name"],
                    "rank": int(appearance["leaderboard_rank"]), "score": float(appearance["leaderboard_score"]),
                    "replay_path": episode["replay_path"],
                })
    grouped = defaultdict(list)
    mismatch_count = 0
    for index, (episode_id, metas) in enumerate(sorted(meta_by_episode.items()), 1):
        replay = json.loads((ROOT / metas[0]["replay_path"]).read_text())
        timelines, mismatches = economic_timelines(replay)
        mismatch_count += len(mismatches)
        for meta in metas:
            player = meta["seat"]
            actions = [normalized_action(replay, player, step) for step in range(719)]
            components = [request_components(action) for action in actions]
            features = [state_features(replay["steps"][step][player]["observation"], player) for step in range(719)]
            forensics = crop_and_worker_forensics(replay, player, actions)
            row = summarize_appearance(meta, replay, timelines[player], timelines[1 - player], actions, features, forensics)
            row["action_components"] = components
            grouped[meta["team"]].append(row)
        if index % 10 == 0:
            print(f"processed {index}/{len(meta_by_episode)} replay files", flush=True)
    summaries, adaptive_rows = [], []
    for submission in sorted(selected.values(), key=lambda row: row["rank"]):
        team = submission["team_name"]
        rows = grouped[team]
        if len(rows) != 30:
            raise RuntimeError(f"expected 30 appearances for {team}, got {len(rows)}")
        adaptive = divergence_map(team, rows)
        adaptive.update({"rank": submission["rank"], "submission_id": submission["selected_submission_id"]})
        adaptive_rows.append(adaptive)
        summaries.append(aggregate_submission(team, rows, submission["rank"], submission["selected_submission_id"], submission["selected_submission_score"]))
    version_audit = {
        "schema_version": 1, "leaderboard_captured_at": manifest["captured_at"],
        "manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
        "selection_rule": manifest["selection_rule"], "corpus_summary": manifest["corpus_summary"],
        "current_versions": [
            {
                "rank": row["rank"], "team": row["team_name"], "team_id": row["team_id"],
                "submission_id": row["selected_submission_id"], "public_score": row["selected_submission_score"],
                "leaderboard_submission_date": row["leaderboard_submission_date"],
                "available_public_episodes": row["available_completed_public_episodes"],
                "analyzed_current_version_appearances": len(grouped[row["team_name"]]),
                "alternate_active_versions_excluded": [item for item in row["active_public_submissions"] if int(item["id"]) != int(row["selected_submission_id"])],
                "attribution": "exact submission id in public episode metadata",
            }
            for row in sorted(selected.values(), key=lambda value: value["rank"])
        ],
        "ambiguous_version_appearances": 0,
        "financial_reconstruction_note": f"{mismatch_count} local/server price-rounding mismatches were reconciled against observed bank deltas; quantities/actions remain replay-derived.",
    }
    write_json(VERSION, version_audit)
    write_json(ADAPTIVE, {"schema_version": 1, "strategies": adaptive_rows})
    baseline = json.loads((EXP / "current_best.json").read_text())
    direct = {
        "schema_version": 1,
        "baseline": {
            "path": baseline["agent_path"], "sha256": baseline["source_sha256"],
            "architecture": "step-1 observable selector over three complete safety-repaired replay parents (Dmitry/Hanserong/redblackbst)",
            "reference_control": {"path": baseline["previous_best_path"], "sha256": baseline["previous_best_sha256"]},
        },
        "top3": summaries,
        "comparison_dimensions": {
            "opening": "all three start mixed livestock plus wheat/melon-capable crops; Rank1 is sheep/fertilizer biased",
            "land": {row["team"]: row["land_purchase_timing"] for row in summaries},
            "hands": {row["team"]: row["max_hands"] for row in summaries},
            "animals": {row["team"]: row["peak_animals"] for row in summaries},
            "crops": {row["team"]: row["peak_crops"] for row in summaries},
            "market": {row["team"]: row["commodity"] for row in summaries},
        },
    }
    write_json(DIRECT, direct)
    shared_behaviors = [
        {
            "behavior": "three-quadrant economy with two early reinvestment waves",
            "evidence": {row["team"]: row["land_purchase_timing"] for row in summaries},
            "baseline": "portfolio parents are also complete multi-quadrant economies",
            "difference": "timing and funding commodity differ; not absent from baseline",
            "status": "OBSERVED_SHARED_NOT_NOVEL",
        },
        {
            "behavior": "mixed cow+sheep livestock rather than cow-only",
            "evidence": {row["team"]: row["peak_animals"] for row in summaries},
            "baseline": "portfolio includes mixed-livestock parents but selection is not explicitly commodity-aware",
            "difference": "Rank1 is substantially more sheep/wool weighted",
            "status": "OBSERVED_SHARED_CANDIDATE",
        },
        {
            "behavior": "wheat/melon/strawberry crop succession with diversified realization",
            "evidence": {row["team"]: row["peak_crops"] for row in summaries},
            "baseline": "same broad crop family exists in all three replay parents",
            "difference": "cohort sizes and timing, not crop vocabulary",
            "status": "OBSERVED_SHARED_NOT_NOVEL",
        },
        {
            "behavior": "twelve-hand ceiling and high field movement budget",
            "evidence": {row["team"]: row["max_hands"] for row in summaries},
            "baseline": "parent-dependent hand ramps, generally similar ceiling",
            "difference": "Rank1 scales six/eight hands earlier",
            "status": "OBSERVED_SHARED_TIMING_HYPOTHESIS",
        },
        {
            "behavior": "near-terminal liquidation instead of season-long premium holding",
            "evidence": {row["team"]: {item: row["commodity"][item] for item in ("MELON", "STRAWBERRY", "MILK", "WOOL")} for row in summaries},
            "baseline": "complete parent routes also liquidate terminally",
            "difference": "Top3 differ in within-season staggering and commodity emphasis",
            "status": "OBSERVED_SHARED_NOT_NOVEL",
        },
        {
            "behavior": "observable-state-dependent field and market branching",
            "evidence": {row["team"]: {"classification": row["classification"], "unique_routes": row["unique_action_trajectories"]} for row in adaptive_rows},
            "baseline": "one step-1 selector followed by a fixed complete route",
            "difference": "Top3 continue branching after expansion; baseline does not",
            "status": "OBSERVED_SHARED_HIGH_PRIORITY_BUT_NOT_YET_CAUSAL",
        },
    ]
    write_json(SHARED, {"schema_version": 1, "behaviors": shared_behaviors})
    top1, top2, top3 = summaries
    rank1_unique = {
        "schema_version": 1, "rank1": top1["team"],
        "observed_differences": [
            {"difference": "much larger sheep/wool/fertilizer economy", "rank1": {"animals": top1["peak_animals"], "wool_revenue": top1["commodity"]["WOOL"]["mean_revenue"], "fertilizer_revenue": top1["commodity"]["FERTILIZER"]["mean_revenue"]}, "rank2": {"animals": top2["peak_animals"], "wool_revenue": top2["commodity"]["WOOL"]["mean_revenue"], "fertilizer_revenue": top2["commodity"]["FERTILIZER"]["mean_revenue"]}, "rank3": {"animals": top3["peak_animals"], "wool_revenue": top3["commodity"]["WOOL"]["mean_revenue"], "fertilizer_revenue": top3["commodity"]["FERTILIZER"]["mean_revenue"]}, "causal_status": "OBSERVED"},
            {"difference": "later first land than Rank2 but earlier six/eight-hand ramp in the representative route", "rank1_land": top1["land_purchase_timing"], "other_land": {top2["team"]: top2["land_purchase_timing"], top3["team"]: top3["land_purchase_timing"]}, "causal_status": "OBSERVED"},
            {"difference": "more diversified carrot/wheat exposure and later melon realization", "rank1_crops": top1["peak_crops"], "other_crops": {top2["team"]: top2["peak_crops"], top3["team"]: top3["peak_crops"]}, "causal_status": "OBSERVED"},
            {"difference": "higher observed mean money, but public-opponent mix is uncontrolled", "money": {row["team"]: row["money"] for row in summaries}, "causal_status": "CORRELATED_NOT_CAUSAL"},
        ],
        "leading_hypothesis": "Rank1 substitutes sheep/wool/fertilizer compounding and earlier labor deployment for part of the cow/milk ramp, creating a broader price footprint and financing later land without depending on a single melon/milk market.",
        "remaining_uncertainty": "Whether this mix causes the rank gap cannot be inferred from public final money because opponent and market paths differ; it requires coherent local route reconstruction and paired tests.",
    }
    write_json(RANK1, rank1_unique)
    core_rows = []
    for summary in summaries:
        core_rows.append({key: value for key, value in summary.items() if key != "daily"})
    write_json(CORE, {"schema_version": 1, "summaries": core_rows, "daily": {row["team"]: row["daily"] for row in summaries}})
    adaptive_by_team = {row["team"]: row for row in adaptive_rows}
    for summary in summaries:
        path = EXP / f"top3_rank{summary['rank']}_strategy_dossier.md"
        path.write_text(markdown_dossier(summary, adaptive_by_team[summary["team"]]))
    print(f"wrote Top3 forensic core for {sum(len(rows) for rows in grouped.values())} appearances; reconciled mismatch events={mismatch_count}")
    for path in (VERSION, ADAPTIVE, DIRECT, SHARED, RANK1, CORE):
        print(path)


if __name__ == "__main__":
    main()
