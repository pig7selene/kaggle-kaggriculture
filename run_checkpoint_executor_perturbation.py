"""Perturbation-gate harness for the checkpoint executor.

Perturbations are action-level and therefore produce valid simulator states:
one legal baseline action is replaced by PASS or one legal market order is
omitted immediately before takeover.  The executor must still protect live
commitments and finish without semantic/runtime failures.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import json
from pathlib import Path
import statistics

from kaggle_environments import make

from run_checkpoint_executor_resume import (
    BASELINE_PATH,
    EXECUTOR_PATH,
    UNIT_OPS,
    MARKET_OPS,
    _animal_count,
    _load,
    _terminal_value,
    _validate,
)


ROOT = Path(__file__).resolve().parent


def _perturb(action, kind):
    out = deepcopy(action)
    if kind == "farmer_pass":
        out["farmer"] = ["PASS"]
        return out, True
    if kind == "skip_water":
        if out.get("farmer", [None])[0] == "WATER":
            out["farmer"] = ["PASS"]
            return out, True
        for i, value in enumerate(out.get("hands", [])):
            if value and value[0] == "WATER":
                out["hands"][i] = ["PASS"]
                return out, True
        return out, False
    if kind == "omit_sell":
        for i, order in enumerate(out.get("market", [])):
            if order and order[0] == "SELL":
                del out["market"][i]
                return out, True
        return out, False
    if kind == "omit_buy_product":
        for i, order in enumerate(out.get("market", [])):
            if order and order[0] == "BUY_PRODUCT":
                del out["market"][i]
                return out, True
        return out, False
    raise ValueError(kind)


def _run(job):
    seed, seat, checkpoint, perturbation = job
    base = _load(BASELINE_PATH, f"pert_base_{seed}_{seat}_{checkpoint}_{perturbation}")
    opponent = _load(BASELINE_PATH, f"pert_opp_{seed}_{seat}_{checkpoint}_{perturbation}")
    executor = _load(EXECUTOR_PATH, f"pert_exec_{seed}_{seat}_{checkpoint}_{perturbation}")
    semantic = []
    changed = False
    perturb_window_start = max(0, int(checkpoint) - 24)

    def controlled(obs):
        nonlocal changed
        step = int(obs.get("step", 0))
        if step < checkpoint:
            action = base(obs)
            if perturbation == "farmer_pass":
                if step == checkpoint - 1 and not changed:
                    action, changed = _perturb(action, perturbation)
            elif not changed and perturb_window_start <= step < checkpoint:
                # Use the first matching action in the preceding day.  Some
                # checkpoints have no WATER/SELL/BUY_PRODUCT exactly one turn
                # before takeover; scanning the valid window keeps the
                # perturbation genuine without editing simulator state.
                candidate, did_change = _perturb(action, perturbation)
                if did_change:
                    action, changed = candidate, True
        else:
            action = executor(obs)
        try:
            _validate(obs, action)
        except Exception as exc:
            semantic.append({"step": step, "error": repr(exc), "action": deepcopy(action)})
        return action

    pair = [opponent, opponent]
    pair[int(seat)] = controlled
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": int(seed)}, debug=False)
    runtime = None
    try:
        env.run(pair)
    except Exception as exc:
        runtime = repr(exc)
    if runtime or len(getattr(env, "steps", [])) != 720:
        return {
            "seed": int(seed), "seat": int(seat), "checkpoint": int(checkpoint),
            "perturbation": perturbation, "changed": changed,
            "runtime_error": runtime or f"steps={len(getattr(env, 'steps', []))}",
            "semantic_failures": semantic,
        }
    final = env.steps[-1]
    own = float(final[int(seat)].reward)
    rival = float(final[1 - int(seat)].reward)
    counts = [_animal_count(step_states[int(seat)], int(seat)) for step_states in env.steps]
    return {
        "seed": int(seed), "seat": int(seat), "checkpoint": int(checkpoint),
        "perturbation": perturbation, "changed": changed,
        "runtime_error": None, "semantic_failures": semantic,
        "own_money": own, "opponent_money": rival, "advantage": own - rival,
        "animal_max": max(counts), "animal_final": counts[-1],
        "animal_loss": counts[-1] < max(counts),
        "terminal_value": _terminal_value(final[int(seat)], int(seat)),
        "telemetry": deepcopy(getattr(executor, "telemetry", {})),
    }


def _stats(rows):
    valid = [r for r in rows if not r.get("runtime_error") and r.get("own_money") is not None]
    return {
        "conditions": len(valid),
        "changed_conditions": sum(bool(r.get("changed")) for r in valid),
        "runtime_failures": sum(bool(r.get("runtime_error")) for r in rows),
        "semantic_failures": sum(len(r.get("semantic_failures", [])) for r in rows),
        "animal_loss_games": sum(bool(r.get("animal_loss")) for r in valid),
        "terminal_stranding_games": sum(float(r.get("terminal_value", 0.0)) > 0.0 for r in valid),
        "mean_own_money": statistics.fmean(r["own_money"] for r in valid) if valid else None,
        "mean_advantage": statistics.fmean(r["advantage"] for r in valid) if valid else None,
        "p10_advantage": _percentile([r["advantage"] for r in valid], 0.10),
        "mean_terminal_value": statistics.fmean(r.get("terminal_value", 0.0) for r in valid) if valid else None,
        "recovery_events": sum(int((r.get("telemetry") or {}).get("recovery_events", 0)) for r in valid),
    }


def _percentile(values, q):
    values = sorted(float(v) for v in values)
    if not values:
        return None
    pos = (len(values) - 1) * q
    lo = int(pos)
    hi = min(len(values) - 1, lo + 1)
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", nargs="+", type=int, default=[52000, 52001])
    parser.add_argument("--checkpoints", nargs="+", type=int, default=[24, 72, 120])
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--output", default="experiments/checkpoint_executor_perturbation_results.json")
    args = parser.parse_args()
    perturbations = ("farmer_pass", "skip_water", "omit_sell", "omit_buy_product")
    jobs = [(seed, seat, checkpoint, perturbation)
            for checkpoint in args.checkpoints
            for seed in args.seeds
            for seat in (0, 1)
            for perturbation in perturbations]
    rows = []
    with ProcessPoolExecutor(max_workers=max(1, int(args.workers))) as pool:
        futures = [pool.submit(_run, job) for job in jobs]
        for i, future in enumerate(as_completed(futures), 1):
            rows.append(future.result())
            if i % 16 == 0 or i == len(futures):
                print(f"{i}/{len(futures)} complete", flush=True)
    rows.sort(key=lambda r: (int(r.get("checkpoint", -1)), int(r.get("seed", -1)), int(r.get("seat", -1)), r.get("perturbation", "")))
    by_type = {kind: _stats([r for r in rows if r.get("perturbation") == kind]) for kind in perturbations}
    payload = {
        "schema_version": 1,
        "design": "valid action-level perturbations immediately before checkpoint takeover",
        "seeds": [int(s) for s in args.seeds],
        "checkpoints": [int(c) for c in args.checkpoints],
        "perturbations": list(perturbations),
        "baseline": BASELINE_PATH, "executor": EXECUTOR_PATH,
        "rows": rows, "by_perturbation": by_type, "overall": _stats(rows),
    }
    output = (ROOT / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(output)
    for key, value in by_type.items():
        print(key, value, flush=True)


if __name__ == "__main__":
    main()
