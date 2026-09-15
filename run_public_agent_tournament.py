"""Head-to-head the current public agents against our own best.

The question this answers is the only one that bears on score right now: is any
currently available public agent in a different class from what we run? Our best
verified submission is Terminal D at 2496.8; the leaderboard's fourth through
fifteenth places sit in a dense band from 2969 to 3034, which is the shape of a
strong public agent plus small tweaks. A gap that size is not closed by adding
another overlay to a 2500 agent, so before any module work it is worth knowing
whether one of these notebooks simply beats us.

Local results have failed to predict leaderboard direction before -- the
calibration report found 99% of official opponents unidentifiable and got the
Terminal-D-versus-front-run direction wrong -- so this is evidence, not proof.
But the question here is not whether a tweak is worth two percent; it is whether
a different agent is in a different class, and a lopsided local record answers
that.

Every contender runs in both seats on each seed so seat effects cancel. Safety
checks follow the existing screens: per-step semantic validation, livestock
escapes, agent status and runtime errors, all recorded per game. Nothing is
submitted to Kaggle.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time

from kaggle_environments import make

from run_raw55899537_final_validation import animal_escapes, semantic_validate


ROOT = Path(__file__).resolve().parent
PULL = Path("/private/tmp/kaggriculture_pull_0915/out")
OUTPUT = ROOT / "experiments" / "public_agent_tournament.json"
REPORT = ROOT / "experiments" / "public_agent_tournament.md"

AGENTS = {
    # ours
    "Ours0911": ROOT / "agents/smaller_market_shock_v233h_non_yarn_0911/main.py",
    "TerminalD": ROOT / "agents/shop_router_0909_terminal/main.py",
    # public, pulled 2026-09-15
    "AhmedV43": PULL / "kaggriculture-v43-recovering-lost-harvests/main.py",
    "LynnV44": PULL / "farming-score-v5-timing-optimized/main.py",
    "MoonMelons": PULL / "kaggriculture-frontier-the-moon-counts-melons/main.py",
    "MoonMarketSmart": PULL / "kaggriculture-frontier-the-moon-counts-melons/"
                              "reacting_market_smart_public_refresh/main.py",
}
OURS = ("Ours0911", "TerminalD")
PUBLIC = ("AhmedV43", "LynnV44", "MoonMelons", "MoonMarketSmart")


def load_agent(path: Path, tag: str):
    name = "tourney_" + hashlib.sha256(f"{path}:{tag}:{time.time_ns()}".encode()).hexdigest()[:24]
    spec = __import__("importlib.util").util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = __import__("importlib.util").util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    found = getattr(module, "agent", None) or getattr(module, "kaggle_agent", None)
    if not callable(found):
        raise TypeError(f"no callable agent in {path}")
    return found


def invoke(agent, observation, configuration=None):
    try:
        return agent(observation, configuration)
    except TypeError:
        return agent(observation)


def semantic_check(observation: dict, action: dict) -> None:
    cleaned = deepcopy(action)
    if isinstance(cleaned, dict) and isinstance(cleaned.get("market"), list):
        cleaned["market"] = [order for order in cleaned["market"] if order]
    semantic_validate(observation, cleaned)


def run_game(job):
    left_name, right_name, seed, left_seat = job
    failures = {left_name: [], right_name: []}
    exceptions = {left_name: [], right_name: []}

    def wrap(agent, name):
        def inner(observation, configuration=None):
            try:
                action = invoke(agent, observation, configuration)
                try:
                    semantic_check(observation, action)
                except Exception as exc:
                    failures[name].append(
                        {"step": int(observation.get("step", -1)), "error": repr(exc)}
                    )
                return action
            except Exception as exc:
                exceptions[name].append(
                    {"step": int(observation.get("step", -1)), "error": repr(exc)}
                )
                raise
        return inner

    try:
        left = load_agent(AGENTS[left_name], f"{left_name}:{seed}:{left_seat}")
        right = load_agent(AGENTS[right_name], f"{right_name}:{seed}:{left_seat}")
    except Exception as exc:
        return {"left": left_name, "right": right_name, "seed": seed,
                "left_seat": left_seat, "load_error": repr(exc)}

    players = [None, None]
    players[left_seat] = wrap(left, left_name)
    players[1 - left_seat] = wrap(right, right_name)
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=False)
    runtime_error = None
    started = time.time()
    try:
        env.run(players)
    except Exception as exc:
        runtime_error = repr(exc)
    if len(getattr(env, "steps", [])) != 720:
        return {"left": left_name, "right": right_name, "seed": seed, "left_seat": left_seat,
                "runtime_error": runtime_error or "incomplete episode",
                "agent_error": True,
                "semantic_failures": {k: len(v) for k, v in failures.items()},
                "exceptions": {k: v[:3] for k, v in exceptions.items()}}

    final = env.steps[-1]
    left_money = float(final[left_seat].reward)
    right_money = float(final[1 - left_seat].reward)
    statuses = [str(final[i].status) for i in range(2)]
    return {
        "left": left_name, "right": right_name, "seed": seed, "left_seat": left_seat,
        "shops": list(final[left_seat].observation["town"]["unlocked_shops"])[:2],
        "left_money": left_money, "right_money": right_money,
        "margin": left_money - right_money,
        "outcome": ("win" if left_money > right_money
                    else "loss" if left_money < right_money else "tie"),
        "runtime_error": runtime_error,
        "agent_error": any(s not in {"DONE", "Status.DONE"} for s in statuses),
        "semantic_failures": {k: len(v) for k, v in failures.items()},
        "livestock_escapes": {left_name: len(animal_escapes(env.steps, left_seat)),
                              right_name: len(animal_escapes(env.steps, 1 - left_seat))},
        "exceptions": {k: v[:3] for k, v in exceptions.items()},
        "seconds": time.time() - started,
    }


def pairing_summary(rows, left_name, right_name):
    played = [r for r in rows if r.get("outcome")
              and r["left"] == left_name and r["right"] == right_name]
    if not played:
        return None
    margins = [r["margin"] for r in played]
    tally = Counter(r["outcome"] for r in played)
    return {
        "games": len(played), "wins": tally["win"], "losses": tally["loss"],
        "ties": tally["tie"],
        "gsr": (tally["win"] + 0.5 * tally["tie"]) / len(played),
        "mean_margin": statistics.fmean(margins),
        "median_margin": statistics.median(margins),
        "worst_margin": min(margins), "best_margin": max(margins),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=12)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--smoke", action="store_true",
                        help="one seed per public agent against Ours0911, to check they run")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()

    missing = [name for name, path in AGENTS.items() if not path.is_file()]
    if missing:
        raise RuntimeError(f"missing agent files: {missing}")

    if args.smoke:
        jobs = [(name, "Ours0911", 1, 0) for name in PUBLIC]
    else:
        jobs = [(public, ours, seed, seat)
                for public in PUBLIC for ours in OURS
                for seed in range(1, args.seeds + 1) for seat in (0, 1)]

    rows = []
    started = time.time()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_game, job) for job in jobs]
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            tag = row.get("outcome") or row.get("load_error") or row.get("runtime_error") or "?"
            print(f"{len(rows)}/{len(jobs)} {row['left']} vs {row['right']} "
                  f"seed={row['seed']} seat={row['left_seat']} {str(tag)[:60]} "
                  f"{row.get('margin', 0):+,.0f}", flush=True)

    summaries = {}
    for public in PUBLIC:
        for ours in OURS:
            key = f"{public} vs {ours}"
            summary = pairing_summary(rows, public, ours)
            if summary:
                summaries[key] = summary

    data = {
        "schema_version": 1,
        "purpose": "is any current public agent in a different class from ours",
        "agents": {name: str(path) for name, path in AGENTS.items()},
        "pulled": "2026-09-15",
        "seeds": 1 if args.smoke else args.seeds,
        "smoke": args.smoke,
        "summaries": summaries,
        "load_errors": [r for r in rows if r.get("load_error")],
        "elapsed_seconds": time.time() - started,
        "kaggle_submission_made": False,
        "games": rows,
    }
    args.output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    lines = ["# Public agent tournament", "",
             f"Public agents pulled 2026-09-15, each against ours in both seats. "
             f"A positive margin favours the public agent.", "",
             "| Pairing | N | W/L/T | GSR | Mean margin | Median | Worst | Best |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for key, s in sorted(summaries.items(), key=lambda kv: -kv[1]["gsr"]):
        lines.append(
            f"| {key} | {s['games']} | {s['wins']}/{s['losses']}/{s['ties']} | "
            f"{s['gsr']:.3f} | {s['mean_margin']:+,.0f} | {s['median_margin']:+,.0f} | "
            f"{s['worst_margin']:+,.0f} | {s['best_margin']:+,.0f} |"
        )
    problems = [r for r in rows if r.get("load_error") or r.get("runtime_error")
                or r.get("agent_error")]
    if problems:
        lines += ["", "## Problems", ""]
        for r in problems[:20]:
            lines.append(f"- {r['left']} vs {r['right']} seed {r['seed']}: "
                         f"{r.get('load_error') or r.get('runtime_error') or 'agent error'}")
    args.report.write_text("\n".join(lines) + "\n")
    print(args.output)
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
