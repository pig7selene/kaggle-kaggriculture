"""Do the strong V43 forks adapt to the town where shipped cannot?

Shipped's money runs from 49k to 177k by town: PET_CAFE and BAKERY towns want
carrots, eggs and wheat, and V43's wool, milk and strawberries fetch nothing
there. The forks that sit at ranks 15-34 keep V43's opening and replace the
tail. If their edge is town adaptation it shows in the same replay: their crop
and animal mix, planted tiles and money against the opponent's, town by town.
"""
from __future__ import annotations
import json, runpy, statistics
from collections import Counter
from pathlib import Path
from analyze_v27_routes import normalized_action
from extract_lineage_frontier import field

D = Path("/private/tmp/kaggriculture_daily_0916")
SHIPPED = Path("/private/tmp/kaggriculture_v43_variants/shipped.py")
route0 = runpy.run_path(str(SHIPPED), run_name="v43ship")["_ROUTES"][0]


def mix(farm):
    crops, animals, kinds = Counter(), Counter(), Counter()
    for row in farm["tiles"]:
        for t in row:
            if isinstance(t, dict):
                kinds[t.get("kind")] += 1
                if t.get("kind") == "PLANT":
                    crops[t.get("crop")] += 1
                if t.get("animal"):
                    animals[t.get("animal")] += 1
            elif t is None:
                kinds["empty"] += 1
    return crops, animals, kinds


def opening_agree(rep, seat):
    return sum(field(normalized_action(rep, seat, s)) == field(route0[s]) for s in range(144)) / 144


rows = json.load(open("experiments/strong_forks_0916.rows.json"))
for r in rows:
    p = D / f"{r['episode_id']}.json"
    if not p.is_file():
        continue
    rep = json.loads(p.read_text())
    names = rep["info"]["TeamNames"]
    seat = names.index(r["team"]) if r["team"] in names else 0
    opp = 1 - seat
    town = rep["steps"][600][0]["observation"]["town"]["unlocked_shops"]
    fm = rep["steps"][500][0]["observation"]["farms"]
    mc, ma, mk = mix(fm[seat]); oc, oa, ok = mix(fm[opp])
    print(f"\n{r['team']} vs {names[opp]} | ep {r['episode_id']} | town {'+'.join(town)}")
    print(f"  money {r['money']:>9,.0f} vs {r['opp_money']:>9,.0f} (margin {r['money']-r['opp_money']:+,.0f}) | opp opening agrees with V43 {opening_agree(rep, opp):.0%}")
    print(f"  step 500 crops   me {dict(mc)} | opp {dict(oc)}")
    print(f"  step 500 animals me {dict(ma)} | opp {dict(oa)}")
    print(f"  step 500 tiles   me {dict(mk)} | opp {dict(ok)}")
