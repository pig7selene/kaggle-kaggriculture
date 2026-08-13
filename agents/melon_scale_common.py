"""Shared scale-only melon strategy used by the crop-choice experiments."""

import math


MELON = "MELON"
MELON_SEED_COST = 80
MELON_HARVEST_AGE = 10
TURNS_PER_DAY = 24
PLOTS_PER_WORKER = 4

# Keep the carrot experiment's continuous route through the unlocked NW
# quadrant so crop choice remains the only meaningful strategy change.
PLOT_ROUTE = (
    (4, 4), (3, 4), (2, 4), (2, 3),
    (3, 3), (4, 3), (4, 2), (3, 2),
    (2, 2), (1, 2), (1, 3), (1, 4),
    (0, 4), (0, 3), (0, 2), (0, 1),
    (1, 1), (2, 1), (3, 1), (4, 1),
    (4, 0), (3, 0), (2, 0), (1, 0), (0, 0),
)


def _is_plant(tile):
    return isinstance(tile, dict) and tile.get("kind") == "PLANT"


def _nearest(origin, candidates, plot_order):
    return min(
        candidates,
        key=lambda position: (
            abs(position[0] - origin[0]) + abs(position[1] - origin[1]),
            plot_order[position],
        ),
    )


def _move_toward(origin, target):
    x, y = origin
    target_x, target_y = target
    if target_x < x:
        return ["WEST"]
    if target_x > x:
        return ["EAST"]
    if target_y < y:
        return ["NORTH"]
    if target_y > y:
        return ["SOUTH"]
    return ["PASS"]


def _worker_action(position, assigned_plots, tiles, day, hour, seeds, plot_order):
    unwatered = []
    harvestable = []
    weeds = []
    empty = []

    for x, y in assigned_plots:
        tile = tiles[y][x]
        if _is_plant(tile) and tile.get("crop") == MELON:
            if not tile.get("watered_today", False):
                unwatered.append((x, y))
            elif (
                day - tile["planted_day"] >= MELON_HARVEST_AGE
                and tile.get("yield_units", 0) > 0
            ):
                harvestable.append((x, y))
        elif isinstance(tile, dict) and tile.get("kind") == "WEED":
            weeds.append((x, y))
        elif tile is None:
            empty.append((x, y))

    # Daily watering is mandatory. For melons, ages 6-10 also fill the five
    # bonus-yield units, reaching the unfertilized cap of six before harvest.
    if unwatered:
        target = _nearest(position, unwatered, plot_order)
        return (["WATER"] if position == target else _move_toward(position, target), 0)
    if harvestable:
        target = _nearest(position, harvestable, plot_order)
        return (
            ["HARVEST"] if position == target else _move_toward(position, target),
            0,
        )
    if weeds:
        target = _nearest(position, weeds, plot_order)
        return (["DIG"] if position == target else _move_toward(position, target), 0)
    if empty and seeds > 0:
        target = _nearest(position, empty, plot_order)
        if position != target:
            return (_move_toward(position, target), 0)
        # A crop planted on the final turn of a day would immediately record
        # its first missed watering refresh, so defer that replant by one turn.
        if hour < TURNS_PER_DAY - 1:
            return (["PLANT", MELON], 1)
    return (["PASS"], 0)


def _fib(index):
    a, b = 1, 1
    for _ in range(index):
        a, b = b, a + b
    return a


def make_agent(plot_count):
    """Create a melon agent whose only parameter is initial farm scale."""
    if plot_count < 1 or plot_count > len(PLOT_ROUTE):
        raise ValueError("plot_count must be between 1 and 25")

    plots = PLOT_ROUTE[:plot_count]
    plot_order = {position: index for index, position in enumerate(plots)}
    worker_count = math.ceil(plot_count / PLOTS_PER_WORKER)
    desired_hands = worker_count - 1
    assignments = tuple(
        plots[index * PLOTS_PER_WORKER : (index + 1) * PLOTS_PER_WORKER]
        for index in range(worker_count)
    )

    def scaled_melon_agent(obs):
        player = obs["player"]
        me = obs["farms"][player]
        private = obs["private"]
        tiles = me["tiles"]

        market = []
        shed_melons = private["shed"].get(MELON, 0)
        if shed_melons > 0:
            market.append(["SELL", MELON, shed_melons])

        planted = sum(
            1
            for x, y in plots
            if _is_plant(tiles[y][x]) and tiles[y][x].get("crop") == MELON
        )
        seeds = private["seeds"].get(MELON, 0)
        needed = max(0, plot_count - planted - seeds)
        budget = float(me["money"])
        to_buy = min(needed, int(budget // MELON_SEED_COST))
        if to_buy > 0:
            market.append(["BUY_SEED", MELON, to_buy])
            budget -= to_buy * MELON_SEED_COST

        # Twenty initial seeds cost 1600, leaving ample starting capital for
        # four daily hires (1 + 1 + 2 + 3 = 7). On later cycles, purchases are
        # limited to cash on hand and hires use whatever capital remains.
        hires_today = me.get("hires_today", 0)
        for hire_index in range(hires_today, desired_hands):
            cost = _fib(hire_index)
            if budget < cost:
                break
            market.append(["HIRE"])
            budget -= cost

        positions = [tuple(me["farmer"])] + [tuple(pos) for pos in me["hands"]]
        remaining_seeds = seeds
        actions = []
        for worker_index, position in enumerate(positions):
            if worker_index >= len(assignments):
                actions.append(["PASS"])
                continue
            action, seeds_used = _worker_action(
                position=position,
                assigned_plots=assignments[worker_index],
                tiles=tiles,
                day=obs["day"],
                hour=obs["hour"],
                seeds=remaining_seeds,
                plot_order=plot_order,
            )
            remaining_seeds -= seeds_used
            actions.append(action)

        return {"farmer": actions[0], "hands": actions[1:], "market": market}

    return scaled_melon_agent
