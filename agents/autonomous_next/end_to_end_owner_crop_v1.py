"""End-to-end owner with one pre-reserved, capital-gated wheat lifecycle.

The frozen economic route remains authoritative.  A single farmer slot is
reserved at turn zero; after step 240 it may execute exactly one additional
WHEAT cycle, but only on base PASS turns and only after all visible animal
feed/care and crop deadline commitments are clear.  No route action is
discarded or reordered, and no land, animals, fertilizer, or economic policy
is changed.
"""

from copy import deepcopy
from pathlib import Path
from runpy import run_path


ROOT = Path(__file__).resolve().parents[2]
BASE = run_path(str(ROOT / "agents/top50_distilled/top50_observable_portfolio.py"))["agent"]

SHED_TILES = {(4, 4), (5, 4), (4, 5), (5, 5)}
MOVES = {"NORTH", "SOUTH", "EAST", "WEST"}
PROGRAM = "WHEAT"
SEED_COST = 10
FIRST_YIELD_DAY = 2
START_STEP = 240
LAST_ADMISSION_STEP = 432
LIQUIDATION_STEP = 648

state = {}
telemetry = {}


def _reset(obs):
    state.clear()
    state.update({
        "last_step": int(obs.get("step", 0)) - 1,
        "reserved_worker": 0,
        "reserved_crop": PROGRAM,
        "reservation_start": START_STEP,
        "reservation_end": LIQUIDATION_STEP,
        "target": None,
        "stage": "reserved",
        "seed_ordered": False,
        "seed_before": 0,
        "planted_step": None,
        "harvested": False,
        "sold": False,
        "harvest_units": 0,
        "sell_remaining": 0,
        "last_target_tile": None,
    })
    telemetry.clear()
    telemetry.update({
        "calls": 0,
        "reservation_planned_at": 0,
        "reserved_worker": 0,
        "admissions": 0,
        "seed_requests": 0,
        "plant_actions": 0,
        "water_actions": 0,
        "harvest_actions": 0,
        "drop_actions": 0,
        "sell_requests": 0,
        "overrides": 0,
        "moves": 0,
        "rejected_overrides": 0,
        "animal_blocked": 0,
        "deadline_blocked": 0,
        "harvest_units": 0,
    })


def _op(action):
    return action[0] if isinstance(action, list) and action else "PASS"


def _positions(obs):
    me = obs["farms"][obs["player"]]
    return [me["farmer"], *me.get("hands", [])]


def _tile(obs, position):
    me = obs["farms"][obs["player"]]
    x, y = map(int, position)
    rows = me.get("tiles", [])
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


def _has_unserviced_animal(obs):
    me = obs["farms"][obs["player"]]
    for row in me.get("tiles", []):
        for tile in row:
            if not isinstance(tile, dict) or not tile.get("animal"):
                continue
            if not tile.get("fed_today", False):
                return True
            if not tile.get("cared_today", False):
                return True
            if tile.get("fertilizer_available", False):
                return True
    return False


def _has_urgent_crop(obs):
    me = obs["farms"][obs["player"]]
    day = int(obs.get("day", 0))
    for row in me.get("tiles", []):
        for tile in row:
            if not isinstance(tile, dict) or tile.get("kind") != "PLANT":
                continue
            if not tile.get("watered_today", False) and int(tile.get("consecutive_unwatered", 0)) >= 1:
                return True
            crop = tile.get("crop")
            if int(tile.get("yield_units", 0)) > 0:
                first = 2 if crop in {"WHEAT", "CARROT"} else 10 if crop in {"MELON", "STRAWBERRY"} else 8
                if day - int(tile.get("planted_day", day)) >= first:
                    return True
    return False


def _empty_target(obs, action):
    me = obs["farms"][obs["player"]]
    occupied_by_route = set()
    units = [action.get("farmer", ["PASS"]), *list(action.get("hands", []))]
    positions = _positions(obs)
    for index, value in enumerate(units):
        if _op(value) == "PLANT" and index < len(positions):
            occupied_by_route.add(tuple(map(int, positions[index])))
    candidate = []
    for y, row in enumerate(me.get("tiles", [])):
        for x, tile in enumerate(row):
            if tile is None and (x, y) not in SHED_TILES and (x, y) not in occupied_by_route:
                candidate.append((x, y))
    if not candidate:
        return None
    farmer = tuple(map(int, me["farmer"]))
    return min(candidate, key=lambda p: (abs(p[0] - farmer[0]) + abs(p[1] - farmer[1]), p[1], p[0]))


def _replace(action, index, value):
    if index == 0:
        action["farmer"] = value
        return
    hands = list(action.get("hands", []))
    if index - 1 < len(hands):
        hands[index - 1] = value
        action["hands"] = hands


def _observe_target(obs):
    """Advance the lifecycle ledger from the real tile transition.

    The base route may harvest a reserved tile while the farmer is in transit.
    Treating that observed transition as a completed harvest prevents the
    owner from silently declaring success and losing the resulting inventory.
    """
    target = state.get("target")
    if target is None:
        return
    current = _tile(obs, target)
    previous = state.get("last_target_tile")
    if (
        isinstance(previous, dict)
        and previous.get("kind") == "PLANT"
        and previous.get("crop") == PROGRAM
        and current is None
        and int(previous.get("yield_units", 0)) > 0
    ):
        if not state.get("harvested"):
            state["harvested"] = True
            state["harvest_units"] = int(previous.get("yield_units", 0))
            state["sell_remaining"] = int(previous.get("yield_units", 0))
            telemetry["harvest_actions"] += 1
        state["stage"] = "to_shed"
    elif isinstance(current, dict) and current.get("kind") == "WEED" and state.get("stage") not in {"reserved", "acquire"}:
        state["stage"] = "done"
    state["last_target_tile"] = deepcopy(current)


def _can_override(obs, action):
    index = int(state["reserved_worker"])
    positions = _positions(obs)
    if index >= len(positions):
        return False
    if _op(([action.get("farmer", ["PASS"]), *list(action.get("hands", []))])[index]) != "PASS":
        return False
    # The base route can have many visible commitments while another unit is
    # already executing them.  Only deny the reserved slot when *no* other
    # unit has an executable commitment action this turn; this is the key
    # difference from the overly conservative checkpoint overlay, which
    # treated every ready tile as globally blocking.
    unit_actions = [action.get("farmer", ["PASS"]), *list(action.get("hands", []))]
    other_ops = {_op(value) for i, value in enumerate(unit_actions) if i != index}
    commitment_ops = {"FEED", "WATER", "HARVEST", "CARE", "COLLECT_FERTILIZER", "PICKUP", "DROP", "PLACE", "PLANT"}
    if _has_unserviced_animal(obs) and not (other_ops & commitment_ops):
        telemetry["animal_blocked"] += 1
        return False
    if _has_urgent_crop(obs) and not (other_ops & {"WATER", "HARVEST", "PLANT"}):
        telemetry["deadline_blocked"] += 1
        return False
    tile = _tile(obs, positions[index])
    # Never leave an animal tile, and never borrow a unit carrying a route
    # animal or wheat feed.  This keeps the reservation genuinely spare.
    if isinstance(tile, dict) and tile.get("animal"):
        return False
    invs = obs.get("private", {}).get("inventories", [])
    inv = invs[index] if index < len(invs) else {}
    if any(int(inv.get(item, 0)) > 0 for item in ("COW", "SHEEP", "GOOSE")):
        return False
    if int(inv.get("WHEAT", 0)) > 0 and state.get("stage") not in {"to_shed", "drop"}:
        return False
    return True


def _admit(obs, action):
    if state.get("stage") != "reserved":
        return False
    step = int(obs.get("step", 0))
    if step < START_STEP or step > LAST_ADMISSION_STEP:
        return False
    if int(obs.get("day", 0)) >= 19:
        return False
    target = _empty_target(obs, action)
    if target is None:
        return False
    me = obs["farms"][obs["player"]]
    if float(me.get("money", 0)) < 150:
        return False
    seeds = int(obs.get("private", {}).get("seeds", {}).get(PROGRAM, 0))
    market = list(action.get("market", []))
    if seeds <= 0 and len(market) >= 10:
        return False
    state["target"] = target
    state["stage"] = "acquire" if seeds <= 0 else "plant"
    state["seed_before"] = seeds
    state["seed_ordered"] = False
    telemetry["admissions"] += 1
    return True


def _append_seed_order(obs, action):
    if state.get("stage") != "acquire" or state.get("seed_ordered"):
        return
    market = list(action.get("market", []))
    if len(market) >= 10:
        return
    if any(isinstance(order, list) and order and order[0] == "BUY_SEED" and len(order) > 1 and order[1] == PROGRAM for order in market):
        return
    me = obs["farms"][obs["player"]]
    if float(me.get("money", 0)) < SEED_COST + 25:
        return
    market.append(["BUY_SEED", PROGRAM, 1])
    action["market"] = market[:10]
    state["seed_ordered"] = True
    telemetry["seed_requests"] += 1


def _observe_seed(obs):
    if state.get("stage") == "acquire":
        seeds = int(obs.get("private", {}).get("seeds", {}).get(PROGRAM, 0))
        if seeds > int(state.get("seed_before", 0)):
            state["stage"] = "plant"


def _program_action(obs):
    stage = state.get("stage")
    target = state.get("target")
    if stage in {None, "reserved", "acquire", "done"} or target is None:
        return None
    positions = _positions(obs)
    index = int(state["reserved_worker"])
    if index >= len(positions):
        return None
    position = tuple(map(int, positions[index]))
    tile = _tile(obs, position)
    target_tile = _tile(obs, target)
    day = int(obs.get("day", 0))
    if stage == "plant":
        if position != tuple(target):
            return _step_toward(position, target)
        if target_tile is None and int(obs.get("private", {}).get("seeds", {}).get(PROGRAM, 0)) > 0:
            state["stage"] = "maintain"
            state["planted_step"] = int(obs.get("step", 0))
            telemetry["plant_actions"] += 1
            return ["PLANT", PROGRAM]
        return ["PASS"]
    if stage == "maintain":
        if state.get("harvested"):
            state["stage"] = "to_shed"
            return None
        if target_tile is None:
            return None
        if isinstance(target_tile, dict) and target_tile.get("kind") == "PLANT":
            if not target_tile.get("watered_today", False):
                telemetry["water_actions"] += 1
                return ["WATER"]
            age = day - int(target_tile.get("planted_day", day))
            if age >= FIRST_YIELD_DAY and int(target_tile.get("yield_units", 0)) > 0:
                telemetry["harvest_actions"] += 1
                state["harvest_units"] = int(target_tile.get("yield_units", 0))
                state["sell_remaining"] = int(target_tile.get("yield_units", 0))
                telemetry["harvest_units"] += int(target_tile.get("yield_units", 0))
                state["stage"] = "to_shed"
                return ["HARVEST"]
        return ["PASS"]
    if stage == "to_shed":
        invs = obs.get("private", {}).get("inventories", [])
        inv = invs[index] if index < len(invs) else {}
        if int(inv.get(PROGRAM, 0)) <= 0:
            state["stage"] = "sell"
            return None
        nearest = min(SHED_TILES, key=lambda p: abs(position[0] - p[0]) + abs(position[1] - p[1]))
        if position != nearest:
            telemetry["moves"] += 1
            return _step_toward(position, nearest)
        state["stage"] = "drop"
        return ["DROP"]
    if stage == "drop":
        invs = obs.get("private", {}).get("inventories", [])
        inv = invs[index] if index < len(invs) else {}
        if int(inv.get(PROGRAM, 0)) > 0:
            telemetry["drop_actions"] += 1
            return ["DROP"]
        state["stage"] = "sell"
        return None
    if stage == "sell":
        state["stage"] = "done"
        return None
    return None


def _append_sell(obs, action):
    if state.get("stage") not in {"sell", "done"} or state.get("sold"):
        return
    shed = obs.get("private", {}).get("shed", {})
    quantity = min(int(shed.get(PROGRAM, 0)), int(state.get("sell_remaining", 0)))
    if quantity <= 0:
        return
    market = list(action.get("market", []))
    if len(market) >= 10:
        return
    if any(isinstance(order, list) and order and order[0] == "SELL" and len(order) > 1 and order[1] == PROGRAM for order in market):
        return
    market.append(["SELL", PROGRAM, quantity])
    action["market"] = market[:10]
    state["sold"] = True
    state["sell_remaining"] = max(0, int(state.get("sell_remaining", 0)) - quantity)
    telemetry["sell_requests"] += quantity


def agent(obs):
    step = int(obs.get("step", 0))
    if not state or step == 0 or step <= int(state.get("last_step", -1)):
        _reset(obs)
    state["last_step"] = step
    telemetry["calls"] += 1
    action = deepcopy(BASE(obs))
    _observe_target(obs)
    _observe_seed(obs)
    if _admit(obs, action):
        pass
    _append_seed_order(obs, action)
    if step >= START_STEP and step < LIQUIDATION_STEP and state.get("stage") not in {"reserved", "acquire", "done"}:
        index = int(state["reserved_worker"])
        if _can_override(obs, action):
            desired = _program_action(obs)
            if desired is not None and desired != ["PASS"]:
                _replace(action, index, desired)
                telemetry["overrides"] += 1
        else:
            telemetry["rejected_overrides"] += 1
    _append_sell(obs, action)
    # Preserve the base schema/cardinality exactly even if a route variant
    # emits a short hands list on a day transition.
    expected = len(obs["farms"][obs["player"]].get("hands", []))
    hands = list(action.get("hands", []))
    hands.extend([["PASS"]] * max(0, expected - len(hands)))
    action["hands"] = hands[:expected]
    if not isinstance(action.get("market"), list):
        action["market"] = []
    action["market"] = action["market"][:10]
    return action


agent.telemetry = telemetry
agent.description = "complete route owner with day-0 farmer reservation and one capital-gated wheat cycle"
agent.base = BASE
agent.debug_state = state
