"""At the step where an online opponent departs from local shipped V43, what does it do?

Re-simulates the online game locally (same seed and seats, 1.32.7 market
curves, our submitted bytes against local shipped), then compares the online
opponent's actions with local shipped's step by step from 144: prints the first
divergences, the raw route in our bank that best matches each side's field
actions over 144-647, and the shop draw. A different best route means the
opponent runs a different route bank or router (another notebook version); the
same route with market differences means a changed market layer.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import runpy

from kaggle_environments import make

from analyze_v27_routes import normalized_action
from extract_lineage_frontier import field
from run_route_remap_pilot import load_agent
import resimulate_online_games as R

ROOT = Path(__file__).resolve().parent


def best_route(routes, acts, lo=144, hi=648):
    scored = sorted(((sum(field(acts[s]) == field(routes[r][s]) for s in range(lo, hi)) / (hi - lo), r)
                     for r in routes if len(routes[r]) >= hi), reverse=True)
    return scored[:3]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submission", type=int, required=True)
    parser.add_argument("--episode", type=int, action="append", required=True)
    parser.add_argument("--agent", type=Path, default=Path("agents/v43_room_clamp_adapt5/main.py"))
    args = parser.parse_args()
    manifest = {e["episode_id"]: e for e in json.loads((ROOT / "experiments" / f"online_{args.submission}_episodes_manifest.json").read_text())["episodes"]}
    ns = runpy.run_path(str(R.SHIPPED), run_name="v43ship")
    routes, non_yarn, yarn = ns["_ROUTES"], ns["_R108_SHOP_ROUTES"], ns["_R110_OLD_SHOPS"]
    R.patch_engine("1.32.7")
    for eid in args.episode:
        e = manifest[eid]
        rep = json.loads(Path(e["file"]).read_text())
        seed, seat, opp = rep["info"].get("seed"), e["seat"], 1 - e["seat"]
        env, margin = R.play(args.agent, R.SHIPPED, seed, seat, f"insp:{eid}")
        shops_on = tuple(rep["steps"][-1][0]["observation"]["town"]["unlocked_shops"][:2])
        shops_loc = tuple(env.steps[-1][0]["observation"]["town"]["unlocked_shops"][:2])
        online_opp = [normalized_action(rep, opp, s) for s in range(719)]
        local_opp = [env.steps[s + 1][opp]["action"] if isinstance(env.steps[s + 1][opp].get("action"), dict) else {} for s in range(719)]
        print(f"\n=== episode {eid} vs {e.get('opp_team_name')} (rating {e.get('opp_score') and round(e['opp_score'])}) seed {seed} seat {seat}")
        print(f"online margin {(e['our_reward'] or 0) - (e['opp_reward'] or 0):+,.0f} | local margin {margin:+,.0f} | shops online {shops_on} local {shops_loc} | "
              f"router would pick {yarn.get(shops_on, 0) if 'YARN_STORE' in shops_on else non_yarn.get(shops_on, 100)}")
        print("best raw route for ONLINE opponent field 144-647:", best_route(routes, online_opp))
        print("best raw route for LOCAL shipped field 144-647:  ", best_route(routes, local_opp))
        n = 0
        for s in range(144, 719):
            fo, fl = field(online_opp[s]), field(local_opp[s])
            mo = [list(o) for o in (online_opp[s].get("market") or []) if o]
            ml = [list(o) for o in (local_opp[s].get("market") or []) if o]
            if fo != fl or mo != ml:
                print(f"  step {s}: online field {fo[:4]}... market {mo[:4]}")
                print(f"           local  field {fl[:4]}... market {ml[:4]}")
                n += 1
                if n >= 4:
                    break
        agree = sum(field(online_opp[s]) == field(local_opp[s]) for s in range(144, 719)) / 575
        magree = sum([list(o) for o in (online_opp[s].get("market") or []) if o] == [list(o) for o in (local_opp[s].get("market") or []) if o] for s in range(144, 719)) / 575
        print(f"  online-vs-local opponent agreement 144-718: field {agree:.2f} market {magree:.2f}")
    R.patch_engine("1.32.6")


if __name__ == "__main__":
    main()
