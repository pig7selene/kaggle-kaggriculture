"""Safe checkpoint executor with one compact, owned MELON cohort.

This is an oracle-style research candidate, not a deployment agent.  It keeps
the proven commitment executor authoritative and may borrow only PASS actions
from idle units for a four-tile melon lifecycle.  The cohort is admitted only
when seed, feed, capital, time, and worker slack are all visible in the real
state.  No land, animals, or other economic commitments are created.
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

COHORT_SIZE = 4
CROP = "MELON"
SEED_COST = 80
FIRST_YIELD_DAY = 10
MAX_COMMIT_STEP = 600
UNIT_ACTIONS = {
    "NORTH", "SOUTH", "EAST", "WEST", "PASS", "PLANT", "WATER",
    "HARVEST", "FERTILIZE", "DIG", "BUILD_COOP", "BUILD_PASTURE",
    "PICKUP", "DROP", "PLACE", "FEED", "CARE", "COLLECT_FERTILIZER",
}

state = {}
telemetry = {}


def _positions(obs):
    farm = obs["farms"][obs["player"]]
    return [farm["farmer"], *farm.get("hands", [])]


def _tile_at(obs, pos):
    farm = obs["farms"][obs["player"]]
    x, y = map(int, pos)
    rows = farm.get("tiles", [])
    return rows[y][x] if 0 <= y < len(rows) and 0 <= x < len(rows[y]) else None


def _empty_unlocked_tiles(farm):
    # Locked quadrants are represented by the literal string LOCKED.
    return [
        (x, y)
        for y, row in enumerate(farm.get("tiles", []))
        for x, tile in enumerate(row)
        if tile is None and (x, y) not in SHED_TILES
    ]


def _feed_reserve(obs):
    """Reserve the same conservative wheat liability as the base executor."""
    farm = obs["farms"][obs["player"]]
    animals = _tile_animals(farm)
    day = int(obs.get("day", 0))
    step = int(obs.get("step", 0))
    price = float(obs.get("market", {}).get("prices", {}).get("WHEAT", 25))
    remaining = max(0, 30 - day)
    due = sum(not bool(tile.get("fed_today", False)) for _, _, tile in animals)
    units = due + len(animals) * max(0, remaining - 1) if step >= 648 else len(animals) * 2
    return float(units) * price


def _cohort_targets(obs):
    """Choose four co-located empty tiles with a short route from the shed."""
    farm = obs["farms"][obs["player"]]
    empty = _empty_unlocked_tiles(farm)
    if len(empty) < COHORT_SIZE:
        return []
    # Minimize a simple service-route proxy: distance to the center plus the
    # bounding-box perimeter.  Stable row/column tie-breaks keep experiments
    # reproducible and avoid scattering the optional cohort.
    center = (4, 4)
    candidates = sorted(empty, key=lambda p: (_distance(p, center), p[1], p[0]))
    chosen = [candidates[0]]
    while len(chosen) < COHORT_SIZE:
        best = min(
            (p for p in candidates if p not in chosen),
            key=lambda p: (
                min(_distance(p, q) for q in chosen),
                _distance(p, center), p[1], p[0],
            ),
        )
        chosen.append(best)
    return chosen


def _idle_units(action, obs):
    positions = _positions(obs)
    actions = [action.get("farmer", ["PASS"]), *action.get("hands", [])]
    out = []
    for index, value in enumerate(actions):
        if index >= len(positions):
            continue
        if isinstance(value, list) and value and value[0] == "PASS":
            out.append(index)
    return out


def _replace(action, index, value):
    if index == 0:
        action["farmer"] = value
    else:
        hands = list(action.get("hands", []))
        if index - 1 < len(hands):
            hands[index - 1] = value
            action["hands"] = hands


def _admission_allowed(obs, action):
    step = int(obs.get("step", 0))
    day = int(obs.get("day", 0))
    if step >= MAX_COMMIT_STEP or day > 18 or state.get("targets"):
        return False
    farm = obs["farms"][obs["player"]]
    private = obs.get("private", {})
    # Do not consume seeds that could belong to an observed route commitment.
    if int(private.get("seeds", {}).get(CROP, 0)) > 0:
        return False
    targets = _cohort_targets(obs)
    if len(targets) < COHORT_SIZE:
        return False
    # Two idle units give the cohort a realistic chance of meeting its daily
    # watering window while the base executor retains all mandatory work.
    if len(_idle_units(action, obs)) < 2:
        return False
    melon_price = float(obs.get("market", {}).get("prices", {}).get(CROP, 250))
    if melon_price < 180.0:
        return False
    money = float(farm.get("money", 0))
    reserve = _feed_reserve(obs)
    # Four seeds plus a substantial operating cushion; this intentionally
    # rejects marginal admissions that could starve feed or terminal work.
    required = COHORT_SIZE * SEED_COST + reserve + 500.0
    if money < required:
        return False
    return True


def _seed_order(obs, action):
    if not state.get("targets") or state.get("seed_ordered"):
        return
    if int(obs.get("step", 0)) >= MAX_COMMIT_STEP:
        return
    private = obs.get("private", {})
    if int(private.get("seeds", {}).get(CROP, 0)) > 0:
        return
    market = list(action.get("market", []))
    if len(market) >= 10:
        return
    # Never displace a feed, land, animal, or hire transaction generated by
    # the safety executor.  Retry on a later turn if its queue is busy.
    if any(isinstance(o, list) and o and o[0] in {"BUY_PRODUCT", "BUY_ANIMAL", "BUY_LAND", "HIRE"} for o in market):
        return
    farm = obs["farms"][obs["player"]]
    if float(farm.get("money", 0)) < COHORT_SIZE * SEED_COST + _feed_reserve(obs) + 500.0:
        return
    market.append(["BUY_SEED", CROP, COHORT_SIZE])
    action["market"] = market[:10]
    state["seed_ordered"] = True
    state["seed_before"] = int(private.get("seeds", {}).get(CROP, 0))
    telemetry["seed_requests"] += 1


def _observe(obs):
    targets = state.get("targets") or []
    if not targets:
        return
    private = obs.get("private", {})
    seeds = int(private.get("seeds", {}).get(CROP, 0))
    if state.get("seed_ordered") and not state.get("seed_acquired") and seeds >= COHORT_SIZE:
        state["seed_acquired"] = True
        telemetry["seed_acquired"] += 1
    day = int(obs.get("day", 0))
    for target in targets:
        tile = _tile_at(obs, target)
        previous = state.setdefault("last_tiles", {}).get(target)
        if isinstance(tile, dict) and tile.get("kind") == "PLANT" and tile.get("crop") == CROP:
            if not state.setdefault("planted", {}).get(target):
                state["planted"][target] = True
                telemetry["planted"] += 1
            if tile.get("watered_today"):
                marker = (day, target)
                marks = state.setdefault("water_marks", set())
                if marker not in marks:
                    marks.add(marker)
                    telemetry["watered_actions"] += 1
        elif state.setdefault("planted", {}).get(target) and not state.setdefault("harvested", {}).get(target):
            # One-time melons disappear after HARVEST.  A weed is a genuine
            # lifecycle failure and is never silently counted as realized.
            if isinstance(previous, dict) and previous.get("kind") == "PLANT" and tile is None:
                state["harvested"][target] = True
                telemetry["harvested"] += 1
                telemetry["harvest_units_lower_bound"] += int(previous.get("yield_units", 0))
            elif isinstance(tile, dict) and tile.get("kind") == "WEED":
                state["failed"][target] = True
                telemetry["failed_weeds"] += 1
        state["last_tiles"][target] = deepcopy(tile)


def _next_target(obs):
    day = int(obs.get("day", 0))
    targets = state.get("targets") or []
    planted = state.setdefault("planted", {})
    harvested = state.setdefault("harvested", {})
    # Protect the final watering window: watering always precedes harvest on
    # the same day, and a not-yet-watered tile is selected before any harvest.
    for target in targets:
        tile = _tile_at(obs, target)
        if isinstance(tile, dict) and tile.get("kind") == "PLANT" and tile.get("crop") == CROP:
            if not tile.get("watered_today", False):
                return target, "WATER"
            age = day - int(tile.get("planted_day", day))
            if int(tile.get("yield_units", 0)) > 0 and age >= FIRST_YIELD_DAY:
                return target, "HARVEST"
        elif tile is None and state.get("seed_acquired") and not planted.get(target) and not harvested.get(target):
            return target, "PLANT"
    return None, None


def _optional_override(obs, action):
    target, desired = _next_target(obs)
    if target is None:
        return
    positions = _positions(obs)
    idle = _idle_units(action, obs)
    if not idle:
        return
    # Reuse a persistent owner when it is idle; otherwise choose the nearest
    # idle hand.  Farmer is a last resort because it is often the base route's
    # central carrier.
    owner = state.get("owner")
    if owner not in idle:
        hands = [i for i in idle if i > 0]
        pool = hands or idle
        owner = min(pool, key=lambda i: (_distance(positions[i], target), i))
        state["owner"] = owner
    if tuple(map(int, positions[owner])) == tuple(map(int, target)):
        _replace(action, owner, [desired] if desired != "PLANT" else ["PLANT", CROP])
        telemetry["optional_overrides"] += 1
    else:
        _replace(action, owner, _step_toward(positions[owner], target))
        telemetry["optional_moves"] += 1


def _reset(obs):
    state.clear()
    state.update({
        "last_step": int(obs.get("step", 0)) - 1,
        "targets": [], "seed_ordered": False, "seed_acquired": False,
        "seed_before": 0, "planted": {}, "harvested": {}, "failed": {},
        "last_tiles": {}, "water_marks": set(), "owner": None,
    })
    telemetry.clear()
    telemetry.update({
        "calls": 0, "admission_requests": 0, "seed_requests": 0,
        "seed_acquired": 0, "planted": 0, "watered_actions": 0,
        "harvested": 0, "harvest_units_lower_bound": 0,
        "failed_weeds": 0, "optional_moves": 0, "optional_overrides": 0,
    })


def agent(obs):
    step = int(obs.get("step", 0))
    if not state or step == 0 or step <= int(state.get("last_step", -1)):
        _reset(obs)
    state["last_step"] = step
    telemetry["calls"] += 1

    # Existing commitments always get the first say.
    action = deepcopy(_base_agent(obs))
    _observe(obs)
    if not state.get("targets") and _admission_allowed(obs, action):
        state["targets"] = _cohort_targets(obs)
        telemetry["admission_requests"] += 1
    _seed_order(obs, action)
    _optional_override(obs, action)

    # Preserve the exact action schema even for unusual observations.
    expected = len(obs["farms"][obs["player"]].get("hands", []))
    hands = list(action.get("hands", []))
    hands.extend([["PASS"]] * max(0, expected - len(hands)))
    action["hands"] = hands[:expected]
    if not isinstance(action.get("farmer"), list) or not action["farmer"] or action["farmer"][0] not in UNIT_ACTIONS:
        action["farmer"] = ["PASS"]
    if not isinstance(action.get("market"), list):
        action["market"] = []
    action["market"] = action["market"][:10]
    telemetry.update({
        "targets": [list(p) for p in state.get("targets", [])],
        "seed_ordered_state": bool(state.get("seed_ordered")),
        "seed_acquired_state": bool(state.get("seed_acquired")),
        "planted_count": sum(bool(v) for v in state.get("planted", {}).values()),
        "harvested_count": sum(bool(v) for v in state.get("harvested", {}).values()),
    })
    return action


agent.telemetry = telemetry
agent.description = "safe checkpoint executor plus one capital/worker-reserved four-melon cohort"
