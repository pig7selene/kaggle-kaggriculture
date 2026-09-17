"""Every 9/16 replay: who has V43's farm, who adapts, and what the gap is.

For each game record both sides' agreement with V43's opening, the town, final
money, and the crop, animal and tile mix at step 500. The rows let us ask, by
town class, how much a town-adapted farm earns over V43's fixed one.
"""
from __future__ import annotations
import json, runpy, sys
from collections import Counter
from pathlib import Path
from analyze_v27_routes import normalized_action
from extract_lineage_frontier import field

D = Path("/private/tmp/kaggriculture_daily_0916")
route0 = runpy.run_path(str(Path("/private/tmp/kaggriculture_v43_variants/shipped.py")), run_name="v43ship")["_ROUTES"][0]


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
    return dict(crops), dict(animals), dict(kinds)


rows = []
files = sorted(D.glob("*.json"))
for i, p in enumerate(files):
    if p.name == "manifest.csv":
        continue
    try:
        rep = json.loads(p.read_text())
    except Exception:
        continue
    if len(rep.get("steps", [])) < 700:
        continue
    names = rep["info"]["TeamNames"]
    town = rep["steps"][600][0]["observation"]["town"]["unlocked_shops"]
    farms = rep["steps"][500][0]["observation"]["farms"]
    quads = [len(f.get("unlocked_quadrants", [])) for f in farms]
    r = {"episode_id": int(p.stem), "town": town, "teams": names,
         "money": [rep["steps"][-1][s]["reward"] or 0 for s in range(2)],
         "agree": [sum(field(normalized_action(rep, s, t)) == field(route0[t]) for t in range(144)) / 144 for s in range(2)],
         "quads": quads, "mix": [mix(farms[s]) for s in range(2)]}
    rows.append(r)
    if i % 50 == 0:
        print(f"{i}/{len(files)}", flush=True)
Path("experiments/farm_gap_0916.rows.json").write_text(json.dumps(rows) + "\n")
print("rows", len(rows))
