"""Action-level crop lifecycle metrics for Kaggriculture replay JSON objects."""

from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path

from kaggle_environments.envs.kaggriculture import kaggriculture as game

from analyze_worker_routing import MOVEMENT, _effect_category, _op, _responsibility


CROPS = tuple(game.CROPS)
TARGET_HARVEST_AGE = {
    "WHEAT": 4,
    "CARROT": 3,
    "MELON": 10,
}


def _percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    point = fraction * (len(ordered) - 1)
    lower = int(point)
    upper = min(lower + 1, len(ordered) - 1)
    weight = point - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _plant_key(position, tile):
    return (position[0], position[1], int(tile.get("planted_day", -1)), tile.get("crop"))


def _is_plant(tile):
    return isinstance(tile, dict) and tile.get("kind") == "PLANT"


def lifecycle_metrics(replay, player, start_day=10, end_day=20):
    """Measure completed crop work and pending task-hours in an inclusive window."""

    steps = replay["steps"]
    configuration = replay.get("configuration", {})
    board_size = int(configuration.get("boardSize", 10))
    turns_per_day = int(configuration.get("turnsPerDay", 24))
    shed_capacity = int(configuration.get("shedCapacity", 100))
    ready_since = {}
    replacement_since = {}
    harvest_delays = []
    harvest_delay_by_crop = defaultdict(list)
    replant_delays = []
    replant_delay_by_crop = defaultdict(list)
    harvest_actions = Counter()
    harvest_units = Counter()
    successful = Counter()
    movement_by_unit = Counter()
    crop_actions_by_unit = Counter()
    animal_actions_by_unit = Counter()
    total_unit_turns = 0
    worker_days = 0.0
    plant_checks = 0
    watering_misses = 0
    critical_watering_misses = 0
    crop_tile_hours = 0
    harvest_ready_tile_hours = 0
    critical_water_tile_hours = 0
    replacement_tile_hours = 0
    lifecycle_debt_tile_hours = 0
    lost_crops = Counter()
    daily = {
        day: {
            "harvest_actions": Counter(),
            "harvest_units": Counter(),
            "harvest_delays": [],
            "replant_delays": [],
            "crop_tile_hours": 0,
            "lifecycle_debt_tile_hours": 0,
            "movement": 0,
            "crop_productive": 0,
            "plant_checks": 0,
            "watering_misses": 0,
            "critical_watering_misses": 0,
        }
        for day in range(start_day, end_day + 1)
    }

    for state_index in range(1, len(steps)):
        previous_states = steps[state_index - 1]
        current_states = steps[state_index]
        previous_obs = previous_states[0]["observation"]
        day = int(previous_obs.get("day", (state_index - 1) // turns_per_day))
        if day < start_day or day > end_day:
            continue
        hour = int(previous_obs.get("hour", (state_index - 1) % turns_per_day))
        step = int(previous_obs.get("step", state_index - 1))
        farm = deepcopy(previous_obs["farms"][player])
        private = deepcopy(previous_states[player]["observation"]["private"])

        live_keys = set()
        harvestable = 0
        critical = 0
        plants = 0
        for y, row in enumerate(farm["tiles"]):
            for x, tile in enumerate(row):
                if not _is_plant(tile):
                    continue
                plants += 1
                position = (x, y)
                key = _plant_key(position, tile)
                live_keys.add(key)
                crop_data = game.CROPS[tile["crop"]]
                age = day - int(tile.get("planted_day", day))
                harvest_due = (
                    tile.get("yield_units", 0) > 0
                    and (
                        crop_data.get("ongoing", False)
                        or age >= TARGET_HARVEST_AGE[tile["crop"]]
                    )
                )
                if harvest_due:
                    ready_since.setdefault(key, step)
                    harvestable += 1
                if not tile.get("watered_today", False) and tile.get("consecutive_unwatered", 0) >= 1:
                    critical += 1
        for key in list(ready_since):
            if key not in live_keys:
                ready_since.pop(key, None)
        crop_tile_hours += plants
        harvest_ready_tile_hours += harvestable
        critical_water_tile_hours += critical
        replacement_tile_hours += len(replacement_since)
        debt = harvestable + critical + len(replacement_since)
        lifecycle_debt_tile_hours += debt
        daily[day]["crop_tile_hours"] += plants
        daily[day]["lifecycle_debt_tile_hours"] += debt

        action = current_states[player].get("action") or {}
        unit_actions = [action.get("farmer", ["PASS"]), *action.get("hands", [])]
        unit_count = 1 + len(farm.get("hands", []))
        unit_actions += [["PASS"]] * max(0, unit_count - len(unit_actions))
        unit_actions = unit_actions[:unit_count]
        total_unit_turns += unit_count
        worker_days += unit_count / turns_per_day

        plant_demand = Counter(
            unit_action[1]
            for unit_action in unit_actions
            if isinstance(unit_action, list)
            and len(unit_action) >= 2
            and unit_action[0] == "PLANT"
        )
        blocked = {
            crop for crop, count in plant_demand.items()
            if count > private.get("seeds", {}).get(crop, 0)
        }
        for unit_index, original in enumerate(unit_actions):
            unit_action = original
            if (
                isinstance(original, list)
                and len(original) >= 2
                and original[0] == "PLANT"
                and original[1] in blocked
            ):
                unit_action = ["PASS"]
            position = tuple(
                farm["farmer"] if unit_index == 0 else farm["hands"][unit_index - 1]
            )
            inventory = private["inventories"][unit_index]
            before_inventory = dict(inventory)
            before_tile = deepcopy(farm["tiles"][position[1]][position[0]])
            op = _op(unit_action)
            game._apply_unit_action(
                farm, private, unit_index, unit_action, board_size,
                day, turns_per_day, shed_capacity,
            )
            after_position = tuple(
                farm["farmer"] if unit_index == 0 else farm["hands"][unit_index - 1]
            )
            after_tile = deepcopy(farm["tiles"][position[1]][position[0]])
            after_inventory = dict(private["inventories"][unit_index])
            category = _effect_category(
                op, before_tile, before_inventory, after_tile, after_inventory,
                position, after_position,
            )
            if category == "movement":
                movement_by_unit[unit_index] += 1
                daily[day]["movement"] += 1
            if category != "productive":
                continue
            successful[op] += 1
            responsibility = _responsibility(op, before_tile, after_tile)
            if responsibility == "crop":
                crop_actions_by_unit[unit_index] += 1
                daily[day]["crop_productive"] += 1
            elif responsibility == "animal":
                animal_actions_by_unit[unit_index] += 1

            if op == "HARVEST" and _is_plant(before_tile):
                crop = before_tile["crop"]
                units = max(0, after_inventory.get(crop, 0) - before_inventory.get(crop, 0))
                harvest_actions[crop] += 1
                harvest_units[crop] += units
                daily[day]["harvest_actions"][crop] += 1
                daily[day]["harvest_units"][crop] += units
                key = _plant_key(position, before_tile)
                delay = max(0, step - ready_since.get(key, step))
                harvest_delays.append(delay)
                harvest_delay_by_crop[crop].append(delay)
                daily[day]["harvest_delays"].append(delay)
                ready_since.pop(key, None)
                if not _is_plant(after_tile):
                    replacement_since[position] = (step, crop)
            elif op == "PLANT" and _is_plant(after_tile):
                crop = after_tile["crop"]
                if position in replacement_since:
                    removed_step, removed_crop = replacement_since.pop(position)
                    delay = max(0, step - removed_step)
                    replant_delays.append(delay)
                    replant_delay_by_crop[removed_crop].append(delay)
                    daily[day]["replant_delays"].append(delay)

        if hour == turns_per_day - 1:
            for row in farm["tiles"]:
                for tile in row:
                    if not _is_plant(tile):
                        continue
                    plant_checks += 1
                    daily[day]["plant_checks"] += 1
                    if not tile.get("watered_today", False):
                        watering_misses += 1
                        daily[day]["watering_misses"] += 1
                        if tile.get("consecutive_unwatered", 0) >= 1:
                            critical_watering_misses += 1
                            daily[day]["critical_watering_misses"] += 1

            # End-of-day refresh happens between the simulated field actions
            # and the recorded current state. Track plants lost to decay or a
            # second missed watering as replacement debt.
            actual_farm = current_states[0]["observation"]["farms"][player]
            for y, row in enumerate(farm["tiles"]):
                for x, simulated_tile in enumerate(row):
                    actual_tile = actual_farm["tiles"][y][x]
                    if _is_plant(simulated_tile) and not _is_plant(actual_tile):
                        crop = simulated_tile["crop"]
                        lost_crops[crop] += 1
                        replacement_since.setdefault((x, y), (step + 1, crop))
                        ready_since.pop(_plant_key((x, y), simulated_tile), None)

    crop_dominant_units = {
        index for index, count in crop_actions_by_unit.items()
        if count >= animal_actions_by_unit.get(index, 0) and count > 0
    }
    crop_worker_movement = sum(movement_by_unit[index] for index in crop_dominant_units)
    total_harvest_actions = sum(harvest_actions.values())
    serialized_daily = []
    for day in range(start_day, end_day + 1):
        row = daily[day]
        serialized_daily.append({
            "day": day,
            "harvest_actions": dict(row["harvest_actions"]),
            "harvest_units": dict(row["harvest_units"]),
            "average_harvest_delay_turns": (
                statistics.fmean(row["harvest_delays"]) if row["harvest_delays"] else None
            ),
            "average_replant_delay_turns": (
                statistics.fmean(row["replant_delays"]) if row["replant_delays"] else None
            ),
            "crop_tile_hours": row["crop_tile_hours"],
            "lifecycle_debt_tile_hours": row["lifecycle_debt_tile_hours"],
            "movement": row["movement"],
            "crop_productive": row["crop_productive"],
            "watering_miss_rate": row["watering_misses"] / max(1, row["plant_checks"]),
            "critical_watering_miss_rate": (
                row["critical_watering_misses"] / max(1, row["plant_checks"])
            ),
        })
    return {
        "window": [start_day, end_day],
        "harvest_actions": dict(harvest_actions),
        "harvest_units": dict(harvest_units),
        "total_harvest_actions": total_harvest_actions,
        "total_harvest_units": sum(harvest_units.values()),
        "average_harvest_delay_turns": statistics.fmean(harvest_delays) if harvest_delays else None,
        "median_harvest_delay_turns": statistics.median(harvest_delays) if harvest_delays else None,
        "p90_harvest_delay_turns": _percentile(harvest_delays, 0.90),
        "harvest_delay_by_crop": {
            crop: {
                "count": len(values),
                "average": statistics.fmean(values),
                "median": statistics.median(values),
                "p90": _percentile(values, 0.90),
            }
            for crop, values in sorted(harvest_delay_by_crop.items()) if values
        },
        "average_replant_delay_turns": statistics.fmean(replant_delays) if replant_delays else None,
        "median_replant_delay_turns": statistics.median(replant_delays) if replant_delays else None,
        "p90_replant_delay_turns": _percentile(replant_delays, 0.90),
        "replant_delay_by_removed_crop": {
            crop: {
                "count": len(values),
                "average": statistics.fmean(values),
                "median": statistics.median(values),
                "p90": _percentile(values, 0.90),
            }
            for crop, values in sorted(replant_delay_by_crop.items()) if values
        },
        "watering_miss_rate": watering_misses / max(1, plant_checks),
        "critical_watering_miss_rate": critical_watering_misses / max(1, plant_checks),
        "plant_checks": plant_checks,
        "lost_crops": dict(lost_crops),
        "productive_crop_tile_hours": crop_tile_hours,
        "average_productive_crop_tiles": crop_tile_hours / max(1, (end_day - start_day + 1) * turns_per_day),
        "harvest_ready_tile_hours": harvest_ready_tile_hours,
        "critical_water_tile_hours": critical_water_tile_hours,
        "replacement_tile_hours": replacement_tile_hours,
        "lifecycle_debt_tile_hours": lifecycle_debt_tile_hours,
        "average_lifecycle_debt": lifecycle_debt_tile_hours / max(1, (end_day - start_day + 1) * turns_per_day),
        "movement_actions": sum(movement_by_unit.values()),
        "crop_worker_movement_actions": crop_worker_movement,
        "movement_per_crop_cycle": crop_worker_movement / max(1, total_harvest_actions),
        "worker_days": worker_days,
        "completed_cycles_per_worker_day": total_harvest_actions / max(1, worker_days),
        "successful_actions": dict(successful),
        "daily": serialized_daily,
    }


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("replay", type=Path)
    parser.add_argument("--player", type=int, default=0)
    parser.add_argument("--start-day", type=int, default=10)
    parser.add_argument("--end-day", type=int, default=20)
    args = parser.parse_args()
    replay = json.loads(args.replay.read_text())
    print(json.dumps(
        lifecycle_metrics(replay, args.player, args.start_day, args.end_day),
        indent=2,
    ))


if __name__ == "__main__":
    main()
