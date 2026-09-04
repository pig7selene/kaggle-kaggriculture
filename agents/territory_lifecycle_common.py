"""CurrentBest-preserving crop lifecycle scheduler ablations.

The frozen Top-50 portfolio owns the complete economic program (opening,
capital, land, animals, market and terminal liquidation).  This module is a
deliberately narrow overlay: it keeps the portfolio's market orders and only
reassigns otherwise non-critical unit actions to crop work.  The four modes
are cumulative ablations:

S0  exact CurrentBest unit actions;
S1  persistent worker territories;
S2  S1 plus hard-deadline watering rescue;
S3  S2 plus same-worker harvest -> replant chaining and cohort priority.

The overlay is conservative by design.  Animal service, carried animals,
feed transfers, shed logistics, and already productive base actions remain
authoritative.  Telemetry is attached to the returned function so benchmark
scripts can separate scheduler effects from economic effects.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from pathlib import Path
from runpy import run_path


ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = ROOT / "agents" / "top50_distilled" / "top50_observable_portfolio.py"
BASE_MODULE = run_path(str(BASE_PATH))
BASE_AGENT = BASE_MODULE["agent"]

try:
    GAME = run_path(str(ROOT / "agents" / "animal_land_common.py"))
    CROPS = GAME["CROPS"]
except Exception:  # pragma: no cover - simulator is available in benchmarks
    CROPS = {
        "WHEAT": {"first": 2, "peak": 4, "ongoing": False},
        "CARROT": {"first": 2, "peak": 3, "ongoing": False},
        "TOMATO": {"first": 8, "peak": 11, "ongoing": True},
        "STRAWBERRY": {"first": 10, "peak": 16, "ongoing": True},
        "MELON": {"first": 10, "peak": 10, "ongoing": False},
    }

MOVES = {"NORTH", "SOUTH", "EAST", "WEST"}
ANIMAL_OPS = {
    "FEED", "CARE", "COLLECT_FERTILIZER", "BUILD_COOP", "BUILD_PASTURE", "PLACE"
}
LOGISTICS_OPS = {"DROP", "PICKUP"}
UNIT_OPS = MOVES | {
    "PASS", "PLANT", "WATER", "HARVEST", "FERTILIZE", "DIG",
    "BUILD_COOP", "BUILD_PASTURE", "PICKUP", "DROP", "PLACE", "FEED",
    "CARE", "COLLECT_FERTILIZER",
}
SHED_TILES = ((4, 4), (5, 4), (4, 5), (5, 5))
QUADRANTS = ("NW", "NE", "SW", "SE")


def _op(action):
    return action[0] if isinstance(action, list) and action else "PASS"


def _quadrant(position):
    x, y = position
    return ("N" if y < 5 else "S") + ("W" if x < 5 else "E")


def _distance(left, right):
    return abs(int(left[0]) - int(right[0])) + abs(int(left[1]) - int(right[1]))


def _move_toward(origin, target):
    x, y = origin
    tx, ty = target
    dx, dy = tx - x, ty - y
    if abs(dy) > abs(dx):
        return ["SOUTH" if dy > 0 else "NORTH"]
    if dx:
        return ["EAST" if dx > 0 else "WEST"]
    if dy:
        return ["SOUTH" if dy > 0 else "NORTH"]
    return ["PASS"]


def _is_plant(tile):
    return isinstance(tile, dict) and tile.get("kind") == "PLANT"


def _is_animal(tile):
    return isinstance(tile, dict) and tile.get("animal") is not None


def _is_protected_base_action(obs, index, action):
    """Whether changing this base action risks an existing commitment."""
    op = _op(action)
    if op in ANIMAL_OPS:
        return True
    me = obs["farms"][obs["player"]]
    positions = [tuple(me["farmer"]), *[tuple(p) for p in me.get("hands", [])]]
    inventories = obs.get("private", {}).get("inventories", [])
    if index >= len(positions):
        return True
    x, y = positions[index]
    tile = me["tiles"][y][x]
    if _is_animal(tile):
        # The portfolio may use a movement step to finish an animal queue.
        return True
    inventory = inventories[index] if index < len(inventories) else {}
    if any(inventory.get(item, 0) for item in ("COW", "SHEEP", "GOOSE")):
        return True
    # A wheat carrier is often in transit to an animal pasture.  Borrowing the
    # movement step is unsafe while any animal still needs feed.
    if inventory.get("WHEAT", 0):
        animal_unfed = any(
            _is_animal(value)
            and not value.get("fed_today", False)
            for row in me["tiles"] for value in row
        )
        if animal_unfed:
            return True
    if op in LOGISTICS_OPS and inventory:
        return True
    if op in {"PLANT", "WATER", "HARVEST", "FERTILIZE", "DIG"}:
        # Preserve an already executable crop action; only movement/PASS is
        # cheap slack for the overlay to borrow.
        return True
    return False


def _available_quadrants(me):
    return tuple(q for q in QUADRANTS if q in set(me.get("unlocked_quadrants", [])))


def _animal_specialists(obs):
    me = obs["farms"][obs["player"]]
    animal_count = sum(
        1 for row in me["tiles"] for tile in row if _is_animal(tile)
    )
    if animal_count <= 0:
        return set()
    units = 1 + len(me.get("hands", []))
    preferred = (0, 1, 4, 5, 2, 3, 6, 7)
    return set(index for index in preferred if index < units) if units <= 4 else set(
        index for index in preferred[:4] if index < units
    )


def _crop_tasks(obs, mode, state):
    """Return (priority, position, action, crop) crop tasks."""
    me = obs["farms"][obs["player"]]
    day = int(obs.get("day", 0))
    hour = int(obs.get("hour", 0))
    seeds = obs.get("private", {}).get("seeds", {})
    tasks = []
    # At most one task per tile.  Existing crop actions are excluded by the
    # caller when the base route is already servicing that tile.
    for y, row in enumerate(me["tiles"]):
        for x, tile in enumerate(row):
            position = (x, y)
            if tile == "LOCKED":
                continue
            if _is_plant(tile):
                crop = tile.get("crop")
                data = CROPS.get(crop, {})
                age = day - int(tile.get("planted_day", day))
                if not tile.get("watered_today", False) and tile.get("consecutive_unwatered", 0) >= 1:
                    # Hard survival deadline.  S1 also sees the task, but S2
                    # gives it cross-territory priority below.
                    tasks.append((0, position, ["WATER"], None))
                    continue
                if tile.get("yield_units", 0) > 0:
                    ready = age >= int(data.get("peak", data.get("first", 0)))
                    if data.get("ongoing") and age >= int(data.get("first", 0)):
                        ready = True
                    if day >= 29 and age >= int(data.get("first", 0)):
                        ready = True
                    if ready:
                        # Ongoing harvests are urgent because each missed tick
                        # is lost; one-time crops retain peak-yield ordering.
                        priority = 1 if data.get("ongoing") else 1.5
                        held = int(tile.get("yield_units", 0))
                        if mode == "S3":
                            priority -= min(0.25, held / 100.0)
                        tasks.append((priority, position, ["HARVEST"], None))
                        continue
                if day >= 29 and tile.get("yield_units", 0) <= 0 and data.get("ongoing"):
                    tasks.append((4, position, ["DIG"], None))
                elif not tile.get("watered_today", False) and mode in {"S2", "S3"}:
                    # Safe watering is lower priority than deadlines but keeps
                    # a local territory from accumulating lifecycle debt.
                    tasks.append((3, position, ["WATER"], None))
                continue
            if isinstance(tile, dict) and tile.get("kind") == "WEED":
                tasks.append((4, position, ["DIG"], None))

    # S3 only admits planting where this same worker harvested immediately
    # before.  This avoids changing the frozen capital/seed plan.
    if mode == "S3":
        for index, record in list(state.get("last_harvest", {}).items()):
            if int(record.get("step", -10)) != int(obs.get("step", 0)) - 1:
                continue
            position = tuple(record["position"])
            x, y = position
            tile = me["tiles"][y][x]
            crop = record.get("crop")
            if tile is None and crop and seeds.get(crop, 0) > 0 and hour <= 21:
                tasks.append((0.5, position, ["PLANT", crop], crop))
    return tasks


def _assign_zones(obs, state, specialists):
    me = obs["farms"][obs["player"]]
    unlocked = _available_quadrants(me)
    zones = state.setdefault("zones", {})
    # Keep a worker's zone stable across turns.  New hands are assigned to the
    # least-loaded quadrant, matching the replay population's purity.
    for index in range(1 + len(me.get("hands", []))):
        if index in specialists:
            continue
        if zones.get(index) in unlocked:
            continue
        counts = Counter(value for value in zones.values() if value in unlocked)
        zone = min(unlocked, key=lambda q: (counts[q], QUADRANTS.index(q))) if unlocked else "NW"
        zones[index] = zone
    return zones


def _urgent_animal_indices(obs, specialists):
    me = obs["farms"][obs["player"]]
    urgent = any(
        _is_animal(tile)
        and not tile.get("fed_today", False)
        and int(tile.get("consecutive_unfed", 0)) >= 1
        for row in me["tiles"] for tile in row
    )
    return set(specialists) if urgent else set()


def _schedule(obs, base_action, mode, state):
    me = obs["farms"][obs["player"]]
    positions = [tuple(me["farmer"]), *[tuple(p) for p in me.get("hands", [])]]
    count = len(positions)
    original = [base_action.get("farmer", ["PASS"]), *list(base_action.get("hands", []))]
    original += [["PASS"]] * max(0, count - len(original))
    original = original[:count]
    output = [deepcopy(value) for value in original]
    if mode == "S0" or count == 0:
        return output, {"overrides": 0, "urgent_overrides": 0, "chain_plants": 0, "tasks": 0}

    specialists = _animal_specialists(obs)
    roles = state.setdefault("animal_roles", set())
    for index, action in enumerate(original):
        if _op(action) in ANIMAL_OPS:
            roles.add(index)
        if index < len(positions):
            tile = me["tiles"][positions[index][1]][positions[index][0]]
            if _is_animal(tile):
                roles.add(index)
    zones = _assign_zones(obs, state, specialists)
    urgent_specialists = _urgent_animal_indices(obs, specialists)
    tasks = _crop_tasks(obs, mode, state)
    # The frozen route gets first claim on any task it is already executing.
    claimed = set()
    for index, action in enumerate(original):
        if _op(action) in {"WATER", "HARVEST", "PLANT", "FERTILIZE", "DIG"}:
            claimed.add(positions[index])
    available = [task for task in tasks if task[1] not in claimed]
    by_zone = {}
    for task in available:
        by_zone.setdefault(_quadrant(task[1]), []).append(task)
    for values in by_zone.values():
        values.sort(key=lambda item: (item[0], item[1][1], item[1][0]))

    reserved_tasks = set(claimed)
    overrides = 0
    urgent_overrides = 0
    chain_plants = 0
    # First pass: local territory tasks.  S2/S3 may rescue a hard deadline
    # cross-territory only after local workers have been considered.
    for index, position in enumerate(positions):
        if index in specialists or index in urgent_specialists or index in roles:
            continue
        if _is_protected_base_action(obs, index, original[index]):
            continue
        # Before all animals are fed, preserve every movement step.  The base
        # route may be carrying wheat toward a pasture several turns away, and
        # a crop detour here can turn a one-day delay into an escape.
        if _op(original[index]) in MOVES:
            animal_unfed = any(
                _is_animal(value)
                and not value.get("fed_today", False)
                for row in me["tiles"] for value in row
            )
            if animal_unfed:
                continue
        zone = zones.get(index, _quadrant(position))
        candidates = [task for task in by_zone.get(zone, ()) if task[1] not in reserved_tasks]
        if not candidates:
            continue
        task = min(candidates, key=lambda item: (_distance(position, item[1]), item[0], item[1]))
        priority, target, action, required_crop = task
        # A borrowed route is worthwhile only when the crop is already close;
        # long detours cost more than a single missed low-value refresh.
        if _distance(position, target) > (2 if priority == 0 else 3):
            continue
        if priority == 0 and mode in {"S2", "S3"} or mode == "S1" and priority <= 1.5:
            output[index] = action if position == target else _move_toward(position, target)
            reserved_tasks.add(target)
            overrides += 1
            urgent_overrides += priority == 0
            chain_plants += action[0] == "PLANT"

    if mode in {"S2", "S3"}:
        # Cross-territory rescue is only for plants one refresh from death and
        # only for units that still had PASS/movement slack.
        urgent_tasks = [task for task in tasks if task[0] == 0 and task[1] not in reserved_tasks]
        for task in sorted(urgent_tasks, key=lambda item: item[1]):
            _, target, action, _ = task
            eligible = [
                (index, position) for index, position in enumerate(positions)
                if index not in specialists
                and index not in urgent_specialists
                and index not in roles
                and output[index] == original[index]
                and not _is_protected_base_action(obs, index, original[index])
            ]
            if not eligible:
                continue
            index, position = min(eligible, key=lambda row: (_distance(row[1], target), row[0]))
            if _distance(position, target) > 2:
                continue
            output[index] = action if position == target else _move_toward(position, target)
            reserved_tasks.add(target)
            overrides += 1
            urgent_overrides += 1

    # Record the previous call's crop action for the S3 handoff.  We use the
    # output (not the route) so the chain is owned by the same unit.
    for index, action in enumerate(output):
        if _op(action) != "HARVEST":
            continue
        position = positions[index]
        tile = me["tiles"][position[1]][position[0]]
        if _is_plant(tile):
            state.setdefault("last_harvest", {})[index] = {
                "step": int(obs.get("step", 0)),
                "position": position,
                "crop": tile.get("crop"),
            }
    return output, {
        "overrides": overrides,
        "urgent_overrides": urgent_overrides,
        "chain_plants": chain_plants,
        "tasks": len(tasks),
    }


def make_agent(mode="S0"):
    mode = str(mode).upper()
    if mode not in {"S0", "S1", "S2", "S3"}:
        raise ValueError(f"unknown scheduler mode: {mode}")
    state = {"zones": {}, "last_harvest": {}, "animal_roles": set()}
    telemetry = {
        "mode": mode, "calls": 0, "overrides": 0, "urgent_overrides": 0,
        "chain_plants": 0, "tasks_seen": 0, "override_ops": Counter(),
        "base_agent": str(BASE_PATH.relative_to(ROOT)),
    }

    def agent(obs):
        if int(obs.get("step", 0)) == 0:
            state.clear()
            state.update({"zones": {}, "last_harvest": {}, "animal_roles": set()})
            telemetry["calls"] = 0
            telemetry["overrides"] = 0
            telemetry["urgent_overrides"] = 0
            telemetry["chain_plants"] = 0
            telemetry["tasks_seen"] = 0
            telemetry["override_ops"] = Counter()
        base_action = deepcopy(BASE_AGENT(obs))
        fields, metrics = _schedule(obs, base_action, mode, state)
        telemetry["calls"] += 1
        telemetry["overrides"] += metrics["overrides"]
        telemetry["urgent_overrides"] += metrics["urgent_overrides"]
        telemetry["chain_plants"] += metrics["chain_plants"]
        telemetry["tasks_seen"] += metrics["tasks"]
        original = [base_action.get("farmer", ["PASS"]), *list(base_action.get("hands", []))]
        for before, after in zip(original, fields):
            if before != after:
                telemetry["override_ops"][_op(after)] += 1
        return {
            "farmer": fields[0],
            "hands": fields[1:],
            # Economic decisions are byte-for-byte inherited from CurrentBest.
            "market": list(base_action.get("market", [])),
        }

    agent.telemetry = telemetry
    agent.base_agent = BASE_AGENT
    agent.scheduler_mode = mode
    agent.scheduler_state = state
    return agent
