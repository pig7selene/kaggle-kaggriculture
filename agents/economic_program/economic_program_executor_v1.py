"""Checkpoint-resumable executor with one fully owned melon program.

This research agent is deliberately narrow.  It reconstructs every visible
crop, animal, worker and inventory commitment from the live observation, then
admits at most one compact four-tile MELON program when capital and season
slack permit.  Unlike the earlier PASS-overlay probes, program planting,
watering, harvesting, transport, feed, hiring and liquidation share one task
queue and one worker allocator.

It is research infrastructure, not a submission candidate.  It buys no land,
structures, animals, fertilizer or unrelated crops.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from runpy import run_path


ROOT = Path(__file__).resolve().parents[2]
_BASE = run_path(str(ROOT / "agents/checkpoint_executor/commitment_executor_v1.py"))

CROPS = _BASE["CROPS"]
ANIMALS = _BASE["ANIMALS"]
SELLABLE = _BASE["SELLABLE"]
SHED_TILES = set(_BASE["SHED_TILES"])
_tile_animals = _BASE["_tile_animals"]
_tile_plants = _BASE["_tile_plants"]
_distance = _BASE["_distance"]
_step_toward = _BASE["_step_toward"]
_count_inventory = _BASE["_count_inventory"]
_snapshot = _BASE["_snapshot"]
_build_base_tasks = _BASE["_build_tasks"]
_base_task_score = _BASE["_task_score"]
_base_unit_action = _BASE["_unit_action"]
_feed_overrides = _BASE["_feed_overrides"]
_fib = _BASE["_fib"]


PROGRAM_CROP = "MELON"
PROGRAM_SIZE = 4
PROGRAM_SEED_COST = 80
PROGRAM_FIRST_YIELD_DAY = 10
PROGRAM_FIRST_ADMISSION_DAY = 10
PROGRAM_LAST_ADMISSION_DAY = 18
PROGRAM_LAST_ADMISSION_HOUR = 6
PROGRAM_HARVEST_CUTOFF = 696
PROGRAM_CASH_BUFFER = 400.0
PROGRAM_WORKERS = 3
MAX_HANDS = 10

state = {}
telemetry = {}


def _positions(obs):
    farm = obs["farms"][obs["player"]]
    return [farm["farmer"], *farm.get("hands", [])]


def _tile_at(obs, position):
    farm = obs["farms"][obs["player"]]
    x, y = map(int, position)
    rows = farm.get("tiles", [])
    if 0 <= y < len(rows) and 0 <= x < len(rows[y]):
        return rows[y][x]
    return "LOCKED"


def _target_key(position):
    return f"{int(position[0])},{int(position[1])}"


def _feed_reserve(obs):
    farm = obs["farms"][obs["player"]]
    animals = _tile_animals(farm)
    if not animals:
        return 0.0
    day = int(obs.get("day", 0))
    wheat_price = float(obs.get("market", {}).get("prices", {}).get("WHEAT", 25))
    remaining_days = max(0, 30 - day)
    due_today = sum(not bool(tile.get("fed_today", False)) for _, _, tile in animals)
    reserve_units = due_today + len(animals) * (remaining_days - 1 if int(obs.get("step", 0)) >= 648 else 2)
    private = obs.get("private", {})
    held = int(private.get("shed", {}).get("WHEAT", 0)) + _count_inventory(private.get("inventories", []), "WHEAT")
    return max(0, reserve_units - held) * wheat_price


def _realizable_cash(obs):
    farm = obs["farms"][obs["player"]]
    private = obs.get("private", {})
    prices = obs.get("market", {}).get("prices", {})
    value = float(farm.get("money", 0))
    for item, quantity in private.get("shed", {}).items():
        if item in SELLABLE and item not in ANIMALS:
            value += int(quantity) * float(prices.get(item, 1))
    return value


def _empty_tiles(obs):
    farm = obs["farms"][obs["player"]]
    return {
        (x, y)
        for y, row in enumerate(farm.get("tiles", []))
        for x, tile in enumerate(row)
        if tile is None and (x, y) not in SHED_TILES
    }


def _select_targets(obs):
    """Pick a compact connected zone close to a shed-access tile."""
    empty = _empty_tiles(obs)
    if len(empty) < PROGRAM_SIZE:
        return []
    anchor = min(
        empty,
        key=lambda p: (min(_distance(p, shed) for shed in SHED_TILES), p[1], p[0]),
    )
    chosen = [anchor]
    remaining = set(empty)
    remaining.remove(anchor)
    while len(chosen) < PROGRAM_SIZE and remaining:
        nxt = min(
            remaining,
            key=lambda p: (
                min(_distance(p, q) for q in chosen),
                min(_distance(p, shed) for shed in SHED_TILES),
                p[1],
                p[0],
            ),
        )
        chosen.append(nxt)
        remaining.remove(nxt)
    return chosen if len(chosen) == PROGRAM_SIZE else []


def _can_admit(obs):
    if state.get("targets") or state.get("admission_closed"):
        return False
    day = int(obs.get("day", 0))
    hour = int(obs.get("hour", 0))
    if day < PROGRAM_FIRST_ADMISSION_DAY or day > PROGRAM_LAST_ADMISSION_DAY or hour > PROGRAM_LAST_ADMISSION_HOUR:
        return False
    if int(obs.get("step", 0)) + (PROGRAM_FIRST_YIELD_DAY + 2) * 24 >= 720:
        return False
    private = obs.get("private", {})
    if int(private.get("seeds", {}).get(PROGRAM_CROP, 0)) > 0:
        return False
    targets = _select_targets(obs)
    required = PROGRAM_SIZE * PROGRAM_SEED_COST + PROGRAM_CASH_BUFFER + _feed_reserve(obs)
    return len(targets) == PROGRAM_SIZE and _realizable_cash(obs) >= required


def _admit(obs):
    targets = _select_targets(obs)
    state["targets"] = list(targets)
    state["target_records"] = {
        _target_key(p): {
            "position": list(p),
            "requested": True,
            "planted": False,
            "planted_day": None,
            "maintained_days": [],
            "matured": False,
            "harvested": False,
            "harvest_units": 0,
            "failed": False,
        }
        for p in targets
    }
    state["admitted_step"] = int(obs.get("step", 0))
    telemetry["admission_requests"] += 1


def _reset(obs):
    state.clear()
    state.update({
        "last_step": int(obs.get("step", 0)) - 1,
        "commitment_snapshot": _snapshot(obs),
        "targets": [],
        "target_records": {},
        "admission_closed": False,
        "seed_ordered": False,
        "seed_acquired": False,
        "seed_before": int(obs.get("private", {}).get("seeds", {}).get(PROGRAM_CROP, 0)),
        "last_tiles": {},
        "last_actions": {},
        "program_units": [],
        "program_units_day": None,
        "feed_mode": None,
        "late_critical": 0,
        "recovery_events": 0,
    })
    telemetry.clear()
    telemetry.update({
        "calls": 0,
        "admission_requests": 0,
        "seed_requests": 0,
        "seed_acquired": 0,
        "planted": 0,
        "maintained_tile_days": 0,
        "matured": 0,
        "harvested": 0,
        "harvest_units": 0,
        "sell_requests": 0,
        "sold_units_requested": 0,
        "failed_weeds": 0,
        "program_moves": 0,
        "program_actions": 0,
        "recovery_events": 0,
        "late_critical": 0,
    })


def _observe_program(obs):
    if not state.get("targets"):
        return
    private = obs.get("private", {})
    seed_count = int(private.get("seeds", {}).get(PROGRAM_CROP, 0))
    if state.get("seed_ordered") and not state.get("seed_acquired") and seed_count > int(state.get("seed_before", 0)):
        state["seed_acquired"] = True
        telemetry["seed_acquired"] += min(PROGRAM_SIZE, seed_count - int(state.get("seed_before", 0)))

    day = int(obs.get("day", 0))
    previous_tiles = state.setdefault("last_tiles", {})
    previous_actions = state.setdefault("last_actions", {})
    for position in state.get("targets", []):
        key = _target_key(position)
        record = state["target_records"][key]
        tile = _tile_at(obs, position)
        previous = previous_tiles.get(key)
        if isinstance(tile, dict) and tile.get("kind") == "PLANT" and tile.get("crop") == PROGRAM_CROP:
            if not record["planted"]:
                record["planted"] = True
                record["planted_day"] = int(tile.get("planted_day", day))
                telemetry["planted"] += 1
            if tile.get("watered_today", False) and day not in record["maintained_days"]:
                record["maintained_days"].append(day)
                telemetry["maintained_tile_days"] += 1
            age = day - int(tile.get("planted_day", day))
            if age >= PROGRAM_FIRST_YIELD_DAY and int(tile.get("yield_units", 0)) > 0 and not record["matured"]:
                record["matured"] = True
                telemetry["matured"] += 1
        elif record["planted"] and not record["harvested"]:
            if (
                isinstance(previous, dict)
                and previous.get("kind") == "PLANT"
                and tile is None
                and int(previous.get("yield_units", 0)) > 0
                and day - int(previous.get("planted_day", day)) >= PROGRAM_FIRST_YIELD_DAY
            ):
                record["harvested"] = True
                record["harvest_units"] = int(previous.get("yield_units", 0))
                telemetry["harvested"] += 1
                telemetry["harvest_units"] += int(previous.get("yield_units", 0))
            elif isinstance(tile, dict) and tile.get("kind") == "WEED" and not record["failed"]:
                record["failed"] = True
                telemetry["failed_weeds"] += 1
        previous_tiles[key] = deepcopy(tile)


def _program_tasks(obs):
    day = int(obs.get("day", 0))
    private = obs.get("private", {})
    available_seeds = int(private.get("seeds", {}).get(PROGRAM_CROP, 0))
    tasks = []
    plant_candidates = []
    for position in state.get("targets", []):
        key = _target_key(position)
        record = state["target_records"][key]
        if record["harvested"] or record["failed"]:
            continue
        tile = _tile_at(obs, position)
        if isinstance(tile, dict) and tile.get("kind") == "PLANT" and tile.get("crop") == PROGRAM_CROP:
            age = day - int(tile.get("planted_day", day))
            if not tile.get("watered_today", False):
                tasks.append({
                    "kind": "WATER", "x": position[0], "y": position[1],
                    "urgency": int(tile.get("consecutive_unwatered", 0)),
                    "program": True,
                })
            elif int(tile.get("yield_units", 0)) > 0 and age >= PROGRAM_FIRST_YIELD_DAY and int(obs.get("step", 0)) < PROGRAM_HARVEST_CUTOFF:
                tasks.append({
                    "kind": "HARVEST", "x": position[0], "y": position[1],
                    "urgency": int(tile.get("yield_units", 0)),
                    "program": True,
                })
        elif tile is None and not record["planted"]:
            plant_candidates.append(position)
    for position in plant_candidates[:available_seeds]:
        tasks.append({
            "kind": "PLANT", "x": position[0], "y": position[1],
            "urgency": max(0, 18 - int(obs.get("hour", 0))), "program": True,
            "crop": PROGRAM_CROP,
        })
    return tasks


def _task_score(task, obs):
    if not task.get("program"):
        base_score = _base_task_score(task, obs)
        # At a late checkpoint a newly reconstructed plant can already have
        # one consecutive missed watering day.  Preserve that commitment
        # before servicing ordinary (non-overdue) animal feed; otherwise the
        # first takeover day can turn a healthy premium crop into a weed even
        # though enough workers exist.  Feed tasks with their own overdue
        # flag remain above this rescue tier.
        if task.get("kind") == "WATER" and int(task.get("urgency", 0)) >= 1:
            return base_score + 4000
        return base_score
    hour = int(obs.get("hour", 0))
    if task["kind"] == "WATER":
        return 11750 + int(task.get("urgency", 0)) * 1200 + (1800 if hour >= 18 else 0)
    if task["kind"] == "HARVEST":
        return 10100 + int(task.get("urgency", 0)) * 40
    if task["kind"] == "PLANT":
        return 9550 + (1600 if hour >= 12 else 0)
    return 4000


def _merge_tasks(obs):
    targets = {tuple(p) for p in state.get("targets", [])}
    base_tasks = []
    for task in _build_base_tasks(obs, state):
        if (int(task["x"]), int(task["y"])) in targets and task["kind"] in {"WATER", "HARVEST"}:
            continue
        base_tasks.append(task)
    return base_tasks + _program_tasks(obs)


def _program_unit_indices(obs, tasks):
    positions = _positions(obs)
    program_tasks = [task for task in tasks if task.get("program")]
    if not positions or not program_tasks:
        state["program_units"] = []
        return set()
    day = int(obs.get("day", 0))
    count = min(PROGRAM_WORKERS, len(positions), len(program_tasks))
    if state.get("program_units_day") != day or any(i >= len(positions) for i in state.get("program_units", [])):
        center = (
            sum(int(task["x"]) for task in program_tasks) / len(program_tasks),
            sum(int(task["y"]) for task in program_tasks) / len(program_tasks),
        )
        ranked = sorted(
            range(len(positions)),
            key=lambda i: (i == 0, abs(positions[i][0] - center[0]) + abs(positions[i][1] - center[1]), i),
        )
        state["program_units"] = ranked[:count]
        state["program_units_day"] = day
    return set(state.get("program_units", [])[:count])


def _unit_action(obs, index, task, all_tasks):
    if task and task.get("program") and task["kind"] == "PLANT":
        positions = _positions(obs)
        if index >= len(positions):
            return ["PASS"]
        position = tuple(map(int, positions[index]))
        target = (int(task["x"]), int(task["y"]))
        if position == target:
            if _tile_at(obs, target) is None and int(obs.get("private", {}).get("seeds", {}).get(PROGRAM_CROP, 0)) > 0:
                return ["PLANT", PROGRAM_CROP]
            return ["PASS"]
        return _step_toward(position, target)
    return _base_unit_action(obs, index, task, all_tasks)


def _desired_hands(obs):
    farm = obs["farms"][obs["player"]]
    plants = len(_tile_plants(farm))
    animals = len(_tile_animals(farm))
    program_pending = sum(
        not record["harvested"] and not record["failed"]
        for record in state.get("target_records", {}).values()
    )
    workload = plants * 1.35 + animals * 2.2 + program_pending * 1.8
    target_units = max(1, int((workload + 4.5) // 5.0)) if workload else 1
    desired = max(0, target_units - 1)
    if program_pending:
        desired = max(desired, 6)
    return min(MAX_HANDS, desired)


def _market_orders(obs):
    farm = obs["farms"][obs["player"]]
    private = obs.get("private", {})
    prices = obs.get("market", {}).get("prices", {})
    shed = {item: int(quantity) for item, quantity in private.get("shed", {}).items() if int(quantity) > 0}
    inventories = private.get("inventories", [])
    animals = _tile_animals(farm)
    animal_total = len(animals)
    wheat_total = shed.get("WHEAT", 0) + _count_inventory(inventories, "WHEAT")
    day = int(obs.get("day", 0))
    terminal = int(obs.get("step", 0)) >= 648
    remaining_days = max(0, 30 - day)
    due_today = sum(not tile.get("fed_today", False) for _, _, tile in animals)
    reserve = due_today + animal_total * max(0, remaining_days - 1) if terminal else animal_total * 2

    orders = []
    cash = float(farm.get("money", 0))
    for item in sorted(shed):
        if item not in SELLABLE or item in ANIMALS:
            continue
        quantity = shed[item]
        if item == "WHEAT":
            quantity = max(0, min(quantity, wheat_total - reserve))
        if quantity > 0:
            orders.append(["SELL", item, int(quantity)])
            cash += int(quantity) * float(prices.get(item, 1))

    # Feed is a hard commitment and is bought before optional seeds or labor.
    if wheat_total < reserve and animal_total:
        price = max(1.0, float(prices.get("WHEAT", 25)))
        affordable = max(0, int((cash - 1.0) // price))
        quantity = min(int(reserve - wheat_total), affordable)
        if quantity > 0:
            orders.append(["BUY_PRODUCT", "WHEAT", quantity])
            cash -= quantity * price

    if state.get("targets") and not state.get("seed_ordered"):
        held = int(private.get("seeds", {}).get(PROGRAM_CROP, 0))
        need = max(0, PROGRAM_SIZE - held)
        required = need * PROGRAM_SEED_COST
        if need > 0 and cash >= required + PROGRAM_CASH_BUFFER:
            orders.append(["BUY_SEED", PROGRAM_CROP, need])
            cash -= required
            state["seed_ordered"] = True
            state["seed_before"] = held
            telemetry["seed_requests"] += need

    desired = _desired_hands(obs)
    current = int(farm.get("hires_today", 0))
    hands = len(farm.get("hands", []))
    needed = max(0, desired - hands)
    for offset in range(needed):
        cost = _fib(current + offset)
        if cash < cost or len(orders) >= 10:
            break
        orders.append(["HIRE"])
        cash -= cost
    return orders[:10]


def _assign_actions(obs, tasks):
    farm = obs["farms"][obs["player"]]
    positions = _positions(obs)
    forced_actions, forced_units = _feed_overrides(obs, state)
    program_units = _program_unit_indices(obs, tasks)
    used = set()
    actions = []
    inventories = obs.get("private", {}).get("inventories", [])
    # A worker already carrying wheat is a feed carrier.  Never let the
    # generic pickup/logistics task outrank an executable FEED task for that
    # worker: at checkpoint day-rollovers this otherwise strands an overdue
    # animal until the end-of-day refresh (and can cause an escape).  Keep the
    # restriction local to wheat carriers; units without wheat still perform
    # pickup and other logistics normally.
    feed_tasks = [task for task in tasks if task.get("kind") == "FEED"]

    for index, position in enumerate(positions):
        if index in forced_units:
            actions.append(forced_actions[index])
            continue
        carries_wheat = index < len(inventories) and int(inventories[index].get("WHEAT", 0)) > 0
        candidates = []
        for task_index, task in enumerate(tasks):
            if task_index in used:
                continue
            if task.get("unit") is not None and int(task.get("unit")) != index:
                continue
            if task["kind"] == "FEED" and not carries_wheat:
                continue
            score = _task_score(task, obs) - _distance(position, (task["x"], task["y"])) * 18
            if task.get("program"):
                score += 1100 if index in program_units else -250
            elif index in program_units and _task_score(task, obs) < 10000:
                score -= 300
            candidates.append((score, -int(task["y"]), -int(task["x"]), task_index, task))
        if carries_wheat and feed_tasks:
            feed_candidates = [item for item in candidates if item[-1].get("kind") == "FEED"]
            if feed_candidates:
                candidates = feed_candidates
        if not candidates:
            actions.append(["PASS"])
            continue
        _, _, _, task_index, task = max(candidates)
        used.add(task_index)
        action = _unit_action(obs, index, task, tasks)
        actions.append(action)
        if task.get("program"):
            telemetry["program_actions"] += int(action[0] not in {"NORTH", "SOUTH", "EAST", "WEST", "PASS"})
            telemetry["program_moves"] += int(action[0] in {"NORTH", "SOUTH", "EAST", "WEST"})

    required = 1 + len(farm.get("hands", []))
    actions.extend([["PASS"]] * max(0, required - len(actions)))
    return actions[:required]


def _remember_actions(obs, actions):
    remembered = {}
    for position, action in zip(_positions(obs), actions):
        pos = tuple(map(int, position))
        if pos in {tuple(p) for p in state.get("targets", [])} and action:
            remembered[_target_key(pos)] = action[0]
    state["last_actions"] = remembered


def _update_telemetry(obs, tasks, orders):
    if any(order and order[0] == "SELL" and order[1] == PROGRAM_CROP for order in orders):
        quantity = sum(int(order[2]) for order in orders if order and order[0] == "SELL" and order[1] == PROGRAM_CROP)
        telemetry["sell_requests"] += 1
        telemetry["sold_units_requested"] += quantity
    records = list(state.get("target_records", {}).values())
    requested = len(records)
    telemetry.update({
        "last_step": int(obs.get("step", 0)),
        "targets": [list(p) for p in state.get("targets", [])],
        "requested": requested,
        "acquired": int(telemetry.get("seed_acquired", 0)),
        "planted_count": sum(bool(r["planted"]) for r in records),
        "matured_count": sum(bool(r["matured"]) for r in records),
        "harvested_count": sum(bool(r["harvested"]) for r in records),
        "failed_count": sum(bool(r["failed"]) for r in records),
        "realization_rate": (sum(bool(r["harvested"]) for r in records) / requested) if requested else 0.0,
        "program_units": list(state.get("program_units", [])),
        "pending_tasks": len(tasks),
        "late_critical": int(state.get("late_critical", 0)),
        "recovery_events": int(state.get("recovery_events", 0)),
        "target_records": deepcopy(records),
    })


def agent(obs):
    step = int(obs.get("step", 0))
    if not state or step == 0 or step <= int(state.get("last_step", -1)):
        _reset(obs)
    state["last_step"] = step
    telemetry["calls"] += 1
    _observe_program(obs)
    if _can_admit(obs):
        _admit(obs)
    elif int(obs.get("day", 0)) > PROGRAM_LAST_ADMISSION_DAY:
        state["admission_closed"] = True

    # If no new program is active, preserve the proven commitment executor's
    # exact routing and market behavior.  Re-running a second greedy scheduler
    # in a dense late-checkpoint state can perturb an otherwise safe crop route
    # even when this candidate admitted nothing.  The candidate scheduler is
    # therefore enabled only while it owns an unfinished cohort.
    active_program = any(
        not record.get("harvested") and not record.get("failed")
        for record in state.get("target_records", {}).values()
    )
    if not active_program:
        # Keep lifecycle telemetry in sync even when the safety executor is
        # handling the current turn (including the final harvest observation).
        _update_telemetry(obs, [], [])
        return _BASE["agent"](obs)

    tasks = _merge_tasks(obs)
    tasks.sort(key=lambda task: (-_task_score(task, obs), int(task["y"]), int(task["x"])))
    actions = _assign_actions(obs, tasks)
    orders = _market_orders(obs)
    if int(obs.get("hour", 0)) >= 21 and any(task["kind"] in {"FEED", "WATER"} for task in tasks):
        state["late_critical"] += 1
        state["recovery_events"] += 1
    _remember_actions(obs, actions)
    _update_telemetry(obs, tasks, orders)
    return {"farmer": actions[0], "hands": actions[1:], "market": orders}


agent.telemetry = telemetry
agent.description = "checkpoint-resumable full-owner four-melon economic program executor"
