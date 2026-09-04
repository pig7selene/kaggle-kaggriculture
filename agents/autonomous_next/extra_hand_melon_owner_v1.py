"""Pre-opening owner probe with a genuinely additional worker lane.

The earlier future-quadrant probe borrowed the route's tail hand and therefore
changed the inherited economy.  This candidate instead reserves one MELON
tile at step 0 and hires an additional hand during an otherwise open market
turn after first land unlock.  The extra hand alone owns the crop lifecycle;
all inherited units keep their original actions.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from runpy import run_path


ROOT = Path(__file__).resolve().parents[2]
BASE = run_path(str(ROOT / "agents/top50_distilled/top50_observable_portfolio.py"))["agent"]

CROP = "MELON"
SEED_COST = 80
FIRST_YIELD_DAY = 10
SHED_TILES = {(4, 4), (5, 4), (4, 5), (5, 5)}
NE_TILES = [(x, y) for y in range(0, 5) for x in range(5, 10)]
MOVES = {"NORTH", "SOUTH", "EAST", "WEST"}

state = {}
telemetry = {}


def _reset(obs):
    state.clear()
    state.update({
        "last_step": int(obs.get("step", 0)) - 1,
        "reserved_at": 0,
        "target": None,
        "stage": "reserved",
        "seed_ordered": False,
        "seed_before": 0,
        "seed_acquired": False,
        "hire_day": None,
        "hire_pending": False,
        "hands_before_hire": None,
        "extra_confirmed": False,
        "planted": False,
        "harvested": False,
        "failed": False,
        "harvest_units": 0,
        "sell_remaining": 0,
        "last_tile": None,
    })
    telemetry.clear()
    telemetry.update({
        "calls": 0,
        "reservation_planned_at": 0,
        "admissions": 0,
        "seed_requests": 0,
        "hire_requests": 0,
        "hire_days": 0,
        "plant_actions": 0,
        "water_actions": 0,
        "harvest_actions": 0,
        "harvest_units": 0,
        "sell_requests": 0,
        "overrides": 0,
        "moves": 0,
        "animal_blocked": 0,
        "deadline_blocked": 0,
        "failed_weeds": 0,
        "extra_confirmed": 0,
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


def _replace(action, index, value):
    if index == 0:
        action["farmer"] = value
    else:
        hands = list(action.get("hands", []))
        if index - 1 < len(hands):
            hands[index - 1] = value
            action["hands"] = hands


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


def _choose_target(obs):
    farm = obs["farms"][obs["player"]]
    empty = [p for p in NE_TILES if farm["tiles"][p[1]][p[0]] is None]
    if not empty:
        return None
    center = tuple(map(int, farm.get("farmer", [4, 4])))
    return min(empty, key=lambda p: (abs(p[0] - center[0]) + abs(p[1] - center[1]), p[1], p[0]))


def _urgent_deadline(obs):
    hour = int(obs.get("hour", 0))
    farm = obs["farms"][obs["player"]]
    for row in farm.get("tiles", []):
        for tile in row:
            if not isinstance(tile, dict):
                continue
            if tile.get("animal") and not tile.get("fed_today", False) and (hour >= 22 or int(tile.get("consecutive_unfed", 0)) >= 1):
                return True
            if tile.get("kind") == "PLANT" and not tile.get("watered_today", False) and (hour >= 22 or int(tile.get("consecutive_unwatered", 0)) >= 1):
                return True
    return False


def _admit(obs):
    if state.get("stage") != "reserved" or int(obs.get("day", 0)) < 6 or int(obs.get("day", 0)) > 16:
        return
    if "NE" not in obs["farms"][obs["player"]].get("unlocked_quadrants", []):
        return
    target = _choose_target(obs)
    if target is None:
        return
    farm = obs["farms"][obs["player"]]
    # Cover seed cost, one expensive late-day hire, and the route's feed
    # liability.  This is deliberately conservative and never borrows debt.
    if float(farm.get("money", 0)) < SEED_COST + 250.0:
        return
    state["target"] = target
    state["stage"] = "funding"
    telemetry["admissions"] += 1


def _append_hire(obs, action):
    if state.get("stage") not in {"funding", "plant", "grow", "to_shed", "sell"}:
        return
    day = int(obs.get("day", 0))
    hour = int(obs.get("hour", 0))
    if state.get("hire_day") == day or hour < 1 or state.get("hire_pending"):
        return
    market = list(action.get("market", []))
    if len(market) >= 10:
        return
    farm = obs["farms"][obs["player"]]
    hires = int(farm.get("hires_today", 0))
    a, b = 1, 1
    for _ in range(max(0, hires)):
        a, b = b, a + b
    cost = a
    # Leave a cash buffer for feed and the seed order.  A later hour is
    # retried if the route has not yet created a free market slot.
    if float(farm.get("money", 0)) < cost + 120.0:
        return
    market.append(["HIRE"])
    action["market"] = market[:10]
    state["hire_day"] = day
    state["hire_pending"] = True
    state["hands_before_hire"] = len(farm.get("hands", []))
    telemetry["hire_requests"] += 1
    telemetry["hire_days"] += 1


def _append_seed(obs, action):
    if state.get("stage") not in {"funding", "plant"} or state.get("seed_ordered"):
        return
    private = obs.get("private", {})
    current = int(private.get("seeds", {}).get(CROP, 0))
    if current > 0:
        state["seed_acquired"] = True
        state["stage"] = "plant" if state.get("extra_confirmed") else "funding"
        return
    market = list(action.get("market", []))
    if len(market) >= 10:
        return
    if any(isinstance(o, list) and o and o[0] in {"BUY_LAND", "BUY_ANIMAL", "BUY_PRODUCT"} for o in market):
        return
    money = float(obs["farms"][obs["player"]].get("money", 0))
    if money < SEED_COST + 180.0:
        return
    market.append(["BUY_SEED", CROP, 1])
    action["market"] = market[:10]
    state["seed_ordered"] = True
    state["seed_before"] = current
    telemetry["seed_requests"] += 1


def _observe(obs):
    target = state.get("target")
    if target is None:
        return
    current = _tile(obs, target)
    previous = state.get("last_tile")
    if state.get("hire_pending") and len(obs["farms"][obs["player"]].get("hands", [])) > int(state.get("hands_before_hire", 0)):
        state["hire_pending"] = False
        state["extra_confirmed"] = True
        telemetry["extra_confirmed"] += 1
        if state.get("seed_acquired"):
            state["stage"] = "plant"
    seeds = int(obs.get("private", {}).get("seeds", {}).get(CROP, 0))
    if state.get("seed_ordered") and seeds > int(state.get("seed_before", 0)):
        state["seed_acquired"] = True
        if state.get("extra_confirmed"):
            state["stage"] = "plant"
    if isinstance(current, dict) and current.get("kind") == "PLANT" and current.get("crop") == CROP:
        state["planted"] = True
        age = int(obs.get("day", 0)) - int(current.get("planted_day", obs.get("day", 0)))
        if age >= FIRST_YIELD_DAY and int(current.get("yield_units", 0)) > 0 and not state.get("harvested"):
            # Harvest transition is recorded on the next observation when the
            # tile becomes empty; this marker only keeps the lifecycle alive.
            pass
    elif state.get("planted") and not state.get("harvested"):
        if isinstance(previous, dict) and previous.get("kind") == "PLANT" and current is None and int(previous.get("yield_units", 0)) > 0:
            state["harvested"] = True
            units = int(previous.get("yield_units", 0))
            state["harvest_units"] = units
            state["sell_remaining"] += units
            state["stage"] = "to_shed"
            telemetry["harvest_actions"] += 1
            telemetry["harvest_units"] += units
        elif isinstance(current, dict) and current.get("kind") == "WEED":
            state["failed"] = True
            state["stage"] = "done"
            telemetry["failed_weeds"] += 1
    state["last_tile"] = deepcopy(current)


def _program_action(obs):
    target = state.get("target")
    if target is None or not state.get("extra_confirmed"):
        return None
    positions = _positions(obs)
    index = len(positions) - 1 if len(positions) >= 2 else None
    if index is None:
        return None
    position = tuple(map(int, positions[index]))
    tile = _tile(obs, target)
    stage = state.get("stage")
    if stage == "plant":
        if tile == "LOCKED":
            return None
        if tile is None and int(obs.get("private", {}).get("seeds", {}).get(CROP, 0)) > 0:
            if position != tuple(target):
                telemetry["moves"] += 1
                return _step_toward(position, target)
            telemetry["plant_actions"] += 1
            return ["PLANT", CROP]
        if isinstance(tile, dict) and tile.get("kind") == "PLANT":
            state["stage"] = "grow"
    if stage in {"plant", "grow"} or state.get("stage") == "grow":
        if isinstance(tile, dict) and tile.get("kind") == "PLANT" and tile.get("crop") == CROP:
            if not tile.get("watered_today", False):
                telemetry["water_actions"] += 1
                return ["WATER"]
            age = int(obs.get("day", 0)) - int(tile.get("planted_day", obs.get("day", 0)))
            if age >= FIRST_YIELD_DAY and int(tile.get("yield_units", 0)) > 0 and not state.get("harvested"):
                state["stage"] = "to_shed"
                telemetry["harvest_actions"] += 1
                telemetry["harvest_units"] += int(tile.get("yield_units", 0))
                state["harvested"] = True
                state["harvest_units"] = int(tile.get("yield_units", 0))
                state["sell_remaining"] += int(tile.get("yield_units", 0))
                return ["HARVEST"]
    if state.get("stage") == "to_shed":
        invs = obs.get("private", {}).get("inventories", [])
        inv = invs[index] if index < len(invs) else {}
        if int(inv.get(CROP, 0)) > 0:
            shed = min(SHED_TILES, key=lambda p: abs(position[0] - p[0]) + abs(position[1] - p[1]))
            if position != shed:
                telemetry["moves"] += 1
                return _step_toward(position, shed)
            return ["DROP"]
        state["stage"] = "sell"
    return None


def _protect_target(obs, action):
    target = state.get("target")
    if target is None:
        return
    positions = _positions(obs)
    for index, value in enumerate([action.get("farmer", ["PASS"]), *list(action.get("hands", []))]):
        if index >= len(positions) or index == len(positions) - 1:
            continue
        if tuple(map(int, positions[index])) == tuple(target) and _op(value) in {"PLANT", "HARVEST", "DIG"}:
            _replace(action, index, ["PASS"])


def _append_sell(obs, action):
    remaining = int(state.get("sell_remaining", 0))
    if remaining <= 0:
        return
    market = list(action.get("market", []))
    if len(market) >= 10:
        return
    quantity = min(remaining, int(obs.get("private", {}).get("shed", {}).get(CROP, 0)))
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
    _admit(obs)
    _append_hire(obs, action)
    _append_seed(obs, action)
    _protect_target(obs, action)
    if state.get("extra_confirmed") and not state.get("failed") and not _urgent_deadline(obs):
        index = len(_positions(obs)) - 1 if len(_positions(obs)) >= 2 else None
        if index is not None:
            desired = _program_action(obs)
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
agent.description = "pre-opening extra-hand owner: one NE melon tile with daily incremental hire"
agent.base = BASE
agent.debug_state = state

