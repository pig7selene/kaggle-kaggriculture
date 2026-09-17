"""Majkel1337's plan, executed by chasing its state instead of repeating its actions.

Two facts make this possible, both measured today. His farm at step 144 is the
same in every game -- 100 of 100 tiles identical across eight episodes, same
hand count, same quadrant, money within 90 -- even though his opening *actions*
agree with each other on only 29% of steps, because the order of the tasks
varies while the result does not. And a recorded trajectory can be executed
faithfully by chasing the state it was in rather than replaying its actions:
walk a unit back to the tile the recording had it on, buy the hands, seeds,
animals and land it owned at that step when the money allows, dig a weed
sitting where it wanted to plant, and size sell orders to the stock we actually
hold. That ladder took his own game from 4,194 (raw replay) to 120,848, 104% of
what he made himself.

So the agent is V43's architecture with his plan inside: one canonical opening
to step 143, then a tail chosen by the first two shops, each tail recorded in a
game that drew those shops. Pairs he never played fall back to the tail of the
pair that shares the most shops.
"""

from __future__ import annotations

import argparse
import base64
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import zlib

import pandas as pd

from analyze_v27_routes import normalized_action

ROOT = Path(__file__).resolve().parent
OPEN_END = 144
LAST = 719

AGENT = '''"""Majkel1337's plan under a state-chasing replayer. Generated; do not edit."""
import base64, json, zlib

_MJ = json.loads(zlib.decompress(base64.b85decode(@@PAYLOAD@@)))
_OPENING = _MJ["opening"]          # steps 0-143: actions, positions, targets
_TAILS = {tuple(k.split("|")): v for k, v in _MJ["tails"].items()}
_ORDER = _MJ["shop_order"]
_CFG = @@CFG@@
OPEN_END = @@OPEN_END@@
_STATE = {}
_TELEMETRY = {"steps": 0, "corrected": 0, "hire": 0, "land": 0, "seed": 0, "animal": 0,
              "dug": 0, "no_tail": 0, "errors": 0, "route": None}
_PRODUCTS = ("CARROT", "EGG", "FERTILIZER", "MELON", "MILK", "STRAWBERRY", "TOMATO", "WHEAT", "WOOL")


def _get(o, k, d=None):
    return o.get(k, d) if isinstance(o, dict) else getattr(o, k, d)


def _toward(cur, tgt):
    dx, dy = tgt[0] - cur[0], tgt[1] - cur[1]
    if dx > 0:
        return ["EAST"]
    if dx < 0:
        return ["WEST"]
    if dy > 0:
        return ["SOUTH"]
    if dy < 0:
        return ["NORTH"]
    return None


def _tile(tiles, pos):
    x, y = pos
    if 0 <= y < len(tiles) and 0 <= x < len(tiles[y]):
        return tiles[y][x]
    return None


def _pick_tail(shops):
    key = tuple(shops)
    if key in _TAILS:
        return key
    best, score = None, -1
    for k in _TAILS:
        s = len(set(k) & set(key)) * 2 + (1 if k and key and k[0] == key[0] else 0)
        if s > score:
            best, score = k, s
    return best


def agent(observation, configuration=None):
    try:
        _TELEMETRY["steps"] += 1
        step = int(_get(observation, "step", 0))
        seat = int(_get(observation, "player", 0) or 0)
        if step == 0:
            _STATE.clear()
        if step >= OPEN_END and "tail" not in _STATE:
            shops = list(_get(_get(observation, "town", {}) or {}, "unlocked_shops", []) or [])[:2]
            key = _pick_tail(shops)
            _STATE["tail"] = _TAILS.get(key)
            _TELEMETRY["route"] = "|".join(key) if key else None
            if _STATE["tail"] is None:
                _TELEMETRY["no_tail"] += 1
        plan = _OPENING[step] if step < OPEN_END else (
            (_STATE.get("tail") or [None])[step - OPEN_END] if step - OPEN_END < len(_STATE.get("tail") or []) else None)
        if plan is None:
            return {"farmer": ["PASS"], "hands": [], "market": []}
        nxt_src = _OPENING if step + 1 < OPEN_END else _STATE.get("tail")
        nxt_idx = step + 1 if step + 1 < OPEN_END else step + 1 - OPEN_END
        nxt = nxt_src[nxt_idx] if nxt_src and 0 <= nxt_idx < len(nxt_src) else plan

        farm = _get(observation, "farms")[seat]
        private = _get(observation, "private")
        cur = [tuple(farm["farmer"])] + [tuple(p) for p in farm["hands"]]
        units = []
        for i in range(len(cur)):
            act = plan["u"][i] if i < len(plan["u"]) else ["PASS"]
            tgt = tuple(plan["p"][i]) if i < len(plan["p"]) else None
            tgt_next = tuple(nxt["p"][i]) if i < len(nxt["p"]) else tgt
            if tgt is None:
                units.append(["PASS"])
                continue
            if cur[i] == tgt:
                if act and act[0] in ("PLANT", "BUILD_PASTURE", "BUILD_COOP"):
                    t = _tile(farm["tiles"], cur[i])
                    if isinstance(t, dict) and t.get("kind") == "WEED":
                        _TELEMETRY["dug"] += 1
                        units.append(["DIG"])
                        continue
                units.append(act)
            else:
                _TELEMETRY["corrected"] += 1
                units.append(_toward(cur[i], tgt_next or tgt) or ["PASS"])

        market = []
        missing = plan["h"] - (len(cur) - 1)
        for _ in range(max(0, min(missing, _CFG["max_catch_up"]))):
            market.append(["HIRE"])
            _TELEMETRY["hire"] += 1
        if len(farm["unlocked_quadrants"]) < plan["q"]:
            market.append(["BUY_LAND"])
            _TELEMETRY["land"] += 1
        seeds = private.get("seeds", {}) or {}
        for crop, n in (plan.get("s") or {}).items():
            have = int(seeds.get(crop, 0))
            if have < n:
                market.append(["BUY_SEED", crop, min(n - have, _CFG["max_catch_up"])])
                _TELEMETRY["seed"] += 1
        shed = dict(private["shed"])
        for animal, n in (plan.get("a") or {}).items():
            if int(shed.get(animal, 0)) < n:
                market.append(["BUY_ANIMAL", animal, min(n - int(shed.get(animal, 0)), _CFG["max_catch_up"])])
                _TELEMETRY["animal"] += 1
        sells, others = [], []
        covered = {o[0] for o in market}
        for o in plan["m"]:
            if o[0] == "SELL" and len(o) >= 3 and o[1] in _PRODUCTS:
                have = int(shed.get(o[1], 0))
                if have <= 0:
                    continue
                q = min(int(o[2]), have)
                shed[o[1]] = have - q
                sells.append(["SELL", o[1], q])
            elif o[0] not in covered:
                others.append(list(o))
        return {"farmer": units[0], "hands": units[1:], "market": (sells + market + others)[:10]}
    except Exception:
        _TELEMETRY["errors"] += 1
        return {"farmer": ["PASS"], "hands": [], "market": []}


agent.telemetry = {"majkel": _TELEMETRY}
kaggle_agent = agent
'''


def snapshot(rep, seat, step):
    o = dict(rep["steps"][step][seat]["observation"])
    for k in ("farms", "private", "town", "market"):
        if k not in o:
            o[k] = rep["steps"][step][0]["observation"][k]
    f = o["farms"][seat]
    a = normalized_action(rep, seat, step)
    animals = {k: int(v) for k, v in o["private"]["shed"].items() if k in ("COW", "SHEEP", "GOOSE") and int(v)}
    seeds = {k: int(v) for k, v in (o["private"].get("seeds") or {}).items() if int(v)}
    return {"u": [a.get("farmer") or ["PASS"]] + list(a.get("hands") or []),
            "p": [list(f["farmer"])] + [list(p) for p in f["hands"]],
            "m": [list(x) for x in (a.get("market") or []) if x],
            "h": len(f["hands"]), "q": len(f["unlocked_quadrants"]),
            "s": seeds, "a": animals}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dirs", default="/private/tmp/kaggriculture_daily_0916,/private/tmp/kaggriculture_daily_0915")
    parser.add_argument("--team", default="Majkel1337")
    parser.add_argument("--output", type=Path, default=Path("/private/tmp/kaggriculture_v43_variants/majkel_agent.py"))
    parser.add_argument("--receipt", type=Path, default=ROOT / "experiments" / "majkel_agent_build.json")
    parser.add_argument("--max-catch-up", type=int, default=4)
    args = parser.parse_args()

    episodes = []
    for d in args.dirs.split(","):
        d = Path(d)
        if not (d / "manifest.csv").is_file():
            continue
        for _, m in pd.read_csv(d / "manifest.csv").iterrows():
            p = d / f"{int(m.episode_id)}.json"
            if not p.is_file():
                continue
            rep = json.loads(p.read_text())
            names = rep["info"]["TeamNames"]
            if args.team not in names:
                continue
            seat = names.index(args.team)
            shops = tuple(rep["steps"][-1][seat]["observation"]["town"]["unlocked_shops"][:2])
            episodes.append({"id": int(m.episode_id), "rep": rep, "seat": seat, "shops": shops,
                             "money": rep["rewards"][seat],
                             "margin": rep["rewards"][seat] - rep["rewards"][1 - seat]})
    print(f"{len(episodes)} {args.team} episodes")
    best = {}
    for e in episodes:
        if e["shops"] not in best or best[e["shops"]]["margin"] < e["margin"]:
            best[e["shops"]] = e
    print(f"{len(best)} shop pairs covered")

    opening_src = max(episodes, key=lambda e: e["margin"])
    opening = [snapshot(opening_src["rep"], opening_src["seat"], s) for s in range(OPEN_END)]
    tails = {}
    for shops, e in sorted(best.items()):
        tails["|".join(shops)] = [snapshot(e["rep"], e["seat"], s) for s in range(OPEN_END, LAST)]
    payload = base64.b85encode(zlib.compress(json.dumps(
        {"opening": opening, "tails": tails, "shop_order": sorted({s for k in best for s in k})},
        separators=(",", ":")).encode(), 9)).decode()
    src = (AGENT.replace("@@PAYLOAD@@", repr(payload))
                .replace("@@CFG@@", repr({"max_catch_up": args.max_catch_up}))
                .replace("@@OPEN_END@@", str(OPEN_END)))
    args.output.write_text(src)
    receipt = {"team": args.team, "episodes": len(episodes), "pairs": len(best),
               "opening_from": opening_src["id"], "opening_margin": opening_src["margin"],
               "tails": {"|".join(k): {"episode_id": v["id"], "money": v["money"], "margin": v["margin"]}
                         for k, v in sorted(best.items())},
               "output": str(args.output), "bytes": args.output.stat().st_size,
               "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest()}
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"wrote {args.output} ({receipt['bytes']:,} bytes), opening from ep {opening_src['id']}")


if __name__ == "__main__":
    main()
