"""How the top of the board sells, in terms that transfer.

Their farms do not transfer -- copying one cost 124 of 128 games -- but market
rules do: every gain we have made came from changing what we sell and when.
What we have never extracted is how the teams above 3,000 actually trade. They
sell into the same book we do, so "when do they sell, how much, and at what
point on the price curve" is directly comparable whatever they grow.

Per team and product this records the timing profile by day, the price at the
moment each lot is posted relative to that product's average over the game, how
much stock they let accumulate, and what share goes out in the last two days.
A team that consistently posts into prices above the game average is timing
better, and the rule behind it is implementable regardless of its farm.
"""
from __future__ import annotations
import argparse, gc, json, statistics
from collections import Counter, defaultdict
from pathlib import Path
from analyze_v27_routes import normalized_action

ROOT = Path(__file__).resolve().parent
PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")


def behaviour(rep, seat):
    """Sell orders with the price and inventory they were posted into."""
    prices_seen = defaultdict(list)
    for s in range(144, 719, 6):
        pr = rep["steps"][s][0]["observation"]["market"]["prices"]
        for p in PRODUCTS:
            prices_seen[p].append(int(pr.get(p, 0) or 0))
    avg = {p: (statistics.mean(v) if v else 1) for p, v in prices_seen.items()}

    orders = defaultdict(list)          # product -> [(step, qty, price, inventory)]
    shed_peak = Counter()
    for s in range(144, 719):
        obs = rep["steps"][s][0]["observation"]
        pr = obs["market"]["prices"]
        inv = obs["market"].get("inventory") or {}
        priv = rep["steps"][s][seat]["observation"].get("private") or {}
        shed = dict(priv.get("shed") or {})
        for p, q in shed.items():
            if p in PRODUCTS:
                shed_peak[p] = max(shed_peak[p], int(q or 0))
        a = normalized_action(rep, seat, s)
        for o in (a.get("market") or []):
            if o and o[0] == "SELL" and len(o) >= 3 and o[1] in PRODUCTS and int(o[2]) > 0:
                fill = min(int(o[2]), int(shed.get(o[1], 0) or 0))
                if fill > 0:
                    orders[o[1]].append((s, fill, int(pr.get(o[1], 0) or 0), int(inv.get(o[1], 10000))))
    out = {}
    for p in PRODUCTS:
        v = orders[p]
        if not v:
            continue
        units = sum(q for _, q, _, _ in v)
        rev = sum(q * pz for _, q, pz, _ in v)
        late = sum(q for s, q, _, _ in v if s >= 672)          # last two days
        first_half = sum(q for s, q, _, _ in v if s < 432)
        out[p] = {"units": units, "revenue": rev,
                  "realised": rev / units,
                  "vs_average": (rev / units) / max(1, avg[p]),
                  "late_share": late / units,
                  "early_share": first_half / units,
                  "orders": len(v),
                  "peak_shed": shed_peak[p],
                  "mean_day": statistics.mean(s // 24 for s, _, _, _ in v)}
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", type=Path, default=Path("/private/tmp/kaggriculture_daily_0917"))
    ap.add_argument("--limit", type=int, default=650)
    ap.add_argument("--out", type=Path, default=ROOT / "experiments" / "market_behaviour_0917.json")
    a = ap.parse_args()
    rows = []
    n = 0
    for p in sorted(a.dir.glob("*.json")):
        if n >= a.limit:
            break
        try:
            rep = json.loads(p.read_text())
        except Exception:
            continue
        if len(rep.get("steps", [])) < 700:
            continue
        names = rep["info"]["TeamNames"]
        n += 1
        for s in range(2):
            try:
                b = behaviour(rep, s)
            except Exception:
                continue
            rows.append({"team": names[s], "episode": p.stem,
                         "money": rep["steps"][-1][s]["reward"] or 0, "products": b})
        del rep
        if n % 50 == 0:
            print(f"  {n} replays", flush=True)
            gc.collect()
    a.out.write_text(json.dumps(rows) + "\n")
    print(f"{len(rows)} team-games from {n} replays -> {a.out}")


if __name__ == "__main__":
    main()
