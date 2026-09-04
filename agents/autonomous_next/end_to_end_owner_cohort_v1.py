"""Pre-opening two-tile cohort owner.

This is the next capability test after ``end_to_end_owner_crop_v1``.  The
frozen replay portfolio remains the economic authority; at turn zero this
module reserves two worker slots and two WHEAT tiles.  After step 240 it may
run the complete lifecycle on those reservations, but only when the inherited
route gives each reserved unit a genuine PASS lane.  The cohort has no land,
animal, fertilizer, hiring, or market-policy changes beyond buying two wheat
seeds and selling the realized cohort output.
"""

from copy import deepcopy
from pathlib import Path
from runpy import run_path


ROOT = Path(__file__).resolve().parents[2]
BASE = run_path(str(ROOT / "agents/top50_distilled/top50_observable_portfolio.py"))["agent"]

PROGRAM = "WHEAT"
COHORT_SIZE = 2
SEED_COST = 10
FIRST_YIELD_DAY = 2
START_STEP = 240
LAST_ADMISSION_STEP = 360
LIQUIDATION_STEP = 648
SHED_TILES = {(4, 4), (5, 4), (4, 5), (5, 5)}

state = {}
telemetry = {}


def _reset(obs):
    state.clear()
    state.update({
        "last_step": int(obs.get("step", 0)) - 1,
        "reserved_workers": [0, 1],
        "reservation_planned_at": 0,
        "targets": [],
        "stage": "reserved",
        "seed_ordered": False,
        "seed_before": 0,
        "last_tiles": {},
        "harvest_units": [0, 0],
        "sell_remaining": 0,
        "harvested": [False, False],
        "failed": [False, False],
    })
    telemetry.clear()
    telemetry.update({
        "calls": 0,
        "reservation_planned_at": 0,
        "reserved_workers": [0, 1],
        "admissions": 0,
        "seed_requests": 0,
        "plant_actions": 0,
        "water_actions": 0,
        "harvest_actions": 0,
        "harvest_units": 0,
        "moves": 0,
        "drop_actions": 0,
        "sell_requests": 0,
        "overrides": 0,
        "blocked": 0,
        "animal_blocked": 0,
        "crop_deadline_blocked": 0,
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


def _route_plant_positions(obs, action):
    positions = _positions(obs)
    out = set()
    for index, value in enumerate(_unit_actions(action)):
        if index < len(positions) and _op(value) == "PLANT":
            out.add(tuple(map(int, positions[index])))
    return out


def _select_targets(obs, action):
    me = obs["farms"][obs["player"]]
    route_targets = _route_plant_positions(obs, action)
    farmer = tuple(map(int, me["farmer"]))
    candidates = []
    for y, row in enumerate(me.get("tiles", [])):
        for x, tile in enumerate(row):
            position = (x, y)
            if tile is None and position not in SHED_TILES and position not in route_targets:
                candidates.append(position)
    if len(candidates) < COHORT_SIZE:
        return []
    # Compact, connected-ish targets minimize the additional movement lane.
    candidates.sort(key=lambda p: (abs(p[0] - farmer[0]) + abs(p[1] - farmer[1]), p[1], p[0]))
    chosen = [candidates[0]]
    while len(chosen) < COHORT_SIZE:
        chosen.append(min(
            (p for p in candidates if p not in chosen),
            key=lambda p: (min(abs(p[0] - q[0]) + abs(p[1] - q[1]) for q in chosen), p[1], p[0]),
        ))
    return chosen


def _has_global_deadline(obs):
    me = obs["farms"][obs["player"]]
    for row in me.get("tiles", []):
        for tile in row:
            if not isinstance(tile, dict):
                continue
            if tile.get("animal") and not tile.get("fed_today", False):
                return "animal"
            if tile.get("kind") == "PLANT" and not tile.get("watered_today", False) and int(tile.get("consecutive_unwatered", 0)) >= 1:
                return "crop"
    return None


def _admit(obs, action):
    if state.get("stage") != "reserved":
        return False
    step = int(obs.get("step", 0))
    if step < START_STEP or step > LAST_ADMISSION_STEP:
        return False
    if int(obs.get("day", 0)) >= 16:
        return False
    me = obs["farms"][obs["player"]]
    if float(me.get("money", 0)) < 300:
        return False
    targets = _select_targets(obs, action)
    if len(targets) != COHORT_SIZE:
        return False
    if len(_positions(obs)) < COHORT_SIZE:
        return False
    seed_count = int(obs.get("private", {}).get("seeds", {}).get(PROGRAM, 0))
    market = list(action.get("market", []))
    if seed_count < COHORT_SIZE and len(market) >= 10:
        return False
    state["targets"] = list(targets)
    state["stage"] = "plant"
    state["seed_before"] = seed_count
    state["seed_ordered"] = False
    state["last_tiles"] = {str(i): deepcopy(_tile(obs, target)) for i, target in enumerate(targets)}
    telemetry["admissions"] += 1
    return True


def _append_seed_order(obs, action):
    if state.get("stage") not in {"plant", "acquire"} or state.get("seed_ordered"):
        return
    current = int(obs.get("private", {}).get("seeds", {}).get(PROGRAM, 0))
    if current >= COHORT_SIZE:
        return
    market = list(action.get("market", []))
    if len(market) >= 10:
        return
    if any(isinstance(order, list) and len(order) > 1 and order[0] == "BUY_SEED" and order[1] == PROGRAM for order in market):
        return
    me = obs["farms"][obs["player"]]
    quantity = COHORT_SIZE - current
    if float(me.get("money", 0)) < quantity * SEED_COST + 50:
        return
    market.append(["BUY_SEED", PROGRAM, quantity])
    action["market"] = market[:10]
    state["seed_ordered"] = True
    state["stage"] = "plant"
    telemetry["seed_requests"] += quantity


def _observe(obs):
    targets = state.get("targets", [])
    if not targets:
        return
    for index, target in enumerate(targets):
        key = str(index)
        current = _tile(obs, target)
        previous = state.setdefault("last_tiles", {}).get(key)
        if (
            isinstance(previous, dict)
            and previous.get("kind") == "PLANT"
            and previous.get("crop") == PROGRAM
            and current is None
            and int(previous.get("yield_units", 0)) > 0
            and not state["harvested"][index]
        ):
            units = int(previous.get("yield_units", 0))
            state["harvested"][index] = True
            state["harvest_units"][index] = units
            state["sell_remaining"] += units
            telemetry["harvest_actions"] += 1
            telemetry["harvest_units"] += units
        elif isinstance(current, dict) and current.get("kind") == "WEED" and state.get("stage") not in {"reserved", "acquire"}:
            state["failed"][index] = True
        state["last_tiles"][key] = deepcopy(current)
    if state.get("targets") and all(state["harvested"][i] or state["failed"][i] for i in range(len(targets))):
        state["stage"] = "to_shed" if any(state["harvested"]) else "done"


def _can_use_slot(obs, action, index):
    positions = _positions(obs)
    if index >= len(positions):
        return False
    actions = _unit_actions(action)
    if index >= len(actions) or _op(actions[index]) != "PASS":
        telemetry["blocked"] += 1
        return False
    tile = _tile(obs, positions[index])
    if isinstance(tile, dict) and tile.get("animal"):
        return False
    invs = obs.get("private", {}).get("inventories", [])
    inv = invs[index] if index < len(invs) else {}
    if any(int(inv.get(item, 0)) > 0 for item in ("COW", "SHEEP", "GOOSE")):
        return False
    deadline = _has_global_deadline(obs)
    other_ops = {_op(value) for i, value in enumerate(actions) if i != index}
    if deadline == "animal" and not (other_ops & {"FEED", "CARE", "COLLECT_FERTILIZER", "PICKUP", "PLACE"}):
        telemetry["animal_blocked"] += 1
        return False
    if deadline == "crop" and not (other_ops & {"WATER", "HARVEST", "PLANT"}):
        telemetry["crop_deadline_blocked"] += 1
        return False
    return True


def _target_action(obs, index, target_index):
    positions = _positions(obs)
    if index >= len(positions):
        return None
    target = tuple(state["targets"][target_index])
    position = tuple(map(int, positions[index]))
    tile = _tile(obs, target)
    harvested = bool(state["harvested"][target_index])
    failed = bool(state["failed"][target_index])
    if harvested or failed:
        return None
    seeds = int(obs.get("private", {}).get("seeds", {}).get(PROGRAM, 0))
    if tile is None:
        if seeds <= 0:
            return None
        if position != target:
            telemetry["moves"] += 1
            return _step_toward(position, target)
        telemetry["plant_actions"] += 1
        return ["PLANT", PROGRAM]
    if isinstance(tile, dict) and tile.get("kind") == "PLANT" and tile.get("crop") == PROGRAM:
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
    return None


def _protect_reserved_tiles(obs, action):
    """Do not let the inherited route consume a reserved tile's seed/output."""
    targets = {tuple(p) for p in state.get("targets", [])}
    if not targets:
        return
    positions = _positions(obs)
    for index, value in enumerate(_unit_actions(action)):
        if index >= len(positions) or index in state.get("reserved_workers", []):
            continue
        if tuple(map(int, positions[index])) in targets and _op(value) in {"PLANT", "HARVEST", "DIG"}:
            _replace(action, index, ["PASS"])


def _append_sell(obs, action):
    remaining = int(state.get("sell_remaining", 0))
    if remaining <= 0 or int(obs.get("step", 0)) >= LIQUIDATION_STEP:
        return
    market = list(action.get("market", []))
    if len(market) >= 10:
        return
    shed = int(obs.get("private", {}).get("shed", {}).get(PROGRAM, 0))
    quantity = min(remaining, shed)
    if quantity <= 0:
        return
    market.append(["SELL", PROGRAM, quantity])
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
    if _admit(obs, action):
        pass
    _append_seed_order(obs, action)
    _protect_reserved_tiles(obs, action)
    if state.get("stage") in {"plant", "to_shed"}:
        for target_index, worker_index in enumerate(state.get("reserved_workers", [])):
            if target_index >= len(state.get("targets", [])):
                break
            if not _can_use_slot(obs, action, worker_index):
                continue
            desired = _target_action(obs, worker_index, target_index)
            if desired is not None and desired != ["PASS"]:
                _replace(action, worker_index, desired)
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
agent.description = "complete route owner with day-0 two-worker/two-wheat cohort reservation"
agent.base = BASE
agent.debug_state = state
