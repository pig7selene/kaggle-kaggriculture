"""Held-out confirmation for the remap pilot's largest gains.

The pilot chose each pair's best route on the same two seeds it scored it on.
Picking the maximum of 27 noisy means guarantees a positive "gain" even when
every route is identical in expectation, so the pilot's +432 median is a
ceiling, not an estimate -- the same in-sample trap the 0911 blacklist's +1782
fell into. Anything remapped on that evidence alone would be fitted to noise.

This replays only the hypotheses large enough to plausibly survive that bias:
the pairs whose pilot gain exceeded 2,000, on seeds the pilot never used (the
manifest's third seed onward), in both seats. For each pair it tests the
pilot's best route plus routes 124 and 110, which between them were best on 15
of 21 pilot pairs, so the question "is one route simply better than 105 here"
gets asked directly. Margin is against the room_plus_clamp baseline playing
V43's current assignment, exactly as in the pilot.

A gain that holds on unseen seeds earns a remap. One that collapses closes this
tier with a clean negative.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
import statistics
import time

from run_route_remap_pilot import build_forced_variants, run_game


ROOT = Path(__file__).resolve().parent
PILOT = ROOT / "experiments" / "route_remap_pilot.json"
SEEDS = ROOT / "experiments" / "seed_first_shops_manifest.json"
OUTPUT = ROOT / "experiments" / "route_remap_holdout.json"
REPORT = ROOT / "experiments" / "route_remap_holdout.md"
EXTRA_ROUTES = (124, 110)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", type=Path, default=PILOT,
                        help="pilot JSON to confirm; outputs are named after its stem")
    parser.add_argument("--select-on", choices=("gain", "best"), default="gain",
                        help="gain: gain_over_current (valid when the pilot's 'current' is what the "
                             "baseline really played); best: best_mean_margin against the baseline "
                             "directly (use when 'current' was mislabelled, as in the first Yarn run)")
    parser.add_argument("--min-pilot-gain", type=float, default=2000.0)
    parser.add_argument("--extra-routes", default="124,110",
                        help="routes tested on every selected pair in addition to its pilot best")
    parser.add_argument("--holdout-seeds", type=int, default=4)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()

    stem = args.pilot.stem.replace("route_remap_pilot", "route_remap_holdout")
    args.output = args.output or (ROOT / "experiments" / f"{stem}.json")
    args.report = args.report or (ROOT / "experiments" / f"{stem}.md")
    extra_routes = tuple(int(r) for r in args.extra_routes.split(",") if r.strip())

    pilot = json.loads(args.pilot.read_text())
    if pilot.get("smoke"):
        raise RuntimeError("pilot JSON is the smoke run; rerun the pilot first")
    seeds = json.loads(SEEDS.read_text())["by_pair"]
    metric = "gain_over_current" if args.select_on == "gain" else "best_mean_margin"
    targets = {pair: cell for pair, cell in pilot["cells"].items()
               if cell[metric] > args.min_pilot_gain}
    if not targets:
        raise RuntimeError(f"no pilot pair has {metric} above {args.min_pilot_gain}")

    plan, skipped = {}, {}
    for pair, cell in targets.items():
        held = seeds.get(pair, [])[2:2 + args.holdout_seeds]   # pilot used [:2]
        if len(held) < 2:
            skipped[pair] = f"only {len(held)} unseen seeds"
            continue
        routes = sorted({int(cell["best_route"]), *extra_routes})
        plan[pair] = {"seeds": held, "routes": routes,
                      "pilot_best": int(cell["best_route"]),
                      "pilot_gain": cell["gain_over_current"],
                      "pilot_by_route": cell["by_route"]}

    all_routes = sorted({r for p in plan.values() for r in p["routes"]})
    paths = build_forced_variants(all_routes)
    jobs = [(pair, r, str(paths[r]), seed, seat)
            for pair, p in plan.items() for seed in p["seeds"]
            for r in p["routes"] for seat in (0, 1)]
    print(f"pairs {len(plan)} skipped {len(skipped)} jobs {len(jobs)}", flush=True)

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
                if done % 20 == 0 or done == len(jobs):
                    print(f"  {done}/{len(jobs)}  {time.time() - started:.0f}s", flush=True)
    finally:
        pool.shutdown(wait=False, cancel_futures=True)

    played = [r for r in rows if "margin" in r]
    errors = [r for r in rows if "error" in r]
    by: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    for r in played:
        by[r["pair"]][r["route"]].append(r["margin"])

    cells = {}
    for pair, p in plan.items():
        holdout = {route: statistics.fmean(v) for route, v in by[pair].items()}
        best_h = holdout.get(p["pilot_best"])
        cells[pair] = {
            "pilot_best_route": p["pilot_best"],
            "pilot_gain": p["pilot_gain"],
            "holdout_gain_of_pilot_best": best_h,
            "shrinkage": (None if best_h is None else best_h / p["pilot_gain"]),
            "holdout_by_route": {str(k): v for k, v in sorted(holdout.items())},
            "holdout_seeds": p["seeds"],
            "games": sum(len(v) for v in by[pair].values()),
        }

    data = {
        "schema_version": 1,
        "purpose": "out-of-sample check of the remap pilot's largest gains",
        "pilot": str(args.pilot.relative_to(ROOT)) if args.pilot.is_relative_to(ROOT) else str(args.pilot),
        "selected_on": metric,
        "min_pilot_gain": args.min_pilot_gain,
        "extra_routes": list(extra_routes),
        "skipped": skipped,
        "games": len(rows), "errors": len(errors),
        "elapsed_seconds": time.time() - started,
        "cells": cells,
        "kaggle_submission_made": False,
    }
    args.output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    extra_cols = " | ".join(f"{r} held-out" for r in extra_routes)
    lines = [f"# Route remap held-out check ({args.pilot.stem})", "",
             f"Pairs whose pilot {metric} exceeded {args.min_pilot_gain:,.0f}, replayed on "
             f"seeds the pilot never used, both seats, against the baseline's actual play. "
             f"{len(played)} games, {len(errors)} errors.", "",
             f"| Pair | Pilot best | Pilot {metric} | Held-out margin of pilot best | Kept | {extra_cols} |",
             "| --- | ---: | ---: | ---: | ---: | " + " | ".join("---:" for _ in extra_routes) + " |"]
    for pair, c in sorted(cells.items(), key=lambda kv: -kv[1]["pilot_gain"]):
        h = c["holdout_by_route"]
        hg = c["holdout_gain_of_pilot_best"]
        extra_vals = " | ".join(
            f"{h[str(r)]:+,.0f}" if str(r) in h else "-" for r in extra_routes)
        lines.append(
            f"| {pair} | {c['pilot_best_route']} | {c['pilot_gain']:+,.0f} | "
            f"{(f'{hg:+,.0f}' if hg is not None else '-')} | "
            f"{(f'{c['shrinkage']:.0%}' if c['shrinkage'] is not None else '-')} | {extra_vals} |"
        )
    survivors = [p for p, c in cells.items()
                 if c["holdout_gain_of_pilot_best"] is not None
                 and c["holdout_gain_of_pilot_best"] > 0]
    lines += ["", f"Pilot-best route still positive on unseen seeds: {len(survivors)}/{len(cells)}."]
    for pair, why in skipped.items():
        lines.append(f"- skipped {pair}: {why}")
    args.report.write_text("\n".join(lines) + "\n")
    print(args.output)
    print(lines[-1 - len(skipped)])


if __name__ == "__main__":
    main()
