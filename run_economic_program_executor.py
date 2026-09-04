"""Capability screen for the unified economic-program executor.

The opener always runs in the real simulator until a checkpoint.  The
candidate then takes over and owns one compact MELON program together with all
observed crop/livestock commitments.  A passive commitment executor from the
same checkpoint is the control.  No simulator state is edited.

The harness records requested versus realized lifecycle events, deadline
pressure, safety failures, and paired own-money deltas.  It is intentionally a
small capability gate, not a strategy benchmark.
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
    _animal_count,
    _load,
    _terminal_value,
    _validate,
)


ROOT = Path(__file__).resolve().parent
CONTROL_PATH = "agents/checkpoint_executor/commitment_executor_v1.py"
CANDIDATE_PATH = "agents/economic_program/economic_program_executor_v1.py"
FIRST_YIELD = {"WHEAT": 2, "CARROT": 2, "TOMATO": 8, "STRAWBERRY": 10, "MELON": 10}


def _plants(obs, seat):
    farm = obs["farms"][seat]
    return {
        (x, y): tile
        for y, row in enumerate(farm.get("tiles", []))
        for x, tile in enumerate(row)
        if isinstance(tile, dict) and tile.get("kind") == "PLANT"
    }


def _animals(obs, seat):
    farm = obs["farms"][seat]
    return {
        (x, y): tile
        for y, row in enumerate(farm.get("tiles", []))
        for x, tile in enumerate(row)
        if isinstance(tile, dict) and tile.get("animal")
    }


def _productive(obs, seat):
    farm = obs["farms"][seat]
    return sum(
        1
        for row in farm.get("tiles", [])
        for tile in row
        if isinstance(tile, dict)
        and (tile.get("kind") == "PLANT" or tile.get("animal"))
    )


def _run_variant(path, seed, seat, checkpoint):
    opener = _load(BASELINE_PATH, f"program_open_{path}_{seed}_{seat}_{checkpoint}")
    variant = _load(path, f"program_variant_{path}_{seed}_{seat}_{checkpoint}")
    opponent = _load(BASELINE_PATH, f"program_opp_{path}_{seed}_{seat}_{checkpoint}")
    semantic = []
    action_history = []

    def controlled(obs):
        step = int(obs.get("step", 0))
        action = opener(obs) if step < checkpoint else variant(obs)
        try:
            _validate(obs, action)
        except Exception as exc:
            semantic.append({"step": step, "error": repr(exc), "action": deepcopy(action)})
        if step >= checkpoint:
            action_history.append((step, deepcopy(action)))
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
            "runtime_error": runtime or f"steps={len(getattr(env, 'steps', []))}",
            "semantic_failures": semantic,
        }

    takeover = env.steps[checkpoint][seat].observation
    initial_animals = _animals(takeover, seat)
    initial_plants = _plants(takeover, seat)
    animal_loss_events = []
    crop_loss_events = []
    max_unfed = 0
    max_unwatered = 0
    productive_series = []
    for index in range(checkpoint, 720):
        obs = env.steps[index][seat].observation
        animals = _animals(obs, seat)
        plants = _plants(obs, seat)
        productive_series.append(_productive(obs, seat))
        for pos, tile in initial_animals.items():
            if pos not in animals:
                animal_loss_events.append({"step": index, "position": pos, "animal": tile.get("animal")})
        for pos, tile in initial_plants.items():
            if pos not in plants:
                crop = tile.get("crop")
                age = int(obs.get("day", 0)) - int(tile.get("planted_day", obs.get("day", 0)))
                if age < FIRST_YIELD.get(crop, 999) and obs["farms"][seat]["tiles"][pos[1]][pos[0]] != "LOCKED":
                    crop_loss_events.append({"step": index, "position": pos, "crop": crop})
        for tile in animals.values():
            max_unfed = max(max_unfed, int(tile.get("consecutive_unfed", 0)))
        for tile in plants.values():
            max_unwatered = max(max_unwatered, int(tile.get("consecutive_unwatered", 0)))

    final = env.steps[-1][seat]
    counts = [_animal_count(step_states[seat], seat) for step_states in env.steps]
    telemetry = deepcopy(getattr(variant, "telemetry", {}))
    return {
        "seed": int(seed), "seat": int(seat), "checkpoint": int(checkpoint),
        "runtime_error": None, "semantic_failures": semantic,
        "own_money": float(final.reward),
        "opponent_money": float(env.steps[-1][1 - int(seat)].reward),
        "advantage": float(final.reward) - float(env.steps[-1][1 - int(seat)].reward),
        "animal_loss": bool(animal_loss_events), "animal_loss_events": animal_loss_events,
        "crop_loss": bool(crop_loss_events), "crop_loss_events": crop_loss_events,
        "max_animal_count": max(counts), "final_animal_count": counts[-1],
        "max_unfed": max_unfed, "max_unwatered": max_unwatered,
        "terminal_value": _terminal_value(final, seat),
        "final_productive_tiles": productive_series[-1],
        "mean_productive_tiles": statistics.fmean(productive_series) if productive_series else 0.0,
        "action_calls": len(action_history),
        "telemetry": telemetry,
    }


def _job(job):
    seed, seat, checkpoint = job
    control = _run_variant(CONTROL_PATH, seed, seat, checkpoint)
    candidate = _run_variant(CANDIDATE_PATH, seed, seat, checkpoint)
    row = {
        "seed": int(seed), "seat": int(seat), "checkpoint": int(checkpoint),
        "control": control, "candidate": candidate,
    }
    if not control.get("runtime_error") and not candidate.get("runtime_error"):
        row["own_money_delta"] = candidate["own_money"] - control["own_money"]
        row["advantage_delta"] = candidate["advantage"] - control["advantage"]
    return row


def _percentile(values, q):
    values = sorted(float(value) for value in values)
    if not values:
        return None
    position = (len(values) - 1) * q
    low = int(position)
    high = min(len(values) - 1, low + 1)
    return values[low] + (values[high] - values[low]) * (position - low)


def _summary(rows):
    valid = [row for row in rows if "own_money_delta" in row]
    deltas = [float(row["own_money_delta"]) for row in valid]
    candidate = [row["candidate"] for row in valid]
    return {
        "conditions": len(rows), "valid": len(valid),
        "runtime_failures": sum(bool(row.get("candidate", {}).get("runtime_error") or row.get("control", {}).get("runtime_error")) for row in rows),
        "semantic_failures": sum(len(row.get("candidate", {}).get("semantic_failures", [])) + len(row.get("control", {}).get("semantic_failures", [])) for row in rows),
        "candidate_animal_loss_conditions": sum(bool(result.get("animal_loss")) for result in candidate),
        "candidate_crop_loss_conditions": sum(bool(result.get("crop_loss")) for result in candidate),
        "candidate_terminal_stranding_conditions": sum(float(result.get("terminal_value", 0.0)) > 0 for result in candidate),
        "max_consecutive_unfed": max((int(result.get("max_unfed", 0)) for result in candidate), default=None),
        "max_consecutive_unwatered": max((int(result.get("max_unwatered", 0)) for result in candidate), default=None),
        "mean_control_money": statistics.fmean(row["control"]["own_money"] for row in valid) if valid else None,
        "mean_candidate_money": statistics.fmean(row["candidate"]["own_money"] for row in valid) if valid else None,
        "mean_own_money_delta": statistics.fmean(deltas) if deltas else None,
        "median_own_money_delta": statistics.median(deltas) if deltas else None,
        "p10_own_money_delta": _percentile(deltas, 0.10),
        "p5_own_money_delta": _percentile(deltas, 0.05),
        "mean_advantage_delta": statistics.fmean(float(row["advantage_delta"]) for row in valid) if valid else None,
        "mean_productive_tiles": statistics.fmean(result.get("mean_productive_tiles", 0.0) for result in candidate) if candidate else None,
        "admissions": sum(int(result.get("telemetry", {}).get("admission_requests", 0)) for result in candidate),
        "seed_requests": sum(int(result.get("telemetry", {}).get("seed_requests", 0)) for result in candidate),
        "seed_acquired": sum(int(result.get("telemetry", {}).get("seed_acquired", 0)) for result in candidate),
        "planted": sum(int(result.get("telemetry", {}).get("planted", 0)) for result in candidate),
        "matured": sum(int(result.get("telemetry", {}).get("matured", 0)) for result in candidate),
        "harvested": sum(int(result.get("telemetry", {}).get("harvested", 0)) for result in candidate),
        "harvest_units": sum(int(result.get("telemetry", {}).get("harvest_units", 0)) for result in candidate),
        "realization_rate": (
            statistics.fmean(
                float(result.get("telemetry", {}).get("realization_rate", 0.0))
                for result in candidate
                if int(result.get("telemetry", {}).get("requested", 0)) > 0
            )
            if any(int(result.get("telemetry", {}).get("requested", 0)) > 0 for result in candidate)
            else 0.0
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", nargs="+", type=int, default=[57200, 57201, 57202, 57203])
    parser.add_argument("--checkpoints", nargs="+", type=int, default=[240, 264, 288, 312])
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--output", default="experiments/economic_program_executor_screen.json")
    parser.add_argument("--partial", default="experiments/economic_program_executor_screen.partial.json")
    args = parser.parse_args()
    jobs = [(seed, seat, checkpoint) for checkpoint in args.checkpoints for seed in args.seeds for seat in (0, 1)]
    partial = (ROOT / args.partial).resolve()
    output = (ROOT / args.output).resolve()
    rows = []
    if partial.is_file():
        try:
            rows = json.loads(partial.read_text()).get("rows", [])
        except Exception:
            rows = []
    done = {(int(row.get("seed", -1)), int(row.get("seat", -1)), int(row.get("checkpoint", -1))) for row in rows}
    todo = [job for job in jobs if job not in done]
    print(f"Running {len(todo)} capability conditions ({len(rows)} cached)", flush=True)
    with ProcessPoolExecutor(max_workers=max(1, int(args.workers))) as pool:
        futures = [pool.submit(_job, job) for job in todo]
        for index, future in enumerate(as_completed(futures), 1):
            rows.append(future.result())
            if index % 4 == 0 or index == len(futures):
                partial.parent.mkdir(parents=True, exist_ok=True)
                partial.write_text(json.dumps({"schema_version": 1, "rows": rows}, indent=2, sort_keys=True) + "\n")
                print(f"{index}/{len(futures)} complete", flush=True)
    rows.sort(key=lambda row: (int(row.get("checkpoint", -1)), int(row.get("seed", -1)), int(row.get("seat", -1))))
    payload = {
        "schema_version": 1,
        "design": "unified full-owner melon program from real CurrentBest checkpoints; passive commitment executor control; no state editing",
        "baseline": BASELINE_PATH, "control": CONTROL_PATH, "candidate": CANDIDATE_PATH,
        "seeds": [int(seed) for seed in args.seeds], "checkpoints": [int(cp) for cp in args.checkpoints],
        "rows": rows, "summary": _summary(rows),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(output)
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
