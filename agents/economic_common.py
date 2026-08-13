"""Modular crop-economy engine for adaptive-agent ablation experiments."""

import math


CROPS = {
    "WHEAT": {
        "seed": 10, "first": 2, "peak": 4, "final": 4,
        "yield": 4, "ongoing": False,
    },
    "CARROT": {
        "seed": 20, "first": 2, "peak": 3, "final": 3,
        "yield": 3, "ongoing": False,
    },
    "TOMATO": {
        "seed": 50, "first": 8, "peak": 11, "final": 11,
        "yield": 4, "ongoing": True, "interval": 1,
    },
    "STRAWBERRY": {
        "seed": 100, "first": 10, "peak": 16, "final": 16,
        "yield": 4, "ongoing": True, "interval": 2,
    },
    "MELON": {
        "seed": 80, "first": 10, "peak": 10, "final": 10,
        "yield": 6, "ongoing": False,
    },
}
BASE_PRICES = {
    "WHEAT": 25,
    "CARROT": 35,
    "TOMATO": 60,
    "STRAWBERRY": 120,
    "MELON": 250,
    "EGG": 50,
    "MILK": 160,
    "WOOL": 200,
    "FERTILIZER": 100,
}
ANIMALS = {
    "GOOSE": {
        "cost": 300, "structure": "COOP", "first": 4, "interval": 1,
        "max_held": 4, "product": "EGG",
    },
    "COW": {
        "cost": 400, "structure": "PASTURE", "first": 8, "interval": 2,
        "max_held": 6, "product": "MILK",
    },
    "SHEEP": {
        "cost": 500, "structure": "PASTURE", "first": 6, "interval": 3,
        "max_held": 6, "product": "WOOL",
    },
}
MARKET_PARAMS = {
    "WHEAT": (400, "sqrt", 0.80, "log", 0.20),
    "CARROT": (450, "log", 0.20, "sqrt", 0.70),
    "TOMATO": (200, "linear", 0.40, "sqrt", 0.60),
    "STRAWBERRY": (100, "sqrt", 0.70, "linear", 1.60),
    "MELON": (300, "log", 0.20, "sq", 3.60),
    "EGG": (332, "linear", 0.40, "log", 0.20),
    "MILK": (122, "sqrt", 0.60, "linear", 1.60),
    "WOOL": (105, "log", 0.20, "sq", 3.20),
    "FERTILIZER": (200, "linear", 0.40, "linear", 0.40),
}
SHOP_PRODUCTS = {
    "BAKERY": ("EGG", "WHEAT"),
    "PIZZA_SHOP": ("MILK", "TOMATO", "WHEAT"),
    "BRUNCH_SPOT": ("EGG", "WHEAT", "STRAWBERRY"),
    "YARN_STORE": ("WOOL",),
    "ICE_CREAM_SHOP": ("STRAWBERRY", "MILK", "WHEAT"),
    "PET_CAFE": ("CARROT",),
    "SMOOTHIE_SHOP": ("STRAWBERRY", "MILK"),
    "FARMERS_MARKET": ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY"),
}

# NW preserves the route used by the frozen carrot and melon baselines. The
# other quadrants begin at their shed-access tile and snake outwards.
NW_ROUTE = (
    (4, 4), (3, 4), (2, 4), (2, 3), (3, 3),
    (4, 3), (4, 2), (3, 2), (2, 2), (1, 2),
    (1, 3), (1, 4), (0, 4), (0, 3), (0, 2),
    (0, 1), (1, 1), (2, 1), (3, 1), (4, 1),
    (4, 0), (3, 0), (2, 0), (1, 0), (0, 0),
)
NE_ROUTE = tuple(
    (x, y)
    for row, y in enumerate(range(4, -1, -1))
    for x in (range(5, 10) if row % 2 == 0 else range(9, 4, -1))
)
SW_ROUTE = tuple(
    (x, y)
    for row, y in enumerate(range(5, 10))
    for x in (range(4, -1, -1) if row % 2 == 0 else range(0, 5))
)
SE_ROUTE = tuple(
    (x, y)
    for row, y in enumerate(range(5, 10))
    for x in (range(5, 10) if row % 2 == 0 else range(9, 4, -1))
)
ALL_ROUTE = NW_ROUTE + NE_ROUTE + SW_ROUTE + SE_ROUTE
ROUTE_ORDER = {position: index for index, position in enumerate(ALL_ROUTE)}
SHED_TILES = ((4, 4), (5, 4), (4, 5), (5, 5))
LAND_COSTS = (1000, 2000, 4000)

DEFAULT_CONFIG = {
    "crop_mode": "adaptive",
    "fixed_crop": "MELON",
    "phase_schedule": ((0, "MELON"), (21, "WHEAT")),
    "hybrid_deviation": 1.30,
    "mixed_pattern": ("MELON", "WHEAT", "TOMATO", "STRAWBERRY", "CARROT"),
    "base_plots": 12,
    "plots_per_land": 12,
    "max_plots": 36,
    "fixed_hands": 2,
    "dynamic_labor": False,
    "plots_per_worker": 9,
    "max_hands": 6,
    "selling": "immediate",
    "sell_threshold": 0.92,
    "premium_sell_threshold": 0.90,
    "forecast_sell_ratio": 0.96,
    "hold_days": 3,
    "reserve_level": 55,
    "overflow_trigger": 82,
    "liquidation_step": 648,
    "adaptive_crops": True,
    "allocation_limits": {
        "MELON": 0.67,
        "STRAWBERRY": 0.34,
        "TOMATO": 0.34,
        "CARROT": 0.50,
        "WHEAT": 1.00,
    },
    "market_impact_weight": 1.0,
    "opponent_impact_weight": 1.0,
    "crop_bias": {},
    "phased_weights": False,
    "phase_biases": {
        "early": {"MELON": 1.20},
        "mid": {"MELON": 1.10, "STRAWBERRY": 1.10, "TOMATO": 1.10},
        "late": {"WHEAT": 1.25, "CARROT": 1.25},
    },
    "enable_land": False,
    "forced_land_days": (),
    "land_hurdle": 1.35,
    "land_reserve": 500,
    "land_last_day": 13,
    "animal_type": None,
    "animal_count": 0,
    "animal_start_day": 11,
    # The legacy defaults below preserve the frozen livestock proxy exactly.
    # New animal candidates opt into NW structures, explicit payback gates,
    # feed production, and product-aware selling through overrides.
    "animal_region": "NE",
    "structure_start_day": None,
    "animal_start_mode": "day",
    "animal_bank_threshold": 0,
    "animal_payback_hurdle": 0.0,
    "require_animal_payback": False,
    "animal_workers": 1,
    "animal_survival_priority": False,
    "feed_policy": "daily",
    "care_policy": "daily",
    "fertilizer_policy": "collect",
    "animal_harvest_threshold": 1,
    "wheat_policy": "market",
    "wheat_feed_plots": 0,
    "wheat_reserve_days": 2,
    "liquidate_feed_reserve": False,
    "animal_selling": "inherit",
    "animal_sell_threshold": 0.92,
    "animal_premium_sell_threshold": 0.90,
    "animal_hold_days": 3,
    "animal_opponent_impact_weight": 1.0,
    "animal_endgame_priority": False,
    "endgame_return_hour": 0,
}


def _shape(name, value):
    value = max(0.0, value)
    if name == "linear":
        return value
    if name == "sq":
        return value * value
    if name == "sqrt":
        return math.sqrt(value)
    if name == "log":
        return math.log(1.0 + value)
    return value


def _market_price(product, inventory):
    base = BASE_PRICES[product]
    throughput, below_func, below_target, above_func, above_target = MARKET_PARAMS[
        product
    ]
    delta = abs(inventory - 10000)
    if inventory < 10000:
        amplitude = below_target * base / _shape(below_func, throughput)
        value = base + amplitude * _shape(below_func, delta)
    else:
        amplitude = above_target * base / _shape(above_func, throughput)
        value = base - amplitude * _shape(above_func, delta)
    return max(1, int(math.floor(value + 0.5)))


def _is_plant(tile):
    return isinstance(tile, dict) and tile.get("kind") == "PLANT"


def _is_animal(tile):
    return isinstance(tile, dict) and tile.get("animal") is not None


def _move_toward(origin, target):
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


def _nearest(origin, positions):
    return min(
        positions,
        key=lambda position: (
            abs(position[0] - origin[0]) + abs(position[1] - origin[1]),
            ROUTE_ORDER.get(position, 999),
        ),
    )


def _fib(index):
    a, b = 1, 1
    for _ in range(index):
        a, b = b, a + b
    return a


def _daily_demand(obs, product):
    demand = 1.0  # Town center.
    for shop in obs.get("town", {}).get("unlocked_shops", []):
        products = SHOP_PRODUCTS.get(shop, ())
        if product in products:
            demand += 12.0 if len(products) == 1 else 6.0
    return demand


def _crop_yield_before(crop, days_available):
    data = CROPS[crop]
    if days_available < data["first"]:
        return 0, 0
    harvest_age = min(data["final"], days_available)
    if data["ongoing"]:
        units = 1 + (harvest_age - data["first"]) // data["interval"]
        return min(data["yield"], units), harvest_age
    window_start = (data["peak"] + 1) // 2
    bonus_days = max(0, harvest_age - window_start + 1)
    return min(data["yield"], 1 + bonus_days), harvest_age


def _visible_future_output(farm, crop, horizon, current_day):
    output = 0
    for row in farm["tiles"]:
        for tile in row:
            if not (_is_plant(tile) and tile.get("crop") == crop):
                continue
            data = CROPS[crop]
            age = current_day - tile["planted_day"]
            if data["ongoing"]:
                for production_age in range(data["first"], data["final"] + 1, data["interval"]):
                    if age < production_age <= age + horizon:
                        output += 1
            elif age <= data["peak"] <= age + horizon:
                output += data["yield"]
    return output


def _visible_animals(farm):
    counts = {animal: 0 for animal in ANIMALS}
    for row in farm["tiles"]:
        for tile in row:
            if _is_animal(tile) and tile.get("animal") in counts:
                counts[tile["animal"]] += 1
    return counts


def _animal_output_before(animal, start_day, final_day, care_policy, feed_policy):
    """Conservative output estimate for a newly placed animal.

    It models the first delayed payout and subsequent production ticks.  Care
    bonuses are capped by max-held, and survival feeding is credited only with
    base output because skipped feed cannot bank a care bonus reliably.
    """
    data = ANIMALS[animal]
    first_day = start_day + data["first"]
    if first_day > final_day:
        return 0
    output = 0
    production_day = first_day
    first = True
    while production_day <= final_day:
        if care_policy == "daily" and feed_policy == "daily":
            cared_days = data["first"] if first else data["interval"]
            units = min(data["max_held"], 1 + cared_days)
        elif care_policy == "preproduction" and feed_policy != "survival":
            units = 2
        else:
            units = 1
        output += units
        first = False
        production_day += data["interval"]
    return output


def _opponent_animal_output(obs, animal, horizon):
    data = ANIMALS[animal]
    output = 0
    for row in obs["farms"][1 - obs["player"]]["tiles"]:
        for tile in row:
            if not (_is_animal(tile) and tile.get("animal") == animal):
                continue
            placed = tile.get("placed_day", obs["day"])
            for future_day in range(obs["day"] + 1, obs["day"] + horizon + 1):
                since_first = future_day - placed - data["first"]
                if since_first >= 0 and since_first % data["interval"] == 0:
                    output += 1
    return output


def _animal_economics(obs, animal, count, config):
    day = obs["day"]
    remaining_days = max(0, 29 - day)
    output_each = _animal_output_before(
        animal,
        day,
        29,
        config.get("care_policy", "daily"),
        config.get("feed_policy", "daily"),
    )
    if output_each <= 0:
        return None
    data = ANIMALS[animal]
    product = data["product"]
    output = output_each * count
    opponent_output = _opponent_animal_output(obs, animal, remaining_days)
    # Price the production stream at its actual cadence instead of valuing the
    # whole season against one terminal-glut quote.  This is especially
    # important for milk and wool, whose nonlinear curves make early batches
    # much more valuable than the last batch.
    simulated_inventory = float(obs["market"]["inventory"][product])
    opponent_daily = (
        config.get("animal_opponent_impact_weight", 1.0)
        * opponent_output
        / max(1, remaining_days)
    )
    product_revenue = 0.0
    produced_units = 0
    for offset in range(1, remaining_days + 1):
        simulated_inventory -= _daily_demand(obs, product)
        simulated_inventory += opponent_daily
        since_first = offset - data["first"]
        if since_first < 0 or since_first % data["interval"] != 0:
            continue
        production_index = since_first // data["interval"]
        if config.get("care_policy") == "daily" and config.get("feed_policy") == "daily":
            cared = data["first"] if production_index == 0 else data["interval"]
            units_each = min(data["max_held"], 1 + cared)
        elif config.get("care_policy") == "preproduction" and config.get("feed_policy") != "survival":
            units_each = 2
        else:
            units_each = 1
        for _ in range(units_each * count):
            price = _market_price(product, simulated_inventory)
            product_revenue += price
            produced_units += 1
            if price > 1:
                simulated_inventory += 1
    expected_product_price = product_revenue / max(1, produced_units)
    fertilizer_units = count * max(0, remaining_days - 1)
    if config.get("fertilizer_policy", "collect") == "none":
        fertilizer_units = 0
    fertilizer_inventory = (
        obs["market"]["inventory"]["FERTILIZER"] + fertilizer_units
    )
    fertilizer_price = _market_price("FERTILIZER", fertilizer_inventory)
    if config.get("feed_policy", "daily") == "survival":
        feed_days = (remaining_days + 1) // 2
    else:
        feed_days = remaining_days
    feed_cost = feed_days * count * obs["market"]["prices"]["WHEAT"]
    # Self-grown feed still has opportunity cost.  Use the seed cost plus the
    # current value of the wheat consumed rather than pretending it is free.
    if config.get("wheat_policy") == "self":
        feed_cost *= 0.55
    elif config.get("wheat_policy") == "mixed":
        feed_cost *= 0.78
    revenue = product_revenue + fertilizer_units * fertilizer_price
    capital = count * data["cost"]
    profit = revenue - capital - feed_cost
    payback_days = None
    cumulative = -capital
    for offset in range(1, remaining_days + 1):
        cumulative -= count * obs["market"]["prices"]["WHEAT"] * (
            0.5 if config.get("feed_policy") == "survival" else 1.0
        )
        if offset >= 2 and config.get("fertilizer_policy", "collect") != "none":
            cumulative += count * fertilizer_price
        since_first = offset - data["first"]
        if since_first >= 0 and since_first % data["interval"] == 0:
            production_index = since_first // data["interval"]
            if config.get("care_policy") == "daily" and config.get("feed_policy") == "daily":
                cared = data["first"] if production_index == 0 else data["interval"]
                units = min(data["max_held"], 1 + cared)
            elif config.get("care_policy") == "preproduction" and config.get("feed_policy") != "survival":
                units = 2
            else:
                units = 1
            cumulative += count * units * expected_product_price
        if cumulative >= 0:
            payback_days = offset
            break
    return {
        "animal": animal,
        "product": product,
        "output": output,
        "expected_product_price": expected_product_price,
        "fertilizer_units": fertilizer_units,
        "fertilizer_price": fertilizer_price,
        "feed_cost": feed_cost,
        "capital": capital,
        "profit": profit,
        "payback_days": payback_days,
        "score": profit / max(1, data["first"]),
    }


def _selected_animal_type(obs, config):
    configured = config.get("animal_type")
    if configured != "ADAPTIVE":
        return configured
    me = obs["farms"][obs["player"]]
    private = obs["private"]
    owned = _visible_animals(me)
    for animal in ANIMALS:
        owned[animal] += private["shed"].get(animal, 0)
        owned[animal] += sum(inv.get(animal, 0) for inv in private["inventories"])
    if any(owned.values()):
        return max(owned, key=lambda animal: owned[animal])
    ranked = []
    for animal in ANIMALS:
        economics = _animal_economics(obs, animal, config.get("animal_count", 0), config)
        if economics is not None and economics["profit"] > 0:
            ranked.append((economics["score"], economics["profit"], animal))
    return max(ranked)[2] if ranked else None


def _phase_crop(day, schedule):
    crop = schedule[0][1]
    for start_day, candidate in schedule:
        if day >= start_day:
            crop = candidate
    return crop


def _candidate_economics(obs, crop, planned_count, config):
    day = obs["day"]
    # Harvest by day 28 so end-of-day drops can still be sold on day 29.
    units, harvest_age = _crop_yield_before(crop, 28 - day)
    if units <= 0:
        return None

    player = obs["player"]
    me = obs["farms"][player]
    opponent = obs["farms"][1 - player]
    current_inventory = obs["market"]["inventory"][crop]
    town_draw = _daily_demand(obs, crop) * harvest_age
    own_output = _visible_future_output(me, crop, harvest_age, day)
    opponent_output = _visible_future_output(opponent, crop, harvest_age, day)
    own_output += obs["private"]["shed"].get(crop, 0)
    projected_inventory = (
        current_inventory
        - town_draw
        + config["market_impact_weight"] * (own_output + planned_count * units)
        + config["opponent_impact_weight"] * opponent_output
        + units / 2.0
    )
    expected_price = _market_price(crop, projected_inventory)
    revenue = units * expected_price
    profit = revenue - CROPS[crop]["seed"]
    if profit <= 0:
        return None

    score = profit / max(1, harvest_age)
    # Early capital is scarce; favor return on seed cost without hard-coding a
    # crop. Mid-game scores are driven by expected profit and town draw.
    if day < 8:
        score *= 1.0 + min(0.25, profit / max(1, CROPS[crop]["seed"]) / 40.0)
    if config.get("phased_weights"):
        phase = "early" if day < 10 else ("mid" if day < 21 else "late")
        score *= config["phase_biases"].get(phase, {}).get(crop, 1.0)
    score *= config.get("crop_bias", {}).get(crop, 1.0)
    return {
        "score": score,
        "profit": profit,
        "price": expected_price,
        "units": units,
        "harvest_age": harvest_age,
    }


def _plan_crops(obs, crop_positions, config):
    tiles = obs["farms"][obs["player"]]["tiles"]
    counts = {crop: 0 for crop in CROPS}
    for x, y in crop_positions:
        tile = tiles[y][x]
        if _is_plant(tile) and tile.get("crop") in counts:
            counts[tile["crop"]] += 1

    choices = {}
    total_slots = len(crop_positions)
    planned = dict(counts)
    for position in crop_positions:
        x, y = position
        tile = tiles[y][x]
        if _is_plant(tile):
            continue
        mode = config["crop_mode"]
        if mode == "fixed":
            crop = config["fixed_crop"]
        elif mode == "phased":
            crop = _phase_crop(obs["day"], config["phase_schedule"])
        elif mode == "mixed":
            crop = config["mixed_pattern"][ROUTE_ORDER[position] % len(config["mixed_pattern"])]
        else:
            ranked = []
            for candidate in CROPS:
                limit = config["allocation_limits"].get(candidate, 1.0)
                if planned[candidate] >= max(1, math.ceil(total_slots * limit)):
                    continue
                economics = _candidate_economics(
                    obs, candidate, planned[candidate], config
                )
                if economics is not None:
                    ranked.append((economics["score"], economics["profit"], candidate))
            if mode == "hybrid":
                preferred = _phase_crop(obs["day"], config["phase_schedule"])
                preferred_economics = _candidate_economics(
                    obs, preferred, planned[preferred], config
                )
                if ranked and preferred_economics is not None:
                    best = max(ranked)
                    if (
                        preferred_economics["score"] * config["hybrid_deviation"]
                        >= best[0]
                    ):
                        crop = preferred
                    else:
                        crop = best[2]
                elif ranked:
                    crop = max(ranked)[2]
                elif preferred_economics is not None:
                    crop = preferred
                else:
                    continue
            elif not ranked:
                fallback = [
                    crop
                    for crop in CROPS
                    if _crop_yield_before(crop, 28 - obs["day"])[0] > 0
                ]
                if not fallback:
                    continue
                crop = min(fallback, key=lambda item: CROPS[item]["seed"])
            else:
                crop = max(ranked)[2]
        if _crop_yield_before(crop, 28 - obs["day"])[0] <= 0:
            continue
        choices[position] = crop
        planned[crop] += 1
    feed_plots = min(config.get("wheat_feed_plots", 0), len(crop_positions))
    if feed_plots > 0:
        feed_positions = set(crop_positions[-feed_plots:])
        for position in feed_positions:
            tile = tiles[position[1]][position[0]]
            if not _is_plant(tile):
                choices[position] = "WHEAT"
    return choices


def _target_positions(obs, config):
    me = obs["farms"][obs["player"]]
    extra_land = len(me["unlocked_quadrants"]) - 1
    desired = min(
        config["max_plots"],
        config["base_plots"]
        + config.get("wheat_feed_plots", 0)
        + extra_land * config["plots_per_land"],
    )
    available = [
        position
        for position in ALL_ROUTE
        if me["tiles"][position[1]][position[0]] != "LOCKED"
    ]
    animal_positions = set(_animal_positions(obs, config))
    return tuple(position for position in available if position not in animal_positions)[:desired]


def _animal_positions(obs, config):
    count = config.get("animal_count", 0)
    if not count:
        return ()
    me = obs["farms"][obs["player"]]
    if config.get("animal_region") == "NW":
        cash_crop_core = set(NW_ROUTE[: config.get("base_plots", 12)])
        route = tuple(
            sorted(
                (position for position in NW_ROUTE if position not in cash_crop_core),
                key=lambda position: (
                    abs(position[0] - 4) + abs(position[1] - 4),
                    ROUTE_ORDER[position],
                ),
            )
        )
    else:
        route = NE_ROUTE
    positions = [
        position
        for position in route
        if me["tiles"][position[1]][position[0]] != "LOCKED"
    ]
    return tuple(positions[:count])


def _expired(tile, day):
    if not _is_plant(tile):
        return False
    data = CROPS[tile["crop"]]
    return data["ongoing"] and day - tile["planted_day"] > data["final"]


def _crop_tasks(obs, crop_positions, choices):
    me = obs["farms"][obs["player"]]
    tasks = []
    for position in crop_positions:
        x, y = position
        tile = me["tiles"][y][x]
        if _is_plant(tile):
            crop = tile["crop"]
            data = CROPS[crop]
            age = obs["day"] - tile["planted_day"]
            if obs["day"] >= 29:
                # A final-day harvest is only useful while there is ample time
                # to walk back, DROP, observe the shed, and SELL before turn
                # 720. Watering has no terminal value.
                if (
                    obs["hour"] <= 10
                    and tile.get("yield_units", 0) > 0
                    and age >= data["first"]
                ):
                    tasks.append((0, position, ["HARVEST"], None))
                continue
            if not tile.get("watered_today", False):
                tasks.append((0, position, ["WATER"], None))
            elif tile.get("yield_units", 0) > 0 and (
                age >= data["peak"] or obs["day"] >= 28
            ):
                tasks.append((1, position, ["HARVEST"], None))
            elif _expired(tile, obs["day"]) and tile.get("yield_units", 0) <= 0:
                tasks.append((2, position, ["DIG"], None))
        elif isinstance(tile, dict) and tile.get("kind") == "WEED":
            tasks.append((2, position, ["DIG"], None))
        elif tile is None and position in choices and obs["hour"] < 23:
            crop = choices[position]
            tasks.append((3, position, ["PLANT", crop], crop))
    return tasks


def _animal_worker_action(obs, position, inventory, config, reserved=None):
    animal_type = _selected_animal_type(obs, config)
    animal_positions = _animal_positions(obs, config)
    structure_start = config.get("structure_start_day")
    if structure_start is None:
        structure_start = config["animal_start_day"]
    if not animal_type or not animal_positions or obs["day"] < structure_start:
        return None
    reserved = reserved if reserved is not None else set()
    me = obs["farms"][obs["player"]]
    tiles = me["tiles"]
    structure = ANIMALS[animal_type]["structure"]

    empty_structures = []
    unbuilt = []
    weeds = []
    animals = []
    for target in animal_positions:
        if target in reserved:
            continue
        tile = tiles[target[1]][target[0]]
        if tile is None:
            unbuilt.append(target)
        elif isinstance(tile, dict) and tile.get("kind") == "WEED":
            weeds.append(target)
        elif isinstance(tile, dict) and tile.get("kind") == structure and not tile.get("animal"):
            empty_structures.append(target)
        elif _is_animal(tile):
            animals.append((target, tile))

    purchasing_started = obs["day"] >= config["animal_start_day"]
    critical_unfed = [
        target
        for target, tile in animals
        if not tile.get("fed_today", False)
        and tile.get("consecutive_unfed", 0) >= 1
    ]
    if purchasing_started and config.get("animal_survival_priority", False) and critical_unfed:
        if inventory.get("WHEAT", 0) > 0:
            target = _nearest(position, critical_unfed)
            reserved.add(target)
            return ["FEED"] if position == target else _move_toward(position, target)
        if obs["private"]["shed"].get("WHEAT", 0) > 0:
            target = _nearest(position, SHED_TILES)
            amount = min(
                len(critical_unfed), obs["private"]["shed"].get("WHEAT", 0)
            )
            return ["PICKUP", "WHEAT", amount] if position in SHED_TILES else _move_toward(position, target)
    if purchasing_started and inventory.get(animal_type, 0) > 0 and empty_structures:
        target = _nearest(position, empty_structures)
        reserved.add(target)
        return ["PLACE", animal_type] if position == target else _move_toward(position, target)
    if purchasing_started and empty_structures and obs["private"]["shed"].get(animal_type, 0) > 0:
        target = _nearest(position, SHED_TILES)
        return ["PICKUP", animal_type, 1] if position in SHED_TILES else _move_toward(position, target)
    if weeds and config.get("animal_clear_weeds", False):
        target = _nearest(position, weeds)
        reserved.add(target)
        return ["DIG"] if position == target else _move_toward(position, target)
    if unbuilt:
        target = _nearest(position, unbuilt)
        reserved.add(target)
        return [f"BUILD_{structure}"] if position == target else _move_toward(position, target)

    if not purchasing_started:
        return None

    if config.get("animal_endgame_priority", False) and obs["day"] >= 29:
        ready = [target for target, tile in animals if tile.get("yield_units", 0) > 0]
        if ready:
            target = _nearest(position, ready)
            reserved.add(target)
            return ["HARVEST"] if position == target else _move_toward(position, target)
        fertilizer = [
            target
            for target, tile in animals
            if tile.get("fertilizer_available", False) and obs["hour"] <= 8
        ]
        if fertilizer:
            target = _nearest(position, fertilizer)
            reserved.add(target)
            return ["COLLECT_FERTILIZER"] if position == target else _move_toward(position, target)
        return None

    feed_policy = config.get("feed_policy", "daily")
    unfed = []
    for target, tile in animals:
        if tile.get("fed_today", False):
            continue
        data = ANIMALS[tile["animal"]]
        next_age = obs["day"] + 1 - tile.get("placed_day", obs["day"])
        production_due = (
            next_age >= data["first"]
            and (next_age - data["first"]) % data["interval"] == 0
        )
        should_feed = feed_policy == "daily"
        if feed_policy == "survival":
            should_feed = tile.get("consecutive_unfed", 0) >= 1
        elif feed_policy == "production":
            should_feed = production_due or tile.get("consecutive_unfed", 0) >= 1
        if should_feed:
            unfed.append(target)
    if unfed:
        if inventory.get("WHEAT", 0) > 0:
            target = _nearest(position, unfed)
            reserved.add(target)
            return ["FEED"] if position == target else _move_toward(position, target)
        if obs["private"]["shed"].get("WHEAT", 0) > 0:
            target = _nearest(position, SHED_TILES)
            amount = min(len(unfed), obs["private"]["shed"].get("WHEAT", 0))
            return ["PICKUP", "WHEAT", amount] if position in SHED_TILES else _move_toward(position, target)

    threshold = config.get("animal_harvest_threshold", 1)
    ready = [
        target
        for target, tile in animals
        if tile.get("yield_units", 0) >= threshold
        or (obs["day"] >= 28 and tile.get("yield_units", 0) > 0)
    ]
    if ready:
        target = _nearest(position, ready)
        reserved.add(target)
        return ["HARVEST"] if position == target else _move_toward(position, target)
    fertilizer = []
    if config.get("fertilizer_policy", "collect") != "none":
        fertilizer = [
            target for target, tile in animals if tile.get("fertilizer_available", False)
        ]
    if fertilizer:
        target = _nearest(position, fertilizer)
        reserved.add(target)
        return ["COLLECT_FERTILIZER"] if position == target else _move_toward(position, target)
    care_policy = config.get("care_policy", "daily")
    uncared = []
    for target, tile in animals:
        if tile.get("cared_today", False) or care_policy == "none":
            continue
        if care_policy == "preproduction":
            data = ANIMALS[tile["animal"]]
            next_age = obs["day"] + 1 - tile.get("placed_day", obs["day"])
            if next_age < data["first"] or (next_age - data["first"]) % data["interval"] != 0:
                continue
        uncared.append(target)
    if uncared:
        target = _nearest(position, uncared)
        reserved.add(target)
        return ["CARE"] if position == target else _move_toward(position, target)
    return None


def _assign_unit_actions(obs, crop_positions, choices, config):
    me = obs["farms"][obs["player"]]
    positions = [tuple(me["farmer"])] + [tuple(value) for value in me["hands"]]
    inventories = obs["private"]["inventories"]
    tasks = _crop_tasks(obs, crop_positions, choices)
    reserved = set()
    animal_reserved = set()
    seed_remaining = dict(obs["private"]["seeds"])
    actions = []
    for index, position in enumerate(positions):
        inventory = inventories[index] if index < len(inventories) else {}
        if obs["day"] >= 29 and obs["hour"] >= config.get("endgame_return_hour", 0) and any(
            inventory.get(product, 0) > 0 for product in BASE_PRICES
        ):
            target = _nearest(position, SHED_TILES)
            actions.append(["DROP"] if position in SHED_TILES else _move_toward(position, target))
            continue
        if index < config.get("animal_workers", 1):
            animal_action = _animal_worker_action(
                obs, position, inventory, config, animal_reserved
            )
            if animal_action is not None:
                actions.append(animal_action)
                continue
        available = []
        for priority, target, action, required_seed in tasks:
            if target in reserved:
                continue
            if required_seed and seed_remaining.get(required_seed, 0) <= 0:
                continue
            available.append((priority, target, action, required_seed))
        if not available:
            actions.append(["PASS"])
            continue
        priority, target, action, required_seed = min(
            available,
            key=lambda task: (
                task[0],
                abs(position[0] - task[1][0]) + abs(position[1] - task[1][1]),
                ROUTE_ORDER.get(task[1], 999),
            ),
        )
        reserved.add(target)
        if position == target:
            actions.append(action)
            if required_seed:
                seed_remaining[required_seed] -= 1
        else:
            actions.append(_move_toward(position, target))
    return actions


def _opponent_output_near(obs, product, days):
    if product not in CROPS:
        return 0
    return _visible_future_output(
        obs["farms"][1 - obs["player"]], product, days, obs["day"]
    )


def _opponent_animal_product_near(obs, product, days):
    if product == "FERTILIZER":
        return sum(_visible_animals(obs["farms"][1 - obs["player"]]).values()) * days
    for animal, data in ANIMALS.items():
        if data["product"] == product:
            return _opponent_animal_output(obs, animal, days)
    return 0


def _sell_orders(obs, config):
    shed = obs["private"]["shed"]
    occupied = sum(shed.values())
    orders = []
    products = sorted(
        (product for product in BASE_PRICES if shed.get(product, 0) > 0),
        key=lambda product: BASE_PRICES[product],
        reverse=True,
    )
    forced = obs.get("step", obs["day"] * 24 + obs["hour"]) >= config["liquidation_step"]
    overflow = occupied >= config["overflow_trigger"]
    overflow_to_sell = max(0, occupied - config["reserve_level"])
    for product in products:
        quantity = shed.get(product, 0)
        if (
            product == "WHEAT"
            and config.get("animal_count", 0)
            and not (
                obs["day"] >= 29
                and forced
                and config.get("liquidate_feed_reserve", False)
            )
        ):
            reserve = config["animal_count"] * config.get("wheat_reserve_days", 2)
            quantity = max(0, quantity - reserve)
        if quantity <= 0:
            continue
        animal_product = product in {"EGG", "MILK", "WOOL", "FERTILIZER"}
        selling_mode = config["selling"]
        if animal_product and config.get("animal_selling", "inherit") != "inherit":
            selling_mode = config["animal_selling"]
        if selling_mode == "immediate" or forced:
            orders.append(["SELL", product, quantity])
            continue
        price = obs["market"]["prices"][product]
        base = BASE_PRICES[product]
        if animal_product:
            threshold = (
                config.get("animal_premium_sell_threshold", 0.90)
                if base > 100
                else config.get("animal_sell_threshold", 0.92)
            )
            hold_days = min(config.get("animal_hold_days", 3), max(0, 27 - obs["day"]))
        else:
            threshold = (
                config["premium_sell_threshold"] if base > 100 else config["sell_threshold"]
            )
            hold_days = min(config["hold_days"], max(0, 27 - obs["day"]))
        opponent_output = _opponent_output_near(obs, product, hold_days)
        if animal_product and config.get("animal_selling", "inherit") != "inherit":
            opponent_output = _opponent_animal_product_near(obs, product, hold_days)
        future_inventory = (
            obs["market"]["inventory"][product]
            - _daily_demand(obs, product) * hold_days
            + config.get("animal_opponent_impact_weight", 1.0) * opponent_output
        )
        future_price = _market_price(product, future_inventory)
        should_sell = (
            price >= base * threshold
            or price >= future_price * config["forecast_sell_ratio"]
            or overflow
        )
        if should_sell:
            amount = min(quantity, overflow_to_sell) if overflow and price < base * threshold else quantity
            if amount > 0:
                orders.append(["SELL", product, amount])
                overflow_to_sell = max(0, overflow_to_sell - amount)
    return orders


def _best_new_land_profit(obs, config):
    best = 0.0
    for crop in CROPS:
        economics = _candidate_economics(obs, crop, 0, config)
        if economics is not None:
            best = max(best, economics["profit"])
    return best


def _should_buy_land(obs, config, budget):
    me = obs["farms"][obs["player"]]
    purchased = len(me["unlocked_quadrants"]) - 1
    if purchased >= len(LAND_COSTS):
        return False
    cost = LAND_COSTS[purchased]
    forced_days = config.get("forced_land_days", ())
    if purchased < len(forced_days):
        return obs["day"] >= forced_days[purchased] and budget >= cost
    if not config["enable_land"] or obs["day"] > config["land_last_day"]:
        return False
    if budget < cost + config["land_reserve"]:
        return False
    extra_slots = min(
        config["plots_per_land"], config["max_plots"] - len(_target_positions(obs, config))
    )
    if extra_slots <= 0:
        return False
    expected_gain = _best_new_land_profit(obs, config) * extra_slots
    seed_buffer = extra_slots * min(data["seed"] for data in CROPS.values())
    return expected_gain >= config["land_hurdle"] * (cost + seed_buffer)


def _desired_hands(obs, crop_positions, config):
    if not config["dynamic_labor"]:
        return config["fixed_hands"]
    active = len(crop_positions) + config.get("animal_count", 0) * 2
    workers = max(1, math.ceil(active / config["plots_per_worker"]))
    return min(config["max_hands"], workers - 1)


def _animal_transition_ready(obs, animal_type, config, budget):
    if not animal_type or obs["day"] < config.get("animal_start_day", 0):
        return False
    mode = config.get("animal_start_mode", "day")
    if mode in {"bank", "day_and_bank"} and budget < config.get("animal_bank_threshold", 0):
        return False
    hurdle = config.get("animal_payback_hurdle", 0.0)
    require_payback = config.get("require_animal_payback", False)
    if hurdle <= 0 and not require_payback:
        return True
    economics = _animal_economics(
        obs, animal_type, config.get("animal_count", 0), config
    )
    if economics is None or economics["payback_days"] is None:
        return False
    return economics["profit"] >= hurdle * economics["capital"]


def make_agent(overrides=None):
    """Create an economic agent from a small, serializable config override."""
    config = dict(DEFAULT_CONFIG)
    config["allocation_limits"] = dict(DEFAULT_CONFIG["allocation_limits"])
    config["crop_bias"] = dict(DEFAULT_CONFIG["crop_bias"])
    config["phase_biases"] = {
        phase: dict(values) for phase, values in DEFAULT_CONFIG["phase_biases"].items()
    }
    if overrides:
        for key, value in overrides.items():
            if key in {"allocation_limits", "crop_bias"}:
                config[key].update(value)
            elif key == "phase_biases":
                for phase, biases in value.items():
                    config[key].setdefault(phase, {}).update(biases)
            else:
                config[key] = value

    def economic_agent(obs):
        player = obs["player"]
        me = obs["farms"][player]
        private = obs["private"]
        crop_positions = _target_positions(obs, config)
        choices = _plan_crops(obs, crop_positions, config)

        market = _sell_orders(obs, config)
        budget = float(me["money"])
        for order in market:
            if order[0] == "SELL":
                budget += order[2] * obs["market"]["prices"][order[1]] * 0.75

        if _should_buy_land(obs, config, budget) and len(market) < 10:
            cost = LAND_COSTS[len(me["unlocked_quadrants"]) - 1]
            market.append(["BUY_LAND"])
            budget -= cost

        animal_type = _selected_animal_type(obs, config)
        if animal_type:
            animal_positions = _animal_positions(obs, config)
            placed = sum(
                1
                for position in animal_positions
                if _is_animal(me["tiles"][position[1]][position[0]])
            )
            carried = sum(inv.get(animal_type, 0) for inv in private["inventories"])
            owned = placed + private["shed"].get(animal_type, 0) + carried
            animal_cost = ANIMALS[animal_type]["cost"]
            transition_ready = _animal_transition_ready(
                obs, animal_type, config, budget
            )
            to_buy = 0
            if transition_ready:
                to_buy = min(
                    config["animal_count"] - owned, int(budget // animal_cost)
                )
            if to_buy > 0 and len(market) < 10:
                market.append(["BUY_ANIMAL", animal_type, to_buy])
                budget -= to_buy * animal_cost
            wheat_owned = private["shed"].get("WHEAT", 0) + sum(
                inv.get("WHEAT", 0) for inv in private["inventories"]
            )
            wheat_policy = config.get("wheat_policy", "market")
            active_target = min(config["animal_count"], owned + to_buy)
            if obs["day"] >= 29 and config.get("liquidate_feed_reserve", False):
                wheat_target = 0
            elif wheat_policy == "market":
                wheat_target = active_target * config.get("wheat_reserve_days", 2)
            elif wheat_policy == "mixed":
                wheat_target = max(placed, active_target)
            else:
                at_risk = sum(
                    1
                    for position in animal_positions
                    if _is_animal(me["tiles"][position[1]][position[0]])
                    and me["tiles"][position[1]][position[0]].get("consecutive_unfed", 0) >= 1
                    and not me["tiles"][position[1]][position[0]].get("fed_today", False)
                )
                wheat_target = at_risk
            wheat_needed = max(0, wheat_target - wheat_owned)
            wheat_price = obs["market"]["prices"]["WHEAT"]
            wheat_buy = min(wheat_needed, int(budget // max(1, wheat_price)))
            if wheat_buy > 0 and len(market) < 10:
                market.append(["BUY_PRODUCT", "WHEAT", wheat_buy])
                budget -= wheat_buy * wheat_price

        desired = {crop: 0 for crop in CROPS}
        planted = {crop: 0 for crop in CROPS}
        for position, crop in choices.items():
            desired[crop] += 1
        for position in crop_positions:
            tile = me["tiles"][position[1]][position[0]]
            if _is_plant(tile):
                planted[tile["crop"]] += 1
        for crop in CROPS:
            needed = max(0, desired[crop] - private["seeds"].get(crop, 0))
            affordable = int(budget // CROPS[crop]["seed"])
            to_buy = min(needed, affordable)
            if to_buy > 0 and len(market) < 10:
                market.append(["BUY_SEED", crop, to_buy])
                budget -= to_buy * CROPS[crop]["seed"]

        desired_hands = _desired_hands(obs, crop_positions, config)
        for hire_index in range(me.get("hires_today", 0), desired_hands):
            if len(market) >= 10:
                break
            cost = _fib(hire_index)
            if budget < cost:
                break
            market.append(["HIRE"])
            budget -= cost

        actions = _assign_unit_actions(obs, crop_positions, choices, config)
        return {"farmer": actions[0], "hands": actions[1:], "market": market}

    economic_agent.config = config
    return economic_agent
