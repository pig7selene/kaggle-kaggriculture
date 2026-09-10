"""Local-only reproduction and validation for public Shop Router 0909.

This runner never packages, uploads, submits, or modifies deployment files.  It
loads every policy fresh per game, evaluates identical seeds and seats, and
keeps the score-linked public v1 agent byte-for-byte unchanged.
"""

from __future__ import annotations

import argparse
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
from run_raw55899537_final_validation import (
    animal_escapes,
    digest,
    economic_summary,
    farm_counts,
    milestone_summary,
    percentile,
    semantic_validate,
    terminal_value,
)


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "experiments/shop_router_0909_runs"
SELECTED = ROOT / "agents/shop_router_0909/main.py"
VARIANTS = {
    "shop_router_0909": SELECTED,
    "current_best": ROOT / "agents/top50_distilled/top50_observable_portfolio.py",
    "v2": ROOT / "agents/super_replay_v2/super_backbone_v2.py",
}
OPPONENTS = {
    "current_best": ROOT / "agents/top50_distilled/top50_observable_portfolio.py",
    "v2": ROOT / "agents/super_replay_v2/super_backbone_v2.py",
    "k3": ROOT / "agents/v27_k3_weed.py",
    "nazmus": ROOT / "agents/super_replay_v4/n1_nazmus_weed.py",
    "tetsuya": ROOT / "agents/top3_tuned/raw_rank1_tetsuya.py",
    "crop_dusta": ROOT / "agents/top3_tuned/raw_rank2_crop_dusta.py",
    "oceanmix": ROOT / "agents/top3_tuned/raw_rank3_oceanmix.py",
    "farming_v3": ROOT / "agents/public_farming_v3/main.py",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_agent(path: Path, tag: str):
    name = f"shop0909_{tag}_{time.time_ns()}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, module.agent


def _plain(value):
    if isinstance(value, Counter):
        return dict(value)
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _forced_agent(module, plan: int):
    policy = module.Policy(SELECTED.parent)

    def forced(observation, configuration=None):
        step = int(observation["step"])
        player = int(observation["player"])
        state = policy.players.get(player)
        if state is None or step <= state.last_step:
            state = policy.players[player] = module.DayState()
        state.last_step = step
        if step == module.ROUTE_STEP:
            state.plan = int(plan)
        if step == module.FINAL_PLAN_STEP:
            state.plan = 2
        view = module.FarmView(observation)
        tape = policy.tapes[state.plan]
        action = deepcopy(tape[step])
        module.repair_weeds(action, view, state, step)
        module.subtract_advanced_sales(action, state, step)
        module.advance_sales(action, view, state, tape, step)
        action["market"] = action["market"][: module.MAX_ORDERS]
        return module.liquidate(view) if step == module.LAST_STEP else action

    return forced


def run_game(job):
    stage, candidate_name, candidate_path, opponent_name, opponent_path, seed, seat, mode, forced_plan = job
    started = time.perf_counter()
    module, candidate = load_agent(candidate_path, f"candidate_{candidate_name}_{seed}_{seat}")
    if forced_plan is not None:
        candidate = _forced_agent(module, forced_plan)
    _, opponent = load_agent(opponent_path, f"opponent_{opponent_name}_{seed}_{seat}")
    actions = []
    semantic_failures = []
    exceptions = []
    route = {"plan_at_144": forced_plan, "shops_at_144": None}

    def checked(observation):
        step = int(observation.get("step", 0))
        try:
            action = candidate(observation)
        except Exception as exc:
            exceptions.append({"step": step, "error": repr(exc)})
            raise
        actions.append(deepcopy(action))
        try:
            semantic_validate(observation, action)
        except Exception as exc:
            semantic_failures.append({"step": step, "error": repr(exc)})
        if step == 144:
            route["shops_at_144"] = list(observation["town"]["unlocked_shops"][:2])
            if forced_plan is None and candidate_name == "shop_router_0909":
                route["plan_at_144"] = module._POLICY.players[int(observation["player"])].plan
        return action

    pair = [opponent, opponent]
    pair[int(seat)] = checked
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": int(seed)}, debug=False)
    runtime_error = None
    try:
        if mode == "fixed":
            _run_with_fixed_shops(env, pair, _independent_shop_schedule(seed))
        else:
            env.run(pair)
    except Exception as exc:
        runtime_error = repr(exc)
    if runtime_error or len(getattr(env, "steps", [])) != 720:
        return {
            "stage": stage,
            "candidate": candidate_name,
            "opponent": opponent_name,
            "seed": int(seed),
            "seat": int(seat),
            "shop_mode": mode,
            "forced_plan": forced_plan,
            "runtime_error": runtime_error or f"steps={len(env.steps)}",
            "semantic_failures": semantic_failures,
            "exceptions": exceptions,
        }

    states = env.steps
    final = states[-1]
    replay = env.toJSON()
    own = float(final[seat].reward)
    other = float(final[1 - seat].reward)
    economics = economic_summary(replay, seat)
    economics.pop("daily", None)
    own_farm = final[seat].observation["farms"][seat]
    return _plain({
        "stage": stage,
        "candidate": candidate_name,
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
        "final_counts": farm_counts(own_farm),
        "livestock_escapes": animal_escapes(states, seat),
        "terminal": terminal_value(final, seat),
        "milestones": milestone_summary(states, seat),
        "economics": economics,
    })


def league_jobs():
    jobs = []
    seed_sets = {"fixed": (1309100, 1309101), "natural": (1309200, 1309201)}
    for candidate_name, candidate_path in VARIANTS.items():
        for opponent_name, opponent_path in OPPONENTS.items():
            for mode, seeds in seed_sets.items():
                for seed in seeds:
                    for seat in (0, 1):
                        jobs.append(("league", candidate_name, candidate_path, opponent_name, opponent_path, seed, seat, mode, None))
    return jobs


def h2h_jobs():
    jobs = []
    seed_sets = {"fixed": range(1309400, 1309404), "natural": range(1309500, 1309504)}
    for opponent_name in ("current_best", "v2"):
        for mode, seeds in seed_sets.items():
            for seed in seeds:
                for seat in (0, 1):
                    jobs.append(("h2h", "shop_router_0909", SELECTED, opponent_name, OPPONENTS[opponent_name], seed, seat, mode, None))
    return jobs


def oracle_jobs():
    jobs = []
    for plan in range(13):
        for opponent_name in ("current_best", "k3"):
            for seat in (0, 1):
                jobs.append(("oracle", f"forced_plan_{plan}", SELECTED, opponent_name, OPPONENTS[opponent_name], 1309300, seat, "natural", plan))
    return jobs


def summarize(rows):
    output = {}
    grouped = defaultdict(list)
    for row in rows:
        if row.get("runtime_error"):
            continue
        grouped[(row["candidate"], row["opponent"], row["shop_mode"])].append(row)
    for key, group in sorted(grouped.items()):
        advantages = [row["advantage"] for row in group]
        own = [row["own_money"] for row in group]
        output["|".join(key)] = {
            "games": len(group),
            "wins": sum(row["outcome"] == "win" for row in group),
            "losses": sum(row["outcome"] == "loss" for row in group),
            "ties": sum(row["outcome"] == "tie" for row in group),
            "mean_own_money": statistics.fmean(own),
            "median_own_money": statistics.median(own),
            "mean_advantage": statistics.fmean(advantages),
            "median_advantage": statistics.median(advantages),
            "p10_advantage": percentile(advantages, 0.10),
            "worst_advantage": min(advantages),
        }
    return output


def compatibility_reuse():
    module, candidate = load_agent(SELECTED, "sequential_reuse")
    rows = []
    for seed, seat in ((1309600, 0), (1309601, 1), (1309602, 0), (1309603, 1)):
        calls = 0
        failures = []

        def checked(observation):
            nonlocal calls
            action = candidate(observation)
            calls += 1
            try:
                semantic_validate(observation, action)
            except Exception as exc:
                failures.append({"step": int(observation["step"]), "error": repr(exc)})
            return action

        pair = ["random", "random"]
        pair[seat] = checked
        env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=False)
        env.run(pair)
        final = env.steps[-1]
        rows.append({
            "seed": seed,
            "seat": seat,
            "steps": len(env.steps),
            "calls": calls,
            "semantic_failures": failures,
            "status": [state.status for state in final],
            "own_money": float(final[seat].reward),
            "opponent_money": float(final[1 - seat].reward),
        })
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--stage", choices=("league", "h2h", "oracle", "all"), default="all")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = []
    if args.stage in ("league", "all"):
        jobs.extend(league_jobs())
    if args.stage in ("h2h", "all"):
        jobs.extend(h2h_jobs())
    if args.stage in ("oracle", "all"):
        jobs.extend(oracle_jobs())
    rows = []
    with ProcessPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(run_game, job): job for job in jobs}
        for future in as_completed(futures):
            rows.append(future.result())
            if len(rows) % 25 == 0 or len(rows) == len(jobs):
                print(f"completed {len(rows)}/{len(jobs)}", flush=True)
    rows.sort(key=lambda row: (
        row["stage"], row["candidate"], row["opponent"], row["shop_mode"], row["seed"], row["seat"]
    ))
    payload = {
        "schema_version": 1,
        "design": "Exact score-linked Shop Router 0909 v1; fresh module per game; identical seeds, both seats, fixed and natural shops.",
        "source_hashes": {
            "main.py": sha256(SELECTED),
            "actions.json": sha256(SELECTED.parent / "actions.json"),
            "LICENSE.txt": sha256(SELECTED.parent / "LICENSE.txt"),
        },
        "job_count": len(jobs),
        "rows": rows,
        "summary": summarize(rows),
        "compatibility_reuse": compatibility_reuse() if args.stage == "all" else [],
    }
    (OUT / f"{args.stage}_results.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    failures = [row for row in rows if row.get("runtime_error") or row.get("semantic_failures") or row.get("exceptions")]
    print(json.dumps({"jobs": len(jobs), "failures": len(failures), "output": str(OUT / f"{args.stage}_results.json")}, indent=2))


if __name__ == "__main__":
    main()
