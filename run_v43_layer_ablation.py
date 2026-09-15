"""What are V43's six disabled layers actually worth?

The shipped V43 runs three of its nine layers:

    _SETTINGS = {'hand_align': True, 'weed_repair': True, 'sell_lead': True,
                 'budget_guard': False, 'room_guard': False, 'clamp_sells': False,
                 'dead_stock': False, 'terminal_liquidation': False,
                 'front_run': False}

while the chassis's own DEFAULT_SETTINGS has all nine on. Three of the disabled
ones answer mechanics this repository measured independently: room_guard guards
the end-of-day shed overflow that destroys about five units twice per episode in
our own official replays, clamp_sells trims the speculative thousand-unit
liquidation orders we found fill nothing, and terminal_liquidation is simply not
running at all.

Each variant is the shipped agent with settings patched, played against the
shipped agent itself in both seats, so a positive margin is that switch's value.
Turning a switch on may also cost something -- the author disabled them for some
reason -- and that is the point of measuring rather than assuming.

Nothing is submitted to Kaggle.
"""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import statistics
import sys
import time

from kaggle_environments import make

from run_raw55899537_final_validation import animal_escapes, semantic_validate


ROOT = Path(__file__).resolve().parent
BASE = Path("/private/tmp/kaggriculture_pull_0915/out/"
            "kaggriculture-v43-recovering-lost-harvests/main.py")
VARIANTS = Path("/private/tmp/kaggriculture_v43_variants")
OUTPUT = ROOT / "experiments" / "v43_layer_ablation.json"
REPORT = ROOT / "experiments" / "v43_layer_ablation.md"

SHIPPED = {"hand_align": True, "weed_repair": True, "sell_lead": True,
           "budget_guard": False, "room_guard": False, "clamp_sells": False,
           "dead_stock": False, "terminal_liquidation": False, "front_run": False}
DISABLED = tuple(k for k, v in SHIPPED.items() if not v)


def build_variants() -> dict[str, Path]:
    """Write one patched copy of the agent per settings configuration."""
    source = BASE.read_text()
    pattern = re.compile(r"^_SETTINGS=\{.*?\}$", re.M)
    if not pattern.search(source):
        raise RuntimeError("could not find the _SETTINGS line to patch")

    configs = {"shipped": dict(SHIPPED), "all_on": {k: True for k in SHIPPED}}
    for switch in DISABLED:
        configs[f"+{switch}"] = {**SHIPPED, switch: True}
    # budget_guard scores 0.075 GSR on its own but all_on still wins, so the
    # layers interact; this isolates whether dropping it beats all_on.
    configs["all_on_no_budget"] = {**{k: True for k in SHIPPED}, "budget_guard": False}
    configs["room_plus_clamp"] = {**SHIPPED, "room_guard": True, "clamp_sells": True}

    VARIANTS.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, config in configs.items():
        text = pattern.sub("_SETTINGS=" + repr(config), source, count=1)
        if "_SETTINGS=" + repr(config) not in text:
            raise RuntimeError(f"patch failed for {name}")
        path = VARIANTS / f"{name.replace('+', 'plus_')}.py"
        path.write_text(text)
        paths[name] = path
    return paths


PATHS: dict[str, Path] = {}


def load_agent(path: Path, tag: str):
    name = "ablate_" + hashlib.sha256(f"{path}:{tag}:{time.time_ns()}".encode()).hexdigest()[:24]
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


def run_game(job):
    variant, variant_path, base_path, seed, variant_seat = job
    failures, exceptions = [], []

    def wrap(agent, validate):
        def inner(observation, configuration=None):
            try:
                action = invoke(agent, observation, configuration)
                if validate:
                    try:
                        semantic_validate(observation, {
                            **deepcopy(action),
                            "market": [o for o in (action.get("market") or []) if o],
                        })
                    except Exception as exc:
                        failures.append({"step": int(observation.get("step", -1)),
                                         "error": repr(exc)})
                return action
            except Exception as exc:
                exceptions.append({"step": int(observation.get("step", -1)), "error": repr(exc)})
                raise
        return inner

    try:
        challenger = load_agent(Path(variant_path), f"{variant}:{seed}:{variant_seat}")
        incumbent = load_agent(Path(base_path), f"shipped:{seed}:{variant_seat}")
    except Exception as exc:
        return {"variant": variant, "seed": seed, "variant_seat": variant_seat,
                "load_error": repr(exc)}

    players = [None, None]
    players[variant_seat] = wrap(challenger, True)
    players[1 - variant_seat] = wrap(incumbent, False)
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=False)
    runtime_error = None
    try:
        env.run(players)
    except Exception as exc:
        runtime_error = repr(exc)
    if len(getattr(env, "steps", [])) != 720:
        return {"variant": variant, "seed": seed, "variant_seat": variant_seat,
                "runtime_error": runtime_error or "incomplete episode", "agent_error": True,
                "semantic_failures": len(failures), "exceptions": exceptions[:3]}

    final = env.steps[-1]
    mine = float(final[variant_seat].reward)
    theirs = float(final[1 - variant_seat].reward)
    statuses = [str(final[i].status) for i in range(2)]
    return {
        "variant": variant, "seed": seed, "variant_seat": variant_seat,
        "variant_money": mine, "shipped_money": theirs, "margin": mine - theirs,
        "outcome": "win" if mine > theirs else "loss" if mine < theirs else "tie",
        "runtime_error": runtime_error,
        "agent_error": any(s not in {"DONE", "Status.DONE"} for s in statuses),
        "semantic_failures": len(failures),
        "variant_livestock_escapes": len(animal_escapes(env.steps, variant_seat)),
        "exceptions": exceptions[:3],
    }


def summarize(rows, variant):
    played = [r for r in rows if r["variant"] == variant and r.get("outcome")]
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
        "semantic_failures": sum(r.get("semantic_failures", 0) for r in played),
        "livestock_escapes": sum(r.get("variant_livestock_escapes", 0) for r in played),
        "errors": sum(1 for r in rows if r["variant"] == variant
                      and (r.get("runtime_error") or r.get("load_error"))),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()

    paths = build_variants()
    base = paths["shipped"]
    challengers = [name for name in paths if name != "shipped"]
    print(f"variants: {challengers}", flush=True)

    jobs = [(name, str(paths[name]), str(base), seed, seat)
            for name in challengers
            for seed in range(1, args.seeds + 1) for seat in (0, 1)]
    rows = []
    started = time.time()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_game, job) for job in jobs]
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            if len(rows) % 10 == 0 or len(rows) == len(jobs):
                print(f"  {len(rows)}/{len(jobs)}", flush=True)

    summaries = {name: summarize(rows, name) for name in challengers}
    summaries = {k: v for k, v in summaries.items() if v}
    data = {
        "schema_version": 1,
        "purpose": "value of each layer V43 ships disabled, against the shipped agent",
        "shipped_settings": SHIPPED,
        "seeds": args.seeds,
        "summaries": summaries,
        "elapsed_seconds": time.time() - started,
        "kaggle_submission_made": False,
        "games": rows,
    }
    args.output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    lines = ["# V43 layer ablation", "",
             f"Each variant is the shipped V43 with settings patched, against the shipped "
             f"agent itself, {args.seeds} seeds in both seats. A positive margin is that "
             f"change's value.", "",
             "| Variant | N | W/L/T | GSR | Mean margin | Median | Worst | Semantic fails | Escapes |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for name, s in sorted(summaries.items(), key=lambda kv: -kv[1]["mean_margin"]):
        lines.append(
            f"| {name} | {s['games']} | {s['wins']}/{s['losses']}/{s['ties']} | "
            f"{s['gsr']:.3f} | {s['mean_margin']:+,.0f} | {s['median_margin']:+,.0f} | "
            f"{s['worst_margin']:+,.0f} | {s['semantic_failures']} | {s['livestock_escapes']} |"
        )
    args.report.write_text("\n".join(lines) + "\n")
    print(args.output)
    print(json.dumps({k: {"gsr": v["gsr"], "mean_margin": round(v["mean_margin"])}
                      for k, v in summaries.items()}, indent=2))


if __name__ == "__main__":
    main()
