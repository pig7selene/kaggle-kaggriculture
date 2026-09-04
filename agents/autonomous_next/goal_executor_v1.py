"""Small goal-conditioned executor prototype.

This is intentionally a research candidate, not a replacement for the frozen
Top-50 portfolio.  It keeps the proven replay backbone through the opening and
then asks the state-driven economic engine to deploy crop capacity from the
actual farm state.  Existing animal tiles are treated as hard safety zones:
animal servicing remains delegated to the backbone while the executor owns
crop actions and market transactions.  That separation lets us test the
executor hypothesis without silently abandoning the proven livestock route.
"""

from copy import deepcopy
from runpy import run_path


_BACKBONE = run_path("agents/top50_distilled/top50_observable_portfolio.py")["agent"]
_COMMON = run_path("agents/planner_common.py")


def _animal_tile(tile):
    return isinstance(tile, dict) and tile.get("animal") is not None


def _animal_counts(farm):
    counts = {name: 0 for name in _COMMON["ANIMALS"]}
    for row in farm["tiles"]:
        for tile in row:
            if _animal_tile(tile) and tile.get("animal") in counts:
                counts[tile["animal"]] += 1
    return counts


_MOVES = {"NORTH", "SOUTH", "EAST", "WEST"}
_SELLABLE = {
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
    "EGG", "MILK", "WOOL", "FERTILIZER",
}
_STRUCTURE = {"GOOSE": "COOP", "COW": "PASTURE", "SHEEP": "PASTURE"}
_FIRST = {name: int(data["first"]) for name, data in _COMMON["CROPS"].items()}
_SHED = {(4, 4), (5, 4), (4, 5), (5, 5)}


def _unit_legal(obs, index, action, seeds_used=None):
    """State legality for the small target executor.

    The Kaggriculture engine treats illegal requests as silent no-ops.  A
    goal-driven controller cannot rely on that behaviour because one no-op can
    push an animal or a crop past its two-day safety deadline.  We therefore
    roll back only requests that are provably illegal in the current state.
    """
    if not isinstance(action, list) or not action:
        return False
    farm = obs["farms"][obs["player"]]
    positions = [farm["farmer"], *farm.get("hands", [])]
    inventories = obs["private"].get("inventories", [])
    if index >= len(positions):
        return False
    x, y = positions[index]
    tile = farm["tiles"][y][x]
    inv = inventories[index] if index < len(inventories) else {}
    op = action[0]
    if op in _MOVES:
        dx = -1 if op == "WEST" else 1 if op == "EAST" else 0
        dy = -1 if op == "NORTH" else 1 if op == "SOUTH" else 0
        return 0 <= x + dx < 10 and 0 <= y + dy < 10
    if op == "PASS":
        return len(action) == 1
    if op == "PLANT":
        crop = action[1] if len(action) > 1 else None
        used = 0 if seeds_used is None else int(seeds_used.get(crop, 0))
        return tile is None and crop in _FIRST and int(obs["private"]["seeds"].get(crop, 0)) > used
    if op == "WATER":
        return isinstance(tile, dict) and tile.get("kind") == "PLANT" and not tile.get("watered_today", False)
    if op == "HARVEST":
        if not isinstance(tile, dict) or int(tile.get("yield_units", 0)) <= 0:
            return False
        if tile.get("kind") != "PLANT":
            return bool(tile.get("animal"))
        return int(obs["day"]) - int(tile.get("planted_day", obs["day"])) >= _FIRST.get(tile.get("crop"), 10)
    if op == "FERTILIZE":
        return isinstance(tile, dict) and tile.get("kind") == "PLANT" and int(inv.get("FERTILIZER", 0)) > 0
    if op == "DIG":
        return tile not in (None, "LOCKED") and not (isinstance(tile, dict) and tile.get("animal"))
    if op in {"BUILD_COOP", "BUILD_PASTURE"}:
        return tile is None
    if op == "PICKUP":
        return (x, y) in _SHED and len(action) >= 2 and int(obs["private"]["shed"].get(action[1], 0)) > 0
    if op == "DROP":
        return (x, y) in _SHED and any(int(v) > 0 for v in inv.values())
    if op == "PLACE":
        item = action[1] if len(action) > 1 else None
        if item in _STRUCTURE:
            return isinstance(tile, dict) and tile.get("kind") == _STRUCTURE[item] and not tile.get("animal") and int(inv.get(item, 0)) > 0
        return (x, y) in _SHED and int(inv.get(item, 0)) > 0
    if op == "FEED":
        return isinstance(tile, dict) and bool(tile.get("animal")) and not tile.get("fed_today", False) and int(inv.get("WHEAT", 0)) > 0
    if op == "CARE":
        return isinstance(tile, dict) and bool(tile.get("animal")) and not tile.get("cared_today", False)
    if op == "COLLECT_FERTILIZER":
        return isinstance(tile, dict) and bool(tile.get("animal")) and bool(tile.get("fertilizer_available", False))
    return False


def _sanitize(obs, unit_actions, market):
    """Convert a proposed target action to a semantically valid action."""
    farm = obs["farms"][obs["player"]]
    required = len(farm.get("hands", []))
    actions = list(unit_actions[: required + 1])
    actions.extend([["PASS"]] * (required + 1 - len(actions)))
    seeds_used = {}
    clean_units = []
    for index, action in enumerate(actions):
        if _unit_legal(obs, index, action, seeds_used):
            clean_units.append(action)
            if action[0] == "PLANT":
                seeds_used[action[1]] = int(seeds_used.get(action[1], 0)) + 1
        else:
            clean_units.append(["PASS"])

    # Keep sell quantities bounded by the observed shed.  This check is
    # intentionally conservative: it does not invent market orders or change
    # the planner's capital plan, it only trims an impossible quantity.
    shed = {item: int(value) for item, value in obs["private"].get("shed", {}).items()}
    sold = {}
    clean_market = []
    for order in list(market or [])[:10]:
        if not isinstance(order, list) or not order:
            continue
        if order[0] != "SELL":
            clean_market.append(deepcopy(order))
            continue
        if len(order) < 3 or order[1] not in _SELLABLE:
            continue
        item = order[1]
        requested = max(0, int(order[2]))
        available = max(0, shed.get(item, 0) - sold.get(item, 0))
        quantity = min(requested, available)
        if quantity > 0:
            clean_market.append(["SELL", item, quantity])
            sold[item] = sold.get(item, 0) + quantity
    return clean_units, clean_market


def _step_toward(origin, target):
    x, y = origin
    tx, ty = target
    if tx < x:
        return ["WEST"]
    if tx > x:
        return ["EAST"]
    if ty < y:
        return ["NORTH"]
    if ty > y:
        return ["SOUTH"]
    return ["PASS"]


def _animal_safety_overrides(obs, units):
    """Patch imminent feeding misses while leaving ordinary crop work alone."""
    farm = obs["farms"][obs["player"]]
    positions = [farm["farmer"], *farm.get("hands", [])]
    inventories = obs["private"].get("inventories", [])
    animals = []
    for y, row in enumerate(farm["tiles"]):
        for x, tile in enumerate(row):
            if not _animal_tile(tile):
                continue
            if tile.get("fed_today", False):
                continue
            animals.append((x, y))
    if not animals:
        return units
    out = list(units)
    used = set()
    shed_targets = [(4, 4), (5, 4), (4, 5), (5, 5)]
    # Use every unit carrying wheat, and allow a unit to remain assigned to a
    # cluster on successive turns.  A one-to-one assignment leaves animals
    # stranded whenever there are more animals than workers (the common
    # 9-cow/4-sheep route has 13 animals but only 10 units).
    wheat_units = [
        i for i, inv in enumerate(inventories)
        if i < len(positions) and int(inv.get("WHEAT", 0)) > 0
    ]
    for index in wheat_units:
        if not animals:
            break
        target = min(animals, key=lambda p: abs(positions[index][0] - p[0]) + abs(positions[index][1] - p[1]))
        position = positions[index]
        if list(position) == list(target):
            out[index] = ["FEED"]
            animals.remove(target)
        else:
            out[index] = _step_toward(position, target)
    # If no worker currently carries feed, route the closest free unit to the
    # shed.  The next observation will see the pickup and the loop above will
    # resume the animal route.
    if animals and not wheat_units:
        free = [i for i in range(len(positions)) if i not in used]
        if free:
            index = min(free, key=lambda i: min(abs(positions[i][0] - p[0]) + abs(positions[i][1] - p[1]) for p in shed_targets))
            position = positions[index]
            shed = min(shed_targets, key=lambda p: abs(position[0] - p[0]) + abs(position[1] - p[1]))
            if list(position) == list(shed) and int(obs["private"].get("shed", {}).get("WHEAT", 0)) > 0:
                out[index] = ["PICKUP", "WHEAT", 4]
            else:
                out[index] = _step_toward(position, shed)
    return out


def _make_tail(obs):
    """Construct a crop-focused executor from the observed checkpoint.

    The executor deliberately has no animal target.  This is not pretending
    that animals disappeared: animal units are merged back from the backbone
    below, so all currently visible animals retain their original service
    route.  Crop capacity is inferred from the unlocked quadrants rather than
    from a historical expected-state anchor.
    """
    farm = obs["farms"][obs["player"]]
    quadrants = len(farm.get("unlocked_quadrants", []))
    crop_slots = 12 + max(0, quadrants - 1) * 12
    observed_animals = _animal_counts(farm)
    observed_animal_total = sum(observed_animals.values())
    config = deepcopy(_COMMON["CURRENT_BEST_CONFIG"])
    config.update(
        {
            "planner_enabled": True,
            "crop_mode": "planner",
            "base_plots": crop_slots,
            "max_plots": max(crop_slots, 36),
            "plots_per_land": 12,
            "quadrant_land_targets": False,
            # Keep the planner's feed-reserve accounting active for animals
            # already on the board.  No BUY_ANIMAL order is emitted because
            # the owned count meets this inferred target, and animal actions
            # are merged from the safety controller below.
            "animal_type": "COW" if observed_animal_total else None,
            "animal_count": observed_animal_total,
            "animal_portfolio": tuple((name, count) for name, count in observed_animals.items() if count),
            "animal_workers": max(1, min(4, observed_animal_total // 4)) if observed_animal_total else 0,
            "land_policy": "legacy",
            "enable_land": False,
            "max_land_purchases": 0,
            "selling_horizon": "legacy",
            "selling": "immediate",
            "liquidation_step": 648,
            "planner_fallback": True,
        }
    )
    tail = _COMMON["make_agent"](config)
    tail.config["inferred_animal_counts"] = observed_animals
    tail.config["inferred_quadrants"] = quadrants
    return tail


def make_agent(switch_step=240, safe_mode=False):
    """Return a state-driven crop executor with a safe backbone fallback."""

    tail = None
    telemetry = {
        "switch_step": int(switch_step),
        "tail_calls": 0,
        "tail_unit_actions": 0,
        "animal_delegations": 0,
        "fallback_calls": 0,
        "tail_exceptions": 0,
    }

    def agent(obs):
        nonlocal tail
        step = int(obs.get("step", 0))
        if step < int(switch_step):
            telemetry["fallback_calls"] += 1
            # The proven route intentionally relies on the environment's
            # action ordering (DROP/PICKUP happens before market orders).
            # Leave that transaction choreography untouched in the control
            # prefix; the semantic sanitizer is applied only to experimental
            # tail actions.
            return _BACKBONE(obs)

        if tail is None or step == int(switch_step):
            tail = _make_tail(obs)
            telemetry["tail_start_day"] = int(obs.get("day", 0))

        # Both controllers observe the same state.  Keeping the backbone call
        # here gives us a legal, proven animal-service action to merge in.
        fallback = _BACKBONE(obs)
        farm = obs["farms"][obs["player"]]
        if safe_mode:
            # Safety control: the full replay backbone remains authoritative
            # whenever livestock are present.  This isolates the economic
            # value of the crop planner from the known animal-routing gap.
            if any(_animal_tile(tile) for row in farm["tiles"] for tile in row):
                return fallback
        try:
            proposed = tail(obs)
            telemetry["tail_calls"] += 1
        except Exception:
            telemetry["tail_exceptions"] += 1
            return fallback

        positions = [farm["farmer"], *farm.get("hands", [])]
        proposed_units = [proposed.get("farmer", ["PASS"]), *proposed.get("hands", [])]
        fallback_units = [fallback.get("farmer", ["PASS"]), *fallback.get("hands", [])]
        # If the crop planner has not left enough time for a feed route, hand
        # the whole turn back to the coherent backbone.  This conservative
        # cut-over is the executor's safety contract; it is preferable to a
        # spectacular crop gain followed by an unrecoverable livestock loss.
        animal_due = any(
            _animal_tile(tile) and not tile.get("fed_today", False)
            for row in farm["tiles"] for tile in row
        )
        if animal_due and int(obs.get("hour", 0)) >= 16:
            safe = _animal_safety_overrides(obs, fallback_units)
            return {"farmer": safe[0], "hands": safe[1:], "market": fallback.get("market", [])}
        merged = []
        for index, position in enumerate(positions):
            x, y = position
            tile = farm["tiles"][y][x]
            proposed_action = proposed_units[index] if index < len(proposed_units) else ["PASS"]
            fallback_action = fallback_units[index] if index < len(fallback_units) else ["PASS"]
            if _animal_tile(tile):
                merged.append(deepcopy(fallback_action))
                telemetry["animal_delegations"] += 1
            else:
                merged.append(deepcopy(proposed_action))
                telemetry["tail_unit_actions"] += 1

        # Preserve the backbone's cash-flow transactions that fund existing
        # livestock (feed purchases, hires and realized sales), then append
        # only the planner's crop seed orders.  Letting the planner replace a
        # feed/hire batch was the first prototype's dominant failure mode: it
        # consumed the ten-order market budget on seeds and left animals with
        # no wheat.  No new animal or land commitment is admitted here.
        market = []
        observed_total = sum(_animal_counts(farm).values())
        feed_reserve = observed_total * 2
        for order in fallback.get("market", []):
            if order and order[0] in {"BUY_ANIMAL", "BUY_LAND"}:
                continue
            if order and order[0] == "SELL" and order[1] == "WHEAT" and observed_total:
                available = int(obs["private"].get("shed", {}).get("WHEAT", 0))
                quantity = min(int(order[2]), max(0, available - feed_reserve))
                if quantity <= 0:
                    continue
                order = ["SELL", "WHEAT", quantity]
            if len(market) < 10:
                market.append(deepcopy(order))
        for order in proposed.get("market", []):
            if not order or order[0] in {"BUY_ANIMAL", "BUY_LAND", "HIRE", "BUY_PRODUCT"}:
                continue
            if len(market) < 10:
                market.append(deepcopy(order))

        merged = _animal_safety_overrides(obs, merged)
        clean_units, clean_market = _sanitize(obs, merged, market)
        return {"farmer": clean_units[0], "hands": clean_units[1:], "market": clean_market}

    agent.telemetry = telemetry
    agent.switch_step = int(switch_step)
    agent.description = "Top-50 backbone opening + state-driven crop planner with animal-unit safety delegation"
    return agent


agent = make_agent()
