"""Strict K0-K9 evaluation for the V27 replay-backbone research."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import json
import statistics
from pathlib import Path
from runpy import run_path

from kaggle_environments import make

from run_epic_experiments import _independent_shop_schedule, _recorded_shop_schedule, _run_with_fixed_shops
from run_leaderboard_breakthrough import HELDOUT_REPLAY_CASES, REPLAY_CASES
from run_post_opening_validation import _load_opponent


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "experiments/v27_replay_backbone_results.json"
STAGES = {
    "K0": "agents/v27_k0_raw.py",
    "K1": "agents/v27_k1_stable.py",
    "K2": "agents/v27_k2_aligned.py",
    "K3": "agents/v27_k3_weed.py",
    "K4": "agents/v27_k4_capital.py",
    "K5": "agents/v27_k5_hire.py",
    "K6": "agents/v27_k6_safety.py",
    "K7": "agents/v27_k7_sell_order.py",
    "K8": "agents/v27_k8_sell_horizon.py",
    "K9": "agents/v27_k9_full.py",
}
FROZEN = {
    "803_opening": "agents/opening_public_front_cow8_day6.py",
    "lifecycle": "agents/lifecycle_lc_combined.py",
    "R3": "agents/leaderboard_r3_cow6_capital.py",
}
PRODUCTS = {"WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"}
ANIMALS = {"GOOSE", "COW", "SHEEP"}
UNIT_OPS = {"NORTH", "SOUTH", "EAST", "WEST", "PASS", "PLANT", "WATER", "HARVEST", "FERTILIZE", "DIG", "BUILD_COOP", "BUILD_PASTURE", "PICKUP", "DROP", "PLACE", "FEED", "CARE", "COLLECT_FERTILIZER"}
MARKET_OPS = {"HIRE", "BUY_LAND", "BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL"}


def _trace_spec(path, player):
    return f"trace:{ROOT / path}:{int(player)}"


def _percentile(values, fraction):
    if not values:
        return None
    values = sorted(values)
    point = fraction * (len(values) - 1)
    lower = int(point)
    weight = point - lower
    return values[lower] * (1 - weight) + values[min(lower + 1, len(values) - 1)] * weight


def _semantic_validate(obs, action):
    assert isinstance(action, dict) and set(action) == {"farmer", "hands", "market"}
    assert isinstance(action["farmer"], list) and action["farmer"] and action["farmer"][0] in UNIT_OPS
    assert isinstance(action["hands"], list)
    assert len(action["hands"]) == len(obs["farms"][obs["player"]]["hands"])
    for request in action["hands"]:
        assert isinstance(request, list) and request and request[0] in UNIT_OPS
    assert isinstance(action["market"], list) and len(action["market"]) <= 10
    for order in action["market"]:
        assert isinstance(order, list) and order and order[0] in MARKET_OPS
        if order[0] in {"BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL"}:
            assert len(order) == 3 and isinstance(order[2], int) and order[2] > 0


def _inventory_value(final_state):
    obs = final_state.observation
    private = obs["private"]
    prices = obs["market"]["prices"]
    quantity = Counter({item: private["shed"].get(item, 0) for item in PRODUCTS})
    for inventory in private["inventories"]:
        for item in PRODUCTS:
            quantity[item] += inventory.get(item, 0)
    return sum(quantity[item] * prices[item] for item in PRODUCTS), {item: quantity[item] for item in sorted(quantity) if quantity[item]}


def _farm_counts(farm):
    crops, animals = Counter(), Counter()
    weeds = 0
    for row in farm["tiles"]:
        for tile in row:
            if not isinstance(tile, dict):
                continue
            if tile.get("kind") == "PLANT":
                crops[tile["crop"]] += 1
            elif tile.get("kind") == "WEED":
                weeds += 1
            elif tile.get("animal"):
                animals[tile["animal"]] += 1
    return crops, animals, weeds


def _transition_metrics(replay, seat):
    sales = Counter()
    buys = Counter()
    hires = 0
    land_steps = []
    crop_deaths = 0
    for index in range(1, len(replay["steps"])):
        previous = replay["steps"][index - 1][0]["observation"]
        current = replay["steps"][index][0]["observation"]
        action = replay["steps"][index][seat].get("action") or {}
        for order in action.get("market", []):
            if not order:
                continue
            if order[0] == "SELL":
                # Exact realized revenue is bank-delta coupled; request value is
                # retained here while route telemetry stores exact simulation.
                sales[order[1]] += int(order[2])
            elif order[0] == "BUY_ANIMAL":
                buys[order[1]] += int(order[2])
            elif order[0] == "HIRE":
                hires += 1
            elif order[0] == "BUY_LAND":
                land_steps.append(index - 1)
        before = previous["farms"][seat]["tiles"]
        after = current["farms"][seat]["tiles"]
        for y in range(len(before)):
            for x in range(len(before[y])):
                if isinstance(before[y][x], dict) and before[y][x].get("kind") == "PLANT" and isinstance(after[y][x], dict) and after[y][x].get("kind") == "WEED":
                    crop_deaths += 1
    return {"sale_requests": dict(sales), "animal_buy_requests": dict(buys), "hire_requests": hires, "land_request_steps": land_steps, "crop_deaths": crop_deaths}


def _run(job):
    stage, path, group, opponent, opponent_spec, seed, seat, schedule, config_patch = job
    candidate = run_path(str(ROOT / path))["agent"]
    rival = _load_opponent(opponent_spec)
    calls = 0
    semantic_failures = []

    def checked(obs):
        nonlocal calls
        action = candidate(obs)
        try:
            _semantic_validate(obs, action)
        except Exception as error:
            semantic_failures.append({"step": int(obs["step"]), "error": repr(error), "action": action})
        calls += 1
        return action

    pair = [rival, rival]
    pair[seat] = checked
    configuration = {"episodeSteps": 720, "seed": int(seed), **dict(config_patch or {})}
    env = make("kaggriculture", configuration=configuration, debug=True)
    runtime_error = None
    try:
        if schedule is None:
            env.run(pair)
        else:
            _run_with_fixed_shops(env, pair, schedule)
    except Exception as error:
        runtime_error = repr(error)
    if runtime_error or len(env.steps) != 720:
        return {"stage": stage, "group": group, "opponent": opponent, "seed": seed, "seat": seat, "runtime_error": runtime_error or f"steps={len(env.steps)}", "semantic_failures": semantic_failures}
    final = env.steps[-1]
    replay = env.toJSON()
    value, stranded = _inventory_value(final[seat])
    crops, animals, weeds = _farm_counts(final[seat].observation["farms"][seat])
    transition = _transition_metrics(replay, seat)
    bought = Counter(transition["animal_buy_requests"])
    livestock_losses = {animal: max(0, bought[animal] - animals[animal]) for animal in ANIMALS}
    checkpoints = {}
    for day in (4, 6, 8, 10, 11, 15, 20, 25, 29):
        index = min(day * 24 + 23, 719)
        obs = replay["steps"][index][0]["observation"]
        farm = obs["farms"][seat]
        cc, aa, ww = _farm_counts(farm)
        checkpoints[str(day)] = {"money": float(farm["money"]), "hands": len(farm["hands"]), "quadrants": len(farm["unlocked_quadrants"]), "crops": dict(cc), "animals": dict(aa), "weeds": ww}
    return {
        "stage": stage, "path": path, "group": group, "opponent": opponent,
        "seed": int(seed), "seat": int(seat), "shop_mode": "natural" if schedule is None else "fixed",
        "configuration_patch": dict(config_patch or {}),
        "money": float(final[seat].reward), "opponent_money": float(final[1 - seat].reward),
        "advantage": float(final[seat].reward) - float(final[1 - seat].reward),
        "status": [state.status for state in final], "calls": calls,
        "runtime_error": None, "semantic_failures": semantic_failures,
        "stranded_value": value, "stranded": stranded,
        "final_crops": dict(crops), "final_animals": dict(animals), "final_weeds": weeds,
        "livestock_losses": livestock_losses, "checkpoints": checkpoints,
        "transition": transition, "telemetry": deepcopy(candidate.telemetry),
    }


def _source_fidelity():
    bank = json.loads((ROOT / "experiments/v27_route_manifest.json").read_text())
    route = next(row for row in bank["routes"] if row["route_id"] == "v27_family_3_victor_at_tufa_labs")
    appearances = []
    for replay_path in sorted((ROOT / "experiments/top_player_replays/replays").glob("episode-*-replay.json")):
        replay = json.loads(replay_path.read_text())
        for player, team in enumerate(replay["info"]["TeamNames"]):
            if team != "Victor @ Tufa Labs":
                continue
            for stage in ("K0", "K1", "K3", "K4", "K9"):
                candidate = run_path(str(ROOT / STAGES[stage]))["agent"]
                mismatches = []
                component = Counter()
                for step in range(719):
                    obs = deepcopy(replay["steps"][step][player]["observation"])
                    obs["player"] = player
                    obs["step"] = step
                    obs["day"] = step // 24
                    obs["hour"] = step % 24
                    actual = candidate(obs)
                    expected = deepcopy(replay["steps"][step + 1][player].get("action") or {})
                    expected.setdefault("farmer", ["PASS"])
                    expected.setdefault("market", [])
                    count = len(obs["farms"][player]["hands"])
                    hands = list(expected.get("hands", []))
                    hands.extend([["PASS"]] * max(0, count - len(hands)))
                    expected["hands"] = hands[:count]
                    if actual != expected:
                        mismatches.append(step)
                        component["farmer"] += actual["farmer"] != expected["farmer"]
                        component["hands"] += actual["hands"] != expected["hands"]
                        component["market"] += actual["market"] != expected["market"]
                appearances.append({
                    "stage": stage, "episode": int(replay["info"]["EpisodeId"]), "seat": player,
                    "seed": int(replay["info"]["seed"]), "opponent": replay["info"]["TeamNames"][1-player],
                    "source_final_money": float(replay["steps"][-1][player]["reward"]),
                    "actions_compared": 719, "mismatches": len(mismatches),
                    "first_mismatch": mismatches[0] if mismatches else None,
                    "component_mismatches": dict(component),
                    "route_fidelity": 1 - len(mismatches) / 719,
                })
    return appearances


def _jobs():
    jobs = []
    # Development: the four reconstructed real losses, recorded shops, both seats.
    for stage, path in STAGES.items():
        for name in ("Jayveer_melon_burst", "Pedro_wheat_turnover", "Lucas_four_quadrant", "Alexander_cow_melon"):
            _, replay_path, player = REPLAY_CASES[name]
            replay = json.loads((ROOT / replay_path).read_text())
            for seat in (0, 1):
                jobs.append((stage, path, "development_real", name, _trace_spec(replay_path, player), int(replay["info"]["seed"]), seat, _recorded_shop_schedule(replay), {}))
        # Direct fixed/natural checks against frozen baselines on disjoint seeds.
        for opponent, opponent_path in FROZEN.items():
            for seed in (973001, 973002):
                for seat in (0, 1):
                    jobs.append((stage, path, "frozen_fixed", opponent, opponent_path, seed, seat, _independent_shop_schedule(seed), {}))
                    jobs.append((stage, path, "frozen_natural", opponent, opponent_path, seed, seat, None, {}))
        # Entire held-out top-template families; never used to extract corrections.
        for name, (_, replay_path, player) in HELDOUT_REPLAY_CASES.items():
            replay = json.loads((ROOT / replay_path).read_text())
            for seat in (0, 1):
                jobs.append((stage, path, "final_unseen_real", name, _trace_spec(replay_path, player), int(replay["info"]["seed"]), seat, _recorded_shop_schedule(replay), {}))
    # Mechanism pressure is diagnostic, not weighted promotion evidence.
    pressure = {
        "weed_pressure": {"weedSpawnChance": 0.03},
        "hire_cost_pressure": {"farmHandCostMult": 3},
        "capital_pressure": {"startingMoney": 2400},
    }
    for stage in ("K0", "K2", "K3", "K4", "K5", "K6", "K9"):
        path = STAGES[stage]
        for name, patch in pressure.items():
            for seed in (979001, 979002):
                for seat in (0, 1):
                    jobs.append((stage, path, "mechanism_pressure", name, FROZEN["lifecycle"], seed, seat, _independent_shop_schedule(seed), patch))
    return jobs


def _fresh_confirmation_jobs():
    """Small final set chosen before looking at V27 results."""
    real = {
        "harmo_miu": ("experiments/leaderboard_replays/submission_55438811/replays/episode-92062516-replay.json", 0),
        "somasundar": ("experiments/leaderboard_replays/submission_55438811/replays/episode-92059628-replay.json", 1),
        "kks": ("experiments/leaderboard_replays/submission_55438811/replays/episode-92067306-replay.json", 1),
        "asuran": ("experiments/leaderboard_replays/submission_55438811/replays/episode-92250378-replay.json", 1),
    }
    jobs = []
    for stage in ("K0", "K3", "K4"):
        for name, (path, player) in real.items():
            replay = json.loads((ROOT / path).read_text())
            for seat in (0, 1):
                jobs.append((stage, STAGES[stage], "fresh_confirmation_real", name, _trace_spec(path, player), int(replay["info"]["seed"]), seat, _recorded_shop_schedule(replay), {}))
        for opponent, opponent_path in FROZEN.items():
            for seed in (991001, 991002):
                for seat in (0, 1):
                    jobs.append((stage, STAGES[stage], "fresh_confirmation_direct", opponent, opponent_path, seed, seat, _independent_shop_schedule(seed), {}))
                    jobs.append((stage, STAGES[stage], "fresh_confirmation_direct_natural", opponent, opponent_path, seed, seat, None, {}))
    return jobs


def _summary(games):
    output = {}
    valid = [row for row in games if not row.get("runtime_error")]
    for stage in STAGES:
        rows = [row for row in valid if row["stage"] == stage and row["group"] != "mechanism_pressure"]
        advantages = [row["advantage"] for row in rows]
        modes = Counter()
        repairs = Counter()
        for row in rows:
            modes.update(row["telemetry"]["mode_steps"])
            repairs.update(row["telemetry"]["repairs"])
        total_actions = sum(row["telemetry"]["all_route_requests"] for row in rows)
        matched_actions = sum(row["telemetry"]["all_route_matches"] for row in rows)
        output[stage] = {
            "games": len(rows), "wins": sum(value > 0 for value in advantages),
            "losses": sum(value < 0 for value in advantages), "ties": sum(value == 0 for value in advantages),
            "win_rate": sum(value > 0 for value in advantages) / max(1, len(rows)),
            "average_money": statistics.fmean(row["money"] for row in rows) if rows else None,
            "average_advantage": statistics.fmean(advantages) if advantages else None,
            "median_advantage": statistics.median(advantages) if advantages else None,
            "p25_advantage": _percentile(advantages, .25), "p10_advantage": _percentile(advantages, .10),
            "p5_advantage": _percentile(advantages, .05), "worst_advantage": min(advantages) if advantages else None,
            "performance_variance": statistics.pvariance(advantages) if len(advantages) > 1 else 0,
            "runtime_failures": sum(row.get("runtime_error") is not None for row in games if row["stage"] == stage),
            "semantic_failures": sum(len(row.get("semantic_failures", [])) for row in games if row["stage"] == stage),
            "route_action_fidelity": matched_actions / max(1, total_actions),
            "mode_steps": dict(modes), "repairs": dict(repairs),
            "fallback_games": sum(row["telemetry"].get("fallback_step") is not None for row in rows),
            "livestock_losses": sum(sum(row["livestock_losses"].values()) for row in rows),
            "meaningful_stranding_games": sum(row["stranded_value"] > 500 for row in rows),
            "sell_reorders": sum(row["telemetry"]["sell_reorders"] for row in rows),
            "future_sell_assignments": sum(row["telemetry"]["future_sell_assignments"] for row in rows),
            "hire_suppressions": sum(row["telemetry"]["hire_suppressed"] for row in rows),
            "critical_failures": sum(row["telemetry"]["critical_failed"] for row in rows),
        }
        by_opponent = {}
        for opponent in sorted({row["opponent"] for row in rows}):
            subset = [row for row in rows if row["opponent"] == opponent]
            adv = [row["advantage"] for row in subset]
            by_opponent[opponent] = {"games": len(subset), "wins": sum(v > 0 for v in adv), "losses": sum(v < 0 for v in adv), "average_money": statistics.fmean(row["money"] for row in subset), "average_advantage": statistics.fmean(adv), "p10": _percentile(adv, .10)}
        output[stage]["by_opponent"] = by_opponent
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--limit", type=int, default=0, help="run first N jobs for smoke testing")
    parser.add_argument("--fresh-confirmation", action="store_true")
    parser.add_argument("--stages", default="", help="optional comma-separated stage filter")
    args = parser.parse_args()
    jobs = _fresh_confirmation_jobs() if args.fresh_confirmation else _jobs()
    selected_stages = {value for value in args.stages.split(",") if value}
    if selected_stages:
        jobs = [job for job in jobs if job[0] in selected_stages]
    if args.limit:
        jobs = jobs[:args.limit]
    games = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(_run, job) for job in jobs]
        for index, future in enumerate(as_completed(futures), 1):
            games.append(future.result())
            if index % 40 == 0 or index == len(futures):
                print(f"games {index}/{len(futures)}", flush=True)
    payload = {
        "schema_version": 1,
        "design": "K0-K9 strict cumulative ablation; route-family-held-out real transfer; both seats",
        "source_fidelity": _source_fidelity(),
        "games": games,
        "summary": _summary(games),
    }
    output_path = OUT.with_name("v27_replay_backbone_fresh_confirmation.json") if args.fresh_confirmation else OUT
    output_path.write_text(json.dumps(payload, indent=2) + "\n")
    print(output_path)
    for stage, row in payload["summary"].items():
        if row["games"]:
            print(stage, row["games"], row["wins"], row["losses"], round(row["average_money"], 1), round(row["average_advantage"], 1), round(row["p10_advantage"], 1), round(row["route_action_fidelity"], 4))


if __name__ == "__main__":
    main()
