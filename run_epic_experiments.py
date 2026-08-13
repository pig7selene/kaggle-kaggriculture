"""RNG-controlled architecture ablations for the epic next-stage research."""

from __future__ import annotations

import argparse
import json
import random
import statistics
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from runpy import run_path

from kaggle_environments import make
from kaggle_environments.envs.kaggriculture import kaggriculture as game

from analyze_crop_lifecycle import lifecycle_metrics
from analyze_post_opening_real_gap import _field_analysis
from analyze_top_player_replays import _transition_ledger
from run_post_opening_validation import (
    LOSS_EPISODES,
    REPLAY_DERIVED,
    REPLAY_DIR,
    ROOT,
    _load_opponent,
    _trace_spec,
)
from test_economic_agents import SELLABLE, _validate_action


CANDIDATES = {
    "B0": "agents/epic_b0_current.py",
    "B1_value": "agents/epic_b1_value_scheduler.py",
    "B2_predictive": "agents/epic_b2_predictive.py",
    "B3_adjacent": "agents/epic_b3_adjacent_help.py",
    "B5_phase": "agents/epic_b5_replay_crop_phase.py",
    "B6_cows6": "agents/epic_b6_cows6.py",
    "B6_cows7": "agents/epic_b6_cows7.py",
    "B6_cows8": "agents/epic_b6_cows8.py",
    "B6_cows9": "agents/epic_b0_current.py",
    "B_market": "agents/epic_b_market_demand_capture.py",
    "B7_c6_value": "agents/epic_b7_cows6_value.py",
    "B7_c6_adjacent": "agents/epic_b7_cows6_adjacent.py",
    "B7_c6_value_adjacent": "agents/epic_b7_cows6_value_adjacent.py",
    "B7_c7_value_adjacent": "agents/epic_b7_cows7_value_adjacent.py",
    "B7_c6_phase": "agents/epic_b7_cows6_phase.py",
    "B8_c6_value_phase": "agents/epic_b8_cows6_value_phase.py",
    "B8_guarded": "agents/epic_b8_capacity_value_guarded.py",
    "B_pedro_market": "agents/epic_b_pedro_market.py",
    "B8_c6_value_market": "agents/epic_b8_cows6_value_market.py",
    "R0_803": "agents/opening_public_front_cow8_day6.py",
    "R1_yield": "agents/leaderboard_r1_yield_completion.py",
    "R2_capital": "agents/leaderboard_r2_capital_cohorts.py",
    "R3_c6_capital": "agents/leaderboard_r3_cow6_capital.py",
    "R4_capital_value": "agents/leaderboard_r4_capital_planner.py",
    "R5_c6_capital_clean": "agents/leaderboard_r5_cow6_capital_clean.py",
    "R6_timeline_planner": "agents/leaderboard_r6_timeline_planner.py",
    "G1_capital_harvest": "agents/r3_g1_capital_window_harvest.py",
    "G2_market_harvest": "agents/r3_g2_market_harvest.py",
    "G3_capital_sale": "agents/r3_g3_capital_sale.py",
    "G4_milk_annuity": "agents/r3_g4_milk_annuity.py",
    "G5_late_crop_floor": "agents/r3_g5_late_crop_floor.py",
    "G6_combined": "agents/r3_g6_combined.py",
    "G7_market_cow_recovery": "agents/r3_g7_market_cow_recovery.py",
    "G8_market_cow7": "agents/r3_g8_market_cow7.py",
    "L798": "agents/lifecycle_lc_combined.py",
}
REAL_NAMES = {
    92008833: "Jayveer",
    92009080: "Lucas",
    92010768: "Pedro",
    92011750: "Alexander",
}
HARD_POOL = {
    **REPLAY_DERIVED,
    "epic_jay_wave": "agents/adversaries/epic_jay_capital_wave.py",
    "epic_pedro_trader": "agents/adversaries/epic_pedro_demand_trader.py",
    "livestock_crop": "agents/proxies/livestock_crop.py",
    "high_labor": "agents/proxies/high_labor.py",
    "land_expander": "agents/proxies/land_expander.py",
    "gen_cow6_d8": "agents/adversaries/gen_cow6_d8.py",
}
CROPS = tuple(game.CROPS)
ANIMAL_PRODUCTS = ("EGG", "MILK", "WOOL", "FERTILIZER")
ANIMALS = ("GOOSE", "COW", "SHEEP")


def _source_replay(episode_id):
    return json.loads(next(REPLAY_DIR.glob(f"episode-{episode_id}-replay.json")).read_text())


def _recorded_shop_schedule(replay):
    schedule = {}
    for states in replay["steps"]:
        obs = states[0]["observation"]
        schedule.setdefault(int(obs["day"]), list(obs["town"]["unlocked_shops"]))
    return schedule


def _independent_shop_schedule(seed):
    shops = []
    schedule = {0: []}
    for day in range(1, 30):
        if day % 3 == 0 and len(shops) < 8:
            rng = random.Random(((int(seed) * 1_000_003) ^ (day - 1)) ^ 0xE91C)
            shops.append(rng.choice(sorted(game.SHOPS)))
        schedule[day] = list(shops)
    return schedule


def _run_with_fixed_shops(env, pair, schedule):
    original = game._end_of_day

    def controlled(state, inner_env, day):
        original(state, inner_env, day)
        if day + 1 in schedule:
            state[0].observation.town["unlocked_shops"] = list(schedule[day + 1])

    game._end_of_day = controlled
    try:
        env.run(pair)
    finally:
        game._end_of_day = original


def _plain(counter):
    return {key: counter[key] for key in sorted(counter) if counter[key]}


def _percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    point = fraction * (len(ordered) - 1)
    lower = int(point)
    upper = min(lower + 1, len(ordered) - 1)
    weight = point - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _economic_windows(replay, player):
    windows = {
        "full": (0, 29),
        "day10_20": (10, 20),
        "day21_29": (21, 29),
    }
    rows = {
        name: {
            "sale_quantity": Counter(), "sale_revenue": Counter(),
            "seed_spend": Counter(), "product_spend": Counter(),
            "animal_spend": Counter(), "harvest_quantity": Counter(),
            "labor_spend": 0.0, "land_spend": 0.0, "animal_service_actions": 0,
        }
        for name in windows
    }
    errors = []
    for index in range(1, len(replay["steps"])):
        previous = replay["steps"][index - 1]
        current = replay["steps"][index]
        day = int(previous[0]["observation"]["day"])
        ledgers, mismatch = _transition_ledger(previous, current, replay["configuration"])
        errors.extend(mismatch)
        ledger = ledgers[player]
        for name, (start, end) in windows.items():
            if not start <= day <= end:
                continue
            row = rows[name]
            for key in ("sale_quantity", "sale_revenue", "seed_spend", "product_spend", "animal_spend", "harvest_quantity"):
                row[key].update(ledger[key])
            row["labor_spend"] += ledger["labor_spend"]
            row["land_spend"] += ledger["land_spend"]
            row["animal_service_actions"] += (
                ledger["feed_actions"] + ledger["care_actions"]
                + ledger["fertilizer_collected"]
                + sum(ledger["harvest_quantity"][item] for item in ANIMAL_PRODUCTS)
            )
    if errors:
        raise AssertionError(errors[:3])
    output = {}
    for name, row in rows.items():
        revenue = row["sale_revenue"]
        serialized = {
            key: _plain(value) if isinstance(value, Counter) else value
            for key, value in row.items()
        }
        serialized["crop_revenue"] = sum(revenue[crop] for crop in CROPS)
        serialized["animal_revenue"] = sum(revenue[item] for item in ANIMAL_PRODUCTS)
        serialized["total_revenue"] = sum(revenue.values())
        output[name] = serialized
    return output


def _inventory_value(final_state):
    obs = final_state.observation
    private = obs["private"]
    prices = obs["market"]["prices"]
    quantity = Counter({item: private["shed"].get(item, 0) for item in SELLABLE})
    for inventory in private["inventories"]:
        for item in SELLABLE:
            quantity[item] += inventory.get(item, 0)
    return sum(quantity[item] * prices.get(item, 0) for item in SELLABLE), _plain(quantity)


def _final_animals(final_state):
    obs = final_state.observation
    player = int(obs["player"])
    farm = obs["farms"][player]
    private = obs["private"]
    counts = Counter()
    for row in farm["tiles"]:
        for tile in row:
            if isinstance(tile, dict) and tile.get("animal"):
                counts[tile["animal"]] += 1
    for animal in ANIMALS:
        counts[animal] += private["shed"].get(animal, 0)
        counts[animal] += sum(inv.get(animal, 0) for inv in private["inventories"])
    return counts


def _routing_summary(replay, player):
    analysis = _field_analysis(replay, [player])[player]
    rows = analysis["daily"][10:30]
    counts = Counter()
    responsibilities = Counter()
    crossings = 0
    shed_entries = 0
    for row in rows:
        counts.update(row["counts"])
        responsibilities.update(row["responsibilities"])
        for worker in row["workers"]:
            crossings += worker["quadrant_crossings"]
            shed_entries += worker["shed_entries"]
    total = counts["total"]
    productive = counts["productive"]
    return {
        "counts": _plain(counts),
        "responsibilities": _plain(responsibilities),
        "worker_turns": total,
        "productive_rate": productive / max(1, total),
        "idle_rate": counts["pass"] / max(1, total),
        "movement_rate": counts["movement"] / max(1, total),
        "logistics_tax_rate": counts["logistics"] / max(1, total),
        "movement_per_productive": counts["movement"] / max(1, productive),
        "territory_crossings": crossings,
        "shed_entries": shed_entries,
        "invalid_actions": counts["invalid"],
    }


def _cash_wave_metrics(replay, player):
    """Compact cohort/liquidation/reinvestment metrics for search-scale runs."""

    transitions = []
    for index in range(1, len(replay["steps"])):
        previous, current = replay["steps"][index - 1], replay["steps"][index]
        obs = previous[0]["observation"]
        ledgers, mismatch = _transition_ledger(previous, current, replay["configuration"])
        if mismatch:
            raise AssertionError(mismatch[:2])
        ledger = ledgers[player]
        action = current[player].get("action") or {}
        requested = [action.get("farmer", ["PASS"]), *action.get("hands", [])]
        ops = Counter(value[0] for value in requested if isinstance(value, list) and value)
        crop_revenue = sum(ledger["sale_revenue"][crop] for crop in CROPS)
        crop_quantity = sum(ledger["sale_quantity"][crop] for crop in CROPS)
        seed_spend = sum(ledger["seed_spend"].values())
        productive_spend = (
            seed_spend + sum(ledger["animal_spend"].values())
            + ledger["land_spend"] + ledger["labor_spend"]
        )
        transitions.append({
            "step": int(obs["step"]), "day": int(obs["day"]), "hour": int(obs["hour"]),
            "crop_revenue": crop_revenue, "crop_quantity": crop_quantity,
            "sale_revenue": _plain(ledger["sale_revenue"]),
            "sale_quantity": _plain(ledger["sale_quantity"]),
            "seed_spend": seed_spend, "productive_spend": productive_spend,
            "plant_actions": sum(ledger["plant_quantity"].values()),
            "harvest_quantity": sum(ledger["harvest_quantity"][crop] for crop in CROPS),
            "water_actions": ops["WATER"], "harvest_actions": ops["HARVEST"],
        })

    output = {}
    for name, (start_day, end_day) in {
        "wave1": (8, 13), "wave2": (16, 22), "wave3": (23, 29),
    }.items():
        rows = [row for row in transitions if start_day <= row["day"] <= end_day]
        sale_rows = [row for row in rows if row["crop_revenue"] > 0]
        groups = []
        for row in sale_rows:
            if not groups or row["step"] - groups[-1][-1]["step"] > 8:
                groups.append([])
            groups[-1].append(row)
        major = max(groups, key=lambda group: sum(row["crop_revenue"] for row in group), default=[])
        if major:
            first_step, last_step = major[0]["step"], major[-1]["step"]
            next_spend = next(
                (row["step"] for row in transitions if row["step"] >= last_step and row["productive_spend"] > 0),
                None,
            )
            reinvest = {
                str(turns): sum(
                    row["productive_spend"] for row in transitions
                    if last_step <= row["step"] <= last_step + turns
                )
                for turns in (3, 6, 12)
            }
        else:
            first_step = last_step = next_spend = None
            reinvest = {"3": 0, "6": 0, "12": 0}
        seed_spend = sum(row["seed_spend"] for row in rows)
        crop_revenue = sum(row["crop_revenue"] for row in rows)
        crop_actions = sum(
            row["plant_actions"] + row["water_actions"] + row["harvest_actions"]
            for row in rows
        )
        output[name] = {
            "window": [start_day, end_day],
            "planted_tiles": sum(row["plant_actions"] for row in rows),
            "maintenance_actions": sum(row["water_actions"] for row in rows),
            "harvest_actions": sum(row["harvest_actions"] for row in rows),
            "harvest_quantity": sum(row["harvest_quantity"] for row in rows),
            "crop_liquidation_quantity": sum(row["crop_quantity"] for row in rows),
            "crop_liquidation_revenue": crop_revenue,
            "major_liquidation_first_step": first_step,
            "major_liquidation_last_step": last_step,
            "major_liquidation_revenue": sum(row["crop_revenue"] for row in major),
            "major_liquidation_products": _plain(sum((Counter(row["sale_revenue"]) for row in major), Counter())),
            "cash_idle_turns": None if next_spend is None or last_step is None else next_spend - last_step,
            "productive_reinvestment": reinvest,
            "reinvestment_fraction_6_turns": reinvest["6"] / max(1, sum(row["crop_revenue"] for row in major)),
            "seed_spend": seed_spend,
            "wave_roi": (crop_revenue - seed_spend) / max(1, seed_spend),
            "profit_per_crop_worker_action": (crop_revenue - seed_spend) / max(1, crop_actions),
            "crop_worker_actions": crop_actions,
        }
    return output


def _run(job):
    candidate, path, group, opponent, opponent_spec, seed, seat, schedule = job
    if isinstance(path, dict) and "multiwave_config" in path:
        raw = run_path(
            str(ROOT / "agents/multiwave_candidate.py"),
            init_globals={"MULTIWAVE_CONFIG": path["multiwave_config"]},
        )["agent"]
        recorded_path = f"multiwave:{candidate}"
    else:
        raw = run_path(str(ROOT / path))["agent"]
        recorded_path = path
    rival = _load_opponent(opponent_spec)
    calls = 0

    def checked(obs):
        nonlocal calls
        action = raw(obs)
        _validate_action(obs, action)
        calls += 1
        return action

    pair = [rival, rival]
    pair[seat] = checked
    env = make(
        "kaggriculture",
        configuration={"episodeSteps": 720, "seed": int(seed)},
        debug=True,
    )
    if schedule is None:
        env.run(pair)
    else:
        _run_with_fixed_shops(env, pair, schedule)
    final = env.steps[-1]
    statuses = [state.status for state in final]
    if len(env.steps) != 720 or statuses != ["DONE", "DONE"] or calls != 719:
        raise RuntimeError((candidate, opponent, seed, seat, len(env.steps), statuses, calls))
    replay = env.toJSON()
    economics = _economic_windows(replay, seat)
    lifecycle_mid = lifecycle_metrics(replay, seat, 10, 20)
    lifecycle_late = lifecycle_metrics(replay, seat, 21, 29)
    routing = _routing_summary(replay, seat)
    cash_waves = _cash_wave_metrics(replay, seat)
    stranded_value, stranded = _inventory_value(final[seat])
    bought = Counter(economics["full"]["animal_spend"])
    # animal_spend stores coins; use actual BUY_ANIMAL quantities from actions.
    bought = Counter()
    for states in replay["steps"][1:]:
        action = states[seat].get("action") or {}
        for order in action.get("market", []):
            if isinstance(order, list) and len(order) >= 3 and order[0] == "BUY_ANIMAL":
                bought[order[1]] += int(order[2])
    remaining_animals = _final_animals(final[seat])
    losses = {animal: max(0, bought[animal] - remaining_animals[animal]) for animal in ANIMALS}
    money = float(final[seat].reward)
    opponent_money = float(final[1 - seat].reward)
    full_revenue = economics["full"]["total_revenue"]
    crop_actions = routing["responsibilities"].get("crop", 0)
    animal_actions = routing["responsibilities"].get("animal", 0)
    checkpoints = {}
    for day in (2, 4, 6, 8, 10, 11, 12, 15, 20, 25, 29):
        index = min(day * 24 + 23, len(replay["steps"]) - 1)
        obs = replay["steps"][index][0]["observation"]
        farm = obs["farms"][seat]
        crops = Counter()
        animals = Counter()
        productive = 0
        for tile_row in farm["tiles"]:
            for tile in tile_row:
                if not isinstance(tile, dict):
                    continue
                if tile.get("kind") == "PLANT":
                    crops[tile["crop"]] += 1
                    productive += 1
                elif tile.get("animal"):
                    animals[tile["animal"]] += 1
                    productive += 1
        checkpoints[str(day)] = {
            "bank": float(farm["money"]),
            "quadrants": len(farm.get("unlocked_quadrants", [])),
            "hands": len(farm.get("hands", [])),
            "productive_tiles": productive,
            "crops": _plain(crops),
            "animals": _plain(animals),
        }
    land_days = []
    sale_windows = []
    for index in range(1, len(replay["steps"])):
        previous = replay["steps"][index - 1]
        current = replay["steps"][index]
        obs = previous[0]["observation"]
        ledgers, _ = _transition_ledger(previous, current, replay["configuration"])
        ledger = ledgers[seat]
        land_days.extend([int(obs["day"])] * int(ledger["land_count"]))
        revenue = sum(ledger["sale_revenue"].values())
        if revenue >= 1000:
            sale_windows.append({
                "day": int(obs["day"]), "hour": int(obs["hour"]),
                "revenue": revenue, "products": _plain(ledger["sale_revenue"]),
            })
    return {
        "candidate": candidate, "path": recorded_path, "group": group,
        "opponent": opponent, "seed": int(seed), "seat": seat,
        "money": money, "opponent_money": opponent_money,
        "advantage": money - opponent_money,
        "shop_schedule": schedule,
        "calls": calls, "runtime_failures": 0, "semantic_failures": 0,
        "stranded_value": stranded_value, "stranded": stranded,
        "animals_bought": _plain(bought), "animals_remaining": _plain(remaining_animals),
        "livestock_losses": losses,
        "economics": economics,
        "lifecycle_day10_20": lifecycle_mid,
        "lifecycle_day21_29": lifecycle_late,
        "routing_day10_29": routing,
        "money_per_worker_turn": full_revenue / max(1, routing["worker_turns"]),
        "crop_revenue_per_crop_action": economics["full"]["crop_revenue"] / max(1, crop_actions),
        "animal_revenue_per_animal_action": economics["full"]["animal_revenue"] / max(1, animal_actions),
        "checkpoints": checkpoints,
        "land_days": land_days,
        "major_sale_windows": sale_windows,
        "cash_waves": cash_waves,
    }


def _summary(games):
    advantages = [row["advantage"] for row in games]
    wins = sum(value > 0 for value in advantages)
    losses = sum(value < 0 for value in advantages)
    ties = len(games) - wins - losses
    paired = {}
    for row in games:
        paired.setdefault((row["opponent"], row["seed"]), []).append(row["advantage"])
    mean = lambda fn: statistics.fmean(fn(row) for row in games)
    mid = lambda row: row["lifecycle_day10_20"]
    late = lambda row: row["lifecycle_day21_29"]
    return {
        "games": len(games), "wins": wins, "losses": losses, "ties": ties,
        "score_rate": (wins + 0.5 * ties) / len(games),
        "average_money": mean(lambda row: row["money"]),
        "average_advantage": statistics.fmean(advantages),
        "p10_paired_advantage": _percentile(
            [statistics.fmean(values) for values in paired.values()], 0.10
        ),
        "money_stddev": statistics.pstdev(row["money"] for row in games),
        "average_crop_harvests_day10_20": mean(lambda row: mid(row)["total_harvest_actions"]),
        "average_crop_harvests_day21_29": mean(lambda row: late(row)["total_harvest_actions"]),
        "average_all_crop_harvests_day10_29": mean(
            lambda row: mid(row)["total_harvest_actions"] + late(row)["total_harvest_actions"]
        ),
        "average_crop_revenue_day10_20": mean(lambda row: row["economics"]["day10_20"]["crop_revenue"]),
        "average_crop_revenue_day21_29": mean(lambda row: row["economics"]["day21_29"]["crop_revenue"]),
        "average_full_crop_revenue": mean(lambda row: row["economics"]["full"]["crop_revenue"]),
        "average_full_animal_revenue": mean(lambda row: row["economics"]["full"]["animal_revenue"]),
        "average_critical_watering_miss_rate_day10_20": mean(lambda row: mid(row)["critical_watering_miss_rate"]),
        "average_harvest_delay_day10_20": mean(lambda row: mid(row)["average_harvest_delay_turns"] or 0),
        "average_replant_delay_day10_20": mean(lambda row: mid(row)["average_replant_delay_turns"] or 0),
        "average_movement_per_crop_cycle_day10_20": mean(lambda row: mid(row)["movement_per_crop_cycle"]),
        "average_completed_cycles_per_worker_day_day10_20": mean(lambda row: mid(row)["completed_cycles_per_worker_day"]),
        "average_lifecycle_debt_day10_20": mean(lambda row: mid(row)["lifecycle_debt_tile_hours"]),
        "average_productive_crop_tile_hours_day10_20": mean(lambda row: mid(row)["productive_crop_tile_hours"]),
        "average_worker_idle_rate": mean(lambda row: row["routing_day10_29"]["idle_rate"]),
        "average_logistics_tax_rate": mean(lambda row: row["routing_day10_29"]["logistics_tax_rate"]),
        "average_territory_crossings": mean(lambda row: row["routing_day10_29"]["territory_crossings"]),
        "average_shed_entries": mean(lambda row: row["routing_day10_29"]["shed_entries"]),
        "average_animal_service_actions": mean(lambda row: row["economics"]["full"]["animal_service_actions"]),
        "average_money_per_worker_turn": mean(lambda row: row["money_per_worker_turn"]),
        "average_crop_revenue_per_crop_action": mean(lambda row: row["crop_revenue_per_crop_action"]),
        "average_animal_revenue_per_animal_action": mean(lambda row: row["animal_revenue_per_animal_action"]),
        "total_invalid_actions": sum(row["routing_day10_29"]["invalid_actions"] for row in games),
        "total_livestock_losses": sum(sum(row["livestock_losses"].values()) for row in games),
        "max_stranded_value": max(row["stranded_value"] for row in games),
    }


def _candidate_rows(games, candidates):
    rows = []
    control_name = "B0" if "B0" in candidates else "R0_803"
    controls = {
        (row["group"], row["opponent"], row["seed"], row["seat"]): row
        for row in games if row["candidate"] == control_name
    }
    weights = {
        "jay_pedro": 0.40, "real_losses": 0.20,
        "real_replay": 0.45, "direct": 0.20,
        "direct_fixed": 0.15, "direct_natural": 0.15,
        "replay_pool": 0.20, "hard_pool": 0.05,
        "red_team": 0.05,
    }
    for candidate in candidates:
        selected = [row for row in games if row["candidate"] == candidate]
        groups = {
            group: _summary([row for row in selected if row["group"] == group])
            for group in sorted({row["group"] for row in selected})
        }
        matchups = {
            opponent: _summary([row for row in selected if row["opponent"] == opponent])
            for opponent in sorted({row["opponent"] for row in selected})
        }
        paired_delta = Counter()
        paired_count = Counter()
        for row in selected:
            key = (row["group"], row["opponent"], row["seed"], row["seat"])
            control = controls.get(key)
            if control is not None:
                paired_delta[row["group"]] += row["money"] - control["money"]
                paired_count[row["group"]] += 1
        average_delta = {
            group: paired_delta[group] / paired_count[group]
            for group in paired_count
        }
        paired_deltas = [
            row["money"] - controls[(row["group"], row["opponent"], row["seed"], row["seat"])]["money"]
            for row in selected
            if (row["group"], row["opponent"], row["seed"], row["seat"]) in controls
        ]
        used_weight = sum(weights.get(group, 0) for group in average_delta)
        transfer_score = (
            sum(weights.get(group, 0) * value for group, value in average_delta.items()) / used_weight
            if used_weight else None
        )
        rows.append({
            "candidate": candidate,
            "path": CANDIDATES[candidate],
            "overall": _summary(selected),
            "groups": groups,
            "matchups": matchups,
            "paired_money_delta_vs_B0": average_delta,
            "paired_delta_p10_vs_control": _percentile(paired_deltas, 0.10),
            "paired_delta_median_vs_control": statistics.median(paired_deltas) if paired_deltas else None,
            "real_transfer_score_delta": transfer_score,
        })
    return rows


def _build_jobs(stage, candidates, seeds):
    jobs = []
    def add(candidate, group, opponent, spec, seed, schedule):
        for seat in (0, 1):
            jobs.append((candidate, CANDIDATES[candidate], group, opponent, spec, seed, seat, schedule))

    if stage == "rng_audit":
        for candidate in candidates:
            for seed in seeds:
                add(
                    candidate, "rng_fixed", "current_best_fixed",
                    "agents/lifecycle_lc_combined.py", seed,
                    _independent_shop_schedule(seed),
                )
                add(
                    candidate, "rng_natural", "current_best_natural",
                    "agents/lifecycle_lc_combined.py", seed, None,
                )
        return jobs

    real_ids = (92008833, 92010768) if stage == "screen" else LOSS_EPISODES
    for candidate in candidates:
        for episode_id in real_ids:
            source = _source_replay(episode_id)
            group = "jay_pedro" if episode_id in {92008833, 92010768} else "real_losses"
            add(
                candidate, group, REAL_NAMES[episode_id], _trace_spec(episode_id),
                int(source["info"]["seed"]), _recorded_shop_schedule(source),
            )
        if stage in {"selection", "heldout"}:
            current_path = "agents/lifecycle_lc_combined.py"
            direct_count = 3 if stage == "selection" else 8
            for seed in seeds[:direct_count]:
                add(candidate, "direct", "current_best", current_path, seed, _independent_shop_schedule(seed))
            pool = REPLAY_DERIVED if stage == "selection" else HARD_POOL
            pool_count = 1 if stage == "selection" else 3
            for opponent, spec in pool.items():
                for seed in seeds[:pool_count]:
                    group = "replay_pool" if opponent in REPLAY_DERIVED else "hard_pool"
                    add(candidate, group, opponent, spec, seed, _independent_shop_schedule(seed))
    return jobs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("screen", "diagnosis", "selection", "heldout", "rng_audit"), default="screen")
    parser.add_argument("--candidates", default="B0,B1_value,B2_predictive,B3_adjacent,B5_phase,B6_cows6,B6_cows7,B6_cows8,B_market")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--seed-start", type=int, default=941000)
    parser.add_argument("--output")
    args = parser.parse_args()
    candidates = tuple(value for value in args.candidates.split(",") if value)
    for candidate in candidates:
        if candidate not in CANDIDATES or not (ROOT / CANDIDATES[candidate]).exists():
            raise FileNotFoundError(candidate)
    seed_count = 3 if args.stage == "selection" else 8
    seeds = tuple(range(args.seed_start, args.seed_start + seed_count))
    jobs = _build_jobs(args.stage, candidates, seeds)
    games = []
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(_run, job) for job in jobs]
        for index, future in enumerate(as_completed(futures), 1):
            games.append(future.result())
            if index % 24 == 0 or index == len(jobs):
                print(f"{args.stage}: {index}/{len(jobs)}", flush=True)
    payload = {
        "schema_version": 1,
        "stage": args.stage,
        "shop_control": "recorded schedules for real traces; independent common schedules for fresh games",
        "seed_partition": {"start": args.seed_start, "count": seed_count},
        "candidates": _candidate_rows(games, candidates),
        "games": games,
    }
    output = Path(args.output) if args.output else ROOT / "experiments" / f"epic_{args.stage}.json"
    output.write_text(json.dumps(payload, indent=2) + "\n")
    print(output)
    for row in payload["candidates"]:
        summary = row["overall"]
        print(
            row["candidate"], f"{summary['wins']}/{summary['losses']}/{summary['ties']}",
            f"money={summary['average_money']:.0f}", f"adv={summary['average_advantage']:+.0f}",
            f"delta={row['real_transfer_score_delta'] or 0:+.0f}",
            f"h={summary['average_all_crop_harvests_day10_29']:.1f}",
            f"crop={summary['average_full_crop_revenue']:.0f}",
            f"crit={summary['average_critical_watering_miss_rate_day10_20']:.2%}",
            f"rdelay={summary['average_replant_delay_day10_20']:.1f}",
        )


if __name__ == "__main__":
    main()
