"""The same selling statistics for our own agent, as a baseline.

The 9/17 dataset holds only top teams, so the lineage column in the extraction
is one game and useless. Running our own agent locally and applying the same
definitions gives a real comparison: units, the price realised against the
product's average over the game, when the lots go out, and how much stock is
allowed to pile up.
"""
from __future__ import annotations
import argparse, gc, json, statistics, sys
from collections import Counter, defaultdict
from pathlib import Path
from kaggle_environments import make
from run_route_remap_pilot import load_agent

ROOT = Path(__file__).resolve().parent
VD = Path("/private/tmp/kaggriculture_v43_variants")
PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")


def behaviour(steps, seat):
    prices_seen = defaultdict(list)
    for s in range(144, 719, 6):
        pr = steps[s][0]["observation"]["market"]["prices"]
        for p in PRODUCTS:
            prices_seen[p].append(int(pr.get(p, 0) or 0))
    avg = {p: (statistics.mean(v) if v else 1) for p, v in prices_seen.items()}
    orders = defaultdict(list)
    peak = Counter()
    for s in range(144, 719):
        obs = steps[s][0]["observation"]
        pr = obs["market"]["prices"]
        shed = dict(steps[s][seat]["observation"].get("private", {}).get("shed") or {})
        for p, q in shed.items():
            if p in PRODUCTS:
                peak[p] = max(peak[p], int(q or 0))
        a = steps[s + 1][seat].get("action") or {}
        for o in (a.get("market") or []):
            if o and o[0] == "SELL" and len(o) >= 3 and o[1] in PRODUCTS and int(o[2]) > 0:
                fill = min(int(o[2]), int(shed.get(o[1], 0) or 0))
                if fill > 0:
                    orders[o[1]].append((s, fill, int(pr.get(o[1], 0) or 0)))
    out = {}
    for p in PRODUCTS:
        v = orders[p]
        if not v:
            continue
        units = sum(q for _, q, _ in v)
        rev = sum(q * pz for _, q, pz in v)
        out[p] = {"units": units, "revenue": rev, "realised": rev / units,
                  "vs_average": (rev / units) / max(1, avg[p]),
                  "late_share": sum(q for s, q, _ in v if s >= 672) / units,
                  "mean_day": statistics.mean(s // 24 for s, _, _ in v),
                  "peak_shed": peak[p], "orders": len(v)}
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--agent", default="alp_dw_416_fv_r30_qc_all")
    ap.add_argument("--opponent", default="alp")
    ap.add_argument("--seeds", default="4242,99,7,555,31337,2024")
    a = ap.parse_args()
    acc = defaultdict(lambda: defaultdict(list))
    for seed in [int(x) for x in a.seeds.split(",")]:
        v = load_agent(VD / f"{a.agent}.py", f"mb{seed}")
        o = load_agent(VD / f"{a.opponent}.py", f"mbo{seed}")
        env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=False)
        env.run([v, o])
        for p, d in behaviour(env.steps, 0).items():
            for k, val in d.items():
                acc[p][k].append(val)
        for k in [k for k in sys.modules if k.startswith("remap_")]:
            sys.modules.pop(k, None)
        gc.collect()
    out = {p: {k: statistics.mean(v) for k, v in d.items()} for p, d in acc.items()}
    (ROOT / "experiments" / "our_market_behaviour.json").write_text(json.dumps(out, indent=1) + "\n")
    print(f"{'product':12s} {'units':>7s} {'realised/avg':>13s} {'mean day':>9s} {'last-2d':>8s} {'peak shed':>10s} {'orders':>7s}")
    for p in PRODUCTS:
        if p not in out:
            continue
        d = out[p]
        print(f"{p:12s} {d['units']:7.0f} {d['vs_average']:13.2f} {d['mean_day']:9.1f} {d['late_share']:8.0%} {d['peak_shed']:10.0f} {d['orders']:7.0f}")


if __name__ == "__main__":
    main()
