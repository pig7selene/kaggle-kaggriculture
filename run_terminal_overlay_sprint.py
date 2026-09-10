"""Fast 1.32.7-only terminal-overlay evaluation with prefix-identity auditing."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import time

from kaggle_environments import make

from run_lb_gap_forensics import market_events, terminal_trace
from run_raw55899537_final_validation import animal_escapes, economic_summary, terminal_value
from run_epic_experiments import _run_with_fixed_shops


ROOT = Path(__file__).resolve().parent
EXP = ROOT / "experiments"
TMP = Path("/private/tmp/lb_gap_opponents")
FROZEN = ROOT / "agents/shop_router_0909_hardened/main.py"

CANDIDATES = {
    "terminal_a": ROOT / "agents/shop_router_0909_terminal_a_most_powerfull/main.py",
    "terminal_b": ROOT / "agents/shop_router_0909_terminal_b_market_smart/main.py",
    "terminal_c": ROOT / "agents/shop_router_0909_terminal_c_seven_turn/main.py",
    "terminal_d": ROOT / "agents/shop_router_0909_terminal_d_market_smart_2pass/main.py",
    "terminal_e": ROOT / "agents/shop_router_0909_terminal_e_market_smart_708/main.py",
    "terminal_f": ROOT / "agents/shop_router_0909_terminal_f_market_smart_711/main.py",
}
OPPONENTS = {
    "market_smart_terminal": TMP / "market_smart/main.py",
    "most_powerfull_terminal": TMP / "most_powerfull/main.py",
    "farming_v3_current": TMP / "farming_v3_current/main.py",
    "shape_shop_current": TMP / "shape_shop_current/main.py",
    "previous_current_best": ROOT / "agents/top50_distilled/top50_observable_portfolio.py",
    "v2": ROOT / "agents/super_replay_v2/super_backbone_v2.py",
}

KNOWN_SEEDS = (2609100, 2609101, 2609102, 2609103, 2609104)
FRESH_SEEDS = (2609300, 2609301, 2609302, 2609303)
SMOKE_SEEDS = (2609400, 2609401)


def load_agent(path: Path, tag: str):
    name = f"terminal_sprint_{tag}_{time.time_ns()}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module, module.agent


def fixed_schedule(first, second):
    return {day: ([first] if day >= 3 else []) + ([second] if day >= 6 else []) for day in range(30)}


def job_key(row):
    return (row["candidate"], row["opponent"], row["seed"], row["seat"], tuple(row.get("fixed_pair") or ()))


def execute(job):
    stage, candidate_name, opponent_name, seed, seat, fixed_pair = job
    started = time.perf_counter()
    candidate_path = FROZEN if candidate_name == "frozen_control" else CANDIDATES[candidate_name]
    candidate_module, candidate = load_agent(candidate_path, f"candidate_{candidate_name}_{seed}_{seat}")
    _, frozen = load_agent(FROZEN, f"frozen_audit_{candidate_name}_{seed}_{seat}")
    _, opponent = load_agent(OPPONENTS[opponent_name], f"opponent_{opponent_name}_{seed}_{seat}")
    prefix_mismatches, candidate_errors, frozen_errors = [], [], []

    def audited(obs, config=None):
        step = int(obs["step"])
        try:
            action = candidate(obs, config)
        except Exception as exc:
            candidate_errors.append({"step": step, "error": repr(exc)})
            raise
        try:
            expected = frozen(deepcopy(obs), config)
        except Exception as exc:
            frozen_errors.append({"step": step, "error": repr(exc)})
            raise
        prefix_cutoff = 707 if candidate_name == "terminal_e" else 710 if candidate_name == "terminal_f" else 711
        if step <= prefix_cutoff and action != expected:
            prefix_mismatches.append({"step": step, "candidate": action, "frozen": expected})
        return action

    pair = [opponent, opponent]
    pair[seat] = audited
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": int(seed)}, debug=False)
    run_error = None
    try:
        if fixed_pair:
            _run_with_fixed_shops(env, pair, fixed_schedule(*fixed_pair))
        else:
            env.run(pair)
    except Exception as exc:
        run_error = repr(exc)
    if run_error or len(env.steps) != 720:
        return {"stage":stage,"candidate":candidate_name,"opponent":opponent_name,"seed":seed,"seat":seat,"fixed_pair":list(fixed_pair) if fixed_pair else None,"runtime_error":run_error or f"steps={len(env.steps)}","candidate_errors":candidate_errors,"frozen_errors":frozen_errors,"prefix_mismatches":prefix_mismatches,"elapsed_s":time.perf_counter()-started}
    replay = env.toJSON()
    final = env.steps[-1]
    own, other = float(final[seat].reward), float(final[1-seat].reward)
    telemetry = deepcopy(getattr(getattr(candidate_module, "_candidate", None), "telemetry", {}))
    return {
        "stage":stage,"candidate":candidate_name,"opponent":opponent_name,"seed":int(seed),"seat":int(seat),
        "fixed_pair":list(fixed_pair) if fixed_pair else None,"shop_mode":"fixed" if fixed_pair else "natural",
        "shop_pair":list(final[seat].observation["town"]["unlocked_shops"][:2]),
        "own_money":own,"opponent_money":other,"advantage":own-other,
        "outcome":"win" if own>other else "loss" if own<other else "tie",
        "runtime_error":None,"candidate_errors":candidate_errors,"frozen_errors":frozen_errors,
        "prefix_calls_checked":708 if candidate_name == "terminal_e" else 711 if candidate_name == "terminal_f" else 712,"prefix_mismatches":prefix_mismatches,
        "livestock_escapes":animal_escapes(env.steps,seat),
        "candidate_economics":economic_summary(replay,seat),
        "candidate_terminal":terminal_value(final,seat),
        "terminal_trace":terminal_trace(replay,seat),
        "market_events":market_events(replay,seat),
        "telemetry":telemetry,
        "statuses":[str(final[i].status) for i in range(2)],
        "elapsed_s":time.perf_counter()-started,
    }


def jobs(stage):
    if stage == "known":
        return [(stage,c,o,s,seat,None) for c in CANDIDATES for o in ("market_smart_terminal","most_powerfull_terminal","farming_v3_current","shape_shop_current") for s in KNOWN_SEEDS for seat in (0,1)]
    if stage == "prefix_plan10":
        return [(stage,c,"v2",2609500,seat,("YARN_STORE","PET_CAFE")) for c in CANDIDATES for seat in (0,1)]
    if stage == "validation":
        fresh = [(stage,c,o,s,seat,None) for c in ("terminal_d","frozen_control") for o in ("market_smart_terminal","most_powerfull_terminal") for s in FRESH_SEEDS for seat in (0,1)]
        smoke = [(stage,c,o,s,seat,None) for c in ("terminal_d","frozen_control") for o in ("farming_v3_current","shape_shop_current","previous_current_best","v2") for s in SMOKE_SEEDS for seat in (0,1)]
        return fresh + smoke
    if stage.startswith("fresh_"):
        c=stage.removeprefix("fresh_")
        return [(stage,c,o,s,seat,None) for o in ("market_smart_terminal","most_powerfull_terminal") for s in FRESH_SEEDS for seat in (0,1)]
    if stage.startswith("smoke_"):
        c=stage.removeprefix("smoke_")
        return [(stage,c,o,s,seat,None) for o in ("farming_v3_current","shape_shop_current","previous_current_best","v2") for s in SMOKE_SEEDS for seat in (0,1)]
    raise KeyError(stage)


def run(stage, workers):
    path=EXP/f"terminal_overlay_{stage}.partial.json"
    prior=json.loads(path.read_text()) if path.exists() else {"schema_version":1,"stage":stage,"rows":[]}
    rows=[r for r in prior["rows"] if not r.get("runtime_error")]
    done={job_key(r) for r in rows}
    pending=[j for j in jobs(stage) if (j[1],j[2],j[3],j[4],tuple(j[5] or ())) not in done]
    if not pending:
        print(f"{stage}: already complete {len(rows)}/{len(jobs(stage))}")
        return
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures=[pool.submit(execute,j) for j in pending]
        for f in as_completed(futures):
            rows.append(f.result())
            if len(rows)%4==0 or len(rows)==len(jobs(stage)):
                rows.sort(key=job_key)
                path.write_text(json.dumps({"schema_version":1,"stage":stage,"expected_games":len(jobs(stage)),"rows":rows},indent=2,sort_keys=True)+"\n")
                print(f"{stage}: {len(rows)}/{len(jobs(stage))}",flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("stage")
    parser.add_argument("--workers",type=int,default=6)
    args=parser.parse_args()
    run(args.stage,args.workers)


if __name__ == "__main__":
    main()
