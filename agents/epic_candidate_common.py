"""Isolated epic-stage candidate factory.

The promoted lifecycle agent and its dependencies stay frozen.  Candidates in
this research branch use private copies of the opening engine and router so an
opt-in scheduler experiment cannot silently alter the control.
"""

from __future__ import annotations

from copy import deepcopy
from collections import Counter
from runpy import run_path


COMMON = run_path("agents/epic_opening_common.py")
SOURCE = COMMON["SOURCE"]
REPLAY = COMMON["REPLAY"]
CROPS = COMMON["CROPS"]

BASE_SCHEDULE = ((0, 1, 4), (5, 2, 4), (6, 8, 4), (15, 9, 4))
BASE_POST_CONFIG = {
    "harvest_policy": "ready_ongoing",
    "harvest_priority": 0.75,
    "chain_replant": True,
    "chain_last_hour": 21,
}


def opening_phase_pattern():
    """Reproduce the frozen 5-wheat/5-melon opening spatially."""

    phase = ["STRAWBERRY"] * len(SOURCE["ALL_ROUTE"])
    initial_animals = set(COMMON["_mixed_positions"](1, 4))
    initial_positions = [
        position for position in SOURCE["NW_ROUTE"][:15]
        if position not in initial_animals
    ][:10]
    for position, crop in zip(initial_positions, ("WHEAT",) * 5 + ("MELON",) * 5):
        phase[SOURCE["ROUTE_ORDER"][position]] = crop
    initial_set = set(initial_positions)
    for position in SOURCE["ALL_ROUTE"]:
        index = SOURCE["ROUTE_ORDER"][position]
        if position not in initial_set and index >= 15 and index % 4 == 3:
            phase[index] = "WHEAT"
    return tuple(phase)


def replay_midgame_pattern():
    """Replay-derived 13-melon/roughly 13-wheat three-quadrant phase.

    The melon block is contiguous in the NW/SW rows used by nearly every top
    appearance.  Existing opening wheat lanes remain wheat; the remaining
    productive crop slots are strawberry.
    """

    phase = list(opening_phase_pattern())
    melon_block = {
        *((x, 1) for x in range(5)),
        *((x, 5) for x in range(5)),
        (0, 6), (1, 6), (3, 6),
    }
    for position in SOURCE["ALL_ROUTE"]:
        index = SOURCE["ROUTE_ORDER"][position]
        if position in melon_block:
            phase[index] = "MELON"
        elif phase[index] != "WHEAT":
            phase[index] = "STRAWBERRY"
    return tuple(phase)


def _smooth_pattern(mix, *, structure="synchronized", offset=0):
    """Build a deterministic crop territory from replay-range proportions."""

    weights = {crop: float(mix.get(crop, 0)) for crop in CROPS}
    weights = {crop: value for crop, value in weights.items() if value > 0}
    if not weights:
        weights = {"WHEAT": 1.0}
    total = sum(weights.values())
    weights = {crop: value / total for crop, value in weights.items()}
    crop_order = sorted(weights, key=lambda crop: (-weights[crop], crop))

    def sequence(length):
        counts = {crop: int(length * weights[crop]) for crop in weights}
        remainder = length - sum(counts.values())
        fractions = sorted(
            weights,
            key=lambda crop: (-(length * weights[crop] - counts[crop]), crop),
        )
        for crop in fractions[:remainder]:
            counts[crop] += 1
        if structure == "staggered":
            output = []
            used = Counter()
            for index in range(length):
                eligible = [crop for crop in crop_order if used[crop] < counts[crop]]
                crop = max(
                    eligible,
                    key=lambda item: (
                        (index + 1) * weights[item] - used[item],
                        weights[item], item,
                    ),
                )
                output.append(crop)
                used[crop] += 1
            return output
        output = []
        for crop in crop_order:
            output.extend([crop] * counts[crop])
        if output and offset:
            shift = int(offset) % len(output)
            output = output[shift:] + output[:shift]
        return output

    if structure == "quadrant":
        pattern = ["WHEAT"] * len(SOURCE["ALL_ROUTE"])
        for index, route in enumerate((SOURCE["NW_ROUTE"], SOURCE["NE_ROUTE"], SOURCE["SW_ROUTE"], SOURCE["SE_ROUTE"])):
            values = sequence(len(route))
            if index % 2:
                values = values[1:] + values[:1]
            for position, crop in zip(route, values):
                pattern[SOURCE["ROUTE_ORDER"][position]] = crop
        return tuple(pattern)
    return tuple(sequence(len(SOURCE["ALL_ROUTE"])))


def multiwave_schedule(config):
    """Translate a serializable capital-wave configuration into crop intent."""

    opening = list(opening_phase_pattern())
    extension = _smooth_pattern(
        config.get("opening_extension_mix", {"MELON": .30, "STRAWBERRY": .50, "WHEAT": .20}),
        structure=config.get("opening_structure", "staggered"),
    )
    # Keep the proven first ten positions exactly 5 wheat/5 melon. Only slots
    # exposed by the day-3/day-6 expansion use the searched extension mix.
    initial_animals = set(COMMON["_mixed_positions"](1, 4))
    initial_positions = [
        position for position in SOURCE["NW_ROUTE"][:15]
        if position not in initial_animals
    ][:10]
    protected = set(initial_positions)
    for position in SOURCE["ALL_ROUTE"]:
        if position not in protected:
            index = SOURCE["ROUTE_ORDER"][position]
            opening[index] = extension[index]

    wave1 = _smooth_pattern(
        config["wave1_mix"], structure=config.get("wave1_structure", "synchronized"),
        offset=config.get("wave1_offset", 0),
    )
    wave2 = _smooth_pattern(
        config["wave2_mix"], structure=config.get("wave2_structure", "synchronized"),
        offset=config.get("wave2_offset", 0),
    )
    wave3 = _smooth_pattern(
        config.get("wave3_mix", {"WHEAT": .80, "STRAWBERRY": .20}),
        structure=config.get("wave3_structure", "staggered"),
        offset=config.get("wave3_offset", 0),
    )
    return (
        (0, ("mixed", tuple(opening))),
        (int(config["wave1_start_day"]), ("mixed", wave1)),
        (int(config["wave2_start_day"]), ("mixed", wave2)),
        (int(config["wave3_start_day"]), ("mixed", wave3)),
    )


def crop_schedule(kind="frozen"):
    opening = opening_phase_pattern()
    if kind == "frozen":
        return (
            (0, ("mixed", opening)),
            (11, ("fixed", "STRAWBERRY")),
            (21, ("fixed", "WHEAT")),
        )
    if kind == "replay_phase":
        return (
            (0, ("mixed", opening)),
            # Keep the promoted public opening byte-for-byte through day 10.
            # The replay phase governs replacement/new planting from day 11.
            (11, ("mixed", replay_midgame_pattern())),
            (20, ("fixed", "WHEAT")),
        )
    if kind == "capital_window":
        return (
            (0, ("mixed", opening)),
            # The first fully-watered melon cohort is converted to cash on
            # day 10.  Use the proceeds to establish the replay-derived
            # second cohort immediately, not after a one-day dead zone.
            (10, ("mixed", replay_midgame_pattern())),
            (20, ("fixed", "WHEAT")),
        )
    raise ValueError(f"unknown crop schedule: {kind}")


def animal_schedule(cows=9):
    if cows == "adaptive7":
        return ((0, 1, 4), (5, 2, 4), (6, 6, 4), (13, 7, 4))
    if cows == "adaptive8":
        # The engine is built with two extra pasture slots.  The active
        # configuration below keeps the actual target at six unless the
        # replay-grounded late-annuity gate passes.
        return ((0, 1, 4), (5, 2, 4), (6, 6, 4), (13, 8, 4))
    cows = int(cows)
    if cows == 9:
        return BASE_SCHEDULE
    if cows not in {6, 7, 8}:
        raise ValueError("controlled cow count must be 6, 7, 8, or 9")
    return ((0, 1, 4), (5, 2, 4), (6, cows, 4), (15, cows, 4))


def make_candidate(*, config=None, cows=9, phase="frozen"):
    caps = list(REPLAY["REPLAY_LABOR_CAPS"])
    caps[0] = 5
    post_config = deepcopy(BASE_POST_CONFIG)
    post_config.update(config or {})
    if phase in {"replay_phase", "capital_window"}:
        # The historical engine's new-land allocator otherwise overrides the
        # spatial mixed pattern outside NW, making the crop-phase experiment a
        # no-op on most of the three-quadrant farm.
        post_config["new_land_allocation"] = "inherit"
    if phase == "capital_window":
        post_config["capital_phase_start_day"] = 10
    if phase == "capital_planner":
        post_config.update({
            "new_land_allocation": "inherit",
            "capital_phase_start_day": 10,
            "capital_planner": True,
            "capital_pattern": replay_midgame_pattern(),
        })
        phase = "capital_window"
    schedule = animal_schedule(cows)
    return COMMON["make_opening_agent"](
        schedule=schedule,
        feed_mode="hybrid",
        land_priority=True,
        labor_caps=tuple(caps),
        post_crop_schedule=crop_schedule(phase),
        post_config=post_config,
    )


def make_multiwave_candidate(config):
    """Create one multi-wave architecture without generating an agent file."""

    config = deepcopy(config)
    cows = int(config.get("cow_target", 6))
    caps = list(REPLAY["REPLAY_LABOR_CAPS"])
    caps[0] = 5
    hand_mode = config.get("hand_policy", "replay")
    if isinstance(hand_mode, int):
        for day in range(10, len(caps)):
            caps[day] = min(caps[day], int(hand_mode))
    elif hand_mode in {"10", "12", "14"}:
        limit = int(hand_mode)
        for day in range(10, len(caps)):
            caps[day] = min(caps[day], limit)
    post = deepcopy(BASE_POST_CONFIG)
    post.update({
        "capital_yield_completion": True,
        "value_scheduler": True,
        "new_land_allocation": "inherit",
        "capital_phase_start_day": int(config["wave1_start_day"]),
        "multiwave": config,
        "plant_admission": bool(config.get("plant_admission", False)),
        "plant_admission_last_hour": int(config.get("plant_cutoff_hour", 20)),
    })
    return COMMON["make_opening_agent"](
        schedule=animal_schedule(cows),
        feed_mode="hybrid",
        land_priority=True,
        labor_caps=tuple(caps),
        post_crop_schedule=multiwave_schedule(config),
        post_config=post,
    )


def demand_capture_wrapper(base_agent, *, start_day=11, units=16, cash_reserve=1500):
    """Buy wheat immediately before observed four-turn town consumption.

    Town consumes after market processing on steps divisible by four.  Buying
    on that tick and allowing the frozen immediate-sale policy to liquidate on
    the following tick is Pedro's measured structural edge.  The wrapper is
    deliberately bounded by visible demand, shed capacity, cash reserve, and
    the ten-order market cap.
    """

    wheat_shops = {"BAKERY", "PIZZA", "BRUNCH", "ICE_CREAM", "FARMERS_MARKET"}

    def agent(obs):
        action = deepcopy(base_agent(obs))
        if obs["day"] < start_day or obs["day"] >= 29 or obs["step"] % 4:
            return action
        shops = [str(value).upper().replace(" ", "_") for value in obs["town"]["unlocked_shops"]]
        demand = 1 + sum(1 for value in shops if value in wheat_shops)
        if demand <= 1:
            return action
        orders = [order for order in action["market"] if not (order[0] == "SELL" and order[1] == "WHEAT")]
        if len(orders) >= 10:
            action["market"] = orders[:10]
            return action
        me = obs["farms"][obs["player"]]
        price = max(1, int(obs["market"]["prices"]["WHEAT"]))
        budget = max(0, int(me["money"] - cash_reserve))
        carried = sum(sum(inv.get(item, 0) for item in CROPS) for inv in obs["private"]["inventories"])
        shed_used = sum(obs["private"]["shed"].values())
        capacity = max(0, 96 - shed_used - carried)
        quantity = min(int(units), demand * 4, capacity, budget // price)
        if quantity > 0:
            orders.append(["BUY_PRODUCT", "WHEAT", quantity])
        action["market"] = orders[:10]
        return action

    return agent


def semantic_animal_guard(base_agent):
    """Suppress a later duplicate terminal action on the same animal tile.

    Multiple hands may share a tile.  The engine applies their actions in
    order, so two valid-looking COLLECT/HARVEST requests can make the second a
    silent no-op.  This guard changes only that later duplicate request.
    """

    terminal = {"FEED", "CARE", "COLLECT_FERTILIZER", "HARVEST"}

    def agent(obs):
        action = deepcopy(base_agent(obs))
        me = obs["farms"][obs["player"]]
        positions = [tuple(me["farmer"])] + [tuple(value) for value in me["hands"]]
        unit_actions = [action["farmer"], *action["hands"]]
        claimed = set()
        for index, (position, unit_action) in enumerate(zip(positions, unit_actions)):
            op = unit_action[0] if unit_action else "PASS"
            tile = me["tiles"][position[1]][position[0]]
            if op not in terminal or not isinstance(tile, dict) or not tile.get("animal"):
                continue
            if position in claimed:
                unit_actions[index] = ["PASS"]
            else:
                claimed.add(position)
        action["farmer"] = unit_actions[0]
        action["hands"] = unit_actions[1:]
        return action

    return agent


def oscillating_wheat_market_maker(
    base_agent, *, start_day=7, units=18, cash_reserve=250
):
    """Replay-faithful two-turn wheat inventory cycle.

    Pedro repeatedly removes roughly one price-step of wheat inventory on even
    turns and returns it on odd turns.  This is intentionally a separate
    economic ablation; it does not alter field scheduling or crop allocation.
    """

    def agent(obs):
        action = deepcopy(base_agent(obs))
        if obs["day"] < start_day or obs["day"] >= 29:
            return action
        if obs["step"] % 2:
            return action
        orders = [
            order for order in action["market"]
            if not (order[0] == "SELL" and order[1] == "WHEAT")
        ]
        if len(orders) >= 10:
            action["market"] = orders[:10]
            return action
        me = obs["farms"][obs["player"]]
        price = max(1, int(obs["market"]["prices"]["WHEAT"]))
        budget = max(0, int(me["money"] - cash_reserve))
        shed_used = sum(obs["private"]["shed"].values())
        carried = sum(sum(inv.get(item, 0) for item in CROPS) for inv in obs["private"]["inventories"])
        capacity = max(0, 96 - shed_used - carried)
        quantity = min(int(units), capacity, budget // price)
        if quantity:
            orders.append(["BUY_PRODUCT", "WHEAT", quantity])
        action["market"] = orders[:10]
        return action

    return agent
