"""Small checkpoint counterfactual for the CurrentBest-preserving overlay."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics

from kaggle_environments import make

from run_checkpoint_executor_resume import BASELINE_PATH, _validate


ROOT = Path(__file__).resolve().parent
CANDIDATE_PATH = "agents/economic_program/currentbest_overlay_v1.py"


def _module(path, tag):
    absolute = (ROOT / path).resolve()
    name = f"overlay_{tag}_{hashlib.sha256(str(absolute).encode()).hexdigest()[:10]}"
    spec = importlib.util.spec_from_file_location(name, absolute)
    if spec is None or spec.loader is None:
        raise ImportError(absolute)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_full(seed, seat):
    own = _module(BASELINE_PATH, f"fullown_{seed}_{seat}")
    opponent = _module(BASELINE_PATH, f"fullopp_{seed}_{seat}")
    pair = [opponent.agent, opponent.agent]
    pair[int(seat)] = own.agent
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": int(seed)}, debug=False)
    runtime = None
    try:
        env.run(pair)
    except Exception as exc:
        runtime = repr(exc)
    if runtime or len(getattr(env, "steps", [])) != 720:
        return {"runtime_error": runtime or f"steps={len(getattr(env, 'steps', []))}", "semantic_failures": []}
    final = env.steps[-1]
    return {
        "runtime_error": None,
        "semantic_failures": [],
        "own_money": float(final[int(seat)].reward),
        "opponent_money": float(final[1 - int(seat)].reward),
        "advantage": float(final[int(seat)].reward) - float(final[1 - int(seat)].reward),
    }


def _run_overlay(seed, seat, checkpoint):
    opener = _module(BASELINE_PATH, f"open_{seed}_{seat}_{checkpoint}")
    candidate = _module(CANDIDATE_PATH, f"candidate_{seed}_{seat}_{checkpoint}")
    opponent = _module(BASELINE_PATH, f"opp_{seed}_{seat}_{checkpoint}")
    overlay = candidate.make_agent(opener.agent)
    semantic = []

    def controlled(obs):
        step = int(obs.get("step", 0))
        action = opener.agent(obs) if step < int(checkpoint) else overlay(obs)
        try:
            _validate(obs, action)
        except Exception as exc:
            semantic.append({"step": step, "error": repr(exc), "action": deepcopy(action)})
        return action

    pair = [opponent.agent, opponent.agent]
    pair[int(seat)] = controlled
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": int(seed)}, debug=False)
    runtime = None
    try:
        env.run(pair)
    except Exception as exc:
        runtime = repr(exc)
    if runtime or len(getattr(env, "steps", [])) != 720:
        return {
            "runtime_error": runtime or f"steps={len(getattr(env, 'steps', []))}",
            "semantic_failures": semantic,
            "telemetry": deepcopy(getattr(overlay, "telemetry", {})),
        }
    final = env.steps[-1]
    return {
        "runtime_error": None,
        "semantic_failures": semantic,
        "own_money": float(final[int(seat)].reward),
        "opponent_money": float(final[1 - int(seat)].reward),
        "advantage": float(final[int(seat)].reward) - float(final[1 - int(seat)].reward),
        "telemetry": deepcopy(getattr(overlay, "telemetry", {})),
    }


def _job(job):
    seed, seat, checkpoint = job
    baseline = _run_full(seed, seat)
    overlay = _run_overlay(seed, seat, checkpoint)
    row = {"seed": int(seed), "seat": int(seat), "checkpoint": int(checkpoint), "baseline": baseline, "overlay": overlay}
    if not baseline.get("runtime_error") and not overlay.get("runtime_error"):
        row["own_money_delta"] = overlay["own_money"] - baseline["own_money"]
        row["advantage_delta"] = overlay["advantage"] - baseline["advantage"]
    return row


def _summary(rows):
    valid = [r for r in rows if "own_money_delta" in r]
    deltas = [float(r["own_money_delta"]) for r in valid]
    return {
        "conditions": len(rows),
        "valid": len(valid),
        "runtime_failures": sum(bool(r.get("baseline", {}).get("runtime_error") or r.get("overlay", {}).get("runtime_error")) for r in rows),
        "semantic_failures": sum(len(r.get("baseline", {}).get("semantic_failures", [])) + len(r.get("overlay", {}).get("semantic_failures", [])) for r in rows),
        "mean_baseline_money": statistics.fmean(r["baseline"]["own_money"] for r in valid) if valid else None,
        "mean_overlay_money": statistics.fmean(r["overlay"]["own_money"] for r in valid) if valid else None,
        "mean_own_money_delta": statistics.fmean(deltas) if deltas else None,
        "median_own_money_delta": statistics.median(deltas) if deltas else None,
        "p10_own_money_delta": sorted(deltas)[max(0, int((len(deltas) - 1) * 0.10))] if deltas else None,
        "p5_own_money_delta": sorted(deltas)[max(0, int((len(deltas) - 1) * 0.05))] if deltas else None,
        "mean_advantage_delta": statistics.fmean(float(r["advantage_delta"]) for r in valid) if valid else None,
        "admissions": sum(int(r.get("overlay", {}).get("telemetry", {}).get("admissions", 0)) for r in valid),
        "admitted_conditions": sum(bool(r.get("overlay", {}).get("telemetry", {}).get("admissions", 0)) for r in valid),
        "admitted_realization": (
            statistics.fmean(float(r["overlay"].get("telemetry", {}).get("realization_rate", 0.0)) for r in valid if r.get("overlay", {}).get("telemetry", {}).get("admissions", 0))
            if any(r.get("overlay", {}).get("telemetry", {}).get("admissions", 0) for r in valid)
            else None
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", nargs="+", type=int, default=[57210, 57211, 57212, 57213])
    parser.add_argument("--checkpoints", nargs="+", type=int, default=[72])
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--output", default="experiments/currentbest_overlay_counterfactual.json")
    parser.add_argument("--partial", default="experiments/currentbest_overlay_counterfactual.partial.json")
    args = parser.parse_args()
    jobs = [(seed, seat, checkpoint) for checkpoint in args.checkpoints for seed in args.seeds for seat in (0, 1)]
    output = (ROOT / args.output).resolve()
    partial = (ROOT / args.partial).resolve()
    rows = []
    if partial.is_file():
        try:
            rows = json.loads(partial.read_text()).get("rows", [])
        except Exception:
            rows = []
    done = {(int(r.get("seed", -1)), int(r.get("seat", -1)), int(r.get("checkpoint", -1))) for r in rows}
    todo = [job for job in jobs if job not in done]
    print(f"Running {len(todo)} overlay conditions ({len(rows)} cached)", flush=True)
    with ProcessPoolExecutor(max_workers=max(1, int(args.workers))) as pool:
        futures = [pool.submit(_job, job) for job in todo]
        for index, future in enumerate(as_completed(futures), 1):
            rows.append(future.result())
            if index % 4 == 0 or index == len(futures):
                partial.parent.mkdir(parents=True, exist_ok=True)
                partial.write_text(json.dumps({"schema_version": 1, "rows": rows}, indent=2, sort_keys=True) + "\n")
                print(f"{index}/{len(futures)} complete", flush=True)
    rows.sort(key=lambda r: (int(r.get("checkpoint", -1)), int(r.get("seed", -1)), int(r.get("seat", -1))))
    payload = {
        "schema_version": 1,
        "design": "CurrentBest continuation with PASS-unit/market-slot bounded melon overlay",
        "baseline": BASELINE_PATH,
        "candidate": CANDIDATE_PATH,
        "seeds": [int(s) for s in args.seeds],
        "checkpoints": [int(c) for c in args.checkpoints],
        "rows": rows,
        "summary": _summary(rows),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(output)
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
