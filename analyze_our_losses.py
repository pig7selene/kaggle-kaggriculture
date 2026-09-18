"""Why we lose the games we lose, product by product.

Both sides' money is start plus sales minus spending, and every cost is known,
so a loss decomposes exactly: did they out-earn us, or did we overspend? For
each episode this also reports whether the opponent shares our opening (the
public lineage) and where the two money curves separate.
"""
from __future__ import annotations
import argparse, json, runpy, statistics
from collections import Counter
from pathlib import Path
from analyze_v27_routes import normalized_action
from extract_lineage_frontier import field

ROOT = Path(__file__).resolve().parent
SHIPPED = Path("/private/tmp/kaggriculture_v43_variants/shipped.py")
ROUTE0 = runpy.run_path(str(SHIPPED), run_name="v43_open")["_ROUTES"][0]
SEED_COST = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
ANIMAL_COST = {"GOOSE": 300, "COW": 400, "SHEEP": 500}
LAND = [1000, 2000, 4000]
FIB = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987]
PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")


def flows(rep, seat):
    spend = Counter()
    lands = 0
    sells = Counter()
    for s in range(719):
        a = normalized_action(rep, seat, s)
        obs = rep["steps"][s][0]["observation"]
        prices = obs["market"]["prices"]
        hires_today = int(obs["farms"][seat].get("hires_today", 0) or 0)
        n_hire = 0
        for o in (a.get("market") or []):
            if not o:
                continue
            if o[0] == "HIRE":
                spend["hire"] += FIB[min(hires_today + n_hire, len(FIB) - 1)]
                n_hire += 1
            elif o[0] == "BUY_LAND":
                spend["land"] += LAND[min(lands, 2)]
                lands += 1
            elif o[0] == "BUY_SEED" and len(o) >= 3:
                spend["seed"] += SEED_COST.get(o[1], 0) * max(0, int(o[2]))
            elif o[0] == "BUY_ANIMAL" and len(o) >= 3:
                spend["animal"] += ANIMAL_COST.get(o[1], 0) * max(0, int(o[2]))
            elif o[0] == "BUY_PRODUCT" and len(o) >= 3:
                spend[f"buy_{o[1]}"] += int(prices.get(o[1], 0) or 0) * max(0, int(o[2]))
            elif o[0] == "SELL" and len(o) >= 3 and int(o[2]) > 0:
                sells[o[1]] += 1
    start = float(rep["steps"][0][0]["observation"]["farms"][seat]["money"])
    end = float(rep["steps"][-1][seat]["reward"] or 0)
    ts = sum(spend.values())
    return spend, ts, end - start + ts, end, sells


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--submission", required=True)
    ap.add_argument("--losses-only", action="store_true")
    ap.add_argument("--min-opp-score", type=float, default=0.0)
    a = ap.parse_args()
    man = json.loads((ROOT / "experiments" / f"online_{a.submission}_episodes_manifest.json").read_text())
    for e in man["episodes"]:
        if a.losses_only and e["result"] != "L":
            continue
        if (e.get("opp_score") or 0) < a.min_opp_score:
            continue
        rep = json.loads(Path(e["file"]).read_text())
        seat, opp = e["seat"], 1 - e["seat"]
        agree = sum(field(normalized_action(rep, opp, s)) == field(ROUTE0[s]) for s in range(144)) / 144
        sp, ts, sales, end, sells = flows(rep, seat)
        osp, ots, osales, oend, osells = flows(rep, opp)
        print(f"\n=== vs {e.get('opp_team_name')} ({e.get('opp_score') or 0:,.0f}) {e['result']} margin {end-oend:+,.0f} "
              f"| их opening matches the public tape {agree:.0%} ===")
        print(f"  money   {end:>9,.0f} vs {oend:>9,.0f} | sales {sales:>9,.0f} vs {osales:>9,.0f} | spend {ts:>8,.0f} vs {ots:>8,.0f}")
        keys = sorted(set(sp) | set(osp), key=lambda k: -abs(sp[k] - osp[k]))
        print("  spending: " + ", ".join(f"{k} {sp[k]:,.0f}/{osp[k]:,.0f}" for k in keys[:5]))
        print("  sell orders: " + ", ".join(f"{k} {sells[k]}/{osells[k]}" for k in PRODUCTS if sells[k] or osells[k]))
        curve = []
        for s in (144, 288, 432, 576, 700):
            f = rep["steps"][s][0]["observation"]["farms"]
            curve.append(f"s{s} {f[seat]['money']-f[opp]['money']:+,.0f}")
        print("  money gap: " + " | ".join(curve))


if __name__ == "__main__":
    main()
