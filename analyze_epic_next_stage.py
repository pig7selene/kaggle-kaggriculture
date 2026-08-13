"""Hour-level real-loss and top-crop-machine analysis for the epic research stage."""

from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path

from kaggle_environments.envs.kaggriculture import kaggriculture as game

from analyze_crop_lifecycle import lifecycle_metrics
from analyze_post_opening_real_gap import _effect_category, _op, _responsibility
from analyze_top_player_replays import _transition_ledger


ROOT = Path(__file__).resolve().parent
EPIC = ROOT / "experiments" / "epic_replays"
TOP = ROOT / "experiments" / "top_player_replays" / "replays"
TOP_ROUTING = ROOT / "experiments" / "top_player_worker_routing.json"
OUTPUT = ROOT / "experiments" / "epic_next_stage_diagnosis.json"
CROPS = tuple(game.CROPS)
ANIMAL_PRODUCTS = {value["product"] for value in game.ANIMALS.values()} | {"FERTILIZER"}
SHED_TILES = {(4, 4), (5, 4), (4, 5), (5, 5)}
MOVEMENT = {"NORTH", "SOUTH", "EAST", "WEST"}


def _plain(counter):
    return {key: counter[key] for key in sorted(counter) if counter[key]}


def _rate(numerator, denominator):
    return numerator / denominator if denominator else 0.0


def _quadrant(position):
    x, y = position
    return ("N" if y < 5 else "S") + ("W" if x < 5 else "E")


def _distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _snapshot(obs, player):
    farm = obs["farms"][player]
    crops = Counter()
    mature = Counter()
    critical = Counter()
    watered = Counter()
    cohorts = defaultdict(Counter)
    animals = Counter()
    structures = Counter()
    tiles = {}
    productive = 0
    occupied = 0
    for y, row in enumerate(farm["tiles"]):
        for x, tile in enumerate(row):
            if tile in (None, "LOCKED"):
                continue
            occupied += 1
            if not isinstance(tile, dict):
                continue
            kind = tile.get("kind")
            record = {"kind": kind}
            if kind == "PLANT":
                crop = tile["crop"]
                crops[crop] += 1
                productive += 1
                cohorts[crop][int(tile["planted_day"])] += 1
                if tile.get("yield_units", 0) > 0:
                    mature[crop] += 1
                if tile.get("watered_today", False):
                    watered[crop] += 1
                if not tile.get("watered_today", False) and tile.get("consecutive_unwatered", 0) >= 1:
                    critical[crop] += 1
                record.update({
                    "crop": crop,
                    "planted_day": int(tile["planted_day"]),
                    "age": int(obs["day"] - tile["planted_day"]),
                    "yield_units": int(tile.get("yield_units", 0)),
                    "watered": bool(tile.get("watered_today", False)),
                    "unwatered": int(tile.get("consecutive_unwatered", 0)),
                })
            elif kind in {"COOP", "PASTURE"}:
                structures[kind] += 1
                animal = tile.get("animal")
                if animal:
                    animals[animal] += 1
                    productive += 1
                    record.update({
                        "animal": animal,
                        "yield_units": int(tile.get("yield_units", 0)),
                        "fed": bool(tile.get("fed_today", False)),
                        "cared": bool(tile.get("cared_today", False)),
                        "unfed": int(tile.get("consecutive_unfed", 0)),
                        "fertilizer": bool(tile.get("fertilizer_available", False)),
                    })
            tiles[f"{x},{y}"] = record
    return {
        "money": float(farm["money"]),
        "quadrants": len(farm.get("unlocked_quadrants", [])),
        "unlocked_quadrants": list(farm.get("unlocked_quadrants", [])),
        "hands": len(farm.get("hands", [])),
        "workers": [list(farm["farmer"]), *[list(value) for value in farm.get("hands", [])]],
        "productive_tiles": productive,
        "occupied_tiles": occupied,
        "crops": _plain(crops),
        "mature_crops": _plain(mature),
        "critical_crops": _plain(critical),
        "watered_crops": _plain(watered),
        "cohorts": {crop: _plain(values) for crop, values in sorted(cohorts.items())},
        "animals": _plain(animals),
        "structures": _plain(structures),
        "tiles": tiles,
    }


def _inventory_snapshot(state):
    private = state["observation"]["private"]
    carried = Counter()
    for inventory in private["inventories"]:
        carried.update(inventory)
    return {
        "shed": {key: value for key, value in sorted(private["shed"].items()) if value},
        "seeds": {key: value for key, value in sorted(private["seeds"].items()) if value},
        "carried": _plain(carried),
        "unit_inventories": [
            {key: value for key, value in sorted(inventory.items()) if value}
            for inventory in private["inventories"]
        ],
    }


def _action_effects(previous_states, current_states, player, configuration):
    obs = previous_states[0]["observation"]
    farm = deepcopy(obs["farms"][player])
    private = deepcopy(previous_states[player]["observation"]["private"])
    action = current_states[player].get("action") or {}
    unit_actions = [action.get("farmer", ["PASS"]), *action.get("hands", [])]
    unit_count = 1 + len(farm.get("hands", []))
    unit_actions += [["PASS"]] * max(0, unit_count - len(unit_actions))
    unit_actions = unit_actions[:unit_count]
    counts = Counter()
    ops = Counter()
    responsibility = Counter()
    events = []
    records = []
    board_size = int(configuration.get("boardSize", 10))
    turns_per_day = int(configuration.get("turnsPerDay", 24))
    shed_capacity = int(configuration.get("shedCapacity", 100))
    for unit_index, unit_action in enumerate(unit_actions):
        position = tuple(farm["farmer"] if unit_index == 0 else farm["hands"][unit_index - 1])
        inventory = private["inventories"][unit_index]
        before_inventory = dict(inventory)
        before_tile = deepcopy(farm["tiles"][position[1]][position[0]])
        op = _op(unit_action)
        game._apply_unit_action(
            farm, private, unit_index, unit_action, board_size,
            int(obs["day"]), turns_per_day, shed_capacity,
        )
        after_position = tuple(farm["farmer"] if unit_index == 0 else farm["hands"][unit_index - 1])
        after_tile = deepcopy(farm["tiles"][position[1]][position[0]])
        after_inventory = dict(private["inventories"][unit_index])
        category = _effect_category(
            op, before_tile, before_inventory, after_tile, after_inventory,
            position, after_position,
        )
        role = _responsibility(op, before_tile, after_tile) if category == "productive" else "none"
        counts[category] += 1
        ops[op] += 1
        responsibility[role] += category == "productive"
        item = None
        age = None
        if isinstance(before_tile, dict) and before_tile.get("kind") == "PLANT":
            item = before_tile.get("crop")
            age = int(obs["day"] - before_tile.get("planted_day", obs["day"]))
        elif isinstance(after_tile, dict) and after_tile.get("kind") == "PLANT":
            item = after_tile.get("crop")
            age = 0
        elif isinstance(before_tile, dict) and before_tile.get("animal"):
            item = before_tile.get("animal")
        if category == "productive":
            events.append({
                "unit": unit_index, "op": op, "position": list(position),
                "item": item, "age": age,
                "inventory_delta": {
                    key: after_inventory.get(key, 0) - before_inventory.get(key, 0)
                    for key in set(before_inventory) | set(after_inventory)
                    if after_inventory.get(key, 0) != before_inventory.get(key, 0)
                },
            })
        records.append({
            "unit": unit_index,
            "position": list(position),
            "after_position": list(after_position),
            "action": unit_action,
            "op": op,
            "category": category,
            "responsibility": role,
            "loaded": sum(before_inventory.values()) > 0,
            "quadrant_before": _quadrant(position),
            "quadrant_after": _quadrant(after_position),
        })
    return {
        "counts": _plain(counts),
        "ops": _plain(ops),
        "responsibility": _plain(responsibility),
        "events": events,
        "unit_records": records,
    }


def _spatial_stats(positions):
    positions = set(positions)
    if not positions:
        return {"tiles": 0, "components": 0, "largest_component_fraction": None, "adjacency_per_tile": None}
    remaining = set(positions)
    components = []
    while remaining:
        stack = [remaining.pop()]
        size = 0
        while stack:
            x, y = stack.pop()
            size += 1
            for neighbor in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    stack.append(neighbor)
        components.append(size)
    adjacency = sum(
        (x + 1, y) in positions or (x, y + 1) in positions
        for x, y in positions
    )
    return {
        "tiles": len(positions),
        "components": len(components),
        "largest_component_fraction": max(components) / len(positions),
        "adjacency_per_tile": adjacency / len(positions),
    }


def _is_actionable(tile, op, day):
    if op == "HARVEST":
        return isinstance(tile, dict) and tile.get("yield_units", 0) > 0
    if op == "WATER":
        return isinstance(tile, dict) and tile.get("kind") == "PLANT" and not tile.get("watered_today", False)
    if op == "PLANT":
        return tile is None
    return True


def analyze_appearance(replay, player, include_hourly=False):
    steps = replay["steps"]
    config = replay.get("configuration", {})
    start_day, end_day = 6, 29
    cumulative_revenue = Counter()
    cumulative_spending = Counter()
    totals = Counter()
    ops = Counter()
    responsibilities = Counter()
    harvest_by_crop = Counter()
    harvest_steps = []
    plant_positions = defaultdict(list)
    plant_hours = defaultdict(list)
    crop_events = []
    action_records = {}
    hourly = []
    daily_last = {}
    previous_quadrant = {}
    quadrant_crossings = 0
    shed_entries = 0
    loaded_shed_moves = 0
    seed_buy_events = 0
    market_events = []
    bank_mismatches = []

    for index in range(1, len(steps)):
        previous_states = steps[index - 1]
        current_states = steps[index]
        obs = previous_states[0]["observation"]
        day = int(obs["day"])
        hour = int(obs["hour"])
        step = int(obs["step"])
        ledgers, errors = _transition_ledger(previous_states, current_states, config)
        bank_mismatches.extend(errors)
        ledger = ledgers[player]
        revenue = Counter(ledger["sale_revenue"])
        spending = Counter()
        spending["seed"] = sum(ledger["seed_spend"].values())
        spending["feed"] = sum(ledger["product_spend"].values())
        spending["animal"] = sum(ledger["animal_spend"].values())
        spending["land"] = ledger["land_spend"]
        spending["labor"] = ledger["labor_spend"]
        cumulative_revenue.update(revenue)
        cumulative_spending.update(spending)
        effects = _action_effects(previous_states, current_states, player, config)
        for key, value in effects["counts"].items():
            totals[key] += value
        for key, value in effects["ops"].items():
            ops[key] += value
        for key, value in effects["responsibility"].items():
            responsibilities[key] += value
        for record in effects["unit_records"]:
            action_records[(step, record["unit"])] = record
            if record["quadrant_before"] != record["quadrant_after"]:
                quadrant_crossings += 1
            if tuple(record["after_position"]) in SHED_TILES and tuple(record["position"]) not in SHED_TILES:
                shed_entries += 1
            if record["category"] == "movement" and record["loaded"]:
                before = min(_distance(record["position"], value) for value in SHED_TILES)
                after = min(_distance(record["after_position"], value) for value in SHED_TILES)
                if after < before:
                    loaded_shed_moves += 1
        for event in effects["events"]:
            event = {"step": step, "day": day, "hour": hour, **event}
            if event["op"] in {"HARVEST", "WATER", "PLANT"} and event["item"] in CROPS:
                crop_events.append(event)
            if event["op"] == "HARVEST" and event["item"] in CROPS:
                harvest_by_crop[event["item"]] += 1
                harvest_steps.append(step)
            if event["op"] == "PLANT" and event["item"] in CROPS:
                key = (day, event["item"])
                plant_positions[key].append(tuple(event["position"]))
                plant_hours[key].append(hour)
        action = current_states[player].get("action") or {}
        for order in action.get("market", []):
            if order[0] == "BUY_SEED":
                seed_buy_events += 1
            if order[0] in {"BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL", "HIRE", "BUY_LAND"}:
                market_events.append({"step": step, "day": day, "hour": hour, "order": order})

        if start_day <= day <= end_day:
            snapshot = _snapshot(obs, player)
            row = {
                "step": step, "day": day, "hour": hour,
                "bank": snapshot["money"],
                "cumulative_revenue": sum(cumulative_revenue.values()),
                "cumulative_crop_revenue": sum(cumulative_revenue[crop] for crop in CROPS),
                "cumulative_animal_revenue": sum(cumulative_revenue[item] for item in ANIMAL_PRODUCTS),
                "cumulative_spending": sum(cumulative_spending.values()),
                "revenue_this_hour": _plain(revenue),
                "spending_this_hour": _plain(spending),
                "farm": snapshot,
                "inventory": _inventory_snapshot(previous_states[player]),
                "effects": effects,
                "market_orders": action.get("market", []),
                "market_prices": dict(obs["market"]["prices"]),
                "market_inventory": dict(obs["market"]["inventory"]),
                "town_shops": list(obs["town"]["unlocked_shops"]),
            }
            daily_last[day] = row
            if include_hourly:
                hourly.append(row)

    # Estimate predictive pre-positioning by looking up to three turns before
    # each productive crop action by the same same-day worker index.
    predictive = 0
    approached = 0
    eligible = 0
    for event in crop_events:
        if event["op"] not in {"HARVEST", "WATER", "PLANT"}:
            continue
        target = tuple(event["position"])
        eligible += 1
        event_approached = False
        event_predictive = False
        for prior_step in range(max(event["day"] * 24, event["step"] - 3), event["step"]):
            record = action_records.get((prior_step, event["unit"]))
            if not record or record["category"] != "movement":
                continue
            if _distance(record["after_position"], target) >= _distance(record["position"], target):
                continue
            event_approached = True
            prior_obs = steps[prior_step][0]["observation"]
            tile = prior_obs["farms"][player]["tiles"][target[1]][target[0]]
            if not _is_actionable(tile, event["op"], int(prior_obs["day"])):
                event_predictive = True
        approached += event_approached
        predictive += event_predictive

    cohort_rows = []
    for (day, crop), positions in sorted(plant_positions.items()):
        spatial = _spatial_stats(positions)
        hours = plant_hours[(day, crop)]
        cohort_rows.append({
            "day": day, "crop": crop, "planted": len(positions),
            "first_hour": min(hours), "last_hour": max(hours),
            "hour_span": max(hours) - min(hours), **spatial,
        })
    harvest_gaps = [right - left for left, right in zip(harvest_steps, harvest_steps[1:])]
    harvest_waves = Counter(harvest_steps)
    final_state = steps[-1][player]
    final_money = float(final_state.get("reward", 0))
    lifecycle_10_20 = lifecycle_metrics(replay, player, 10, 20)
    lifecycle_20_29 = lifecycle_metrics(replay, player, 20, 29)
    return {
        "player": player,
        "final_money": final_money,
        "bank_mismatches": bank_mismatches,
        "daily": [
            {key: value for key, value in row.items() if key != "effects"}
            for _, row in sorted(daily_last.items())
        ],
        "hourly": hourly,
        "totals": _plain(totals),
        "ops": _plain(ops),
        "responsibilities": _plain(responsibilities),
        "harvest_by_crop": _plain(harvest_by_crop),
        "harvest_cadence": {
            "events": len(harvest_steps),
            "mean_gap_turns": statistics.fmean(harvest_gaps) if harvest_gaps else None,
            "median_gap_turns": statistics.median(harvest_gaps) if harvest_gaps else None,
            "mean_wave_size": statistics.fmean(harvest_waves.values()) if harvest_waves else None,
            "max_wave_size": max(harvest_waves.values()) if harvest_waves else 0,
        },
        "cohorts": cohort_rows,
        "prepositioning": {
            "eligible_crop_actions": eligible,
            "approached_within_3_turns": approached,
            "predictive_before_task_actionable": predictive,
            "approach_rate": _rate(approached, eligible),
            "predictive_rate": _rate(predictive, eligible),
        },
        "logistics": {
            "logistics_actions": totals["logistics"],
            "loaded_shed_moves": loaded_shed_moves,
            "shed_entries": shed_entries,
            "seed_market_order_events": seed_buy_events,
            "seed_retrieval_trips": 0,
            "quadrant_crossings": quadrant_crossings,
            "logistics_tax_rate": _rate(totals["logistics"] + loaded_shed_moves, sum(totals.values())),
        },
        "economics": {
            "revenue": _plain(cumulative_revenue),
            "spending": _plain(cumulative_spending),
            "crop_revenue": sum(cumulative_revenue[crop] for crop in CROPS),
            "animal_revenue": sum(cumulative_revenue[item] for item in ANIMAL_PRODUCTS),
            "crop_revenue_per_crop_action": _rate(
                sum(cumulative_revenue[crop] for crop in CROPS), responsibilities["crop"]
            ),
            "animal_revenue_per_animal_action": _rate(
                sum(cumulative_revenue[item] for item in ANIMAL_PRODUCTS), responsibilities["animal"]
            ),
            "final_money_per_worker_turn": _rate(final_money, sum(totals.values())),
        },
        "lifecycle_10_20": lifecycle_10_20,
        "lifecycle_20_29": lifecycle_20_29,
        "market_events": market_events,
    }


def _first_durable(rows, key, threshold=0):
    for index, row in enumerate(rows):
        if row[key] <= threshold:
            continue
        if all(later[key] > threshold for later in rows[index:]):
            return {"step": row["step"], "day": row["day"], "hour": row["hour"], "gap": row[key]}
    return None


def _loss_comparison(replay, ours, opponent):
    left = {row["step"]: row for row in ours["hourly"]}
    right = {row["step"]: row for row in opponent["hourly"]}
    gaps = []
    for step in sorted(set(left) & set(right)):
        our = left[step]
        rival = right[step]
        gaps.append({
            "step": step, "day": our["day"], "hour": our["hour"],
            "bank_gap": rival["bank"] - our["bank"],
            "revenue_gap": rival["cumulative_revenue"] - our["cumulative_revenue"],
            "crop_revenue_gap": rival["cumulative_crop_revenue"] - our["cumulative_crop_revenue"],
            "animal_revenue_gap": rival["cumulative_animal_revenue"] - our["cumulative_animal_revenue"],
            "spending_gap": rival["cumulative_spending"] - our["cumulative_spending"],
            "productive_gap": rival["farm"]["productive_tiles"] - our["farm"]["productive_tiles"],
            "hands_gap": rival["farm"]["hands"] - our["farm"]["hands"],
            "mature_gap": sum(rival["farm"]["mature_crops"].values()) - sum(our["farm"]["mature_crops"].values()),
        })
    return {
        "first_durable_bank_lead": _first_durable(gaps, "bank_gap"),
        "first_durable_revenue_lead": _first_durable(gaps, "revenue_gap"),
        "first_durable_2500_revenue_lead": _first_durable(gaps, "revenue_gap", 2500),
        "first_durable_crop_revenue_lead": _first_durable(gaps, "crop_revenue_gap"),
        "hourly_gaps": gaps,
    }


def _average_maps(appearances, daily_key, nested_key=None):
    days = defaultdict(lambda: defaultdict(list))
    for appearance in appearances:
        for row in appearance["daily"]:
            source = row[daily_key]
            if nested_key:
                source = source[nested_key]
            for key in set(CROPS) | set(source):
                days[row["day"]][key].append(source.get(key, 0))
    return {
        str(day): {key: statistics.fmean(values) for key, values in sorted(items.items())}
        for day, items in sorted(days.items())
    }


def _aggregate(appearances):
    def avg(path):
        values = []
        for item in appearances:
            value = item
            for key in path:
                value = value[key]
            if value is not None:
                values.append(value)
        return statistics.fmean(values) if values else None

    crop_totals = Counter()
    for item in appearances:
        crop_totals.update(item["harvest_by_crop"])
    cohort_sizes = [row["planted"] for item in appearances for row in item["cohorts"] if row["day"] >= 10]
    cohort_spans = [row["hour_span"] for item in appearances for row in item["cohorts"] if row["day"] >= 10]
    contiguous = [row["largest_component_fraction"] for item in appearances for row in item["cohorts"] if row["day"] >= 10 and row["largest_component_fraction"] is not None]
    return {
        "appearances": len(appearances),
        "daily_crop_tiles": _average_maps(appearances, "farm", "crops"),
        "average_final_money": statistics.fmean(item["final_money"] for item in appearances),
        "average_harvest_by_crop": {crop: crop_totals[crop] / len(appearances) for crop in CROPS},
        "average_crop_harvests_day10_20": avg(("lifecycle_10_20", "total_harvest_actions")),
        "average_all_harvests": avg(("harvest_cadence", "events")),
        "average_harvest_gap_turns": avg(("harvest_cadence", "mean_gap_turns")),
        "average_harvest_wave_size": avg(("harvest_cadence", "mean_wave_size")),
        "average_critical_miss_day10_20": avg(("lifecycle_10_20", "critical_watering_miss_rate")),
        "average_harvest_delay_day10_20": avg(("lifecycle_10_20", "average_harvest_delay_turns")),
        "average_replant_delay_day10_20": avg(("lifecycle_10_20", "average_replant_delay_turns")),
        "average_movement_per_cycle_day10_20": avg(("lifecycle_10_20", "movement_per_crop_cycle")),
        "average_predictive_preposition_rate": avg(("prepositioning", "predictive_rate")),
        "average_approach_rate": avg(("prepositioning", "approach_rate")),
        "average_logistics_tax_rate": avg(("logistics", "logistics_tax_rate")),
        "average_shed_entries": avg(("logistics", "shed_entries")),
        "average_loaded_shed_moves": avg(("logistics", "loaded_shed_moves")),
        "average_quadrant_crossings": avg(("logistics", "quadrant_crossings")),
        "average_crop_revenue": avg(("economics", "crop_revenue")),
        "average_animal_revenue": avg(("economics", "animal_revenue")),
        "average_crop_revenue_per_crop_action": avg(("economics", "crop_revenue_per_crop_action")),
        "average_animal_revenue_per_animal_action": avg(("economics", "animal_revenue_per_animal_action")),
        "average_money_per_worker_turn": avg(("economics", "final_money_per_worker_turn")),
        "cohorts_day10_plus": {
            "median_batch_size": statistics.median(cohort_sizes) if cohort_sizes else None,
            "mean_batch_size": statistics.fmean(cohort_sizes) if cohort_sizes else None,
            "median_planting_hour_span": statistics.median(cohort_spans) if cohort_spans else None,
            "mean_largest_component_fraction": statistics.fmean(contiguous) if contiguous else None,
        },
    }


def main():
    manifest = json.loads((EPIC / "manifest.json").read_text())
    losses = []
    current_appearances = []
    for case in manifest["cases"]:
        replay = json.loads((ROOT / case["replay"]).read_text())
        ours = analyze_appearance(replay, int(case["our_seat"]), include_hourly=True)
        opponent = analyze_appearance(replay, int(case["opponent_seat"]), include_hourly=True)
        comparison = _loss_comparison(replay, ours, opponent)
        losses.append({"case": case, "ours": ours, "opponent": opponent, "comparison": comparison})
        current_appearances.append(ours)

    selected = json.loads(TOP_ROUTING.read_text())["appearances"]
    top_appearances = []
    for row in selected:
        replay = json.loads((TOP / f"episode-{row['episode_id']}-replay.json").read_text())
        appearance = analyze_appearance(replay, int(row["player_index"]), include_hourly=False)
        appearance["episode_id"] = int(row["episode_id"])
        appearance["team"] = row["team_name"]
        top_appearances.append(appearance)

    payload = {
        "schema_version": 1,
        "definitions": {
            "predictive_preposition": "within three same-day turns, worker moved closer before the future target action was yet actionable",
            "logistics_tax": "explicit logistics actions plus loaded moves toward a shed, divided by all unit actions",
            "seed_retrieval_trips": "always zero because Kaggriculture seeds are global private inventory, not worker-carried items",
        },
        "losses": losses,
        "current_aggregate": _aggregate(current_appearances),
        "top_aggregate": _aggregate(top_appearances),
        "top_appearances": top_appearances,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(OUTPUT)
    print(json.dumps({
        "losses": [
            {
                "opponent": row["case"]["opponent"],
                "final": [row["ours"]["final_money"], row["opponent"]["final_money"]],
                "firsts": {key: value for key, value in row["comparison"].items() if key != "hourly_gaps"},
            }
            for row in losses
        ],
        "current": payload["current_aggregate"],
        "top": payload["top_aggregate"],
    }, indent=2))


if __name__ == "__main__":
    main()
