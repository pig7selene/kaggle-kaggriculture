"""Resume, perturbation, and commitment safety checks for the wheat candidate."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import json
from pathlib import Path
import statistics

from kaggle_environments import make

from run_checkpoint_executor_resume import BASELINE_PATH, _animal_count, _load, _terminal_value, _validate


ROOT = Path(__file__).resolve().parent
CANDIDATE_PATH = "agents/checkpoint_executor/crop_lifecycle_v1.py"
PERTURBATIONS = ("farmer_pass", "skip_water", "omit_sell", "omit_buy_product")


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
    if kind in {"omit_sell", "omit_buy_product"}:
        wanted = "SELL" if kind == "omit_sell" else "BUY_PRODUCT"
        for i, order in enumerate(out.get("market", [])):
            if order and order[0] == wanted:
                del out["market"][i]
                return out, True
        return out, False
    raise ValueError(kind)


def _plants(obs, seat):
    farm = obs["farms"][seat]
    return {(x, y): tile for y, row in enumerate(farm.get("tiles", [])) for x, tile in enumerate(row)
            if isinstance(tile, dict) and tile.get("kind") == "PLANT"}


def _animals(obs, seat):
    farm = obs["farms"][seat]
    return {(x, y): tile for y, row in enumerate(farm.get("tiles", [])) for x, tile in enumerate(row)
            if isinstance(tile, dict) and tile.get("animal")}


def _run(job):
    seed, seat, checkpoint, perturbation, candidate_path = job
    opener = _load(BASELINE_PATH, f"life_safe_open_{seed}_{seat}_{checkpoint}_{perturbation}")
    candidate = _load(candidate_path, f"life_safe_candidate_{seed}_{seat}_{checkpoint}_{perturbation}")
    opponent = _load(BASELINE_PATH, f"life_safe_opp_{seed}_{seat}_{checkpoint}_{perturbation}")
    semantic = []
    changed = False
    perturb_start = max(0, checkpoint - 24)

    def controlled(obs):
        nonlocal changed
        step = int(obs.get("step", 0))
        if step < checkpoint:
            action = opener(obs)
            if not changed and perturb_start <= step < checkpoint:
                action, changed = _perturb(action, perturbation)
        else:
            action = candidate(obs)
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
        return {"seed": seed, "seat": seat, "checkpoint": checkpoint, "perturbation": perturbation,
                "changed": changed, "runtime_error": runtime or f"steps={len(getattr(env, 'steps', []))}",
                "semantic_failures": semantic}

    takeover = env.steps[checkpoint][seat].observation
    initial_animals = _animals(takeover, seat)
    initial_plants = _plants(takeover, seat)
    animal_loss_events = []
    crop_loss_events = []
    max_unfed = 0
    max_unwatered = 0
    for index in range(checkpoint, 720):
        obs = env.steps[index][seat].observation
        animals = _animals(obs, seat)
        plants = _plants(obs, seat)
        for pos, tile in initial_animals.items():
            if pos not in animals:
                animal_loss_events.append({"step": index, "position": pos, "animal": tile.get("animal")})
        for pos, tile in initial_plants.items():
            if pos not in plants and int(obs.get("day", 0)) - int(tile.get("planted_day", obs.get("day", 0))) < {"WHEAT": 2, "CARROT": 2, "TOMATO": 8, "STRAWBERRY": 10, "MELON": 10}.get(tile.get("crop"), 999):
                current = obs["farms"][seat]["tiles"][pos[1]][pos[0]]
                if current != "LOCKED":
                    crop_loss_events.append({"step": index, "position": pos, "tile": deepcopy(current)})
        for tile in animals.values():
            max_unfed = max(max_unfed, int(tile.get("consecutive_unfed", 0)))
        for tile in plants.values():
            max_unwatered = max(max_unwatered, int(tile.get("consecutive_unwatered", 0)))
    final = env.steps[-1][seat]
    counts = [_animal_count(step_states[seat], seat) for step_states in env.steps]
    return {
        "seed": seed, "seat": seat, "checkpoint": checkpoint, "perturbation": perturbation,
        "changed": changed, "runtime_error": None, "semantic_failures": semantic,
        "animal_loss": bool(animal_loss_events), "animal_loss_events": animal_loss_events,
        "crop_loss": bool(crop_loss_events), "crop_loss_events": crop_loss_events,
        "max_animal_count": max(counts), "final_animal_count": counts[-1],
        "max_unfed": max_unfed, "max_unwatered": max_unwatered,
        "terminal_value": _terminal_value(final, seat), "final_money": float(final.reward),
        "telemetry": deepcopy(getattr(candidate, "telemetry", {})),
    }


def _summary(rows):
    valid = [r for r in rows if not r.get("runtime_error")]
    return {
        "conditions": len(valid),
        "changed_conditions": sum(bool(r.get("changed")) for r in valid),
        "runtime_failures": sum(bool(r.get("runtime_error")) for r in rows),
        "semantic_failures": sum(len(r.get("semantic_failures", [])) for r in rows),
        "animal_loss_conditions": sum(bool(r.get("animal_loss")) for r in valid),
        "crop_loss_conditions": sum(bool(r.get("crop_loss")) for r in valid),
        "terminal_stranding_conditions": sum(float(r.get("terminal_value", 0.0)) > 0 for r in valid),
        "max_consecutive_unfed": max((r.get("max_unfed", 0) for r in valid), default=None),
        "max_consecutive_unwatered": max((r.get("max_unwatered", 0) for r in valid), default=None),
        "mean_final_money": statistics.fmean(r["final_money"] for r in valid) if valid else None,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", nargs="+", type=int, default=[55002])
    parser.add_argument("--checkpoints", nargs="+", type=int, default=[24, 72])
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--candidate", default=CANDIDATE_PATH)
    parser.add_argument("--output", default="experiments/checkpoint_executor_lifecycle_safety.json")
    args = parser.parse_args()
    jobs = [(seed, seat, checkpoint, perturbation, args.candidate)
            for checkpoint in args.checkpoints for seed in args.seeds for seat in (0, 1)
            for perturbation in PERTURBATIONS]
    rows = []
    with ProcessPoolExecutor(max_workers=max(1, int(args.workers))) as pool:
        futures = [pool.submit(_run, job) for job in jobs]
        for i, future in enumerate(as_completed(futures), 1):
            rows.append(future.result())
            if i % 8 == 0 or i == len(futures):
                print(f"{i}/{len(futures)} complete", flush=True)
    rows.sort(key=lambda r: (int(r["checkpoint"]), int(r["seed"]), int(r["seat"]), r["perturbation"]))
    payload = {"schema_version": 1,
               "design": "wheat lifecycle candidate safety gates with valid action perturbations",
               "candidate": CANDIDATE_PATH, "baseline": BASELINE_PATH,
               "seeds": [int(s) for s in args.seeds], "checkpoints": [int(c) for c in args.checkpoints],
               "perturbations": list(PERTURBATIONS), "rows": rows, "summary": _summary(rows)}
    output = (ROOT / args.output).resolve(); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(output); print(json.dumps(payload["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
