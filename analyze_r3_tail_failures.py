"""Turn-level diagnosis for the frozen leaderboard R3 tail.

The script intentionally reruns only games already identified by the held-out
artifact: every R3 loss and every R3-vs-R0 paired money delta below -$3,000.
It compares the frozen R3 and lifecycle agents under the identical opponent,
seed, seat and shop schedule, then emits compact daily and decision timelines.
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
from pathlib import Path
from runpy import run_path

from kaggle_environments import make
from kaggle_environments.envs.kaggriculture import kaggriculture as game

from analyze_crop_lifecycle import lifecycle_metrics
from analyze_epic_next_stage import _action_effects, _snapshot
from analyze_top_player_replays import _transition_ledger
from run_epic_experiments import _run_with_fixed_shops
from run_leaderboard_breakthrough import HELDOUT_REPLAY_CASES, RED_TEAM, _trace_spec
from run_post_opening_validation import _load_opponent
from test_economic_agents import _validate_action


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "experiments" / "leaderboard_breakthrough_heldout.json"
OUTPUT = ROOT / "experiments" / "r3_tail_diagnosis.json"
AGENTS = {
    "L798": "agents/lifecycle_lc_combined.py",
    "R3": "agents/leaderboard_r3_cow6_capital.py",
}
CROPS = tuple(game.CROPS)
ANIMAL_PRODUCTS = ("EGG", "MILK", "WOOL", "FERTILIZER")
DESTRUCTIVE = tuple(crop for crop, data in game.CROPS.items() if not data["ongoing"])
CHECKPOINT_DAYS = (2, 4, 6, 8, 10, 11, 12, 15, 20, 25, 29)


def _plain(value):
    return {key: value[key] for key in sorted(value) if value[key]}


def _percentile(values, fraction):
    values = sorted(values)
    if not values:
        return None
    point = fraction * (len(values) - 1)
    lower = int(point)
    upper = min(len(values) - 1, lower + 1)
    return values[lower] * (upper - point) + values[upper] * (point - lower)


def _inventory(state):
    private = state["observation"]["private"]
    values = Counter(private.get("shed", {}))
    for carried in private.get("inventories", []):
        values.update(carried)
    return _plain(values)


def _daily_template(day):
    return {
        "day": day,
        "bank_start": None,
        "bank_end": None,
        "revenue": Counter(),
        "spending": Counter(),
        "sales": Counter(),
        "harvests": Counter(),
        "plantings": Counter(),
        "max_hands": 0,
        "farm": {},
        "inventory": {},
        "prices_end": {},
        "shops_end": [],
        "major_sales": [],
        "investments": [],
    }


def _daily_timeline(replay, player):
    rows = [_daily_template(day) for day in range(30)]
    cumulative_revenue = Counter()
    cumulative_spending = Counter()
    mismatches = []
    for states in replay["steps"]:
        obs = states[0]["observation"]
        day = min(29, int(obs["day"]))
        farm = obs["farms"][player]
        row = rows[day]
        if row["bank_start"] is None:
            row["bank_start"] = float(farm["money"])
        row["bank_end"] = float(farm["money"])
        row["max_hands"] = max(row["max_hands"], len(farm.get("hands", [])))
        row["farm"] = {
            key: value for key, value in _snapshot(obs, player).items()
            if key not in {"tiles", "workers", "unlocked_quadrants", "watered_crops"}
        }
        row["inventory"] = _inventory(states[player])
        row["prices_end"] = dict(obs["market"]["prices"])
        row["shops_end"] = list(obs["town"]["unlocked_shops"])
    for index in range(1, len(replay["steps"])):
        previous = replay["steps"][index - 1]
        current = replay["steps"][index]
        obs = previous[0]["observation"]
        day, hour = int(obs["day"]), int(obs["hour"])
        ledger, errors = _transition_ledger(previous, current, replay["configuration"])
        mismatches.extend(errors)
        ledger = ledger[player]
        row = rows[day]
        row["revenue"].update(ledger["sale_revenue"])
        row["sales"].update(ledger["sale_quantity"])
        row["harvests"].update(ledger["harvest_quantity"])
        row["plantings"].update(ledger["plant_quantity"])
        spend = {
            "seed": sum(ledger["seed_spend"].values()),
            "feed": sum(ledger["product_spend"].values()),
            "animal": sum(ledger["animal_spend"].values()),
            "land": ledger["land_spend"],
            "labor": ledger["labor_spend"],
        }
        row["spending"].update(spend)
        sale_revenue = sum(ledger["sale_revenue"].values())
        if sale_revenue >= 500:
            row["major_sales"].append({
                "step": int(obs["step"]), "hour": hour,
                "revenue": sale_revenue,
                "products": _plain(ledger["sale_revenue"]),
                "quantities": _plain(ledger["sale_quantity"]),
                "prices": {
                    product: int(obs["market"]["prices"][product])
                    for product in ledger["sale_quantity"]
                },
            })
        if spend["land"] or spend["animal"] or spend["labor"] >= 100:
            row["investments"].append({
                "step": int(obs["step"]), "hour": hour,
                "bank_before": float(obs["farms"][player]["money"]),
                "bank_after": float(current[0]["observation"]["farms"][player]["money"]),
                **spend,
                "animals": _plain(ledger["animal_quantity"]),
            })
    serialized = []
    for row in rows:
        for key in ("revenue", "spending", "sales", "harvests", "plantings"):
            row[key] = _plain(row[key])
        cumulative_revenue.update(row["revenue"])
        cumulative_spending.update(row["spending"])
        row["crop_revenue"] = sum(row["revenue"].get(crop, 0) for crop in CROPS)
        row["animal_revenue"] = sum(row["revenue"].get(item, 0) for item in ANIMAL_PRODUCTS)
        row["total_revenue"] = sum(row["revenue"].values())
        row["total_spending"] = sum(row["spending"].values())
        row["cumulative_revenue"] = sum(cumulative_revenue.values())
        row["cumulative_crop_revenue"] = sum(cumulative_revenue[crop] for crop in CROPS)
        row["cumulative_animal_revenue"] = sum(cumulative_revenue[item] for item in ANIMAL_PRODUCTS)
        row["cumulative_spending"] = sum(cumulative_spending.values())
        serialized.append(row)
    return serialized, mismatches


def _decision_events(replay, player):
    events = []
    for index in range(1, len(replay["steps"])):
        previous = replay["steps"][index - 1]
        current = replay["steps"][index]
        obs = previous[0]["observation"]
        effects = _action_effects(previous, current, player, replay["configuration"])
        farm = obs["farms"][player]
        rival = obs["farms"][1 - player]
        positions = [tuple(farm["farmer"]), *map(tuple, farm.get("hands", []))]
        action = current[player].get("action") or {}
        unit_actions = [action.get("farmer", ["PASS"]), *action.get("hands", [])]
        for unit, (position, unit_action) in enumerate(zip(positions, unit_actions)):
            op = unit_action[0] if unit_action else "PASS"
            tile = farm["tiles"][position[1]][position[0]]
            if not isinstance(tile, dict) or tile.get("kind") != "PLANT":
                continue
            crop = tile["crop"]
            data = game.CROPS[crop]
            age = int(obs["day"] - tile["planted_day"])
            final_water_opportunity = (
                crop in DESTRUCTIVE
                and age == data["max_yield_day"]
                and tile.get("yield_units", 0) > 0
                and not tile.get("watered_today", False)
                and tile.get("yield_units", 0) < data["max_yield"]
            )
            if op not in {"WATER", "HARVEST"} or not (final_water_opportunity or op == "HARVEST"):
                continue
            rival_mature = Counter()
            rival_supply = Counter()
            for rival_row in rival["tiles"]:
                for rival_tile in rival_row:
                    if isinstance(rival_tile, dict) and rival_tile.get("kind") == "PLANT":
                        rival_supply[rival_tile["crop"]] += int(rival_tile.get("yield_units", 0))
                        if rival_tile.get("yield_units", 0) > 0:
                            rival_mature[rival_tile["crop"]] += 1
            price = int(obs["market"]["prices"][crop])
            held = int(tile.get("yield_units", 0))
            land_index = len(farm.get("unlocked_quadrants", [])) - 1
            next_land = (1000, 2000, 4000)[land_index] if land_index < 3 else None
            events.append({
                "step": int(obs["step"]), "day": int(obs["day"]), "hour": int(obs["hour"]),
                "unit": unit, "position": list(position), "op": op, "crop": crop,
                "age": age, "yield_before": held, "watered_before": bool(tile.get("watered_today")),
                "final_water_opportunity": final_water_opportunity,
                "price": price, "market_inventory": int(obs["market"]["inventory"][crop]),
                "wait_marginal_value": price if final_water_opportunity else 0,
                "harvest_value_now": held * price,
                "bank": float(farm["money"]), "quadrants": len(farm.get("unlocked_quadrants", [])),
                "next_land_cost": next_land,
                "harvest_unlocks_land": bool(next_land and farm["money"] < next_land <= farm["money"] + held * price),
                "opponent_mature_tiles": rival_mature[crop],
                "opponent_held_supply": rival_supply[crop],
                "shops": list(obs["town"]["unlocked_shops"]),
                "successful": any(event["unit"] == unit and event["op"] == op for event in effects["events"]),
            })
    return events


def _first_durable(rows, key, threshold=0):
    for index, row in enumerate(rows):
        if row[key] > threshold and all(later[key] > threshold for later in rows[index:]):
            return row["day"]
    return None


def _game_diagnosis(candidate, opponent):
    gaps = []
    cumulative_harvest_gap = 0
    for day, (ours, rival) in enumerate(zip(candidate, opponent)):
        cumulative_harvest_gap += sum(rival["harvests"].values()) - sum(ours["harvests"].values())
        gaps.append({
            "day": day,
            "bank_gap": rival["bank_end"] - ours["bank_end"],
            "revenue_gap": rival["cumulative_revenue"] - ours["cumulative_revenue"],
            "crop_revenue_gap": rival["cumulative_crop_revenue"] - ours["cumulative_crop_revenue"],
            "animal_revenue_gap": rival["cumulative_animal_revenue"] - ours["cumulative_animal_revenue"],
            "spending_gap": rival["cumulative_spending"] - ours["cumulative_spending"],
            "productive_tile_gap": rival["farm"].get("productive_tiles", 0) - ours["farm"].get("productive_tiles", 0),
            "harvest_gap": cumulative_harvest_gap,
        })
    daily_damage = [
        (rival["total_revenue"] - ours["total_revenue"], day)
        for day, (ours, rival) in enumerate(zip(candidate, opponent))
    ]
    largest, largest_day = max(daily_damage)
    return {
        "first_durable_bank_lead_day": _first_durable(gaps, "bank_gap"),
        "first_durable_revenue_lead_day": _first_durable(gaps, "revenue_gap"),
        "first_durable_crop_lead_day": _first_durable(gaps, "crop_revenue_gap"),
        "first_durable_productive_tile_lead_day": _first_durable(gaps, "productive_tile_gap"),
        "largest_daily_revenue_divergence": largest,
        "largest_daily_revenue_divergence_day": largest_day,
        "gaps": gaps,
    }


def _run(job):
    agent_name, agent_path, kind, opponent_name, opponent_spec, seed, seat, schedule = job
    raw = run_path(str(ROOT / agent_path))["agent"]
    rival = _load_opponent(opponent_spec)
    calls = 0

    def checked(obs):
        nonlocal calls
        result = raw(obs)
        _validate_action(obs, result)
        calls += 1
        return result

    pair = [rival, rival]
    pair[seat] = checked
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": int(seed)}, debug=True)
    if schedule is None:
        env.run(pair)
    else:
        _run_with_fixed_shops(env, pair, schedule)
    if len(env.steps) != 720 or calls != 719 or [s.status for s in env.steps[-1]] != ["DONE", "DONE"]:
        raise RuntimeError((job, len(env.steps), calls, [s.status for s in env.steps[-1]]))
    replay = env.toJSON()
    ours, ours_errors = _daily_timeline(replay, seat)
    opponent, opponent_errors = _daily_timeline(replay, 1 - seat)
    return {
        "agent": agent_name, "path": agent_path, "tail_kind": kind,
        "opponent": opponent_name, "seed": int(seed), "seat": int(seat),
        "calls": calls,
        "money": float(env.steps[-1][seat].reward),
        "opponent_money": float(env.steps[-1][1 - seat].reward),
        "advantage": float(env.steps[-1][seat].reward - env.steps[-1][1 - seat].reward),
        "daily": ours, "opponent_daily": opponent,
        "decision_events": _decision_events(replay, seat),
        "diagnosis": _game_diagnosis(ours, opponent),
        "lifecycle_day10_20": lifecycle_metrics(replay, seat, 10, 20),
        "lifecycle_day21_29": lifecycle_metrics(replay, seat, 21, 29),
        "financial_mismatches": ours_errors + opponent_errors,
    }


def _jobs():
    payload = json.loads(SOURCE.read_text())
    games = payload["games"]
    r3 = [row for row in games if row["candidate"] == "R3_c6_capital"]
    r0 = {
        (row["group"], row["opponent"], row["seed"], row["seat"]): row
        for row in games if row["candidate"] == "R0_803"
    }
    selected = {}
    for row in r3:
        key = (row["group"], row["opponent"], row["seed"], row["seat"])
        paired_delta = row["money"] - r0[key]["money"]
        if row["advantage"] < 0:
            selected[key] = "heldout_loss"
        if paired_delta <= -3000:
            selected[key] = "loss_and_negative_delta" if key in selected else "negative_paired_delta"
    jobs = []
    for (group, opponent, seed, seat), kind in sorted(selected.items()):
        original = next(row for row in r3 if (row["group"], row["opponent"], row["seed"], row["seat"]) == (group, opponent, seed, seat))
        if group == "real_replay":
            _, replay_path, player = HELDOUT_REPLAY_CASES[opponent]
            opponent_spec = _trace_spec(replay_path, player)
        else:
            opponent_spec = RED_TEAM[opponent]
        schedule = original["shop_schedule"]
        if schedule is not None:
            schedule = {int(day): shops for day, shops in schedule.items()}
        for agent_name, path in AGENTS.items():
            jobs.append((agent_name, path, kind, opponent, opponent_spec, seed, seat, schedule))
    return selected, jobs


def _paired_summary(games):
    by_key = {}
    for row in games:
        by_key.setdefault((row["tail_kind"], row["opponent"], row["seed"], row["seat"]), {})[row["agent"]] = row
    pairs = []
    for key, values in sorted(by_key.items()):
        if set(values) != set(AGENTS):
            continue
        r3, baseline = values["R3"], values["L798"]
        delta = r3["money"] - baseline["money"]
        classification = "R3-specific regression" if delta < -1000 else "new mechanism partially works" if delta > 1000 else "shared weakness"
        pairs.append({
            "tail_kind": key[0], "opponent": key[1], "seed": key[2], "seat": key[3],
            "r3_money": r3["money"], "lifecycle_money": baseline["money"],
            "r3_delta_vs_lifecycle": delta, "classification": classification,
            "r3_advantage": r3["advantage"], "lifecycle_advantage": baseline["advantage"],
        })
    deltas = [row["r3_delta_vs_lifecycle"] for row in pairs]
    return pairs, {
        "pairs": len(pairs), "average_delta": statistics.fmean(deltas),
        "median_delta": statistics.median(deltas), "p10_delta": _percentile(deltas, .10),
        "r3_specific_regressions": sum(row["classification"] == "R3-specific regression" for row in pairs),
        "shared_weaknesses": sum(row["classification"] == "shared weakness" for row in pairs),
        "partial_improvements": sum(row["classification"] == "new mechanism partially works" for row in pairs),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    selected, jobs = _jobs()
    games = []
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(_run, job) for job in jobs]
        for index, future in enumerate(as_completed(futures), 1):
            games.append(future.result())
            if index % 8 == 0 or index == len(jobs):
                print(f"diagnosis {index}/{len(jobs)}", flush=True)
    pairs, summary = _paired_summary(games)
    payload = {
        "schema_version": 1,
        "source_artifact": str(SOURCE.relative_to(ROOT)),
        "selection": {
            "heldout_losses": sum("loss" in value for value in selected.values()),
            "large_negative_paired_deltas": sum("negative" in value for value in selected.values()),
            "unique_games": len(selected), "threshold": -3000,
        },
        "agents": AGENTS,
        "paired_summary": summary,
        "pairs": pairs,
        "games": sorted(games, key=lambda row: (row["opponent"], row["seed"], row["seat"], row["agent"])),
    }
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(args.output)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
