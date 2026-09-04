"""Compare the economic-program takeover with an uninterrupted CurrentBest.

Each row uses the same deterministic seed, seat, opener, and opponent.  The
only difference is whether the controlled player continues CurrentBest for the
whole episode or hands control to the research executor at a checkpoint.
This is intentionally a small, resumable counterfactual screen rather than a
promotion benchmark.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import json
from pathlib import Path

from kaggle_environments import make

from run_checkpoint_executor_resume import BASELINE_PATH, _load, _validate


ROOT = Path(__file__).resolve().parent
CANDIDATE_PATH = "agents/economic_program/economic_program_executor_v1.py"


def _run_baseline(seed, seat):
    own = _load(BASELINE_PATH, f"cf_base_own_{seed}_{seat}")
    opponent = _load(BASELINE_PATH, f"cf_base_opp_{seed}_{seat}")
    pair = [opponent, opponent]
    pair[int(seat)] = own
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": int(seed)}, debug=False)
    runtime = None
    try:
        env.run(pair)
    except Exception as exc:
        runtime = repr(exc)
    if runtime or len(getattr(env, "steps", [])) != 720:
        return {
            "runtime_error": runtime or f"steps={len(getattr(env, 'steps', []))}",
            "semantic_failures": [],
        }
    final = env.steps[-1]
    return {
        "runtime_error": None,
        "semantic_failures": [],
        "own_money": float(final[int(seat)].reward),
        "opponent_money": float(final[1 - int(seat)].reward),
        "advantage": float(final[int(seat)].reward) - float(final[1 - int(seat)].reward),
    }


def _run_candidate(seed, seat, checkpoint):
    opener = _load(BASELINE_PATH, f"cf_open_{seed}_{seat}_{checkpoint}")
    candidate = _load(CANDIDATE_PATH, f"cf_candidate_{seed}_{seat}_{checkpoint}")
    opponent = _load(BASELINE_PATH, f"cf_opp_{seed}_{seat}_{checkpoint}")
    semantic = []

    def controlled(obs):
        step = int(obs.get("step", 0))
        action = opener(obs) if step < int(checkpoint) else candidate(obs)
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
            "runtime_error": runtime or f"steps={len(getattr(env, 'steps', []))}",
            "semantic_failures": semantic,
            "telemetry": deepcopy(getattr(candidate, "telemetry", {})),
        }
    final = env.steps[-1]
    return {
        "runtime_error": None,
        "semantic_failures": semantic,
        "own_money": float(final[int(seat)].reward),
        "opponent_money": float(final[1 - int(seat)].reward),
        "advantage": float(final[int(seat)].reward) - float(final[1 - int(seat)].reward),
        "telemetry": deepcopy(getattr(candidate, "telemetry", {})),
    }


def _job(job):
    seed, seat, checkpoint = job
    baseline = _run_baseline(seed, seat)
    candidate = _run_candidate(seed, seat, checkpoint)
    row = {
        "seed": int(seed),
        "seat": int(seat),
        "checkpoint": int(checkpoint),
        "baseline": baseline,
        "candidate": candidate,
    }
    if not baseline.get("runtime_error") and not candidate.get("runtime_error"):
        row["own_money_delta"] = candidate["own_money"] - baseline["own_money"]
        row["advantage_delta"] = candidate["advantage"] - baseline["advantage"]
    return row


def _percentile(values, q):
    values = sorted(float(v) for v in values)
    if not values:
        return None
    position = (len(values) - 1) * float(q)
    low = int(position)
    high = min(len(values) - 1, low + 1)
    return values[low] + (values[high] - values[low]) * (position - low)


def _summary(rows):
    valid = [r for r in rows if "own_money_delta" in r]
    deltas = [float(r["own_money_delta"]) for r in valid]
    advantages = [float(r["advantage_delta"]) for r in valid]
    return {
        "conditions": len(rows),
        "valid": len(valid),
        "runtime_failures": sum(
            bool(r.get("baseline", {}).get("runtime_error") or r.get("candidate", {}).get("runtime_error"))
            for r in rows
        ),
        "semantic_failures": sum(
            len(r.get("baseline", {}).get("semantic_failures", []))
            + len(r.get("candidate", {}).get("semantic_failures", []))
            for r in rows
        ),
        "mean_baseline_money": sum(r["baseline"]["own_money"] for r in valid) / len(valid) if valid else None,
        "mean_candidate_money": sum(r["candidate"]["own_money"] for r in valid) / len(valid) if valid else None,
        "mean_own_money_delta": sum(deltas) / len(deltas) if deltas else None,
        "median_own_money_delta": __import__("statistics").median(deltas) if deltas else None,
        "p10_own_money_delta": _percentile(deltas, 0.10),
        "p5_own_money_delta": _percentile(deltas, 0.05),
        "mean_advantage_delta": sum(advantages) / len(advantages) if advantages else None,
        "admissions": sum(int(r.get("candidate", {}).get("telemetry", {}).get("admission_requests", 0)) for r in valid),
        "realization_rate": (
            sum(float(r["candidate"].get("telemetry", {}).get("realization_rate", 0.0)) for r in valid)
            / len(valid)
            if valid
            else None
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", nargs="+", type=int, default=[57210, 57211, 57212, 57213])
    parser.add_argument("--checkpoints", nargs="+", type=int, default=[72])
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--output", default="experiments/economic_program_counterfactual.json")
    parser.add_argument("--partial", default="experiments/economic_program_counterfactual.partial.json")
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
    print(f"Running {len(todo)} counterfactual conditions ({len(rows)} cached)", flush=True)
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
        "design": "CurrentBest uninterrupted continuation versus economic-program takeover from identical deterministic checkpoints",
        "baseline": BASELINE_PATH,
        "candidate": CANDIDATE_PATH,
        "seeds": [int(seed) for seed in args.seeds],
        "checkpoints": [int(checkpoint) for checkpoint in args.checkpoints],
        "rows": rows,
        "summary": _summary(rows),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(output)
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
