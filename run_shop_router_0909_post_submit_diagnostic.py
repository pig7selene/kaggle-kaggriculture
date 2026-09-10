"""Read-only post-submission diagnostics for ShopRouter0909Hardened.

The script writes experiment data only.  It never changes, packages, uploads,
or submits the frozen agent.  Hindsight comparisons hold the seed, seat,
opponent, and complete shop schedule constant while forcing each continuation.
"""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import time

from kaggle_environments import make

from run_epic_experiments import _independent_shop_schedule, _run_with_fixed_shops
from run_raw55899537_final_validation import (
    animal_escapes,
    digest,
    economic_summary,
    farm_counts,
    semantic_validate,
    terminal_value,
)


ROOT = Path(__file__).resolve().parent
EXPERIMENTS = ROOT / "experiments"
FROZEN = ROOT / "agents/shop_router_0909_hardened/main.py"
EXACT_DIR = ROOT / "agents/shop_router_0909"
OPPONENTS = {
    "current_best": ROOT / "agents/top50_distilled/top50_observable_portfolio.py",
    "v2": ROOT / "agents/super_replay_v2/super_backbone_v2.py",
    "k3": ROOT / "agents/v27_k3_weed.py",
    "crop_dusta": ROOT / "agents/top3_tuned/raw_rank2_crop_dusta.py",
}
SHOPS = (
    "BAKERY", "BRUNCH_SPOT", "FARMERS_MARKET", "ICE_CREAM_SHOP",
    "PET_CAFE", "PIZZA_SHOP", "SMOOTHIE_SHOP", "YARN_STORE",
)
ROUTE = {
    ("BAKERY", "YARN_STORE"): 3,
    ("BRUNCH_SPOT", "YARN_STORE"): 4,
    ("FARMERS_MARKET", "YARN_STORE"): 5,
    ("ICE_CREAM_SHOP", "YARN_STORE"): 6,
    ("PET_CAFE", "YARN_STORE"): 5,
    ("PIZZA_SHOP", "YARN_STORE"): 7,
    ("SMOOTHIE_SHOP", "YARN_STORE"): 8,
    ("YARN_STORE", "BAKERY"): 9,
    ("YARN_STORE", "BRUNCH_SPOT"): 9,
    ("YARN_STORE", "FARMERS_MARKET"): 1,
    ("YARN_STORE", "ICE_CREAM_SHOP"): 9,
    ("YARN_STORE", "PET_CAFE"): 10,
    ("YARN_STORE", "PIZZA_SHOP"): 6,
    ("YARN_STORE", "SMOOTHIE_SHOP"): 11,
    ("YARN_STORE", "YARN_STORE"): 12,
}
ORACLE_CASES = (
    ("fallback_bakery_pet", "BAKERY", "PET_CAFE"),
    ("fallback_pizza_farmers", "PIZZA_SHOP", "FARMERS_MARKET"),
    ("fallback_smoothie_ice", "SMOOTHIE_SHOP", "ICE_CREAM_SHOP"),
    ("fallback_pet_brunch", "PET_CAFE", "BRUNCH_SPOT"),
    ("plan1_yarn_farmers", "YARN_STORE", "FARMERS_MARKET"),
    ("plan3_bakery_yarn", "BAKERY", "YARN_STORE"),
    ("plan4_brunch_yarn", "BRUNCH_SPOT", "YARN_STORE"),
    ("plan5_farmers_yarn", "FARMERS_MARKET", "YARN_STORE"),
    ("plan6_ice_yarn", "ICE_CREAM_SHOP", "YARN_STORE"),
    ("plan7_pizza_yarn", "PIZZA_SHOP", "YARN_STORE"),
    ("plan8_smoothie_yarn", "SMOOTHIE_SHOP", "YARN_STORE"),
    ("plan9_yarn_bakery", "YARN_STORE", "BAKERY"),
    ("plan10_yarn_pet", "YARN_STORE", "PET_CAFE"),
    ("plan11_yarn_smoothie", "YARN_STORE", "SMOOTHIE_SHOP"),
    ("plan12_yarn_yarn", "YARN_STORE", "YARN_STORE"),
)
FREQUENCY_PARTIAL = EXPERIMENTS / "shop_router_0909_frequency_runs_v2.partial.json"
ORACLE_PARTIAL = EXPERIMENTS / "shop_router_0909_oracle_runs.partial.json"
RAW_OUT = EXPERIMENTS / "shop_router_0909_post_submit_diagnostic_raw.json"


def _load(path: Path, tag: str):
    name = f"post0909_{tag}_{time.time_ns()}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _plain(value):
    if isinstance(value, Counter):
        return dict(value)
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _hash(value):
    return hashlib.sha256(
        json.dumps(_plain(value), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _fixed_schedule(seed: int, first: str, second: str):
    schedule = _independent_shop_schedule(seed)
    for day, shops in schedule.items():
        if day >= 3 and shops:
            shops[0] = first
        if day >= 6 and len(shops) >= 2:
            shops[1] = second
    return schedule


def _forced_agent(hardened_module, plan: int):
    """Force the step-144 continuation and preserve the frozen Plan-10 patch."""
    exact = hardened_module.agent.exact_module
    policy = exact.Policy(EXACT_DIR)

    def forced(observation, configuration=None):
        step = int(observation["step"])
        player = int(observation["player"])
        state = policy.players.get(player)
        if state is None or step <= state.last_step:
            state = policy.players[player] = exact.DayState()
        state.last_step = step
        if step == exact.ROUTE_STEP:
            state.plan = int(plan)
        if step == exact.FINAL_PLAN_STEP:
            state.plan = 2
        view = exact.FarmView(observation)
        tape = policy.tapes[state.plan]
        action = deepcopy(tape[step])
        exact.repair_weeds(action, view, state, step)
        exact.subtract_advanced_sales(action, state, step)
        exact.advance_sales(action, view, state, tape, step)
        action["market"] = action["market"][: exact.MAX_ORDERS]
        action = exact.liquidate(view) if step == exact.LAST_STEP else action
        if state.plan == 10 and step == 360 and action["farmer"] == ["PICKUP", "WHEAT", 5]:
            action["farmer"][2] = 4
        return action

    forced.policy = policy
    return forced


def _observable_features(observation):
    player = int(observation["player"])
    own = observation["farms"][player]
    other = observation["farms"][1 - player]

    def public_farm(farm):
        counts = farm_counts(farm)
        return {
            "money": float(farm["money"]),
            "hands": len(farm.get("hands", [])),
            "unlocked_quadrants": len(farm.get("unlocked_quadrants", [])),
            "counts": counts,
        }

    prices = {key: int(value) for key, value in observation["market"]["prices"].items()}
    inventory = {key: int(value) for key, value in observation["market"]["inventory"].items()}
    premium = [prices.get(item, 0) for item in ("STRAWBERRY", "MELON", "MILK", "WOOL")]
    staples = [prices.get(item, 0) for item in ("WHEAT", "CARROT", "TOMATO", "EGG")]
    return {
        "step": int(observation["step"]),
        "shop_pair": list(observation["town"]["unlocked_shops"][:2]),
        "own": public_farm(own),
        "opponent": public_farm(other),
        "bank_gap": float(own["money"]) - float(other["money"]),
        "market_prices": prices,
        "market_inventory": inventory,
        "market_regime": {
            "premium_mean_price": sum(premium) / len(premium),
            "staple_mean_price": sum(staples) / len(staples),
            "wool_price": prices.get("WOOL"),
            "milk_price": prices.get("MILK"),
            "crop_premium_price": (prices.get("STRAWBERRY", 0) + prices.get("MELON", 0)) / 2,
        },
    }


def _trace_state(observation):
    """Hash only information legally observable by the candidate at this step."""
    player = int(observation["player"])
    return {
        "step": int(observation["step"]),
        "day": int(observation["day"]),
        "hour": int(observation["hour"]),
        "farms": observation["farms"],
        "private": observation["private"],
        "market": observation["market"],
        "town": observation["town"],
        "player": player,
    }


def run_game(job):
    (stage, opponent_name, seed, seat, mode, first, second, forced_plan,
     case_name, capture_trace) = job
    started = time.perf_counter()
    hardened = _load(FROZEN, f"candidate_{stage}_{seed}_{seat}_{forced_plan}")
    candidate = hardened.agent if forced_plan is None else _forced_agent(hardened, forced_plan)
    opponent = _load(OPPONENTS[opponent_name], f"opponent_{opponent_name}_{seed}_{seat}_{forced_plan}").agent
    actions = []
    semantic_failures = []
    exceptions = []
    route = {"plan_at_144": forced_plan, "shops_at_144": None}
    features = None
    state_step_hashes = []
    action_step_hashes = []

    def checked(observation):
        nonlocal features
        step = int(observation["step"])
        if capture_trace:
            state_step_hashes.append(_hash(_trace_state(observation)))
        try:
            action = candidate(observation)
        except Exception as exc:
            exceptions.append({"step": step, "error": repr(exc)})
            raise
        actions.append(deepcopy(action))
        if capture_trace:
            action_step_hashes.append(_hash(action))
        try:
            semantic_validate(observation, action)
        except Exception as exc:
            semantic_failures.append({"step": step, "error": repr(exc)})
        if step == 144:
            route["shops_at_144"] = list(observation["town"]["unlocked_shops"][:2])
            features = _observable_features(observation)
            if forced_plan is None:
                exact = hardened.agent.exact_module
                route["plan_at_144"] = int(exact._POLICY.players[int(observation["player"])].plan)
        return action

    pair = [opponent, opponent]
    pair[int(seat)] = checked
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": int(seed)}, debug=False)
    runtime_error = None
    try:
        if mode == "fixed":
            _run_with_fixed_shops(env, pair, _fixed_schedule(seed, first, second))
        else:
            env.run(pair)
    except Exception as exc:
        runtime_error = repr(exc)
    if runtime_error or len(getattr(env, "steps", [])) != 720:
        return {
            "stage": stage, "condition_id": case_name, "opponent": opponent_name,
            "seed": int(seed), "seat": int(seat), "shop_mode": mode,
            "forced_plan": forced_plan, "runtime_error": runtime_error or f"steps={len(env.steps)}",
            "semantic_failures": semantic_failures, "exceptions": exceptions,
        }

    states = env.steps
    final = states[-1]
    own = float(final[seat].reward)
    other = float(final[1 - seat].reward)
    economics = economic_summary(env.toJSON(), seat)
    economics.pop("daily", None)
    own_farm = final[seat].observation["farms"][seat]
    terminal = terminal_value(final, seat)
    return _plain({
        "stage": stage,
        "condition_id": case_name,
        "opponent": opponent_name,
        "seed": int(seed),
        "seat": int(seat),
        "shop_mode": mode,
        "forced_plan": forced_plan,
        "runtime_error": None,
        "semantic_failures": semantic_failures,
        "exceptions": exceptions,
        "calls": len(actions),
        "elapsed_s": time.perf_counter() - started,
        "own_money": own,
        "opponent_money": other,
        "advantage": own - other,
        "outcome": "win" if own > other else "loss" if own < other else "tie",
        "action_hash": digest(actions),
        "route": route,
        "decision_features": features,
        "final_counts": farm_counts(own_farm),
        "livestock_escapes": animal_escapes(states, seat),
        "terminal": terminal,
        "economics": economics,
        "trace": {
            "state_step_hashes": state_step_hashes,
            "action_step_hashes": action_step_hashes,
        } if capture_trace else None,
    })


def frequency_jobs():
    jobs = []
    for index, first in enumerate(SHOPS):
        for jndex, second in enumerate(SHOPS):
            seed = 1_332_000 + index * len(SHOPS) + jndex
            case = f"fixed_{first}_{second}"
            for seat in (0, 1):
                jobs.append(("frequency", "current_best", seed, seat, "fixed", first, second, None, case, False))
    for opponent_index, opponent_name in enumerate(("current_best", "v2", "k3", "crop_dusta")):
        # Distinct ranges give 64 independent natural shop realizations rather
        # than replaying the same 16 shop sequences against four opponents.
        seed_start = 1_331_000 + opponent_index * 16
        for seed in range(seed_start, seed_start + 16):
            for seat in (0, 1):
                jobs.append(("frequency", opponent_name, seed, seat, "natural", None, None, None,
                             f"natural_{opponent_name}_{seed}", False))
    return jobs


def oracle_jobs():
    jobs = []
    for index, (label, first, second) in enumerate(ORACLE_CASES):
        seed = 1_333_000 + index
        for opponent_name in ("current_best", "v2", "crop_dusta"):
            for seat in (0, 1):
                condition = f"{label}|{opponent_name}|seat{seat}"
                for plan in range(13):
                    capture = label == "fallback_bakery_pet" and opponent_name == "current_best" and seat == 0
                    jobs.append(("oracle", opponent_name, seed, seat, "fixed", first, second, plan,
                                 condition, capture))
    return jobs


def _job_key(job):
    stage, opponent, seed, seat, mode, _first, _second, forced, condition, _trace = job
    return "|".join(str(value) for value in (stage, opponent, seed, seat, mode, forced, condition))


def _row_key(row):
    return "|".join(str(value) for value in (
        row["stage"], row["opponent"], row["seed"], row["seat"], row["shop_mode"],
        row.get("forced_plan"), row.get("condition_id"),
    ))


def run_jobs(jobs, partial_path: Path, workers: int):
    existing = []
    if partial_path.exists():
        existing = json.loads(partial_path.read_text()).get("rows", [])
    done = {_row_key(row) for row in existing if not row.get("runtime_error")}
    pending = [job for job in jobs if _job_key(job) not in done]
    rows = list(existing)
    print(f"{partial_path.name}: total={len(jobs)} done={len(done)} pending={len(pending)}", flush=True)
    completed = 0
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(run_game, job): job for job in pending}
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            completed += 1
            if completed % 20 == 0 or completed == len(pending):
                partial_path.write_text(json.dumps({"rows": rows}, indent=2, sort_keys=True) + "\n")
                print(f"completed {completed}/{len(pending)} errors={sum(bool(r.get('runtime_error')) for r in rows)}", flush=True)
    partial_path.write_text(json.dumps({"rows": rows}, indent=2, sort_keys=True) + "\n")
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("frequency", "oracle", "all"), default="all")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    frequency = []
    oracle = []
    if args.stage in ("frequency", "all"):
        frequency = run_jobs(frequency_jobs(), FREQUENCY_PARTIAL, args.workers)
    elif FREQUENCY_PARTIAL.exists():
        frequency = json.loads(FREQUENCY_PARTIAL.read_text()).get("rows", [])
    if args.stage in ("oracle", "all"):
        oracle = run_jobs(oracle_jobs(), ORACLE_PARTIAL, args.workers)
    elif ORACLE_PARTIAL.exists():
        oracle = json.loads(ORACLE_PARTIAL.read_text()).get("rows", [])
    RAW_OUT.write_text(json.dumps({
        "schema": "shop-router-0909-post-submit-diagnostic-raw-v1",
        "frozen_agent": str(FROZEN.relative_to(ROOT)),
        "design": {
            "frequency_fixed": "all 64 ordered first/second shop pairs x both seats",
            "frequency_natural": "4 opponent families x 16 fresh seeds x both seats",
            "oracle": "15 shop regimes x 3 opponents x both seats x all 13 continuations",
            "forced_policy": "plan 0 through step 143; forced plan at 144; common plan 2 at 648; frozen Plan-10 patch retained",
        },
        "frequency_rows": frequency,
        "oracle_rows": oracle,
    }, indent=2, sort_keys=True) + "\n")
    print(f"wrote {RAW_OUT}", flush=True)


if __name__ == "__main__":
    main()
