"""Coherent checkpoint owner with a bounded replacement-melon program.

This is a research-only candidate.  It is deliberately smaller than the
rejected general planner: the existing commitment executor remains the sole
owner of observed crops, animals, feed, inventories, and terminal work.  Once
the candidate is handed a real checkpoint, it may admit at most two melons on
currently empty tiles, but those tiles are serviced by the same task queue as
all mandatory work.  No land, structure, animal, fertilizer, or market-timing
decision is introduced.

The implementation can be shadow-called before a takeover checkpoint.  In
that mode it records the observed tile history but does not admit a program;
this lets the admission rule prefer tiles that were recently harvested rather
than stealing an untouched tile from the opening route.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from runpy import run_path


ROOT = Path(__file__).resolve().parents[2]
_BASE = run_path(str(ROOT / "agents/checkpoint_executor/commitment_executor_v1.py"))

ANIMALS = _BASE["ANIMALS"]
CROPS = _BASE["CROPS"]
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
PROGRAM_SIZE = 2
PROGRAM_SEED_COST = int(CROPS[PROGRAM_CROP]["seed"])
PROGRAM_FIRST_YIELD_DAY = int(CROPS[PROGRAM_CROP]["first"])
PROGRAM_LAST_ADMISSION_DAY = 16
PROGRAM_LAST_ADMISSION_HOUR = 12
PROGRAM_HARVEST_CUTOFF = 696
PROGRAM_CASH_BUFFER = 400.0
PROGRAM_MAX_HANDS = 8
TAKEOVER_MIN_STEP = 240

MOVES = {"NORTH", "SOUTH", "EAST", "WEST"}

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


def _key(position):
    return f"{int(position[0])},{int(position[1])}"


def _empty_tiles(obs):
    farm = obs["farms"][obs["player"]]
    out = set()
    for y, row in enumerate(farm.get("tiles", [])):
        for x, tile in enumerate(row):
            if tile is None and (x, y) not in SHED_TILES:
                out.add((x, y))
    return out


def _reset(obs):
    state.clear()
    state.update({
        "last_step": int(obs.get("step", 0)) - 1,
        "commitment_snapshot": _snapshot(obs),
        "targets": [],
        "target_records": {},
        "admission_closed": False,
        "seed_ordered": False,
        "seed_before": int(obs.get("private", {}).get("seeds", {}).get(PROGRAM_CROP, 0)),
        "last_tiles": {},
        "last_tile_steps": {},
        "feed_mode": None,
        "program_units": [],
        "program_units_day": None,
        "shadow_only": int(obs.get("step", 0)) < TAKEOVER_MIN_STEP,
        "live_started": False,
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
        "failed_weeds": 0,
        "program_moves": 0,
        "program_actions": 0,
        "replacement_candidates": 0,
        "recent_vacancy_candidates": 0,
        "late_critical": 0,
        "recovery_events": 0,
    })


def _remember_tiles(obs):
    """Track tile transitions without assuming an unseen pre-checkpoint state."""
    step = int(obs.get("step", 0))
    for y, row in enumerate(obs["farms"][obs["player"]].get("tiles", [])):
        for x, tile in enumerate(row):
            if (x, y) in SHED_TILES:
                continue
            key = _key((x, y))
            previous = state["last_tiles"].get(key)
            # A recently observed plant that became empty is a replacement
            # candidate.  Keep the crop and harvest step for a short window.
            if previous is not None and isinstance(previous, dict) and previous.get("kind") == "PLANT" and tile is None:
                state["last_tile_steps"][key] = step
            state["last_tiles"][key] = deepcopy(tile)


def _observe_program(obs):
    if not state.get("targets"):
        return
    day = int(obs.get("day", 0))
    previous_tiles = state.setdefault("program_previous", {})
    for position in state.get("targets", []):
        key = _key(position)
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
            if isinstance(previous, dict) and previous.get("kind") == "PLANT" and tile is None:
                if int(previous.get("yield_units", 0)) > 0 and day - int(previous.get("planted_day", day)) >= PROGRAM_FIRST_YIELD_DAY:
                    record["harvested"] = True
                    record["harvest_units"] = int(previous.get("yield_units", 0))
                    telemetry["harvested"] += 1
                    telemetry["harvest_units"] += int(previous.get("yield_units", 0))
            elif isinstance(tile, dict) and tile.get("kind") == "WEED" and not record["failed"]:
                record["failed"] = True
                telemetry["failed_weeds"] += 1
        previous_tiles[key] = deepcopy(tile)


def _recent_empty_candidates(obs):
    empty = _empty_tiles(obs)
    day = int(obs.get("day", 0))
    step = int(obs.get("step", 0))
    candidates = []
    for position in empty:
        key = _key(position)
        vacancy_step = state.get("last_tile_steps", {}).get(key)
        recent = vacancy_step is not None and 0 <= step - int(vacancy_step) <= 48
        # Prefer known vacancies; otherwise allow an untouched empty tile only
        # when it is close to the shed and no recent vacancy is available.
        shed_distance = min(_distance(position, shed) for shed in SHED_TILES)
        candidates.append((0 if recent else 1, shed_distance, position[1], position[0], position))
    candidates.sort()
    recent_count = sum(item[0] == 0 for item in candidates)
    telemetry["recent_vacancy_candidates"] = recent_count
    telemetry["replacement_candidates"] = len(candidates)
    return [item[-1] for item in candidates]


def _realizable_cash(obs):
    farm = obs["farms"][obs["player"]]
    private = obs.get("private", {})
    prices = obs.get("market", {}).get("prices", {})
    value = float(farm.get("money", 0))
    for item, quantity in private.get("shed", {}).items():
        if item in SELLABLE and item not in ANIMALS:
            value += int(quantity) * float(prices.get(item, 1))
    return value


def _feed_reserve_value(obs):
    farm = obs["farms"][obs["player"]]
    animals = _tile_animals(farm)
    if not animals:
        return 0.0
    private = obs.get("private", {})
    held = int(private.get("shed", {}).get("WHEAT", 0)) + _count_inventory(private.get("inventories", []), "WHEAT")
    day = int(obs.get("day", 0))
    remaining = max(0, 30 - day)
    due_today = sum(not tile.get("fed_today", False) for _, _, tile in animals)
    required = due_today + len(animals) * (remaining - 1 if int(obs.get("step", 0)) >= 648 else 2)
    price = float(obs.get("market", {}).get("prices", {}).get("WHEAT", 25))
    return max(0, required - held) * price


def _can_admit(obs):
    if state.get("targets") or state.get("admission_closed"):
        return False
    step = int(obs.get("step", 0))
    day = int(obs.get("day", 0))
    hour = int(obs.get("hour", 0))
    takeover_step = int(getattr(agent, "takeover_step", TAKEOVER_MIN_STEP))
    if step < takeover_step or day > PROGRAM_LAST_ADMISSION_DAY:
        return False
    if day == PROGRAM_LAST_ADMISSION_DAY and hour > PROGRAM_LAST_ADMISSION_HOUR:
        return False
    # Melon must have time to mature and be carried to the shed before the
    # terminal reservation.  This is intentionally conservative.
    if step + (PROGRAM_FIRST_YIELD_DAY + 2) * 24 >= PROGRAM_HARVEST_CUTOFF:
        return False
    private = obs.get("private", {})
    if int(private.get("seeds", {}).get(PROGRAM_CROP, 0)) > 0:
        return False
    targets = _recent_empty_candidates(obs)
    if len(targets) < PROGRAM_SIZE:
        return False
    farm = obs["farms"][obs["player"]]
    positions = _positions(obs)
    if len(positions) < 2:
        return False
    # Require two actual units and a cash reserve for feed; this prevents the
    # optional cohort from creating a debt-like opening or starving livestock.
    required = PROGRAM_SIZE * PROGRAM_SEED_COST + PROGRAM_CASH_BUFFER + _feed_reserve_value(obs)
    # Require the seed bill and feed reserve to be payable from the bank now.
    # Counting shed value here would admit a cohort whose BUY_SEED order is
    # later truncated behind ten existing market orders.
    return float(farm.get("money", 0)) >= required


def _admit(obs):
    targets = _recent_empty_candidates(obs)[:PROGRAM_SIZE]
    state["targets"] = list(targets)
    state["target_records"] = {
        _key(position): {
            "position": list(position),
            "planted": False,
            "planted_day": None,
            "maintained_days": [],
            "matured": False,
            "harvested": False,
            "harvest_units": 0,
            "failed": False,
        }
        for position in targets
    }
    state["program_previous"] = {}
    state["admitted_step"] = int(obs.get("step", 0))
    telemetry["admission_requests"] += 1


def _program_tasks(obs):
    day = int(obs.get("day", 0))
    step = int(obs.get("step", 0))
    seeds = int(obs.get("private", {}).get("seeds", {}).get(PROGRAM_CROP, 0))
    tasks = []
    plant_candidates = []
    for position in state.get("targets", []):
        key = _key(position)
        record = state["target_records"][key]
        if record["harvested"] or record["failed"]:
            continue
        tile = _tile_at(obs, position)
        if isinstance(tile, dict) and tile.get("kind") == "PLANT" and tile.get("crop") == PROGRAM_CROP:
            age = day - int(tile.get("planted_day", day))
            if not tile.get("watered_today", False):
                tasks.append({"kind": "WATER", "x": position[0], "y": position[1], "urgency": int(tile.get("consecutive_unwatered", 0)), "program": True})
            elif int(tile.get("yield_units", 0)) > 0 and age >= PROGRAM_FIRST_YIELD_DAY and step < PROGRAM_HARVEST_CUTOFF:
                tasks.append({"kind": "HARVEST", "x": position[0], "y": position[1], "urgency": int(tile.get("yield_units", 0)), "program": True})
        elif tile is None and not record["planted"]:
            plant_candidates.append(position)
    for position in plant_candidates[:seeds]:
        tasks.append({"kind": "PLANT", "x": position[0], "y": position[1], "urgency": 10, "program": True, "crop": PROGRAM_CROP})
    return tasks


def _task_score(task, obs):
    if not task.get("program"):
        score = _base_task_score(task, obs)
        if task.get("kind") == "WATER" and int(task.get("urgency", 0)) >= 1:
            score += 4000
        return score
    kind = task["kind"]
    hour = int(obs.get("hour", 0))
    if kind == "WATER":
        # Optional work must remain below mandatory base WATER/FEED scores;
        # it may use genuinely idle capacity but cannot steal a deadline lane.
        return 9000 + int(task.get("urgency", 0)) * 800 + (600 if hour >= 18 else 0)
    if kind == "HARVEST":
        return 7600 + int(task.get("urgency", 0)) * 40
    if kind == "PLANT":
        return 7000 + (600 if hour >= 12 else 0)
    return 4000


def _merge_tasks(obs):
    targets = {tuple(position) for position in state.get("targets", [])}
    base_tasks = []
    for task in _build_base_tasks(obs, state):
        if (int(task["x"]), int(task["y"])) in targets and task["kind"] in {"WATER", "HARVEST"}:
            continue
        base_tasks.append(task)
    return base_tasks + _program_tasks(obs)


def _program_units(obs, tasks):
    program_tasks = [task for task in tasks if task.get("program")]
    positions = _positions(obs)
    if not program_tasks or not positions:
        state["program_units"] = []
        return set()
    day = int(obs.get("day", 0))
    count = min(2, len(positions), len(program_tasks))
    if state.get("program_units_day") != day or any(index >= len(positions) for index in state.get("program_units", [])):
        center = (sum(int(task["x"]) for task in program_tasks) / len(program_tasks), sum(int(task["y"]) for task in program_tasks) / len(program_tasks))
        ranked = sorted(range(len(positions)), key=lambda index: (index == 0, _distance(positions[index], center), index))
        state["program_units"] = ranked[:count]
        state["program_units_day"] = day
    return set(state.get("program_units", []))


def _program_action(obs, index, task, all_tasks):
    if task and task.get("program") and task["kind"] == "PLANT":
        positions = _positions(obs)
        if index >= len(positions):
            return ["PASS"]
        position = tuple(map(int, positions[index]))
        target = (int(task["x"]), int(task["y"]))
        if position == target and _tile_at(obs, target) is None and int(obs.get("private", {}).get("seeds", {}).get(PROGRAM_CROP, 0)) > 0:
            return ["PLANT", PROGRAM_CROP]
        return _step_toward(position, target)
    return _base_unit_action(obs, index, task, all_tasks)


def _assign_actions(obs, tasks):
    positions = _positions(obs)
    forced_actions, forced_units = _feed_overrides(obs, state)
    program_units = _program_units(obs, tasks)
    inventories = obs.get("private", {}).get("inventories", [])
    feed_tasks = [task for task in tasks if task.get("kind") == "FEED"]
    used = set()
    actions = []
    for index, position in enumerate(positions):
        if index in forced_units:
            actions.append(forced_actions[index])
            continue
        carries_wheat = index < len(inventories) and int(inventories[index].get("WHEAT", 0)) > 0
        candidates = []
        for task_index, task in enumerate(tasks):
            if task_index in used:
                continue
            if task.get("unit") is not None and int(task["unit"]) != index:
                continue
            if task["kind"] == "FEED" and not carries_wheat:
                continue
            score = _task_score(task, obs) - _distance(position, (task["x"], task["y"])) * 18
            if task.get("program"):
                score += 300 if index in program_units else -100
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
        action = _program_action(obs, index, task, tasks)
        actions.append(action)
        if task.get("program"):
            telemetry["program_moves"] += int(action[0] in MOVES)
            telemetry["program_actions"] += int(action[0] not in MOVES and action[0] != "PASS")
    required = 1 + len(obs["farms"][obs["player"]].get("hands", []))
    actions.extend([["PASS"]] * max(0, required - len(actions)))
    return actions[:required]


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

    # Reserve the first market slot for the program seed purchase.  This is a
    # commitment of the coherent owner, so it must not be silently dropped by
    # a long list of ordinary SELL orders.
    if state.get("targets") and not state.get("seed_ordered"):
        held = int(private.get("seeds", {}).get(PROGRAM_CROP, 0))
        need = max(0, PROGRAM_SIZE - held)
        cost = need * PROGRAM_SEED_COST
        if need > 0 and cash >= cost + PROGRAM_CASH_BUFFER:
            orders.append(["BUY_SEED", PROGRAM_CROP, need])
            cash -= cost
            state["seed_ordered"] = True
            state["seed_before"] = held
            telemetry["seed_requests"] += need
    # Preserve the commitment executor's inventory-aware selling policy.
    for item in sorted(shed):
        if item not in SELLABLE or item in ANIMALS:
            continue
        quantity = shed[item]
        if item == "WHEAT":
            quantity = max(0, min(quantity, wheat_total - reserve))
        if quantity > 0:
            orders.append(["SELL", item, int(quantity)])
            cash += int(quantity) * float(prices.get(item, 1))

    # Buy the program seeds only after all mandatory sales and feed reserves
    # are accounted for.  A small buffer protects the next day's operations.
    # Reuse the base workload hire policy, capped conservatively.  This can
    # add hands only for visible mandatory workload and does not target the
    # optional cohort itself.
    plants = _tile_plants(farm)
    workload = len(plants) * 1.35 + len(animals) * 2.2
    target_units = max(1, int((workload + 5.0) // 6.0)) if plants or animals else 0
    desired_hands = min(PROGRAM_MAX_HANDS, max(0, target_units - 1))
    current = int(farm.get("hires_today", 0))
    needed = max(0, desired_hands - len(farm.get("hands", [])))
    for offset in range(needed):
        cost = _fib(current + offset)
        if cash < cost or len(orders) >= 10:
            break
        orders.append(["HIRE"])
        cash -= cost

    if wheat_total < reserve and animal_total and len(orders) < 10:
        price = max(1.0, float(prices.get("WHEAT", 25)))
        quantity = min(int(reserve - wheat_total), max(0, int((cash - 1.0) // price)))
        if quantity > 0:
            orders.append(["BUY_PRODUCT", "WHEAT", quantity])
    return orders[:10]


def _update_telemetry(obs, tasks):
    records = list(state.get("target_records", {}).values())
    telemetry.update({
        "last_step": int(obs.get("step", 0)),
        "targets": [list(position) for position in state.get("targets", [])],
        "requested": len(records),
        "planted_count": sum(bool(record["planted"]) for record in records),
        "matured_count": sum(bool(record["matured"]) for record in records),
        "harvested_count": sum(bool(record["harvested"]) for record in records),
        "failed_count": sum(bool(record["failed"]) for record in records),
        "realization_rate": (sum(bool(record["harvested"]) for record in records) / len(records)) if records else 0.0,
        "pending_tasks": len(tasks),
        "target_records": deepcopy(records),
    })


def agent(obs):
    step = int(obs.get("step", 0))
    if not state or step == 0 or step <= int(state.get("last_step", -1)):
        _reset(obs)
    state["last_step"] = step
    telemetry["calls"] += 1
    _remember_tiles(obs)

    # Shadow calls are used only to learn recent vacancies.  Reset scheduler
    # cursors at the actual takeover so stale feed-carrier or worker-zone
    # state from ignored actions cannot perturb the passive continuation.
    takeover_step = int(getattr(agent, "takeover_step", TAKEOVER_MIN_STEP))
    if step >= takeover_step and not state.get("live_started"):
        state["live_started"] = True
        state["feed_mode"] = None
        state["program_units"] = []
        state["program_units_day"] = None
        state["program_previous"] = {}
        state["seed_ordered"] = False
        state["targets"] = []
        state["target_records"] = {}
    _observe_program(obs)

    if _can_admit(obs):
        _admit(obs)
    elif int(obs.get("day", 0)) > PROGRAM_LAST_ADMISSION_DAY:
        state["admission_closed"] = True

    active = any(not record.get("harvested") and not record.get("failed") for record in state.get("target_records", {}).values())
    if not active:
        # No optional program: delegate to a fresh commitment executor.  This
        # keeps the no-program path action-equivalent to the passive control;
        # a shadow history must never perturb its feed or hire cursors.
        action = _BASE["agent"](obs)
        telemetry["last_step"] = step
        _update_telemetry(obs, [])
        return action
    else:
        tasks = _merge_tasks(obs)
        tasks.sort(key=lambda task: (-_task_score(task, obs), int(task["y"]), int(task["x"])))
        actions = _assign_actions(obs, tasks)
        orders = _market_orders(obs)
        if int(obs.get("hour", 0)) >= 21 and any(task["kind"] in {"FEED", "WATER"} for task in tasks):
            telemetry["late_critical"] += 1
            telemetry["recovery_events"] += 1

    _update_telemetry(obs, tasks)
    return {"farmer": actions[0], "hands": actions[1:], "market": orders}


agent.telemetry = telemetry
agent.description = "coherent checkpoint owner with two capital-gated replacement melons"
agent.state = state
agent.takeover_step = TAKEOVER_MIN_STEP
