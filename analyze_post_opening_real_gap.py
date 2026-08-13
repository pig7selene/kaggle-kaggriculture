"""Diagnose the post-opening gap from newest and top-player public replays."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path

from kaggle_environments.envs.kaggriculture import kaggriculture as game

from analyze_opponent_awareness import _first_durable_positive, _reconstruct
from analyze_worker_routing import (
    LOGISTICS,
    MOVEMENT,
    PRODUCTIVE,
    SHED_TILES,
    _effect_category,
    _op,
    _quadrant,
    _responsibility,
    _shed_distance,
)


ROOT = Path(__file__).resolve().parent
NEWEST = ROOT / "experiments" / "kaggle_episodes" / "submission_55435253"
TOP = ROOT / "experiments" / "top_player_replays"
TOP_ANALYSIS = ROOT / "experiments" / "top_player_replay_analysis.json"
OUTPUT = ROOT / "experiments" / "post_opening_real_gap_diagnosis.json"
REPORT = ROOT / "experiments" / "post_opening_real_gap_diagnosis.md"
OUR_TEAM = "Selene"
CHECKPOINTS = (2, 4, 6, 8, 10, 12, 15, 20, 25, 30)
CROPS = tuple(game.CROPS)
ANIMAL_PRODUCTS = {"MILK", "WOOL", "EGG", "FERTILIZER"}


def _plain(counter):
    return {key: counter[key] for key in sorted(counter) if counter[key]}


def _rate(numerator, denominator):
    return numerator / denominator if denominator else 0.0


def _percentile(values, fraction):
    ordered = sorted(values)
    if not ordered:
        return None
    point = fraction * (len(ordered) - 1)
    lower = int(point)
    upper = min(lower + 1, len(ordered) - 1)
    weight = point - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _median(values):
    values = [value for value in values if value is not None]
    return statistics.median(values) if values else None


def _snapshot(farm):
    crops = Counter()
    animals = Counter()
    structures = Counter()
    by_quadrant = defaultdict(lambda: {"crops": Counter(), "animals": Counter(), "productive": 0, "empty": 0})
    productive = 0
    actionable_empty = 0
    inactive = 0
    for y, row in enumerate(farm["tiles"]):
        for x, tile in enumerate(row):
            if tile == "LOCKED":
                continue
            quadrant = _quadrant((x, y))
            if tile is None or (isinstance(tile, dict) and tile.get("kind") == "WEED"):
                actionable_empty += 1
                inactive += 1
                by_quadrant[quadrant]["empty"] += 1
                continue
            if not isinstance(tile, dict):
                inactive += 1
                continue
            kind = tile.get("kind")
            if kind == "PLANT":
                crop = tile["crop"]
                crops[crop] += 1
                productive += 1
                by_quadrant[quadrant]["crops"][crop] += 1
                by_quadrant[quadrant]["productive"] += 1
            elif kind in {"COOP", "PASTURE"}:
                structures[kind] += 1
                if tile.get("animal"):
                    animal = tile["animal"]
                    animals[animal] += 1
                    productive += 1
                    by_quadrant[quadrant]["animals"][animal] += 1
                    by_quadrant[quadrant]["productive"] += 1
                else:
                    inactive += 1
            else:
                inactive += 1
    quadrants = len(farm.get("unlocked_quadrants", []))
    unlocked = 25 * quadrants
    return {
        "money": float(farm.get("money", 0)),
        "hands": len(farm.get("hands", [])),
        "quadrants": quadrants,
        "unlocked_quadrants": list(farm.get("unlocked_quadrants", [])),
        "unlocked_tiles": unlocked,
        "productive_tiles": productive,
        "capacity_utilization": _rate(productive, unlocked),
        "actionable_empty_tiles": actionable_empty,
        "inactive_tiles": inactive,
        "crops": _plain(crops),
        "animals": _plain(animals),
        "structures": _plain(structures),
        "by_quadrant": {
            quadrant: {
                "crops": _plain(values["crops"]),
                "animals": _plain(values["animals"]),
                "productive": values["productive"],
                "empty": values["empty"],
            }
            for quadrant, values in sorted(by_quadrant.items())
        },
    }


def _blank_day(day):
    return {
        "day": day,
        "counts": Counter(),
        "ops": Counter(),
        "task_items": Counter(),
        "responsibilities": Counter(),
        "utilized_positions": set(),
        "plant_checks": 0,
        "missed_watering": 0,
        "critical_missed_watering": 0,
        "missed_watering_by_quadrant": Counter(),
        "critical_missed_by_quadrant": Counter(),
        "max_hands": 0,
        "workers": {},
        "end_snapshot": None,
    }


def _blank_worker(day, index, position):
    return {
        "day": day,
        "unit_index": index,
        "spawn_position": list(position),
        "counts": Counter(),
        "responsibilities": Counter(),
        "productive_quadrants": Counter(),
        "quadrant_crossings": 0,
        "shed_entries": 0,
    }


def _serialize_day(row):
    counts = row["counts"]
    total = counts["total"]
    productive = counts["productive"]
    workers = []
    for worker in row["workers"].values():
        worker_productive = sum(worker["productive_quadrants"].values())
        workers.append(
            {
                "day": worker["day"],
                "unit_index": worker["unit_index"],
                "spawn_position": worker["spawn_position"],
                "counts": _plain(worker["counts"]),
                "responsibilities": _plain(worker["responsibilities"]),
                "productive_quadrants": _plain(worker["productive_quadrants"]),
                "territory_purity": (
                    max(worker["productive_quadrants"].values()) / worker_productive
                    if worker_productive else None
                ),
                "quadrant_crossings": worker["quadrant_crossings"],
                "shed_entries": worker["shed_entries"],
            }
        )
    animal_specialists = sum(
        worker["responsibilities"].get("animal", 0)
        > worker["responsibilities"].get("crop", 0)
        and worker["responsibilities"].get("animal", 0) > 0
        for worker in workers
    )
    snapshot = row["end_snapshot"] or {}
    utilized = len(row["utilized_positions"])
    output = {
        "day": row["day"],
        "counts": _plain(counts),
        "ops": _plain(row["ops"]),
        "task_items": _plain(row["task_items"]),
        "responsibilities": _plain(row["responsibilities"]),
        "total_actions": total,
        "productive_action_ratio": _rate(productive, total),
        "movement_action_ratio": _rate(counts["movement"], total),
        "pass_action_ratio": _rate(counts["pass"], total),
        "logistics_action_ratio": _rate(counts["logistics"], total),
        "invalid_action_ratio": _rate(counts["invalid"], total),
        "movement_per_productive_action": _rate(counts["movement"], productive),
        "watering_miss_rate": _rate(row["missed_watering"], row["plant_checks"]),
        "critical_watering_miss_rate": _rate(row["critical_missed_watering"], row["plant_checks"]),
        "plant_checks": row["plant_checks"],
        "missed_watering": row["missed_watering"],
        "critical_missed_watering": row["critical_missed_watering"],
        "missed_watering_by_quadrant": _plain(row["missed_watering_by_quadrant"]),
        "critical_missed_by_quadrant": _plain(row["critical_missed_by_quadrant"]),
        "actually_utilized_tiles": utilized,
        "utilized_productive_fraction": _rate(utilized, snapshot.get("productive_tiles", 0)),
        "animal_specialist_count": animal_specialists,
        "max_hands": row["max_hands"],
        "end_snapshot": snapshot,
        "workers": sorted(workers, key=lambda value: value["unit_index"]),
    }
    return output


def _field_analysis(replay, selected_players):
    steps = replay["steps"]
    configuration = replay.get("configuration", {})
    board_size = int(configuration.get("boardSize", 10))
    turns_per_day = int(configuration.get("turnsPerDay", 24))
    shed_capacity = int(configuration.get("shedCapacity", 100))
    daily = {player: [_blank_day(day) for day in range(30)] for player in selected_players}
    hourly = {player: [] for player in selected_players}
    land_events = {player: [] for player in selected_players}
    previous_unlocked = {player: None for player in selected_players}

    for state_index, states in enumerate(steps):
        obs = states[0]["observation"]
        day = int(obs.get("day", obs.get("step", state_index) // turns_per_day))
        hour = int(obs.get("hour", obs.get("step", state_index) % turns_per_day))
        for player in selected_players:
            farm = obs["farms"][player]
            snapshot = _snapshot(farm)
            current_unlocked = set(farm.get("unlocked_quadrants", []))
            previous = previous_unlocked[player]
            if previous is not None:
                for quadrant in sorted(current_unlocked - previous):
                    land_events[player].append(
                        {
                            "quadrant": quadrant,
                            "observed_step": int(obs.get("step", state_index)),
                            "day": day,
                            "hour": hour,
                            "deployment": [],
                        }
                    )
            previous_unlocked[player] = current_unlocked
            if 10 <= day <= 20:
                private = states[player]["observation"]["private"]
                total_seeds = sum(private.get("seeds", {}).values())
                strawberry_seeds = private.get("seeds", {}).get("STRAWBERRY", 0)
                hourly[player].append(
                    {
                        "step": int(obs.get("step", state_index)),
                        "day": day,
                        "hour": hour,
                        "bank": snapshot["money"],
                        "hands": snapshot["hands"],
                        "quadrants": snapshot["quadrants"],
                        "productive_tiles": snapshot["productive_tiles"],
                        "actionable_empty_tiles": snapshot["actionable_empty_tiles"],
                        "capacity_utilization": snapshot["capacity_utilization"],
                        "seed_inventory": dict(private.get("seeds", {})),
                        "empty_with_any_seed_capital": (
                            snapshot["actionable_empty_tiles"]
                            if total_seeds > 0 or snapshot["money"] >= 10 else 0
                        ),
                        "empty_with_strawberry_capital": (
                            snapshot["actionable_empty_tiles"]
                            if strawberry_seeds > 0
                            or snapshot["money"] >= game.CROPS["STRAWBERRY"]["seed"]
                            else 0
                        ),
                        "crop_mix": snapshot["crops"],
                        "animal_mix": snapshot["animals"],
                        "by_quadrant": snapshot["by_quadrant"],
                    }
                )
            if day < 30:
                daily[player][day]["max_hands"] = max(daily[player][day]["max_hands"], snapshot["hands"])
                daily[player][day]["end_snapshot"] = snapshot

        if state_index == 0:
            continue
        previous_states = steps[state_index - 1]
        previous_obs = previous_states[0]["observation"]
        action_day = int(previous_obs.get("day", (state_index - 1) // turns_per_day))
        action_hour = int(previous_obs.get("hour", (state_index - 1) % turns_per_day))
        actions = [state.get("action") or {} for state in states]
        for player in selected_players:
            row = daily[player][action_day]
            farm = deepcopy(previous_obs["farms"][player])
            private = deepcopy(previous_states[player]["observation"]["private"])
            action = actions[player] if isinstance(actions[player], dict) else {}
            unit_actions = [action.get("farmer", ["PASS"]), *action.get("hands", [])]
            unit_count = 1 + len(farm.get("hands", []))
            unit_actions += [["PASS"]] * max(0, unit_count - len(unit_actions))
            unit_actions = unit_actions[:unit_count]
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
                position = tuple(farm["farmer"] if unit_index == 0 else farm["hands"][unit_index - 1])
                inventory = private["inventories"][unit_index]
                before_inventory = dict(inventory)
                before_tile = deepcopy(farm["tiles"][position[1]][position[0]])
                op = _op(unit_action)
                worker = row["workers"].setdefault(
                    unit_index, _blank_worker(action_day, unit_index, position)
                )
                game._apply_unit_action(
                    farm,
                    private,
                    unit_index,
                    unit_action,
                    board_size,
                    action_day,
                    turns_per_day,
                    shed_capacity,
                )
                after_position = tuple(farm["farmer"] if unit_index == 0 else farm["hands"][unit_index - 1])
                after_tile = farm["tiles"][position[1]][position[0]]
                after_inventory = dict(private["inventories"][unit_index])
                category = _effect_category(
                    op,
                    before_tile,
                    before_inventory,
                    after_tile,
                    after_inventory,
                    position,
                    after_position,
                )
                responsibility = _responsibility(op, before_tile, after_tile)
                row["counts"]["total"] += 1
                row["counts"][category] += 1
                if category == "productive":
                    row["counts"][f"successful_{op}"] += 1
                    if isinstance(before_tile, dict) and before_tile.get("kind") == "PLANT":
                        row["task_items"][f"{op}:{before_tile['crop']}"] += 1
                    elif isinstance(after_tile, dict) and after_tile.get("kind") == "PLANT":
                        row["task_items"][f"{op}:{after_tile['crop']}"] += 1
                    elif isinstance(before_tile, dict) and before_tile.get("animal"):
                        row["task_items"][f"{op}:{before_tile['animal']}"] += 1
                    elif isinstance(after_tile, dict) and after_tile.get("animal"):
                        row["task_items"][f"{op}:{after_tile['animal']}"] += 1
                row["ops"][op] += 1
                worker["counts"][category] += 1
                if category == "productive":
                    row["responsibilities"][responsibility] += 1
                    worker["responsibilities"][responsibility] += 1
                    worker["productive_quadrants"][_quadrant(position)] += 1
                    row["utilized_positions"].add(position)
                if category == "movement":
                    if _quadrant(position) != _quadrant(after_position):
                        worker["quadrant_crossings"] += 1
                    if after_position in SHED_TILES and position not in SHED_TILES:
                        worker["shed_entries"] += 1
                    if sum(before_inventory.values()) and _shed_distance(after_position) < _shed_distance(position):
                        row["counts"]["loaded_shed_moves"] += 1
            if action_hour == turns_per_day - 1:
                snapshot = _snapshot(farm)
                row["end_snapshot"] = snapshot
                for y, farm_row in enumerate(farm["tiles"]):
                    for x, tile in enumerate(farm_row):
                        if not isinstance(tile, dict) or tile.get("kind") != "PLANT":
                            continue
                        row["plant_checks"] += 1
                        if not tile.get("watered_today", False):
                            row["missed_watering"] += 1
                            row["missed_watering_by_quadrant"][_quadrant((x, y))] += 1
                            if tile.get("consecutive_unwatered", 0) >= 1:
                                row["critical_missed_watering"] += 1
                                row["critical_missed_by_quadrant"][_quadrant((x, y))] += 1

    for player in selected_players:
        for event in land_events[player]:
            quadrant = event["quadrant"]
            for snapshot in hourly[player]:
                if snapshot["step"] < event["observed_step"]:
                    continue
                quadrant_state = snapshot["by_quadrant"].get(
                    quadrant, {"productive": 0, "empty": 25, "crops": {}, "animals": {}}
                )
                event["deployment"].append(
                    {
                        "turns_after_unlock": snapshot["step"] - event["observed_step"],
                        "day": snapshot["day"],
                        "hour": snapshot["hour"],
                        "productive": quadrant_state["productive"],
                        "empty": quadrant_state["empty"],
                        "crops": quadrant_state["crops"],
                        "animals": quadrant_state["animals"],
                    }
                )
            for threshold in (1, 6, 12, 18, 23):
                point = next(
                    (value for value in event["deployment"] if value["productive"] >= threshold),
                    None,
                )
                event[f"turns_to_{threshold}_productive"] = (
                    point["turns_after_unlock"] if point else None
                )
        daily[player] = [_serialize_day(row) for row in daily[player]]
    return {
        player: {
            "daily": daily[player],
            "hourly_day10_20": hourly[player],
            "land_events": land_events[player],
        }
        for player in selected_players
    }


def _leaderboard_scores(directory):
    files = sorted(directory.glob("*publicleaderboard*.csv"))
    if not files:
        return {}
    with files[-1].open(newline="", encoding="utf-8-sig") as handle:
        return {
            row["TeamName"]: {
                "rank": int(row["Rank"]),
                "score": float(row["Score"]),
            }
            for row in csv.DictReader(handle)
        }


def _checkpoint_index(day):
    return 29 if day == 30 else day


def _cumulative_sum(timeline, day, field, products=None):
    index = _checkpoint_index(day)
    total = 0
    for row in timeline[: index + 1]:
        values = row[field]
        if products is None:
            total += sum(values.values())
        else:
            total += sum(values.get(product, 0) for product in products)
    return total


def _route_cumulative(daily, day):
    index = _checkpoint_index(day)
    rows = daily[: index + 1]
    counts = Counter()
    plant_checks = missed = critical = 0
    for row in rows:
        counts.update(row["counts"])
        plant_checks += int(row.get("plant_checks", 0))
        missed += int(row.get("missed_watering", 0))
        critical += int(row.get("critical_missed_watering", 0))
    total = counts["total"]
    return {
        "movement_action_ratio": _rate(counts["movement"], total),
        "productive_action_ratio": _rate(counts["productive"], total),
        "watering_miss_rate": _rate(missed, plant_checks),
    }


def _appearance_checkpoint(appearance, day):
    index = _checkpoint_index(day)
    timeline = appearance["timeline"]
    route = appearance["routing"]["daily"]
    row = timeline[index]
    farm = row["farm"]
    routing = route[index]
    cumulative_route = _route_cumulative(route, day)
    cumulative_revenue = sum(row["cumulative_sale_revenue"].values())
    crop_revenue = _cumulative_sum(timeline, day, "sale_revenue", CROPS)
    animal_revenue = _cumulative_sum(timeline, day, "sale_revenue", ANIMAL_PRODUCTS)
    return {
        "day": day,
        "bank": row["bank_end"],
        "cumulative_revenue": cumulative_revenue,
        "cumulative_crop_revenue": crop_revenue,
        "cumulative_animal_revenue": animal_revenue,
        "quadrants": farm["quadrants"],
        "hands": row["max_hands"],
        "cows": farm.get("animals", {}).get("COW", 0),
        "sheep": farm.get("animals", {}).get("SHEEP", 0),
        "productive_tiles": farm["productive_tiles"],
        "capacity_utilization": _rate(farm["productive_tiles"], 25 * farm["quadrants"]),
        "actually_utilized_tiles": routing["actually_utilized_tiles"],
        "crop_mix": farm.get("crops", {}),
        **cumulative_route,
    }


def _aggregate_checkpoint(appearances, day):
    rows = [_appearance_checkpoint(appearance, day) for appearance in appearances]
    numeric = (
        "bank",
        "cumulative_revenue",
        "cumulative_crop_revenue",
        "cumulative_animal_revenue",
        "quadrants",
        "hands",
        "cows",
        "sheep",
        "productive_tiles",
        "capacity_utilization",
        "actually_utilized_tiles",
        "movement_action_ratio",
        "productive_action_ratio",
        "watering_miss_rate",
    )
    output = {key: _median([row[key] for row in rows]) for key in numeric}
    crop_mix = {}
    for crop in CROPS:
        crop_mix[crop] = _median([row["crop_mix"].get(crop, 0) for row in rows])
    output["crop_mix"] = {crop: value for crop, value in crop_mix.items() if value}
    output["appearances"] = len(rows)
    return output


def _window_summary(appearance, start=10, end=20):
    timeline = appearance["timeline"]
    route = appearance["routing"]["daily"]
    before = timeline[start]
    after = timeline[end]
    rows = route[start : end + 1]
    counts = Counter()
    for row in rows:
        counts.update(row["counts"])
    total = counts["total"]
    revenue_growth = (
        sum(after["cumulative_sale_revenue"].values())
        - sum(before["cumulative_sale_revenue"].values())
    )
    crop_growth = _cumulative_sum(timeline, end, "sale_revenue", CROPS) - _cumulative_sum(
        timeline, start, "sale_revenue", CROPS
    )
    animal_growth = _cumulative_sum(timeline, end, "sale_revenue", ANIMAL_PRODUCTS) - _cumulative_sum(
        timeline, start, "sale_revenue", ANIMAL_PRODUCTS
    )
    purities = [
        worker["territory_purity"]
        for row in rows for worker in row["workers"]
        if worker["territory_purity"] is not None
    ]
    worker_crossings = [
        worker["quadrant_crossings"]
        for row in rows for worker in row["workers"]
    ]
    return {
        "revenue_growth": revenue_growth,
        "crop_revenue_growth": crop_growth,
        "animal_revenue_growth": animal_growth,
        "productive_tile_growth": (
            after["farm"]["productive_tiles"] - before["farm"]["productive_tiles"]
        ),
        "average_productive_tiles": statistics.fmean(
            row["end_snapshot"].get("productive_tiles", 0) for row in rows
        ),
        "average_capacity_utilization": statistics.fmean(
            row["end_snapshot"].get("capacity_utilization", 0) for row in rows
        ),
        "average_actually_utilized_tiles": statistics.fmean(
            row["actually_utilized_tiles"] for row in rows
        ),
        "average_hands": statistics.fmean(row["max_hands"] for row in rows),
        "peak_hands": max(row["max_hands"] for row in rows),
        "movement_action_ratio": _rate(counts["movement"], total),
        "productive_action_ratio": _rate(counts["productive"], total),
        "pass_action_ratio": _rate(counts["pass"], total),
        "logistics_action_ratio": _rate(counts["logistics"], total),
        "invalid_action_ratio": _rate(counts["invalid"], total),
        "movement_per_productive_action": _rate(counts["movement"], counts["productive"]),
        "plant_actions": counts.get("successful_PLANT", 0),
        "loaded_shed_moves": counts.get("loaded_shed_moves", 0),
        "animal_productive_share": _rate(
            sum(row["responsibilities"].get("animal", 0) for row in rows),
            counts["productive"],
        ),
        "average_animal_specialists": statistics.fmean(
            row["animal_specialist_count"] for row in rows
        ),
        "median_territory_purity": _median(purities),
        "average_quadrant_crossings_per_worker_day": (
            statistics.fmean(worker_crossings) if worker_crossings else 0
        ),
        "watering_miss_rate": (
            _rate(
                sum(row["missed_watering"] for row in rows),
                sum(row["plant_checks"] for row in rows),
            )
        ),
        "critical_watering_miss_rate": _rate(
            sum(row["critical_missed_watering"] for row in rows),
            sum(row["plant_checks"] for row in rows),
        ),
        "fertilize_actions": sum(
            count
            for row in rows
            for task, count in row["task_items"].items()
            if task.startswith("FERTILIZE:")
        ),
        "fertilized_crops": _plain(
            Counter(
                {
                    crop: sum(
                        row["task_items"].get(f"FERTILIZE:{crop}", 0) for row in rows
                    )
                    for crop in CROPS
                }
            )
        ),
        "critical_misses_by_quadrant": _plain(
            sum(
                (Counter(row["critical_missed_by_quadrant"]) for row in rows),
                Counter(),
            )
        ),
        "average_empty_tiles": statistics.fmean(
            row["end_snapshot"].get("actionable_empty_tiles", 0) for row in rows
        ),
        "average_empty_tiles_with_strawberry_capital": statistics.fmean(
            snapshot["empty_with_strawberry_capital"]
            for snapshot in appearance["routing"]["hourly_day10_20"]
        ),
        "fraction_post_land_hours_with_empty_and_strawberry_capital": statistics.fmean(
            snapshot["empty_with_strawberry_capital"] > 0
            for snapshot in appearance["routing"]["hourly_day10_20"]
        ),
        "seed_spending": sum(
            sum(timeline[day]["seed_spending"].values()) for day in range(start + 1, end + 1)
        ),
        "labor_spending": sum(timeline[day]["labor_spending"] for day in range(start + 1, end + 1)),
    }


def _aggregate_windows(appearances):
    rows = [_window_summary(appearance) for appearance in appearances]
    keys = rows[0].keys()
    output = {}
    for key in keys:
        values = [row[key] for row in rows]
        if isinstance(values[0], dict):
            subkeys = sorted({subkey for value in values for subkey in value})
            output[key] = {
                subkey: _median([value.get(subkey, 0) for value in values])
                for subkey in subkeys
            }
        else:
            output[key] = _median(values)
    output["appearances"] = len(rows)
    return output


def _durable_day(gaps, threshold=0):
    for day, gap in enumerate(gaps):
        if gap > threshold and all(later > threshold for later in gaps[day:]):
            return day
    return None


def _loss_diagnosis(appearance):
    our = appearance["timeline"]
    opponent = appearance["opponent_timeline"]
    revenue_gap = [
        sum(opp["cumulative_sale_revenue"].values())
        - sum(me["cumulative_sale_revenue"].values())
        for me, opp in zip(our, opponent)
    ]
    bank_gap = [float(opp["bank_end"]) - float(me["bank_end"]) for me, opp in zip(our, opponent)]
    equity_gap = [opp["estimated_equity"] - me["estimated_equity"] for me, opp in zip(our, opponent)]
    final_gap = appearance["opponent_money"] - appearance["final_money"]
    threshold = max(2500, final_gap * 0.08)
    return {
        "episode_id": appearance["episode_id"],
        "opponent": appearance["opponent"],
        "opponent_rating": appearance.get("opponent_rating"),
        "final_gap": final_gap,
        "first_durable_revenue_lead_day": _durable_day(revenue_gap, 0),
        "first_durable_revenue_lead_2500_day": _durable_day(revenue_gap, 2500),
        "first_durable_bank_lead_day": _durable_day(bank_gap, 0),
        "first_durable_equity_lead_day": _first_durable_positive(equity_gap, threshold),
        "revenue_gap_by_day": revenue_gap,
        "bank_gap_by_day": bank_gap,
        "equity_gap_by_day": equity_gap,
    }


def _deployment_summary(appearances):
    rows = []
    for appearance in appearances:
        events = appearance["routing"]["land_events"]
        second = events[1] if len(events) >= 2 else None
        if not second:
            continue
        rows.append(second)
    thresholds = (1, 6, 12, 18, 23)
    return {
        "appearances": len(rows),
        "median_unlock_day": _median([row["day"] for row in rows]),
        "median_unlock_hour": _median([row["hour"] for row in rows]),
        "median_turns_to_productive_threshold": {
            str(threshold): _median([row[f"turns_to_{threshold}_productive"] for row in rows])
            for threshold in thresholds
        },
        "events": rows,
    }


def _load_top_appearances():
    cached = json.loads(TOP_ANALYSIS.read_text())
    selected_names = {row["team_name"] for row in json.loads((TOP / "manifest.json").read_text())["players"]}
    timelines = {}
    for player in cached["players"]:
        for appearance in player["appearances"]:
            timeline = deepcopy(appearance["timeline"])
            cumulative = Counter()
            for row in timeline:
                cumulative.update(row["sale_revenue"])
                row["cumulative_sale_revenue"] = _plain(cumulative)
            timelines[(appearance["episode_id"], appearance["player_index"])] = timeline
    appearances = []
    for path in sorted((TOP / "replays").glob("episode-*-replay.json")):
        replay = json.loads(path.read_text())
        selected = [
            index for index, name in enumerate(replay["info"]["TeamNames"])
            if name in selected_names
        ]
        routing = _field_analysis(replay, selected)
        episode = int(replay["info"]["EpisodeId"])
        for player in selected:
            appearances.append(
                {
                    "episode_id": episode,
                    "team": replay["info"]["TeamNames"][player],
                    "player": player,
                    "timeline": timelines[(episode, player)],
                    "routing": routing[player],
                }
            )
        print(f"top routing {path.name}", flush=True)
    return appearances


def _newest_appearances(scores):
    appearances = []
    records = []
    manifest_rows = []
    for path in sorted((NEWEST / "replays").glob("episode-*-replay.json")):
        replay = json.loads(path.read_text())
        record = _reconstruct(path)
        routing = _field_analysis(replay, (0, 1))
        records.append(record)
        ours = record["team_names"].index(OUR_TEAM)
        theirs = 1 - ours
        final = record["final_money"]
        result = "win" if final[ours] > final[theirs] else "loss" if final[ours] < final[theirs] else "tie"
        appearance = {
            "episode_id": record["episode_id"],
            "seed": record["seed"],
            "team": OUR_TEAM,
            "player": ours,
            "opponent": record["team_names"][theirs],
            "opponent_rating": scores.get(record["team_names"][theirs], {}).get("score"),
            "opponent_rank": scores.get(record["team_names"][theirs], {}).get("rank"),
            "result": result,
            "final_money": final[ours],
            "opponent_money": final[theirs],
            "timeline": record["timelines"][ours],
            "opponent_timeline": record["timelines"][theirs],
            "routing": routing[ours],
            "opponent_routing": routing[theirs],
            "financial_reconstruction_mismatches": record["financial_reconstruction_mismatches"],
        }
        appearances.append(appearance)
        manifest_rows.append(
            {
                key: appearance[key]
                for key in (
                    "episode_id", "seed", "player", "opponent", "opponent_rating",
                    "opponent_rank", "result", "final_money", "opponent_money"
                )
            }
        )
        print(f"newest reconstructed {path.name}", flush=True)
    return appearances, records, manifest_rows


def _write_report(payload):
    lines = [
        "# Post-opening real-gap diagnosis",
        "",
        "This report is the diagnosis stage only. No agent or submission strategy was changed.",
        "",
        "## Newest public episodes",
        "",
        "| Episode | Opponent | Rating | Result | Final money | Opponent | Durable revenue lead | Durable +2500 lead |",
        "|---:|---|---:|---|---:|---:|---:|---:|",
    ]
    losses = {row["episode_id"]: row for row in payload["loss_diagnoses"]}
    for row in payload["newest_manifest"]:
        diagnosis = losses.get(row["episode_id"], {})
        lines.append(
            f"| {row['episode_id']} | {row['opponent']} | {row['opponent_rating']:.1f} | "
            f"{row['result']} | {row['final_money']:.0f} | {row['opponent_money']:.0f} | "
            f"{diagnosis.get('first_durable_revenue_lead_day', '-')} | "
            f"{diagnosis.get('first_durable_revenue_lead_2500_day', '-')} |"
        )
    lines.extend(
        [
            "",
            "## Checkpoint trajectory: newest agent versus selected top population",
            "",
            "| Day | Our revenue | Top revenue | Our bank | Top bank | Our Q | Top Q | Our hands | Top hands | Our tiles | Top tiles | Our occupancy | Top occupancy | Our movement | Top movement | Our productive | Top productive |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for day in CHECKPOINTS:
        ours = payload["checkpoints"][str(day)]["newest"]
        top = payload["checkpoints"][str(day)]["top"]
        lines.append(
            f"| {day} | {ours['cumulative_revenue']:.0f} | {top['cumulative_revenue']:.0f} | "
            f"{ours['bank']:.0f} | {top['bank']:.0f} | {ours['quadrants']:.1f} | {top['quadrants']:.1f} | "
            f"{ours['hands']:.1f} | {top['hands']:.1f} | {ours['productive_tiles']:.1f} | "
            f"{top['productive_tiles']:.1f} | {ours['capacity_utilization']:.1%} | "
            f"{top['capacity_utilization']:.1%} | {ours['movement_action_ratio']:.1%} | "
            f"{top['movement_action_ratio']:.1%} | {ours['productive_action_ratio']:.1%} | "
            f"{top['productive_action_ratio']:.1%} |"
        )
    ours = payload["day10_20"]["newest"]
    top = payload["day10_20"]["top"]
    loss_opp = payload["day10_20"]["real_loss_opponents"]
    lines.extend(
        [
            "",
            "## Day 10-20 throughput",
            "",
            "| Population | Revenue growth | Crop rev | Animal rev | Avg productive tiles | Occupancy | Active tiles/day | Hands avg/peak | Move % | Productive % | Move/productive | Animal-work share | Territory purity |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for label, row in (("Newest", ours), ("Top", top), ("Real-loss opponents", loss_opp)):
        lines.append(
            f"| {label} | {row['revenue_growth']:.0f} | {row['crop_revenue_growth']:.0f} | "
            f"{row['animal_revenue_growth']:.0f} | {row['average_productive_tiles']:.1f} | "
            f"{row['average_capacity_utilization']:.1%} | {row['average_actually_utilized_tiles']:.1f} | "
            f"{row['average_hands']:.1f}/{row['peak_hands']:.1f} | {row['movement_action_ratio']:.1%} | "
            f"{row['productive_action_ratio']:.1%} | {row['movement_per_productive_action']:.2f} | "
            f"{row['animal_productive_share']:.1%} | {row['median_territory_purity']:.1%} |"
        )
    lines.extend(
        [
            "",
            "Complete both-player timelines, per-hour deployment states, worker profiles, crop mixes, exact revenue/spending ledgers, and land activation curves are in `experiments/post_opening_real_gap_diagnosis.json`.",
            "",
        ]
    )
    REPORT.write_text("\n".join(lines))


def analyze():
    scores = _leaderboard_scores(NEWEST)
    newest, records, manifest_rows = _newest_appearances(scores)
    top = _load_top_appearances()
    loss_appearances = [appearance for appearance in newest if appearance["result"] == "loss"]
    loss_opponents = [
        {
            "episode_id": appearance["episode_id"],
            "team": appearance["opponent"],
            "player": 1 - appearance["player"],
            "timeline": appearance["opponent_timeline"],
            "routing": appearance["opponent_routing"],
        }
        for appearance in loss_appearances
    ]
    mismatches = [
        {"episode_id": appearance["episode_id"], **mismatch}
        for appearance in newest
        for mismatch in appearance["financial_reconstruction_mismatches"]
    ]
    payload = {
        "schema_version": 1,
        "submission": {
            "id": 55435253,
            "description": "public-opening + scalable router v6",
            "submission_public_score_at_query": 798.4,
            "team_leaderboard_score_at_download": scores.get(OUR_TEAM, {}).get("score"),
            "team_leaderboard_rank_at_download": scores.get(OUR_TEAM, {}).get("rank"),
        },
        "definitions": {
            "productive_tiles": "end-of-day plants plus occupied animal structures",
            "capacity_utilization": "productive tiles / (25 * unlocked quadrants)",
            "actually_utilized_tiles": "distinct positions with a successful productive field action that day",
            "durable_revenue_lead": "first day after which opponent cumulative realized sales revenue remains ahead through day 30",
            "day10_20_window": "growth from end-day-10 checkpoint to end-day-20 checkpoint; action ratios cover days 10-20 inclusive",
        },
        "newest_manifest": sorted(manifest_rows, key=lambda row: row["episode_id"]),
        "wins": sum(row["result"] == "win" for row in newest),
        "losses": sum(row["result"] == "loss" for row in newest),
        "financial_reconstruction_mismatches": mismatches,
        "loss_diagnoses": [_loss_diagnosis(appearance) for appearance in loss_appearances],
        "checkpoints": {
            str(day): {
                "newest": _aggregate_checkpoint(newest, day),
                "newest_losses": _aggregate_checkpoint(loss_appearances, day),
                "real_loss_opponents": _aggregate_checkpoint(loss_opponents, day),
                "top": _aggregate_checkpoint(top, day),
            }
            for day in CHECKPOINTS
        },
        "day10_20": {
            "newest": _aggregate_windows(newest),
            "newest_losses": _aggregate_windows(loss_appearances),
            "real_loss_opponents": _aggregate_windows(loss_opponents),
            "top": _aggregate_windows(top),
        },
        "deployment_after_second_land": {
            "newest": _deployment_summary(newest),
            "newest_losses": _deployment_summary(loss_appearances),
            "real_loss_opponents": _deployment_summary(loss_opponents),
            "top": _deployment_summary(top),
        },
        "newest_appearances": newest,
        "top_appearances": top,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n")
    manifest = {
        "submission_id": 55435253,
        "episodes": sorted(manifest_rows, key=lambda row: row["episode_id"]),
        "replays": [path.name for path in sorted((NEWEST / "replays").glob("*.json"))],
        "logs": [path.name for path in sorted((NEWEST / "logs").glob("*.json"))],
        "opponent_logs": "not available: Kaggle returned HTTP 403; replay actions are public",
    }
    (NEWEST / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    _write_report(payload)
    print(f"newest={len(newest)} top={len(top)} mismatches={len(mismatches)}")
    print(OUTPUT)
    print(REPORT)
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    analyze()


if __name__ == "__main__":
    main()
