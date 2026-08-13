"""Short-horizon watering-debt audit for local and public replays."""

from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path

from kaggle_environments.envs.kaggriculture import kaggriculture as game

from analyze_post_opening_real_gap import _effect_category, _op, _responsibility


ROOT = Path(__file__).resolve().parent
EPIC = ROOT / "experiments" / "epic_replays"
TOP = ROOT / "experiments" / "top_player_replays" / "replays"
TOP_SELECTION = ROOT / "experiments" / "top_player_worker_routing.json"
OUTPUT = ROOT / "experiments" / "predictive_watering_diagnosis.json"
MOVEMENT = {"NORTH", "SOUTH", "EAST", "WEST"}
ONE_TIME = {crop for crop, data in game.CROPS.items() if not data.get("ongoing")}


def _is_plant(tile):
    return isinstance(tile, dict) and tile.get("kind") == "PLANT"


def _quadrant(position):
    x, y = position
    return ("N" if y < 5 else "S") + ("W" if x < 5 else "E")


def _percentile(values, fraction):
    values = sorted(values)
    if not values:
        return None
    point = fraction * (len(values) - 1)
    lo = int(point)
    hi = min(lo + 1, len(values) - 1)
    weight = point - lo
    return values[lo] * (1 - weight) + values[hi] * weight


def _risk_value(obs, tile):
    """Conservative visible crop value protected by one survival watering."""

    crop = tile["crop"]
    data = game.CROPS[crop]
    price = max(1, int(obs["market"]["prices"].get(crop, 1)))
    age = int(obs["day"]) - int(tile.get("planted_day", obs["day"]))
    held = max(0, int(tile.get("yield_units", 0)))
    if data.get("ongoing"):
        first = int(data["first_yield_day"])
        interval = max(1, int(data["interval"]))
        produced = max(0, (age - first) // interval + 1) if age >= first else 0
        remaining = max(0, int(data["max_yield"]) - produced)
        future = remaining * price
    else:
        future = max(held, int(data["max_yield"])) * price
    return int(data["seed"]) + held * price + future


def _harvest_ready(obs, tile):
    if not _is_plant(tile) or tile.get("yield_units", 0) <= 0:
        return False
    data = game.CROPS[tile["crop"]]
    age = int(obs["day"]) - int(tile.get("planted_day", obs["day"]))
    return bool(data.get("ongoing")) or age >= int(data["max_yield_day"])


def watering_metrics(replay, player, start_day=10, end_day=25):
    """Replay submitted actions and measure water pressure/action outcomes."""

    steps = replay["steps"]
    config = replay.get("configuration", {})
    board_size = int(config.get("boardSize", 10))
    turns_per_day = int(config.get("turnsPerDay", 24))
    shed_capacity = int(config.get("shedCapacity", 100))
    snapshots = 0
    debt_values = []
    debt_actions = []
    near_counts = []
    critical_counts = []
    backlog_counts = []
    by_quadrant = defaultdict(Counter)
    actions = Counter()
    water_by_crop = Counter()
    emergency_by_crop = Counter()
    inherited_emergency_by_crop = Counter()
    planting_day_water_by_crop = Counter()
    proactive_by_crop = Counter()
    water_travel = []
    movement_buffer = defaultdict(int)
    cohort_current = defaultdict(int)
    cohorts = []
    last_water_step = {}
    water_before_harvest = 0
    harvests = 0
    plant_checks_end_day = 0
    critical_misses_end_day = 0
    daily = defaultdict(Counter)
    previous_day = None

    def finish_cohort(key):
        if cohort_current.get(key, 0):
            cohorts.append(cohort_current.pop(key))

    for index in range(1, len(steps)):
        previous, current = steps[index - 1], steps[index]
        obs = previous[0]["observation"]
        day = int(obs.get("day", (index - 1) // turns_per_day))
        hour = int(obs.get("hour", (index - 1) % turns_per_day))
        if not start_day <= day <= end_day:
            continue
        if previous_day is not None and day != previous_day:
            for key in list(cohort_current):
                finish_cohort(key)
            movement_buffer.clear()
        previous_day = day
        farm = deepcopy(obs["farms"][player])
        private = deepcopy(previous[player]["observation"]["private"])

        critical = near = backlog = 0
        critical_value = near_value = 0
        for y, row in enumerate(farm["tiles"]):
            for x, tile in enumerate(row):
                if not _is_plant(tile):
                    continue
                quadrant = _quadrant((x, y))
                if _harvest_ready(obs, tile):
                    backlog += 1
                    by_quadrant[quadrant]["harvest_backlog_turns"] += 1
                if tile.get("watered_today", False):
                    by_quadrant[quadrant]["safe_turns"] += 1
                    continue
                value = _risk_value(obs, tile)
                if int(tile.get("consecutive_unwatered", 0)) >= 1:
                    critical += 1
                    critical_value += value
                    by_quadrant[quadrant]["critical_turns"] += 1
                    by_quadrant[quadrant]["critical_value_turns"] += value
                else:
                    near += 1
                    near_value += value
                    by_quadrant[quadrant]["near_critical_turns"] += 1
                    by_quadrant[quadrant]["near_value_turns"] += value
        urgency = (hour + 1) / turns_per_day
        debt_actions.append(critical + near * urgency)
        debt_values.append(critical_value + near_value * urgency)
        critical_counts.append(critical)
        near_counts.append(near)
        backlog_counts.append(backlog)
        daily[day]["debt_action_turns"] += debt_actions[-1]
        daily[day]["debt_value_turns"] += debt_values[-1]
        daily[day]["critical_crop_turns"] += critical
        daily[day]["near_critical_crop_turns"] += near
        daily[day]["harvest_backlog_turns"] += backlog
        snapshots += 1

        submitted = current[player].get("action") or {}
        unit_actions = [submitted.get("farmer", ["PASS"]), *submitted.get("hands", [])]
        unit_count = 1 + len(farm.get("hands", []))
        unit_actions += [["PASS"]] * max(0, unit_count - len(unit_actions))
        unit_actions = unit_actions[:unit_count]
        plant_demand = Counter(
            action[1] for action in unit_actions
            if isinstance(action, list) and len(action) >= 2 and action[0] == "PLANT"
        )
        blocked = {
            crop for crop, count in plant_demand.items()
            if count > private.get("seeds", {}).get(crop, 0)
        }
        for unit, original in enumerate(unit_actions):
            action = original
            if (
                isinstance(original, list) and len(original) >= 2
                and original[0] == "PLANT" and original[1] in blocked
            ):
                action = ["PASS"]
            key = (day, unit)
            position = tuple(farm["farmer"] if unit == 0 else farm["hands"][unit - 1])
            inventory = dict(private["inventories"][unit])
            tile = deepcopy(farm["tiles"][position[1]][position[0]])
            op = _op(action)
            game._apply_unit_action(
                farm, private, unit, action, board_size, day,
                turns_per_day, shed_capacity,
            )
            after_position = tuple(farm["farmer"] if unit == 0 else farm["hands"][unit - 1])
            after_inventory = dict(private["inventories"][unit])
            after_tile = deepcopy(farm["tiles"][position[1]][position[0]])
            category = _effect_category(
                op, tile, inventory, after_tile, after_inventory,
                position, after_position,
            )
            if category == "movement":
                actions["movement"] += 1
                movement_buffer[key] += 1
                if _quadrant(position) != _quadrant(after_position):
                    actions["territory_crossing"] += 1
                continue
            if category == "productive":
                actions["productive"] += 1
                responsibility = _responsibility(op, tile, after_tile)
                actions[f"{responsibility}_productive"] += 1
                if op == "WATER" and _is_plant(tile):
                    crop = tile["crop"]
                    emergency = int(tile.get("consecutive_unwatered", 0)) >= 1
                    planting_day = int(tile.get("planted_day", day)) == day
                    actions["water"] += 1
                    water_by_crop[crop] += 1
                    bucket = emergency_by_crop if emergency else proactive_by_crop
                    bucket[crop] += 1
                    if emergency and planting_day:
                        planting_day_water_by_crop[crop] += 1
                        actions["planting_day_water"] += 1
                    elif emergency:
                        inherited_emergency_by_crop[crop] += 1
                        actions["inherited_emergency_water"] += 1
                    actions["emergency_water" if emergency else "proactive_water"] += 1
                    water_travel.append(movement_buffer.pop(key, 0))
                    cohort_current[key] += 1
                    last_water_step[_quadrant(position)] = int(obs.get("step", index - 1))
                else:
                    finish_cohort(key)
                    movement_buffer[key] = 0
                if op == "HARVEST" and _is_plant(tile):
                    harvests += 1
                    actions["crop_harvest"] += 1
                    if int(obs.get("step", index - 1)) - last_water_step.get(_quadrant(position), -999) <= 6:
                        water_before_harvest += 1
            elif op == "PASS":
                actions["pass"] += 1
            else:
                actions["invalid"] += 1

        if hour == turns_per_day - 1:
            for row in farm["tiles"]:
                for tile in row:
                    if not _is_plant(tile):
                        continue
                    plant_checks_end_day += 1
                    if (
                        not tile.get("watered_today", False)
                        and int(tile.get("consecutive_unwatered", 0)) >= 1
                    ):
                        critical_misses_end_day += 1

    for key in list(cohort_current):
        finish_cohort(key)
    return {
        "window": [start_day, end_day],
        "turn_snapshots": snapshots,
        "average_watering_debt_actions": statistics.fmean(debt_actions) if debt_actions else 0,
        "peak_watering_debt_actions": max(debt_actions, default=0),
        "average_watering_debt_value": statistics.fmean(debt_values) if debt_values else 0,
        "peak_watering_debt_value": max(debt_values, default=0),
        "average_near_critical_crops": statistics.fmean(near_counts) if near_counts else 0,
        "peak_near_critical_crops": max(near_counts, default=0),
        "average_critical_crops": statistics.fmean(critical_counts) if critical_counts else 0,
        "peak_critical_crops": max(critical_counts, default=0),
        "average_harvest_backlog": statistics.fmean(backlog_counts) if backlog_counts else 0,
        "peak_harvest_backlog": max(backlog_counts, default=0),
        "critical_watering_miss_rate": critical_misses_end_day / max(1, plant_checks_end_day),
        "critical_watering_misses": critical_misses_end_day,
        "plant_day_checks": plant_checks_end_day,
        "water_actions": actions["water"],
        "emergency_water_actions": actions["emergency_water"],
        "inherited_emergency_water_actions": actions["inherited_emergency_water"],
        "planting_day_water_actions": actions["planting_day_water"],
        "proactive_water_actions": actions["proactive_water"],
        "proactive_water_fraction": actions["proactive_water"] / max(1, actions["water"]),
        "water_actions_by_crop": dict(water_by_crop),
        "emergency_water_by_crop": dict(emergency_by_crop),
        "inherited_emergency_water_by_crop": dict(inherited_emergency_by_crop),
        "planting_day_water_by_crop": dict(planting_day_water_by_crop),
        "proactive_water_by_crop": dict(proactive_by_crop),
        "average_water_travel": statistics.fmean(water_travel) if water_travel else 0,
        "p90_water_travel": _percentile(water_travel, 0.9),
        "watering_movement": sum(water_travel),
        "average_watering_cohort": statistics.fmean(cohorts) if cohorts else 0,
        "p90_watering_cohort": _percentile(cohorts, 0.9),
        "max_watering_cohort": max(cohorts, default=0),
        "water_actions_per_crop_harvest": actions["water"] / max(1, harvests),
        "water_before_harvest_wave_rate": water_before_harvest / max(1, harvests),
        "territory_crossings": actions["territory_crossing"],
        "movement_actions": actions["movement"],
        "productive_actions": actions["productive"],
        "crop_productive_actions": actions["crop_productive"],
        "animal_productive_actions": actions["animal_productive"],
        "crop_harvests": harvests,
        "invalid_actions": actions["invalid"],
        "by_quadrant": {key: dict(value) for key, value in sorted(by_quadrant.items())},
        "daily": {str(day): dict(value) for day, value in sorted(daily.items())},
    }


def _aggregate(rows):
    if not rows:
        return {}
    numeric = [
        "average_watering_debt_actions", "peak_watering_debt_actions",
        "average_watering_debt_value", "peak_watering_debt_value",
        "average_near_critical_crops", "peak_near_critical_crops",
        "average_critical_crops", "peak_critical_crops",
        "average_harvest_backlog", "peak_harvest_backlog",
        "critical_watering_miss_rate", "water_actions",
        "emergency_water_actions", "proactive_water_actions",
        "inherited_emergency_water_actions", "planting_day_water_actions",
        "proactive_water_fraction", "average_water_travel", "p90_water_travel",
        "watering_movement", "average_watering_cohort", "p90_watering_cohort",
        "max_watering_cohort", "water_actions_per_crop_harvest",
        "water_before_harvest_wave_rate", "territory_crossings",
        "movement_actions", "productive_actions", "crop_productive_actions",
        "animal_productive_actions", "crop_harvests", "invalid_actions",
    ]
    return {
        "appearances": len(rows),
        **{key: statistics.fmean(row[key] for row in rows) for key in numeric},
    }


def main():
    current = []
    manifest = json.loads((EPIC / "manifest.json").read_text())
    for case in manifest["cases"]:
        replay = json.loads((ROOT / case["replay"]).read_text())
        metrics = watering_metrics(replay, int(case["our_seat"]))
        current.append({
            "episode_id": int(case["episode_id"]),
            "opponent": case["opponent"],
            "player": int(case["our_seat"]),
            "metrics": metrics,
        })
    top = []
    selection = json.loads(TOP_SELECTION.read_text())["appearances"]
    for appearance in selection:
        replay = json.loads((TOP / f"episode-{appearance['episode_id']}-replay.json").read_text())
        metrics = watering_metrics(replay, int(appearance["player_index"]))
        top.append({
            "episode_id": int(appearance["episode_id"]),
            "team": appearance["team_name"],
            "player": int(appearance["player_index"]),
            "metrics": metrics,
        })
    payload = {
        "schema_version": 1,
        "definitions": {
            "critical": "unwatered now with consecutive_unwatered >= 1; dies at this day end if not serviced",
            "near_critical": "unwatered now with consecutive_unwatered == 0; becomes tomorrow's critical debt if skipped",
            "safe": "already watered today",
            "watering_debt_actions": "critical count + near-critical count * (hour+1)/24",
            "watering_debt_value": "visible crop value at risk with the same urgency weights",
            "proactive_water": "successful watering before the tile is critical",
            "watering_movement": "same-day movement actions since that worker's previous productive action and ending in WATER",
            "watering_cohort": "consecutive successful WATER actions by one worker, allowing movement but no intervening productive action"
        },
        "current_appearances": current,
        "current_aggregate": _aggregate([row["metrics"] for row in current]),
        "top_appearances": top,
        "top_aggregate": _aggregate([row["metrics"] for row in top]),
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(OUTPUT)
    print(json.dumps({
        "current": payload["current_aggregate"],
        "top": payload["top_aggregate"],
    }, indent=2))


if __name__ == "__main__":
    main()
