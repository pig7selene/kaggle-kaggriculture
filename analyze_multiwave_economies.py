"""Reconstruct crop cohorts, liquidation waves, and reinvestment from replays.

This analyzer is deliberately economic rather than strategic: it treats each
successful planting-day/crop group as a cohort, measures its spatial and labor
shape, groups crop sales into liquidation waves, and then measures the capital
converted into productive purchases after each wave.
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from runpy import run_path

from kaggle_environments import make
from kaggle_environments.envs.kaggriculture import kaggriculture as game

from analyze_epic_next_stage import _snapshot
from analyze_top_player_replays import _transition_ledger
from run_epic_experiments import _recorded_shop_schedule, _run_with_fixed_shops
from run_leaderboard_breakthrough import HELDOUT_REPLAY_CASES, _trace_spec
from run_post_opening_validation import _load_opponent


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "experiments/multiwave_top_analysis.json"
R3_REPLAYS = ROOT / "experiments/multiwave_r3_replays"
CROPS = tuple(game.CROPS)
ANIMAL_PRODUCTS = ("EGG", "MILK", "WOOL", "FERTILIZER")
CHECKPOINT_DAYS = (4, 6, 8, 9, 10, 11, 12, 14, 16, 18, 20, 21, 22, 25, 30)
PRIORITY = {
    key: HELDOUT_REPLAY_CASES[key]
    for key in (
        "Filip_top_template", "Amer_high_scale",
        "Yankang_wheat_close", "Prashant_crop_scaler",
    )
}


def _plain(value):
    return {key: value[key] for key in sorted(value) if value[key]}


def _quadrant(position):
    x, y = position
    return ("N" if y < 5 else "S") + ("W" if x < 5 else "E")


def _components(positions):
    remaining = set(positions)
    sizes = []
    while remaining:
        stack = [remaining.pop()]
        size = 0
        while stack:
            x, y = stack.pop()
            size += 1
            for neighbor in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    stack.append(neighbor)
        sizes.append(size)
    return sorted(sizes, reverse=True)


def _inventory(state):
    private = state.get("observation", {}).get("private", {})
    total = Counter(private.get("shed", {}))
    for carried in private.get("inventories", []):
        total.update(carried)
    return total


def _checkpoint(replay, player, day):
    target_step = 719 if day == 30 else min(719, day * 24 + 23)
    states = replay["steps"][target_step]
    obs = states[0]["observation"]
    farm = obs["farms"][player]
    snap = _snapshot(obs, player)
    inventory = _inventory(states[player])
    inventory_value = sum(
        inventory[item] * obs["market"]["prices"].get(item, 0)
        for item in set(CROPS) | set(ANIMAL_PRODUCTS)
    )
    return {
        "day": day,
        "step": target_step,
        "bank": float(farm["money"]),
        "quadrants": len(farm.get("unlocked_quadrants", [])),
        "hands": len(farm.get("hands", [])),
        "productive_tiles": snap["productive_tiles"],
        "occupied_crop_tiles": sum(snap["crops"].values()),
        "mature_crop_tiles": sum(snap["mature_crops"].values()),
        "crops": snap["crops"],
        "mature_crops": snap["mature_crops"],
        "cows": snap["animals"].get("COW", 0),
        "sheep": snap["animals"].get("SHEEP", 0),
        "inventory": _plain(inventory),
        "inventory_value": inventory_value,
    }


def _unit_events(previous, current, player):
    obs = previous[0]["observation"]
    farm = obs["farms"][player]
    next_obs = current[0]["observation"]
    next_farm = next_obs["farms"][player]
    before_private = previous[player]["observation"]["private"]
    after_private = current[player]["observation"]["private"]
    action = current[player].get("action") or {}
    positions = [tuple(farm["farmer"]), *map(tuple, farm.get("hands", []))]
    unit_actions = [action.get("farmer", ["PASS"]), *action.get("hands", [])]
    unit_actions.extend([["PASS"]] * max(0, len(positions) - len(unit_actions)))
    rows = []
    for unit, (position, unit_action) in enumerate(zip(positions, unit_actions)):
        op = unit_action[0] if unit_action else "PASS"
        if op not in {"PLANT", "WATER", "HARVEST", "DIG"}:
            continue
        x, y = position
        before_tile = farm["tiles"][y][x]
        after_tile = next_farm["tiles"][y][x]
        successful = False
        quantity = 0
        crop = None
        planted_day = None
        if op == "PLANT":
            crop = unit_action[1] if len(unit_action) > 1 else None
            successful = (
                before_tile is None and isinstance(after_tile, dict)
                and after_tile.get("kind") == "PLANT" and after_tile.get("crop") == crop
            )
            planted_day = int(obs["day"])
        elif isinstance(before_tile, dict) and before_tile.get("kind") == "PLANT":
            crop = before_tile.get("crop")
            planted_day = int(before_tile.get("planted_day", obs["day"]))
            if op == "WATER":
                successful = bool(
                    not before_tile.get("watered_today", False)
                    and isinstance(after_tile, dict) and after_tile.get("watered_today", False)
                )
            elif op == "HARVEST":
                before_inventories = before_private.get("inventories", [])
                after_inventories = after_private.get("inventories", [])
                before_inv = before_inventories[unit] if unit < len(before_inventories) else {}
                after_inv = after_inventories[unit] if unit < len(after_inventories) else {}
                quantity = max(0, after_inv.get(crop, 0) - before_inv.get(crop, 0))
                # At the end-of-day boundary hands disappear and their carried
                # inventory is returned before the next observation. Infer the
                # successful harvest from the tile transition in that case.
                if quantity <= 0:
                    if not game.CROPS[crop]["ongoing"] and not (
                        isinstance(after_tile, dict) and after_tile.get("kind") == "PLANT"
                    ):
                        quantity = int(before_tile.get("yield_units", 0))
                    elif isinstance(after_tile, dict):
                        quantity = max(
                            0,
                            int(before_tile.get("yield_units", 0))
                            - int(after_tile.get("yield_units", 0)),
                        )
                successful = quantity > 0
            elif op == "DIG":
                successful = before_tile != after_tile
        if successful:
            rows.append({
                "step": int(obs["step"]), "day": int(obs["day"]),
                "hour": int(obs["hour"]), "unit": unit,
                "position": list(position), "quadrant": _quadrant(position),
                "op": op, "crop": crop, "planted_day": planted_day,
                "quantity": quantity,
            })
    return rows


def _group_liquidations(sales):
    by_crop = defaultdict(list)
    for event in sales:
        for crop in CROPS:
            quantity = event["quantities"].get(crop, 0)
            if quantity:
                by_crop[crop].append({
                    "step": event["step"], "day": event["day"], "hour": event["hour"],
                    "quantity": quantity, "revenue": event["revenue"].get(crop, 0),
                    "mean_price": event["mean_prices"].get(crop),
                })
    waves = []
    for crop, events in by_crop.items():
        groups = []
        for event in events:
            if not groups or event["step"] - groups[-1][-1]["step"] > 8:
                groups.append([])
            groups[-1].append(event)
        for group in groups:
            quantity = sum(row["quantity"] for row in group)
            revenue = sum(row["revenue"] for row in group)
            if quantity < 6 and revenue < 500:
                continue
            waves.append({
                "crop": crop, "first_step": group[0]["step"],
                "last_step": group[-1]["step"],
                "liquidation_day": group[0]["day"],
                "liquidation_hour": group[0]["hour"],
                "units_sold": quantity, "revenue": revenue,
                "average_price": revenue / max(1, quantity),
                "sale_events": group,
            })
    return sorted(waves, key=lambda row: (row["first_step"], row["crop"]))


def analyze_replay(replay, player, label):
    cohorts = defaultdict(lambda: {
        "plant_steps": [], "harvest_steps": [], "positions": set(),
        "workers": set(), "plant_actions": 0, "water_actions": 0,
        "harvest_actions": 0, "harvest_quantity": 0,
        "movement_inside": 0, "territory_crossings": 0,
    })
    sales = []
    investments = []
    cumulative_crop = 0
    cumulative_animal = 0
    cumulative_spending = 0
    checkpoints = {}
    checkpoint_steps = {719 if day == 30 else min(719, day * 24 + 23): day for day in CHECKPOINT_DAYS}
    financial_mismatches = []

    for index in range(1, len(replay["steps"])):
        previous, current = replay["steps"][index - 1], replay["steps"][index]
        obs = previous[0]["observation"]
        step, day, hour = int(obs["step"]), int(obs["day"]), int(obs["hour"])
        ledgers, errors = _transition_ledger(previous, current, replay["configuration"])
        financial_mismatches.extend(errors)
        ledger = ledgers[player]
        crop_revenue = sum(ledger["sale_revenue"][crop] for crop in CROPS)
        animal_revenue = sum(ledger["sale_revenue"][item] for item in ANIMAL_PRODUCTS)
        cumulative_crop += crop_revenue
        cumulative_animal += animal_revenue
        productive_spend = (
            sum(ledger["seed_spend"].values()) + sum(ledger["animal_spend"].values())
            + ledger["land_spend"] + ledger["labor_spend"]
        )
        cumulative_spending += productive_spend + sum(ledger["product_spend"].values())
        if sum(ledger["sale_quantity"].values()):
            sales.append({
                "step": step, "day": day, "hour": hour,
                "quantities": _plain(ledger["sale_quantity"]),
                "revenue": _plain(ledger["sale_revenue"]),
                "mean_prices": {
                    item: statistics.fmean(values)
                    for item, values in ledger["sale_prices"].items() if values
                },
            })
        if productive_spend:
            investments.append({
                "step": step, "day": day, "hour": hour,
                "seed_spend": _plain(ledger["seed_spend"]),
                "animal_spend": _plain(ledger["animal_spend"]),
                "land_spend": ledger["land_spend"],
                "labor_spend": ledger["labor_spend"],
                "productive_spend": productive_spend,
                "seed_quantity": _plain(ledger["seed_quantity"]),
                "animal_quantity": _plain(ledger["animal_quantity"]),
                "land_count": ledger["land_count"],
                "hire_count": ledger["hire_count"],
            })
        unit_events = _unit_events(previous, current, player)
        for event in unit_events:
            if event["crop"] is None or event["op"] == "DIG":
                continue
            key = (event["crop"], event["planted_day"])
            row = cohorts[key]
            row[event["op"].lower() + "_actions"] += 1
            row["workers"].add(event["unit"])
            if event["op"] == "PLANT":
                row["positions"].add(tuple(event["position"]))
                row["plant_steps"].append(step)
            elif event["op"] == "HARVEST":
                row["harvest_steps"].append(step)
                row["harvest_quantity"] += event["quantity"]

        # Count movement inside the eventual cohort territory and crossings.
        farm = obs["farms"][player]
        action = current[player].get("action") or {}
        positions = [tuple(farm["farmer"]), *map(tuple, farm.get("hands", []))]
        actions = [action.get("farmer", ["PASS"]), *action.get("hands", [])]
        for unit, (position, unit_action) in enumerate(zip(positions, actions)):
            op = unit_action[0] if unit_action else "PASS"
            if op not in {"NORTH", "SOUTH", "EAST", "WEST"}:
                continue
            delta = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}[op]
            after = (position[0] + delta[0], position[1] + delta[1])
            if _quadrant(position) != _quadrant(after):
                for row in cohorts.values():
                    if position in row["positions"] or after in row["positions"]:
                        row["territory_crossings"] += 1

        if index in checkpoint_steps:
            cp = _checkpoint(replay, player, checkpoint_steps[index])
            cp["cumulative_crop_revenue"] = cumulative_crop
            cp["cumulative_animal_revenue"] = cumulative_animal
            cp["cumulative_spending"] = cumulative_spending
            checkpoints[str(checkpoint_steps[index])] = cp

    cohort_rows = []
    for (crop, planted_day), row in sorted(cohorts.items(), key=lambda item: (item[0][1], item[0][0])):
        positions = row["positions"]
        if not positions:
            continue
        component_sizes = _components(positions)
        quadrants = Counter(_quadrant(position) for position in positions)
        cohort_rows.append({
            "crop": crop, "planted_day": planted_day,
            "cohort_size": len(positions),
            "first_plant_step": min(row["plant_steps"]),
            "median_plant_step": statistics.median(row["plant_steps"]),
            "last_plant_step": max(row["plant_steps"]),
            "planting_spread_turns": max(row["plant_steps"]) - min(row["plant_steps"]),
            "first_harvest_step": min(row["harvest_steps"]) if row["harvest_steps"] else None,
            "median_harvest_step": statistics.median(row["harvest_steps"]) if row["harvest_steps"] else None,
            "last_harvest_step": max(row["harvest_steps"]) if row["harvest_steps"] else None,
            "harvest_spread_turns": (
                max(row["harvest_steps"]) - min(row["harvest_steps"])
                if row["harvest_steps"] else None
            ),
            "harvest_quantity": row["harvest_quantity"],
            "plant_actions": row["plant_actions"],
            "water_actions": row["water_actions"],
            "harvest_actions": row["harvest_actions"],
            "maintenance_actions": row["water_actions"],
            "workers": len(row["workers"]),
            "quadrants": _plain(quadrants),
            "quadrant_purity": max(quadrants.values()) / max(1, len(positions)),
            "component_sizes": component_sizes,
            "largest_component_fraction": component_sizes[0] / max(1, len(positions)),
            "territory_crossings": row["territory_crossings"],
            "positions": [list(position) for position in sorted(positions)],
        })

    waves = _group_liquidations(sales)
    for wave in waves:
        horizon = [row for row in investments if wave["first_step"] <= row["step"] <= wave["last_step"] + 24]
        within3 = sum(row["productive_spend"] for row in horizon if row["step"] <= wave["last_step"] + 3)
        within6 = sum(row["productive_spend"] for row in horizon if row["step"] <= wave["last_step"] + 6)
        within12 = sum(row["productive_spend"] for row in horizon if row["step"] <= wave["last_step"] + 12)
        first = min((row["step"] for row in horizon), default=None)
        wave.update({
            "cash_idle_turns": None if first is None else max(0, first - wave["last_step"]),
            "productive_reinvestment_3_turns": within3,
            "productive_reinvestment_6_turns": within6,
            "productive_reinvestment_12_turns": within12,
            "reinvestment_fraction_6_turns": within6 / max(1, wave["revenue"]),
            "reinvestment_fraction_12_turns": within12 / max(1, wave["revenue"]),
            "purchases_12_turns": horizon,
        })
        before = _checkpoint(replay, player, min(30, wave["liquidation_day"]))
        after = _checkpoint(replay, player, min(30, wave["liquidation_day"] + 1))
        wave["productive_capacity_gain_next_day"] = after["productive_tiles"] - before["productive_tiles"]

        recent = [
            cohort for cohort in cohort_rows
            if cohort["crop"] == wave["crop"]
            and cohort["first_harvest_step"] is not None
            and cohort["first_harvest_step"] <= wave["last_step"]
            and cohort["last_harvest_step"] >= wave["first_step"] - 24
        ]
        wave["source_cohorts"] = [
            {key: cohort[key] for key in (
                "crop", "planted_day", "cohort_size", "first_plant_step",
                "median_plant_step", "first_harvest_step", "median_harvest_step",
                "harvest_quantity", "maintenance_actions", "workers",
                "quadrant_purity", "largest_component_fraction",
            )}
            for cohort in recent
        ]

    final = replay["steps"][-1][player]
    return {
        "label": label, "episode_id": replay.get("info", {}).get("EpisodeId"),
        "player": player,
        "team": replay.get("info", {}).get("TeamNames", [None, None])[player],
        "seed": int(replay.get("info", {}).get("seed", replay["configuration"].get("seed", 0))),
        "final_money": float(final.get("reward", 0)),
        "financial_mismatches": financial_mismatches,
        "checkpoints": checkpoints,
        "cohorts": cohort_rows,
        "liquidation_waves": waves,
        "investments": investments,
        "capital_wave_graph": [
            {
                "cohort": wave["source_cohorts"],
                "liquidation": {key: wave[key] for key in (
                    "crop", "first_step", "last_step", "units_sold", "revenue", "average_price"
                )},
                "reinvestment": {
                    "cash_idle_turns": wave["cash_idle_turns"],
                    "fraction_6_turns": wave["reinvestment_fraction_6_turns"],
                    "fraction_12_turns": wave["reinvestment_fraction_12_turns"],
                    "purchases": wave["purchases_12_turns"],
                    "next_day_capacity_gain": wave["productive_capacity_gain_next_day"],
                },
            }
            for wave in waves if wave["revenue"] >= 1000
        ],
    }


def _rerun_r3(name, case):
    _, replay_path, source_player = case
    source = json.loads((ROOT / replay_path).read_text())
    opponent = _load_opponent(_trace_spec(replay_path, source_player))
    agent = run_path(str(ROOT / "agents/leaderboard_r3_cow6_capital.py"))["agent"]
    seed = int(source["info"]["seed"])
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=True)
    _run_with_fixed_shops(env, [agent, opponent], _recorded_shop_schedule(source))
    replay = env.toJSON()
    R3_REPLAYS.mkdir(parents=True, exist_ok=True)
    path = R3_REPLAYS / f"{name}_r3_seat0.json"
    path.write_text(json.dumps(replay))
    return replay, 0, str(path.relative_to(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reuse-r3", action="store_true")
    args = parser.parse_args()
    appearances = []
    manifest = []
    for name, case in PRIORITY.items():
        _, replay_path, player = case
        replay = json.loads((ROOT / replay_path).read_text())
        appearances.append(analyze_replay(replay, player, name))
        r3_path = R3_REPLAYS / f"{name}_r3_seat0.json"
        if args.reuse_r3 and r3_path.exists():
            r3_replay, r3_player, relative = json.loads(r3_path.read_text()), 0, str(r3_path.relative_to(ROOT))
        else:
            r3_replay, r3_player, relative = _rerun_r3(name, case)
        appearances.append(analyze_replay(r3_replay, r3_player, f"R3_vs_{name}"))
        manifest.append({
            "opponent": name, "source_replay": replay_path,
            "source_player": player, "r3_replay": relative, "r3_player": r3_player,
        })
    payload = {
        "schema_version": 1,
        "definitions": {
            "cohort": "successful plant actions grouped by crop and planted day",
            "liquidation_wave": "same-crop sale events separated by no more than eight turns",
            "cash_idle_turns": "turns from the end of a crop liquidation group to the next seed/animal/land/labor spend",
            "reinvestment_fraction": "productive spend in the horizon divided by crop liquidation revenue; may exceed one when other cash is deployed",
        },
        "manifest": manifest,
        "appearances": appearances,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(OUTPUT)


if __name__ == "__main__":
    main()
