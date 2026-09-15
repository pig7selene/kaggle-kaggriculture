"""Self-play the price-gated variant against the ungated 0911 candidate.

The metric here is the outcome, not action similarity. Every imitation study in
this line has confirmed that matching a frontier agent's actions is not the same
as beating anyone, and the production profile showed our real deficit is the
shape of the margin distribution rather than its mean: our tenth percentile is a
3,319 loss where Majkel's is a 654 win. So this reports the distribution, not
just a win count, and treats the tenth percentile and the worst game as the
numbers that matter.

Each seed is played in both seats, so seat effects cancel. The gated variant is
always the left agent and the ungated parent the right one, so a positive margin
is a gain for the gate.

Safety checks come from the existing screens: per-step semantic validation of
the gated agent's actions, livestock escapes for both seats, agent status, and
runtime errors. Nothing is submitted to Kaggle.
"""

from __future__ import annotations

import argparse
from collections import Counter
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
GATED = ROOT / "agents/smaller_market_shock_v233h_gate/main.py"
PARENT = ROOT / "agents/smaller_market_shock_v233h_non_yarn_0911/main.py"
OUTPUT = ROOT / "experiments/inventory_gate_selfplay.json"
REPORT = ROOT / "experiments/inventory_gate_selfplay.md"


def load_agent(path: Path, tag: str):
    name = "gate_selfplay_" + hashlib.sha256(
        f"{path}:{tag}:{time.time_ns()}".encode()
    ).hexdigest()[:24]
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
    seed, gated_seat = job
    gated = load_agent(GATED, f"gate:{seed}:{gated_seat}")
    parent = load_agent(PARENT, f"parent:{seed}:{gated_seat}")
    semantic_failures, exceptions = [], [[], []]

    def wrap(agent, index, validate):
        def inner(observation, configuration=None):
            try:
                action = invoke(agent, observation, configuration)
                if validate:
                    try:
                        semantic_check(observation, action)
                    except Exception as exc:
                        semantic_failures.append(
                            {"step": int(observation.get("step", -1)), "error": repr(exc)}
                        )
                return action
            except Exception as exc:
                exceptions[index].append(
                    {"step": int(observation.get("step", -1)), "error": repr(exc)}
                )
                raise
        return inner

    players = [None, None]
    players[gated_seat] = wrap(gated, gated_seat, True)
    players[1 - gated_seat] = wrap(parent, 1 - gated_seat, False)
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=False)
    runtime_error = None
    try:
        env.run(players)
    except Exception as exc:
        runtime_error = repr(exc)
    if len(getattr(env, "steps", [])) != 720:
        return {"seed": seed, "gated_seat": gated_seat,
                "runtime_error": runtime_error or "incomplete episode",
                "agent_error": True, "semantic_failures": semantic_failures,
                "exceptions_by_seat": exceptions}

    final = env.steps[-1]
    gated_money = float(final[gated_seat].reward)
    parent_money = float(final[1 - gated_seat].reward)
    statuses = [str(final[i].status) for i in range(2)]
    telemetry = deepcopy(getattr(gated, "telemetry", {}) or {})
    gate_state = telemetry.get("gate_state", {}) if isinstance(telemetry, dict) else {}
    return {
        "seed": seed,
        "gated_seat": gated_seat,
        "shops": list(final[gated_seat].observation["town"]["unlocked_shops"])[:2],
        "gated_money": gated_money,
        "parent_money": parent_money,
        "margin": gated_money - parent_money,
        "outcome": ("win" if gated_money > parent_money
                    else "loss" if gated_money < parent_money else "tie"),
        "runtime_error": runtime_error,
        "agent_error": any(s not in {"DONE", "Status.DONE"} for s in statuses),
        "semantic_failures": semantic_failures,
        "gated_livestock_escapes": len(animal_escapes(env.steps, gated_seat)),
        "parent_livestock_escapes": len(animal_escapes(env.steps, 1 - gated_seat)),
        "gate_skipped_units": int(gate_state.get("skipped", 0) or 0),
        "gate_released_units": int(gate_state.get("released", 0) or 0),
        "exceptions_by_seat": exceptions,
    }


def summarize(rows):
    played = [r for r in rows if r.get("outcome")]
    if not played:
        return {"games": 0}
    margins = [r["margin"] for r in played]
    tally = Counter(r["outcome"] for r in played)
    return {
        "games": len(played),
        "wins": tally["win"], "losses": tally["loss"], "ties": tally["tie"],
        "gsr": (tally["win"] + 0.5 * tally["tie"]) / len(played),
        "mean_margin": statistics.fmean(margins),
        "median_margin": statistics.median(margins),
        "p10_margin": statistics.quantiles(margins, n=10)[0] if len(margins) >= 10 else min(margins),
        "worst_margin": min(margins),
        "best_margin": max(margins),
        "runtime_errors": sum(bool(r.get("runtime_error")) for r in rows),
        "agent_errors": sum(bool(r.get("agent_error")) for r in rows),
        "semantic_failures": sum(len(r.get("semantic_failures", [])) for r in rows),
        "gated_livestock_escapes": sum(r.get("gated_livestock_escapes", 0) for r in played),
        "parent_livestock_escapes": sum(r.get("parent_livestock_escapes", 0) for r in played),
        "mean_units_skipped": statistics.fmean(r.get("gate_skipped_units", 0) for r in played),
        "mean_units_released": statistics.fmean(r.get("gate_released_units", 0) for r in played),
        "games_where_gate_fired": sum(1 for r in played if r.get("gate_skipped_units", 0) > 0),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=40)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()

    jobs = [(seed, seat) for seed in range(1, args.seeds + 1) for seat in (0, 1)]
    rows = []
    started = time.time()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_game, job) for job in jobs]
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            print(f"{len(rows)}/{len(jobs)} seed={row['seed']} seat={row['gated_seat']} "
                  f"{row.get('outcome', 'ERROR')} {row.get('margin', 0):+,.0f}", flush=True)
    rows.sort(key=lambda r: (r["seed"], r["gated_seat"]))

    summary = summarize(rows)
    data = {
        "schema_version": 1,
        "purpose": "does the premium-sale price gate beat the ungated 0911 candidate",
        "gated_agent": str(GATED.relative_to(ROOT)),
        "ungated_parent": str(PARENT.relative_to(ROOT)),
        "parent_submission_id": 56250442,
        "seeds": args.seeds,
        "summary": summary,
        "elapsed_seconds": time.time() - started,
        "kaggle_submission_made": False,
        "games": rows,
    }
    args.output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    lines = ["# Inventory gate self-play", "",
             f"Gated variant against the ungated 0911 candidate, {args.seeds} seeds in both "
             f"seats ({summary['games']} games). A positive margin is a gain for the gate.", "",
             "| Metric | Value |", "| --- | ---: |",
             f"| W/L/T | {summary['wins']}/{summary['losses']}/{summary['ties']} |",
             f"| GSR | {summary['gsr']:.4f} |",
             f"| Mean margin | {summary['mean_margin']:+,.0f} |",
             f"| Median margin | {summary['median_margin']:+,.0f} |",
             f"| p10 margin | {summary['p10_margin']:+,.0f} |",
             f"| Worst | {summary['worst_margin']:+,.0f} |",
             f"| Best | {summary['best_margin']:+,.0f} |",
             f"| Games where the gate fired | {summary['games_where_gate_fired']} |",
             f"| Mean units skipped / released | {summary['mean_units_skipped']:.1f} / "
             f"{summary['mean_units_released']:.1f} |",
             f"| Runtime errors | {summary['runtime_errors']} |",
             f"| Agent errors | {summary['agent_errors']} |",
             f"| Semantic failures | {summary['semantic_failures']} |",
             f"| Livestock escapes, gated / parent | {summary['gated_livestock_escapes']} / "
             f"{summary['parent_livestock_escapes']} |"]
    args.report.write_text("\n".join(lines) + "\n")
    print(args.output)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
