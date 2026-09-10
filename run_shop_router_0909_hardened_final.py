"""Post-lock final validation for the one-primitive Shop Router hardening."""

from __future__ import annotations

from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics
import time

from kaggle_environments import make

from run_epic_experiments import _independent_shop_schedule, _run_with_fixed_shops
from run_raw55899537_final_validation import animal_escapes, economic_summary, farm_counts, semantic_validate, terminal_value


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "experiments/shop_router_0909_hardened_final_raw.json"
LOCK = ROOT / "experiments/shop_router_0909_hardened_lock.json"
HARDENED = ROOT / "agents/shop_router_0909_hardened/main.py"
EXACT = ROOT / "agents/shop_router_0909/main.py"
CURRENT = ROOT / "agents/top50_distilled/top50_observable_portfolio.py"
V2 = ROOT / "agents/super_replay_v2/super_backbone_v2.py"
VARIANTS = {"hardened": HARDENED, "exact": EXACT, "current_best": CURRENT, "v2": V2}
OPPONENTS = {
    "current_best": CURRENT,
    "v2": V2,
    "k3": ROOT / "agents/v27_k3_weed.py",
    "nazmus": ROOT / "agents/super_replay_v4/n1_nazmus_weed.py",
    "tetsuya": ROOT / "agents/top3_tuned/raw_rank1_tetsuya.py",
    "crop_dusta": ROOT / "agents/top3_tuned/raw_rank2_crop_dusta.py",
    "oceanmix": ROOT / "agents/top3_tuned/raw_rank3_oceanmix.py",
    "farming_v3": ROOT / "agents/public_farming_v3/main.py",
    "exact": EXACT,
}
LEAGUE_SEEDS = {"fixed": (1314000, 1314001), "natural": (1314100, 1314101)}
H2H_SEEDS = {"fixed": tuple(range(1314200, 1314206)), "natural": tuple(range(1314300, 1314306))}
PLAN10_FIXED_SEEDS = tuple(range(1313000, 1313004))
PLAN10_NATURAL_SEEDS = (1311167, 1311212, 1311308, 1311370)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_agent(path, tag):
    spec = importlib.util.spec_from_file_location(f"shop0909_final_{tag}_{time.time_ns()}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, module.agent


def forced_plan10_schedule(seed):
    schedule = _independent_shop_schedule(seed)
    for day, shops in schedule.items():
        if day >= 3 and shops:
            shops[0] = "YARN_STORE"
        if day >= 6 and len(shops) >= 2:
            shops[1] = "PET_CAFE"
    return schedule


def policy_plan(module, agent, player):
    if hasattr(agent, "exact_module"):
        return agent.exact_module._POLICY.players[player].plan
    policy = getattr(module, "_POLICY", None)
    if policy is not None and player in getattr(policy, "players", {}):
        return policy.players[player].plan
    return None


def terminal_animal_risk(final, seat):
    farm = final[seat].observation["farms"][seat]
    rows = []
    for y, tiles in enumerate(farm["tiles"]):
        for x, tile in enumerate(tiles):
            if isinstance(tile, dict) and tile.get("animal") and tile.get("consecutive_unfed", 0):
                rows.append({"position": [x, y], "animal": tile["animal"], "consecutive_unfed": tile["consecutive_unfed"]})
    return rows


def run_game(job):
    panel, variant, variant_path, opponent_name, opponent_path, seed, seat, mode = job
    module, candidate = load_agent(variant_path, f"candidate_{panel}_{variant}_{seed}_{seat}")
    _, opponent = load_agent(opponent_path, f"opponent_{panel}_{opponent_name}_{seed}_{seat}")
    warnings = []
    actions = []
    route = {"shops_at_144": None, "plan_at_144": None}
    exceptions = []

    def checked(obs):
        try:
            action = candidate(obs)
        except Exception as exc:
            exceptions.append({"step": int(obs.get("step", -1)), "error": repr(exc)})
            raise
        actions.append(deepcopy(action))
        if int(obs["step"]) == 144:
            route["shops_at_144"] = list(obs["town"]["unlocked_shops"][:2])
            route["plan_at_144"] = policy_plan(module, candidate, int(obs["player"]))
        try:
            semantic_validate(obs, action)
        except Exception as exc:
            warnings.append({"step": int(obs["step"]), "class": repr(exc)})
        return action

    pair = [opponent, opponent]
    pair[seat] = checked
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": int(seed)}, debug=False)
    runtime_error = None
    try:
        if mode == "fixed":
            _run_with_fixed_shops(env, pair, _independent_shop_schedule(seed))
        elif mode == "fixed_plan10":
            _run_with_fixed_shops(env, pair, forced_plan10_schedule(seed))
        else:
            env.run(pair)
    except Exception as exc:
        runtime_error = repr(exc)
    if runtime_error or len(env.steps) != 720:
        return {
            "panel": panel, "variant": variant, "opponent": opponent_name, "seed": seed, "seat": seat,
            "shop_mode": mode, "runtime_error": runtime_error or f"steps={len(env.steps)}", "exceptions": exceptions,
        }
    final = env.steps[-1]
    replay = env.toJSON()
    economics = economic_summary(replay, seat)
    economics.pop("daily", None)
    farm = final[seat].observation["farms"][seat]
    return {
        "panel": panel, "variant": variant, "opponent": opponent_name, "seed": int(seed), "seat": int(seat),
        "shop_mode": mode, "runtime_error": None, "exceptions": exceptions, "route": route,
        "steps": len(env.steps), "calls": len(actions),
        "own_money": float(final[seat].reward), "opponent_money": float(final[1 - seat].reward),
        "advantage": float(final[seat].reward) - float(final[1 - seat].reward),
        "outcome": "win" if final[seat].reward > final[1 - seat].reward else "loss" if final[seat].reward < final[1 - seat].reward else "tie",
        "livestock_escapes": animal_escapes(env.steps, seat),
        "terminal_at_risk_animals": terminal_animal_risk(final, seat),
        "terminal": terminal_value(final, seat), "final_counts": farm_counts(farm),
        "strict_warning_count": len(warnings),
        "strict_warning_classes": sorted({row["class"] for row in warnings}),
        "action_hash": hashlib.sha256(json.dumps(actions, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "economics": economics,
    }


def build_jobs():
    jobs = []
    for variant, variant_path in VARIANTS.items():
        for opponent_name in ("current_best", "v2", "k3", "nazmus", "tetsuya", "crop_dusta", "oceanmix", "farming_v3"):
            for mode, seeds in LEAGUE_SEEDS.items():
                for seed in seeds:
                    for seat in (0, 1):
                        jobs.append(("league", variant, variant_path, opponent_name, OPPONENTS[opponent_name], seed, seat, mode))
    for opponent_name in ("current_best", "v2", "exact"):
        for mode, seeds in H2H_SEEDS.items():
            for seed in seeds:
                for seat in (0, 1):
                    jobs.append(("h2h", "hardened", HARDENED, opponent_name, OPPONENTS[opponent_name], seed, seat, mode))
    for opponent_name in ("current_best", "v2", "k3", "crop_dusta"):
        for seed in PLAN10_FIXED_SEEDS:
            for seat in (0, 1):
                jobs.append(("plan10_final", "hardened", HARDENED, opponent_name, OPPONENTS[opponent_name], seed, seat, "fixed_plan10"))
    for opponent_name in ("current_best", "v2"):
        for seed in PLAN10_NATURAL_SEEDS:
            for seat in (0, 1):
                jobs.append(("plan10_final", "hardened", HARDENED, opponent_name, OPPONENTS[opponent_name], seed, seat, "natural_plan10"))
    return jobs


def capture_trajectory(path, tag):
    module, candidate = load_agent(path, f"trajectory_{tag}")
    _, opponent = load_agent(CURRENT, f"trajectory_opponent_{tag}")
    actions = []
    state_hashes = []
    state_rows = []

    def checked(obs):
        action = candidate(obs)
        actions.append(deepcopy(action))
        own = {
            "farm": obs["farms"][int(obs["player"])], "private": obs["private"],
            "market": obs["market"], "town": obs["town"],
        }
        state_hashes.append(hashlib.sha256(json.dumps(own, sort_keys=True, separators=(",", ":")).encode()).hexdigest())
        if 330 <= int(obs["step"]) <= 385:
            tile = obs["farms"][int(obs["player"])]["tiles"][4][7]
            state_rows.append({
                "step": int(obs["step"]), "action": deepcopy(action),
                "money": float(obs["farms"][int(obs["player"])]["money"]),
                "shed_wheat": int(obs["private"]["shed"].get("WHEAT", 0)),
                "total_wheat": int(obs["private"]["shed"].get("WHEAT", 0)) + sum(int(inv.get("WHEAT", 0)) for inv in obs["private"]["inventories"]),
                "target_tile": deepcopy(tile),
            })
        return action

    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": 1309401}, debug=False)
    _run_with_fixed_shops(env, [checked, opponent], _independent_shop_schedule(1309401))
    return {"actions": actions, "state_hashes": state_hashes, "state_rows": state_rows}


def trajectory_diff():
    exact = capture_trajectory(EXACT, "exact")
    hardened = capture_trajectory(HARDENED, "hardened")
    action_steps = [step for step, (a, b) in enumerate(zip(exact["actions"], hardened["actions"])) if a != b]
    state_steps = [step for step, (a, b) in enumerate(zip(exact["state_hashes"], hardened["state_hashes"])) if a != b]
    detail = []
    for step in action_steps:
        detail.append({"step": step, "exact": exact["actions"][step], "hardened": hardened["actions"][step]})
    return {
        "condition": {"seed": 1309401, "seat": 0, "shop_mode": "fixed", "opponent": "current_best"},
        "action_difference_count": len(action_steps), "action_difference_steps": action_steps,
        "action_differences": detail,
        "first_state_difference_step": state_steps[0] if state_steps else None,
        "state_difference_count": len(state_steps), "state_difference_steps": state_steps,
        "tape_indices_shifted": False,
        "exact_trace_window": exact["state_rows"], "hardened_trace_window": hardened["state_rows"],
    }


def main():
    lock = json.loads(LOCK.read_text())
    assert sha(HARDENED) == lock["candidate_sha256"]
    assert sha(EXACT) == lock["exact_parent"]["main_sha256"]
    assert sha(ROOT / "agents/shop_router_0909/actions.json") == lock["exact_parent"]["actions_sha256"]
    assert sha(CURRENT) == "f9ca672848ccffdfe56888d99bcdf5a9d7644062b9eec0cf0cdea13574931233"
    assert sha(ROOT / "submission/main.py") == "789bb9bbd5122eb4891983e776a13777328e3e87736cbbc0b4bc86d13fc33f9b"
    jobs = build_jobs()
    rows = []
    with ProcessPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(run_game, job) for job in jobs]
        for future in as_completed(futures):
            rows.append(future.result())
            if len(rows) % 40 == 0 or len(rows) == len(jobs):
                print(f"completed {len(rows)}/{len(jobs)}", flush=True)
    rows.sort(key=lambda row: (row["panel"], row["variant"], row["opponent"], row["shop_mode"], row["seed"], row["seat"]))
    payload = {
        "schema_version": 1,
        "design": "Post-lock fresh validation: 256-game four-policy league, 72 direct H2H, 48 Plan-10 confirmation games.",
        "locked_hashes": {
            "hardened": sha(HARDENED), "exact": sha(EXACT), "actions": sha(ROOT / "agents/shop_router_0909/actions.json"),
            "current_best": sha(CURRENT), "submission": sha(ROOT / "submission/main.py"),
        },
        "job_count": len(jobs), "rows": rows, "downstream_trajectory_diff": trajectory_diff(),
    }
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    failures = [row for row in rows if row.get("runtime_error") or row.get("exceptions")]
    print(json.dumps({"games": len(rows), "runtime_or_agent_failures": len(failures), "output": str(OUT)}, indent=2))


if __name__ == "__main__":
    main()
