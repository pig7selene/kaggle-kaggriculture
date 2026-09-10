"""Controlled local evaluation for the public Farming Score V3 notebook agent.

This script is deliberately research-only: it never packages or submits an agent.
It evaluates the exact reconstructed source and isolated route/guard ablations with
fresh imports, paired seeds, both seats, and resumable JSON shards.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path
import random
import statistics
import time

from kaggle_environments import make

from analyze_top3_forensics import crop_and_worker_forensics
from run_raw55899537_final_validation import (
    aggregate,
    animal_escapes,
    daily_bank,
    digest,
    economic_summary,
    farm_counts,
    load_agent,
    milestone_summary,
    percentile,
    semantic_validate,
    sign_test,
    terminal_value,
)


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "experiments/farming_v3_runs"
AGENTS = {
    "v3": ROOT / "agents/public_farming_v3/main.py",
    "v3_route0": ROOT / "agents/public_farming_v3/forced_route0.py",
    "v3_route1": ROOT / "agents/public_farming_v3/forced_route1.py",
    "v3_no_guard": ROOT / "agents/public_farming_v3/no_budget_guard.py",
    "v3_route0_no_guard": ROOT / "agents/public_farming_v3/forced_route0_no_guard.py",
    "v3_route1_no_guard": ROOT / "agents/public_farming_v3/forced_route1_no_guard.py",
    "candidate_v1": ROOT / "agents/farming_v3_distilled/v1_force_route1.py",
    "current_best": ROOT / "agents/top50_distilled/top50_observable_portfolio.py",
}
OPPONENTS = {
    "current_best": ROOT / "agents/top50_distilled/top50_observable_portfolio.py",
    "v2": ROOT / "agents/super_replay_v2/super_backbone_v2.py",
    "tetsuya": ROOT / "agents/top3_tuned/raw_rank1_tetsuya.py",
    "crop_dusta": ROOT / "agents/top3_tuned/raw_rank2_crop_dusta.py",
    "k3": ROOT / "agents/v27_k3_weed.py",
    "nazmus": ROOT / "agents/super_replay_v4/n1_nazmus_weed.py",
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bootstrap_mean_ci(values, resamples=10000, seed=912559):
    """Deterministic bootstrap using an independent PRNG for every draw."""
    values = [float(value) for value in values]
    if not values:
        return {"mean": None, "low": None, "high": None, "resamples": 0}
    rng = random.Random(seed)
    n = len(values)
    means = [statistics.fmean(values[rng.randrange(n)] for _ in range(n)) for _ in range(resamples)]
    return {
        "mean": statistics.fmean(values),
        "low": percentile(means, .025),
        "high": percentile(means, .975),
        "resamples": int(resamples),
    }


def _v3_globals(agent):
    values = getattr(agent, "__globals__", {})
    return values if "_ROUTES" in values and "_STATE" in values else None


def _compact_economics(econ, keep_daily=False):
    result = dict(econ)
    if not keep_daily:
        result.pop("daily", None)
    return result


def run_case(job):
    stage, variant, opponent_name, seed, seat, keep_detail = job
    started = time.perf_counter()
    agent = load_agent(AGENTS[variant])
    opponent_path = OPPONENTS[opponent_name]
    opponent = load_agent(opponent_path)
    actions = []
    semantic_failures = []
    exceptions = []
    guard_events = []
    decision = None
    v3g = _v3_globals(agent)

    def checked(obs):
        nonlocal decision
        step = int(obs.get("step", 0))
        try:
            action = agent(obs)
        except Exception as exc:
            exceptions.append({"step": step, "error": repr(exc)})
            raise
        actions.append(deepcopy(action))
        try:
            semantic_validate(obs, action)
        except Exception as exc:
            semantic_failures.append({"step": step, "error": repr(exc)})
        if v3g is not None and 0 <= step < int(v3g["_TURNS"]):
            route = int(v3g["_STATE"][seat].get("route", 0))
            base = v3g["_copy_action"](v3g["_ROUTES"][route][step])
            if action != base:
                before = Counter(tuple(x) for x in base.get("market", []))
                after = Counter(tuple(x) for x in action.get("market", []))
                guard_events.append({
                    "step": step,
                    "route": route,
                    "money": float(obs["farms"][seat]["money"]),
                    "added_market_orders": [list(x) for x in (after - before).elements()],
                    "removed_market_orders": [list(x) for x in (before - after).elements()],
                })
            if step == int(v3g["_DECISION_STEP"]):
                town = list(obs.get("town", {}).get("unlocked_shops", []))
                rival = obs["farms"][1 - seat]
                decision = {
                    "route": route,
                    "first_shop": town[0] if town else None,
                    "shops": town,
                    "fertilizer_inventory": int(obs["market"]["inventory"].get("FERTILIZER", 0)),
                    "rival_plant_tiles": int(v3g["_plant_tiles"](rival)),
                    "money": float(obs["farms"][seat]["money"]),
                }
        return action

    pair = [opponent, opponent]
    pair[seat] = checked
    configuration = {"episodeSteps": 720, "seed": int(seed)}
    if stage == "guard_stress":
        configuration["startingMoney"] = 2000
    env = make("kaggriculture", configuration=configuration, debug=False)
    runtime_error = None
    try:
        env.run(pair)
    except Exception as exc:
        runtime_error = repr(exc)
    elapsed = time.perf_counter() - started
    if len(getattr(env, "steps", [])) != 720:
        return {
            "stage": stage, "variant": variant, "opponent": opponent_name,
            "seed": seed, "seat": seat, "runtime_error": runtime_error or f"steps={len(env.steps)}",
            "semantic_failures": semantic_failures, "exceptions": exceptions,
        }
    states = env.steps
    final = states[-1]
    replay = env.toJSON()
    own = float(final[seat].reward)
    other = float(final[1 - seat].reward)
    row = {
        "stage": stage, "variant": variant, "opponent": opponent_name,
        "seed": int(seed), "seat": int(seat), "runtime_error": runtime_error,
        "semantic_failures": semantic_failures, "exceptions": exceptions,
        "elapsed_s": elapsed, "own_money": own, "opponent_money": other,
        "advantage": own - other, "action_hash": digest(actions),
        "opening_action_hash_through_359": digest(actions[:360]),
        "decision": decision, "budget_guard_events": guard_events,
        "livestock_escapes": animal_escapes(states, seat),
        "terminal": terminal_value(final, seat),
        "milestones": milestone_summary(states, seat),
        "economics": _compact_economics(economic_summary(replay, seat), keep_detail),
    }
    if keep_detail:
        row["daily_bank"] = daily_bank(states, seat)
        row["forensics"] = crop_and_worker_forensics(replay, seat, actions)
        row["daily_farm"] = [
            {
                "day": day,
                "money": float(states[min(day * 24, 719)][seat].observation["farms"][seat]["money"]),
                "hands": len(states[min(day * 24, 719)][seat].observation["farms"][seat].get("hands", [])),
                "quadrants": len(states[min(day * 24, 719)][seat].observation["farms"][seat].get("unlocked_quadrants", [])),
                **farm_counts(states[min(day * 24, 719)][seat].observation["farms"][seat]),
            }
            for day in range(30)
        ]
    return row


def jobs_for(stage):
    raw_panel = {
        "current_best": range(881000, 881008),
        "v2": range(881100, 881104),
        "tetsuya": range(881200, 881204),
        "crop_dusta": range(881300, 881304),
        "k3": range(881400, 881404),
        "nazmus": range(881500, 881504),
    }
    if stage == "raw":
        jobs = []
        for opponent, seeds in raw_panel.items():
            for seed in seeds:
                for seat in (0, 1):
                    for variant in ("v3", "current_best"):
                        jobs.append((stage, variant, opponent, seed, seat, False))
        return jobs
    if stage == "candidate":
        return [
            (stage, "v3_route1", opponent, seed, seat, False)
            for opponent, seeds in raw_panel.items()
            for seed in seeds
            for seat in (0, 1)
        ]
    if stage == "guard_stress":
        return [
            (stage, variant, "current_best", seed, seat, False)
            for seed in range(884000, 884004)
            for seat in (0, 1)
            for variant in ("v3", "v3_no_guard")
        ]
    if stage == "counterfactual":
        jobs = []
        panel = {
            "current_best": range(882000, 882008),
            "v2": range(882100, 882104),
            "tetsuya": range(882200, 882204),
        }
        for opponent, seeds in panel.items():
            for seed in seeds:
                for seat in (0, 1):
                    for variant in ("v3_route0", "v3_route1", "v3", "v3_no_guard"):
                        jobs.append((stage, variant, opponent, seed, seat, False))
        return jobs
    if stage == "dossier":
        jobs = []
        for opponent, seed in (("current_best", 883000), ("v2", 883100)):
            for seat in (0, 1):
                for variant in ("v3_route0", "v3_route1"):
                    jobs.append((stage, variant, opponent, seed, seat, True))
        return jobs
    raise ValueError(stage)


def _key(job):
    return "|".join(map(str, job[:5]))


def execute(stage, workers):
    OUT.mkdir(parents=True, exist_ok=True)
    partial = OUT / f"{stage}.partial.json"
    rows = json.loads(partial.read_text()) if partial.exists() else []
    done = {"|".join(map(str, (r["stage"], r["variant"], r["opponent"], r["seed"], r["seat"]))) for r in rows}
    pending = [job for job in jobs_for(stage) if _key(job) not in done]
    print(f"{stage}: {len(rows)} cached, {len(pending)} pending", flush=True)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(run_case, job): job for job in pending}
        for index, future in enumerate(as_completed(futures), 1):
            rows.append(future.result())
            if index % 8 == 0 or index == len(pending):
                partial.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n")
                print(f"{stage}: {index}/{len(pending)} new games", flush=True)
    rows.sort(key=lambda r: (r["opponent"], r["seed"], r["seat"], r["variant"]))
    partial.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n")
    return rows


def paired(rows, left, right):
    by = defaultdict(dict)
    for row in rows:
        by[(row["opponent"], row["seed"], row["seat"])][row["variant"]] = row
    output = []
    for (opponent, seed, seat), group in sorted(by.items()):
        if left not in group or right not in group:
            continue
        a, b = group[left], group[right]
        output.append({
            "opponent": opponent, "seed": seed, "seat": seat,
            "left": left, "right": right,
            "left_money": a["own_money"], "right_money": b["own_money"],
            "own_money_delta": a["own_money"] - b["own_money"],
            "left_advantage": a["advantage"], "right_advantage": b["advantage"],
            "advantage_delta": a["advantage"] - b["advantage"],
            "opponent_money_delta": a["opponent_money"] - b["opponent_money"],
            "opening_hash_equal": a["opening_action_hash_through_359"] == b["opening_action_hash_through_359"],
            "left_route": (a.get("decision") or {}).get("route"),
            "right_route": (b.get("decision") or {}).get("route"),
            "left_guard_events": len(a.get("budget_guard_events", [])),
            "right_guard_events": len(b.get("budget_guard_events", [])),
            "left_escapes": len(a.get("livestock_escapes", [])),
            "right_escapes": len(b.get("livestock_escapes", [])),
        })
    return output


def summarize(pair_rows):
    def one(selected):
        own = [r["own_money_delta"] for r in selected]
        adv = [r["advantage_delta"] for r in selected]
        return {
            "games": len(selected),
            "own_money_delta": {
                "mean": statistics.fmean(own) if own else None,
                "median": statistics.median(own) if own else None,
                "p10": percentile(own, .10), "worst": min(own) if own else None,
                "negative_rate": sum(x < 0 for x in own) / len(own) if own else None,
                "bootstrap_95": bootstrap_mean_ci(own, 10000), "sign_test": sign_test(own),
            },
            "advantage_delta": {
                "mean": statistics.fmean(adv) if adv else None,
                "median": statistics.median(adv) if adv else None,
                "p10": percentile(adv, .10), "worst": min(adv) if adv else None,
                "negative_rate": sum(x < 0 for x in adv) / len(adv) if adv else None,
                "bootstrap_95": bootstrap_mean_ci(adv, 10000), "sign_test": sign_test(adv),
            },
            "opening_hash_all_equal": all(r["opening_hash_equal"] for r in selected),
            "left_escapes": sum(r["left_escapes"] for r in selected),
            "right_escapes": sum(r["right_escapes"] for r in selected),
        }
    return {
        "overall": one(pair_rows),
        "by_opponent": {name: one([r for r in pair_rows if r["opponent"] == name]) for name in sorted({r["opponent"] for r in pair_rows})},
        "by_seat": {str(seat): one([r for r in pair_rows if r["seat"] == seat]) for seat in (0, 1)},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("raw", "counterfactual", "dossier", "candidate", "guard_stress", "all"))
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    stages = ("raw", "counterfactual", "dossier", "candidate", "guard_stress") if args.stage == "all" else (args.stage,)
    all_rows = {}
    for stage in stages:
        all_rows[stage] = execute(stage, args.workers)
    if "raw" in all_rows:
        pairs = paired(all_rows["raw"], "v3", "current_best")
        (OUT / "raw_summary.json").write_text(json.dumps({"summary": summarize(pairs), "pairs": pairs}, indent=2, sort_keys=True) + "\n")
    if "counterfactual" in all_rows:
        route_pairs = paired(all_rows["counterfactual"], "v3_route1", "v3_route0")
        guard_pairs = paired(all_rows["counterfactual"], "v3", "v3_no_guard")
        result = {
            "route1_minus_route0": {"summary": summarize(route_pairs), "pairs": route_pairs},
            "guard_minus_no_guard": {"summary": summarize(guard_pairs), "pairs": guard_pairs},
        }
        (OUT / "counterfactual_summary.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    if "candidate" in all_rows:
        baseline = json.loads((OUT / "raw.partial.json").read_text())
        candidate_pairs = paired(baseline + all_rows["candidate"], "v3_route1", "current_best")
        (OUT / "candidate_summary.json").write_text(json.dumps({"summary": summarize(candidate_pairs), "pairs": candidate_pairs}, indent=2, sort_keys=True) + "\n")
    if "guard_stress" in all_rows:
        stress_pairs = paired(all_rows["guard_stress"], "v3", "v3_no_guard")
        (OUT / "guard_stress_summary.json").write_text(json.dumps({"summary": summarize(stress_pairs), "pairs": stress_pairs}, indent=2, sort_keys=True) + "\n")
    print("done", flush=True)


if __name__ == "__main__":
    main()
