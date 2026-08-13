"""A small, deterministic baseline agent for Kaggriculture.

The strategy intentionally uses only the starting quadrant and the main farmer.
It maintains four nearby carrot plots, which keeps the daily route short enough
for one unit to water every crop reliably.
"""

CARROT = "CARROT"
CARROT_SEED_COST = 20
CARROT_HARVEST_AGE = 3
TURNS_PER_DAY = 24

# A connected route near the NW shed-access tile at (4, 4).
PLOTS = ((4, 4), (3, 4), (2, 4), (2, 3))


def _is_plant(tile):
    return isinstance(tile, dict) and tile.get("kind") == "PLANT"


def _nearest(origin, candidates):
    """Choose a deterministic nearest coordinate, preserving PLOTS on ties."""
    plot_order = {position: index for index, position in enumerate(PLOTS)}
    return min(
        candidates,
        key=lambda position: (
            abs(position[0] - origin[0]) + abs(position[1] - origin[1]),
            plot_order[position],
        ),
    )


def _move_toward(origin, target):
    """Return one legal cardinal move from origin toward target."""
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


def _market_orders(me, private, tiles):
    """Sell harvested carrots and keep one seed allocated to each plot."""
    orders = []
    shed_carrots = private["shed"].get(CARROT, 0)
    if shed_carrots > 0:
        orders.append(["SELL", CARROT, shed_carrots])

    planted = sum(
        1
        for x, y in PLOTS
        if _is_plant(tiles[y][x]) and tiles[y][x].get("crop") == CARROT
    )
    seeds = private["seeds"].get(CARROT, 0)
    needed = max(0, len(PLOTS) - planted - seeds)

    # Use only money already in the bank. A sale earlier in this queue may make
    # more money available, but waiting until the next turn avoids speculative
    # or partially affordable orders.
    affordable = int(me["money"] // CARROT_SEED_COST)
    to_buy = min(needed, affordable)
    if to_buy > 0:
        orders.append(["BUY_SEED", CARROT, to_buy])
    return orders


def agent(obs):
    """Return one schema-valid Kaggriculture action for the current turn."""
    player = obs["player"]
    me = obs["farms"][player]
    private = obs["private"]
    tiles = me["tiles"]
    day = obs["day"]
    hour = obs["hour"]
    position = tuple(me["farmer"])

    market = _market_orders(me, private, tiles)
    unwatered = []
    harvestable = []
    weeds = []
    empty = []

    for x, y in PLOTS:
        tile = tiles[y][x]
        if _is_plant(tile) and tile.get("crop") == CARROT:
            if not tile.get("watered_today", False):
                unwatered.append((x, y))
            elif (
                day - tile["planted_day"] >= CARROT_HARVEST_AGE
                and tile.get("yield_units", 0) > 0
            ):
                harvestable.append((x, y))
        elif isinstance(tile, dict) and tile.get("kind") == "WEED":
            weeds.append((x, y))
        elif tile is None:
            empty.append((x, y))

    # Watering is always first: a freshly planted or established crop must not
    # be allowed to reach the second consecutive unwatered end-of-day refresh.
    if unwatered:
        target = _nearest(position, unwatered)
        farmer = ["WATER"] if position == target else _move_toward(position, target)
    elif harvestable:
        target = _nearest(position, harvestable)
        farmer = ["HARVEST"] if position == target else _move_toward(position, target)
    elif weeds:
        target = _nearest(position, weeds)
        farmer = ["DIG"] if position == target else _move_toward(position, target)
    elif empty and private["seeds"].get(CARROT, 0) > 0:
        target = _nearest(position, empty)
        if position != target:
            farmer = _move_toward(position, target)
        elif hour < TURNS_PER_DAY - 1:
            # PLANT now and WATER on the following turn. Planting on hour 23
            # would create a weed during that night's refresh.
            farmer = ["PLANT", CARROT]
        else:
            farmer = ["PASS"]
    else:
        farmer = ["PASS"]

    # This baseline never hires hands, so the list must be empty and remains in
    # exact correspondence with me["hands"].
    return {"farmer": farmer, "hands": [], "market": market}

