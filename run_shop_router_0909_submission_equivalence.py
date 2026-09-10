"""Strict behavioral-equivalence and reset tests for the final package."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tarfile
import tempfile
import time

from kaggle_environments import make

from run_epic_experiments import _independent_shop_schedule, _run_with_fixed_shops
from run_raw55899537_final_validation import animal_escapes


ROOT = Path(__file__).resolve().parent
RESEARCH = ROOT / "agents/shop_router_0909_hardened/main.py"
PACKAGE_MAIN = ROOT / "submission/main.py"
ARCHIVE = ROOT / "submission/shop_router_0909_hardened.tar.gz"
CURRENT = ROOT / "agents/top50_distilled/top50_observable_portfolio.py"
V2 = ROOT / "agents/super_replay_v2/super_backbone_v2.py"
K3 = ROOT / "agents/v27_k3_weed.py"
CROP_DUSTA = ROOT / "agents/top3_tuned/raw_rank2_crop_dusta.py"
OUT_ROUTE = ROOT / "experiments/shop_router_0909_submission_route_equivalence.json"
OUT_EQ = ROOT / "experiments/shop_router_0909_submission_equivalence.json"
RAW = ROOT / "experiments/shop_router_0909_submission_equivalence_raw.json"


PLAN_PAIRS = {
    0: ("BAKERY", "PET_CAFE"),
    1: ("YARN_STORE", "FARMERS_MARKET"),
    2: ("BAKERY", "PET_CAFE"),  # plan 2 is the universal tail at step 648
    3: ("BAKERY", "YARN_STORE"),
    4: ("BRUNCH_SPOT", "YARN_STORE"),
    5: ("FARMERS_MARKET", "YARN_STORE"),
    6: ("ICE_CREAM_SHOP", "YARN_STORE"),
    7: ("PIZZA_SHOP", "YARN_STORE"),
    8: ("SMOOTHIE_SHOP", "YARN_STORE"),
    9: ("YARN_STORE", "BAKERY"),
    10: ("YARN_STORE", "PET_CAFE"),
    11: ("YARN_STORE", "SMOOTHIE_SHOP"),
    12: ("YARN_STORE", "YARN_STORE"),
}


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def load_agent(path, tag):
    name = f"submission_eq_{tag}_{time.time_ns()}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, module.agent


def selected_plan(module, agent, player):
    if hasattr(agent, "exact_module"):
        return agent.exact_module._POLICY.players[player].plan
    return module._POLICY.players[player].plan


def fixed_pair_schedule(seed, pair):
    schedule = _independent_shop_schedule(seed)
    for day, shops in schedule.items():
        if day >= 3 and shops:
            shops[0] = pair[0]
        if day >= 6 and len(shops) >= 2:
            shops[1] = pair[1]
    return schedule


def run_capture(path, opponent_path, seed, seat, pair=None, persistent=None, tag="run"):
    if persistent is None:
        module, candidate = load_agent(path, f"candidate_{tag}")
    else:
        module, candidate = persistent
    if opponent_path is None:
        def opponent(_observation):
            return {"farmer": ["PASS"], "hands": [], "market": []}
    else:
        _, opponent = load_agent(opponent_path, f"opponent_{tag}")
    actions, plans, observations = [], [], []
    special = {}
    errors = []

    def checked(obs):
        try:
            action = candidate(obs)
        except Exception as exc:
            errors.append({"step": int(obs.get("step", -1)), "error": repr(exc)})
            raise
        step = int(obs["step"])
        player = int(obs["player"])
        actions.append(deepcopy(action))
        plans.append(selected_plan(module, candidate, player))
        observations.append(sha_bytes(json.dumps(obs, sort_keys=True, separators=(",", ":")).encode()))
        if step == 360:
            special["step_360_action"] = deepcopy(action)
        if step == 370:
            special["target_sheep_at_370"] = deepcopy(obs["farms"][player]["tiles"][4][7])
        return action

    agents = [opponent, opponent]
    agents[seat] = checked
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": int(seed)}, debug=False)
    runtime_error = None
    try:
        if pair is None:
            env.run(agents)
        else:
            _run_with_fixed_shops(env, agents, fixed_pair_schedule(seed, pair))
    except Exception as exc:
        runtime_error = repr(exc)
    if runtime_error or len(env.steps) != 720:
        return {"runtime_error": runtime_error or f"steps={len(env.steps)}", "agent_errors": errors}
    final = env.steps[-1]
    final_payload = [{"reward": state.reward, "status": state.status, "observation": state.observation} for state in final]
    return {
        "runtime_error": None,
        "agent_errors": errors,
        "actions": actions,
        "plans": plans,
        "observation_hashes": observations,
        "action_trace_sha256": sha_bytes(json.dumps(actions, sort_keys=True, separators=(",", ":")).encode()),
        "plan_trace_sha256": sha_bytes(json.dumps(plans, separators=(",", ":")).encode()),
        "final_state": final_payload,
        "final_state_sha256": sha_bytes(json.dumps(final_payload, sort_keys=True, separators=(",", ":")).encode()),
        "own_money": float(final[seat].reward),
        "opponent_money": float(final[1 - seat].reward),
        "advantage": float(final[seat].reward) - float(final[1 - seat].reward),
        "escapes": animal_escapes(env.steps, seat),
        "special": special,
    }


def compare_job(job):
    panel, case, expected_plan, pair, opponent_name, opponent_path, seed, seat = job
    research_module, research_agent = load_agent(RESEARCH, f"dual_research_{panel}_{case}_{seed}_{seat}")
    packaged_module, packaged_agent = load_agent(PACKAGE_MAIN, f"dual_package_{panel}_{case}_{seed}_{seat}")
    _, opponent = load_agent(opponent_path, f"dual_opponent_{panel}_{case}_{seed}_{seat}")
    research_actions, packaged_actions = [], []
    research_plans, packaged_plans = [], []
    action_steps, plan_steps = [], []
    research_errors, packaged_errors = [], []
    research_special, packaged_special = {}, {}

    def dual_checked(obs):
        step = int(obs["step"])
        player = int(obs["player"])
        try:
            research_action = research_agent(deepcopy(obs))
        except Exception as exc:
            research_errors.append({"step": step, "error": repr(exc)})
            raise
        try:
            packaged_action = packaged_agent(deepcopy(obs))
        except Exception as exc:
            packaged_errors.append({"step": step, "error": repr(exc)})
            raise
        research_plan = selected_plan(research_module, research_agent, player)
        packaged_plan = selected_plan(packaged_module, packaged_agent, player)
        research_actions.append(deepcopy(research_action))
        packaged_actions.append(deepcopy(packaged_action))
        research_plans.append(research_plan)
        packaged_plans.append(packaged_plan)
        if research_action != packaged_action:
            action_steps.append(step)
        if research_plan != packaged_plan:
            plan_steps.append(step)
        if step == 360:
            research_special["step_360_action"] = deepcopy(research_action)
            packaged_special["step_360_action"] = deepcopy(packaged_action)
        if step == 370:
            target = deepcopy(obs["farms"][player]["tiles"][4][7])
            research_special["target_sheep_at_370"] = target
            packaged_special["target_sheep_at_370"] = deepcopy(target)
        # The research action drives the one shared environment. A mismatch is
        # recorded as a packaging failure; when none exists both policies imply
        # the exact same transition and final state from identical observations.
        return research_action

    agents = [opponent, opponent]
    agents[seat] = dual_checked
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": int(seed)}, debug=False)
    runtime_error = None
    try:
        if pair is None:
            env.run(agents)
        else:
            _run_with_fixed_shops(env, agents, fixed_pair_schedule(seed, pair))
    except Exception as exc:
        runtime_error = repr(exc)
    if runtime_error or len(env.steps) != 720:
        return {"panel": panel, "case": case, "expected_plan": expected_plan, "pair": pair,
                "opponent": opponent_name, "seed": seed, "seat": seat,
                "research_runtime_error": runtime_error, "packaged_runtime_error": runtime_error,
                "research_agent_errors": research_errors, "packaged_agent_errors": packaged_errors,
                "comparison_failed": True}
    final = env.steps[-1]
    final_payload = [{"reward": state.reward, "status": state.status, "observation": state.observation} for state in final]
    final_hash = sha_bytes(json.dumps(final_payload, sort_keys=True, separators=(",", ":")).encode())
    escapes = animal_escapes(env.steps, seat)
    plan_probe_step = 648 if expected_plan == 2 else 144
    return {
        "panel": panel, "case": case, "expected_plan": expected_plan, "pair": pair,
        "opponent": opponent_name, "seed": seed, "seat": seat,
        "research_action_sha256": sha_bytes(json.dumps(research_actions, sort_keys=True, separators=(",", ":")).encode()),
        "packaged_action_sha256": sha_bytes(json.dumps(packaged_actions, sort_keys=True, separators=(",", ":")).encode()),
        "research_final_state_sha256": final_hash,
        "packaged_final_state_sha256": final_hash if not action_steps else None,
        "expected_plan_observed_research": research_plans[plan_probe_step],
        "expected_plan_observed_packaged": packaged_plans[plan_probe_step],
        "plan_mismatch_count": len(plan_steps), "plan_mismatch_steps": plan_steps,
        "action_mismatch_count": len(action_steps), "action_mismatch_steps": action_steps,
        "observation_mismatch_count": 0, "observation_mismatch_steps": [],
        "identical_observation_calls": len(research_actions),
        "final_state_equal": not action_steps,
        "final_money_equal": not action_steps,
        "own_money": float(final[seat].reward), "opponent_money": float(final[1 - seat].reward),
        "advantage": float(final[seat].reward) - float(final[1 - seat].reward),
        "research_escapes": escapes, "packaged_escapes": escapes if not action_steps else [],
        "research_special": research_special, "packaged_special": packaged_special,
        "research_runtime_error": None, "packaged_runtime_error": None,
        "research_agent_errors": research_errors, "packaged_agent_errors": packaged_errors,
        "comparison_failed": False,
    }


def build_jobs():
    jobs = []
    for plan, pair in PLAN_PAIRS.items():
        seed = 1309401 if plan == 10 else 1320000 + plan
        for seat in (0, 1):
            jobs.append(("all_routes", f"plan_{plan}", plan, pair, "current_best", CURRENT, seed, seat))
    natural_opponents = (("current_best", CURRENT), ("v2", V2), ("k3", K3), ("crop_dusta", CROP_DUSTA))
    for opponent_name, opponent_path in natural_opponents:
        for seed in (1321000, 1321001):
            for seat in (0, 1):
                jobs.append(("natural", f"natural_{opponent_name}", None, None, opponent_name, opponent_path, seed, seat))
    return jobs


def summarize(rows):
    return {
        "games": len(rows),
        "plan_selection_mismatches": sum(row.get("plan_mismatch_count", 0) for row in rows),
        "action_mismatches": sum(row.get("action_mismatch_count", 0) for row in rows),
        "observation_mismatches": sum(row.get("observation_mismatch_count", 0) for row in rows),
        "final_state_mismatches": sum(not row.get("final_state_equal", False) for row in rows),
        "final_money_mismatches": sum(not row.get("final_money_equal", False) for row in rows),
        "runtime_exceptions": sum(bool(row.get("research_runtime_error") or row.get("packaged_runtime_error")) for row in rows),
        "agent_exceptions": sum(bool(row.get("research_agent_errors") or row.get("packaged_agent_errors")) for row in rows),
    }


def import_tests():
    repo_import = subprocess.run(
        [sys.executable, "-c", "from submission.main import agent; assert callable(agent)"],
        cwd=ROOT, capture_output=True, text=True,
    )
    with tempfile.TemporaryDirectory(prefix="shop0909_clean_", dir="/tmp") as folder:
        extract = Path(folder) / "package"
        extract.mkdir()
        with tarfile.open(ARCHIVE, "r:gz") as archive:
            archive.extractall(extract, filter="data")
        clean_import = subprocess.run(
            [sys.executable, "-c", "import importlib.util; s=importlib.util.spec_from_file_location('agentpkg','package/main.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); assert callable(m.agent)"],
            cwd=folder, capture_output=True, text=True,
        )
        package_capture = run_capture(PACKAGE_MAIN, None, 1321500, 0, PLAN_PAIRS[10], tag="clean_reference")
        old_cwd = Path.cwd()
        try:
            os.chdir(folder)
            clean_capture = run_capture(extract / "main.py", None, 1321500, 0, PLAN_PAIRS[10], tag="clean_extracted")
        finally:
            os.chdir(old_cwd)
    return {
        "repository_import": {"passed": repo_import.returncode == 0, "stderr": repo_import.stderr},
        "clean_directory_import": {"passed": clean_import.returncode == 0, "stderr": clean_import.stderr},
        "clean_directory_full_game": {
            "passed": package_capture.get("action_trace_sha256") == clean_capture.get("action_trace_sha256")
                      and package_capture.get("final_state_sha256") == clean_capture.get("final_state_sha256"),
            "reference_action_sha256": package_capture.get("action_trace_sha256"),
            "extracted_action_sha256": clean_capture.get("action_trace_sha256"),
            "reference_final_state_sha256": package_capture.get("final_state_sha256"),
            "extracted_final_state_sha256": clean_capture.get("final_state_sha256"),
            "runtime_exceptions": sum(bool(x.get("runtime_error")) for x in (package_capture, clean_capture)),
            "agent_exceptions": sum(bool(x.get("agent_errors")) for x in (package_capture, clean_capture)),
        },
    }


def reset_test():
    persistent = load_agent(PACKAGE_MAIN, "persistent_four_games")
    cases = [
        ("A", CURRENT, 1321600, 0, PLAN_PAIRS[0]),
        ("B", CURRENT, 1309401, 1, PLAN_PAIRS[10]),
        ("C", V2, 1321602, 0, None),
        ("D", K3, 1321603, 1, PLAN_PAIRS[12]),
    ]
    rows = []
    for label, opponent, seed, seat, pair in cases:
        carried = run_capture(PACKAGE_MAIN, opponent, seed, seat, pair, persistent=persistent, tag=f"persistent_{label}")
        fresh = run_capture(PACKAGE_MAIN, opponent, seed, seat, pair, tag=f"fresh_{label}")
        rows.append({
            "game": label, "seed": seed, "seat": seat, "pair": pair,
            "action_equal": carried.get("action_trace_sha256") == fresh.get("action_trace_sha256"),
            "plan_equal": carried.get("plan_trace_sha256") == fresh.get("plan_trace_sha256"),
            "final_state_equal": carried.get("final_state_sha256") == fresh.get("final_state_sha256"),
            "runtime_exceptions": sum(bool(x.get("runtime_error")) for x in (carried, fresh)),
            "agent_exceptions": sum(bool(x.get("agent_errors")) for x in (carried, fresh)),
        })
    return {
        "games_without_module_reload": 4,
        "all_equal_to_fresh_import": all(row["action_equal"] and row["plan_equal"] and row["final_state_equal"] for row in rows),
        "runtime_exceptions": sum(row["runtime_exceptions"] for row in rows),
        "agent_exceptions": sum(row["agent_exceptions"] for row in rows),
        "rows": rows,
    }


def main():
    jobs = build_jobs()
    rows = []
    with ProcessPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(compare_job, job) for job in jobs]
        for future in as_completed(futures):
            rows.append(future.result())
            if len(rows) % 10 == 0 or len(rows) == len(jobs):
                print(f"equivalence {len(rows)}/{len(jobs)}", flush=True)
    rows.sort(key=lambda row: (row["panel"], row["case"], row["seed"], row["seat"]))
    route_rows = [row for row in rows if row["panel"] == "all_routes"]
    general = summarize(rows)
    route = summarize(route_rows)
    for row in route_rows:
        if row["expected_plan_observed_research"] != row["expected_plan"] or row["expected_plan_observed_packaged"] != row["expected_plan"]:
            raise RuntimeError(f"forced plan did not activate: {row}")
    imports = import_tests()
    reset = reset_test()
    plan10_rows = [row for row in route_rows if row["expected_plan"] == 10]
    plan10 = {
        "games": len(plan10_rows),
        "step_360_research_actions": [row["research_special"].get("step_360_action") for row in plan10_rows],
        "step_360_packaged_actions": [row["packaged_special"].get("step_360_action") for row in plan10_rows],
        "target_sheep_fed_at_observation_370": [bool(row["packaged_special"].get("target_sheep_at_370", {}).get("fed_today")) for row in plan10_rows],
        "research_escape_events": sum(len(row["research_escapes"]) for row in plan10_rows),
        "packaged_escape_events": sum(len(row["packaged_escapes"]) for row in plan10_rows),
    }
    payload = {"schema_version": 1, "design": "42 paired games: 13 forced plan cases x both seats plus 16 natural games across four opponents.", "summary": general, "import_tests": imports, "multi_game_reset": reset, "plan10_regression": plan10, "rows": rows}
    RAW.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    OUT_ROUTE.write_text(json.dumps({"schema_version": 1, "plans_tested": list(range(13)), "summary": route, "rows": route_rows}, indent=2, sort_keys=True) + "\n")
    OUT_EQ.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    mismatch_fields = {key: value for key, value in general.items() if key != "games"}
    passed = (
        not any(mismatch_fields.values())
        and imports["repository_import"]["passed"]
        and imports["clean_directory_import"]["passed"]
        and imports["clean_directory_full_game"]["passed"]
        and reset["all_equal_to_fresh_import"]
        and all(action["farmer"] == ["PICKUP", "WHEAT", 4] for action in plan10["step_360_packaged_actions"])
        and all(plan10["target_sheep_fed_at_observation_370"])
        and plan10["packaged_escape_events"] == 0
    )
    print(json.dumps({"passed": passed, "summary": general, "plan10": plan10, "imports": imports, "reset": {k: v for k, v in reset.items() if k != "rows"}}, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
