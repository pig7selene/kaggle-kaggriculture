"""Plant the handful of tomatoes every strong fork of our lineage plants.

Driz Lo, mikelou1, Kaggriculture Agent and Catalyst all plant one to three more
tomatoes a game than the tape they would otherwise be replaying, which plants
none at all. Tomato is the one crop nobody in the lineage grows, so the town's
pizza shops and farmers' markets keep consuming a supply that never arrives:
in our own online games it ends between $87 and $144 where strawberry collapses
to $1 and wheat sits near $30. It is also an ongoing crop producing every day
from the eighth after planting, so a tile is worth four units at a price no one
else is pushing down.

The layer converts a few of the tape's wheat plantings, buys the seed in their
place, and harvests the tile itself once the yield is in, leaving everything
else alone.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VD = Path("/private/tmp/kaggriculture_v43_variants")

WRAPPER = '''

# ---------------------------------------------------------------- tomato corner
_TM_CFG = @@CFG@@
_TM_STAY = {"WATER", "FERTILIZE", "HARVEST", "PASS", "DIG"}
_TM_PARENT = agent
_TM_STATE = {}
_TM_TELEMETRY = {"steps": 0, "planted": 0, "harvested": 0, "units": 0, "seeds": 0, "errors": 0}


def _tm_get(o, k, d=None):
    return o.get(k, d) if isinstance(o, dict) else getattr(o, k, d)


def agent(observation, configuration=None):
    action = _TM_PARENT(observation, configuration)
    try:
        _TM_TELEMETRY["steps"] += 1
        step = int(_tm_get(observation, "step", -1))
        seat = int(_tm_get(observation, "player", 0) or 0)
        if step == 0:
            _TM_STATE.pop(seat, None)
        st = _TM_STATE.setdefault(seat, {"tiles": {}, "planted": 0})
        if not (_TM_CFG["from_step"] <= step <= _TM_CFG["to_step"]):
            return action
        day = step // 24
        farm = _tm_get(observation, "farms", [])[seat]
        tiles = _tm_get(farm, "tiles")
        money = float(_tm_get(farm, "money", 0) or 0)
        positions = [_tm_get(farm, "farmer")] + [list(p) for p in (_tm_get(farm, "hands", []) or [])]
        seeds = dict(_tm_get(_tm_get(observation, "private", {}) or {}, "seeds", {}) or {})
        units = [action.get("farmer") or ["PASS"]] + list(action.get("hands") or [])
        days_left = _TM_CFG["last_day"] - day
        for i in range(min(len(units), len(positions))):
            u = units[i]
            pos = positions[i]
            if not u or not isinstance(pos, (list, tuple)):
                continue
            xy = (int(pos[0]), int(pos[1]))
            if u[0] == "PLANT" and len(u) > 1 and u[1] == "WHEAT":
                if st["planted"] < _TM_CFG["tiles"] and int(seeds.get("TOMATO", 0) or 0) > 0 \\
                        and days_left >= _TM_CFG["min_days"]:
                    units[i] = ["PLANT", "TOMATO"]
                    st["tiles"][xy] = day
                    st["planted"] += 1
                    _TM_TELEMETRY["planted"] += 1
                continue
            if xy not in st["tiles"] or u[0] not in _TM_STAY:
                continue
            tile = tiles[xy[1]][xy[0]]
            if not isinstance(tile, dict) or tile.get("crop") != "TOMATO":
                if not isinstance(tile, dict) or tile.get("kind") != "PLANT":
                    st["tiles"].pop(xy, None)
                continue
            yu = int(tile.get("yield_units", 0) or 0)
            if yu > 0 and (yu >= _TM_CFG["cap"] or days_left <= 1):
                units[i] = ["HARVEST"]
                _TM_TELEMETRY["harvested"] += 1
                _TM_TELEMETRY["units"] += yu
            elif not tile.get("watered_today") and u[0] not in ("WATER", "FERTILIZE"):
                units[i] = ["WATER"]
        action["farmer"] = units[0]
        action["hands"] = units[1:]
        market = []
        want = max(0, _TM_CFG["tiles"] - st["planted"] - int(seeds.get("TOMATO", 0) or 0))
        for o in (action.get("market") or []):
            if not o:
                continue
            o = list(o)
            if o[0] == "BUY_SEED" and len(o) >= 3 and o[1] == "WHEAT" and want > 0 and money > _TM_CFG["reserve"]:
                n = min(max(0, int(o[2])), want)
                if n > 0:
                    rest = max(0, int(o[2]) - n)
                    market.append(["BUY_SEED", "TOMATO", n])
                    _TM_TELEMETRY["seeds"] += n
                    want -= n
                    if rest:
                        o = ["BUY_SEED", "WHEAT", rest]
                    else:
                        continue
            market.append(o)
        action["market"] = market[:10]
        return action
    except Exception:
        _TM_TELEMETRY["errors"] += 1
        return action


agent.telemetry = {**(getattr(_TM_PARENT, "telemetry", {}) or {}), "tomato": _TM_TELEMETRY}
kaggle_agent = agent
'''

DEFAULTS = {"from_step": 144, "to_step": 520, "last_day": 29, "min_days": 11, "tiles": 2,
            "cap": 4, "reserve": 2000}
VARIANTS = {"tm2": dict(DEFAULTS), "tm3": {**DEFAULTS, "tiles": 3}, "tm5": {**DEFAULTS, "tiles": 5}}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="alp_dw_416_fv_r30_qc_all")
    a = ap.parse_args()
    src = (VD / f"{a.base}.py").read_text().rstrip()
    receipt = {}
    for name, cfg in VARIANTS.items():
        out = VD / f"{a.base}_{name}.py"
        out.write_text(src + "\n" + WRAPPER.replace("@@CFG@@", repr(cfg)))
        receipt[out.stem] = {"base": a.base, "cfg": cfg, "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}
        print("built", out.name)
    (ROOT / "experiments" / "v43_tomato_build.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
