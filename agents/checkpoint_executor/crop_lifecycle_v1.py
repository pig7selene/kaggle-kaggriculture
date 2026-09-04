"""Checkpoint executor with ownership of one conservative wheat lifecycle.

The commitment executor remains the safety layer.  This candidate adds only
one optional commitment: buy one wheat seed, plant it on a currently empty
unlocked tile, service it when the safety layer has an idle unit, harvest it,
and let the safety layer return and sell the realized item.  No land, animal,
fertilizer, or additional crop commitments are created.
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


WHEAT = "WHEAT"
SEED_COST = 10
MAX_COMMIT_STEP = 648  # leave the tested executor's terminal window intact
UNIT_ACTIONS = {"NORTH", "SOUTH", "EAST", "WEST", "PASS", "PLANT", "WATER", "HARVEST", "FERTILIZE", "DIG", "BUILD_COOP", "BUILD_PASTURE", "PICKUP", "DROP", "PLACE", "FEED", "CARE", "COLLECT_FERTILIZER"}
MANDATORY_OPS = {"FEED", "WATER", "HARVEST", "DROP", "PICKUP", "PLACE", "CARE", "COLLECT_FERTILIZER"}


state = {}
telemetry = {}


def _empty_unlocked_tiles(farm):
    """Return deterministic empty tiles, excluding shed standing squares."""
    result = []
    for y, row in enumerate(farm.get("tiles", [])):
        for x, tile in enumerate(row):
            if (x, y) in SHED_TILES:
                continue
            if tile is None:
                result.append((x, y))
    return result


def _animal_feed_reserve(obs):
    """Match the safety executor's near-term two-unit reserve convention."""
    farm = obs["farms"][obs["player"]]
    animals = _tile_animals(farm)
    day = int(obs.get("day", 0))
    step = int(obs.get("step", 0))
    wheat_price = float(obs.get("market", {}).get("prices", {}).get(WHEAT, 25))
    remaining_days = max(0, 30 - day)
    due_today = sum(not bool(tile.get("fed_today", False)) for _, _, tile in animals)
    if step >= 648:
        units = due_today + len(animals) * max(0, remaining_days - 1)
    else:
        units = len(animals) * 2
    return float(units) * wheat_price


def _critical_pending(obs):
    """Whether a new commitment should wait for the current safety workload."""
    farm = obs["farms"][obs["player"]]
    day = int(obs.get("day", 0))
    animals = _tile_animals(farm)
    for _, _, tile in animals:
        if not tile.get("fed_today", False):
            return True
        # Harvesting is optional only when the tile has no product.  A
        # realized animal product is still a carried commitment, however.
        if int(tile.get("yield_units", 0)) > 0:
            return True
    for _, _, tile in _tile_plants(farm):
        if not tile.get("watered_today", False):
            return True
        crop_age = day - int(tile.get("planted_day", day))
        if int(tile.get("yield_units", 0)) > 0:
            # Wheat/carrot/melon can be harvested as soon as their first
            # yield arrives; ongoing crops are also safe to leave to the base
            # executor, so only treat immediately harvestable tiles as busy.
            first = {"WHEAT": 2, "CARROT": 2, "TOMATO": 8, "STRAWBERRY": 10, "MELON": 10}.get(tile.get("crop"), 999)
            if crop_age >= first:
                return True
    return False


def _unit_positions(obs):
    farm = obs["farms"][obs["player"]]
    return [farm["farmer"], *farm.get("hands", [])]


def _tile_at(obs, position):
    farm = obs["farms"][obs["player"]]
    x, y = map(int, position)
    tiles = farm.get("tiles", [])
    if y < 0 or y >= len(tiles) or x < 0 or x >= len(tiles[y]):
        return None
    return tiles[y][x]


def _wheat_target_tile(obs):
    farm = obs["farms"][obs["player"]]
    empty = _empty_unlocked_tiles(farm)
    if not empty:
        return None
    # A new commitment should be cheap to route.  Prefer an empty tile next
    # to the currently unlocked shed side, then use board order for a stable
    # tie-break.  Choosing the first empty tile in row-major order can send an
    # optional worker across the whole 5x5 field and makes ownership fragile.
    return min(empty, key=lambda p: (_distance(p, (4, 4)), p[1], p[0]))


def _find_idle_unit(base_action, obs, target):
    """Return the nearest unit whose base action is PASS.

    A PASS assignment is the only action this candidate is allowed to
    replace.  This prevents the optional lifecycle from stealing a safety
    action, including an action that is merely movement toward a deadline.
    """
    positions = _unit_positions(obs)
    actions = [base_action.get("farmer", ["PASS"]), *base_action.get("hands", [])]
    candidates = []
    for index, action in enumerate(actions):
        if index >= len(positions) or not isinstance(action, list) or not action:
            continue
        if action[0] != "PASS":
            continue
        candidates.append((int(_distance(positions[index], target)), index))
    if not candidates:
        return None
    return min(candidates)[1]


def _find_preferred_idle_unit(base_action, obs, target):
    """Prefer one hired hand as a persistent owner of the optional route."""
    positions = _unit_positions(obs)
    actions = [base_action.get("farmer", ["PASS"]), *base_action.get("hands", [])]
    hands = []
    all_units = []
    for index, action in enumerate(actions):
        if index >= len(positions) or not isinstance(action, list) or not action or action[0] != "PASS":
            continue
        item = (int(_distance(positions[index], target)), index)
        all_units.append(item)
        if index > 0:
            hands.append(item)
    choices = hands or all_units
    return min(choices)[1] if choices else None


def _replace_unit_action(action, index, value):
    if index == 0:
        action["farmer"] = value
    else:
        hands = list(action.get("hands", []))
        hand_index = index - 1
        if hand_index < len(hands):
            hands[hand_index] = value
            action["hands"] = hands


def _observe_progress(obs):
    """Update lifecycle telemetry from successive real observations."""
    target = state.get("target")
    if target is None:
        return
    tile = _tile_at(obs, target)
    previous = state.get("last_tile")
    seeds = int(obs.get("private", {}).get("seeds", {}).get(WHEAT, 0))
    if state.get("seed_ordered") and not state.get("seed_acquired") and seeds > int(state.get("seed_before", 0)):
        state["seed_acquired"] = True
        telemetry["seed_acquired"] = int(telemetry.get("seed_acquired", 0)) + 1
    if isinstance(tile, dict) and tile.get("kind") == "PLANT" and tile.get("crop") == WHEAT:
        if not state.get("planted"):
            state["planted"] = True
            state["phase"] = "growing"
            telemetry["planted"] = int(telemetry.get("planted", 0)) + 1
        if tile.get("watered_today"):
            marker = (int(obs.get("day", 0)), target)
            if marker not in state.setdefault("water_marks", set()):
                state["water_marks"].add(marker)
                telemetry["watered_days"] = int(telemetry.get("watered_days", 0)) + 1
    elif state.get("planted") and not state.get("harvested"):
        # A one-time wheat tile disappears immediately after a successful
        # harvest.  Record the last observed units as a lower-bound yield.
        if isinstance(previous, dict) and previous.get("kind") == "PLANT" and tile is None:
            state["harvested"] = True
            state["phase"] = "realized"
            telemetry["harvested"] = int(telemetry.get("harvested", 0)) + 1
            telemetry["harvest_units_lower_bound"] = max(
                int(telemetry.get("harvest_units_lower_bound", 0)),
                int(previous.get("yield_units", 0)),
            )
        elif isinstance(tile, dict) and tile.get("kind") == "WEED":
            state["failed"] = True
            state["phase"] = "failed"
            telemetry["failed_weeds"] = int(telemetry.get("failed_weeds", 0)) + 1
    state["last_tile"] = deepcopy(tile)


def _admission_allowed(obs, action):
    if int(obs.get("step", 0)) >= MAX_COMMIT_STEP:
        return False
    farm = obs["farms"][obs["player"]]
    private = obs.get("private", {})
    # Never consume a seed that may belong to a pre-existing commitment.
    if int(private.get("seeds", {}).get(WHEAT, 0)) > 0:
        return False
    money = float(farm.get("money", 0))
    reserve = _animal_feed_reserve(obs)
    # Keep a small operational cushion for the base executor's next hire or
    # feed purchase.  The wheat seed itself is the only new spend.  Admission
    # additionally requires an actually idle unit in the current observation;
    # the lifecycle can never displace a safety assignment.
    if money < SEED_COST + reserve + 50.0:
        return False
    empty = _empty_unlocked_tiles(farm)
    return bool(empty) and _find_idle_unit(action, obs, empty[0]) is not None


def _append_seed_order(obs, action):
    if state.get("seed_ordered") or not state.get("target"):
        return
    if int(obs.get("step", 0)) >= MAX_COMMIT_STEP:
        return
    market = list(action.get("market", []))
    if len(market) >= 10:
        return
    farm = obs["farms"][obs["player"]]
    private = obs.get("private", {})
    if int(private.get("seeds", {}).get(WHEAT, 0)) > 0:
        return
    # Avoid displacing a same-turn feed purchase or a known safety hire.  A
    # later turn will retry if the base is using its full market queue.
    if any(isinstance(order, list) and order and order[0] in {"BUY_PRODUCT", "BUY_ANIMAL", "BUY_LAND"} for order in market):
        return
    reserve = _animal_feed_reserve(obs)
    if float(farm.get("money", 0)) < SEED_COST + reserve + 50.0:
        return
    market.append(["BUY_SEED", WHEAT, 1])
    action["market"] = market[:10]
    state["seed_ordered"] = True
    state["seed_before"] = int(private.get("seeds", {}).get(WHEAT, 0))
    telemetry["seed_requests"] = int(telemetry.get("seed_requests", 0)) + 1


def _lifecycle_override(obs, action):
    target = state.get("target")
    if target is None:
        return
    tile = _tile_at(obs, target)
    positions = _unit_positions(obs)
    day = int(obs.get("day", 0))
    # If the tile has been harvested, no optional action remains.  The base
    # executor owns the DROP/SELL tail.
    if state.get("harvested") or state.get("failed"):
        return
    if isinstance(tile, dict) and tile.get("kind") == "PLANT" and tile.get("crop") == WHEAT:
        crop_age = day - int(tile.get("planted_day", day))
        if not tile.get("watered_today"):
            desired = "WATER"
        elif int(tile.get("yield_units", 0)) > 0 and crop_age >= 2:
            desired = "HARVEST"
        else:
            return
    elif tile is None and state.get("seed_acquired"):
        desired = "PLANT"
    else:
        return
    owner = state.get("owner")
    if owner is None or owner >= len(positions):
        owner = _find_preferred_idle_unit(action, obs, target)
        if owner is not None:
            state["owner"] = owner
    index = owner
    if index is not None:
        actions = [action.get("farmer", ["PASS"]), *action.get("hands", [])]
        if index >= len(actions) or not isinstance(actions[index], list) or not actions[index] or actions[index][0] != "PASS":
            index = None
    if index is None:
        return
    position = positions[index]
    if tuple(map(int, position)) == tuple(map(int, target)):
        _replace_unit_action(action, index, [desired] if desired != "PLANT" else ["PLANT", WHEAT])
        telemetry["optional_overrides"] = int(telemetry.get("optional_overrides", 0)) + 1
    else:
        _replace_unit_action(action, index, _step_toward(position, target))
        telemetry["optional_moves"] = int(telemetry.get("optional_moves", 0)) + 1


def _record_tail_actions(action):
    """Record coarse ownership telemetry for return-to-shed and liquidation."""
    if not state.get("planted"):
        return
    units = [action.get("farmer", []), *action.get("hands", [])]
    telemetry["drop_actions"] = int(telemetry.get("drop_actions", 0)) + sum(
        1 for value in units if isinstance(value, list) and value and value[0] == "DROP"
    )
    if state.get("harvested"):
        for order in action.get("market", []):
            if isinstance(order, list) and len(order) >= 3 and order[0] == "SELL" and order[1] == WHEAT:
                telemetry["sold_wheat_units"] = int(telemetry.get("sold_wheat_units", 0)) + max(0, int(order[2]))


def _reset(obs):
    state.clear()
    state.update({
        "initialized": True,
        "last_step": int(obs.get("step", 0)) - 1,
        "target": None,
        "phase": "idle",
        "seed_ordered": False,
        "seed_acquired": False,
        "seed_before": 0,
        "planted": False,
        "harvested": False,
        "last_tile": None,
        "water_marks": set(),
        "owner": None,
        "failed": False,
    })
    telemetry.clear()
    telemetry.update({
        "calls": 0,
        "admission_requests": 0,
        "seed_requests": 0,
        "seed_acquired": 0,
        "planted": 0,
        "watered_days": 0,
        "harvested": 0,
        "harvest_units_lower_bound": 0,
        "failed_weeds": 0,
        "drop_actions": 0,
        "sold_wheat_units": 0,
        "optional_moves": 0,
        "optional_overrides": 0,
    })


def agent(obs):
    step = int(obs.get("step", 0))
    if not state or step == 0 or step <= int(state.get("last_step", -1)):
        _reset(obs)
    state["last_step"] = step
    telemetry["calls"] = int(telemetry.get("calls", 0)) + 1

    # The safety executor is always called first and remains authoritative for
    # every existing commitment.
    action = deepcopy(_base_agent(obs))
    _observe_progress(obs)

    if state.get("target") is None and _admission_allowed(obs, action):
        target = _wheat_target_tile(obs)
        if target is not None:
            state["target"] = target
            state["phase"] = "admitted"
            telemetry["admission_requests"] = int(telemetry.get("admission_requests", 0)) + 1

    _append_seed_order(obs, action)
    _lifecycle_override(obs, action)
    _record_tail_actions(action)

    # Preserve the exact action schema even if a simulator supplies an
    # unusual observation with missing hand entries.
    expected_hands = len(obs["farms"][obs["player"]].get("hands", []))
    hands = list(action.get("hands", []))
    hands.extend([["PASS"]] * max(0, expected_hands - len(hands)))
    action["hands"] = hands[:expected_hands]
    if not isinstance(action.get("farmer"), list) or not action["farmer"] or action["farmer"][0] not in UNIT_ACTIONS:
        action["farmer"] = ["PASS"]
    if not isinstance(action.get("market"), list):
        action["market"] = []
    action["market"] = action["market"][:10]
    telemetry.update({
        "phase": state.get("phase"),
        "target": state.get("target"),
        "seed_ordered_state": bool(state.get("seed_ordered")),
        "seed_acquired_state": bool(state.get("seed_acquired")),
        "planted_state": bool(state.get("planted")),
        "harvested_state": bool(state.get("harvested")),
    })
    return action


agent.telemetry = telemetry
agent.description = "safe checkpoint executor plus one end-to-end wheat lifecycle"
