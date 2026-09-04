"""Action/transition audit for commitment ownership after checkpoint takeover."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import json
from pathlib import Path

from kaggle_environments import make

from run_checkpoint_executor_resume import (
    BASELINE_PATH,
    EXECUTOR_PATH,
    _load,
    _terminal_value,
    _validate,
)


ROOT = Path(__file__).resolve().parent


def _plants(obs, seat):
    farm = obs["farms"][seat]
    return {(x, y): tile for y, row in enumerate(farm.get("tiles", []))
            for x, tile in enumerate(row)
            if isinstance(tile, dict) and tile.get("kind") == "PLANT"}


def _animals(obs, seat):
    farm = obs["farms"][seat]
    return {(x, y): tile for y, row in enumerate(farm.get("tiles", []))
            for x, tile in enumerate(row)
            if isinstance(tile, dict) and tile.get("animal")}


def _run(job):
    seed, seat, checkpoint = job
    base = _load(BASELINE_PATH, f"audit_base_{seed}_{seat}_{checkpoint}")
    opponent = _load(BASELINE_PATH, f"audit_opp_{seed}_{seat}_{checkpoint}")
    executor = _load(EXECUTOR_PATH, f"audit_exec_{seed}_{seat}_{checkpoint}")
    semantic = []

    def controlled(obs):
        action = base(obs) if int(obs.get("step", 0)) < checkpoint else executor(obs)
        try:
            _validate(obs, action)
        except Exception as exc:
            semantic.append({"step": int(obs.get("step", -1)), "error": repr(exc)})
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
        return {"seed": seed, "seat": seat, "checkpoint": checkpoint,
                "runtime_error": runtime or f"steps={len(getattr(env, 'steps', []))}",
                "semantic_failures": semantic}

    takeover = env.steps[checkpoint][seat].observation
    initial_plants = _plants(takeover, seat)
    initial_animals = _animals(takeover, seat)
    first_days = {pos: int(tile.get("planted_day", takeover.get("day", 0))) +
                  int({"WHEAT": 2, "CARROT": 2, "TOMATO": 8, "STRAWBERRY": 10, "MELON": 10}.get(tile.get("crop"), 999))
                  for pos, tile in initial_plants.items()}
    animal_loss_events = []
    crop_loss_events = []
    max_unfed = 0
    max_unwatered = 0
    for idx in range(checkpoint, 720):
        obs = env.steps[idx][seat].observation
        animals = _animals(obs, seat)
        plants = _plants(obs, seat)
        for pos, animal in initial_animals.items():
            if pos not in animals:
                animal_loss_events.append({"step": idx, "position": pos, "animal": animal.get("animal")})
        for pos, ready_day in first_days.items():
            if int(obs.get("day", 0)) < ready_day and pos not in plants:
                tile = obs["farms"][seat]["tiles"][pos[1]][pos[0]]
                if tile != "LOCKED":
                    crop_loss_events.append({"step": idx, "position": pos, "tile": deepcopy(tile)})
        for tile in animals.values():
            max_unfed = max(max_unfed, int(tile.get("consecutive_unfed", 0)))
        for tile in plants.values():
            max_unwatered = max(max_unwatered, int(tile.get("consecutive_unwatered", 0)))
    final = env.steps[-1][seat]
    telemetry = deepcopy(getattr(executor, "telemetry", {}))
    return {
        "seed": int(seed), "seat": int(seat), "checkpoint": int(checkpoint),
        "runtime_error": None, "semantic_failures": semantic,
        "initial_plants": len(initial_plants), "initial_animals": len(initial_animals),
        "animal_loss_events": animal_loss_events,
        "crop_loss_events": crop_loss_events,
        "max_consecutive_unfed": max_unfed,
        "max_consecutive_unwatered": max_unwatered,
        "terminal_value": _terminal_value(final, seat),
        "final_money": float(final.reward),
        "telemetry": telemetry,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", nargs="+", type=int, default=[53000])
    parser.add_argument("--checkpoints", nargs="+", type=int, default=[24, 72, 120, 240, 480, 600])
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--output", default="experiments/checkpoint_executor_commitment_audit.json")
    args = parser.parse_args()
    jobs = [(seed, seat, checkpoint) for checkpoint in args.checkpoints
            for seed in args.seeds for seat in (0, 1)]
    rows = []
    with ProcessPoolExecutor(max_workers=max(1, int(args.workers))) as pool:
        futures = [pool.submit(_run, job) for job in jobs]
        for i, future in enumerate(as_completed(futures), 1):
            rows.append(future.result())
            if i % 8 == 0 or i == len(futures):
                print(f"{i}/{len(futures)} complete", flush=True)
    rows.sort(key=lambda r: (int(r.get("checkpoint", -1)), int(r.get("seed", -1)), int(r.get("seat", -1))))
    valid = [r for r in rows if not r.get("runtime_error")]
    payload = {
        "schema_version": 1,
        "design": "transition audit of visible commitments from real checkpoint takeover",
        "seeds": [int(s) for s in args.seeds], "checkpoints": [int(c) for c in args.checkpoints],
        "baseline": BASELINE_PATH, "executor": EXECUTOR_PATH, "rows": rows,
        "summary": {
            "conditions": len(valid),
            "runtime_failures": sum(bool(r.get("runtime_error")) for r in rows),
            "semantic_failures": sum(len(r.get("semantic_failures", [])) for r in rows),
            "animal_loss_conditions": sum(bool(r.get("animal_loss_events")) for r in valid),
            "crop_commitment_loss_conditions": sum(bool(r.get("crop_loss_events")) for r in valid),
            "max_unfed": max((r.get("max_consecutive_unfed", 0) for r in valid), default=None),
            "max_unwatered": max((r.get("max_consecutive_unwatered", 0) for r in valid), default=None),
            "terminal_stranding_conditions": sum(float(r.get("terminal_value", 0)) > 0 for r in valid),
        },
    }
    output = (ROOT / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(output)
    print(payload["summary"])


if __name__ == "__main__":
    main()
