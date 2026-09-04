"""Controlled Top-10 opening-signature remapping experiment.

This keeps the three already safety-repaired complete parents intact and only
changes the one-time step-1 mapping from three public opening signatures to a
parent.  It is deliberately separate from the frozen portfolio and submission.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import json
from pathlib import Path
import statistics
from runpy import run_path

from kaggle_environments import make

import run_super_replay_search as engine
from run_epic_experiments import _independent_shop_schedule, _run_with_fixed_shops


ROOT = Path(__file__).resolve().parent
PARENT_PATHS = {
    "dmitry": "agents/top50_distilled/top50_dmitry_safe.py",
    "hanserong": "agents/top50_distilled/top50_hanserong_safe.py",
    "redblack": "agents/top50_distilled/top50_redblack_safe.py",
}
BASELINE = "agents/top50_distilled/top50_observable_portfolio.py"
TOP10 = [
    ("top10_55425101", "agents/super_replay_v3/v3_raw_55425101.py", "fam02"),
    ("top10_55435941", "agents/super_replay_v3/v3_raw_55435941.py", "fam03"),
    ("top10_55463387", "agents/super_replay_v3/v3_raw_55463387.py", "fam01"),
    ("top10_55463671", "agents/super_replay_v3/v3_raw_55463671.py", "fam01"),
    ("top10_55470275", "agents/super_replay_v3/v3_raw_55470275.py", "fam01"),
    ("top10_55445174", "agents/super_replay_v3/v3_raw_55445174.py", "fam02"),
    ("top10_55468815", "agents/super_replay_v3/v3_raw_55468815.py", "fam01"),
    ("top10_55474695", "agents/super_replay_v3/v3_raw_55474695.py", "fam01"),
    ("top10_55469248", "agents/super_replay_v3/v3_raw_55469248.py", "fam01"),
    ("top10_55476469", "agents/super_replay_v3/v3_raw_55476469.py", "fam01"),
]
HARD = [
    ("tetsuya", "agents/top3_tuned/raw_rank1_tetsuya.py"),
    ("crop_dusta", "agents/top3_tuned/raw_rank2_crop_dusta.py"),
    ("oceanmix", "agents/top3_tuned/raw_rank3_oceanmix.py"),
    ("livestock_crop", "agents/proxies/livestock_crop.py"),
    ("land_expander", "agents/proxies/land_expander.py"),
    ("high_labor", "agents/proxies/high_labor.py"),
    ("phased_rotation", "agents/proxies/phased_rotation.py"),
]


def _signature(obs):
    other = obs["farms"][1 - obs["player"]]
    money = float(other.get("money", 0.0))
    hands = len(other.get("hands", []))
    # These bins cover the three reproducible Top-10 step-1 signatures.  The
    # frozen selector's other guards remain the fallback for all other states.
    if money <= 3.1 and hands == 4:
        return "fam01"
    if 10.0 < money < 20.0 and hands == 5:
        return "fam02"
    if 300.0 < money < 500.0 and hands == 5:
        return "fam03"
    return None


def _frozen_fallback(obs):
    other = obs["farms"][1 - obs["player"]]
    money = float(other.get("money", 0.0))
    hands = len(other.get("hands", []))
    if money >= 2500 and hands == 0:
        return "redblack"
    if money >= 1500 and hands >= 6:
        return "hanserong"
    if 3 < money <= 10 and hands >= 5:
        return "hanserong"
    return "dmitry"


def _run_game(policy, opponent, seed, seat, fixed):
    parents = {name: run_path(str(ROOT / path))["agent"] for name, path in PARENT_PATHS.items()}
    selected = None

    def candidate(obs):
        nonlocal selected
        step = int(obs.get("step", 0))
        if step == 0:
            selected = None
            outputs = {name: parent(obs) for name, parent in parents.items()}
            return outputs["dmitry"]
        if selected is None:
            selected = policy.get(_signature(obs), _frozen_fallback(obs))
        return parents[selected](obs)

    rival = engine._load_opponent(opponent)
    calls = 0
    semantic = []

    def checked(obs):
        nonlocal calls
        action = candidate(obs)
        try:
            engine._semantic_validate(obs, action)
        except Exception as exc:
            semantic.append({"step": int(obs["step"]), "error": repr(exc)})
        calls += 1
        return action

    pair = [rival, rival]
    pair[seat] = checked
    config = {"episodeSteps": 720, "seed": int(seed)}
    env = make("kaggriculture", configuration=config, debug=True)
    runtime = None
    try:
        if fixed:
            _run_with_fixed_shops(env, pair, _independent_shop_schedule(seed))
        else:
            env.run(pair)
    except Exception as exc:
        runtime = repr(exc)
    if runtime or len(env.steps) != 720:
        return {
            "runtime_error": runtime or f"steps={len(env.steps)}",
            "semantic_failures": semantic,
            "candidate": str(policy),
            "opponent": opponent,
            "seed": int(seed),
            "seat": int(seat),
            "fixed": bool(fixed),
        }
    final = env.steps[-1]
    mine = float(final[seat].reward)
    theirs = float(final[1 - seat].reward)
    stranded_value, stranded = engine._inventory_value(final[seat])
    replay = env.toJSON()
    transition = engine._transition_metrics(replay, seat)
    bought = transition["animal_buy_requests"]
    crops, animals, weeds = engine._farm_counts(final[seat].observation["farms"][seat])
    losses = {animal: max(0, int(bought.get(animal, 0)) - int(animals.get(animal, 0))) for animal in ("GOOSE", "COW", "SHEEP")}
    return {
        "runtime_error": None,
        "semantic_failures": semantic,
        "candidate": str(policy),
        "opponent": opponent,
        "seed": int(seed),
        "seat": int(seat),
        "fixed": bool(fixed),
        "money": mine,
        "opponent_money": theirs,
        "advantage": mine - theirs,
        "stranded_value": stranded_value,
        "stranded": stranded,
        "livestock_losses": losses,
        "final_animals": dict(animals),
        "final_crops": dict(crops),
        "final_weeds": weeds,
        "selected_parent": selected,
        "calls": calls,
    }


def _policy_rows():
    names = ("dmitry", "hanserong", "redblack")
    for a in names:
        for b in names:
            for c in names:
                yield {"fam01": a, "fam02": b, "fam03": c}


def _label(policy):
    return "fam01=%s,fam02=%s,fam03=%s" % (policy["fam01"], policy["fam02"], policy["fam03"])


def _jobs(policies, seeds, include_hard, natural):
    opponents = [(name, path) for name, path, _ in TOP10]
    if include_hard:
        opponents += HARD
    jobs = []
    for policy in policies:
        label = _label(policy)
        for name, path in opponents:
            for seed in seeds:
                for seat in (0, 1):
                    jobs.append((label, policy, name, path, seed, seat, natural))
    return jobs


def _summarize(rows):
    output = {}
    for label in sorted({r["candidate"] for r in rows}):
        valid = [r for r in rows if r["candidate"] == label and not r.get("runtime_error")]
        adv = [r["advantage"] for r in valid]
        output[label] = {
            "games": len(valid),
            "wins": sum(x > 0 for x in adv),
            "losses": sum(x < 0 for x in adv),
            "ties": sum(x == 0 for x in adv),
            "win_rate": sum(x > 0 for x in adv) / len(adv) if adv else 0.0,
            "average_money": statistics.fmean(r["money"] for r in valid) if valid else 0.0,
            "average_advantage": statistics.fmean(adv) if adv else 0.0,
            "median_advantage": statistics.median(adv) if adv else 0.0,
            "p10_advantage": sorted(adv)[max(0, int(0.10 * (len(adv) - 1)))] if adv else 0.0,
            "worst_advantage": min(adv) if adv else 0.0,
            "runtime_failures": sum(bool(r.get("runtime_error")) for r in rows if r["candidate"] == label),
            "semantic_failures": sum(len(r.get("semantic_failures", [])) for r in rows if r["candidate"] == label),
            "livestock_losses": sum(sum(r.get("livestock_losses", {}).values()) for r in valid),
            "stranding_games": sum(r.get("stranded_value", 0) > 500 for r in valid),
            "by_opponent": {},
        }
        for opp in sorted({r["opponent"] for r in valid}):
            subset = [r for r in valid if r["candidate"] == label and r["opponent"] == opp]
            vals = [r["advantage"] for r in subset]
            output[label]["by_opponent"][opp] = {
                "games": len(vals),
                "wins": sum(x > 0 for x in vals),
                "losses": sum(x < 0 for x in vals),
                "average_money": statistics.fmean(r["money"] for r in subset),
                "average_advantage": statistics.fmean(vals),
            }
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", nargs="+", type=int, default=[58000])
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--include-hard", action="store_true")
    parser.add_argument("--natural", action="store_true")
    parser.add_argument("--output", default="experiments/top10_parent_mapping_screen.json")
    parser.add_argument("--policies", default="all", help="all or comma-separated labels")
    args = parser.parse_args()
    policies = list(_policy_rows())
    if args.policies != "all":
        wanted = set(args.policies.split(";"))
        policies = [p for p in policies if _label(p) in wanted]
    jobs = _jobs(policies, args.seeds, args.include_hard, args.natural)
    rows = []
    print(f"Running {len(jobs)} games", flush=True)
    with ProcessPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {
            pool.submit(_run_game, policy, path, seed, seat, not args.natural): (label, policy)
            for label, policy, _opponent_name, path, seed, seat, _natural in jobs
        }
        for index, future in enumerate(as_completed(futures), 1):
            try:
                rows.append(future.result())
            except Exception as exc:
                label, policy = futures[future]
                rows.append({"candidate": label, "runtime_error": repr(exc)})
            if index % 50 == 0 or index == len(futures):
                print(f"completed {index}/{len(futures)}", flush=True)
    rows.sort(key=lambda r: (r.get("candidate", ""), r.get("opponent", ""), r.get("seed", 0), r.get("seat", 0)))
    payload = {
        "schema_version": 1,
        "design": "one-time remapping of three Top-10 step-1 opening signatures among existing safe complete parents",
        "seeds": list(args.seeds),
        "natural": bool(args.natural),
        "include_hard": bool(args.include_hard),
        "baseline": BASELINE,
        "summaries": _summarize(rows),
        "games": rows,
    }
    out = (ROOT / args.output).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(out)
    for label, summary in sorted(payload["summaries"].items(), key=lambda kv: kv[1]["average_advantage"], reverse=True):
        print(label, summary["games"], summary["wins"], summary["losses"], round(summary["average_money"], 1), round(summary["average_advantage"], 1), round(summary["p10_advantage"], 1), summary["livestock_losses"])


if __name__ == "__main__":
    main()
