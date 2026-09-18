"""Where our agent now stands against the rank-16 fork, action by action.

Everything we concluded about Driz Lo was measured against the V43 tape, and we
no longer run V43: the chassis is alperen's and three layers sit on top. Before
spending more on studying that fork, the cheap check is whether our own play has
already moved towards it. Same counting as the fork analysis -- unit operations
and sell orders per game from step 144 -- so the columns are comparable.
"""
from __future__ import annotations
import argparse, gc, json, statistics, sys
from collections import Counter
from pathlib import Path
from kaggle_environments import make
from run_route_remap_pilot import load_agent

ROOT = Path(__file__).resolve().parent
VD = Path("/private/tmp/kaggriculture_v43_variants")
OPS = ("FERTILIZE", "FEED", "CARE", "WATER", "PASS", "HARVEST", "PICKUP", "COLLECT_FERTILIZER", "PLANT", "DIG")
ITEMS = ("MILK", "FERTILIZER", "WOOL", "STRAWBERRY", "WHEAT", "EGG", "CARROT", "MELON", "TOMATO")
# measured over Driz Lo's 58 games against V43-lineage opponents
DRIZ_OPS = {"FERTILIZE": 151.2, "FEED": 308.9, "CARE": 346.3, "WATER": 951.9, "PASS": 388.8,
            "HARVEST": 464.8, "PICKUP": 190.9, "COLLECT_FERTILIZER": 359.4}
DRIZ_SELL = {"MILK": 68.7, "FERTILIZER": 62.7, "WOOL": 60.0, "STRAWBERRY": 52.0, "WHEAT": 35.6,
             "EGG": 31.3, "CARROT": 24.6}


def signature(steps, seat):
    ops, sells = Counter(), Counter()
    for s in range(144, 719):
        a = steps[s + 1][seat].get("action") or {}
        for u in [a.get("farmer") or []] + list(a.get("hands") or []):
            if u:
                ops[u[0]] += 1
        for o in (a.get("market") or []):
            if o and o[0] == "SELL" and len(o) > 2 and int(o[2]) > 0:
                sells[o[1]] += 1
    return ops, sells


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--agent", default="alp_dw_416_fv_r30_qc_all")
    ap.add_argument("--opponent", default="alp")
    ap.add_argument("--seeds", default="4242,99,7")
    a = ap.parse_args()
    seeds = [int(x) for x in a.seeds.split(",")]
    ours_ops, ours_sells = Counter(), Counter()
    tape_ops, tape_sells = Counter(), Counter()
    for seed in seeds:
        v = load_agent(VD / f"{a.agent}.py", f"sg{seed}")
        o = load_agent(VD / "shipped.py", f"sgo{seed}")
        env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=False)
        env.run([v, o])
        co, cs = signature(env.steps, 0)
        to, ts = signature(env.steps, 1)
        ours_ops.update(co); ours_sells.update(cs); tape_ops.update(to); tape_sells.update(ts)
        for k in [k for k in sys.modules if k.startswith("remap_")]:
            sys.modules.pop(k, None)
        gc.collect()
    n = len(seeds)
    print(f"per game from step 144, {n} seeds; the fork column is its 58 games against lineage opponents\n")
    print(f"{'unit op':22s} {'V43 tape':>9s} {'ours now':>9s} {'Driz Lo':>9s} {'ours-tape':>10s} {'fork-tape':>10s}")
    for k in OPS:
        t, c, d = tape_ops[k] / n, ours_ops[k] / n, DRIZ_OPS.get(k)
        ds = f"{d:9.1f}" if d else " " * 9
        dd = f"{d - t:+10.1f}" if d else " " * 10
        print(f"{k:22s} {t:9.1f} {c:9.1f} {ds} {c - t:+10.1f} {dd}")
    print(f"\n{'sell orders':22s} {'V43 tape':>9s} {'ours now':>9s} {'Driz Lo':>9s} {'ours-tape':>10s} {'fork-tape':>10s}")
    for k in ITEMS:
        t, c, d = tape_sells[k] / n, ours_sells[k] / n, DRIZ_SELL.get(k)
        ds = f"{d:9.1f}" if d else " " * 9
        dd = f"{d - t:+10.1f}" if d else " " * 10
        print(f"{k:22s} {t:9.1f} {c:9.1f} {ds} {c - t:+10.1f} {dd}")
    same = [k for k in DRIZ_OPS if abs(ours_ops[k] / n - DRIZ_OPS[k]) < abs(tape_ops[k] / n - DRIZ_OPS[k])]
    print(f"\nunit ops where we are now closer to the fork than the tape is: {sorted(same)}")
    sames = [k for k in DRIZ_SELL if abs(ours_sells[k] / n - DRIZ_SELL[k]) < abs(tape_sells[k] / n - DRIZ_SELL[k])]
    print(f"sell orders where we are now closer: {sorted(sames)}")


if __name__ == "__main__":
    main()
