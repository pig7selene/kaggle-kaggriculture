"""Persistent-territory scheduler for large Kaggriculture farms.

The router is deliberately independent of economic planning.  A wrapped agent
still chooses every market order, crop allocation, animal target, land rule,
and selling decision.  This module replaces only farmer/hand actions.
"""

from __future__ import annotations

from copy import deepcopy
from runpy import run_path


SOURCE = run_path("agents/animal_land_common.py")
CROPS = SOURCE["CROPS"]
ANIMALS = SOURCE["ANIMALS"]
BASE_PRICES = SOURCE["BASE_PRICES"]
ROUTE_ORDER = SOURCE["ROUTE_ORDER"]
SHED_TILES = tuple(SOURCE["SHED_TILES"])
QUADRANT_ROUTES = {
    "NW": SOURCE["NW_ROUTE"],
    "NE": SOURCE["NE_ROUTE"],
    "SW": SOURCE["SW_ROUTE"],
    "SE": SOURCE["SE_ROUTE"],
}
MOVEMENT = {"NORTH", "SOUTH", "EAST", "WEST"}


def _is_plant(tile):
    return isinstance(tile, dict) and tile.get("kind") == "PLANT"


def _is_animal(tile):
    return isinstance(tile, dict) and tile.get("animal") is not None


def _quadrant(position):
    x, y = position
    return ("N" if y < 5 else "S") + ("W" if x < 5 else "E")


def _distance(left, right):
    return abs(left[0] - right[0]) + abs(left[1] - right[1])


def _nearest(origin, positions):
    return min(
        positions,
        key=lambda position: (_distance(origin, position), ROUTE_ORDER.get(position, 999)),
    )


def _move_toward(origin, target):
    x, y = origin
    tx, ty = target
    # Move along the longer axis first.  This avoids repeated horizontal sweeps
    # when workers travel from the shed into north/south territory.
    dx, dy = tx - x, ty - y
    if abs(dy) > abs(dx):
        return ["SOUTH" if dy > 0 else "NORTH"]
    if dx:
        return ["EAST" if dx > 0 else "WEST"]
    if dy:
        return ["SOUTH" if dy > 0 else "NORTH"]
    return ["PASS"]


def _active_config(base_agent, obs):
    selector = getattr(base_agent, "active_config", None)
    if callable(selector):
        return deepcopy(selector(obs))
    components = getattr(base_agent, "component_agents", None)
    schedule = getattr(base_agent, "animal_schedule", None)
    if components and schedule:
        target = schedule[0][1]
        for day, count in schedule:
            if obs["day"] >= day:
                target = count
        return deepcopy(components[target].config)
    return deepcopy(base_agent.config)


def _animal_specialists(unit_count, target_count):
    # Top replays consistently concentrate animal work in workers spawned on
    # the north side of the shed: 0/1 and then 4/5.  Continue the pattern if a
    # future policy requests more specialists.
    preferred = []
    block = 0
    while len(preferred) < max(target_count, unit_count):
        preferred.extend((4 * block, 4 * block + 1))
        block += 1
    selected = [index for index in preferred if index < unit_count][:target_count]
    if len(selected) < min(target_count, unit_count):
        selected.extend(
            index for index in range(unit_count)
            if index not in selected
        )
    return tuple(selected[: min(target_count, unit_count)])


def _preferred_crop_zone(unit_index, unlocked, policy="persistent"):
    if len(unlocked) == 1:
        return "NW"
    if policy == "replay_balanced" and len(unlocked) == 3:
        # With NW/NE/SW open, four animal specialists already fall back to the
        # small NW crop remainder.  Send the late day-10 hires to the two full
        # 25-tile quadrants instead of adding two more NW crop workers.
        replay_zones = {
            2: "SW", 3: "NE", 6: "SW", 7: "NE", 8: "NW",
            9: "NE", 10: "SW", 11: "NE", 12: "SW", 13: "NE", 14: "SW",
        }
        preferred = replay_zones.get(unit_index)
        if preferred in unlocked:
            return preferred

    residue = unit_index % 4
    preferred = {0: "NW", 1: "NE", 2: "SW", 3: "SE"}[residue]
    if preferred in unlocked:
        return preferred
    if preferred == "SW":
        return "NW" if "NW" in unlocked else sorted(unlocked)[0]
    if preferred == "SE":
        # The first two southeast-spawn workers in the public policy serve NE;
        # the third helps NW once the NE cohort is staffed.
        occurrence = max(0, (unit_index - 3) // 4)
        fallback = "NE" if occurrence < 2 else "NW"
        if fallback in unlocked:
            return fallback
    return min(
        unlocked,
        key=lambda quadrant: min(
            _distance(SHED_TILES[0], position) for position in QUADRANT_ROUTES[quadrant]
        ),
    )


def _partition(values, index, count):
    if not values or count <= 0:
        return ()
    start = len(values) * index // count
    end = len(values) * (index + 1) // count
    return tuple(values[start:end])


def _animal_targets(obs, config):
    mixed = config.get("mixed_animal_positions")
    if mixed:
        targets = []
        for raw_position, animal in mixed.items():
            position = tuple(raw_position) if not isinstance(raw_position, str) else tuple(map(int, raw_position.split(",")))
            targets.append((position, animal))
        return tuple(sorted(targets, key=lambda row: ROUTE_ORDER.get(row[0], 999)))
    animal_type = SOURCE["_selected_animal_type"](obs, config)
    return tuple((position, animal_type) for position in SOURCE["_animal_positions"](obs, config))


def _structure_for(animal):
    return ANIMALS[animal]["structure"]


def _crop_tasks(obs, crop_positions, choices, config=None):
    config = config or {}
    me = obs["farms"][obs["player"]]
    tasks = []
    bonus_start = {"WHEAT": 2, "CARROT": 2, "MELON": 6}
    for position in crop_positions:
        tile = me["tiles"][position[1]][position[0]]
        if _is_plant(tile):
            crop = tile["crop"]
            data = CROPS[crop]
            age = obs["day"] - tile["planted_day"]
            if obs["day"] >= 29:
                if obs["hour"] <= 10 and tile.get("yield_units", 0) > 0 and age >= data["first"]:
                    tasks.append((0, position, ["HARVEST"], None))
                continue
            if not tile.get("watered_today", False) and tile.get("consecutive_unwatered", 0) >= 1:
                tasks.append((0, position, ["WATER"], None))
            harvest_due = tile.get("yield_units", 0) > 0 and (
                age >= data["peak"]
                or obs["day"] >= 28
                or (
                    config.get("harvest_policy") == "ready_ongoing"
                    and data["ongoing"]
                    and age >= data["first"]
                )
            )
            if harvest_due:
                tasks.append((config.get("harvest_priority", 1), position, ["HARVEST"], None))
            elif (
                config.get("crop_fertilizer", False)
                and crop == "STRAWBERRY"
                and age >= data["first"]
                and (age - data["first"]) % data["interval"] == 0
                and tile.get("fertilized_until_day", -1) < obs["day"]
            ):
                # Fertilize only a mature strawberry cohort on a production
                # day.  The following observation exposes WATER for the same
                # tile, so both bonuses can be secured before end-of-day.
                tasks.append((1.5, position, ["FERTILIZE"], None))
            elif not tile.get("watered_today", False):
                if config.get("water_policy") == "deadline":
                    bonus_water = (
                        not data["ongoing"]
                        and crop in bonus_start
                        and bonus_start[crop] <= age <= data["peak"]
                    )
                    if not bonus_water:
                        # Safe plants may intentionally skip one refresh. The
                        # critical branch above guarantees the next day is a
                        # hard deadline, matching the top replay behavior.
                        continue
                    tasks.append((1.25, position, ["WATER"], None))
                    continue
                late_guard = config.get("late_water_priority_hour")
                priority = (
                    0.5
                    if late_guard is not None and obs["hour"] >= int(late_guard)
                    else 2
                )
                tasks.append((priority, position, ["WATER"], None))
            elif data["ongoing"] and age > data["final"] and tile.get("yield_units", 0) <= 0:
                tasks.append((3, position, ["DIG"], None))
        elif isinstance(tile, dict) and tile.get("kind") == "WEED":
            tasks.append((3, position, ["DIG"], None))
        elif tile is None and position in choices and obs["hour"] < 23:
            crop = choices[position]
            tasks.append((config.get("plant_priority", 4), position, ["PLANT", crop], crop))
    if config.get("plant_admission", False):
        plant_tasks = [task for task in tasks if task[2][0] == "PLANT"]
        nonplant = [task for task in tasks if task[2][0] != "PLANT"]
        crop_workers = max(
            1,
            1 + len(me.get("hands", [])) - int(config.get("animal_workers", 0)),
        )
        last_hour = int(config.get("plant_admission_last_hour", 20))
        if obs["hour"] > last_hour:
            plant_limit = 0
        else:
            remaining = max(0, last_hour - obs["hour"] + 1)
            urgent = sum(task[0] <= 1 for task in nonplant)
            # A new crop needs travel/plant plus a guaranteed same-day water.
            plant_limit = max(0, (crop_workers * remaining - urgent) // 3)
        tasks = nonplant + sorted(
            plant_tasks, key=lambda task: ROUTE_ORDER.get(task[1], 999)
        )[:plant_limit]
    return tasks


def _inventory_products(inventory):
    return sum(inventory.get(product, 0) for product in BASE_PRICES)


def _animal_action(obs, unit_index, position, inventory, assigned, config, reserved, resources):
    if not assigned:
        return None
    me = obs["farms"][obs["player"]]
    private = obs["private"]
    structure_start = config.get("structure_start_day")
    if structure_start is None:
        structure_start = config.get("animal_start_day", 0)
    if obs["day"] < structure_start:
        return None

    # Daily hand counts change, so a carried animal can be reassigned to a
    # different territory overnight.  Let any specialist finish that placement
    # in the nearest compatible empty structure instead of stranding capital.
    global_empty = []
    for target, desired_animal in _animal_targets(obs, config):
        if target in reserved or inventory.get(desired_animal, 0) <= 0:
            continue
        tile = me["tiles"][target[1]][target[0]]
        if (
            isinstance(tile, dict)
            and tile.get("kind") == _structure_for(desired_animal)
            and not tile.get("animal")
        ):
            global_empty.append((target, desired_animal))
    if global_empty:
        target, animal = min(
            global_empty,
            key=lambda row: (_distance(position, row[0]), ROUTE_ORDER[row[0]]),
        )
        reserved.add(target)
        return ["PLACE", animal] if position == target else _move_toward(position, target)

    unbuilt = []
    weeds = []
    empty = []
    animals = []
    for target, desired_animal in assigned:
        if target in reserved:
            continue
        tile = me["tiles"][target[1]][target[0]]
        if tile is None:
            unbuilt.append((target, desired_animal))
        elif isinstance(tile, dict) and tile.get("kind") == "WEED":
            weeds.append((target, desired_animal))
        elif isinstance(tile, dict) and tile.get("kind") == _structure_for(desired_animal) and not tile.get("animal"):
            empty.append((target, desired_animal))
        elif _is_animal(tile):
            animals.append((target, tile))

    # Place carried animals before building more empty structures.
    carried_targets = [row for row in empty if inventory.get(row[1], 0) > 0]
    if carried_targets:
        target, animal = min(carried_targets, key=lambda row: (_distance(position, row[0]), ROUTE_ORDER[row[0]]))
        reserved.add(target)
        return ["PLACE", animal] if position == target else _move_toward(position, target)
    shed_animals = [row for row in empty if private["shed"].get(row[1], 0) - resources["animal_claims"][row[1]] > 0]
    if shed_animals:
        target, animal = min(shed_animals, key=lambda row: (_distance(position, row[0]), ROUTE_ORDER[row[0]]))
        if position in SHED_TILES:
            resources["animal_claims"][animal] += 1
            return ["PICKUP", animal, 1]
        return _move_toward(position, _nearest(position, SHED_TILES))
    if weeds and config.get("animal_clear_weeds", False):
        target, _ = min(weeds, key=lambda row: (_distance(position, row[0]), ROUTE_ORDER[row[0]]))
        reserved.add(target)
        return ["DIG"] if position == target else _move_toward(position, target)
    if unbuilt:
        target, animal = min(unbuilt, key=lambda row: (_distance(position, row[0]), ROUTE_ORDER[row[0]]))
        reserved.add(target)
        structure = _structure_for(animal)
        return [f"BUILD_{structure}"] if position == target else _move_toward(position, target)

    if obs["day"] >= 29:
        ready = [target for target, tile in animals if tile.get("yield_units", 0) > 0]
        if ready and obs["hour"] <= 15:
            target = _nearest(position, ready)
            reserved.add(target)
            return ["HARVEST"] if position == target else _move_toward(position, target)
        if _inventory_products(inventory):
            target = _nearest(position, SHED_TILES)
            return ["DROP"] if position in SHED_TILES else _move_toward(position, target)
        return None

    # Finish all useful work on the current animal before beginning another
    # sweep.  This is the largest routing difference from the old scheduler:
    # FEED -> HARVEST -> CARE -> COLLECT can take four stationary turns instead
    # of four separate circuits over the same pasture row.
    current_tile = me["tiles"][position[1]][position[0]]
    assigned_positions = {target for target, _ in assigned}
    if position in assigned_positions and _is_animal(current_tile):
        if not current_tile.get("fed_today", False):
            if inventory.get("WHEAT", 0) > 0:
                reserved.add(position)
                return ["FEED"]
            available = private["shed"].get("WHEAT", 0) - resources["wheat_claimed"]
            if available > 0:
                return _move_toward(position, _nearest(position, SHED_TILES))
        if current_tile.get("yield_units", 0) > 0:
            reserved.add(position)
            return ["HARVEST"]
        if not current_tile.get("cared_today", False):
            reserved.add(position)
            return ["CARE"]
        if current_tile.get("fertilizer_available", False):
            reserved.add(position)
            return ["COLLECT_FERTILIZER"]

    critical = [
        target for target, tile in animals
        if not tile.get("fed_today", False) and tile.get("consecutive_unfed", 0) >= 1
    ]
    regular = [target for target, tile in animals if not tile.get("fed_today", False)]
    feed_targets = critical or regular
    if feed_targets:
        if inventory.get("WHEAT", 0) > 0:
            target = _nearest(position, feed_targets)
            reserved.add(target)
            return ["FEED"] if position == target else _move_toward(position, target)
        available = private["shed"].get("WHEAT", 0) - resources["wheat_claimed"]
        if available > 0:
            amount = min(len(feed_targets), available)
            if position in SHED_TILES:
                resources["wheat_claimed"] += amount
                return ["PICKUP", "WHEAT", amount]
            return _move_toward(position, _nearest(position, SHED_TILES))

    ready = [target for target, tile in animals if tile.get("yield_units", 0) > 0]
    if ready:
        target = _nearest(position, ready)
        reserved.add(target)
        return ["HARVEST"] if position == target else _move_toward(position, target)
    uncared = [target for target, tile in animals if not tile.get("cared_today", False)]
    if uncared:
        target = _nearest(position, uncared)
        reserved.add(target)
        return ["CARE"] if position == target else _move_toward(position, target)
    fertilizer = [target for target, tile in animals if tile.get("fertilizer_available", False)]
    if fertilizer:
        target = _nearest(position, fertilizer)
        reserved.add(target)
        return ["COLLECT_FERTILIZER"] if position == target else _move_toward(position, target)

    # Hands automatically return inventory at day end; only the persistent main
    # farmer or an overloaded worker pays explicit shed travel during the day.
    carried = _inventory_products(inventory)
    if carried and (unit_index == 0 and (carried >= 8 or obs["hour"] >= 18)):
        target = _nearest(position, SHED_TILES)
        return ["DROP"] if position in SHED_TILES else _move_toward(position, target)
    return None


def _assign_actions(obs, crop_positions, choices, config):
    me = obs["farms"][obs["player"]]
    positions = [tuple(me["farmer"])] + [tuple(value) for value in me["hands"]]
    inventories = obs["private"]["inventories"]
    unit_count = len(positions)
    animal_targets = _animal_targets(obs, config)
    target_specialists = min(config.get("animal_workers", 0), max(0, len(animal_targets)))
    specialists = set(_animal_specialists(unit_count, target_specialists))

    assigned_animals = {}
    specialist_list = sorted(specialists)
    for rank, unit_index in enumerate(specialist_list):
        assigned_animals[unit_index] = _partition(animal_targets, rank, len(specialist_list))

    unlocked = set(me.get("unlocked_quadrants", []))
    zone_positions = {
        quadrant: tuple(position for position in crop_positions if _quadrant(position) == quadrant)
        for quadrant in unlocked
    }
    crop_workers = [index for index in range(unit_count) if index not in specialists]
    zone_workers = {quadrant: [] for quadrant in unlocked}
    territory_policy = config.get("territory_policy", "persistent")
    workload = {quadrant: 0.25 * len(zone_positions.get(quadrant, ())) for quadrant in unlocked}
    if territory_policy == "workload":
        provisional_tasks = _crop_tasks(obs, crop_positions, choices, config)
        weights = {"WATER": 3.0, "HARVEST": 3.0, "DIG": 2.0, "PLANT": 2.0, "FERTILIZE": 2.0}
        for task in provisional_tasks:
            workload[_quadrant(task[1])] = workload.get(_quadrant(task[1]), 0) + weights.get(task[2][0], 1.0)
    for unit_index in crop_workers:
        if territory_policy == "workload":
            available = [q for q in unlocked if zone_positions.get(q)]
            zone = max(
                available,
                key=lambda q: (
                    workload.get(q, 0) / (len(zone_workers[q]) + 1),
                    -min(ROUTE_ORDER.get(position, 999) for position in zone_positions[q]),
                ),
            ) if available else "NW"
        else:
            zone = _preferred_crop_zone(unit_index, unlocked, territory_policy)
        if zone not in zone_positions or not zone_positions[zone]:
            available = [q for q, values in zone_positions.items() if values]
            zone = min(available, key=lambda q: len(zone_workers[q]) / max(1, len(zone_positions[q]))) if available else "NW"
        zone_workers.setdefault(zone, []).append(unit_index)

    worker_crop_positions = {}
    for zone, workers in zone_workers.items():
        ordered = sorted(zone_positions.get(zone, ()), key=lambda value: ROUTE_ORDER.get(value, 999))
        for rank, unit_index in enumerate(workers):
            worker_crop_positions[unit_index] = _partition(ordered, rank, len(workers))

    tasks = _crop_tasks(obs, crop_positions, choices, config)
    tasks_by_position = {}
    for task in tasks:
        current = tasks_by_position.get(task[1])
        if current is None or task[0] < current[0]:
            tasks_by_position[task[1]] = task

    crop_reserved = set()
    animal_reserved = set()
    seed_remaining = dict(obs["private"]["seeds"])
    resources = {
        "wheat_claimed": 0,
        "fertilizer_claimed": 0,
        "animal_claims": {animal: 0 for animal in ANIMALS},
    }
    unfed_count = sum(
        1
        for target, _ in animal_targets
        for tile in (me["tiles"][target[1]][target[0]],)
        if _is_animal(tile) and not tile.get("fed_today", False)
    )
    accessible_feed = obs["private"]["shed"].get("WHEAT", 0) + sum(
        inventories[index].get("WHEAT", 0)
        for index in specialists if index < len(inventories)
    )
    resources["feed_transfer_gap"] = max(0, unfed_count - accessible_feed)
    actions = []
    for unit_index, position in enumerate(positions):
        inventory = inventories[unit_index] if unit_index < len(inventories) else {}
        if obs["day"] >= 29 and obs["hour"] >= config.get("endgame_return_hour", 0) and _inventory_products(inventory):
            target = _nearest(position, SHED_TILES)
            actions.append(["DROP"] if position in SHED_TILES else _move_toward(position, target))
            continue

        if unit_index in specialists:
            animal_action = _animal_action(
                obs, unit_index, position, inventory,
                assigned_animals.get(unit_index, ()), config,
                animal_reserved, resources,
            )
            if animal_action is not None:
                actions.append(animal_action)
                continue

        if config.get("crop_fertilizer", False) and unit_index not in specialists:
            fertilizer_tasks = [
                task for task in tasks_by_position.values()
                if task[2][0] == "FERTILIZE" and task[1] not in crop_reserved
            ]
            available_fertilizer = (
                obs["private"]["shed"].get("FERTILIZER", 0)
                - resources["fertilizer_claimed"]
            )
            if (
                fertilizer_tasks
                and inventory.get("FERTILIZER", 0) <= 0
                and available_fertilizer > 0
                and position in SHED_TILES
            ):
                amount = min(4, available_fertilizer, len(fertilizer_tasks))
                resources["fertilizer_claimed"] += amount
                actions.append(["PICKUP", "FERTILIZER", amount])
                continue

        # Market feed accounting sees wheat in every unit inventory, but an
        # animal specialist cannot use wheat carried by a remote crop worker.
        # Return only the amount needed to close that accessibility gap.
        carried_wheat = inventory.get("WHEAT", 0)
        if (
            unit_index not in specialists
            and carried_wheat > 0
            and resources["feed_transfer_gap"] > 0
            and obs["day"] < 29
        ):
            target = _nearest(position, SHED_TILES)
            if position in SHED_TILES:
                resources["feed_transfer_gap"] = max(
                    0, resources["feed_transfer_gap"] - carried_wheat
                )
                actions.append(["DROP"])
            else:
                actions.append(_move_toward(position, target))
            continue

        if (
            config.get("chain_replant", False)
            and unit_index not in specialists
            and position in choices
            and me["tiles"][position[1]][position[0]] is None
            and position not in crop_reserved
            and obs["hour"] <= int(config.get("chain_last_hour", 21))
        ):
            crop = choices[position]
            if seed_remaining.get(crop, 0) > 0:
                crop_reserved.add(position)
                seed_remaining[crop] -= 1
                actions.append(["PLANT", crop])
                continue

        available = []
        if config.get("deadline_rescue", False) and unit_index not in specialists:
            # Persistent zones are normally valuable for movement efficiency,
            # but an already-missed crop is one refresh away from loss. Permit
            # crop workers to cross a zone boundary only for that hard
            # deadline; all safe work remains territory-local.
            for task in tasks_by_position.values():
                if task[0] != 0 or task[2][0] != "WATER" or task[1] in crop_reserved:
                    continue
                available.append(task)

        territory = worker_crop_positions.get(unit_index, ())
        zone = _quadrant(territory[0]) if territory else _quadrant(position)
        if not available:
            for target in territory:
                task = tasks_by_position.get(target)
                if task is None or target in crop_reserved:
                    continue
                if task[2][0] == "FERTILIZE" and inventory.get("FERTILIZER", 0) <= 0:
                    continue
                if task[3] and seed_remaining.get(task[3], 0) <= 0:
                    continue
                available.append(task)
        if not available:
            # Help within the same quadrant before crossing a boundary.
            for task in tasks_by_position.values():
                if task[1] in crop_reserved or _quadrant(task[1]) != zone:
                    continue
                if task[2][0] == "FERTILIZE" and inventory.get("FERTILIZER", 0) <= 0:
                    continue
                if task[3] and seed_remaining.get(task[3], 0) <= 0:
                    continue
                available.append(task)
        if not available and unit_index in specialists:
            # Animal specialists may maintain NW crops after completing their
            # local animal queue, but never roam to a remote crop quadrant.
            animal_zone = _quadrant(assigned_animals[unit_index][0][0]) if assigned_animals.get(unit_index) else zone
            for task in tasks_by_position.values():
                if task[1] in crop_reserved or _quadrant(task[1]) != animal_zone:
                    continue
                if task[2][0] == "FERTILIZE" and inventory.get("FERTILIZER", 0) <= 0:
                    continue
                if task[3] and seed_remaining.get(task[3], 0) <= 0:
                    continue
                available.append(task)
        if not available:
            actions.append(["PASS"])
            continue
        def task_key(task):
            priority, target, task_action, _ = task
            if not config.get("cohort_priority", False):
                return (priority, _distance(position, target), ROUTE_ORDER.get(target, 999))
            tile = me["tiles"][target[1]][target[0]]
            age = (
                obs["day"] - tile.get("planted_day", obs["day"])
                if _is_plant(tile) else -1
            )
            held = tile.get("yield_units", 0) if _is_plant(tile) else 0
            deadline = tile.get("consecutive_unwatered", 0) if _is_plant(tile) else 0
            # Within an existing task priority, complete the oldest/highest-
            # yield cohort before optimizing a short movement hop.
            return (
                priority,
                -deadline,
                -held if task_action[0] == "HARVEST" else 0,
                -age,
                _distance(position, target),
                ROUTE_ORDER.get(target, 999),
            )

        priority, target, action, required_seed = min(available, key=task_key)
        crop_reserved.add(target)
        if position == target:
            actions.append(action)
            if required_seed:
                seed_remaining[required_seed] -= 1
        else:
            actions.append(_move_toward(position, target))
    return actions


def make_routed_agent(base_agent):
    """Wrap an economic agent, replacing only its unit scheduler."""

    def routed_agent(obs):
        economic_action = base_agent(obs)
        config = _active_config(base_agent, obs)
        crop_positions = SOURCE["_target_positions"](obs, config)
        if config.get("mixed_animal_positions"):
            mixed_positions = {
                tuple(position) if not isinstance(position, str) else tuple(map(int, position.split(",")))
                for position in config["mixed_animal_positions"]
            }
            crop_positions = tuple(
                position for position in crop_positions if position not in mixed_positions
            )
        choices = SOURCE["_plan_crops"](obs, crop_positions, config)
        actions = _assign_actions(obs, crop_positions, choices, config)
        return {
            "farmer": actions[0],
            "hands": actions[1:],
            "market": economic_action["market"],
        }

    routed_agent.config = getattr(base_agent, "config", {})
    routed_agent.base_agent = base_agent
    return routed_agent
