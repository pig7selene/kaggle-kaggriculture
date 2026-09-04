"""Bounded pre-opening owner for a two-tile WHEAT cohort.

Unlike the earlier post-opening overlays, this candidate declares its worker,
tiles, seed budget, lifecycle and sale liability at step 0.  It still delegates
the rest of the economy to the frozen observable Top-50 portfolio.  The
reserved lane is the last currently hired unit; it is never borrowed for an
animal tile or an imminent crop deadline.  This is a falsifiable architecture
probe, not a deployment strategy.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from runpy import run_path


ROOT = Path(__file__).resolve().parents[2]
BASE = run_path(str(ROOT / "agents/top50_distilled/top50_observable_portfolio.py"))["agent"]

CROP = "WHEAT"
COHORT_SIZE = 2
SEED_COST = 10
FIRST_YIELD_DAY = 2
SHED_TILES = {(4, 4), (5, 4), (4, 5), (5, 5)}
# Reserve future-quadrant capacity from step 0.  The initial NW quadrant is
# filled by the inherited opening before a spare tile appears.
RESERVED_TARGETS = [(5, 0), (5, 1)]
UNIT_OPS = {
    "NORTH", "SOUTH", "EAST", "WEST", "PASS", "PLANT", "WATER", "HARVEST",
    "FERTILIZE", "DIG", "BUILD_COOP", "BUILD_PASTURE", "PICKUP", "DROP",
    "PLACE", "FEED", "CARE", "COLLECT_FERTILIZER",
}

state = {}
telemetry = {}


def _reset(obs):
    state.clear()
    state.update({
        "last_step": int(obs.get("step", 0)) - 1,
        "reserved_at": 0,
        "reserved_lane": "tail",
        "targets": list(RESERVED_TARGETS),
        "stage": "reserved",
        "seed_ordered": False,
        "seed_before": 0,
        "seed_acquired": False,
        "planted": [False, False],
        "harvested": [False, False],
        "failed": [False, False],
        "harvest_units": [0, 0],
        "sell_remaining": 0,
        "last_tiles": {},
    })
    telemetry.clear()
    telemetry.update({
        "calls": 0,
        "reservation_planned_at": 0,
        "admissions": 0,
        "seed_requests": 0,
        "plant_actions": 0,
        "water_actions": 0,
        "harvest_actions": 0,
        "harvest_units": 0,
        "sell_requests": 0,
        "overrides": 0,
        "moves": 0,
        "blocked": 0,
        "animal_blocked": 0,
        "deadline_blocked": 0,
        "failed_weeds": 0,
    })


def _op(action):
    return action[0] if isinstance(action, list) and action else "PASS"


def _positions(obs):
    farm = obs["farms"][obs["player"]]
    return [farm["farmer"], *farm.get("hands", [])]


def _tile(obs, position):
    farm = obs["farms"][obs["player"]]
    x, y = map(int, position)
    rows = farm.get("tiles", [])
    if 0 <= y < len(rows) and 0 <= x < len(rows[y]):
        return rows[y][x]
    return "LOCKED"


def _step_toward(origin, target):
    x, y = map(int, origin)
    tx, ty = map(int, target)
    if tx < x:
        return ["WEST"]
    if tx > x:
        return ["EAST"]
    if ty < y:
        return ["NORTH"]
    if ty > y:
        return ["SOUTH"]
    return ["PASS"]


def _replace(action, index, value):
    if index == 0:
        action["farmer"] = value
    else:
        hands = list(action.get("hands", []))
        if index - 1 < len(hands):
            hands[index - 1] = value
            action["hands"] = hands


def _unit_actions(action):
    return [action.get("farmer", ["PASS"]), *list(action.get("hands", []))]


def _select_targets(obs, action):
    """Choose compact empty tiles and exclude positions being planted now."""
    farm = obs["farms"][obs["player"]]
    positions = _positions(obs)
    route_plants = {
        tuple(map(int, positions[i]))
        for i, value in enumerate(_unit_actions(action))
        if i < len(positions) and _op(value) == "PLANT"
    }
    empty = []
    for y, row in enumerate(farm.get("tiles", [])):
        for x, tile in enumerate(row):
            if tile is None and (x, y) not in SHED_TILES and (x, y) not in route_plants:
                empty.append((x, y))
    if len(empty) < COHORT_SIZE:
        return []
    center = tuple(map(int, farm.get("farmer", [4, 4])))
    empty.sort(key=lambda p: (abs(p[0] - center[0]) + abs(p[1] - center[1]), p[1], p[0]))
    chosen = [empty[0]]
    while len(chosen) < COHORT_SIZE:
        chosen.append(min(
            (p for p in empty if p not in chosen),
            key=lambda p: (min(abs(p[0] - q[0]) + abs(p[1] - q[1]) for q in chosen), p[1], p[0]),
        ))
    return chosen


def _has_urgent_animal(obs):
    hour = int(obs.get("hour", 0))
    farm = obs["farms"][obs["player"]]
    for row in farm.get("tiles", []):
        for tile in row:
            if not isinstance(tile, dict) or not tile.get("animal"):
                continue
            if not tile.get("fed_today", False) and (hour >= 22 or int(tile.get("consecutive_unfed", 0)) >= 1):
                return True
    return False


def _has_urgent_crop(obs):
    hour = int(obs.get("hour", 0))
    farm = obs["farms"][obs["player"]]
    for row in farm.get("tiles", []):
        for tile in row:
            if not isinstance(tile, dict) or tile.get("kind") != "PLANT":
                continue
            if not tile.get("watered_today", False) and (hour >= 22 or int(tile.get("consecutive_unwatered", 0)) >= 1):
                return True
    return False


def _admit(obs, action):
    if state.get("stage") != "reserved":
        return
    # Execute the reservation only after the first land purchase unlocks NE;
    # the commitment itself was declared in _reset at step 0.
    if int(obs.get("day", 0)) < 6 or int(obs.get("day", 0)) > 12:
        return
    farm = obs["farms"][obs["player"]]
    if any(_tile(obs, target) == "LOCKED" for target in RESERVED_TARGETS):
        return
    if any(_tile(obs, target) is not None for target in RESERVED_TARGETS):
        return
    if len(_positions(obs)) < 2 or len(action.get("market", [])) >= 10:
        return
    if float(farm.get("money", 0)) < COHORT_SIZE * SEED_COST + 100.0:
        return
    state["stage"] = "acquire"
    state["seed_before"] = int(obs.get("private", {}).get("seeds", {}).get(CROP, 0))
    telemetry["admissions"] += 1


def _append_seed_order(obs, action):
    if state.get("stage") != "acquire" or state.get("seed_ordered"):
        return
    market = list(action.get("market", []))
    if len(market) >= 10:
        return
    current = int(obs.get("private", {}).get("seeds", {}).get(CROP, 0))
    need = max(0, COHORT_SIZE - current)
    if need <= 0:
        state["seed_acquired"] = True
        state["stage"] = "plant"
        return
    # Never displace the route's opening land/animal/feed/hire orders.
    if any(isinstance(order, list) and order and order[0] in {"BUY_LAND", "BUY_ANIMAL", "BUY_PRODUCT"} for order in market):
        # The day-2 route has no such order, but retrying later keeps this
        # owner compatible with the other observable parent routes.
        return
    money = float(obs["farms"][obs["player"]].get("money", 0))
    if money < need * SEED_COST + 50.0:
        return
    market.append(["BUY_SEED", CROP, need])
    action["market"] = market[:10]
    state["seed_ordered"] = True
    telemetry["seed_requests"] += need


def _observe(obs):
    targets = state.get("targets", [])
    if not targets:
        return
    seeds = int(obs.get("private", {}).get("seeds", {}).get(CROP, 0))
    if state.get("seed_ordered") and seeds > int(state.get("seed_before", 0)):
        state["seed_acquired"] = True
        state["stage"] = "plant"
    day = int(obs.get("day", 0))
    for index, target in enumerate(targets):
        current = _tile(obs, target)
        previous = state.setdefault("last_tiles", {}).get(str(index))
        if isinstance(current, dict) and current.get("kind") == "PLANT" and current.get("crop") == CROP:
            state["planted"][index] = True
        elif state["planted"][index] and not state["harvested"][index]:
            if isinstance(previous, dict) and previous.get("kind") == "PLANT" and current is None:
                units = int(previous.get("yield_units", 0))
                state["harvested"][index] = True
                state["harvest_units"][index] = units
                state["sell_remaining"] += units
                telemetry["harvest_actions"] += 1
                telemetry["harvest_units"] += units
            elif isinstance(current, dict) and current.get("kind") == "WEED":
                state["failed"][index] = True
                telemetry["failed_weeds"] += 1
        state["last_tiles"][str(index)] = deepcopy(current)
    if targets and all(state["harvested"][i] or state["failed"][i] for i in range(len(targets))):
        state["stage"] = "sell"


def _reserved_index(obs):
    positions = _positions(obs)
    # The lane is deliberately the tail unit: new hands are appended by the
    # simulator each morning, so this gives the owner a stable, auditable slot
    # without depending on hidden worker IDs.
    return len(positions) - 1 if len(positions) >= 2 else None


def _can_use_reserved_lane(obs, action, index):
    actions = _unit_actions(action)
    positions = _positions(obs)
    if index is None or index >= len(actions) or index >= len(positions):
        return False
    tile = _tile(obs, positions[index])
    if isinstance(tile, dict) and tile.get("animal"):
        telemetry["animal_blocked"] += 1
        return False
    # A lane may not be borrowed while another unit is the only carrier of a
    # hard deadline.  This is intentionally conservative; silent no-ops are
    # preferable to an animal escape or crop death.
    if _has_urgent_animal(obs) or _has_urgent_crop(obs):
        telemetry["deadline_blocked"] += 1
        return False
    return True


def _target_action(obs, target_index):
    targets = state.get("targets", [])
    if target_index >= len(targets) or state["harvested"][target_index] or state["failed"][target_index]:
        return None
    target = tuple(targets[target_index])
    positions = _positions(obs)
    index = _reserved_index(obs)
    if index is None or index >= len(positions):
        return None
    position = tuple(map(int, positions[index]))
    tile = _tile(obs, target)
    seeds = int(obs.get("private", {}).get("seeds", {}).get(CROP, 0))
    if tile is None and not state["planted"][target_index] and seeds > 0:
        if position != target:
            telemetry["moves"] += 1
            return _step_toward(position, target)
        telemetry["plant_actions"] += 1
        return ["PLANT", CROP]
    if isinstance(tile, dict) and tile.get("kind") == "PLANT" and tile.get("crop") == CROP:
        if not tile.get("watered_today", False):
            telemetry["water_actions"] += 1
            return ["WATER"]
        age = int(obs.get("day", 0)) - int(tile.get("planted_day", obs.get("day", 0)))
        if age >= FIRST_YIELD_DAY and int(tile.get("yield_units", 0)) > 0:
            telemetry["harvest_actions"] += 1
            telemetry["harvest_units"] += int(tile.get("yield_units", 0))
            state["harvested"][target_index] = True
            state["harvest_units"][target_index] = int(tile.get("yield_units", 0))
            state["sell_remaining"] += int(tile.get("yield_units", 0))
            return ["HARVEST"]
        return ["PASS"]
    return None


def _protect_targets(obs, action):
    targets = {tuple(p) for p in state.get("targets", [])}
    if not targets:
        return
    positions = _positions(obs)
    for index, value in enumerate(_unit_actions(action)):
        if index >= len(positions) or index == _reserved_index(obs):
            continue
        if tuple(map(int, positions[index])) in targets and _op(value) in {"PLANT", "HARVEST", "DIG"}:
            _replace(action, index, ["PASS"])


def _append_sell(obs, action):
    remaining = int(state.get("sell_remaining", 0))
    if remaining <= 0:
        return
    market = list(action.get("market", []))
    if len(market) >= 10:
        return
    shed = int(obs.get("private", {}).get("shed", {}).get(CROP, 0))
    quantity = min(remaining, shed)
    if quantity <= 0:
        return
    market.append(["SELL", CROP, quantity])
    action["market"] = market[:10]
    state["sell_remaining"] = remaining - quantity
    telemetry["sell_requests"] += quantity


def agent(obs):
    step = int(obs.get("step", 0))
    if not state or step == 0 or step <= int(state.get("last_step", -1)):
        _reset(obs)
    state["last_step"] = step
    telemetry["calls"] += 1
    action = deepcopy(BASE(obs))
    _observe(obs)
    _admit(obs, action)
    _append_seed_order(obs, action)
    _protect_targets(obs, action)
    if state.get("stage") in {"plant", "sell"}:
        index = _reserved_index(obs)
        if _can_use_reserved_lane(obs, action, index):
            desired = None
            for target_index in range(len(state.get("targets", []))):
                if not state["planted"][target_index] or not state["harvested"][target_index]:
                    desired = _target_action(obs, target_index)
                    if desired is not None and desired != ["PASS"]:
                        break
            if desired is not None and desired != ["PASS"]:
                _replace(action, index, desired)
                telemetry["overrides"] += 1
    _append_sell(obs, action)
    expected = len(obs["farms"][obs["player"]].get("hands", []))
    hands = list(action.get("hands", []))
    hands.extend([["PASS"]] * max(0, expected - len(hands)))
    action["hands"] = hands[:expected]
    if not isinstance(action.get("market"), list):
        action["market"] = []
    action["market"] = action["market"][:10]
    return action


agent.telemetry = telemetry
agent.description = "pre-opening owner: day-0 reserved tail lane and two-tile wheat cohort"
agent.base = BASE
agent.debug_state = state
