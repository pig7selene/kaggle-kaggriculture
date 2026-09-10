"""Targeted Plan-10 matrix for the four minimal Shop Router hardening fixes."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time

from kaggle_environments import make

from run_epic_experiments import _independent_shop_schedule, _run_with_fixed_shops
from run_raw55899537_final_validation import animal_escapes, economic_summary, semantic_validate, terminal_value


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "experiments/shop_router_0909_plan10_targeted_raw.json"
VARIANTS = {
    "fix_a_reserve_sale": ROOT / "agents/shop_router_0909_hardened/v1_fix_a_reserve_sale.py",
    "fix_b_buy_one": ROOT / "agents/shop_router_0909_hardened/v1_fix_b_buy_one.py",
    "fix_c_reallocate_day14": ROOT / "agents/shop_router_0909_hardened/v1_fix_c_reallocate_day14.py",
    "fix_d_reallocate_day15": ROOT / "agents/shop_router_0909_hardened/v1_fix_d_reallocate_day15.py",
}
OPPONENTS = {
    "current_best": ROOT / "agents/top50_distilled/top50_observable_portfolio.py",
    "v2": ROOT / "agents/super_replay_v2/super_backbone_v2.py",
    "k3": ROOT / "agents/v27_k3_weed.py",
    "crop_dusta": ROOT / "agents/top3_tuned/raw_rank2_crop_dusta.py",
}
FIXED_SEEDS = tuple(range(1312000, 1312006))
NATURAL_SEEDS = (1310349, 1310377, 1310644, 1310687, 1310705, 1311052)


def load_agent(path, tag):
    spec = importlib.util.spec_from_file_location(f"plan10_target_{tag}_{time.time_ns()}", path)
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


def terminal_animal_risk(final, seat):
    farm = final[seat].observation["farms"][seat]
    rows = []
    for y, tiles in enumerate(farm["tiles"]):
        for x, tile in enumerate(tiles):
            if isinstance(tile, dict) and tile.get("animal") and tile.get("consecutive_unfed", 0):
                rows.append({"position": [x, y], "animal": tile["animal"], "consecutive_unfed": tile["consecutive_unfed"]})
    return rows


def run_game(job):
    variant, candidate_path, opponent_name, opponent_path, seed, seat, mode = job
    module, candidate = load_agent(candidate_path, f"candidate_{variant}_{seed}_{seat}")
    _, opponent = load_agent(opponent_path, f"opponent_{opponent_name}_{seed}_{seat}")
    warnings = []
    actions = []
    route = {"shops_at_144": None, "plan_at_144": None}

    def checked(obs):
        action = candidate(obs)
        actions.append(deepcopy(action))
        if int(obs["step"]) == 144:
            route["shops_at_144"] = list(obs["town"]["unlocked_shops"][:2])
            route["plan_at_144"] = candidate.exact_module._POLICY.players[int(obs["player"])].plan
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
        if mode == "fixed_plan10":
            _run_with_fixed_shops(env, pair, forced_plan10_schedule(seed))
        else:
            env.run(pair)
    except Exception as exc:
        runtime_error = repr(exc)
    if runtime_error or len(env.steps) != 720:
        return {
            "variant": variant, "opponent": opponent_name, "seed": seed, "seat": seat,
            "shop_mode": mode, "runtime_error": runtime_error or f"steps={len(env.steps)}",
        }
    final = env.steps[-1]
    replay = env.toJSON()
    economics = economic_summary(replay, seat)
    economics.pop("daily", None)
    return {
        "variant": variant, "opponent": opponent_name, "seed": int(seed), "seat": int(seat),
        "shop_mode": mode, "runtime_error": None, "route": route,
        "steps": len(env.steps), "calls": len(actions),
        "own_money": float(final[seat].reward),
        "opponent_money": float(final[1 - seat].reward),
        "advantage": float(final[seat].reward) - float(final[1 - seat].reward),
        "outcome": "win" if final[seat].reward > final[1 - seat].reward else "loss" if final[seat].reward < final[1 - seat].reward else "tie",
        "livestock_escapes": animal_escapes(env.steps, seat),
        "terminal_at_risk_animals": terminal_animal_risk(final, seat),
        "terminal": terminal_value(final, seat),
        "strict_warning_count": len(warnings),
        "strict_warning_classes": sorted({row["class"] for row in warnings}),
        "action_hash": hashlib.sha256(json.dumps(actions, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "economics": economics,
    }


def jobs():
    output = []
    for variant, candidate_path in VARIANTS.items():
        for opponent_name, opponent_path in OPPONENTS.items():
            for seed in FIXED_SEEDS:
                for seat in (0, 1):
                    output.append((variant, candidate_path, opponent_name, opponent_path, seed, seat, "fixed_plan10"))
        for opponent_name in ("current_best", "v2"):
            for seed in NATURAL_SEEDS:
                for seat in (0, 1):
                    output.append((variant, candidate_path, opponent_name, OPPONENTS[opponent_name], seed, seat, "natural_plan10"))
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    all_jobs = jobs()
    rows = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_game, job) for job in all_jobs]
        for future in as_completed(futures):
            rows.append(future.result())
            if len(rows) % 40 == 0 or len(rows) == len(all_jobs):
                print(f"completed {len(rows)}/{len(all_jobs)}", flush=True)
    rows.sort(key=lambda row: (row["variant"], row["shop_mode"], row["opponent"], row["seed"], row["seat"]))
    OUT.write_text(json.dumps({
        "design": "Four successful one-primitive patches; 192 forced-plan10 and 96 natural-plan10 games.",
        "fixed_seeds": FIXED_SEEDS, "natural_seeds": NATURAL_SEEDS,
        "rows": rows,
    }, indent=2, sort_keys=True) + "\n")
    for variant in VARIANTS:
        selected = [row for row in rows if row["variant"] == variant]
        print(variant, "games", len(selected), "escapes", sum(len(row.get("livestock_escapes", [])) for row in selected),
              "wins", sum(row.get("outcome") == "win" for row in selected))


if __name__ == "__main__":
    main()
