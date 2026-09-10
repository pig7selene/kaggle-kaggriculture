"""Read-only local evaluation harness for the public Farming Score V5 package.

This runner never touches deployment files and never calls remote submission APIs.
It compares the exact current V5 package, public V5 version 1, V3, and CurrentBest
on paired seeds and seats, while preserving enough telemetry for timing forensics.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import statistics
import sys
import time
from typing import Any

from kaggle_environments import make

from analyze_top3_forensics import crop_and_worker_forensics
from run_raw55899537_final_validation import (
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
OUT = ROOT / "experiments/farming_v5_runs"
V5_ROOTS = {
    "v5": ROOT / "agents/public_farming_v5",
    "v5_v1": ROOT / "agents/public_farming_v5_v1",
}
AGENTS = {
    "current_best": ROOT / "agents/top50_distilled/top50_observable_portfolio.py",
    "v3": ROOT / "agents/public_farming_v3/main.py",
}
OPPONENTS = {
    "current_best": ROOT / "agents/top50_distilled/top50_observable_portfolio.py",
    "v3": ROOT / "agents/public_farming_v3/main.py",
    "crop_dusta": ROOT / "agents/top3_tuned/raw_rank2_crop_dusta.py",
    "nazmus": ROOT / "agents/super_replay_v4/n1_nazmus_weed.py",
    "k3": ROOT / "agents/v27_k3_weed.py",
    "tetsuya": ROOT / "agents/top3_tuned/raw_rank1_tetsuya.py",
}
V5_MODULE_NAMES = {
    "optimized_pkg",
    "optimized_pkg.entry",
    "e749a_niklita_consensus_network",
    "e750a_place_funding_repair",
    "e766a_universal_kenjo_medoid",
    "e773a_demand_aligned_pasture_network",
    "e774a_terminal_animal_frontier",
    "e775a_latent_pasture_activation",
    "e776a_engine_exact_latent_pasture",
    "late_bundle_diversifier",
    "optimized_pasture_policy",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _purge_v5_modules() -> None:
    for name in list(sys.modules):
        if name in V5_MODULE_NAMES or name.startswith("farming_v5_loaded_"):
            sys.modules.pop(name, None)
    v5_roots = tuple(str(path) for root in V5_ROOTS.values() for path in (root, root / "agents"))
    sys.path[:] = [entry for entry in sys.path if entry not in v5_roots]


def load_v5(root: Path, label: str):
    """Load one package while allowing v1 and v2 to coexist as callables."""
    _purge_v5_modules()
    sys.path.insert(0, str(root))
    try:
        spec = importlib.util.spec_from_file_location(
            f"farming_v5_loaded_{label}_{time.time_ns()}", root / "main.py"
        )
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load {root / 'main.py'}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        agent = module.kaggriculture_agent
        complete = agent.__globals__["_policy"].__globals__["_MODULE"]
        late = complete.PARENT
        e776 = late.PARENT
        e775 = e776.PARENT
        e774 = e775.PARENT
        e773 = e774.PARENT
        handles = {"complete": complete, "late": late, "e776": e776, "e775": e775, "e774": e774, "e773": e773}
        return agent, handles
    finally:
        sys.path.remove(str(root))


def load_variant(name: str):
    if name in V5_ROOTS:
        return load_v5(V5_ROOTS[name], name)
    return load_agent(AGENTS[name]), None


def load_opponent(name: str):
    return load_agent(OPPONENTS[name])


def _plain(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, Counter):
        return dict(value)
    return value


def v5_diagnostics(handles, seat: int) -> dict[str, Any] | None:
    if handles is None:
        return None
    state = handles["e773"]._STATE.get(seat, {})
    terminal = handles["complete"]._LAST_DIAGNOSTIC.get(seat, {})
    return {
        "assignments": deepcopy(state.get("assignments", {})),
        "cow_to_sheep": int(state.get("cow_to_sheep", 0) or 0),
        "sheep_to_cow": int(state.get("sheep_to_cow", 0) or 0),
        "deferred_cow_signal": deepcopy(state.get("deferred_cow_signal")),
        "cow_window_target": state.get("cow_window_target"),
        "cow_window_shops": deepcopy(state.get("cow_window_shops", [])),
        "decision_rows": deepcopy(state.get("decision_rows", [])),
        "terminal": {
            "step": terminal.get("step"),
            "intervened": bool(terminal.get("intervened", False)),
            "frontier": deepcopy(terminal.get("frontier", {})),
        },
    }


def state_checkpoint(states, seat: int, step: int) -> dict[str, Any]:
    obs = states[step][seat].observation
    farm = obs["farms"][seat]
    private = obs.get("private", {})
    return {
        "step": step,
        "day": int(obs.get("day", 0)),
        "money": float(farm.get("money", 0)),
        "hands": len(farm.get("hands", [])),
        "hires_today": int(farm.get("hires_today", 0)),
        "quadrants": list(farm.get("unlocked_quadrants", [])),
        "farmer": list(farm.get("farmer", [])),
        "counts": farm_counts(farm),
        "shed": dict(sorted(private.get("shed", {}).items())),
        "seeds": dict(sorted(private.get("seeds", {}).items())),
        "inventories": [dict(sorted(x.items())) for x in private.get("inventories", [])],
        "market_prices": dict(sorted(obs.get("market", {}).get("prices", {}).items())),
        "market_inventory": dict(sorted(obs.get("market", {}).get("inventory", {}).items())),
        "shops": list(obs.get("town", {}).get("unlocked_shops", [])),
    }


def run_case(job):
    stage, variant, opponent_name, seed, seat, keep_detail = job
    started = time.perf_counter()
    agent, handles = load_variant(variant)
    opponent = load_opponent(opponent_name)
    actions: list[dict[str, Any]] = []
    semantic_failures = []
    exceptions = []

    def checked(obs):
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
        return action

    pair = [opponent, opponent]
    pair[seat] = checked
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": int(seed)}, debug=False)
    runtime_error = None
    try:
        env.run(pair)
    except Exception as exc:
        runtime_error = repr(exc)
    if len(getattr(env, "steps", [])) != 720:
        return {
            "stage": stage,
            "variant": variant,
            "opponent": opponent_name,
            "seed": seed,
            "seat": seat,
            "runtime_error": runtime_error or f"steps={len(env.steps)}",
            "semantic_failures": semantic_failures,
            "exceptions": exceptions,
        }

    states = env.steps
    final = states[-1]
    replay = env.toJSON()
    own = float(final[seat].reward)
    other = float(final[1 - seat].reward)
    economics = economic_summary(replay, seat)
    if not keep_detail:
        economics.pop("daily", None)
    row = {
        "stage": stage,
        "variant": variant,
        "opponent": opponent_name,
        "seed": int(seed),
        "seat": int(seat),
        "runtime_error": runtime_error,
        "semantic_failures": semantic_failures,
        "exceptions": exceptions,
        "elapsed_s": time.perf_counter() - started,
        "own_money": own,
        "opponent_money": other,
        "advantage": own - other,
        "action_hash": digest(actions),
        "action_step_hashes": [digest([action]) for action in actions],
        "v5_diagnostics": v5_diagnostics(handles, seat),
        "livestock_escapes": animal_escapes(states, seat),
        "terminal": terminal_value(final, seat),
        "milestones": milestone_summary(states, seat),
        "economics": economics,
        "checkpoints": [
            state_checkpoint(states, seat, step)
            for step in (0, 1, 24, 72, 88, 144, 150, 169, 176, 240, 313, 360, 480, 576, 624, 672, 696, 718, 719)
        ],
    }
    if keep_detail:
        row["actions"] = actions
        row["daily_bank"] = daily_bank(states, seat)
        row["forensics"] = crop_and_worker_forensics(replay, seat, actions)
        row["daily_farm"] = [state_checkpoint(states, seat, min(day * 24, 719)) for day in range(30)]
    return _plain(row)


def raw_jobs():
    jobs = []
    for opponent_index, opponent in enumerate(OPPONENTS):
        for seed in range(920000 + opponent_index * 100, 920004 + opponent_index * 100):
            for seat in (0, 1):
                for variant in ("current_best", "v3", "v5_v1", "v5"):
                    jobs.append(("raw", variant, opponent, seed, seat, False))
    return jobs


def dossier_jobs():
    jobs = []
    for opponent_index, opponent in enumerate(("current_best", "v3", "crop_dusta")):
        seed = 921000 + opponent_index * 100
        for seat in (0, 1):
            for variant in ("current_best", "v3", "v5_v1", "v5"):
                jobs.append(("dossier", variant, opponent, seed, seat, True))
    return jobs


def jobs_for(stage: str):
    return raw_jobs() if stage == "raw" else dossier_jobs()


def key(job) -> str:
    return "|".join(map(str, job[:5]))


def execute(stage: str, workers: int):
    OUT.mkdir(parents=True, exist_ok=True)
    partial = OUT / f"{stage}.partial.json"
    rows = json.loads(partial.read_text()) if partial.exists() else []
    done = {key((r["stage"], r["variant"], r["opponent"], r["seed"], r["seat"])) for r in rows}
    pending = [job for job in jobs_for(stage) if key(job) not in done]
    print(f"{stage}: {len(rows)} cached, {len(pending)} pending", flush=True)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(run_case, job): job for job in pending}
        for index, future in enumerate(as_completed(futures), 1):
            rows.append(future.result())
            if index % 4 == 0 or index == len(pending):
                partial.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n")
                print(f"{stage}: {index}/{len(pending)} new games", flush=True)
    rows.sort(key=lambda r: (r["opponent"], r["seed"], r["seat"], r["variant"]))
    partial.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n")
    return rows


def bootstrap_mean_ci(values, resamples=10000, seed=921559):
    values = [float(x) for x in values]
    if not values:
        return {"mean": None, "low": None, "high": None, "resamples": 0}
    rng = random.Random(seed)
    n = len(values)
    means = [statistics.fmean(values[rng.randrange(n)] for _ in range(n)) for _ in range(resamples)]
    return {"mean": statistics.fmean(values), "low": percentile(means, .025), "high": percentile(means, .975), "resamples": resamples}


def paired(rows, left: str, right: str):
    groups = defaultdict(dict)
    for row in rows:
        groups[(row["opponent"], row["seed"], row["seat"])][row["variant"]] = row
    result = []
    for (opponent, seed, seat), group in sorted(groups.items()):
        if left not in group or right not in group:
            continue
        a, b = group[left], group[right]
        hashes_a, hashes_b = a.get("action_step_hashes", []), b.get("action_step_hashes", [])
        prefix = 0
        for ha, hb in zip(hashes_a, hashes_b):
            if ha != hb:
                break
            prefix += 1
        result.append({
            "opponent": opponent,
            "seed": seed,
            "seat": seat,
            "left": left,
            "right": right,
            "left_money": a["own_money"],
            "right_money": b["own_money"],
            "own_money_delta": a["own_money"] - b["own_money"],
            "left_advantage": a["advantage"],
            "right_advantage": b["advantage"],
            "advantage_delta": a["advantage"] - b["advantage"],
            "opponent_money_delta": a["opponent_money"] - b["opponent_money"],
            "exact_action_common_prefix": prefix,
            "left_escapes": len(a.get("livestock_escapes", [])),
            "right_escapes": len(b.get("livestock_escapes", [])),
        })
    return result


def summarize_pairs(pairs):
    def one(selected):
        own = [x["own_money_delta"] for x in selected]
        adv = [x["advantage_delta"] for x in selected]
        return {
            "conditions": len(selected),
            "own_money_delta": {
                "mean": statistics.fmean(own) if own else None,
                "median": statistics.median(own) if own else None,
                "p25": percentile(own, .25),
                "p10": percentile(own, .10),
                "p5": percentile(own, .05),
                "worst": min(own) if own else None,
                "negative_rate": sum(x < 0 for x in own) / len(own) if own else None,
                "bootstrap_95": bootstrap_mean_ci(own),
                "sign_test": sign_test(own),
            },
            "advantage_delta": {
                "mean": statistics.fmean(adv) if adv else None,
                "median": statistics.median(adv) if adv else None,
                "p25": percentile(adv, .25),
                "p10": percentile(adv, .10),
                "p5": percentile(adv, .05),
                "worst": min(adv) if adv else None,
                "negative_rate": sum(x < 0 for x in adv) / len(adv) if adv else None,
                "bootstrap_95": bootstrap_mean_ci(adv),
                "sign_test": sign_test(adv),
            },
            "wins_losses_ties": {
                "wins": sum(x > 0 for x in adv),
                "losses": sum(x < 0 for x in adv),
                "ties": sum(x == 0 for x in adv),
            },
            "left_escapes": sum(x["left_escapes"] for x in selected),
            "right_escapes": sum(x["right_escapes"] for x in selected),
        }
    return {
        "overall": one(pairs),
        "by_opponent": {opponent: one([x for x in pairs if x["opponent"] == opponent]) for opponent in sorted({x["opponent"] for x in pairs})},
        "by_seat": {str(seat): one([x for x in pairs if x["seat"] == seat]) for seat in (0, 1)},
    }


def write_summaries(rows):
    comparisons = {
        "v5_minus_current_best": paired(rows, "v5", "current_best"),
        "v5_minus_v3": paired(rows, "v5", "v3"),
        "v5_minus_v1": paired(rows, "v5", "v5_v1"),
        "v1_minus_v3": paired(rows, "v5_v1", "v3"),
        "v1_minus_current_best": paired(rows, "v5_v1", "current_best"),
    }
    payload = {
        name: {"summary": summarize_pairs(pairs), "pairs": pairs}
        for name, pairs in comparisons.items()
    }
    (OUT / "raw_summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("raw", "dossier", "all"))
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    stages = ("raw", "dossier") if args.stage == "all" else (args.stage,)
    for stage in stages:
        rows = execute(stage, args.workers)
        if stage == "raw":
            write_summaries(rows)
    print("done", flush=True)


if __name__ == "__main__":
    main()
