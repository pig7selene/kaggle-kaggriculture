"""Where and what do the lineage forks sell that the base would not?

For a sample of lineage-opponent episodes, run the base counterfactual on the
opponent's seat and tabulate its extra SELL orders (actual minus base) by hour
of day and by product, plus the quantities. Also estimate, for both seats, the
units destroyed at each end of day: shed after the hour-71 market plus every
unit's carried inventory, minus what the shed holds at the next day's first
step, when that sum exceeds the capacity.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gc
import json
from pathlib import Path
import runpy
import statistics
import sys

from analyze_v27_routes import normalized_action
from extract_lineage_frontier import field
from run_route_remap_pilot import BASE, load_agent

ROOT = Path(__file__).resolve().parent
PRODUCTS = ("CARROT", "EGG", "FERTILIZER", "MELON", "MILK", "STRAWBERRY", "TOMATO", "WHEAT", "WOOL")


def full_obs(rep, s, seat):
    obs = dict(rep["steps"][s][seat]["observation"])
    for key in ("step", "day", "hour", "farms", "market", "town"):
        if key not in obs:
            obs[key] = rep["steps"][s][0]["observation"][key]
    return obs


def base_actions(rep, seat, tag):
    agent = load_agent(BASE, tag)
    acts = []
    for s in range(719):
        try:
            acts.append(agent(full_obs(rep, s, seat), rep.get("configuration")))
        except Exception:
            acts.append({"farmer": ["PASS"], "hands": [], "market": []})
    for k in [k for k in sys.modules if k.startswith("remap_")]:
        sys.modules.pop(k, None)
    gc.collect()
    return acts


def sells(a):
    out = defaultdict(int)
    for o in a.get("market") or []:
        if o and o[0] == "SELL" and len(o) >= 3:
            out[o[1]] += max(0, int(o[2]))
    return out


def destroyed_per_day(rep, seat):
    out = []
    for d in range(1, 10):
        t = 72 * d - 1
        obs = full_obs(rep, t, seat)
        shed = obs["private"]["shed"]
        carried = sum(int(n) for inv in obs["private"].get("inventories", []) for n in inv.values())
        prod_shed = sum(int(shed.get(p, 0)) for p in PRODUCTS)
        animals = sum(int(v) for k, v in shed.items() if k not in PRODUCTS)
        # our fills at hour 71 (shed-capped orders)
        a = normalized_action(rep, seat, t)
        left = dict(shed)
        fills = 0
        for o in a.get("market") or []:
            if o and o[0] == "SELL" and len(o) >= 3:
                q = min(max(0, int(o[2])), int(left.get(o[1], 0)))
                left[o[1]] = int(left.get(o[1], 0)) - q
                fills += q
        after = full_obs(rep, t + 1, seat)["private"]["shed"]
        after_total = sum(int(v) for v in after.values())
        before_total = prod_shed + animals - fills + carried
        out.append(max(0, before_total - after_total) if before_total > 100 else 0)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submission", type=int, required=True)
    parser.add_argument("--sample", type=int, default=30)
    args = parser.parse_args()
    manifest = json.loads((ROOT / "experiments" / f"online_{args.submission}_episodes_manifest.json").read_text())
    route0 = runpy.run_path(str(BASE), run_name="v43base")["_ROUTES"][0]
    hour_hist, prod_hist, qty_hist = Counter(), Counter(), Counter()
    extra_by_hour_prem = Counter()
    ours_destroyed, theirs_destroyed = [], []
    n = 0
    for e in manifest["episodes"]:
        if e.get("opp_team_name") == "pig7selene":
            continue
        rep = json.loads(Path(e["file"]).read_text())
        seat, opp = e["seat"], 1 - e["seat"]
        if sum(field(normalized_action(rep, opp, s)) == field(route0[s]) for s in range(144)) / 144 < 0.9:
            continue
        acts = base_actions(rep, opp, f"dt:{e['episode_id']}")
        for s in range(144, 719):
            a, b = sells(normalized_action(rep, opp, s)), sells(acts[s])
            for item in set(a) | set(b):
                d = a[item] - b[item]
                if d > 0:
                    hour_hist[s % 72] += 1
                    prod_hist[item] += 1
                    qty_hist["1000+" if d >= 1000 else "100-999" if d >= 100 else "10-99" if d >= 10 else "1-9"] += 1
                    if item in ("WOOL", "MILK", "STRAWBERRY", "MELON"):
                        extra_by_hour_prem[s % 72] += 1
        ours_destroyed.append(destroyed_per_day(rep, seat))
        theirs_destroyed.append(destroyed_per_day(rep, opp))
        n += 1
        if n >= args.sample:
            break
    lines = [f"# Lineage forks' extra SELL orders vs the base (sample of {n} episodes, submission {args.submission})", "",
             "## By hour of day (orders per game)", "",
             ", ".join(f"h{h}: {c / n:.1f}" for h, c in sorted(hour_hist.items(), key=lambda kv: -kv[1])[:15]), "",
             "## By product (orders per game)", "",
             ", ".join(f"{p}: {c / n:.1f}" for p, c in prod_hist.most_common()), "",
             "## Extra quantity size", "", ", ".join(f"{k}: {c / n:.1f}" for k, c in qty_hist.most_common()), "",
             "## Premium extra orders by hour", "",
             ", ".join(f"h{h}: {c / n:.1f}" for h, c in sorted(extra_by_hour_prem.items(), key=lambda kv: -kv[1])[:10]), "",
             "## Estimated units destroyed at end of day (per day, mean over games)", "",
             "| day | ours | theirs |", "|---:|---:|---:|"]
    for d in range(9):
        lines.append(f"| {d + 1} | {statistics.mean(x[d] for x in ours_destroyed):.1f} | {statistics.mean(x[d] for x in theirs_destroyed):.1f} |")
    lines.append(f"| total | {statistics.mean(sum(x) for x in ours_destroyed):.1f} | {statistics.mean(sum(x) for x in theirs_destroyed):.1f} |")
    text = "\n".join(lines) + "\n"
    (ROOT / "experiments" / f"online_{args.submission}_fork_dump_timing.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
