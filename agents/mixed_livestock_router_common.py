"""Replay-meta economics with scheduled mixed cow/sheep targets.

This is an experimental economic wrapper for the large-scale router.  The crop,
land, labor, feed, selling, and phase policies remain in the frozen replay-meta
engine; only animal species/count orders and matching pasture slots are added.
"""

from __future__ import annotations

from copy import deepcopy
from runpy import run_path


REPLAY = run_path("agents/replay_meta_common.py")
ROUTER = run_path("agents/large_scale_router.py")
SOURCE = ROUTER["SOURCE"]
ANIMALS = SOURCE["ANIMALS"]
CROPS = SOURCE["CROPS"]
LAND_COSTS = SOURCE["LAND_COSTS"]


def _fib(index):
    a, b = 1, 1
    for _ in range(index):
        a, b = b, a + b
    return a


def _active(schedule, day):
    target = schedule[0][1:]
    for start_day, cows, sheep in schedule:
        if day >= start_day:
            target = (cows, sheep)
    return target


def _owned(obs, animal):
    me = obs["farms"][obs["player"]]
    private = obs["private"]
    placed = sum(
        isinstance(tile, dict) and tile.get("animal") == animal
        for row in me["tiles"] for tile in row
    )
    return (
        placed
        + private["shed"].get(animal, 0)
        + sum(inventory.get(animal, 0) for inventory in private["inventories"])
    )


def _estimated_nonanimal_cost(obs, orders):
    me = obs["farms"][obs["player"]]
    next_hire = me.get("hires_today", 0)
    land_index = len(me["unlocked_quadrants"]) - 1
    cost = 0
    for order in orders:
        op = order[0]
        if op == "BUY_SEED":
            cost += CROPS[order[1]]["seed"] * order[2]
        elif op == "BUY_PRODUCT":
            cost += obs["market"]["prices"][order[1]] * order[2]
        elif op == "HIRE":
            cost += _fib(next_hire)
            next_hire += 1
        elif op == "BUY_LAND" and land_index < len(LAND_COSTS):
            cost += LAND_COSTS[land_index]
            land_index += 1
    return cost


def make_mixed_agent(schedule, slot_types, animal_workers=None):
    schedule = tuple(sorted((int(day), int(cows), int(sheep)) for day, cows, sheep in schedule))
    max_total = max(cows + sheep for _, cows, sheep in schedule)
    totals = tuple((day, cows + sheep) for day, cows, sheep in schedule)
    base = REPLAY["make_replay_agent"](
        {
            "base_plots": 10,
            "structure_start_day": 0,
            "animal_workers": 4,
            "animal_selling": "immediate",
            "wheat_reserve_days": 1,
            "require_animal_payback": False,
            "land_policy": "legacy",
            "forced_land_days": (6, 10),
            "enable_land": False,
            "quadrant_land_targets": True,
            "land_plots_per_quadrant": 25,
            "new_land_allocation": "adaptive",
            "fixed_hands": 4,
            "land_labor_mode": "staged",
            "land_plots_per_added_hand": 3,
            "max_hands": 14,
        },
        animal_schedule=totals,
        crop_schedule=(
            (0, ("mixed", ("MELON", "WHEAT"))),
            (3, ("fixed", "STRAWBERRY")),
            (21, ("fixed", "WHEAT")),
        ),
        labor_caps=REPLAY["REPLAY_LABOR_CAPS"],
    )

    slot_types = tuple(slot_types)
    if len(slot_types) != max_total:
        raise ValueError("slot_types must describe the maximum scheduled animal count")

    def active_config(obs):
        config = deepcopy(base.active_config(obs))
        cows, sheep = _active(schedule, obs["day"])
        config["animal_count"] = cows + sheep
        config["animal_workers"] = (
            int(animal_workers)
            if animal_workers is not None
            else max(4, (cows + sheep + 2) // 3)
        )
        position_config = deepcopy(config)
        position_config["animal_count"] = max_total
        positions = SOURCE["_animal_positions"](obs, position_config)
        remaining = {"COW": cows, "SHEEP": sheep}
        mapping = {}
        for position, animal in zip(positions, slot_types):
            if remaining.get(animal, 0) <= 0:
                continue
            mapping[position] = animal
            remaining[animal] -= 1
        config["mixed_animal_positions"] = mapping
        return config

    def economic_agent(obs):
        action = base(obs)
        cows, sheep = _active(schedule, obs["day"])
        desired = {"COW": cows, "SHEEP": sheep}
        orders = [order for order in action["market"] if order[0] != "BUY_ANIMAL"]

        # The public day-0 opening carries roughly one day of feed, not a full
        # two-day reserve.  Keep that exact capital bridge affordable.
        if obs["day"] == 0:
            feed_cap = max(0, cows + sheep - 1)
            for order in orders:
                if order[0] == "BUY_PRODUCT" and order[1] == "WHEAT":
                    order[2] = min(order[2], feed_cap)
            orders = [order for order in orders if len(order) < 3 or order[2] > 0]

        sale_value = sum(
            order[2] * obs["market"]["prices"][order[1]] * 0.75
            for order in orders if order[0] == "SELL"
        )
        budget = obs["farms"][obs["player"]]["money"] + sale_value
        animal_budget = max(0, budget - _estimated_nonanimal_cost(obs, orders))
        animal_orders = []
        # Preserve the requested mix when capital is tight by alternating the
        # species still furthest below target, with cow winning exact ties.
        needs = {animal: max(0, desired[animal] - _owned(obs, animal)) for animal in desired}
        bought = {"COW": 0, "SHEEP": 0}
        while any(needs.values()):
            candidates = [animal for animal, need in needs.items() if need > 0]
            animal = max(
                candidates,
                key=lambda item: (
                    needs[item] / max(1, desired[item]),
                    item == "COW",
                ),
            )
            cost = ANIMALS[animal]["cost"]
            if animal_budget < cost:
                needs[animal] = 0
                continue
            animal_budget -= cost
            needs[animal] -= 1
            bought[animal] += 1
        for animal in ("COW", "SHEEP"):
            if bought[animal]:
                animal_orders.append(["BUY_ANIMAL", animal, bought[animal]])

        insertion = 0
        while insertion < len(orders) and orders[insertion][0] == "SELL":
            insertion += 1
        action["market"] = (orders[:insertion] + animal_orders + orders[insertion:])[:10]
        return action

    economic_agent.config = base.config
    economic_agent.active_config = active_config
    economic_agent.schedule = schedule
    economic_agent.slot_types = slot_types
    return ROUTER["make_routed_agent"](economic_agent)
