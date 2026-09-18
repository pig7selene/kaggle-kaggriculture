"""What the top teams decide, tagged by the town they were dealt.

Trajectories do not transfer -- copying one team's recorded play lost 124 of 128
games -- but rules do, and a rule shows up as a decision that moves with the
town. One pass over a daily dataset records, per team and game: the herd it
ends with, the crop mix, how much land it buys and when, hands per day, and how
it splits its sell orders, all against the town's shop counts. Aggregated by
town type, a systematic difference from our own chassis is a candidate rule.
"""
from __future__ import annotations
import argparse, json, statistics
from collections import Counter, defaultdict
from pathlib import Path
from analyze_v27_routes import normalized_action

ROOT = Path(__file__).resolve().parent
SHOPS = ("BAKERY", "PIZZA_SHOP", "BRUNCH_SPOT", "YARN_STORE", "ICE_CREAM_SHOP",
         "PET_CAFE", "SMOOTHIE_SHOP", "FARMERS_MARKET")
LAND = [1000, 2000, 4000]


def structure(rep, seat):
    obs700 = rep["steps"][700][0]["observation"]
    farm = obs700["farms"][seat]
    town = Counter(obs700["town"]["unlocked_shops"])
    herd, crops, kinds = Counter(), Counter(), Counter()
    for row in farm["tiles"]:
        for t in row:
            if isinstance(t, dict):
                kinds[t.get("kind")] += 1
                if t.get("animal"):
                    herd[t["animal"]] += 1
                if t.get("kind") == "PLANT":
                    crops[t.get("crop")] += 1
            elif t is None:
                kinds["empty"] += 1
    lands, land_steps, hires_by_day, sells, spend = 0, [], Counter(), Counter(), 0
    for s in range(719):
        a = normalized_action(rep, seat, s)
        for o in (a.get("market") or []):
            if not o:
                continue
            if o[0] == "BUY_LAND":
                spend += LAND[min(lands, 2)]
                lands += 1
                land_steps.append(s)
            elif o[0] == "HIRE":
                hires_by_day[s // 24] += 1
            elif o[0] == "SELL" and len(o) >= 3 and int(o[2]) > 0:
                sells[o[1]] += 1
    return {"money": rep["steps"][-1][seat]["reward"] or 0,
            "town": {k: town.get(k, 0) for k in SHOPS},
            "yarn": town.get("YARN_STORE", 0),
            "herd": dict(herd), "crops": dict(crops), "kinds": dict(kinds),
            "quads": len(farm["unlocked_quadrants"]),
            "lands": lands, "land_steps": land_steps, "land_spend": spend,
            "hires_total": sum(hires_by_day.values()),
            "hires_late": sum(v for d, v in hires_by_day.items() if d >= 20),
            "sells": dict(sells)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", type=Path, default=Path("/private/tmp/kaggriculture_daily_0917"))
    ap.add_argument("--teams", default="")
    ap.add_argument("--limit", type=int, default=650)
    ap.add_argument("--out", type=Path, default=ROOT / "experiments" / "top_structures_0917.json")
    a = ap.parse_args()
    want = set(t.strip() for t in a.teams.split(",") if t.strip())
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
            if want and names[s] not in want:
                continue
            try:
                r = structure(rep, s)
            except Exception:
                continue
            r["team"] = names[s]
            r["episode"] = p.stem
            rows.append(r)
        if n % 100 == 0:
            print(f"  {n} replays", flush=True)
    a.out.write_text(json.dumps(rows) + "\n")
    print(f"{len(rows)} team-games from {n} replays -> {a.out}")


if __name__ == "__main__":
    main()
