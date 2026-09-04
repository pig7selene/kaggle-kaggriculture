"""Cheap causal screen for a single wheat lifecycle commitment.

Each row runs the frozen CurrentBest opener through a real checkpoint, then
compares the passive safety executor with the lifecycle candidate from the
identical simulator state.  No state is edited and both seats are tested.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import json
from pathlib import Path
import statistics

from kaggle_environments import make

from run_checkpoint_executor_resume import BASELINE_PATH, _load, _validate, _animal_count, _terminal_value


ROOT = Path(__file__).resolve().parent
EXECUTOR_PATH = "agents/checkpoint_executor/commitment_executor_v1.py"
CANDIDATE_PATH = "agents/checkpoint_executor/crop_lifecycle_v1.py"


def _plant_count(obs, seat):
    farm = obs["farms"][seat]
    return sum(
        1
        for row in farm.get("tiles", [])
        for tile in row
        if isinstance(tile, dict) and tile.get("kind") == "PLANT"
    )


def _run_variant(path, seed, seat, checkpoint):
    opener = _load(BASELINE_PATH, f"life_open_{path}_{seed}_{seat}_{checkpoint}")
    agent = _load(path, f"life_agent_{path}_{seed}_{seat}_{checkpoint}")
    opponent = _load(BASELINE_PATH, f"life_opp_{path}_{seed}_{seat}_{checkpoint}")
    semantic = []
    action_counts = {"SELL": 0, "BUY_SEED": 0, "BUY_PRODUCT": 0, "HIRE": 0}

    def controlled(obs):
        step = int(obs.get("step", 0))
        action = opener(obs) if step < checkpoint else agent(obs)
        try:
            _validate(obs, action)
        except Exception as exc:
            semantic.append({"step": step, "error": repr(exc), "action": deepcopy(action)})
        if step >= checkpoint:
            for order in action.get("market", []):
                if order:
                    action_counts[order[0]] = action_counts.get(order[0], 0) + 1
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
        return {"runtime_error": runtime or f"steps={len(getattr(env, 'steps', []))}", "semantic_failures": semantic}

    final = env.steps[-1]
    own_state = final[int(seat)]
    counts = [_animal_count(step_state[int(seat)], int(seat)) for step_state in env.steps]
    terminal = _terminal_value(own_state, int(seat))
    telemetry = getattr(agent, "telemetry", {})
    return {
        "runtime_error": None,
        "semantic_failures": semantic,
        "own_money": float(own_state.reward),
        "opponent_money": float(final[1 - int(seat)].reward),
        "advantage": float(own_state.reward) - float(final[1 - int(seat)].reward),
        "animal_max": max(counts),
        "animal_final": counts[-1],
        "animal_loss": counts[-1] < max(counts),
        "terminal_value": terminal,
        "final_plants": _plant_count(own_state.observation, int(seat)),
        "telemetry": deepcopy(telemetry),
        "action_counts": action_counts,
    }


def _job(job):
    seed, seat, checkpoint, candidate_path = job
    control = _run_variant(EXECUTOR_PATH, seed, seat, checkpoint)
    candidate = _run_variant(candidate_path, seed, seat, checkpoint)
    out = {"seed": seed, "seat": seat, "checkpoint": checkpoint, "control": control, "candidate": candidate, "candidate_path": candidate_path}
    if not control.get("runtime_error") and not candidate.get("runtime_error"):
        out["own_money_delta"] = candidate["own_money"] - control["own_money"]
        out["advantage_delta"] = candidate["advantage"] - control["advantage"]
    return out


def _percentile(values, q):
    values = sorted(float(v) for v in values)
    if not values:
        return None
    pos = (len(values) - 1) * q
    low = int(pos)
    high = min(len(values) - 1, low + 1)
    return values[low] + (values[high] - values[low]) * (pos - low)


def _summary(rows):
    valid = [r for r in rows if "own_money_delta" in r]
    deltas = [r["own_money_delta"] for r in valid]
    realizations = []
    for row in valid:
        t = row["candidate"].get("telemetry", {})
        requested = int(t.get("admission_requests", 0))
        harvested = int(t.get("harvested", 0))
        if requested:
            realizations.append(harvested / requested)
    return {
        "conditions": len(rows),
        "valid": len(valid),
        "runtime_failures": sum(bool(r.get("control", {}).get("runtime_error") or r.get("candidate", {}).get("runtime_error")) for r in rows),
        "semantic_failures": sum(len(r.get("control", {}).get("semantic_failures", [])) + len(r.get("candidate", {}).get("semantic_failures", [])) for r in rows),
        "control_animal_loss_games": sum(bool(r.get("control", {}).get("animal_loss")) for r in valid),
        "candidate_animal_loss_games": sum(bool(r.get("candidate", {}).get("animal_loss")) for r in valid),
        "control_terminal_stranding_games": sum(float(r.get("control", {}).get("terminal_value", 0.0)) > 0 for r in valid),
        "candidate_terminal_stranding_games": sum(float(r.get("candidate", {}).get("terminal_value", 0.0)) > 0 for r in valid),
        "mean_control_money": statistics.fmean(r["control"]["own_money"] for r in valid) if valid else None,
        "mean_candidate_money": statistics.fmean(r["candidate"]["own_money"] for r in valid) if valid else None,
        "mean_own_money_delta": statistics.fmean(deltas) if deltas else None,
        "median_own_money_delta": statistics.median(deltas) if deltas else None,
        "p10_own_money_delta": _percentile(deltas, 0.10),
        "mean_advantage_delta": statistics.fmean(r["advantage_delta"] for r in valid) if valid else None,
        "admission_requests": sum(int(r.get("candidate", {}).get("telemetry", {}).get("admission_requests", 0)) for r in valid),
        "seed_requests": sum(int(r.get("candidate", {}).get("telemetry", {}).get("seed_requests", 0)) for r in valid),
        "seed_acquired": sum(int(r.get("candidate", {}).get("telemetry", {}).get("seed_acquired", 0)) for r in valid),
        "planted": sum(int(r.get("candidate", {}).get("telemetry", {}).get("planted", 0)) for r in valid),
        "harvested": sum(int(r.get("candidate", {}).get("telemetry", {}).get("harvested", 0)) for r in valid),
        "realization_rate": statistics.fmean(realizations) if realizations else 0.0,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", nargs="+", type=int, default=[55000, 55001])
    parser.add_argument("--checkpoints", nargs="+", type=int, default=[24, 72, 120, 168])
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--candidate", default=CANDIDATE_PATH)
    parser.add_argument("--output", default="experiments/checkpoint_executor_lifecycle_screen.json")
    args = parser.parse_args()
    jobs = [(seed, seat, checkpoint, args.candidate) for checkpoint in args.checkpoints for seed in args.seeds for seat in (0, 1)]
    rows = []
    with ProcessPoolExecutor(max_workers=max(1, int(args.workers))) as pool:
        futures = [pool.submit(_job, job) for job in jobs]
        for i, future in enumerate(as_completed(futures), 1):
            rows.append(future.result())
            print(f"{i}/{len(futures)} complete", flush=True)
    rows.sort(key=lambda r: (int(r["checkpoint"]), int(r["seed"]), int(r["seat"])))
    payload = {
        "schema_version": 1,
        "design": "CurrentBest opener, passive executor control versus one wheat lifecycle takeover; no state editing",
        "baseline": BASELINE_PATH,
        "control": EXECUTOR_PATH,
        "candidate": CANDIDATE_PATH,
        "seeds": [int(s) for s in args.seeds],
        "checkpoints": [int(c) for c in args.checkpoints],
        "rows": rows,
        "summary": _summary(rows),
    }
    output = (ROOT / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(output)
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
