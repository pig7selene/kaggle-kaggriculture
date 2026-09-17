"""Graft a strong fork's post-144 play into V43's route bank.

Three teams in the top 34 -- Driz Lo (rank 15), Thomas Tschinkel (23) and
Catalyst (34) -- play V43's opening tape byte for byte through step 143 and
then something of their own: their field actions agree with shipped V43 on only
0.35 to 0.79 of steps 144-718, and the less they agree the higher they rank.

Because the opening is shared, their tail is a drop-in route. V43's router
returns route 0 until step 144 and only then picks by the first two shops, so
an injected route's own steps 0-143 are never read; splicing route 0's opening
onto a fork's steps 144-718 gives a route the chassis can replay with all its
reactive layers -- which is what the Majkel graft could not have, his opening
being his own.

A pair with no recorded tail falls through to V43's router untouched.
"""

from __future__ import annotations

import argparse
import base64
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import runpy
import zlib

import pandas as pd

from analyze_v27_routes import normalized_action
from extract_lineage_frontier import field

ROOT = Path(__file__).resolve().parent
BASE = Path("/private/tmp/kaggriculture_v43_variants/room_plus_clamp.py")
ANCHOR = "_IMPL=make_agent(_ROUTES,router=_router,**_SETTINGS)"

OVERLAY = '''

# ---------------------------------------------------------------- fork tails
# Post-144 play recorded from V43-lineage teams in the top 34 of the board.
# Their opening is this tape's own opening, so only steps 144-718 are taken;
# steps 0-143 are route 0's and are never read anyway, the router switching at
# 144. A first-two-shop pair with no recorded tail keeps V43's own route.
_FT_DATA = json.loads(zlib.decompress(base64.b85decode(@@PAYLOAD@@)))
_FT_OPENING = _ROUTES[0][:144]
_FT_BASE = max(_ROUTES) + 1
_FT_SHOPS = {}
for _ft_i, _ft_entry in enumerate(_FT_DATA):
    _ROUTES[_FT_BASE + _ft_i] = _FT_OPENING + _ft_entry["tail"]
    _FT_SHOPS[tuple(_ft_entry["shops"])] = _FT_BASE + _ft_i
del _ft_i, _ft_entry, _FT_DATA

_FT_PARENT_ROUTER = _router


def _router(observation, step, state):
    if step >= 144 and not state.get("ft_done"):
        shops = tuple((_get(_get(observation, "town", {}), "unlocked_shops", []) or [])[:2])
        state["ft_done"] = True
        if shops in _FT_SHOPS:
            state["ft_route"] = _FT_SHOPS[shops]
    if "ft_route" in state:
        return state["ft_route"]
    return _FT_PARENT_ROUTER(observation, step, state)


'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dirs", default="/private/tmp/kaggriculture_daily_0916")
    parser.add_argument("--teams", default="Driz Lo,Thomas Tschinkel,Catalyst,mikelou1")
    parser.add_argument("--base", type=Path, default=BASE)
    parser.add_argument("--output", type=Path, default=Path("/private/tmp/kaggriculture_v43_variants/fork_tails.py"))
    parser.add_argument("--receipt", type=Path, default=ROOT / "experiments" / "v43_fork_tails_build.json")
    parser.add_argument("--min-opening-agreement", type=float, default=0.98)
    args = parser.parse_args()
    teams = [t for t in args.teams.split(",") if t]
    route0 = runpy.run_path(str(args.base), run_name="v43base")["_ROUTES"][0]

    best: dict[tuple, dict] = {}
    rejected = defaultdict(int)
    for d in args.dirs.split(","):
        d = Path(d)
        man = pd.read_csv(d / "manifest.csv")
        for _, m in man.iterrows():
            p = d / f"{int(m.episode_id)}.json"
            if not p.is_file():
                continue
            rep = json.loads(p.read_text())
            names = rep["info"]["TeamNames"]
            for seat, team in enumerate(names):
                if team not in teams:
                    continue
                acts = [normalized_action(rep, seat, s) for s in range(719)]
                agree = sum(field(acts[s]) == field(route0[s]) for s in range(144)) / 144
                if agree < args.min_opening_agreement:
                    rejected[team] += 1
                    continue
                shops = tuple(rep["steps"][-1][seat]["observation"]["town"]["unlocked_shops"][:2])
                margin = rep["rewards"][seat] - rep["rewards"][1 - seat]
                if shops in best and best[shops]["margin"] >= margin:
                    continue
                best[shops] = {"shops": list(shops), "team": team, "margin": margin,
                               "money": rep["rewards"][seat], "episode_id": int(m.episode_id),
                               "opening_agreement": round(agree, 3),
                               "tail": acts[144:719]}
    entries = [best[k] for k in sorted(best)]
    print(f"{len(entries)} pairs covered; rejected for a different opening: {dict(rejected)}")
    for e in entries:
        print(f"  {'+'.join(e['shops']):34s} {e['team'][:18]:18s} ep {e['episode_id']} margin {e['margin']:+9,.0f} money {e['money']:9,.0f}")
    payload = base64.b85encode(zlib.compress(
        json.dumps([{"shops": e["shops"], "tail": e["tail"]} for e in entries], separators=(",", ":")).encode(), 9)).decode()
    source = args.base.read_text()
    if source.count(ANCHOR) != 1:
        raise RuntimeError("anchor not found exactly once")
    args.output.write_text(source.replace(ANCHOR, OVERLAY.replace("@@PAYLOAD@@", repr(payload)).strip() + "\n" + ANCHOR, 1))
    receipt = {"base": str(args.base), "teams": teams, "pairs_covered": len(entries), "pairs_total": 64,
               "entries": [{k: v for k, v in e.items() if k != "tail"} for e in entries],
               "output": str(args.output), "output_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
               "output_bytes": args.output.stat().st_size}
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"wrote {args.output} ({receipt['output_bytes']:,} bytes)")


if __name__ == "__main__":
    main()
