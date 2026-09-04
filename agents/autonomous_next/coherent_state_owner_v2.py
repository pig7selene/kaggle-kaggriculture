"""Strict checkpoint owner: optional melons may use PASS units only.

This follows the v1 diagnostic by separating the shadow history executor from
the live cold-start commitment executor.  The live executor owns every base
crop, animal, feed, inventory, and terminal action.  The optional program can
override only a unit whose live base action is PASS, and only when the market
has a free slot for the seed purchase.  It is therefore a conservative proof
of state ownership rather than a general overlay.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from runpy import run_path


ROOT = Path(__file__).resolve().parents[2]
_HELPERS = run_path(str(ROOT / "agents/checkpoint_executor/commitment_executor_v1.py"))
_BASE_SHADOW = run_path(str(ROOT / "agents/checkpoint_executor/commitment_executor_v1.py"))
_BASE_LIVE = run_path(str(ROOT / "agents/checkpoint_executor/commitment_executor_v1.py"))

ANIMALS = _HELPERS["ANIMALS"]
CROPS = _HELPERS["CROPS"]
SELLABLE = _HELPERS["SELLABLE"]
SHED_TILES = set(_HELPERS["SHED_TILES"])
_tile_animals = _HELPERS["_tile_animals"]
_tile_plants = _HELPERS["_tile_plants"]
_distance = _HELPERS["_distance"]
_step_toward = _HELPERS["_step_toward"]
_count_inventory = _HELPERS["_count_inventory"]
_snapshot = _HELPERS["_snapshot"]

PROGRAM_CROP = "MELON"
PROGRAM_SIZE = 2
PROGRAM_SEED_COST = int(CROPS[PROGRAM_CROP]["seed"])
PROGRAM_FIRST_YIELD_DAY = int(CROPS[PROGRAM_CROP]["first"])
PROGRAM_LAST_ADMISSION_DAY = 16
PROGRAM_LAST_ADMISSION_HOUR = 12
PROGRAM_HARVEST_CUTOFF = 696
PROGRAM_CASH_BUFFER = 400.0
TAKEOVER_MIN_STEP = 240

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
    return {(x, y) for y, row in enumerate(farm.get("tiles", [])) for x, tile in enumerate(row) if tile is None and (x, y) not in SHED_TILES}


def _reset(obs):
    state.clear()
    state.update({
        "last_step": int(obs.get("step", 0)) - 1,
        "takeover_step": int(getattr(agent, "takeover_step", TAKEOVER_MIN_STEP)),
        "targets": [], "target_records": {}, "program_previous": {},
        "last_tiles": {}, "last_tile_steps": {}, "seed_ordered": False,
        "seed_before": 0, "live_started": False, "admission_closed": False,
    })
    telemetry.clear()
    telemetry.update({
        "calls": 0, "admission_requests": 0, "seed_requests": 0,
        "seed_acquired": 0, "planted": 0, "matured": 0, "harvested": 0,
        "harvest_units": 0, "failed_weeds": 0, "program_moves": 0,
        "program_actions": 0, "replacement_candidates": 0,
        "recent_vacancy_candidates": 0, "overrides": 0,
    })


def _remember_tiles(obs):
    step = int(obs.get("step", 0))
    for y, row in enumerate(obs["farms"][obs["player"]].get("tiles", [])):
        for x, tile in enumerate(row):
            if (x, y) in SHED_TILES:
                continue
            key = _key((x, y))
            previous = state["last_tiles"].get(key)
            if isinstance(previous, dict) and previous.get("kind") == "PLANT" and tile is None:
                state["last_tile_steps"][key] = step
            state["last_tiles"][key] = deepcopy(tile)


def _recent_candidates(obs):
    step = int(obs.get("step", 0))
    rows = []
    for position in _empty_tiles(obs):
        vacancy = state.get("last_tile_steps", {}).get(_key(position))
        recent = vacancy is not None and 0 <= step - int(vacancy) <= 48
        shed_distance = min(_distance(position, shed) for shed in SHED_TILES)
        rows.append((0 if recent else 1, shed_distance, position[1], position[0], position))
    rows.sort()
    telemetry["replacement_candidates"] = len(rows)
    telemetry["recent_vacancy_candidates"] = sum(row[0] == 0 for row in rows)
    return [row[-1] for row in rows]


def _cash(obs):
    farm = obs["farms"][obs["player"]]
    private = obs.get("private", {})
    prices = obs.get("market", {}).get("prices", {})
    value = float(farm.get("money", 0))
    for item, quantity in private.get("shed", {}).items():
        if item in SELLABLE and item not in ANIMALS:
            value += int(quantity) * float(prices.get(item, 1))
    return value


def _feed_reserve_value(obs):
    animals = _tile_animals(obs["farms"][obs["player"]])
    if not animals:
        return 0.0
    private = obs.get("private", {})
    held = int(private.get("shed", {}).get("WHEAT", 0)) + _count_inventory(private.get("inventories", []), "WHEAT")
    day = int(obs.get("day", 0))
    remaining = max(0, 30 - day)
    due = sum(not tile.get("fed_today", False) for _, _, tile in animals)
    required = due + len(animals) * (remaining - 1 if int(obs.get("step", 0)) >= 648 else 2)
    price = float(obs.get("market", {}).get("prices", {}).get("WHEAT", 25))
    return max(0, required - held) * price


def _can_admit(obs, base_action):
    if state.get("targets") or state.get("admission_closed"):
        return False
    step = int(obs.get("step", 0))
    takeover = int(getattr(agent, "takeover_step", TAKEOVER_MIN_STEP))
    day = int(obs.get("day", 0))
    hour = int(obs.get("hour", 0))
    if step < takeover or day > PROGRAM_LAST_ADMISSION_DAY:
        return False
    if day == PROGRAM_LAST_ADMISSION_DAY and hour > PROGRAM_LAST_ADMISSION_HOUR:
        return False
    if step + (PROGRAM_FIRST_YIELD_DAY + 2) * 24 >= PROGRAM_HARVEST_CUTOFF:
        return False
    # Require a recently vacated pair and at least two live units.  Untouched
    # empty tiles are not considered replacement capacity.
    candidates = _recent_candidates(obs)
    if telemetry["recent_vacancy_candidates"] < PROGRAM_SIZE or len(_positions(obs)) < 2:
        return False
    private = obs.get("private", {})
    if int(private.get("seeds", {}).get(PROGRAM_CROP, 0)) > 0:
        return False
    farm = obs["farms"][obs["player"]]
    required = PROGRAM_SIZE * PROGRAM_SEED_COST + PROGRAM_CASH_BUFFER + _feed_reserve_value(obs)
    if float(farm.get("money", 0)) < required:
        return False
    # A seed order must fit beside the current base market orders; never
    # discard a base SELL/BUY order merely to fund the optional program.
    unit_actions = [base_action.get("farmer", ["PASS"]), *base_action.get("hands", [])]
    idle_units = sum(bool(action) and action[0] == "PASS" for action in unit_actions)
    return len(base_action.get("market", [])) < 10 and idle_units >= PROGRAM_SIZE and _cash(obs) >= required


def _admit(obs):
    targets = _recent_candidates(obs)[:PROGRAM_SIZE]
    state["targets"] = list(targets)
    state["target_records"] = {_key(position): {"position": list(position), "planted": False, "planted_day": None, "maintained_days": [], "matured": False, "harvested": False, "harvest_units": 0, "failed": False} for position in targets}
    state["program_previous"] = {}
    state["seed_ordered"] = False
    state["seed_before"] = int(obs.get("private", {}).get("seeds", {}).get(PROGRAM_CROP, 0))
    state["admitted_step"] = int(obs.get("step", 0))
    telemetry["admission_requests"] += 1


def _observe_program(obs):
    if not state.get("targets"):
        return
    day = int(obs.get("day", 0))
    private = obs.get("private", {})
    seeds = int(private.get("seeds", {}).get(PROGRAM_CROP, 0))
    if state.get("seed_ordered") and seeds > int(state.get("seed_before", 0)):
        telemetry["seed_acquired"] += seeds - int(state.get("seed_before", 0))
        state["seed_before"] = seeds
    previous_tiles = state.setdefault("program_previous", {})
    for position in state["targets"]:
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
            age = day - int(tile.get("planted_day", day))
            if age >= PROGRAM_FIRST_YIELD_DAY and int(tile.get("yield_units", 0)) > 0 and not record["matured"]:
                record["matured"] = True
                telemetry["matured"] += 1
        elif record["planted"] and not record["harvested"]:
            if isinstance(previous, dict) and previous.get("kind") == "PLANT" and tile is None and int(previous.get("yield_units", 0)) > 0 and day - int(previous.get("planted_day", day)) >= PROGRAM_FIRST_YIELD_DAY:
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
    step = int(obs.get("step", 0))
    seeds = int(obs.get("private", {}).get("seeds", {}).get(PROGRAM_CROP, 0))
    tasks = []
    plant_candidates = []
    for position in state.get("targets", []):
        record = state["target_records"][_key(position)]
        if record["harvested"] or record["failed"]:
            continue
        tile = _tile_at(obs, position)
        if isinstance(tile, dict) and tile.get("kind") == "PLANT" and tile.get("crop") == PROGRAM_CROP:
            age = day - int(tile.get("planted_day", day))
            if not tile.get("watered_today", False):
                tasks.append({"kind": "WATER", "x": position[0], "y": position[1], "urgency": int(tile.get("consecutive_unwatered", 0))})
            elif int(tile.get("yield_units", 0)) > 0 and age >= PROGRAM_FIRST_YIELD_DAY and step < PROGRAM_HARVEST_CUTOFF:
                tasks.append({"kind": "HARVEST", "x": position[0], "y": position[1], "urgency": int(tile.get("yield_units", 0))})
        elif tile is None and not record["planted"]:
            plant_candidates.append(position)
    for position in plant_candidates[:seeds]:
        tasks.append({"kind": "PLANT", "x": position[0], "y": position[1]})
    return tasks


def _program_action(obs, index, task):
    positions = _positions(obs)
    if index >= len(positions):
        return ["PASS"]
    position = tuple(map(int, positions[index]))
    target = (int(task["x"]), int(task["y"]))
    if position != target:
        return _step_toward(position, target)
    tile = _tile_at(obs, target)
    if task["kind"] == "PLANT" and tile is None and int(obs.get("private", {}).get("seeds", {}).get(PROGRAM_CROP, 0)) > 0:
        return ["PLANT", PROGRAM_CROP]
    if task["kind"] == "WATER" and isinstance(tile, dict) and tile.get("kind") == "PLANT" and not tile.get("watered_today", False):
        return ["WATER"]
    if task["kind"] == "HARVEST" and isinstance(tile, dict) and int(tile.get("yield_units", 0)) > 0:
        return ["HARVEST"]
    return ["PASS"]


def _augment(base_action, obs):
    action = deepcopy(base_action)
    if not state.get("targets"):
        return action

    # A PASS from the live executor is not proof that the rest of the farm is
    # idle: its route may be relying on a later same-day visit.  Only borrow a
    # PASS lane when every non-program plant is already watered and no
    # non-program harvest is waiting.  Program tiles remain eligible for their
    # own WATER/HARVEST tasks, so this guard cannot strand the admitted cohort.
    target_positions = {tuple(position) for position in state.get("targets", [])}
    day = int(obs.get("day", 0))
    for y, row in enumerate(obs["farms"][obs["player"]].get("tiles", [])):
        for x, tile in enumerate(row):
            if not isinstance(tile, dict) or tile.get("kind") != "PLANT" or (x, y) in target_positions:
                continue
            if not tile.get("watered_today", False):
                return action
            crop = tile.get("crop")
            first = int(CROPS.get(crop, {}).get("first", 999))
            age = day - int(tile.get("planted_day", day))
            if int(tile.get("yield_units", 0)) > 0 and age >= first and int(obs.get("step", 0)) < PROGRAM_HARVEST_CUTOFF:
                return action
    # Put the program seed in a free market slot; base orders are never
    # removed or reordered.
    if not state.get("seed_ordered"):
        held = int(obs.get("private", {}).get("seeds", {}).get(PROGRAM_CROP, 0))
        need = max(0, PROGRAM_SIZE - held)
        farm = obs["farms"][obs["player"]]
        if need > 0 and len(action.get("market", [])) < 10 and float(farm.get("money", 0)) >= need * PROGRAM_SEED_COST + PROGRAM_CASH_BUFFER:
            action["market"] = [["BUY_SEED", PROGRAM_CROP, need], *action.get("market", [])][:10]
            state["seed_ordered"] = True
            telemetry["seed_requests"] += need
    tasks = _program_tasks(obs)
    if not tasks:
        return action
    unit_actions = [action.get("farmer", ["PASS"]), *action.get("hands", [])]
    available = [index for index, unit_action in enumerate(unit_actions) if unit_action and unit_action[0] == "PASS"]
    used = set()
    positions = _positions(obs)
    for index in available:
        choices = [(task_index, task) for task_index, task in enumerate(tasks) if task_index not in used]
        if not choices:
            break
        task_index, task = min(choices, key=lambda item: (_distance(positions[index], (item[1]["x"], item[1]["y"])), item[1]["y"], item[1]["x"]))
        candidate = _program_action(obs, index, task)
        if candidate[0] != "PASS":
            unit_actions[index] = candidate
            used.add(task_index)
            telemetry["overrides"] += 1
            telemetry["program_moves"] += int(candidate[0] in {"NORTH", "SOUTH", "EAST", "WEST"})
            telemetry["program_actions"] += int(candidate[0] not in {"NORTH", "SOUTH", "EAST", "WEST", "PASS"})
    action["farmer"] = unit_actions[0]
    action["hands"] = unit_actions[1:]
    return action


def _update_telemetry(obs):
    records = list(state.get("target_records", {}).values())
    telemetry.update({
        "last_step": int(obs.get("step", 0)),
        "targets": [list(position) for position in state.get("targets", [])],
        "requested": len(records),
        "planted_count": sum(bool(record["planted"]) for record in records),
        "matured_count": sum(bool(record["matured"]) for record in records),
        "harvested_count": sum(bool(record["harvested"]) for record in records),
        "failed_count": sum(bool(record["failed"]) for record in records),
        "realization_rate": sum(bool(record["harvested"]) for record in records) / len(records) if records else 0.0,
        "target_records": deepcopy(records),
    })


def agent(obs):
    step = int(obs.get("step", 0))
    if not state or step == 0 or step <= int(state.get("last_step", -1)):
        _reset(obs)
    state["last_step"] = step
    telemetry["calls"] += 1
    _remember_tiles(obs)
    takeover = int(getattr(agent, "takeover_step", TAKEOVER_MIN_STEP))
    if step < takeover:
        return _BASE_SHADOW["agent"](obs)
    if not state.get("live_started"):
        state["live_started"] = True
        state["targets"] = []
        state["target_records"] = {}
        state["program_previous"] = {}
        state["seed_ordered"] = False
        # _BASE_LIVE was never called during shadowing and is intentionally
        # cold-started at this checkpoint.
    base_action = _BASE_LIVE["agent"](obs)
    _observe_program(obs)
    if _can_admit(obs, base_action):
        _admit(obs)
    elif int(obs.get("day", 0)) > PROGRAM_LAST_ADMISSION_DAY:
        state["admission_closed"] = True
    active = any(not record["harvested"] and not record["failed"] for record in state.get("target_records", {}).values())
    output = _augment(base_action, obs) if active else base_action
    _update_telemetry(obs)
    return output


agent.telemetry = telemetry
agent.description = "strict checkpoint owner: two replacement melons on PASS units only"
agent.state = state
agent.takeover_step = TAKEOVER_MIN_STEP
