"""How much production does the V43 tape lose to the seed it was not recorded on?

The tape's farm actions were recorded against one seed's weeds. On another seed
a PLANT lands on a weed and `_weed_repair` digs first, replays the PLANT only if
the tape does not move away next step, and otherwise drops it -- the tile stays
empty until the tape happens to plant it again. Water arrives on the recorded
schedule regardless of what actually grows, so misaligned crops can dry out.
This counts, per seed, what those mechanisms cost: weeds dug, plants dropped,
crops that died unwatered, tiles empty per day, and harvest units.
"""
from __future__ import annotations
import argparse, gc, json, statistics, sys
from collections import Counter
from pathlib import Path
from kaggle_environments import make
from run_route_remap_pilot import load_agent

VD = Path("/private/tmp/kaggriculture_v43_variants")
CROP_UNITS = ("WHEAT", "CARROT", "MELON", "STRAWBERRY", "TOMATO")


def farm_stats(steps, seat):
    dig = failed_plant = died = 0
    empty_by_day, weed_by_day, plant_by_day = Counter(), Counter(), Counter()
    harvested = Counter()
    prev_tiles = None
    prev_inv = None
    for s in range(1, len(steps)):
        obs = steps[s][0]["observation"]
        farm = obs["farms"][seat]
        tiles = farm["tiles"]
        act = steps[s][seat].get("action") or {}
        units = [act.get("farmer") or ["PASS"]] + list(act.get("hands") or [])
        for u in units:
            if u and u[0] == "DIG":
                dig += 1
        day = (s - 1) // 24
        if s % 24 == 1:
            for row in tiles:
                for t in row:
                    if t is None:
                        empty_by_day[day] += 1
                    elif isinstance(t, dict) and t.get("kind") == "WEED":
                        weed_by_day[day] += 1
                    elif isinstance(t, dict) and t.get("kind") == "PLANT":
                        plant_by_day[day] += 1
        if prev_tiles is not None:
            for r, row in enumerate(tiles):
                for c, t in enumerate(row):
                    p = prev_tiles[r][c]
                    if isinstance(p, dict) and p.get("kind") == "PLANT" and t is None:
                        if p.get("crop") in ("STRAWBERRY", "TOMATO"):
                            died += 1          # ongoing crops never clear on harvest
                        else:
                            harvested[p.get("crop")] += 1   # harvest or death of a one-shot crop
        prev_tiles = tiles
    shed_final = steps[-1][0]["observation"]["farms"][seat]
    return {"dig": dig, "died_or_cleared_immature": died, "one_shot_cleared": dict(harvested),
            "empty_tiles_by_day": [empty_by_day[d] for d in range(30)],
            "weed_tiles_by_day": [weed_by_day[d] for d in range(30)],
            "plant_tiles_by_day": [plant_by_day[d] for d in range(30)],
            "money": steps[-1][seat]["reward"]}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seeds", default="4242,99,7,555,31337,2024")
    ap.add_argument("--variant", default="shipped")
    a = ap.parse_args()
    out = []
    for seed in [int(x) for x in a.seeds.split(",")]:
        v = load_agent(VD / f"{a.variant}.py", f"fl:{seed}"); o = load_agent(VD / "shipped.py", f"flo:{seed}")
        env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=False); env.run([v, o])
        st = farm_stats(env.steps, 0)
        st["seed"] = seed
        out.append(st)
        e = st["empty_tiles_by_day"]; w = st["weed_tiles_by_day"]; p = st["plant_tiles_by_day"]
        print(f"seed {seed:6d}: money {st['money']:>9,.0f} | digs {st['dig']:3d} | cleared-immature {st['died_or_cleared_immature']:3d} | "
              f"planted tiles d6/d12/d18/d24/d29 {p[6]}/{p[12]}/{p[18]}/{p[24]}/{p[29]} | weeds d6..d29 {w[6]}/{w[12]}/{w[18]}/{w[24]}/{w[29]} | empty {e[6]}/{e[12]}/{e[18]}/{e[24]}/{e[29]}", flush=True)
        for k in [k for k in sys.modules if k.startswith("remap_")]: sys.modules.pop(k, None)
        gc.collect()
    Path("experiments/tape_farm_loss.json").write_text(json.dumps(out, indent=1))
    ms = [x["money"] for x in out]
    print(f"\nmoney across seeds: mean {statistics.mean(ms):,.0f} min {min(ms):,.0f} max {max(ms):,.0f} spread {max(ms)-min(ms):,.0f}")
    print(f"digs mean {statistics.mean(x['dig'] for x in out):.1f} | cleared-immature mean {statistics.mean(x['died_or_cleared_immature'] for x in out):.1f}")


if __name__ == "__main__":
    main()
