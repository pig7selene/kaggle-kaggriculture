"""Pilot for re-mapping V43's shop pairs to better routes.

V43 assigns 64 first-two-shop pairs to only 27 of its 41 routes, and one route,
105, serves 21 pairs by itself. Majkel's own play varies twofold in final money
across shop pairs, so a single route for a third of the non-Yarn space is very
unlikely to be the best choice for all of them.

Re-mapping generates nothing. Every route is a tape V43 itself produced, all 41
share route 0's first 144 steps exactly, and the router only switches at step
144, so any assignment is as internally consistent as V43's own. The worst
outcome is the current mapping. Route-bank size is unchanged, so the memory
ceiling met by the 74-route hybrid does not apply.

The pilot measures every non-Yarn route on the pairs route 105 currently serves.
For each pair it uses seeds known (from the seed manifest) to produce that pair,
and plays a forced-route variant against the room_plus_clamp baseline, which on
that pair plays V43's current assignment. Margin is therefore "this route versus
what V43 picks today", which is exactly the quantity a remap acts on.

The forced route applies only in steps 144-647; the step-648 handover to route
2 is left as V43 has it, so both sides agree on the endgame. What the pilot has
to establish before any full run is whether the matrix has variance at all: if
routes score alike on a pair, remapping is worthless and the full 64x41 run is
not worth its four hours.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time

from kaggle_environments import make


ROOT = Path(__file__).resolve().parent
BASE = Path("/private/tmp/kaggriculture_v43_variants/room_plus_clamp.py")
VARIANTS = Path("/private/tmp/kaggriculture_v43_forced")
SEEDS = ROOT / "experiments" / "seed_first_shops_manifest.json"
ROUTEMAP = Path("/tmp/v43_routemap.json")
OUTPUT = ROOT / "experiments" / "route_remap_pilot.json"
REPORT = ROOT / "experiments" / "route_remap_pilot.md"
ANCHOR = "_IMPL=make_agent(_ROUTES,router=_router,**_SETTINGS)"

FORCED = '''
# Route remap probe: play route @@R@@ for steps 144-647 regardless of the shop
# lookup. The parent router still runs so its day-6/day-27 state is set exactly
# as in the baseline, and the step-648 handover is left untouched.
_FR_ROUTE = @@R@@
_FR_PARENT = _router


def _router(observation, step, state):
    chosen = _FR_PARENT(observation, step, state)
    if 144 <= step < 648:
        return _FR_ROUTE
    return chosen


'''


def build_forced_variants(routes) -> dict[int, Path]:
    source = BASE.read_text()
    if source.count(ANCHOR) != 1:
        raise RuntimeError(f"expected one anchor, found {source.count(ANCHOR)}")
    VARIANTS.mkdir(parents=True, exist_ok=True)
    paths = {}
    for route in routes:
        text = source.replace(ANCHOR, FORCED.replace("@@R@@", str(route)) + ANCHOR, 1)
        path = VARIANTS / f"forced_{route}.py"
        path.write_text(text)
        paths[route] = path
    return paths


def load_agent(path: Path, tag: str):
    import importlib.util
    name = "remap_" + hashlib.sha256(f"{path}:{tag}:{time.time_ns()}".encode()).hexdigest()[:24]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return getattr(module, "agent", None) or getattr(module, "kaggle_agent")


def run_game(job):
    pair, route, variant_path, seed, seat = job
    # Every load registers a fresh module in sys.modules, and a V43 module holds
    # 41 routes of 719 actions. Left registered, 2,268 games grew each worker to
    # over 600 MB and thrashed the machine into a hang. Unregister and collect
    # after every game; the serial hybrid A/B already did this and it should
    # have been carried over.
    loaded = [n for n in sys.modules if n.startswith("remap_")]
    try:
        forced = load_agent(Path(variant_path), f"{route}:{seed}:{seat}")
        base = load_agent(BASE, f"base:{seed}:{seat}")
        players = [None, None]
        players[seat] = forced
        players[1 - seat] = base
        env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=False)
        env.run(players)
        if len(env.steps) != 720:
            return {"pair": pair, "route": route, "seed": seed, "seat": seat, "error": "incomplete"}
        final = env.steps[-1]
        mine = float(final[seat].reward)
        theirs = float(final[1 - seat].reward)
        shops = list(final[seat].observation["town"]["unlocked_shops"])[:2]
        return {"pair": pair, "route": route, "seed": seed, "seat": seat,
                "margin": mine - theirs, "money": mine,
                "shops_seen": " + ".join(shops),
                "statuses": [str(final[i].status) for i in range(2)]}
    except Exception as exc:
        return {"pair": pair, "route": route, "seed": seed, "seat": seat, "error": repr(exc)[:160]}
    finally:
        for name in [n for n in sys.modules if n.startswith("remap_") and n not in loaded]:
            sys.modules.pop(name, None)
        import gc
        gc.collect()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds-per-pair", type=int, default=2)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--smoke", action="store_true",
                        help="one game per route on seed 1, to check every forced variant runs")
    parser.add_argument("--side", choices=("nonyarn", "yarn"), default="nonyarn",
                        help="nonyarn: the 27 routes on the 21 pairs route 105 serves; "
                             "yarn: the 12 routes on the 49 pairs route 0 serves")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()

    # The Yarn side is the same experiment on V43's other router branch: route 0
    # serves 49 of the 64 Yarn pairs and was never measured. Keys come from the
    # routemap JSON, outputs get a side suffix so the two pilots never collide.
    keys = {"nonyarn": ("nonyarn_routes", "shop_routes", "pairs_105", 105),
            "yarn": ("yarn_routes", "yarn_shop_routes", "pairs_0", 0)}[args.side]
    suffix = "" if args.side == "nonyarn" else "_yarn"
    output = args.output or OUTPUT.with_name(OUTPUT.stem + suffix + OUTPUT.suffix)
    report = args.report or REPORT.with_name(REPORT.stem + suffix + REPORT.suffix)
    args.output, args.report = output, report

    routemap = json.loads(ROUTEMAP.read_text())
    routes = [int(r) for r in routemap[keys[0]]]
    workhorse = keys[3]
    paths = build_forced_variants(routes)

    # What the baseline actually plays on a pair is decided by V43's router, not
    # by whichever map we happen to be probing: pairs whose first two shops
    # include YARN_STORE use _R110_OLD_SHOPS, every other pair uses
    # _R108_SHOP_ROUTES. The first Yarn run took _R110_OLD_SHOPS at face value
    # as "the 49 pairs route 0 serves"; most of those are non-Yarn pairs the
    # router never sends to that map, so the baseline was playing route 105's
    # family and the "current" margin was not zero. Resolve per pair.
    def effective_current(pair: str):
        table = routemap["yarn_shop_routes"] if "YARN_STORE" in pair else routemap["shop_routes"]
        return table.get(pair)

    current: dict[str, int | None] = {}
    if args.smoke:
        jobs = [("smoke", r, str(paths[r]), 1, 0) for r in routes]
    else:
        seeds = json.loads(SEEDS.read_text())["by_pair"]
        if args.side == "yarn":
            # The router consults _R110_OLD_SHOPS only for pairs containing
            # YARN_STORE; its 49 route-0 rows are dead entries from an older
            # version and route 0 is never chosen at step 144 for any pair. The
            # real Yarn side is the 15 YARN_STORE pairs, spread over 11 routes.
            targets = [p for p in routemap["yarn_shop_routes"] if "YARN_STORE" in p]
        else:
            targets = [" + ".join(p) for p in routemap[keys[2]]]
        current = {pair: effective_current(pair) for pair in targets}
        missing = [t for t in targets if len(seeds.get(t, [])) < args.seeds_per_pair]
        if missing:
            raise RuntimeError(f"not enough seeds for {len(missing)} pairs: {missing[:5]}")
        jobs = [(pair, r, str(paths[r]), seed, seat)
                for pair in targets
                for seed in seeds[pair][:args.seeds_per_pair]
                for r in routes for seat in (0, 1)]

    # Two lessons from the first full run, which finished all 2,268 games and
    # then hung: the machine was thrashing (parent swapped to under 1 MB RSS,
    # workers in uninterruptible I/O), and every result lived only in the
    # parent's memory. So each row is appended to a JSONL checkpoint the moment
    # it arrives, and the pool is released without waiting for workers to die
    # once every future has returned -- their exit is not needed for the
    # results, and blocking on it is what stranded 74 minutes of compute.
    checkpoint = args.output.with_suffix(".rows.jsonl")
    rows, started = [], time.time()
    pool = ProcessPoolExecutor(max_workers=args.workers)
    try:
        futures = [pool.submit(run_game, j) for j in jobs]
        with checkpoint.open("w") as sink:
            for done, future in enumerate(as_completed(futures), 1):
                row = future.result()
                rows.append(row)
                sink.write(json.dumps(row) + "\n")
                sink.flush()
                if done % 50 == 0 or done == len(jobs):
                    print(f"  {done}/{len(jobs)}  {time.time() - started:.0f}s", flush=True)
    finally:
        pool.shutdown(wait=False, cancel_futures=True)

    errors = [r for r in rows if "error" in r]
    played = [r for r in rows if "margin" in r]
    matrix: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    for r in played:
        matrix[r["pair"]][r["route"]].append(r["margin"])

    cells = {}
    for pair, by_route in matrix.items():
        means = {route: statistics.fmean(v) for route, v in by_route.items()}
        best = max(means, key=lambda route: means[route])
        cur = current.get(pair)
        cur_margin = means.get(cur) if cur is not None else None
        cells[pair] = {
            "current_route": cur,
            "current_mean_margin": cur_margin,
            "best_route": best,
            "best_mean_margin": means[best],
            "worst_mean_margin": min(means.values()),
            "spread": means[best] - min(means.values()),
            # Only meaningful when `current` is what the baseline really played;
            # otherwise best_mean_margin (against the baseline directly) is the
            # number to read, and the holdout script's --select-on best uses it.
            "gain_over_current": means[best] - (cur_margin if cur_margin is not None else 0.0),
            "by_route": {str(k): v for k, v in sorted(means.items())},
        }

    data = {
        "schema_version": 1,
        "smoke": args.smoke,
        "routes_tested": routes,
        "pairs_tested": sorted(cells),
        "games": len(rows), "errors": len(errors),
        "elapsed_seconds": time.time() - started,
        "cells": cells,
        "error_rows": errors[:20],
        "kaggle_submission_made": False,
    }
    args.output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    if args.smoke:
        print(f"smoke: {len(played)} ran, {len(errors)} errors")
        for r in errors[:5]:
            print("  ", r)
        return

    lines = [f"# Route remap pilot ({args.side})", "",
             f"{len(routes)} {args.side} routes on the {len(cells)} pairs route {workhorse} serves, "
             f"{args.seeds_per_pair} seeds per pair, both seats; {len(played)} games, "
             f"{len(errors)} errors. Margin is the forced route against V43's current "
             f"assignment for that pair.", "",
             "| Pair | Current | Cur. margin | Best | Best margin | Spread | Gain |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for pair, c in sorted(cells.items(), key=lambda kv: -kv[1]["gain_over_current"]):
        cur = c["current_mean_margin"]
        lines.append(
            f"| {pair} | {c['current_route']} | {cur:+,.0f} | {c['best_route']} | "
            f"{c['best_mean_margin']:+,.0f} | {c['spread']:,.0f} | {c['gain_over_current']:+,.0f} |"
        )
    gains = [c["gain_over_current"] for c in cells.values()]
    spreads = [c["spread"] for c in cells.values()]
    lines += ["", f"Median spread across routes within a pair: {statistics.median(spreads):,.0f}. "
                  f"Median gain of best route over current: {statistics.median(gains):+,.0f}. "
                  f"Pairs where a different route beats the current one: "
                  f"{sum(1 for g in gains if g > 0)}/{len(gains)}."]
    args.report.write_text("\n".join(lines) + "\n")
    print(args.output)
    print(lines[-1])


if __name__ == "__main__":
    main()
