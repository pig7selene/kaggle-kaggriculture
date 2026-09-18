"""Run carrots on some of the tape's strawberry tiles, using its own visits.

Every team above 92k grows carrot and almost no strawberry -- 0.7 to 5.8
strawberry tiles against our 33, and 13 to 16 carrot against our none. The
arithmetic favours them: a strawberry tile is ongoing and produces at most four
units in the whole season, while a carrot clears in three days and can be
replanted about five times for fifteen to twenty. Seed cost is the same, one
strawberry at 100 against five carrots at 20.

The earlier crop swaps failed because they edited the tape and left its harvest
schedule pointing at cleared tiles. This one does not add a step or move a unit:
the tape already visits each strawberry tile 52 times a game, and stays on the
same tile for two consecutive steps 847 times, so the cycle -- plant, water,
harvest, replant -- fits inside visits that already happen. On a chosen tile the
layer substitutes the action: harvest when the yield is in, replant when the
tile is bare, dig a weed, and otherwise let the tape's watering through.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VD = Path("/private/tmp/kaggriculture_v43_variants")

WRAPPER = '''

# ---------------------------------------------------------------- carrot tiles
_CT_CFG = @@CFG@@
_CT_PARENT = agent
_CT_STATE = {}
_CT_TELEMETRY = {"steps": 0, "claimed": 0, "planted": 0, "harvested": 0, "units": 0,
                 "dug": 0, "seeds_bought": 0, "seed_swaps": 0, "errors": 0}
# carrot: first yield at age 2, last useful day 3, cap 4, seed 20
_CT_FIRST, _CT_LAST, _CT_CAP, _CT_SEED = 2, 3, 4, 20
_CT_STAY = {"WATER", "FERTILIZE", "HARVEST", "PASS", "DIG", "CARE", "FEED", "COLLECT_FERTILIZER"}


def _ct_get(o, k, d=None):
    return o.get(k, d) if isinstance(o, dict) else getattr(o, k, d)


def _ct_state(seat, step):
    st = _CT_STATE.get(seat)
    if st is None or step < st["last_step"]:
        st = {"last_step": step, "tiles": {}, "bought": 0}
        _CT_STATE[seat] = st
    st["last_step"] = step
    return st


def agent(observation, configuration=None):
    action = _CT_PARENT(observation, configuration)
    try:
        _CT_TELEMETRY["steps"] += 1
        step = int(_ct_get(observation, "step", -1))
        seat = int(_ct_get(observation, "player", 0) or 0)
        if step == 0:
            _CT_STATE.pop(seat, None)
        st = _ct_state(seat, step)
        day = step // 24
        if step < _CT_CFG["from_step"]:
            return action
        farm = _ct_get(observation, "farms", [])[seat]
        tiles = _ct_get(farm, "tiles")
        money = float(_ct_get(farm, "money", 0) or 0)
        positions = [_ct_get(farm, "farmer")] + [list(p) for p in (_ct_get(farm, "hands", []) or [])]
        private = _ct_get(observation, "private", {}) or {}
        seeds = dict(_ct_get(private, "seeds", {}) or {})
        units = [action.get("farmer") or ["PASS"]] + list(action.get("hands") or [])
        days_left = _CT_CFG["last_day"] - day

        # 1. claim tiles as the tape plants its strawberries, and plant carrot instead
        for i in range(min(len(units), len(positions))):
            u = units[i]
            if not u or u[0] != "PLANT" or len(u) < 2 or u[1] != "STRAWBERRY":
                continue
            pos = positions[i]
            if not isinstance(pos, (list, tuple)):
                continue
            xy = (int(pos[0]), int(pos[1]))
            if xy in st["tiles"] or len(st["tiles"]) >= _CT_CFG["tiles"]:
                continue
            if int(seeds.get("CARROT", 0) or 0) <= 0:
                continue
            st["tiles"][xy] = day
            units[i] = ["PLANT", "CARROT"]
            _CT_TELEMETRY["claimed"] += 1
            _CT_TELEMETRY["planted"] += 1

        # 2. drive our tiles on any visit the tape already makes
        for i in range(min(len(units), len(positions))):
            pos = positions[i]
            if not isinstance(pos, (list, tuple)):
                continue
            xy = (int(pos[0]), int(pos[1]))
            if xy not in st["tiles"]:
                continue
            u = units[i]
            # Only take over a step the tape was already spending on this tile.
            # Of the 1,744 visits a game, 860 are moves passing through: replacing
            # those strands the unit and breaks the rest of its route, which cost
            # 29,569 a game before this check.
            if u and u[0] not in _CT_STAY:
                continue
            tile = tiles[xy[1]][xy[0]]
            if isinstance(tile, dict) and tile.get("kind") == "WEED":
                units[i] = ["DIG"]
                _CT_TELEMETRY["dug"] += 1
                continue
            if tile is None:
                if days_left >= _CT_CFG["min_days"] and int(seeds.get("CARROT", 0) or 0) > 0:
                    units[i] = ["PLANT", "CARROT"]
                    st["tiles"][xy] = day
                    _CT_TELEMETRY["planted"] += 1
                continue
            if not isinstance(tile, dict) or tile.get("kind") != "PLANT" or tile.get("crop") != "CARROT":
                continue
            age = day - int(tile.get("planted_day", day))
            yu = int(tile.get("yield_units", 0) or 0)
            ripe = yu >= _CT_CAP or (age >= _CT_LAST and yu > 0) or (days_left <= 1 and yu > 0)
            if ripe and (not u or u[0] != "HARVEST"):
                units[i] = ["HARVEST"]
                _CT_TELEMETRY["harvested"] += 1
                _CT_TELEMETRY["units"] += yu
            elif not ripe and not tile.get("watered_today") and (not u or u[0] not in ("WATER", "FERTILIZE")):
                units[i] = ["WATER"]
        action["farmer"] = units[0]
        action["hands"] = units[1:]

        # 3. seeds: swap the tape's strawberry purchases while we are still
        # claiming tiles, then keep a small carrot buffer for the replants
        market = []
        want = _CT_CFG["tiles"] - len(st["tiles"]) if len(st["tiles"]) < _CT_CFG["tiles"] else 0
        for o in (action.get("market") or []):
            if not o:
                continue
            o = list(o)
            if o[0] == "BUY_SEED" and len(o) >= 3 and o[1] == "STRAWBERRY" and want > 0:
                n = min(max(0, int(o[2])), want)
                if n > 0:
                    rest = max(0, int(o[2]) - n)
                    _CT_TELEMETRY["seed_swaps"] += n
                    market.append(["BUY_SEED", "CARROT", n])
                    want -= n
                    if rest:
                        o = ["BUY_SEED", "STRAWBERRY", rest]
                    else:
                        continue
            market.append(o)
        have = int(seeds.get("CARROT", 0) or 0)
        need = _CT_CFG["buffer"] if (st["tiles"] and days_left >= _CT_CFG["min_days"]) else 0
        if have < need and money > _CT_CFG["reserve"] and len(market) < 10 \\
                and st["bought"] < _CT_CFG["max_buys"]:
            k = need - have
            market.append(["BUY_SEED", "CARROT", k])
            st["bought"] += 1
            _CT_TELEMETRY["seeds_bought"] += k
        action["market"] = market[:10]
        return action
    except Exception:
        _CT_TELEMETRY["errors"] += 1
        return action


agent.telemetry = {**(getattr(_CT_PARENT, "telemetry", {}) or {}), "carrot_tiles": _CT_TELEMETRY}
kaggle_agent = agent
'''

DEFAULTS = {"from_step": 120, "last_day": 29, "min_days": 5, "tiles": 10, "buffer": 6,
            "reserve": 1500, "max_buys": 40}
VARIANTS = {
    "ct10": dict(DEFAULTS),
    "ct6": {**DEFAULTS, "tiles": 6, "buffer": 4},
    "ct16": {**DEFAULTS, "tiles": 16, "buffer": 8},
    "ct24": {**DEFAULTS, "tiles": 24, "buffer": 12},
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="alp_dw_46_fv_r30")
    a = ap.parse_args()
    src = (VD / f"{a.base}.py").read_text().rstrip()
    receipt = {}
    for name, cfg in VARIANTS.items():
        out = VD / f"{a.base}_{name}.py"
        out.write_text(src + "\n" + WRAPPER.replace("@@CFG@@", repr(cfg)))
        receipt[out.stem] = {"base": a.base, "cfg": cfg, "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}
        print("built", out.name)
    (ROOT / "experiments" / "v43_carrot_tiles_build.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
