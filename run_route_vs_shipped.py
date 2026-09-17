"""Which route wins against the pool, not against a clone of ourselves?

Every route experiment so far played our variant against another copy of our
own chassis, so both sides produced the same goods and crashed the same prices.
The online pool is shipped V43 on its own router. Against it, a route that
produces a different mix sells into a market the opponent is not flooding --
the premium price index in V43-vs-V43 games is 0.6 of base, while the top teams
trade at 1.0. This forces each candidate route for steps 144-647 and plays it
against shipped V43, which routes itself, on seeds known to produce the pair.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import gc
import json
from pathlib import Path
import statistics
import sys
import time

from kaggle_environments import make

from analyze_v27_routes import normalized_action
from run_route_remap_pilot import BASE, build_forced_variants, load_agent

ROOT = Path(__file__).resolve().parent
SHIPPED = Path("/private/tmp/kaggriculture_v43_variants/shipped.py")
SEEDS = ROOT / "experiments" / "seed_first_shops_manifest.json"
PREM = ("WOOL", "MILK", "STRAWBERRY", "MELON")
BASEP = {"WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120, "MELON": 250,
         "EGG": 50, "MILK": 160, "WOOL": 200, "FERTILIZER": 100}


def premium_index(env, seat):
    units = value = 0.0
    for s in range(144, 719):
        obs = env.steps[s][seat]["observation"]
        shed = dict(obs["private"]["shed"])
        prices = env.steps[s][0]["observation"]["market"]["prices"]
        act = env.steps[s + 1][seat].get("action") if s + 1 < len(env.steps) else None
        for o in (act or {}).get("market") or []:
            if o and o[0] == "SELL" and len(o) > 2 and o[1] in PREM:
                q = min(int(o[2]), int(shed.get(o[1], 0)))
                shed[o[1]] = int(shed.get(o[1], 0)) - q
                units += q
                value += q * prices[o[1]] / BASEP[o[1]]
    return units, (value / units if units else None)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--routes", required=True, help="comma-separated route ids, or 'all'")
    parser.add_argument("--pairs", type=int, default=8, help="every k-th pair of the seed manifest")
    parser.add_argument("--pair-offset", type=int, default=0)
    parser.add_argument("--seed-slice", default="0:1")
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    import runpy
    routes = (sorted(runpy.run_path(str(BASE), run_name="v43base")["_ROUTES"])
              if args.routes == "all" else [int(r) for r in args.routes.split(",")])
    paths = build_forced_variants(routes)
    lo, hi = (int(x) for x in args.seed_slice.split(":"))
    by_pair = json.loads(SEEDS.read_text())["by_pair"]
    pairs = sorted(by_pair)[args.pair_offset::args.pairs]
    out = ROOT / "experiments" / f"route_vs_shipped_{args.name}.rows.jsonl"
    done = set()
    if out.exists():
        for line in out.read_text().splitlines():
            r = json.loads(line)
            done.add((r["pair"], r["route"], r["seed"], r["seat"]))
    jobs = [(pair, r, seed, seat) for pair in pairs for seed in by_pair[pair][lo:hi]
            for r in routes for seat in (0, 1)]
    print(f"{args.name}: {len(pairs)} pairs x {len(routes)} routes x {hi - lo} seeds x 2 seats = {len(jobs)} games "
          f"({len(done)} done)", flush=True)
    with out.open("a") as fh:
        for i, (pair, route, seed, seat) in enumerate(jobs):
            if (pair, route, seed, seat) in done:
                continue
            tag = f"{time.time_ns()}"
            v = load_agent(paths[route], f"fr:{tag}")
            b = load_agent(SHIPPED, f"sh:{tag}")
            env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=False)
            env.run([v, b] if seat == 0 else [b, v])
            last = env.steps[-1]
            row = {"pair": pair, "route": route, "seed": seed, "seat": seat, "steps": len(env.steps),
                   "ours": last[seat]["reward"], "theirs": last[1 - seat]["reward"]}
            if len(env.steps) == 720 and row["ours"] is not None and row["theirs"] is not None:
                row["margin"] = float(row["ours"]) - float(row["theirs"])
                u, idx = premium_index(env, seat)
                row["prem_units"], row["prem_index"] = u, idx
            else:
                row["error"] = "incomplete"
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            for k in [k for k in sys.modules if k.startswith("remap_")]:
                sys.modules.pop(k, None)
            gc.collect()
            if (i + 1) % 10 == 0:
                print(f"  {i + 1}/{len(jobs)}", flush=True)
    rows = [json.loads(l) for l in out.read_text().splitlines() if '"margin"' in l]
    by_route = defaultdict(list)
    for r in rows:
        by_route[r["route"]].append(r)
    print(f"\n| route | n | W/L | mean margin | median | our money | premium units | premium index |")
    print("|---|---:|---|---:|---:|---:|---:|---:|")
    for route, sub in sorted(by_route.items(), key=lambda kv: -statistics.mean(x["margin"] for x in kv[1])):
        m = [x["margin"] for x in sub]
        idx = [x["prem_index"] for x in sub if x.get("prem_index")]
        print(f"| {route} | {len(sub)} | {sum(x > 0 for x in m)}/{sum(x < 0 for x in m)} | {statistics.mean(m):+,.0f} | "
              f"{statistics.median(m):+,.0f} | {statistics.mean(x['ours'] for x in sub):,.0f} | "
              f"{statistics.mean(x['prem_units'] for x in sub):.0f} | {statistics.mean(idx) if idx else 0:.2f} |")


if __name__ == "__main__":
    main()
