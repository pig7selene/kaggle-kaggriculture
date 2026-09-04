"""CurrentBest-preserving overlay for a bounded melon cohort.

This is a research candidate, not a submission agent.  A supplied base agent
continues to emit its complete route; the overlay may replace only PASS unit
actions and append market orders when slots remain.  The experiment asks
whether a small new production commitment has value when existing CurrentBest
state is left in charge.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from runpy import run_path


ROOT = Path(__file__).resolve().parents[2]
BASE_MODULE = run_path(str(ROOT / "agents/top50_distilled/top50_observable_portfolio.py"))
DEFAULT_BASE_AGENT = BASE_MODULE["agent"]

SHED_TILES = {(4, 4), (5, 4), (4, 5), (5, 5)}
MELON = "MELON"
MELON_COST = 80
SIZE = 4
FIRST_YIELD_DAY = 10
LAST_ADMISSION_DAY = 18
HARVEST_CUTOFF = 696
UNIT_OPS = {"NORTH", "SOUTH", "EAST", "WEST", "PASS", "PLANT", "WATER", "HARVEST"}
MOVES = {"NORTH", "SOUTH", "EAST", "WEST"}


def _distance(a, b):
    return abs(int(a[0]) - int(b[0])) + abs(int(a[1]) - int(b[1]))


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


def _tile(obs, pos):
    x, y = map(int, pos)
    rows = obs["farms"][obs["player"]].get("tiles", [])
    return rows[y][x] if 0 <= y < len(rows) and 0 <= x < len(rows[y]) else "LOCKED"


def _empty_tiles(obs):
    farm = obs["farms"][obs["player"]]
    return {
        (x, y)
        for y, row in enumerate(farm.get("tiles", []))
        for x, tile in enumerate(row)
        if tile is None and (x, y) not in SHED_TILES
    }


def _select_targets(obs):
    empty = _empty_tiles(obs)
    if len(empty) < SIZE:
        return []
    anchor = min(empty, key=lambda p: (min(_distance(p, shed) for shed in SHED_TILES), p[1], p[0]))
    chosen = [anchor]
    remaining = set(empty)
    remaining.remove(anchor)
    while len(chosen) < SIZE and remaining:
        nxt = min(
            remaining,
            key=lambda p: (min(_distance(p, q) for q in chosen), min(_distance(p, shed) for shed in SHED_TILES), p[1], p[0]),
        )
        chosen.append(nxt)
        remaining.remove(nxt)
    return chosen if len(chosen) == SIZE else []


def _positions(obs):
    farm = obs["farms"][obs["player"]]
    return [farm["farmer"], *farm.get("hands", [])]


def _reset(state, telemetry):
    state.clear()
    state.update({"last_step": -1, "targets": [], "records": {}, "seed_ordered": False, "seed_before": 0})
    telemetry.clear()
    telemetry.update({"calls": 0, "admissions": 0, "seed_requests": 0, "planted": 0, "matured": 0, "harvested": 0, "failed": 0, "overrides": 0, "overlay_moves": 0, "overlay_actions": 0})


def _admit(state, telemetry, targets, step):
    state["targets"] = list(targets)
    state["records"] = {
        f"{x},{y}": {"position": [x, y], "planted": False, "harvested": False, "failed": False}
        for x, y in targets
    }
    state["admitted_step"] = int(step)
    telemetry["admissions"] += 1


def _observe(state, telemetry, obs):
    if not state.get("targets"):
        return
    day = int(obs.get("day", 0))
    for x, y in state["targets"]:
        key = f"{x},{y}"
        rec = state["records"][key]
        current = _tile(obs, (x, y))
        if isinstance(current, dict) and current.get("kind") == "PLANT" and current.get("crop") == MELON:
            if not rec["planted"]:
                rec["planted"] = True
                rec["planted_day"] = int(current.get("planted_day", day))
                telemetry["planted"] += 1
            age = day - int(current.get("planted_day", day))
            if age >= FIRST_YIELD_DAY and int(current.get("yield_units", 0)) > 0 and not rec["matured"]:
                rec["matured"] = True
                telemetry["matured"] += 1
        elif rec["planted"] and not rec["harvested"]:
            rec["harvested"] = True
            telemetry["harvested"] += 1
        elif rec["planted"] and isinstance(current, dict) and current.get("kind") == "WEED" and not rec["failed"]:
            rec["failed"] = True
            telemetry["failed"] += 1


def _active(state):
    return any(not r["harvested"] and not r["failed"] for r in state.get("records", {}).values())


def _tasks(state, obs):
    day = int(obs.get("day", 0))
    step = int(obs.get("step", 0))
    seeds = int(obs.get("private", {}).get("seeds", {}).get(MELON, 0))
    tasks = []
    for x, y in state.get("targets", []):
        rec = state["records"][f"{x},{y}"]
        if rec["harvested"] or rec["failed"]:
            continue
        tile = _tile(obs, (x, y))
        if isinstance(tile, dict) and tile.get("kind") == "PLANT" and tile.get("crop") == MELON:
            age = day - int(tile.get("planted_day", day))
            if not tile.get("watered_today", False):
                tasks.append((0, (x, y), ["WATER",], "water"))
            elif age >= FIRST_YIELD_DAY and int(tile.get("yield_units", 0)) > 0 and step < HARVEST_CUTOFF:
                tasks.append((1, (x, y), ["HARVEST"], "harvest"))
        elif tile is None and not rec["planted"] and seeds > 0 and step < HARVEST_CUTOFF:
            tasks.append((2, (x, y), ["PLANT", MELON], "plant"))
    return tasks


def _market_overlay(state, obs, base_market):
    orders = list(base_market or [])
    private = obs.get("private", {})
    farm = obs["farms"][obs["player"]]
    cash = float(farm.get("money", 0))
    seeds = int(private.get("seeds", {}).get(MELON, 0))
    active = _active(state)
    if active and not state.get("seed_ordered") and seeds < SIZE and len(orders) < 10:
        need = SIZE - seeds
        if cash >= need * MELON_COST + 400:
            orders.append(["BUY_SEED", MELON, need])
            state["seed_ordered"] = True
            state["seed_before"] = seeds
            state.setdefault("telemetry", {})
    shed = private.get("shed", {})
    melon_qty = int(shed.get(MELON, 0))
    if melon_qty > 0 and len(orders) < 10:
        orders.append(["SELL", MELON, melon_qty])
    return orders[:10]


def make_agent(base_agent=DEFAULT_BASE_AGENT):
    """Return an overlay agent bound to an independent base-agent instance."""
    state = {}
    telemetry = {}

    def agent(obs):
        step = int(obs.get("step", 0))
        if not state or step == 0 or step <= int(state.get("last_step", -1)):
            _reset(state, telemetry)
        state["last_step"] = step
        telemetry["calls"] += 1
        base_action = deepcopy(base_agent(obs))
        _observe(state, telemetry, obs)

        if not state.get("targets") and 10 <= int(obs.get("day", 0)) <= LAST_ADMISSION_DAY:
            targets = _select_targets(obs)
            private = obs.get("private", {})
            seeds = int(private.get("seeds", {}).get(MELON, 0))
            cash = float(obs["farms"][obs["player"]].get("money", 0))
            if len(targets) == SIZE and seeds == 0 and cash >= SIZE * MELON_COST + 400:
                _admit(state, telemetry, targets, step)

        if not _active(state):
            telemetry["realization_rate"] = 0.0
            telemetry["requested"] = len(state.get("targets", []))
            return base_action

        tasks = sorted(_tasks(state, obs), key=lambda t: (t[0], t[1][1], t[1][0]))
        positions = _positions(obs)
        unit_actions = [base_action.get("farmer", ["PASS"]), *base_action.get("hands", [])]
        used = set()
        for index, (position, original) in enumerate(zip(positions, unit_actions)):
            if original and original[0] != "PASS":
                continue
            available = [(task_index, task) for task_index, task in enumerate(tasks) if task_index not in used]
            if not available:
                continue
            task_index, task = min(available, key=lambda item: (item[1][0], _distance(position, item[1][1])))
            _, target, operation, _ = task
            tile = _tile(obs, target)
            if tuple(map(int, position)) == tuple(target):
                if operation[0] == "PLANT" and tile is None and int(obs.get("private", {}).get("seeds", {}).get(MELON, 0)) > 0:
                    unit_actions[index] = operation
                elif operation[0] == "WATER" and isinstance(tile, dict) and tile.get("kind") == "PLANT" and not tile.get("watered_today", False):
                    unit_actions[index] = operation
                elif operation[0] == "HARVEST" and isinstance(tile, dict) and int(tile.get("yield_units", 0)) > 0:
                    unit_actions[index] = operation
                else:
                    continue
            else:
                unit_actions[index] = _step_toward(position, target)
            used.add(task_index)
            telemetry["overrides"] += 1
            telemetry["overlay_moves"] += int(unit_actions[index][0] in MOVES)
            telemetry["overlay_actions"] += int(unit_actions[index][0] not in MOVES and unit_actions[index][0] != "PASS")

        market = _market_overlay(state, obs, base_action.get("market", []))
        telemetry["requested"] = len(state.get("targets", []))
        telemetry["harvested_count"] = sum(bool(r["harvested"]) for r in state.get("records", {}).values())
        telemetry["realization_rate"] = telemetry["harvested_count"] / telemetry["requested"] if telemetry["requested"] else 0.0
        return {"farmer": unit_actions[0], "hands": unit_actions[1:], "market": market}

    agent.telemetry = telemetry
    agent.description = "CurrentBest-preserving PASS-unit overlay with one melon cohort"
    agent.overlay_state = state
    agent.base_agent = base_agent
    return agent


agent = make_agent()
