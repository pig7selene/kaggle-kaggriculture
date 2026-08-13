"""Measure worker routing and maintenance efficiency in public/local replays."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import Counter, defaultdict, deque
from copy import deepcopy
from pathlib import Path

from kaggle_environments.envs.kaggriculture import kaggriculture as game

from analyze_top_player_replays import _transition_ledger


ROOT = Path(__file__).resolve().parent
CORPUS = ROOT / "experiments" / "top_player_replays"
DEFAULT_OUTPUT = ROOT / "experiments" / "top_player_worker_routing.json"
DEFAULT_REPORT = ROOT / "experiments" / "top_player_worker_routing.md"

MOVEMENT = {"NORTH", "SOUTH", "EAST", "WEST"}
PRODUCTIVE = {
    "PLANT", "WATER", "HARVEST", "FERTILIZE", "DIG",
    "BUILD_COOP", "BUILD_PASTURE", "PLACE", "FEED", "CARE",
    "COLLECT_FERTILIZER",
}
LOGISTICS = {"PICKUP", "DROP"}
VALUABLE = {
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
    "EGG", "MILK", "WOOL", "FERTILIZER",
}
ANIMAL_PRODUCTS = {"MILK", "WOOL", "EGG", "FERTILIZER"}
SHED_TILES = {(4, 4), (5, 4), (4, 5), (5, 5)}


def _quadrant(position):
    x, y = position
    return ("N" if y < 5 else "S") + ("W" if x < 5 else "E")


def _shed_distance(position):
    return min(abs(position[0] - x) + abs(position[1] - y) for x, y in SHED_TILES)


def _op(action):
    return action[0] if isinstance(action, list) and action else "PASS"


def _is_animal(tile):
    return isinstance(tile, dict) and tile.get("animal") is not None


def _is_plant(tile):
    return isinstance(tile, dict) and tile.get("kind") == "PLANT"


def _inventory_total(inventory):
    return sum(inventory.get(item, 0) for item in VALUABLE)


def _effect_category(op, before_tile, before_inventory, after_tile, after_inventory, before_pos, after_pos):
    moved = before_pos != after_pos
    if op in MOVEMENT:
        return "movement" if moved else "invalid"
    if op == "PASS":
        return "pass"
    inventory_changed = before_inventory != after_inventory
    tile_changed = before_tile != after_tile
    if op in LOGISTICS:
        return "logistics" if inventory_changed else "invalid"
    if op == "PLACE" and not tile_changed:
        return "logistics" if inventory_changed else "invalid"
    if op in PRODUCTIVE:
        return "productive" if tile_changed or inventory_changed else "invalid"
    return "invalid"


def _responsibility(op, before_tile, after_tile):
    if op in {"FEED", "CARE", "COLLECT_FERTILIZER", "BUILD_COOP", "BUILD_PASTURE"}:
        return "animal"
    if op == "PLACE" and (
        _is_animal(after_tile)
        or (isinstance(after_tile, dict) and after_tile.get("kind") in {"COOP", "PASTURE"})
    ):
        return "animal"
    if op == "HARVEST" and _is_animal(before_tile):
        return "animal"
    if op in {"PLANT", "WATER", "FERTILIZE", "DIG"}:
        return "crop"
    if op == "HARVEST" and _is_plant(before_tile):
        return "crop"
    return "other"


def _blank_metrics():
    return Counter({
        "total_actions": 0,
        "productive_actions": 0,
        "movement_actions": 0,
        "pass_actions": 0,
        "logistics_actions": 0,
        "invalid_actions": 0,
        "duplicate_conflicts": 0,
        "shed_directed_moves": 0,
        "shed_entries": 0,
        "plant_day_checks": 0,
        "missed_watering": 0,
        "critical_missed_watering": 0,
        "delayed_crop_harvests": 0,
        "animal_day_checks": 0,
        "animals_unfed": 0,
        "animals_uncared": 0,
        "animal_product_unharvested": 0,
        "fertilizer_left": 0,
        "productive_tiles_sum": 0,
        "unlocked_tiles_sum": 0,
        "empty_tiles_with_capital": 0,
        "daily_checks": 0,
    })


def _worker_record(day, unit_index, position):
    return {
        "day": day,
        "unit_index": unit_index,
        "spawn_position": list(position),
        "actions": Counter(),
        "categories": Counter(),
        "responsibilities": Counter(),
        "productive_quadrants": Counter(),
        "movement_quadrants": Counter(),
        "quadrant_transitions": 0,
        "shed_entries": 0,
    }


def _serialize_counter(counter):
    return {key: counter[key] for key in sorted(counter) if counter[key]}


def _apply_and_measure(previous_states, current_states, configuration, selected_players, accumulators):
    previous_obs = previous_states[0]["observation"]
    day = int(previous_obs.get("day", previous_obs.get("step", 0) // 24))
    hour = int(previous_obs.get("hour", previous_obs.get("step", 0) % 24))
    board_size = int(configuration.get("boardSize", 10))
    turns_per_day = int(configuration.get("turnsPerDay", 24))
    shed_capacity = int(configuration.get("shedCapacity", 100))
    actions = [state.get("action") or {} for state in current_states]

    ledgers, _ = _transition_ledger(previous_states, current_states, configuration)

    for player in selected_players:
        accumulator = accumulators[player]
        farm = deepcopy(previous_obs["farms"][player])
        private = deepcopy(previous_states[player]["observation"]["private"])
        action = actions[player] if isinstance(actions[player], dict) else {}
        farmer_action = action.get("farmer", ["PASS"])
        hand_actions = action.get("hands", [])
        hand_actions = hand_actions if isinstance(hand_actions, list) else []
        unit_count = 1 + len(farm.get("hands", []))
        unit_actions = [farmer_action, *hand_actions]
        unit_actions += [["PASS"]] * max(0, unit_count - len(unit_actions))
        unit_actions = unit_actions[:unit_count]
        scale = 25 * len(farm.get("unlocked_quadrants", []))
        metrics = accumulator["by_scale"][scale]

        positions_before = [tuple(farm["farmer"])] + [tuple(value) for value in farm["hands"]]
        submitted_targets = Counter()
        for position, unit_action in zip(positions_before, unit_actions):
            if _op(unit_action) in PRODUCTIVE:
                submitted_targets[position] += 1
        metrics["duplicate_conflicts"] += sum(max(0, count - 1) for count in submitted_targets.values())

        plant_demand = Counter(
            unit_action[1]
            for unit_action in unit_actions
            if isinstance(unit_action, list)
            and len(unit_action) >= 2
            and unit_action[0] == "PLANT"
        )
        blocked = {
            crop for crop, count in plant_demand.items()
            if count > private.get("seeds", {}).get(crop, 0)
        }

        for unit_index, original_action in enumerate(unit_actions):
            unit_action = original_action
            if (
                isinstance(original_action, list)
                and len(original_action) >= 2
                and original_action[0] == "PLANT"
                and original_action[1] in blocked
            ):
                unit_action = ["PASS"]
            position = tuple(farm["farmer"] if unit_index == 0 else farm["hands"][unit_index - 1])
            inventory = private["inventories"][unit_index]
            before_inventory = dict(inventory)
            before_tile = deepcopy(farm["tiles"][position[1]][position[0]])
            op = _op(unit_action)
            worker_key = (day, unit_index)
            if worker_key not in accumulator["worker_days"]:
                accumulator["worker_days"][worker_key] = _worker_record(day, unit_index, position)
            worker = accumulator["worker_days"][worker_key]
            worker["actions"][op] += 1

            game._apply_unit_action(
                farm,
                private,
                unit_index,
                unit_action,
                board_size,
                day,
                turns_per_day,
                shed_capacity,
            )
            after_position = tuple(farm["farmer"] if unit_index == 0 else farm["hands"][unit_index - 1])
            after_tile = farm["tiles"][position[1]][position[0]]
            after_inventory = dict(private["inventories"][unit_index])
            category = _effect_category(
                op, before_tile, before_inventory, after_tile, after_inventory,
                position, after_position,
            )
            responsibility = _responsibility(op, before_tile, after_tile)
            metrics["total_actions"] += 1
            metrics[f"{category}_actions"] += 1
            worker["categories"][category] += 1
            worker["responsibilities"][responsibility] += category == "productive"
            if category == "productive":
                worker["productive_quadrants"][_quadrant(position)] += 1
            if category == "movement":
                origin_quadrant = _quadrant(position)
                destination_quadrant = _quadrant(after_position)
                worker["movement_quadrants"][destination_quadrant] += 1
                if origin_quadrant != destination_quadrant:
                    worker["quadrant_transitions"] += 1
                if _inventory_total(before_inventory) and _shed_distance(after_position) < _shed_distance(position):
                    metrics["shed_directed_moves"] += 1
                if after_position in SHED_TILES and position not in SHED_TILES:
                    metrics["shed_entries"] += 1
                    worker["shed_entries"] += 1

        # End-of-day maintenance is measured after the hour-23 submitted field actions.
        if hour == turns_per_day - 1:
            productive = 0
            empty = 0
            for row in farm["tiles"]:
                for tile in row:
                    if tile == "LOCKED":
                        continue
                    if tile is None or (isinstance(tile, dict) and tile.get("kind") == "WEED"):
                        empty += 1
                    if _is_plant(tile):
                        productive += 1
                        metrics["plant_day_checks"] += 1
                        if not tile.get("watered_today", False):
                            metrics["missed_watering"] += 1
                            if tile.get("consecutive_unwatered", 0) >= 1:
                                metrics["critical_missed_watering"] += 1
                        data = game.CROPS[tile["crop"]]
                        age = day - tile.get("planted_day", day)
                        peak = data.get("max_yield_day", data.get("first_yield_day", 0))
                        if tile.get("yield_units", 0) > 0 and age >= peak:
                            metrics["delayed_crop_harvests"] += 1
                    elif _is_animal(tile):
                        productive += 1
                        metrics["animal_day_checks"] += 1
                        if not tile.get("fed_today", False):
                            metrics["animals_unfed"] += 1
                        if not tile.get("cared_today", False):
                            metrics["animals_uncared"] += 1
                        if tile.get("fertilizer_available", False):
                            metrics["fertilizer_left"] += 1
                        if tile.get("yield_units", 0) > 0:
                            metrics["animal_product_unharvested"] += 1
            metrics["productive_tiles_sum"] += productive
            metrics["unlocked_tiles_sum"] += scale
            metrics["daily_checks"] += 1
            if farm.get("money", 0) >= min(data["seed"] for data in game.CROPS.values()):
                metrics["empty_tiles_with_capital"] += empty

        # FIFO harvest-to-sale matching; premium products cannot be bought back.
        for product, quantity in ledgers[player]["harvest_quantity"].items():
            accumulator["harvest_queue"][product].append([quantity, previous_obs.get("step", 0), scale])
        for product, quantity in ledgers[player]["sale_quantity"].items():
            remaining = quantity
            queue = accumulator["harvest_queue"][product]
            while remaining > 0 and queue:
                batch_quantity, harvest_step, harvest_scale = queue[0]
                matched = min(remaining, batch_quantity)
                accumulator["sale_lags"][harvest_scale].extend(
                    [previous_obs.get("step", 0) - harvest_step] * matched
                )
                batch_quantity -= matched
                remaining -= matched
                if batch_quantity:
                    queue[0][0] = batch_quantity
                else:
                    queue.popleft()
        accumulator["sale_revenue"].update(ledgers[player]["sale_revenue"])
        accumulator["seed_spending"].update(ledgers[player]["seed_spend"])
        accumulator["product_spending"].update(ledgers[player]["product_spend"])
        accumulator["animal_spending"].update(ledgers[player]["animal_spend"])
        accumulator["labor_spending"] += ledgers[player]["labor_spend"]
        accumulator["land_spending"] += ledgers[player]["land_spend"]
        animal_revenue = sum(
            ledgers[player]["sale_revenue"].get(product, 0)
            for product in ANIMAL_PRODUCTS
        )
        animal_cost = (
            sum(ledgers[player]["animal_spend"].values())
            + ledgers[player]["product_spend"].get("WHEAT", 0)
        )
        accumulator["animal_cashflow_by_day"][day]["revenue"] += animal_revenue
        accumulator["animal_cashflow_by_day"][day]["cost"] += animal_cost


def _new_accumulator():
    return {
        "by_scale": defaultdict(_blank_metrics),
        "worker_days": {},
        "harvest_queue": defaultdict(deque),
        "sale_lags": defaultdict(list),
        "land_unlocks": [],
        "first_land_use": {},
        "previous_quadrants": None,
        "sale_revenue": Counter(),
        "seed_spending": Counter(),
        "product_spending": Counter(),
        "animal_spending": Counter(),
        "labor_spending": 0,
        "land_spending": 0,
        "animal_cashflow_by_day": defaultdict(Counter),
    }


def _track_land_use(states, index, player, accumulator):
    obs = states[0]["observation"]
    farm = obs["farms"][player]
    unlocked = list(farm.get("unlocked_quadrants", []))
    current = set(unlocked)
    previous = accumulator.get("previous_quadrants")
    if previous is None:
        accumulator["previous_quadrants"] = current
        return
    for quadrant in sorted(current - previous):
        accumulator["land_unlocks"].append({"quadrant": quadrant, "step": obs.get("step", index)})
    accumulator["previous_quadrants"] = current


def _finalize_land_use(steps, player, accumulator):
    # A tile becomes productive on the first observed state containing a plant,
    # animal, or structure in the newly unlocked quadrant.
    for event in accumulator["land_unlocks"]:
        quadrant = event["quadrant"]
        first = None
        for states in steps[event["step"]:]:
            obs = states[0]["observation"]
            farm = obs["farms"][player]
            for y, row in enumerate(farm["tiles"]):
                for x, tile in enumerate(row):
                    if _quadrant((x, y)) != quadrant or not isinstance(tile, dict):
                        continue
                    if tile.get("kind") in {"PLANT", "COOP", "PASTURE"}:
                        first = obs.get("step", 0)
                        break
                if first is not None:
                    break
            if first is not None:
                break
        event["first_productive_step"] = first
        event["delay_turns"] = None if first is None else first - event["step"]


def _rate(numerator, denominator):
    return numerator / denominator if denominator else 0.0


def _finalize_metrics(metrics, sale_lags):
    output = dict(metrics)
    total = output["total_actions"]
    output.update({
        "productive_action_ratio": _rate(output["productive_actions"], total),
        "movement_action_ratio": _rate(output["movement_actions"], total),
        "pass_action_ratio": _rate(output["pass_actions"], total),
        "invalid_action_ratio": _rate(output["invalid_actions"], total),
        "movement_per_productive_action": _rate(
            output["movement_actions"], output["productive_actions"]
        ),
        "watering_miss_rate": _rate(output["missed_watering"], output["plant_day_checks"]),
        "critical_watering_miss_rate": _rate(
            output["critical_missed_watering"], output["plant_day_checks"]
        ),
        "animal_unfed_rate": _rate(output["animals_unfed"], output["animal_day_checks"]),
        "animal_uncared_rate": _rate(output["animals_uncared"], output["animal_day_checks"]),
        "fertilizer_left_rate": _rate(output["fertilizer_left"], output["animal_day_checks"]),
        "animal_product_wait_rate": _rate(
            output["animal_product_unharvested"], output["animal_day_checks"]
        ),
        "productive_tile_utilization": _rate(
            output["productive_tiles_sum"], output["unlocked_tiles_sum"]
        ),
        "average_productive_tiles": _rate(
            output["productive_tiles_sum"], output["daily_checks"]
        ),
        "average_empty_tiles_with_capital": _rate(
            output["empty_tiles_with_capital"], output["daily_checks"]
        ),
        "average_harvest_to_sale_turns": statistics.fmean(sale_lags) if sale_lags else None,
        "median_harvest_to_sale_turns": statistics.median(sale_lags) if sale_lags else None,
    })
    return output


def _worker_summary(worker_days):
    rows = []
    for worker in worker_days.values():
        productive = sum(worker["productive_quadrants"].values())
        worker["territory_purity"] = (
            max(worker["productive_quadrants"].values()) / productive
            if productive else None
        )
        rows.append(worker)
    aggregate = []
    for unit_index in sorted({row["unit_index"] for row in rows}):
        selected = [row for row in rows if row["unit_index"] == unit_index]
        categories = Counter()
        responsibilities = Counter()
        quadrants = Counter()
        spawns = Counter()
        for row in selected:
            categories.update(row["categories"])
            responsibilities.update(row["responsibilities"])
            quadrants.update(row["productive_quadrants"])
            spawns[tuple(row["spawn_position"])] += 1
        purities = [row["territory_purity"] for row in selected if row["territory_purity"] is not None]
        aggregate.append({
            "unit_index": unit_index,
            "worker_days": len(selected),
            "spawn_positions": {str(key): value for key, value in spawns.most_common()},
            "categories": _serialize_counter(categories),
            "responsibilities": _serialize_counter(responsibilities),
            "productive_quadrants": _serialize_counter(quadrants),
            "median_territory_purity": statistics.median(purities) if purities else None,
            "average_quadrant_transitions_per_day": statistics.fmean(
                row["quadrant_transitions"] for row in selected
            ),
            "average_shed_entries_per_day": statistics.fmean(row["shed_entries"] for row in selected),
        })
    return aggregate


def analyze_steps(steps, configuration, selected_players):
    accumulators = {player: _new_accumulator() for player in selected_players}
    for index, states in enumerate(steps):
        for player in selected_players:
            _track_land_use(states, index, player, accumulators[player])
        if index:
            _apply_and_measure(
                steps[index - 1], states, configuration, selected_players, accumulators
            )
    output = {}
    for player, accumulator in accumulators.items():
        _finalize_land_use(steps, player, accumulator)
        cashflow = []
        cumulative = 0
        for day in range(30):
            row = accumulator["animal_cashflow_by_day"][day]
            cumulative += row["revenue"] - row["cost"]
            cashflow.append({
                "day": day,
                "revenue": row["revenue"],
                "cost": row["cost"],
                "cumulative_net": cumulative,
            })
        durable_payback = next(
            (
                row["day"] for index, row in enumerate(cashflow)
                if row["cumulative_net"] >= 0
                and all(later["cumulative_net"] >= 0 for later in cashflow[index:])
            ),
            None,
        )
        output[player] = {
            "by_scale": {
                str(scale): _finalize_metrics(metrics, accumulator["sale_lags"].get(scale, []))
                for scale, metrics in sorted(accumulator["by_scale"].items())
            },
            "worker_profiles": _worker_summary(accumulator["worker_days"]),
            "land_use": accumulator["land_unlocks"],
            "sale_revenue": _serialize_counter(accumulator["sale_revenue"]),
            "spending": {
                "seeds": _serialize_counter(accumulator["seed_spending"]),
                "products": _serialize_counter(accumulator["product_spending"]),
                "animals": _serialize_counter(accumulator["animal_spending"]),
                "labor": accumulator["labor_spending"],
                "land": accumulator["land_spending"],
            },
            "animal_cashflow": cashflow,
            "animal_payback_day": durable_payback,
        }
    return output


def _combine_appearances(appearances):
    scales = defaultdict(_blank_metrics)
    sale_lags = defaultdict(list)
    land_delays = []
    worker_profiles = defaultdict(list)
    for appearance in appearances:
        for raw_scale, metrics in appearance["routing"]["by_scale"].items():
            scale = int(raw_scale)
            for key, value in metrics.items():
                if key.endswith("_ratio") or key.startswith("average_") or key.startswith("median_") or key == "movement_per_productive_action":
                    continue
                if isinstance(value, (int, float)):
                    scales[scale][key] += value
        for event in appearance["routing"]["land_use"]:
            if event.get("delay_turns") is not None:
                land_delays.append(event["delay_turns"])
        for profile in appearance["routing"]["worker_profiles"]:
            worker_profiles[profile["unit_index"]].append(profile)
    combined = {
        str(scale): _finalize_metrics(metrics, sale_lags.get(scale, []))
        for scale, metrics in sorted(scales.items())
    }
    # Harvest-sale aggregates are recomputed separately from appearance means.
    for scale in combined:
        values = [
            appearance["routing"]["by_scale"].get(scale, {}).get("average_harvest_to_sale_turns")
            for appearance in appearances
        ]
        values = [value for value in values if value is not None]
        combined[scale]["average_harvest_to_sale_turns"] = statistics.fmean(values) if values else None
    worker_output = []
    for unit_index, profiles in sorted(worker_profiles.items()):
        purities = [p["median_territory_purity"] for p in profiles if p["median_territory_purity"] is not None]
        roles = Counter()
        quadrants = Counter()
        for profile in profiles:
            roles.update(profile["responsibilities"])
            quadrants.update(profile["productive_quadrants"])
        worker_output.append({
            "unit_index": unit_index,
            "appearances": len(profiles),
            "responsibilities": _serialize_counter(roles),
            "productive_quadrants": _serialize_counter(quadrants),
            "median_territory_purity": statistics.median(purities) if purities else None,
            "average_quadrant_transitions_per_day": statistics.fmean(
                p["average_quadrant_transitions_per_day"] for p in profiles
            ),
            "average_shed_entries_per_day": statistics.fmean(
                p["average_shed_entries_per_day"] for p in profiles
            ),
        })
    return {
        "by_scale": combined,
        "land_first_use_delay_turns": {
            "median": statistics.median(land_delays) if land_delays else None,
            "range": [min(land_delays), max(land_delays)] if land_delays else None,
            "observations": land_delays,
        },
        "worker_profiles": worker_output,
    }


def analyze_public_corpus(corpus=CORPUS):
    manifest = json.loads((corpus / "manifest.json").read_text())
    selected_names = {player["team_name"] for player in manifest["players"]}
    appearances = []
    for path in sorted((corpus / "replays").glob("episode-*-replay.json")):
        replay = json.loads(path.read_text())
        team_names = replay["info"]["TeamNames"]
        selected_players = [index for index, name in enumerate(team_names) if name in selected_names]
        routing = analyze_steps(replay["steps"], replay.get("configuration", {}), selected_players)
        final_money = [float(state["reward"]) for state in replay["steps"][-1]]
        for player in selected_players:
            appearances.append({
                "episode_id": int(replay["info"]["EpisodeId"]),
                "team_name": team_names[player],
                "player_index": player,
                "final_money": final_money[player],
                "routing": routing[player],
            })
        print(f"routing analyzed {path.name}", flush=True)
    return {
        "schema_version": 1,
        "corpus": str(corpus.relative_to(ROOT)),
        "unique_replays": len(list((corpus / "replays").glob("episode-*-replay.json"))),
        "selected_appearances": len(appearances),
        "population": _combine_appearances(appearances),
        "appearances": appearances,
    }


def _markdown(payload):
    lines = [
        "# Top-player worker routing analysis", "",
        "Automatically reconstructed from public replay unit paths and successful action effects.", "",
        "## Efficiency by unlocked capacity", "",
        "| Capacity | Productive % | Movement % | PASS % | Move/productive | Tile utilization | Water miss | Unfed | Uncared | Fertilizer left | Avg harvest-sale turns |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for scale, row in payload["population"]["by_scale"].items():
        def pct(key):
            return f"{100 * row[key]:.1f}%"
        sale = row.get("average_harvest_to_sale_turns")
        lines.append(
            f"| {scale} | {pct('productive_action_ratio')} | {pct('movement_action_ratio')} | "
            f"{pct('pass_action_ratio')} | {row['movement_per_productive_action']:.2f} | "
            f"{pct('productive_tile_utilization')} | {pct('watering_miss_rate')} | "
            f"{pct('animal_unfed_rate')} | {pct('animal_uncared_rate')} | "
            f"{pct('fertilizer_left_rate')} | {sale:.2f} |" if sale is not None else
            f"| {scale} | {pct('productive_action_ratio')} | {pct('movement_action_ratio')} | "
            f"{pct('pass_action_ratio')} | {row['movement_per_productive_action']:.2f} | "
            f"{pct('productive_tile_utilization')} | {pct('watering_miss_rate')} | "
            f"{pct('animal_unfed_rate')} | {pct('animal_uncared_rate')} | "
            f"{pct('fertilizer_left_rate')} | — |"
        )
    delay = payload["population"]["land_first_use_delay_turns"]
    lines.extend([
        "", "## Land activation", "",
        f"Median BUY_LAND-to-first-productive-state delay: {delay['median']} turns; range {delay['range']}.",
        "", "## Worker-index organization", "",
        "| Unit index | Appearances | Main role | Main productive quadrant | Territory purity | Quadrant crossings/day | Shed entries/day |",
        "| ---: | ---: | --- | --- | ---: | ---: | ---: |",
    ])
    for profile in payload["population"]["worker_profiles"]:
        role = max(profile["responsibilities"], key=profile["responsibilities"].get) if profile["responsibilities"] else "none"
        quadrant = max(profile["productive_quadrants"], key=profile["productive_quadrants"].get) if profile["productive_quadrants"] else "none"
        purity = profile["median_territory_purity"]
        lines.append(
            f"| {profile['unit_index']} | {profile['appearances']} | {role} | {quadrant} | "
            f"{purity:.1%} | {profile['average_quadrant_transitions_per_day']:.2f} | "
            f"{profile['average_shed_entries_per_day']:.2f} |"
            if purity is not None else
            f"| {profile['unit_index']} | {profile['appearances']} | {role} | {quadrant} | — | "
            f"{profile['average_quadrant_transitions_per_day']:.2f} | {profile['average_shed_entries_per_day']:.2f} |"
        )
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=CORPUS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    payload = analyze_public_corpus(args.corpus.resolve())
    args.output.resolve().write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.report.resolve().write_text(_markdown(payload), encoding="utf-8")
    print(args.output.resolve())
    print(args.report.resolve())


if __name__ == "__main__":
    main()
