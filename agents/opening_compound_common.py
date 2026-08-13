"""Replay-derived day 0-10 capital-compounding experiments.

This module changes opening economics and target layout only.  Unit assignment
still uses the frozen large-scale territory router.  Compact opening pasture
slots reproduce the spatial fact visible in the public replays: livestock is
serviced beside the shed while the initial 5x2 crop block sits farther away.
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

# Exact compact geometry shared by the selected public replay population.
SHEEP_SLOTS = ((4, 4), (4, 3), (3, 3), (4, 2))
COW_SLOTS = (
    (3, 4), (2, 4),
    (5, 4), (6, 4), (5, 3), (6, 3), (5, 2), (7, 4), (7, 3),
)


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
    return (
        sum(
            isinstance(tile, dict) and tile.get("animal") == animal
            for row in me["tiles"] for tile in row
        )
        + private["shed"].get(animal, 0)
        + sum(inventory.get(animal, 0) for inventory in private["inventories"])
    )


def _order_cost(obs, orders):
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


def _mixed_positions(cows, sheep):
    mapping = {}
    for position in COW_SLOTS[:cows]:
        mapping[position] = "COW"
    for position in SHEEP_SLOTS[:sheep]:
        mapping[position] = "SHEEP"
    return mapping


def make_opening_agent(
    *,
    schedule=((0, 1, 4), (5, 2, 4), (6, 3, 4), (7, 6, 4), (8, 8, 4), (15, 9, 4)),
    opening_pattern=("WHEAT",) * 5 + ("MELON",) * 5,
    wheat_reserve_days=1,
    day0_feed_units=5,
    feed_mode="survival",
    land_priority=False,
    hold_sales_until=None,
    labor_caps=None,
    animal_workers=4,
    wheat_harvest_age=4,
    post_crop_schedule=None,
    post_config=None,
):
    """Build a controlled opening variant with frozen post-opening policies."""

    schedule = tuple(sorted((int(day), int(cows), int(sheep)) for day, cows, sheep in schedule))
    opening_pattern = tuple(opening_pattern)
    hold_sales_until = dict(hold_sales_until or {})
    post_config = dict(post_config or {})
    labor_caps = tuple(labor_caps or REPLAY["REPLAY_LABOR_CAPS"])
    totals = tuple((day, cows + sheep) for day, cows, sheep in schedule)
    max_animals = max(cows + sheep for _, cows, sheep in schedule)

    # Convert the requested ten-crop allocation into persistent spatial lanes.
    # Wheat lanes remain wheat after their day-4 harvest; only new slots use
    # the replay's roughly 1-wheat/3-strawberry expansion mix.
    phase_pattern = ["STRAWBERRY"] * len(SOURCE["ALL_ROUTE"])
    initial_cows, initial_sheep = schedule[0][1:]
    initial_animals = set(_mixed_positions(initial_cows, initial_sheep))
    initial_base_plots = 10 + len(initial_animals)
    initial_positions = [
        position for position in SOURCE["NW_ROUTE"][:initial_base_plots]
        if position not in initial_animals
    ][:10]
    for position, crop in zip(initial_positions, opening_pattern):
        phase_pattern[SOURCE["ROUTE_ORDER"][position]] = crop
    initial_set = set(initial_positions)
    for position in SOURCE["ALL_ROUTE"]:
        index = SOURCE["ROUTE_ORDER"][position]
        if position not in initial_set and index >= 15 and index % 4 == 3:
            phase_pattern[index] = "WHEAT"
    phase_pattern = tuple(phase_pattern)

    def survival_day(day):
        # The replay population skips the unaffordable day-1 ration, then uses
        # the first fertilizer sale to begin daily feed/care compounding.
        return feed_mode == "survival" or (feed_mode == "hybrid" and day < 2)

    crop_schedule = tuple(post_crop_schedule or (
        (0, ("mixed", phase_pattern)),
        (11, ("fixed", "STRAWBERRY")),
        (21, ("fixed", "WHEAT")),
    ))

    def build_component(base_plots):
        return REPLAY["make_replay_agent"](
            {
                "base_plots": base_plots,
                "structure_start_day": 0,
                "animal_workers": animal_workers,
                "animal_selling": "immediate",
                "wheat_reserve_days": wheat_reserve_days,
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
            crop_schedule=crop_schedule,
            labor_caps=labor_caps,
        )

    # Ten opening crops, then the public replay's rapid fill of the remainder
    # of NW.  The routing view includes compact pasture tiles in its region;
    # they are filtered by ``mixed_animal_positions`` below.
    components = {"opening": build_component(10), "fill": build_component(20)}

    def selected(obs):
        return components["opening" if obs["day"] < 3 else "fill"]

    def active_config(obs):
        base = selected(obs)
        config = deepcopy(base.active_config(obs))
        cows, sheep = _active(schedule, obs["day"])
        config["animal_count"] = cows + sheep
        opening_animal_workers = (3, 1, 2, 2, 2, 2, 3, 4, 4, 4, 4)
        config["animal_workers"] = (
            opening_animal_workers[obs["day"]] if obs["day"] <= 10 else animal_workers
        )
        mapping = _mixed_positions(cows, sheep)
        nw_animals = sum(x < 5 and y < 5 for x, y in mapping)
        ne_animals = sum(x >= 5 and y < 5 for x, y in mapping)
        # Public productive-tile ramp (animals included): 15 through day 2,
        # 19 on days 3-4, 25 on day 5, 27/43/50 after the first deed, then 67
        # after the second.  Staging target slots is a capital policy: buying
        # all ten strawberry seeds on day 3 consumed the wool-land bridge.
        if obs["day"] < 3:
            core_crop_target = 10
        elif obs["day"] < 5:
            core_crop_target = 14
        else:
            core_crop_target = 19
        config["base_plots"] = core_crop_target + nw_animals
        if obs["day"] == 6:
            total_crop_target = 20
        elif obs["day"] == 7:
            total_crop_target = 33
        elif obs["day"] in {8, 9}:
            total_crop_target = 38
        elif obs["day"] == 10:
            total_crop_target = 55
        else:
            total_crop_target = None
        if total_crop_target is not None:
            extra_crops = max(0, total_crop_target - core_crop_target)
            if len(obs["farms"][obs["player"]]["unlocked_quadrants"]) >= 3:
                config["land_plots_per_quadrant"] = (extra_crops + ne_animals + 1) // 2
            else:
                config["land_plots_per_quadrant"] = extra_crops + ne_animals
        else:
            config["land_plots_per_quadrant"] = 25
        if obs["day"] <= 10:
            config["new_land_allocation"] = "strawberry_heavy"
        else:
            config.update(post_config)
        config["mixed_animal_positions"] = mapping
        return config

    def economic_agent(obs):
        action = selected(obs)(obs)
        cows, sheep = _active(schedule, obs["day"])
        desired = {"COW": cows, "SHEEP": sheep}
        # Reuse the frozen selling policy but schedule opening investments
        # explicitly. The legacy engine spent its budget on replacement seeds
        # before the next day's $1 hand, even when those replacement seeds were
        # filtered later; that hidden priority inversion killed animal service.
        sell_orders = [
            deepcopy(order) for order in action["market"] if order[0] == "SELL"
        ]
        for product, until_day in hold_sales_until.items():
            sell_orders = [
                order
                for order in sell_orders
                if not (order[1] == product and obs["day"] < until_day)
            ]
        if post_config.get("crop_fertilizer", False) and 10 < obs["day"] < 29:
            reserve = int(post_config.get("fertilizer_reserve", 12))
            adjusted = []
            for order in sell_orders:
                if order[1] == "FERTILIZER":
                    quantity = max(0, int(order[2]) - reserve)
                    if quantity:
                        adjusted.append(["SELL", "FERTILIZER", quantity])
                else:
                    adjusted.append(order)
            sell_orders = adjusted
        sale_value = sum(
            order[2] * obs["market"]["prices"][order[1]] * 0.90
            for order in sell_orders
        )
        budget = obs["farms"][obs["player"]]["money"] + sale_value

        me = obs["farms"][obs["player"]]
        desired_hands = int(labor_caps[min(obs["day"], len(labor_caps) - 1)])
        hire_orders = []
        for hire_index in range(me.get("hires_today", 0), desired_hands):
            cost = _fib(hire_index)
            if budget < cost:
                break
            hire_orders.append(["HIRE"])
            budget -= cost

        config = active_config(obs)
        crop_positions = SOURCE["_target_positions"](obs, config)
        mixed_positions = set(config["mixed_animal_positions"])
        crop_positions = tuple(position for position in crop_positions if position not in mixed_positions)
        choices = SOURCE["_plan_crops"](obs, crop_positions, config)

        # Existing animals and the next day's service labor are senior claims
        # on cash. Expanding the herd before reserving wheat caused otherwise
        # profitable sheep to escape precisely as their first wool matured.
        private = obs["private"]
        wheat_owned = private["shed"].get("WHEAT", 0) + sum(
            inventory.get("WHEAT", 0) for inventory in private["inventories"]
        )
        target_feed = cows + sheep
        if obs["day"] == 0:
            target_feed = day0_feed_units if obs["hour"] == 0 else 0
        else:
            if survival_day(obs["day"]):
                target_feed = sum(
                    bool(
                        isinstance(tile, dict)
                        and tile.get("animal")
                        and not tile.get("fed_today", False)
                        and tile.get("consecutive_unfed", 0) >= 1
                    )
                    for row in me["tiles"] for tile in row
                )
            else:
                target_feed *= wheat_reserve_days
            if obs["hour"] != 0:
                target_feed = 0
        wheat_needed = max(0, target_feed - wheat_owned)
        wheat_price = max(1, obs["market"]["prices"]["WHEAT"])
        wheat_buy = min(wheat_needed, int(budget // wheat_price))
        budget -= wheat_buy * wheat_price
        feed_orders = [["BUY_PRODUCT", "WHEAT", wheat_buy]] if wheat_buy else []

        # The forced deeds are opening milestones, not residual purchases.
        land_due = False
        purchased = len(me["unlocked_quadrants"]) - 1
        forced_days = (6, 10)
        if purchased < len(forced_days) and obs["day"] >= forced_days[purchased]:
            land_due = True
        land_orders = []
        land_cost = LAND_COSTS[purchased] if purchased < len(LAND_COSTS) else 0
        if land_priority and land_due and budget >= land_cost:
            land_orders.append(["BUY_LAND"])
            budget -= land_cost

        animal_orders = []
        needs = {animal: max(0, desired[animal] - _owned(obs, animal)) for animal in desired}
        bought = {"COW": 0, "SHEEP": 0}
        while any(needs.values()):
            candidates = [animal for animal, need in needs.items() if need > 0]
            animal = max(
                candidates,
                key=lambda item: (needs[item] / max(1, desired[item]), item == "COW"),
            )
            cost = ANIMALS[animal]["cost"]
            if budget < cost:
                needs[animal] = 0
                continue
            budget -= cost
            needs[animal] -= 1
            bought[animal] += 1
        for animal in ("COW", "SHEEP"):
            if bought[animal]:
                animal_orders.append(["BUY_ANIMAL", animal, bought[animal]])

        if not land_priority and land_due and budget >= land_cost:
            land_orders.append(["BUY_LAND"])
            budget -= land_cost

        seed_orders = []
        seed_inventory = dict(private["seeds"])
        needed_by_crop = {crop: 0 for crop in CROPS}
        for position, crop in choices.items():
            x, y = position
            if me["tiles"][y][x] is None:
                needed_by_crop[crop] += 1
        for crop in CROPS:
            needed = max(0, needed_by_crop[crop] - seed_inventory.get(crop, 0))
            quantity = min(needed, int(budget // CROPS[crop]["seed"]))
            if quantity:
                seed_orders.append(["BUY_SEED", crop, quantity])
                budget -= quantity * CROPS[crop]["seed"]

        if land_priority:
            investment_orders = land_orders + animal_orders
        else:
            investment_orders = animal_orders + land_orders
        action["market"] = (
            sell_orders + investment_orders + feed_orders + hire_orders + seed_orders
        )[:10]
        return action

    economic_agent.config = components["opening"].config
    economic_agent.active_config = active_config
    economic_agent.schedule = schedule
    economic_agent.opening_pattern = opening_pattern
    economic_agent.components = components
    routed = ROUTER["make_routed_agent"](economic_agent)

    def harvest_planning_obs(obs):
        if wheat_harvest_age >= CROPS["WHEAT"]["peak"] or obs["day"] > 10:
            return obs
        changed = None
        for y, row in enumerate(obs["farms"][obs["player"]]["tiles"]):
            for x, tile in enumerate(row):
                if (
                    isinstance(tile, dict)
                    and tile.get("kind") == "PLANT"
                    and tile.get("crop") == "WHEAT"
                    and tile.get("yield_units", 0) > 0
                    and obs["day"] - tile.get("planted_day", obs["day"]) >= wheat_harvest_age
                ):
                    if changed is None:
                        changed = deepcopy(obs)
                    changed["farms"][obs["player"]]["tiles"][y][x]["planted_day"] = (
                        obs["day"] - CROPS["WHEAT"]["peak"]
                    )
        return changed if changed is not None else obs

    def opening_service_override(obs, action):
        """Batch urgent opening animal work without changing the main router."""
        if obs["day"] > 10:
            return action
        me = obs["farms"][obs["player"]]
        positions = [tuple(me["farmer"])] + [tuple(value) for value in me["hands"]]
        inventories = obs["private"]["inventories"]
        unit_actions = [action["farmer"]] + list(action["hands"])
        config = active_config(obs)
        targets = [
            tuple(position)
            for position in config["mixed_animal_positions"]
            if isinstance(me["tiles"][position[1]][position[0]], dict)
            and me["tiles"][position[1]][position[0]].get("animal")
        ]
        if not targets:
            return action
        specialist_count = min(config["animal_workers"], len(config["mixed_animal_positions"]))
        specialists = ROUTER["_animal_specialists"](len(positions), specialist_count)
        ordered_targets = sorted(
            config["mixed_animal_positions"].items(),
            key=lambda row: SOURCE["ROUTE_ORDER"].get(tuple(row[0]), 999),
        )
        assignments = {
            index: ROUTER["_partition"](ordered_targets, rank, len(specialists))
            for rank, index in enumerate(specialists)
        }
        feed_targets = []
        for target in targets:
            tile = me["tiles"][target[1]][target[0]]
            if tile.get("fed_today", False):
                continue
            if not survival_day(obs["day"]) or obs["day"] == 0 or tile.get("consecutive_unfed", 0) >= 1:
                feed_targets.append(target)
        harvest_targets = [
            target for target in targets
            if me["tiles"][target[1]][target[0]].get("yield_units", 0) > 0
        ]
        care_targets = [
            target for target in targets
            if me["tiles"][target[1]][target[0]].get("fed_today", False)
            and not me["tiles"][target[1]][target[0]].get("cared_today", False)
        ]
        fertilizer_targets = [
            target for target in targets
            if me["tiles"][target[1]][target[0]].get("fertilizer_available", False)
        ]
        reserved = set()
        shed_wheat = obs["private"]["shed"].get("WHEAT", 0)
        for index in specialists:
            if index >= len(unit_actions):
                continue
            current = unit_actions[index]
            op = current[0]
            if op in {"BUILD_PASTURE", "BUILD_COOP", "PLACE"}:
                continue
            if op == "PICKUP" and len(current) > 1 and current[1] in ANIMALS:
                continue
            if any(inventories[index].get(animal, 0) for animal in ANIMALS):
                continue
            position = positions[index]
            unfinished = False
            for target, animal in assignments.get(index, ()):
                target = tuple(target)
                tile = me["tiles"][target[1]][target[0]]
                if tile == "LOCKED":
                    continue
                if tile is None or (isinstance(tile, dict) and tile.get("kind") == "WEED"):
                    unfinished = True
                    break
                if (
                    isinstance(tile, dict)
                    and tile.get("kind") == ANIMALS[animal]["structure"]
                    and not tile.get("animal")
                    and obs["private"]["shed"].get(animal, 0) > 0
                ):
                    unfinished = True
                    break
            if unfinished:
                # Preserve the frozen router's travel toward BUILD/PICKUP/PLACE;
                # overriding only the terminal op left new cows in the shed.
                continue
            candidates = [target for target in feed_targets if target not in reserved]
            if candidates:
                if inventories[index].get("WHEAT", 0) > 0:
                    target = min(candidates, key=lambda value: ROUTER["_distance"](position, value))
                    reserved.add(target)
                    unit_actions[index] = ["FEED"] if position == target else ROUTER["_move_toward"](position, target)
                    continue
                if shed_wheat > 0:
                    if position in SOURCE["SHED_TILES"]:
                        amount = min(shed_wheat, max(1, (len(candidates) + 1) // 2))
                        unit_actions[index] = ["PICKUP", "WHEAT", amount]
                        shed_wheat -= amount
                    else:
                        target = ROUTER["_nearest"](position, SOURCE["SHED_TILES"])
                        unit_actions[index] = ROUTER["_move_toward"](position, target)
                    continue
            for task_targets, op_name in (
                (harvest_targets, "HARVEST"),
                (care_targets, "CARE"),
                (fertilizer_targets, "COLLECT_FERTILIZER"),
            ):
                candidates = [target for target in task_targets if target not in reserved]
                if not candidates:
                    continue
                target = min(candidates, key=lambda value: ROUTER["_distance"](position, value))
                reserved.add(target)
                unit_actions[index] = [op_name] if position == target else ROUTER["_move_toward"](position, target)
                break
        action["farmer"] = unit_actions[0]
        action["hands"] = unit_actions[1:]
        return action

    def opening_cash_return(obs, action):
        if obs["day"] != 10:
            return action
        me = obs["farms"][obs["player"]]
        positions = [tuple(me["farmer"])] + [tuple(value) for value in me["hands"]]
        unit_actions = [action["farmer"]] + list(action["hands"])
        for index, inventory in enumerate(obs["private"]["inventories"]):
            if inventory.get("MELON", 0) <= 0:
                continue
            position = positions[index]
            target = ROUTER["_nearest"](position, SOURCE["SHED_TILES"])
            unit_actions[index] = ["DROP"] if position in SOURCE["SHED_TILES"] else ROUTER["_move_toward"](position, target)
        action["farmer"] = unit_actions[0]
        action["hands"] = unit_actions[1:]
        return action

    def repair_shed_feed_transfer(obs, action):
        """Fix the opening-only shed-tile pickup deadlock.

        An animal can occupy (4, 4), which is also shed-adjacent. The frozen
        router moves toward the nearest shed tile when it lacks wheat; at an
        already-nearest tile that becomes PASS instead of PICKUP. Public paths
        explicitly pick up here. Limit the repair to otherwise-idle units and
        animals that must be fed now.
        """
        available = obs["private"]["shed"].get("WHEAT", 0)
        if available <= 0:
            return action
        me = obs["farms"][obs["player"]]
        positions = [tuple(me["farmer"])] + [tuple(value) for value in me["hands"]]
        unit_actions = [action["farmer"]] + list(action["hands"])
        inventories = obs["private"]["inventories"]
        for index, position in enumerate(positions):
            if available <= 0 or unit_actions[index][0] != "PASS" or position not in SOURCE["SHED_TILES"]:
                continue
            tile = me["tiles"][position[1]][position[0]]
            urgent = (
                isinstance(tile, dict)
                and tile.get("animal")
                and not tile.get("fed_today", False)
                and (obs["day"] == 0 or tile.get("consecutive_unfed", 0) >= 1)
            )
            if not urgent:
                continue
            if inventories[index].get("WHEAT", 0) > 0:
                unit_actions[index] = ["FEED"]
            else:
                unit_actions[index] = ["PICKUP", "WHEAT", 1]
                available -= 1
        action["farmer"] = unit_actions[0]
        action["hands"] = unit_actions[1:]
        return action

    if feed_mode == "daily":
        def daily_routed(obs):
            planning = harvest_planning_obs(obs)
            return opening_cash_return(
                obs,
                repair_shed_feed_transfer(
                    obs, opening_service_override(obs, routed(planning))
                ),
            )
        daily_routed.config = economic_agent.config
        daily_routed.base_agent = economic_agent
        return daily_routed

    def survival_routed(obs):
        if obs["day"] == 0 or not survival_day(obs["day"]):
            planning = harvest_planning_obs(obs)
            return opening_cash_return(
                obs,
                repair_shed_feed_transfer(
                    obs, opening_service_override(obs, routed(planning))
                ),
            )
        planning = deepcopy(harvest_planning_obs(obs))
        urgent_exists = any(
            isinstance(tile, dict)
            and tile.get("animal")
            and not tile.get("fed_today", False)
            and tile.get("consecutive_unfed", 0) >= 1
            for row in obs["farms"][obs["player"]]["tiles"] for tile in row
        )
        for row in planning["farms"][planning["player"]]["tiles"]:
            for tile in row:
                if (
                    isinstance(tile, dict)
                    and tile.get("animal")
                    and not tile.get("fed_today", False)
                    and tile.get("consecutive_unfed", 0) < 1
                ):
                    tile["fed_today"] = True
                    if urgent_exists:
                        # Do not let optional care/collection on a safe animal
                        # consume the only path to an at-risk pasture. As soon
                        # as every critical animal is fed, the next observation
                        # releases these tasks for the rest of the day.
                        tile["cared_today"] = True
                        tile["fertilizer_available"] = False
        return opening_cash_return(
            obs,
            repair_shed_feed_transfer(
                obs, opening_service_override(obs, routed(planning))
            ),
        )

    survival_routed.config = economic_agent.config
    survival_routed.base_agent = economic_agent
    return survival_routed
