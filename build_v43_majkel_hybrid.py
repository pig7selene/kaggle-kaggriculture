"""V43's chassis with Majkel's routes where we have them.

The layer ablation showed V43's switches are nearly exhausted: the two that pay
are worth about +440 of margin together and everything else is zero or negative,
which converts to roughly +37 of score at the ratio V43-over-our-0911 implies.
The leaderboard's fourth to fifteenth places sit 400 or more above that, so the
remaining upside is not in the chassis.

It is in the routes. V43 is a route-replay agent whose routes are plain data --
41 tapes of 719 actions in exactly the shape ``normalized_action`` already
produces -- and we hold 40 episodes of Majkel1337's actual play from the
submission that scored 3193. His production profile is nearly identical to ours
on tiles and hands, so the difference between 3167 and 2560 lives in what the
tape does, not in how much farm it runs.

Coverage is partial: those 40 episodes span 33 of the 64 first-two-shop pairs.
So this is a hybrid. A covered pair plays Majkel's whole recorded game; an
uncovered pair falls through to V43's own router untouched. That makes the
change strictly additive against the V43 baseline: on 31 of 64 pairs the two
agents are byte-identical in behaviour.

Where a pair has several Majkel episodes, the highest-money one is kept.

Sealed material is not touched: routes come only from the 40 development
episodes named in experiments/majkel_g1_split_lock.json.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import zlib

from analyze_v27_routes import normalized_action


ROOT = Path(__file__).resolve().parent
BASE = Path("/private/tmp/kaggriculture_pull_0915/out/"
            "kaggriculture-v43-recovering-lost-harvests/main.py")
CORPUS = Path("/private/tmp/kaggriculture_majkel_56156662")
MANIFEST = ROOT / "experiments" / "majkel_56156662_corpus_manifest.json"
OUTPUT = ROOT / "agents_build" / "v43_majkel_hybrid.py"
RECEIPT = ROOT / "experiments" / "v43_majkel_hybrid_build.json"
TEAM = "Majkel1337"
SETTINGS = {"hand_align": True, "weed_repair": True, "sell_lead": True,
            "budget_guard": False, "room_guard": True, "clamp_sells": True,
            "dead_stock": False, "terminal_liquidation": False, "front_run": False}

OVERLAY = '''

# ---------------------------------------------------------------- Majkel hybrid
# Routes recorded from Majkel1337's submission 56156662 (public score 3193 at
# capture). A first-two-shop pair present here plays his recorded game outright;
# anything else falls through to the router above, unchanged. V43's _R42_OPENING
# rewrite is deliberately not applied to these tapes: each is internally
# consistent with its own opening.
_MJ_DATA = json.loads(zlib.decompress(base64.b85decode(@@PAYLOAD@@)))
_MJ_BASE = max(_ROUTES) + 1
_MJ_SHOPS = {}
for _mj_i, _mj_entry in enumerate(_MJ_DATA):
    _ROUTES[_MJ_BASE + _mj_i] = _mj_entry["actions"]
    _MJ_SHOPS[tuple(_mj_entry["shops"])] = _MJ_BASE + _mj_i
del _mj_i, _mj_entry, _MJ_DATA

_MJ_PARENT_ROUTER = _router


def _router(observation, step, state):
    if step >= 144 and not state.get("mj_done"):
        shops = tuple((_get(_get(observation, "town", {}), "unlocked_shops", []) or [])[:2])
        state["mj_done"] = True
        if shops in _MJ_SHOPS:
            state["mj_route"] = _MJ_SHOPS[shops]
    if "mj_route" in state:
        return state["mj_route"]
    return _MJ_PARENT_ROUTER(observation, step, state)


_SETTINGS = @@SETTINGS@@
'''


def development_paths() -> list[Path]:
    manifest = json.loads(MANIFEST.read_text())
    sealed = set(manifest["seal_integrity"]["sealed_ids_declared"])
    paths = []
    for row in manifest["episodes"]:
        if row["sealed"] or row["episode_id"] in sealed:
            continue
        paths.append(Path(row["source_path"]) if "source_path" in row
                     else CORPUS / row["subset"] / row["replay_filename"])
    if {int(p.stem.split("-")[1]) for p in paths} & sealed:
        raise RuntimeError("sealed holdout episode entered the route bank")
    return [p for p in paths if p.is_file()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--receipt", type=Path, default=RECEIPT)
    args = parser.parse_args()

    best: dict[tuple, dict] = {}
    for path in development_paths():
        replay = json.loads(path.read_text())
        teams = list(replay["info"]["TeamNames"])
        if TEAM not in teams:
            continue
        seat = teams.index(TEAM)
        money = float(replay["steps"][-1][seat]["reward"])
        shops = tuple(replay["steps"][-1][seat]["observation"]["town"]["unlocked_shops"][:2])
        if shops in best and best[shops]["money"] >= money:
            continue
        best[shops] = {
            "shops": list(shops), "money": money,
            "episode_id": int(replay["info"].get("EpisodeId") or path.stem.split("-")[1]),
            "actions": [normalized_action(replay, seat, step) for step in range(719)],
        }
        print(f"  {path.name} {' + '.join(shops)} {money:,.0f}", flush=True)

    entries = [best[k] for k in sorted(best)]
    payload = base64.b85encode(zlib.compress(
        json.dumps(entries, separators=(",", ":")).encode(), 9)).decode()

    overlay = (OVERLAY.replace("@@PAYLOAD@@", repr(payload))
                      .replace("@@SETTINGS@@", repr(SETTINGS)))
    # V43's main.py is a 3,366-line overlay stack; the make_agent call near line
    # 968 is only its base. Appending at EOF leaves the real agent bound to the
    # original _IMPL while corrupting _ROUTES under the layers above it, which
    # scored 2,379 against 135,391. The route bank has to be in place before the
    # base is constructed, so the block is inserted immediately before that line.
    base_source = BASE.read_text()
    anchor = "_IMPL=make_agent(_ROUTES,router=_router,**_SETTINGS)"
    if base_source.count(anchor) != 1:
        raise RuntimeError(f"expected exactly one {anchor!r}, found {base_source.count(anchor)}")
    source = base_source.replace(anchor, overlay.strip() + "\n" + anchor, 1)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(source)

    receipt = {
        "purpose": "V43 chassis with Majkel routes on covered first-two-shop pairs",
        "chassis": "ahmedberatozer/kaggriculture-v43-recovering-lost-harvests (Apache-2.0)",
        "chassis_main_sha256": hashlib.sha256(BASE.read_bytes()).hexdigest(),
        "route_source": "Majkel1337 submission 56156662, 40 development episodes",
        "routes_added": len(entries),
        "pairs_covered": len(entries),
        "pairs_total": 64,
        "settings": SETTINGS,
        "sealed_g1_holdout_used": False,
        "covered_pairs": [
            {"shops": e["shops"], "episode_id": e["episode_id"], "final_money": e["money"]}
            for e in entries
        ],
        "output": str(args.output.relative_to(ROOT)),
        "output_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
        "output_bytes": args.output.stat().st_size,
        "kaggle_submission_made": False,
    }
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: v for k, v in receipt.items() if k != "covered_pairs"}, indent=2))


if __name__ == "__main__":
    main()
