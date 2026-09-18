"""Which public agent, if any, farms the way the top of the board farms.

The teams above 3,000 grow 13 to 16 carrot tiles and almost no strawberry; every
public build we have extracted so far grows 33 strawberry and no carrot, because
they are all forks of one lineage. If a second public lineage exists with the
top teams' farm, it would be worth more than anything we can graft ourselves.
This plays each extracted agent one game and reports its crop and herd mix.
"""
from __future__ import annotations
import argparse, gc, json, sys, traceback
from collections import Counter
from pathlib import Path
from kaggle_environments import make
from run_route_remap_pilot import load_agent

ROOT = Path(__file__).resolve().parent
VD = Path("/private/tmp/kaggriculture_v43_variants")


def mix(farm):
    c = Counter()
    for row in farm["tiles"]:
        for t in row:
            if isinstance(t, dict):
                if t.get("kind") == "PLANT":
                    c[t.get("crop")] += 1
                if t.get("animal"):
                    c[t["animal"]] += 1
    return c


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=4242)
    ap.add_argument("--glob", default="pub_*.py")
    a = ap.parse_args()
    rows = []
    print(f"{'agent':42s} {'wheat':>6s} {'straw':>6s} {'carrot':>7s} {'tom':>4s} {'cow':>4s} {'sheep':>6s} {'goose':>6s} | {'vs V43':>8s}")
    print(f"{'-- top teams (target) --':42s} {'10-25':>6s} {'0.7-6':>6s} {'13-16':>7s} {'0-6':>4s} {'5-9':>4s} {'0-11':>6s} {'0-5':>6s} |")
    for p in sorted(VD.glob(a.glob)):
        tag = p.stem[4:] if p.stem.startswith("pub_") else p.stem
        try:
            v = load_agent(p, f"sig{abs(hash(tag)) % 99999}")
            o = load_agent(VD / "shipped.py", f"sigo{abs(hash(tag)) % 99999}")
            env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": a.seed}, debug=False)
            env.run([v, o])
            c = mix(env.steps[500][0]["observation"]["farms"][0])
            m = env.steps[-1][0]["reward"] - env.steps[-1][1]["reward"]
            print(f"{tag[:42]:42s} {c['WHEAT']:6d} {c['STRAWBERRY']:6d} {c['CARROT']:7d} {c['TOMATO']:4d} "
                  f"{c['COW']:4d} {c['SHEEP']:6d} {c['GOOSE']:6d} | {m:+8,.0f}", flush=True)
            rows.append({"agent": tag, "mix": dict(c), "margin_vs_v43": m})
        except Exception as exc:
            print(f"{tag[:42]:42s} FAILED {type(exc).__name__}: {str(exc)[:46]}", flush=True)
        for k in [k for k in sys.modules if k.startswith("remap_")]:
            sys.modules.pop(k, None)
        gc.collect()
    (ROOT / "experiments" / "public_farm_signatures.json").write_text(json.dumps(rows, indent=1) + "\n")


if __name__ == "__main__":
    main()
