"""The last day: what does a top agent extract that we do not?

Majkel1337 and V43 finish with nearly the same farm (59 vs 58 planted tiles,
10 vs 11 hands) but he ends about 13k richer, and most of that opens up in the
final day. This tabulates, for any set of replays and a named seat, the shed
at the start of the last day, the units and value sold during it, and the
money it produced, so ours and theirs can be laid side by side.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import statistics

from analyze_v27_routes import normalized_action

ROOT = Path(__file__).resolve().parent
PRODUCTS = ("CARROT", "EGG", "FERTILIZER", "MELON", "MILK", "STRAWBERRY", "TOMATO", "WHEAT", "WOOL")
PREM = ("WOOL", "MILK", "STRAWBERRY", "MELON")
BASEP = {"WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120, "MELON": 250,
         "EGG": 50, "MILK": 160, "WOOL": 200, "FERTILIZER": 100}
LAST = 648


def obs_of(rep, s, seat):
    o = dict(rep["steps"][s][seat]["observation"])
    for k in ("step", "day", "hour", "farms", "market", "town"):
        if k not in o:
            o[k] = rep["steps"][s][0]["observation"][k]
    return o


def profile(rep, seat):
    start = obs_of(rep, LAST, seat)
    shed0 = {k: int(v) for k, v in start["private"]["shed"].items() if k in PRODUCTS}
    carried0 = Counter()
    for inv in start["private"].get("inventories", []):
        for k, v in inv.items():
            if k in PRODUCTS:
                carried0[k] += int(v)
    money0 = start["farms"][seat]["money"]
    money1 = rep["steps"][-1][seat]["reward"]
    sold = Counter()
    value = 0.0
    prem_units = prem_value = 0.0
    by_step = Counter()
    for s in range(LAST, 719):
        o = obs_of(rep, s, seat)
        shed = dict(o["private"]["shed"])
        prices = o["market"]["prices"]
        for order in normalized_action(rep, seat, s).get("market") or []:
            if not (order and order[0] == "SELL" and len(order) > 2 and order[1] in PRODUCTS):
                continue
            q = min(int(order[2]), int(shed.get(order[1], 0)))
            if q <= 0:
                continue
            shed[order[1]] = int(shed.get(order[1], 0)) - q
            sold[order[1]] += q
            value += q * prices[order[1]]
            by_step[s] += q
            if order[1] in PREM:
                prem_units += q
                prem_value += q * prices[order[1]] / BASEP[order[1]]
    # harvests during the last day feed the sales too
    harvests = 0
    for s in range(LAST, 719):
        a = normalized_action(rep, seat, s)
        for u in [a.get("farmer")] + list(a.get("hands") or []):
            if isinstance(u, (list, tuple)) and u and u[0] in ("HARVEST", "COLLECT_FERTILIZER"):
                harvests += 1
    return {"money_648": money0, "money_end": money1, "last_day_gain": money1 - money0,
            "shed_648": sum(shed0.values()), "carried_648": sum(carried0.values()),
            "sold_units": sum(sold.values()), "sold_value": value,
            "prem_units": prem_units, "prem_index": (prem_value / prem_units) if prem_units else None,
            "harvest_actions": harvests, "steps_selling": len(by_step),
            "sold_by_item": dict(sold)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path)
    parser.add_argument("--manifest", type=Path, help="our own online episode manifest")
    parser.add_argument("--team", help="team name to profile (for --dir)")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    rows = []
    if args.dir:
        import pandas as pd
        man = pd.read_csv(args.dir / "manifest.csv").sort_values("avg_score", ascending=False)
        for _, m in man.iterrows():
            if len(rows) >= args.limit:
                break
            p = args.dir / f"{int(m.episode_id)}.json"
            if not p.is_file():
                continue
            rep = json.loads(p.read_text())
            names = rep["info"]["TeamNames"]
            if args.team not in names:
                continue
            rows.append(profile(rep, names.index(args.team)))
    else:
        man = json.loads(args.manifest.read_text())
        for e in man["episodes"]:
            if len(rows) >= args.limit:
                break
            if e.get("opp_team_name") == "pig7selene":
                continue
            rep = json.loads(Path(e["file"]).read_text())
            rows.append(profile(rep, e["seat"]))
    mean = lambda k: statistics.mean(r[k] for r in rows if r[k] is not None)
    items = Counter()
    for r in rows:
        items.update(r["sold_by_item"])
    print(f"{args.label}: n={len(rows)}")
    print(f"  money at 648 {mean('money_648'):9,.0f} -> end {mean('money_end'):9,.0f}  (last-day gain {mean('last_day_gain'):8,.0f})")
    print(f"  shed at 648 {mean('shed_648'):5.1f} units (+{mean('carried_648'):4.1f} carried) | sold in the last day {mean('sold_units'):6.1f} units worth {mean('sold_value'):8,.0f}")
    print(f"  premium sold {mean('prem_units'):5.1f} at index {mean('prem_index'):.2f} | harvest actions {mean('harvest_actions'):5.1f} | steps selling {mean('steps_selling'):4.1f}")
    print(f"  by item: {{{', '.join(f'{k}: {v / len(rows):.0f}' for k, v in items.most_common())}}}")


if __name__ == "__main__":
    main()
