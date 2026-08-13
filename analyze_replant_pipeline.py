"""Harvest-to-replant causal audit for frozen and top public replays.

This analyzer follows successful unit actions rather than inferring lifecycle
events only from daily snapshots.  It deliberately distinguishes Kaggriculture
seed semantics (global ``private.seeds``) from carried product inventory.
"""

from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path

from kaggle_environments.envs.kaggriculture import kaggriculture as game

from analyze_post_opening_real_gap import _effect_category, _op, _responsibility
from analyze_top_player_replays import _transition_ledger


ROOT = Path(__file__).resolve().parent
EPIC = ROOT / "experiments" / "epic_replays"
TOP = ROOT / "experiments" / "top_player_replays" / "replays"
TOP_SELECTION = ROOT / "experiments" / "top_player_worker_routing.json"
OUTPUT = ROOT / "experiments" / "replant_pipeline_diagnosis.json"
CROPS = tuple(game.CROPS)
ONE_TIME = {crop for crop, data in game.CROPS.items() if not data.get("ongoing", False)}
MOVEMENT = {"NORTH", "SOUTH", "EAST", "WEST"}
SHED_TILES = {(4, 4), (5, 4), (4, 5), (5, 5)}
ANIMAL_OPS = {
    "FEED", "CARE", "COLLECT_FERTILIZER", "BUILD_PASTURE", "BUILD_COOP", "PLACE"
}


def _quadrant(position):
    x, y = position
    return ("N" if y < 5 else "S") + ("W" if x < 5 else "E")


def _distance(left, right):
    return abs(left[0] - right[0]) + abs(left[1] - right[1])


def _percentile(values, fraction):
    if not values:
        return None
    values = sorted(values)
    point = fraction * (len(values) - 1)
    lower = int(point)
    upper = min(lower + 1, len(values) - 1)
    weight = point - lower
    return values[lower] * (1 - weight) + values[upper] * weight


def _plain(counter):
    return {key: counter[key] for key in sorted(counter) if counter[key]}


def _plant(tile):
    return isinstance(tile, dict) and tile.get("kind") == "PLANT"


def _animal(tile):
    return isinstance(tile, dict) and tile.get("animal") is not None


def _inventory_total(inventory):
    return sum(inventory.values())


def _market_seed_buys(previous, current, configuration, player):
    ledgers, errors = _transition_ledger(previous, current, configuration)
    if errors:
        raise AssertionError(errors[:3])
    return Counter(ledgers[player]["seed_quantity"])


def _transition_records(previous, current, player, configuration):
    """Replay one player's unit phase and return successful action records."""

    obs = previous[0]["observation"]
    farm = deepcopy(obs["farms"][player])
    private = deepcopy(previous[player]["observation"]["private"])
    # Market orders execute before unit actions.  Adding executed seed buys is
    # necessary to recognize same-turn BUY_SEED -> PLANT transitions.
    private["seeds"].update(_market_seed_buys(previous, current, configuration, player))
    action = current[player].get("action") or {}
    unit_actions = [action.get("farmer", ["PASS"]), *action.get("hands", [])]
    unit_count = 1 + len(farm.get("hands", []))
    unit_actions.extend([["PASS"]] * max(0, unit_count - len(unit_actions)))
    unit_actions = unit_actions[:unit_count]
    board_size = int(configuration.get("boardSize", 10))
    turns = int(configuration.get("turnsPerDay", 24))
    shed_capacity = int(configuration.get("shedCapacity", 100))
    records = []
    for unit, unit_action in enumerate(unit_actions):
        position = tuple(farm["farmer"] if unit == 0 else farm["hands"][unit - 1])
        before_inventory = dict(private["inventories"][unit])
        before_tile = deepcopy(farm["tiles"][position[1]][position[0]])
        op = _op(unit_action)
        game._apply_unit_action(
            farm, private, unit, unit_action, board_size,
            int(obs["day"]), turns, shed_capacity,
        )
        after_position = tuple(farm["farmer"] if unit == 0 else farm["hands"][unit - 1])
        after_inventory = dict(private["inventories"][unit])
        after_tile = deepcopy(farm["tiles"][position[1]][position[0]])
        category = _effect_category(
            op, before_tile, before_inventory, after_tile, after_inventory,
            position, after_position,
        )
        responsibility = (
            _responsibility(op, before_tile, after_tile)
            if category == "productive" else "none"
        )
        item = None
        if _plant(before_tile):
            item = before_tile["crop"]
        elif _plant(after_tile):
            item = after_tile["crop"]
        elif _animal(before_tile):
            item = before_tile["animal"]
        records.append({
            "unit": unit,
            "position": position,
            "after_position": after_position,
            "action": unit_action,
            "op": op,
            "category": category,
            "responsibility": responsibility,
            "item": item,
            "inventory_before": before_inventory,
            "inventory_after": after_inventory,
            "tile_before": before_tile,
            "tile_after": after_tile,
        })
    return records


def _step_context(replay, player):
    """Index positions, actions, seeds, deadlines, and backlogs by action step."""

    configuration = replay.get("configuration", {})
    context = {}
    successful = []
    for index in range(1, len(replay["steps"])):
        previous = replay["steps"][index - 1]
        current = replay["steps"][index]
        obs = previous[0]["observation"]
        step = int(obs["step"])
        farm = obs["farms"][player]
        private = previous[player]["observation"]["private"]
        seed_buys = _market_seed_buys(previous, current, configuration, player)
        seeds_after_market = Counter(private["seeds"])
        seeds_after_market.update(seed_buys)
        critical = Counter()
        ready = Counter()
        empty = Counter()
        for y, row in enumerate(farm["tiles"]):
            for x, tile in enumerate(row):
                quadrant = _quadrant((x, y))
                if tile is None:
                    empty[quadrant] += 1
                elif _plant(tile):
                    if not tile.get("watered_today", False) and tile.get("consecutive_unwatered", 0) >= 1:
                        critical[quadrant] += 1
                    if tile.get("yield_units", 0) > 0:
                        ready[quadrant] += 1
        positions = [tuple(farm["farmer"]), *[tuple(value) for value in farm.get("hands", [])]]
        records = _transition_records(previous, current, player, configuration)
        for record in records:
            if record["category"] == "productive":
                successful.append({
                    "step": step, "day": int(obs["day"]), "hour": int(obs["hour"]),
                    **record,
                })
        context[step] = {
            "day": int(obs["day"]),
            "hour": int(obs["hour"]),
            "positions": positions,
            "unit_inventories": [dict(value) for value in private["inventories"]],
            "seeds_before_market": dict(private["seeds"]),
            "seed_buys": _plain(seed_buys),
            "seeds_after_market": dict(seeds_after_market),
            "money": float(farm["money"]),
            "critical_by_quadrant": _plain(critical),
            "ready_by_quadrant": _plain(ready),
            "empty_by_quadrant": _plain(empty),
            "records": records,
            "tile_grid": farm["tiles"],
        }
    return context, successful


def _delay_cause(step_context, harvest, replant_crop, original_unit, position):
    """Assign one excess waiting turn to the strongest observable constraint."""

    quadrant = _quadrant(position)
    seeds = step_context["seeds_after_market"].get(replant_crop, 0)
    records = step_context["records"]
    original = records[original_unit] if original_unit < len(records) else None
    if seeds <= 0:
        return "no_seed_available"
    if step_context["critical_by_quadrant"].get(quadrant, 0):
        if any(row["op"] == "WATER" and row["category"] == "productive" for row in records):
            return "watering_emergency"
    if original and original["responsibility"] == "animal":
        return "animal_service_interruption"
    if original and original["op"] in {"DROP", "PICKUP"}:
        return "shed_travel"
    if original and original["op"] in MOVEMENT:
        before = original["position"]
        after = original["after_position"]
        shed_before = min(_distance(before, value) for value in SHED_TILES)
        shed_after = min(_distance(after, value) for value in SHED_TILES)
        if shed_after < shed_before and _inventory_total(original["inventory_before"]):
            return "shed_travel"
        if _quadrant(after) != quadrant:
            return "worker_left_territory"
    if step_context["ready_by_quadrant"].get(quadrant, 0):
        if any(row["op"] == "HARVEST" and row["category"] == "productive" for row in records):
            return "harvest_backlog"
    if original and original["category"] in {"movement", "productive"}:
        if _quadrant(original["position"]) == quadrant:
            return "scheduler_priority"
        return "territory_assignment"
    # If seeds and nearby capacity exist but nobody selects the tile, this is
    # scheduler/economic admission rather than physical seed logistics.
    min_distance = min((_distance(worker, position) for worker in step_context["positions"]), default=99)
    if min_distance <= 3:
        return "scheduler_priority"
    return "territory_assignment"


def _event_rows(replay, player, start_day=10, end_day=25):
    context, successful = _step_context(replay, player)
    plants_by_position = defaultdict(list)
    harvests = []
    ongoing_harvests = Counter()
    for event in successful:
        position = tuple(event["position"])
        if event["op"] == "PLANT" and event["item"] in CROPS:
            plants_by_position[position].append(event)
        elif event["op"] == "HARVEST" and event["item"] in CROPS:
            if event["item"] not in ONE_TIME:
                ongoing_harvests[event["item"]] += 1
                continue
            if start_day <= event["day"] <= end_day:
                harvests.append(event)

    rows = []
    for harvest in harvests:
        position = tuple(harvest["position"])
        later = [event for event in plants_by_position[position] if event["step"] >= harvest["step"]]
        replant = min(later, key=lambda event: event["step"]) if later else None
        delay = replant["step"] - harvest["step"] if replant else None
        replant_crop = replant["item"] if replant else None
        harvest_context = context[harvest["step"]]
        seeds_at_harvest = (
            harvest_context["seeds_after_market"].get(replant_crop, 0)
            if replant_crop else None
        )
        cause_turns = Counter()
        original_ops = Counter()
        shed_trips = 0
        original_left = False
        first_seed_step = None
        earliest_other = None
        if replant:
            # The first post-harvest action is the theoretical same-worker
            # chain opportunity.  Attribute only excess delay beyond one turn.
            for step in range(harvest["step"] + 1, replant["step"]):
                row = context.get(step)
                if row is None:
                    continue
                if row["seeds_after_market"].get(replant_crop, 0) > 0 and first_seed_step is None:
                    first_seed_step = step
                cause = _delay_cause(
                    row, harvest, replant_crop, harvest["unit"], position
                )
                cause_turns[cause] += 1
                if harvest["unit"] < len(row["records"]):
                    record = row["records"][harvest["unit"]]
                    original_ops[record["op"]] += 1
                    if record["op"] in {"DROP", "PICKUP"}:
                        shed_trips += 1
                    if _quadrant(record["after_position"]) != _quadrant(position):
                        original_left = True
                if row["seeds_after_market"].get(replant_crop, 0) > 0:
                    candidates = [
                        step - harvest["step"] + _distance(worker, position)
                        for unit, worker in enumerate(row["positions"])
                        if unit != harvest["unit"]
                    ]
                    if candidates:
                        opportunity = min(candidates)
                        earliest_other = opportunity if earliest_other is None else min(earliest_other, opportunity)
        primary = cause_turns.most_common(1)[0][0] if cause_turns else (
            "immediate_chain" if delay is not None and delay <= 1 else "not_replanted"
        )
        rows.append({
            "harvest_step": harvest["step"],
            "harvest_day": harvest["day"],
            "harvest_hour": harvest["hour"],
            "replant_step": replant["step"] if replant else None,
            "replant_day": replant["day"] if replant else None,
            "replant_hour": replant["hour"] if replant else None,
            "delay_turns": delay,
            "harvest_crop": harvest["item"],
            "replant_crop": replant_crop,
            "position": list(position),
            "quadrant": _quadrant(position),
            "harvest_worker": harvest["unit"],
            "replant_worker": replant["unit"] if replant else None,
            "same_worker": bool(replant and replant["unit"] == harvest["unit"]),
            "same_worker_identity_reliable": bool(
                replant and replant["day"] == harvest["day"]
            ) or harvest["unit"] == 0,
            "harvest_worker_inventory": _plain(Counter(harvest["inventory_before"])),
            "global_seed_inventory_before_market": harvest_context["seeds_before_market"],
            "seed_bought_on_harvest_turn": harvest_context["seed_buys"],
            "correct_seed_available_after_market": seeds_at_harvest,
            "seed_source_distance": 0 if seeds_at_harvest else None,
            "seed_semantics": "global private.seeds; never carried by a worker",
            "first_later_seed_available_step": first_seed_step,
            "shed_trips_by_harvester_during_delay": shed_trips,
            "harvester_left_quadrant": original_left,
            "harvester_ops_during_delay": _plain(original_ops),
            "cause_turns": _plain(cause_turns),
            "primary_cause": primary,
            "another_worker_estimated_earliest_delay": earliest_other,
            "another_worker_could_replant_sooner": bool(
                delay is not None and earliest_other is not None and earliest_other < delay
            ),
        })
    return rows, ongoing_harvests


def _summary(rows, ongoing_harvests):
    completed = [row for row in rows if row["delay_turns"] is not None]
    delays = [row["delay_turns"] for row in completed]
    excess = sum(max(0, value - 1) for value in delays)
    causes = Counter()
    primary = Counter(row["primary_cause"] for row in rows)
    by_crop = {}
    for crop in ONE_TIME:
        values = [row["delay_turns"] for row in completed if row["harvest_crop"] == crop]
        if values:
            by_crop[crop] = {
                "events": len(values),
                "average": statistics.fmean(values),
                "median": statistics.median(values),
                "p90": _percentile(values, 0.9),
            }
    for row in completed:
        causes.update(row["cause_turns"])
    fractions = {
        f"within_{limit}_turns": sum(value <= limit for value in delays) / max(1, len(delays))
        for limit in (2, 5, 10, 20)
    }
    same_reliable = [row for row in completed if row["same_worker_identity_reliable"]]
    return {
        "one_time_harvests": len(rows),
        "completed_replants": len(completed),
        "not_replanted": len(rows) - len(completed),
        "ongoing_harvests_not_requiring_replant": _plain(ongoing_harvests),
        "average_delay": statistics.fmean(delays) if delays else None,
        "median_delay": statistics.median(delays) if delays else None,
        "p90_delay": _percentile(delays, 0.9),
        "same_tile_immediate_replant_rate": (
            sum(value <= 1 for value in delays) / max(1, len(delays))
        ),
        **fractions,
        "same_worker_rate_reliable_subset": (
            sum(row["same_worker"] for row in same_reliable) / max(1, len(same_reliable))
        ),
        "same_worker_reliable_events": len(same_reliable),
        "correct_seed_available_at_harvest_rate": (
            sum((row["correct_seed_available_after_market"] or 0) > 0 for row in completed)
            / max(1, len(completed))
        ),
        "harvester_left_quadrant_rate": (
            sum(row["harvester_left_quadrant"] for row in completed) / max(1, len(completed))
        ),
        "another_worker_could_replant_sooner_rate": (
            sum(row["another_worker_could_replant_sooner"] for row in completed)
            / max(1, len(completed))
        ),
        "seed_related_shed_trips": 0,
        "seed_retrieval_movement": 0,
        "cause_excess_turns": _plain(causes),
        "cause_share_of_excess_delay": {
            key: value / max(1, excess) for key, value in sorted(causes.items())
        },
        "primary_cause_events": _plain(primary),
        "by_harvest_crop": by_crop,
    }


def _aggregate(appearances):
    rows = [row for appearance in appearances for row in appearance["events"]]
    ongoing = Counter()
    for appearance in appearances:
        ongoing.update(appearance["summary"]["ongoing_harvests_not_requiring_replant"])
    summary = _summary(rows, ongoing)
    summary["appearances"] = len(appearances)
    return summary


def main():
    epic_manifest = json.loads((EPIC / "manifest.json").read_text())
    current = []
    for case in epic_manifest["cases"]:
        replay = json.loads((ROOT / case["replay"]).read_text())
        rows, ongoing = _event_rows(replay, int(case["our_seat"]))
        current.append({
            "episode_id": int(case["episode_id"]),
            "opponent": case["opponent"],
            "player": int(case["our_seat"]),
            "summary": _summary(rows, ongoing),
            "events": rows,
        })

    selection = json.loads(TOP_SELECTION.read_text())["appearances"]
    top = []
    for appearance in selection:
        replay = json.loads(
            (TOP / f"episode-{appearance['episode_id']}-replay.json").read_text()
        )
        rows, ongoing = _event_rows(replay, int(appearance["player_index"]))
        top.append({
            "episode_id": int(appearance["episode_id"]),
            "team": appearance["team_name"],
            "player": int(appearance["player_index"]),
            "summary": _summary(rows, ongoing),
            "events": rows,
        })

    payload = {
        "schema_version": 1,
        "window": {"harvest_days": [10, 25], "replants_followed_through": 29},
        "definitions": {
            "delay_turns": "successful replant action step minus successful destructive harvest step; one turn is the normal same-worker next-action minimum",
            "cause_attribution": "each excess turn after the first is assigned to the strongest observable active constraint; shares sum over excess delay only",
            "seed_semantics": "seeds are global private inventory consumed directly by PLANT; workers cannot carry seeds and no seed shed trip exists",
            "same_worker": "same unit index; hand identity is reliable only within a day, while farmer index zero persists",
            "strawberry": "ongoing strawberry HARVEST leaves the plant in place and therefore has no harvest-to-replant event until terminal removal",
        },
        "current_appearances": current,
        "current_aggregate": _aggregate(current),
        "top_appearances": top,
        "top_aggregate": _aggregate(top),
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(OUTPUT)
    print(json.dumps({
        "current": payload["current_aggregate"],
        "top": payload["top_aggregate"],
    }, indent=2))


if __name__ == "__main__":
    main()
