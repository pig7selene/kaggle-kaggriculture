"""Where a fork's margin over a lineage opponent actually comes from.

Driz Lo beats V43-lineage opponents by +3,828 a game where our lead manages
+2,440. Both run the same tape on the same farm in the same town, so the margin
has to appear in the market: either more units sold, or the same units sold at
better prices, or fewer units sold into a crashed book. This totals, per
product, both sides' filled quantity and revenue -- fills taken from the shed
each side actually held -- and splits the gap into a volume part and a price
part.
"""
from __future__ import annotations
import argparse, json, statistics
from collections import Counter, defaultdict
from pathlib import Path
from analyze_v27_routes import normalized_action

ROOT = Path(__file__).resolve().parent
PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")


SEED_COST = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
ANIMAL_COST = {"GOOSE": 300, "COW": 400, "SHEEP": 500}
LAND = [1000, 2000, 4000]
FIB = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987]


def flows(rep, seat):
    """Exact spending from the orders, and sales revenue backed out of the money.

    Money is the ground truth: end = start + sales - spending, and every cost is
    known (seed and animal prices are fixed, land is 1000/2000/4000, the nth hire
    of a day is the nth Fibonacci number, a bought product costs the board price).
    Counting fills from the shed instead undercounts, because the tape drops
    goods into the shed in the same step it sells them.
    """
    spend = Counter()
    lands = 0
    for s in range(719):
        a = normalized_action(rep, seat, s)
        obs = rep["steps"][s][0]["observation"]
        prices = obs["market"]["prices"]
        farm = obs["farms"][seat]
        hires_today = int(farm.get("hires_today", 0) or 0)
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
    start = float(rep["steps"][0][0]["observation"]["farms"][seat]["money"])
    end = float(rep["steps"][-1][seat]["reward"] or 0)
    total_spend = sum(spend.values())
    return spend, total_spend, end - start + total_spend, end


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--edits", type=Path, required=True, help="fork_<id>_edits.json")
    ap.add_argument("--dir", type=Path, required=True, help="directory of that submission's replays")
    ap.add_argument("--limit", type=int, default=40)
    a = ap.parse_args()
    rows = [r for r in json.loads(a.edits.read_text()) if r.get("opp_lineage")]
    agg = {0: Counter(), 1: Counter()}
    tot = {0: Counter(), 1: Counter()}
    n = 0
    margins = []
    per_game = []
    for r in rows[: a.limit]:
        cand = list(a.dir.glob(f"*{r['episode']}*.json"))
        if not cand:
            continue
        rep = json.loads(cand[0].read_text())
        names = rep["info"]["TeamNames"]
        if names[0] == names[1]:
            continue                      # Kaggle's own validation episode is self-play
        seat = names.index(r["team"]) if r["team"] in names else 0
        for who, sl in ((0, seat), (1, 1 - seat)):
            spend, ts, sales, end = flows(rep, sl)
            agg[who].update(spend)
            tot[who]["spend"] += ts
            tot[who]["sales"] += sales
            tot[who]["money"] += end
        margins.append(r["money"] - r["opp_money"])
        per_game.append((flows(rep, seat)[1], flows(rep, 1 - seat)[1],
                         flows(rep, seat)[0].get("buy_WHEAT", 0), flows(rep, 1 - seat)[0].get("buy_WHEAT", 0),
                         r["money"] - r["opp_money"]))
        n += 1
        if n % 10 == 0:
            print(f"  {n} games", flush=True)
    if not n:
        print("no games matched")
        return
    print(f"\n{rows[0]['team']} vs lineage opponents, {n} games, mean margin {statistics.mean(margins):+,.0f}")
    print("| item | fork | opponent | difference |")
    print("|---|---:|---:|---:|")
    print(f"| final money | {tot[0]['money']/n:,.0f} | {tot[1]['money']/n:,.0f} | {(tot[0]['money']-tot[1]['money'])/n:+,.0f} |")
    print(f"| sales revenue | {tot[0]['sales']/n:,.0f} | {tot[1]['sales']/n:,.0f} | {(tot[0]['sales']-tot[1]['sales'])/n:+,.0f} |")
    print(f"| total spending | {tot[0]['spend']/n:,.0f} | {tot[1]['spend']/n:,.0f} | {(tot[0]['spend']-tot[1]['spend'])/n:+,.0f} |")
    keys = sorted(set(agg[0]) | set(agg[1]), key=lambda k: -(abs(agg[0][k] - agg[1][k])))
    for k in keys:
        print(f"|   {k} | {agg[0][k]/n:,.0f} | {agg[1][k]/n:,.0f} | {(agg[0][k]-agg[1][k])/n:+,.0f} |")
    fw = sorted(x[2] for x in per_game); ow = sorted(x[3] for x in per_game)
    print(f"\nwheat purchases per game -- fork: median {statistics.median(fw):,.0f} max {max(fw):,.0f} | "
          f"opponent: median {statistics.median(ow):,.0f} max {max(ow):,.0f}")
    print(f"total spending per game -- fork: median {statistics.median(x[0] for x in per_game):,.0f} | "
          f"opponent: median {statistics.median(x[1] for x in per_game):,.0f}")
    print(f"margin: median {statistics.median(x[4] for x in per_game):+,.0f}")
    big = [x for x in per_game if x[3] > 20000]
    print(f"games where the opponent spent over 20k on wheat: {len(big)} of {len(per_game)}"
          + (f" (their margins {[f'{x[4]:+,.0f}' for x in big[:6]]})" if big else ""))


if __name__ == "__main__":
    main()
