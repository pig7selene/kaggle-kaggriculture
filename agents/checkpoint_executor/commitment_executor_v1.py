"""Checkpoint-resumable, commitment-first economic executor.

This is deliberately narrower than the rejected goal executor.  It never
creates land/animal/crop commitments.  On its first observation (which may be
any step) it reconstructs visible plants, animal structures, inventory, cash,
workers, and deadlines, then services those objects from the real state.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from runpy import run_path

from kaggle_environments.envs.kaggriculture import kaggriculture as _game


ROOT = Path(__file__).resolve().parents[2]
_COMMON = run_path(str(ROOT / "agents/planner_common.py"))
CROPS = _COMMON["CROPS"]
ANIMALS = _COMMON["ANIMALS"]
PRODUCTS = set(_COMMON["BASE_PRICES"])
SELLABLE = PRODUCTS | {"FERTILIZER"}
SHED_TILES = {(4, 4), (5, 4), (4, 5), (5, 5)}
MOVES = {"NORTH", "SOUTH", "EAST", "WEST"}
ANIMAL_PRODUCT = {name: data["product"] for name, data in ANIMALS.items()}


def _tile_animals(farm):
    out = []
    for y, row in enumerate(farm.get("tiles", [])):
        for x, tile in enumerate(row):
            if isinstance(tile, dict) and tile.get("animal") in ANIMALS:
                out.append((x, y, tile))
    return out


def _tile_plants(farm):
    out = []
    for y, row in enumerate(farm.get("tiles", [])):
        for x, tile in enumerate(row):
            if isinstance(tile, dict) and tile.get("kind") == "PLANT":
                out.append((x, y, tile))
    return out


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


def _count_inventory(inventories, item):
    return sum(int(inv.get(item, 0)) for inv in inventories)


def _animal_counts(farm):
    out = {name: 0 for name in ANIMALS}
    for _, _, tile in _tile_animals(farm):
        out[tile["animal"]] += 1
    return out


def _snapshot(obs):
    farm = obs["farms"][obs["player"]]
    private = obs.get("private", {})
    plants = _tile_plants(farm)
    animals = _tile_animals(farm)
    inventories = private.get("inventories", [])
    return {
        "step": int(obs.get("step", 0)),
        "day": int(obs.get("day", 0)),
        "money": float(farm.get("money", 0)),
        "quadrants": list(farm.get("unlocked_quadrants", [])),
        "hand_count": len(farm.get("hands", [])),
        "plant_count": len(plants),
        "animal_count": len(animals),
        "animals": _animal_counts(farm),
        "shed": dict(private.get("shed", {})),
        "seeds": dict(private.get("seeds", {})),
        "inventory_total": sum(sum(int(v) for v in inv.values()) for inv in inventories),
    }


def _task_key(task):
    return (task["kind"], int(task["x"]), int(task["y"]))


def _task_score(task, obs):
    hour = int(obs.get("hour", 0))
    urgency = int(task.get("urgency", 0))
    kind = task["kind"]
    if kind == "DROP":
        return 14500 + urgency * 100
    if kind == "PLACE":
        return 13000 + urgency
    if kind == "FEED":
        return 12000 + urgency * 1000 + (2500 if hour >= 20 else 0)
    if kind == "WATER":
        return 10500 + urgency * 1000 + (1800 if hour >= 20 else 0)
    if kind in {"HARVEST", "ANIMAL_HARVEST"}:
        return 8000 + urgency * 50
    if kind == "FERTILIZER":
        # Fertilizer is a recovery asset when cash is too low to buy feed, but
        # it must not displace deadline-sensitive crop watering.  Feed and
        # WATER remain above this task; the collector can run in spare lanes.
        return 9000 + urgency * 100
    if kind == "CARE":
        return 3300 + urgency * 20
    if kind == "PICKUP_WHEAT":
        return 11500 + urgency * 100
    if kind == "PICKUP_ANIMAL":
        return 12500
    return 1000


def _build_tasks(obs, state):
    farm = obs["farms"][obs["player"]]
    private = obs.get("private", {})
    plants = _tile_plants(farm)
    animals = _tile_animals(farm)
    step = int(obs.get("step", 0))
    # Leave a final full day for carried inventory to reach the shed and be
    # sold.  Late animal harvest/fertilizer collection creates fresh value in
    # a hand inventory at the exact moment no market turn remains.
    harvest_cutoff = 696
    tasks = []
    # Existing animal items in a unit/shed are commitments too.  Place them
    # only when an empty matching structure is visible.
    empty_structures = {"COOP": [], "PASTURE": []}
    for y, row in enumerate(farm.get("tiles", [])):
        for x, tile in enumerate(row):
            if isinstance(tile, dict) and tile.get("kind") in empty_structures and not tile.get("animal"):
                empty_structures[tile["kind"]].append((x, y))
    for animal, data in ANIMALS.items():
        available = int(private.get("shed", {}).get(animal, 0)) + _count_inventory(private.get("inventories", []), animal)
        if available <= 0 or not empty_structures.get(data["structure"]):
            continue
        for x, y in empty_structures[data["structure"]][:available]:
            tasks.append({"kind": "PLACE", "x": x, "y": y, "item": animal, "urgency": 1})

    # Carried realized goods must eventually reach the shed.  This is a task,
    # rather than an implicit side effect, so it cannot be starved by a large
    # crop task list.
    for index, inv in enumerate(private.get("inventories", [])):
        non_feed = sum(int(v) for item, v in inv.items() if item != "WHEAT")
        if non_feed > 0:
            target = min(SHED_TILES)
            tasks.append({"kind": "DROP", "x": target[0], "y": target[1], "urgency": 2, "unit": index})

    # Feed is a hard commitment.  Every currently visible animal gets its own
    # task; the greedy assignment can service more animals than workers over a
    # day by reusing workers after each action.
    for x, y, tile in animals:
        if not tile.get("fed_today", False):
            tasks.append({"kind": "FEED", "x": x, "y": y, "urgency": int(tile.get("consecutive_unfed", 0))})
        elif tile.get("yield_units", 0) > 0 and step < harvest_cutoff:
            tasks.append({"kind": "ANIMAL_HARVEST", "x": x, "y": y, "urgency": int(tile.get("yield_units", 0))})
        if tile.get("fed_today", False) and not tile.get("cared_today", False):
            tasks.append({"kind": "CARE", "x": x, "y": y, "urgency": 0})
        # Fertilizer is available once per day for every surviving animal,
        # regardless of whether it has already been fed.  Collecting it is a
        # deliberate low-cash recovery path: one sale can finance the next
        # wheat purchase at a checkpoint with an empty bank.
        if tile.get("fertilizer_available", False) and step < harvest_cutoff:
            fertilizer_urgency = 1 if not tile.get("fed_today", False) else 0
            tasks.append({"kind": "FERTILIZER", "x": x, "y": y, "urgency": fertilizer_urgency})

    for x, y, tile in plants:
        if not tile.get("watered_today", False):
            tasks.append({"kind": "WATER", "x": x, "y": y, "urgency": int(tile.get("consecutive_unwatered", 0))})
        crop = tile.get("crop")
        first = int(CROPS.get(crop, {}).get("first", 999))
        age = int(obs.get("day", 0)) - int(tile.get("planted_day", obs.get("day", 0)))
        if int(tile.get("yield_units", 0)) > 0 and age >= first:
            tasks.append({"kind": "HARVEST", "x": x, "y": y, "urgency": int(tile.get("yield_units", 0))})

    # If no unit currently carries wheat, route one to the shed before the
    # deadline.  This is a real-state reserve action, not an animal target.
    animal_total = len(animals)
    wheat_total = int(private.get("shed", {}).get("WHEAT", 0)) + _count_inventory(private.get("inventories", []), "WHEAT")
    due_feed = sum(not tile.get("fed_today", False) for _, _, tile in animals)
    wheat_units = sum(int(inv.get("WHEAT", 0)) > 0 for inv in private.get("inventories", []))
    # A reserve in the shed is not useful until a worker actually picks it up.
    # Route a carrier whenever due animals outnumber current wheat carriers, or
    # whenever no carrier exists at all.  This fixes the common checkpoint
    # state where CurrentBest has feed in the shed but no hand is carrying it.
    if animal_total and due_feed and (wheat_units == 0 or wheat_units < due_feed) and int(private.get("shed", {}).get("WHEAT", 0)) > 0:
        target = min(SHED_TILES)
        tasks.append({"kind": "PICKUP_WHEAT", "x": target[0], "y": target[1], "urgency": animal_total + due_feed})
    elif animal_total and wheat_total < animal_total * 2 and due_feed:
        target = min(SHED_TILES)
        tasks.append({"kind": "PICKUP_WHEAT", "x": target[0], "y": target[1], "urgency": animal_total - wheat_total})
    return tasks


def _unit_action(obs, index, task, used_targets):
    farm = obs["farms"][obs["player"]]
    private = obs.get("private", {})
    positions = [farm["farmer"], *farm.get("hands", [])]
    inventories = private.get("inventories", [])
    if index >= len(positions):
        return ["PASS"]
    position = positions[index]
    inv = inventories[index] if index < len(inventories) else {}
    x, y = map(int, position)
    tile = farm["tiles"][y][x]
    kind = task.get("kind") if task else None

    # Centralize carried goods whenever safe.  Never drop wheat while an
    # animal is awaiting feed; fertilizer and harvested products are safe to
    # drop even while feed work remains and are needed to fund recovery.
    if (x, y) in SHED_TILES and inv:
        non_feed = sum(int(v) for item, v in inv.items() if item != "WHEAT")
        if task and task.get("kind") == "DROP":
            return ["DROP"] if non_feed > 0 else ["PASS"]
        if not task and (non_feed > 0 or not any(t["kind"] == "FEED" for t in used_targets)):
            return ["DROP"]

    if kind == "PICKUP_WHEAT" and (x, y) in SHED_TILES:
        amount = min(4, int(private.get("shed", {}).get("WHEAT", 0)))
        return ["PICKUP", "WHEAT", max(1, amount)] if amount > 0 else ["PASS"]
    if kind == "PICKUP_ANIMAL" and (x, y) in SHED_TILES:
        item = task.get("item")
        amount = int(private.get("shed", {}).get(item, 0))
        return ["PICKUP", item, 1] if amount > 0 else ["PASS"]

    if kind == "PLACE" and (x, y) == (int(task["x"]), int(task["y"])):
        item = task.get("item")
        if isinstance(tile, dict) and tile.get("kind") == ANIMALS[item]["structure"] and not tile.get("animal") and int(inv.get(item, 0)) > 0:
            return ["PLACE", item, 1]
    if kind == "DROP" and (x, y) in SHED_TILES:
        return ["DROP"] if any(int(v) > 0 for v in inv.values()) else ["PASS"]
    if kind == "FEED" and (x, y) == (int(task["x"]), int(task["y"])):
        if isinstance(tile, dict) and tile.get("animal") and not tile.get("fed_today", False) and int(inv.get("WHEAT", 0)) > 0:
            return ["FEED"]
    if kind == "WATER" and (x, y) == (int(task["x"]), int(task["y"])):
        if isinstance(tile, dict) and tile.get("kind") == "PLANT" and not tile.get("watered_today", False):
            return ["WATER"]
    if kind in {"HARVEST", "ANIMAL_HARVEST"} and (x, y) == (int(task["x"]), int(task["y"])):
        if isinstance(tile, dict) and int(tile.get("yield_units", 0)) > 0:
            if tile.get("kind") != "PLANT":
                return ["HARVEST"] if tile.get("animal") else ["PASS"]
            crop = tile.get("crop")
            age = int(obs.get("day", 0)) - int(tile.get("planted_day", obs.get("day", 0)))
            if age >= int(CROPS.get(crop, {}).get("first", 999)):
                return ["HARVEST"]
    if kind == "CARE" and (x, y) == (int(task["x"]), int(task["y"])):
        if isinstance(tile, dict) and tile.get("animal") and tile.get("fed_today") and not tile.get("cared_today", False):
            return ["CARE"]
    if kind == "FERTILIZER" and (x, y) == (int(task["x"]), int(task["y"])):
        if isinstance(tile, dict) and tile.get("animal") and tile.get("fertilizer_available", False):
            return ["COLLECT_FERTILIZER"]

    if task:
        return _step_toward(position, (task["x"], task["y"]))
    return ["PASS"]


def _fib(index):
    a, b = 1, 1
    for _ in range(max(0, int(index))):
        a, b = b, a + b
    return a


def _estimated_sell_value(obs, shed):
    prices = obs.get("market", {}).get("prices", {})
    return sum(int(qty) * float(prices.get(item, 1)) for item, qty in shed.items() if item in SELLABLE and item not in ANIMALS)


def _desired_hires(obs, plants, animals):
    """Estimate the smallest daily roster that can service the checkpoint.

    This is intentionally workload based, not a strategy target.  A handful
    of workers is a safety requirement when a checkpoint contains many live
    crops/animals; no hires are requested when the farm is empty.
    """
    farm = obs["farms"][obs["player"]]
    if not plants and not animals:
        return 0
    # Watering and animal feed/care are separate visits.  Five to six units
    # per daily route is conservative for the 10x10 board and still keeps the
    # first-day Fibonacci hire bill modest.
    workload = len(plants) * 1.35 + len(animals) * 2.2
    target_units = max(1, int((workload + 5.0) // 6.0))
    return min(8, max(0, target_units - 1))


def _hire_orders(obs, desired, cash_after_sales):
    farm = obs["farms"][obs["player"]]
    current = int(farm.get("hires_today", 0))
    hands = len(farm.get("hands", []))
    needed = max(0, int(desired) - hands)
    if needed <= 0:
        return [], cash_after_sales
    orders = []
    cash = float(cash_after_sales)
    for offset in range(needed):
        cost = _fib(current + offset)
        if cash < cost:
            break
        orders.append(["HIRE"])
        cash -= cost
    return orders, cash


def _market_orders(obs, tasks):
    farm = obs["farms"][obs["player"]]
    private = obs.get("private", {})
    shed = {item: int(value) for item, value in private.get("shed", {}).items() if int(value) > 0}
    inventories = private.get("inventories", [])
    animals = _tile_animals(farm)
    animal_total = len(animals)
    wheat_total = shed.get("WHEAT", 0) + _count_inventory(inventories, "WHEAT")
    # In the terminal window reserve exactly the feed still needed through the
    # final day.  Liquidate only after today's feed has been delivered; selling
    # the whole reserve on day 27 would starve livestock before day 30.
    day = int(obs.get("day", 0))
    terminal = int(obs.get("step", 0)) >= 648
    remaining_days = max(0, 30 - day)
    due_today = sum(not tile.get("fed_today", False) for _, _, tile in animals)
    if terminal:
        reserve = due_today + animal_total * max(0, remaining_days - 1)
    else:
        reserve = animal_total * 2
    orders = []
    # Sell only realized products.  Animal items and feed reserve are
    # commitments and are never accidentally liquidated.
    sell_revenue = 0.0
    for item in sorted(shed):
        if item not in SELLABLE or item in ANIMALS:
            continue
        qty = shed[item]
        if item == "WHEAT":
            qty = min(shed.get("WHEAT", 0), max(0, wheat_total - reserve))
        if qty > 0:
            orders.append(["SELL", item, int(qty)])
            sell_revenue += qty * float(obs.get("market", {}).get("prices", {}).get(item, 1))

    # Re-hire only to service visible commitments.  HIRE is a market action
    # and is therefore safe to combine with a same-turn sale; the estimated
    # proceeds above are included in the affordability check.
    plants = _tile_plants(farm)
    desired_hands = _desired_hires(obs, plants, animals)
    hire_orders, cash_after_hire = _hire_orders(obs, desired_hands, float(farm.get("money", 0)) + sell_revenue)
    orders.extend(hire_orders)

    if wheat_total < reserve and animal_total:
        price = float(obs.get("market", {}).get("prices", {}).get("WHEAT", 25))
        # Never spam an impossible order.  Keep a small cash cushion after
        # hiring; realized sales on this same queue are already accounted for.
        affordable = max(0, int((cash_after_hire - 1.0) // max(1.0, price)))
        quantity = min(int(reserve - wheat_total), affordable)
        if quantity > 0:
            orders.append(["BUY_PRODUCT", "WHEAT", quantity])
    return orders[:10]


def _feed_overrides(obs, state):
    """Return mandatory feed logistics actions for the current observation.

    A checkpoint often starts at hour 0 with wheat in the shed, no hands, and
    animals already one day into their unfed grace period.  The generic task
    allocator cannot distribute that wheat quickly enough.  This small
    state-machine splits feed among units when possible and otherwise routes a
    single carrier deterministically.  It never invents wheat or assumes a
    historical position.
    """
    farm = obs["farms"][obs["player"]]
    private = obs.get("private", {})
    positions = [farm["farmer"], *farm.get("hands", [])]
    inventories = private.get("inventories", [])
    animals = _tile_animals(farm)
    due = [(x, y, tile) for x, y, tile in animals if not tile.get("fed_today", False)]
    overrides = {}
    reserved = set()
    if not due or not positions:
        state["feed_mode"] = None
        return overrides, reserved

    def inv_wheat(index):
        return int(inventories[index].get("WHEAT", 0)) if index < len(inventories) else 0

    mode = state.get("feed_mode")
    # After a bulk PICKUP, put the feed back into the shed so newly spawned
    # hands can each take one unit.  PLACE into shed works while standing on
    # any shed-access tile.
    if mode == "place":
        if inv_wheat(0) <= 0:
            state["feed_mode"] = None
        elif tuple(map(int, positions[0])) in SHED_TILES:
            qty = inv_wheat(0)
            overrides[0] = ["PLACE", "WHEAT", qty]
            reserved.add(0)
            state["feed_mode"] = "pickup"
            return overrides, reserved
        else:
            target = min(SHED_TILES, key=lambda p: _distance(positions[0], p))
            overrides[0] = _step_toward(positions[0], target)
            reserved.add(0)
            return overrides, reserved

    # On the turn after PLACE, distribute one unit to each unit already at a
    # shed tile.  Extra requests are avoided by tracking the observed shed
    # quantity; the environment still treats any race as a no-op, never an
    # invalid action.
    if mode == "pickup":
        available = int(private.get("shed", {}).get("WHEAT", 0))
        for index, position in enumerate(positions):
            if available <= 0:
                break
            if tuple(map(int, position)) in SHED_TILES and inv_wheat(index) == 0:
                overrides[index] = ["PICKUP", "WHEAT", 1]
                reserved.add(index)
                available -= 1
        if overrides:
            # Keep the mode until the next observation confirms the pickup.
            return overrides, reserved
        state["feed_mode"] = None

    carriers = [i for i in range(len(positions)) if inv_wheat(i) > 0]
    # If the farmer is carrying a stack and hands are available, split it.  A
    # stack is otherwise still a valid carrier and can feed animals serially.
    if len(positions) > 1 and inv_wheat(0) > 1 and tuple(map(int, positions[0])) in SHED_TILES:
        overrides[0] = ["PLACE", "WHEAT", inv_wheat(0)]
        reserved.add(0)
        state["feed_mode"] = "pickup"
        return overrides, reserved

    if carriers:
        return overrides, reserved

    # No carrier exists.  Retrieve feed from the observed shed, if any.  When
    # hands are present this starts the split sequence; with only a farmer it
    # simply picks up a small stack for serial feeding.
    shed_wheat = int(private.get("shed", {}).get("WHEAT", 0))
    if shed_wheat <= 0:
        return overrides, reserved
    target = min(SHED_TILES, key=lambda p: _distance(positions[0], p))
    index = min(range(len(positions)), key=lambda i: _distance(positions[i], target))
    if tuple(map(int, positions[index])) == target:
        qty = min(4, shed_wheat)
        overrides[index] = ["PICKUP", "WHEAT", qty]
        reserved.add(index)
        state["feed_mode"] = "place" if len(positions) > 1 and qty > 1 and index == 0 else None
    else:
        overrides[index] = _step_toward(positions[index], target)
        reserved.add(index)
    return overrides, reserved


def _reset_state(state, obs):
    state.clear()
    state.update({
        "initialized": True,
        "last_step": int(obs.get("step", 0)) - 1,
        "commitments": _snapshot(obs),
        "task_failures": 0,
        "recovery_events": 0,
        "completed": {"FEED": 0, "WATER": 0, "HARVEST": 0, "CARE": 0, "FERTILIZER": 0},
        "late_critical": 0,
        "feed_mode": None,
    })


state = {}
telemetry = {}


def agent(obs):
    step = int(obs.get("step", 0))
    if not state or step == 0 or step <= int(state.get("last_step", -1)):
        _reset_state(state, obs)
        telemetry.clear()
    state["last_step"] = step
    telemetry["calls"] = int(telemetry.get("calls", 0)) + 1
    farm = obs["farms"][obs["player"]]
    positions = [farm["farmer"], *farm.get("hands", [])]
    tasks = _build_tasks(obs, state)
    # Critical tasks first; within a priority, nearest-unit assignment reduces
    # movement and avoids repeatedly crossing the whole board.
    tasks = sorted(tasks, key=lambda t: (-_task_score(t, obs), t["y"], t["x"]))
    assigned = []
    used_tasks = set()
    unit_actions = []
    forced_actions, forced_units = _feed_overrides(obs, state)
    feed_tasks = [t for t in tasks if t["kind"] == "FEED"]
    wheat_units = [i for i, inv in enumerate(obs.get("private", {}).get("inventories", [])) if int(inv.get("WHEAT", 0)) > 0]
    unit_order = list(range(len(positions)))
    # Feed carriers get first choice of feed tasks.  Remaining units are
    # assigned greedily by score minus travel distance.
    for index in unit_order:
        if index in forced_units:
            assigned.append({"kind": "FEED_OVERRIDE", "x": positions[index][0], "y": positions[index][1]})
            unit_actions.append(forced_actions[index])
            continue
        candidates = [t for t in tasks if id(t) not in used_tasks]
        candidates = [t for t in candidates if t.get("unit") is None or int(t.get("unit")) == index]
        if not candidates:
            assigned.append(None)
            unit_actions.append(["PASS"])
            continue
        unit_inv = obs.get("private", {}).get("inventories", [])
        carries_wheat = index < len(unit_inv) and int(unit_inv[index].get("WHEAT", 0)) > 0
        # A feed task is not executable without wheat.  Do not park a worker
        # on an animal tile issuing harmless FEED no-ops while feed is waiting
        # in the shed; select the pickup task instead.
        executable = [t for t in candidates if t["kind"] != "FEED" or carries_wheat]
        # If no unit carries feed, a FEED task is not merely low value: it is
        # a guaranteed no-op.  Remove it so the unit can collect fertilizer,
        # harvest, water, or move to the shed for recovery instead.
        candidates = executable
        if not candidates:
            assigned.append(None)
            unit_actions.append(["PASS"])
            continue
        if index in wheat_units and feed_tasks:
            candidates = [t for t in candidates if t["kind"] == "FEED"] or candidates
        task = max(candidates, key=lambda t: (_task_score(t, obs) - _distance(positions[index], (t["x"], t["y"])) * 18, -t["y"], -t["x"]))
        # Avoid assigning a worker to a distant optional task when a critical
        # task is already available to another unit; the next turn will retry.
        used_tasks.add(id(task))
        assigned.append(task)
        unit_actions.append(_unit_action(obs, index, task, tasks))
    # Preserve exact action cardinality and schema.
    required_hands = len(farm.get("hands", []))
    unit_actions.extend([["PASS"]] * (required_hands + 1 - len(unit_actions)))
    unit_actions = unit_actions[: required_hands + 1]

    # If an action targets an urgent animal/crop but the unit is not yet there,
    # record a recovery pressure event near the end-of-day deadline.
    if int(obs.get("hour", 0)) >= 21 and any(t["kind"] in {"FEED", "WATER"} for t in tasks):
        state["late_critical"] = int(state.get("late_critical", 0)) + 1
        state["recovery_events"] = int(state.get("recovery_events", 0)) + 1
    orders = _market_orders(obs, tasks)
    telemetry.update({
        "last_step": step,
        "commitment_snapshot": deepcopy(state.get("commitments", {})),
        "visible_plants": len(_tile_plants(farm)),
        "visible_animals": len(_tile_animals(farm)),
        "pending_tasks": len(tasks),
        "late_critical": int(state.get("late_critical", 0)),
        "recovery_events": int(state.get("recovery_events", 0)),
        "task_failures": int(state.get("task_failures", 0)),
    })
    return {"farmer": unit_actions[0], "hands": unit_actions[1:], "market": orders}


agent.telemetry = telemetry
agent.description = "state-based commitment-first checkpoint executor; no optional purchases"
