"""Same game, same farm: whose lots go out at the better price.

Our agent realises 0.47 of the game-average price on milk where the teams above
3,000 realise 0.87, but that could mean either that we time badly or simply that
we sell more and move the book ourselves. Comparing the two sides of one game
settles it: against an opponent whose opening matches the tape the production is
the same and the book is shared, so a systematic difference in realised price is
timing and nothing else.
"""
from __future__ import annotations
import argparse, json, runpy, statistics
from collections import defaultdict
from pathlib import Path
from analyze_v27_routes import normalized_action
from extract_lineage_frontier import field

ROOT = Path(__file__).resolve().parent
ROUTE0 = runpy.run_path("/private/tmp/kaggriculture_v43_variants/shipped.py", run_name="v43op")["_ROUTES"][0]
PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")


def realised(rep, seat):
    units, rev = defaultdict(int), defaultdict(int)
    for s in range(144, 719):
        pr = rep["steps"][s][0]["observation"]["market"]["prices"]
        shed = dict((rep["steps"][s][seat]["observation"].get("private") or {}).get("shed") or {})
        for o in (normalized_action(rep, seat, s).get("market") or []):
            if o and o[0] == "SELL" and len(o) >= 3 and o[1] in PRODUCTS and int(o[2]) > 0:
                fill = min(int(o[2]), int(shed.get(o[1], 0) or 0))
                if fill > 0:
                    units[o[1]] += fill
                    rev[o[1]] += fill * int(pr.get(o[1], 0) or 0)
    return units, rev


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--submissions", default="56330796,56325745,56322741")
    ap.add_argument("--limit", type=int, default=90)
    ap.add_argument("--min-agree", type=float, default=0.9)
    a = ap.parse_args()
    per = defaultdict(lambda: {"ours_u": [], "opp_u": [], "ours_p": [], "opp_p": [], "ratio": []})
    n = 0
    for sid in a.submissions.split(","):
        f = ROOT / "experiments" / f"online_{sid.strip()}_episodes_manifest.json"
        if not f.is_file():
            continue
        for e in json.loads(f.read_text())["episodes"]:
            if n >= a.limit:
                break
            p = Path(e["file"])
            if not p.is_file():
                continue
            rep = json.loads(p.read_text())
            if rep["info"]["TeamNames"][0] == rep["info"]["TeamNames"][1]:
                continue
            seat, opp = e["seat"], 1 - e["seat"]
            agree = sum(field(normalized_action(rep, opp, s)) == field(ROUTE0[s]) for s in range(144)) / 144
            if agree < a.min_agree:
                continue
            u1, r1 = realised(rep, seat)
            u2, r2 = realised(rep, opp)
            for prod in PRODUCTS:
                if u1[prod] and u2[prod]:
                    p1, p2 = r1[prod] / u1[prod], r2[prod] / u2[prod]
                    per[prod]["ours_u"].append(u1[prod]); per[prod]["opp_u"].append(u2[prod])
                    per[prod]["ours_p"].append(p1); per[prod]["opp_p"].append(p2)
                    per[prod]["ratio"].append(p1 / max(1, p2))
            n += 1
            del rep
    print(f"{n} mirror games (opponent's opening matches the tape)\n")
    print(f"{'product':12s} {'our units':>10s} {'their units':>12s} {'our price':>10s} {'their price':>12s} {'ratio':>7s} {'we win':>8s}")
    for prod in PRODUCTS:
        d = per[prod]
        if len(d["ratio"]) < 5:
            continue
        wins = sum(1 for x in d["ratio"] if x > 1.0)
        print(f"{prod:12s} {statistics.mean(d['ours_u']):10.0f} {statistics.mean(d['opp_u']):12.0f} "
              f"{statistics.mean(d['ours_p']):10.1f} {statistics.mean(d['opp_p']):12.1f} "
              f"{statistics.mean(d['ratio']):7.3f} {wins}/{len(d['ratio'])}")
    print("\nrevenue difference per game from price alone (our units at their price minus ours):")
    tot = 0
    for prod in PRODUCTS:
        d = per[prod]
        if len(d["ratio"]) < 5:
            continue
        gap = statistics.mean(u * (op - p) for u, p, op in zip(d["ours_u"], d["ours_p"], d["opp_p"]))
        tot += gap
        print(f"  {prod:12s} {gap:+9,.0f}")
    print(f"  {'total':12s} {tot:+9,.0f}")


if __name__ == "__main__":
    main()
