"""Capital-gated single-melon lifecycle on top of the safe checkpoint executor.

This is an intentionally narrow oracle-style probe.  It asks whether one
premium crop can recover enough value to justify a larger commitment executor.
The base executor remains authoritative for every observed commitment; only a
nearby idle worker may be borrowed for this one melon.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from runpy import run_path


ROOT = Path(__file__).resolve().parents[2]
_BASE = run_path(str(ROOT / "agents/checkpoint_executor/commitment_executor_v1.py"))
_base_agent = _BASE["agent"]
_tile_plants = _BASE["_tile_plants"]
_tile_animals = _BASE["_tile_animals"]
_distance = _BASE["_distance"]
_step_toward = _BASE["_step_toward"]
SHED_TILES = _BASE["SHED_TILES"]

state = {}
telemetry = {}
CROP = "MELON"
SEED_COST = 80
FIRST_YIELD_DAY = 10
MAX_STEP = 648
UNIT_ACTIONS = {"NORTH", "SOUTH", "EAST", "WEST", "PASS", "PLANT", "WATER", "HARVEST", "FERTILIZE", "DIG", "BUILD_COOP", "BUILD_PASTURE", "PICKUP", "DROP", "PLACE", "FEED", "CARE", "COLLECT_FERTILIZER"}


def _empty_tiles(farm):
    return [(x, y) for y, row in enumerate(farm.get("tiles", []))
            for x, tile in enumerate(row) if tile is None and (x, y) not in SHED_TILES]


def _positions(obs):
    farm = obs["farms"][obs["player"]]
    return [farm["farmer"], *farm.get("hands", [])]


def _tile_at(obs, pos):
    farm = obs["farms"][obs["player"]]
    x, y = map(int, pos)
    rows = farm.get("tiles", [])
    return rows[y][x] if 0 <= y < len(rows) and 0 <= x < len(rows[y]) else None


def _feed_reserve(obs):
    farm = obs["farms"][obs["player"]]
    animals = _tile_animals(farm)
    day = int(obs.get("day", 0))
    step = int(obs.get("step", 0))
    price = float(obs.get("market", {}).get("prices", {}).get("WHEAT", 25))
    remaining = max(0, 30 - day)
    due = sum(not tile.get("fed_today", False) for _, _, tile in animals)
    units = due + len(animals) * max(0, remaining - 1) if step >= MAX_STEP else len(animals) * 2
    return units * price


def _preferred_idle(action, obs, target):
    positions = _positions(obs)
    actions = [action.get("farmer", ["PASS"]), *action.get("hands", [])]
    candidates = []
    for index, value in enumerate(actions):
        if index >= len(positions) or not isinstance(value, list) or not value or value[0] != "PASS":
            continue
        candidates.append((index == 0, int(_distance(positions[index], target)), index))
    if not candidates:
        return None
    # Prefer a hand, then the nearest route.
    return min(candidates, key=lambda item: (item[0], item[1], item[2]))[2]


def _replace(action, index, value):
    if index == 0:
        action["farmer"] = value
    else:
        hands = list(action.get("hands", []))
        if index - 1 < len(hands):
            hands[index - 1] = value
            action["hands"] = hands


def _observe(obs):
    target = state.get("target")
    if target is None:
        return
    tile = _tile_at(obs, target)
    previous = state.get("last_tile")
    seeds = int(obs.get("private", {}).get("seeds", {}).get(CROP, 0))
    if state.get("seed_ordered") and not state.get("seed_acquired") and seeds > int(state.get("seed_before", 0)):
        state["seed_acquired"] = True
        telemetry["seed_acquired"] += 1
    if isinstance(tile, dict) and tile.get("kind") == "PLANT" and tile.get("crop") == CROP:
        if not state.get("planted"):
            state["planted"] = True
            state["phase"] = "growing"
            telemetry["planted"] += 1
        if tile.get("watered_today"):
            marker = (int(obs.get("day", 0)), target)
            if marker not in state.setdefault("water_marks", set()):
                state["water_marks"].add(marker)
                telemetry["watered_days"] += 1
    elif state.get("planted") and not state.get("harvested"):
        if isinstance(previous, dict) and previous.get("kind") == "PLANT" and tile is None:
            state["harvested"] = True
            state["phase"] = "realized"
            telemetry["harvested"] += 1
            telemetry["harvest_units_lower_bound"] = max(telemetry["harvest_units_lower_bound"], int(previous.get("yield_units", 0)))
        elif isinstance(tile, dict) and tile.get("kind") == "WEED":
            state["failed"] = True
            state["phase"] = "failed"
            telemetry["failed_weeds"] += 1
    state["last_tile"] = deepcopy(tile)


def _admit(obs, action):
    if int(obs.get("step", 0)) >= MAX_STEP or state.get("target") is not None:
        return
    farm = obs["farms"][obs["player"]]
    private = obs.get("private", {})
    if int(private.get("seeds", {}).get(CROP, 0)) > 0:
        return
    price = float(obs.get("market", {}).get("prices", {}).get(CROP, 250))
    if price < 200.0:
        return
    existing = sum(1 for _, _, tile in _tile_plants(farm) if tile.get("crop") == CROP)
    if existing >= 16:
        return
    empty = _empty_tiles(farm)
    if not empty:
        return
    reserve = _feed_reserve(obs)
    if float(farm.get("money", 0)) < SEED_COST + reserve + 250.0:
        return
    target = min(empty, key=lambda p: (_distance(p, (4, 4)), p[1], p[0]))
    if _preferred_idle(action, obs, target) is None:
        return
    state["target"] = target
    state["phase"] = "admitted"
    telemetry["admission_requests"] += 1


def _seed_order(obs, action):
    if state.get("target") is None or state.get("seed_ordered") or int(obs.get("step", 0)) >= MAX_STEP:
        return
    market = list(action.get("market", []))
    if len(market) >= 10:
        return
    private = obs.get("private", {})
    if int(private.get("seeds", {}).get(CROP, 0)) > 0:
        return
    if any(isinstance(order, list) and order and order[0] in {"BUY_PRODUCT", "BUY_ANIMAL", "BUY_LAND"} for order in market):
        return
    farm = obs["farms"][obs["player"]]
    if float(farm.get("money", 0)) < SEED_COST + _feed_reserve(obs) + 250.0:
        return
    market.append(["BUY_SEED", CROP, 1])
    action["market"] = market[:10]
    state["seed_ordered"] = True
    state["seed_before"] = int(private.get("seeds", {}).get(CROP, 0))
    telemetry["seed_requests"] += 1


def _optional_route(obs, action):
    target = state.get("target")
    if target is None or state.get("harvested") or state.get("failed"):
        return
    tile = _tile_at(obs, target)
    day = int(obs.get("day", 0))
    if isinstance(tile, dict) and tile.get("kind") == "PLANT" and tile.get("crop") == CROP:
        age = day - int(tile.get("planted_day", day))
        desired = "WATER" if not tile.get("watered_today") else ("HARVEST" if int(tile.get("yield_units", 0)) > 0 and age >= FIRST_YIELD_DAY else None)
    elif tile is None and state.get("seed_acquired"):
        desired = "PLANT"
    else:
        desired = None
    if desired is None:
        return
    positions = _positions(obs)
    owner = state.get("owner")
    actions = [action.get("farmer", ["PASS"]), *action.get("hands", [])]
    if owner is None or owner >= len(positions):
        owner = _preferred_idle(action, obs, target)
        if owner is not None:
            state["owner"] = owner
    if owner is None or owner >= len(actions) or not isinstance(actions[owner], list) or not actions[owner] or actions[owner][0] != "PASS":
        return
    if tuple(map(int, positions[owner])) == tuple(map(int, target)):
        _replace(action, owner, [desired] if desired != "PLANT" else ["PLANT", CROP])
        telemetry["optional_overrides"] += 1
    else:
        _replace(action, owner, _step_toward(positions[owner], target))
        telemetry["optional_moves"] += 1


def _reset(obs):
    state.clear()
    state.update({"last_step": int(obs.get("step", 0)) - 1, "target": None, "phase": "idle", "seed_ordered": False,
                  "seed_acquired": False, "seed_before": 0, "planted": False, "harvested": False, "failed": False,
                  "last_tile": None, "water_marks": set(), "owner": None})
    telemetry.clear()
    telemetry.update({"calls": 0, "admission_requests": 0, "seed_requests": 0, "seed_acquired": 0, "planted": 0,
                      "watered_days": 0, "harvested": 0, "harvest_units_lower_bound": 0, "failed_weeds": 0,
                      "optional_moves": 0, "optional_overrides": 0, "phase": "idle", "target": None,
                      "drop_actions": 0, "sold_melon_units": 0})


def agent(obs):
    step = int(obs.get("step", 0))
    if not state or step == 0 or step <= int(state.get("last_step", -1)):
        _reset(obs)
    state["last_step"] = step
    telemetry["calls"] += 1
    action = deepcopy(_base_agent(obs))
    _observe(obs)
    _admit(obs, action)
    _seed_order(obs, action)
    _optional_route(obs, action)
    units = [action.get("farmer", []), *action.get("hands", [])]
    telemetry["drop_actions"] += sum(1 for value in units if isinstance(value, list) and value and value[0] == "DROP")
    if state.get("harvested"):
        for order in action.get("market", []):
            if isinstance(order, list) and len(order) >= 3 and order[0] == "SELL" and order[1] == CROP:
                telemetry["sold_melon_units"] += max(0, int(order[2]))
    expected_hands = len(obs["farms"][obs["player"]].get("hands", []))
    hands = list(action.get("hands", [])); hands.extend([["PASS"]] * max(0, expected_hands - len(hands)))
    action["hands"] = hands[:expected_hands]
    if not isinstance(action.get("farmer"), list) or not action["farmer"] or action["farmer"][0] not in UNIT_ACTIONS:
        action["farmer"] = ["PASS"]
    if not isinstance(action.get("market"), list):
        action["market"] = []
    action["market"] = action["market"][:10]
    telemetry.update({"phase": state.get("phase"), "target": state.get("target"), "seed_ordered_state": bool(state.get("seed_ordered")),
                      "seed_acquired_state": bool(state.get("seed_acquired")), "planted_state": bool(state.get("planted")),
                      "harvested_state": bool(state.get("harvested"))})
    return action


agent.telemetry = telemetry
agent.description = "safe checkpoint executor plus one capital-gated melon lifecycle"

