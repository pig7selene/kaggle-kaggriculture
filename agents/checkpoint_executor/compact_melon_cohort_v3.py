"""Compact melon cohort with one explicitly reserved extra farm hand.

This variant isolates whether v1/v2's weak realization came from worker
capacity rather than crop economics.  It otherwise keeps the same four-tile,
capital-gated MELON commitment and delegates all existing commitments to the
safe checkpoint executor.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from runpy import run_path

ROOT = Path(__file__).resolve().parents[2]
_M = run_path(str(ROOT / "agents/checkpoint_executor/compact_melon_cohort_v2.py"))
_base_agent = _M["_base_agent"]
_tile_animals = _M["_tile_animals"]
_distance = _M["_distance"]
_step_toward = _M["_step_toward"]
SHED_TILES = _M["SHED_TILES"]
COHORT_SIZE = 4
CROP = "MELON"
SEED_COST = 80
FIRST_YIELD_DAY = 10
MAX_COMMIT_STEP = 600
UNIT_ACTIONS = _M["UNIT_ACTIONS"]

state = {}
telemetry = {}


def _positions(obs):
    farm = obs["farms"][obs["player"]]
    return [farm["farmer"], *farm.get("hands", [])]


def _tile_at(obs, pos):
    farm = obs["farms"][obs["player"]]; x, y = map(int, pos)
    rows = farm.get("tiles", [])
    return rows[y][x] if 0 <= y < len(rows) and 0 <= x < len(rows[y]) else None


def _empty(farm):
    return [(x, y) for y, row in enumerate(farm.get("tiles", [])) for x, tile in enumerate(row)
            if tile is None and (x, y) not in SHED_TILES]


def _feed_reserve(obs):
    farm = obs["farms"][obs["player"]]; animals = _tile_animals(farm)
    day = int(obs.get("day", 0)); step = int(obs.get("step", 0))
    price = float(obs.get("market", {}).get("prices", {}).get("WHEAT", 25))
    remaining = max(0, 30 - day); due = sum(not bool(t.get("fed_today", False)) for _, _, t in animals)
    units = due + len(animals) * max(0, remaining - 1) if step >= 648 else len(animals) * 2
    return float(units) * price


def _targets(obs):
    empty = _empty(obs["farms"][obs["player"]])
    if len(empty) < COHORT_SIZE:
        return []
    center = (4, 4); ordered = sorted(empty, key=lambda p: (_distance(p, center), p[1], p[0]))
    chosen = [ordered[0]]
    while len(chosen) < COHORT_SIZE:
        chosen.append(min((p for p in ordered if p not in chosen),
                          key=lambda p: (min(_distance(p, q) for q in chosen), _distance(p, center), p[1], p[0])))
    return chosen


def _idle(action, obs):
    pos = _positions(obs); actions = [action.get("farmer", ["PASS"]), *action.get("hands", [])]
    return [i for i, value in enumerate(actions) if i < len(pos) and isinstance(value, list) and value and value[0] == "PASS"]


def _replace(action, index, value):
    if index == 0:
        action["farmer"] = value
    else:
        hands = list(action.get("hands", []))
        if index - 1 < len(hands):
            hands[index - 1] = value; action["hands"] = hands


def _admit(obs, action):
    if state.get("targets") or int(obs.get("step", 0)) >= MAX_COMMIT_STEP or int(obs.get("day", 0)) > 18:
        return False
    private = obs.get("private", {}); farm = obs["farms"][obs["player"]]
    if int(private.get("seeds", {}).get(CROP, 0)) > 0:
        return False
    targets = _targets(obs)
    if len(targets) < COHORT_SIZE or len(_idle(action, obs)) < 1:
        return False
    price = float(obs.get("market", {}).get("prices", {}).get(CROP, 250))
    money = float(farm.get("money", 0))
    return price >= 180.0 and money >= COHORT_SIZE * SEED_COST + _feed_reserve(obs) + 500.0


def _request_hand(obs, action):
    if not state.get("targets") or state.get("hire_requested"):
        return
    orders = list(action.get("market", [])); farm = obs["farms"][obs["player"]]
    if len(orders) >= 10 or any(isinstance(o, list) and o and o[0] == "HIRE" for o in orders):
        return
    # HIRE costs start at one and reset daily; reserve a generous cushion so
    # the extra hand cannot turn into a feed-shortfall intervention.
    if float(farm.get("money", 0)) < COHORT_SIZE * SEED_COST + _feed_reserve(obs) + 550.0:
        return
    orders.append(["HIRE"]); action["market"] = orders[:10]; state["hire_requested"] = True
    telemetry["extra_hire_requests"] += 1


def _seed_order(obs, action):
    if not state.get("targets") or state.get("seed_ordered") or int(obs.get("step", 0)) >= MAX_COMMIT_STEP:
        return
    private = obs.get("private", {})
    if int(private.get("seeds", {}).get(CROP, 0)) > 0:
        return
    orders = list(action.get("market", []))
    if len(orders) >= 10 or any(isinstance(o, list) and o and o[0] in {"BUY_PRODUCT", "BUY_ANIMAL", "BUY_LAND", "HIRE"} for o in orders):
        return
    farm = obs["farms"][obs["player"]]
    if float(farm.get("money", 0)) < COHORT_SIZE * SEED_COST + _feed_reserve(obs) + 500.0:
        return
    orders.append(["BUY_SEED", CROP, COHORT_SIZE]); action["market"] = orders[:10]
    state["seed_ordered"] = True; telemetry["seed_requests"] += 1


def _observe(obs):
    if not state.get("targets"):
        return
    day = int(obs.get("day", 0)); private = obs.get("private", {})
    if state.get("seed_ordered") and not state.get("seed_acquired") and int(private.get("seeds", {}).get(CROP, 0)) >= COHORT_SIZE:
        state["seed_acquired"] = True; telemetry["seed_acquired"] += 1
    for target in state["targets"]:
        tile = _tile_at(obs, target); prev = state.setdefault("last_tiles", {}).get(target)
        planted = state.setdefault("planted", {}); harvested = state.setdefault("harvested", {})
        if isinstance(tile, dict) and tile.get("kind") == "PLANT" and tile.get("crop") == CROP:
            if not planted.get(target): planted[target] = True; telemetry["planted"] += 1
            if tile.get("watered_today"):
                marker = (day, target); marks = state.setdefault("water_marks", set())
                if marker not in marks: marks.add(marker); telemetry["watered_actions"] += 1
        elif planted.get(target) and not harvested.get(target):
            if isinstance(prev, dict) and prev.get("kind") == "PLANT" and tile is None:
                harvested[target] = True; telemetry["harvested"] += 1; telemetry["harvest_units_lower_bound"] += int(prev.get("yield_units", 0))
            elif isinstance(tile, dict) and tile.get("kind") == "WEED":
                state.setdefault("failed", {})[target] = True; telemetry["failed_weeds"] += 1
        state["last_tiles"][target] = deepcopy(tile)


def _tasks(obs):
    day = int(obs.get("day", 0)); tasks = []
    planted = state.setdefault("planted", {}); harvested = state.setdefault("harvested", {})
    for target in state.get("targets", []):
        tile = _tile_at(obs, target)
        if isinstance(tile, dict) and tile.get("kind") == "PLANT" and tile.get("crop") == CROP:
            if not tile.get("watered_today", False): tasks.append((target, "WATER"))
            elif int(tile.get("yield_units", 0)) > 0 and day - int(tile.get("planted_day", day)) >= FIRST_YIELD_DAY: tasks.append((target, "HARVEST"))
        elif tile is None and state.get("seed_acquired") and not planted.get(target) and not harvested.get(target): tasks.append((target, "PLANT"))
    return tasks


def _override(obs, action):
    tasks = _tasks(obs); idle = _idle(action, obs)
    if not tasks or not idle: return
    positions = _positions(obs); owners = state.setdefault("owners", [])
    # Include the newly spawned last hand and retain any owner that is still
    # present.  Owners only act while the base emits PASS for them.
    ordered = [i for i in owners if i in idle] + [i for i in idle if i not in owners]
    ordered = sorted(ordered, key=lambda i: (i == 0, i))[:min(3, len(ordered))]
    assigned = set()
    for index in ordered:
        available = [task for task in tasks if task[0] not in assigned]
        if not available: break
        target, desired = min(available, key=lambda item: (_distance(positions[index], item[0]), item[0][1], item[0][0]))
        assigned.add(target)
        if index not in owners: owners.append(index)
        if tuple(map(int, positions[index])) == tuple(map(int, target)):
            _replace(action, index, [desired] if desired != "PLANT" else ["PLANT", CROP]); telemetry["optional_overrides"] += 1
        else:
            _replace(action, index, _step_toward(positions[index], target)); telemetry["optional_moves"] += 1


def _reset(obs):
    state.clear(); state.update({"last_step": int(obs.get("step", 0)) - 1, "targets": [], "hire_requested": False,
                                 "seed_ordered": False, "seed_acquired": False, "planted": {}, "harvested": {},
                                 "failed": {}, "last_tiles": {}, "water_marks": set(), "owners": []})
    telemetry.clear(); telemetry.update({"calls": 0, "admission_requests": 0, "extra_hire_requests": 0,
                                         "seed_requests": 0, "seed_acquired": 0, "planted": 0, "watered_actions": 0,
                                         "harvested": 0, "harvest_units_lower_bound": 0, "failed_weeds": 0,
                                         "optional_moves": 0, "optional_overrides": 0})


def agent(obs):
    step = int(obs.get("step", 0))
    if not state or step == 0 or step <= int(state.get("last_step", -1)): _reset(obs)
    state["last_step"] = step; telemetry["calls"] += 1
    action = deepcopy(_base_agent(obs)); _observe(obs)
    if not state.get("targets") and _admit(obs, action):
        state["targets"] = _targets(obs); telemetry["admission_requests"] += 1
    _request_hand(obs, action); _seed_order(obs, action); _override(obs, action)
    expected = len(obs["farms"][obs["player"]].get("hands", [])); hands = list(action.get("hands", []))
    hands.extend([["PASS"]] * max(0, expected - len(hands))); action["hands"] = hands[:expected]
    if not isinstance(action.get("farmer"), list) or not action["farmer"] or action["farmer"][0] not in UNIT_ACTIONS: action["farmer"] = ["PASS"]
    if not isinstance(action.get("market"), list): action["market"] = []
    action["market"] = action["market"][:10]
    telemetry.update({"targets": [list(p) for p in state.get("targets", [])], "planted_count": sum(bool(v) for v in state.get("planted", {}).values()),
                      "harvested_count": sum(bool(v) for v in state.get("harvested", {}).values()), "seed_ordered_state": bool(state.get("seed_ordered")),
                      "seed_acquired_state": bool(state.get("seed_acquired"))})
    return action


agent.telemetry = telemetry
agent.description = "safe checkpoint executor plus one extra-hand four-melon cohort"
