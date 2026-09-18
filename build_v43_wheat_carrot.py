"""Swap a few of the tape's wheat plantings for carrot, and harvest them in time.

All four high-ranking forks of our own lineage plant carrot where the tape plants
wheat -- mikelou1 turns 14.8 wheat plantings into 13.8 carrots, Kaggriculture
Agent 8.6, Driz Lo 4.4 -- and all four fertilize more and feed less. The crop
swap is the one of those we have a clean mechanism for.

Two earlier attempts failed for reasons that do not apply here. Converting
*strawberry* tiles needs 1.25 actions a day against the 0.99 the tape supplies;
wheat already costs 1.2 (plant, four waterings, harvest over five days) and
carrot costs 1.25 over four, so the budget is unchanged. And the 9/17 swap died
because carrot's tile clears a day before wheat's -- lifespan is planted_day+4
against wheat's +5 -- so the harvest the tape had scheduled arrived at a weed.
Here the layer harvests the swapped tiles itself as soon as the yield is in,
using a step the tape was already spending on that tile.

Carrot returns about fifteen units a game against wheat's eighteen but sells at
$41-60 against $21-40, so the tile is worth roughly a quarter more.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VD = Path("/private/tmp/kaggriculture_v43_variants")

WRAPPER = '''

# ---------------------------------------------------------------- wheat to carrot
_WC_CFG = @@CFG@@
_WC_STAY = {"WATER", "FERTILIZE", "HARVEST", "PASS", "DIG"}
_WC_PARENT = agent
_WC_STATE = {}
_WC_TELEMETRY = {"steps": 0, "swapped": 0, "harvested": 0, "units": 0, "seeds": 0,
                 "replanted": 0, "dug": 0, "errors": 0}


def _wc_get(o, k, d=None):
    return o.get(k, d) if isinstance(o, dict) else getattr(o, k, d)


def _wc_state(seat, step):
    st = _WC_STATE.get(seat)
    if st is None or step < st["last"]:
        st = {"last": step, "tiles": {}, "swaps": 0, "buys": 0}
        _WC_STATE[seat] = st
    st["last"] = step
    return st


def agent(observation, configuration=None):
    action = _WC_PARENT(observation, configuration)
    try:
        _WC_TELEMETRY["steps"] += 1
        step = int(_wc_get(observation, "step", -1))
        seat = int(_wc_get(observation, "player", 0) or 0)
        if step == 0:
            _WC_STATE.pop(seat, None)
        st = _wc_state(seat, step)
        if step < _WC_CFG["from_step"] or step > _WC_CFG["to_step"]:
            return action
        day = step // 24
        farm = _wc_get(observation, "farms", [])[seat]
        tiles = _wc_get(farm, "tiles")
        money = float(_wc_get(farm, "money", 0) or 0)
        positions = [_wc_get(farm, "farmer")] + [list(p) for p in (_wc_get(farm, "hands", []) or [])]
        private = _wc_get(observation, "private", {}) or {}
        seeds = dict(_wc_get(private, "seeds", {}) or {})
        units = [action.get("farmer") or ["PASS"]] + list(action.get("hands") or [])
        days_left = _WC_CFG["last_day"] - day
        carrot_seed = int(seeds.get("CARROT", 0) or 0)

        for i in range(min(len(units), len(positions))):
            u = units[i]
            pos = positions[i]
            if not u or not isinstance(pos, (list, tuple)):
                continue
            xy = (int(pos[0]), int(pos[1]))
            tile = tiles[xy[1]][xy[0]]
            # 1. the tape plants wheat here: plant carrot instead, while quota remains
            if u[0] == "PLANT" and len(u) > 1 and u[1] == "WHEAT":
                if st["swaps"] < _WC_CFG["tiles"] and carrot_seed > 0 and days_left >= _WC_CFG["min_days"]:
                    units[i] = ["PLANT", "CARROT"]
                    st["tiles"][xy] = day
                    st["swaps"] += 1
                    carrot_seed -= 1
                    _WC_TELEMETRY["swapped"] += 1
                continue
            if xy not in st["tiles"]:
                continue
            # only take a step the tape was already spending on this tile
            if u[0] not in _WC_STAY:
                continue
            if isinstance(tile, dict) and tile.get("kind") == "WEED":
                units[i] = ["DIG"]
                _WC_TELEMETRY["dug"] += 1
                continue
            if tile is None:
                # the tape will plant wheat here again in its own time; let it
                st["tiles"].pop(xy, None)
                continue
            if not isinstance(tile, dict) or tile.get("crop") != "CARROT":
                st["tiles"].pop(xy, None)
                continue
            age = day - int(tile.get("planted_day", day))
            yu = int(tile.get("yield_units", 0) or 0)
            # carrot clears a day earlier than wheat, so harvest as soon as the
            # window has paid rather than waiting for the tape's wheat schedule
            # the yield window is age 2 and 3, so on the last day of it the
            # watering has to land before the harvest: taking the first step
            # available at age 3 cost a unit a tile, two harvested instead of three
            ripe = yu >= _WC_CFG["cap"] or days_left <= 1 or age > _WC_CFG["harvest_age"] \
                or (age >= _WC_CFG["harvest_age"] and tile.get("watered_today"))
            if yu > 0 and ripe:
                units[i] = ["HARVEST"]
                _WC_TELEMETRY["harvested"] += 1
                _WC_TELEMETRY["units"] += yu
            elif not tile.get("watered_today") and u[0] not in ("WATER", "FERTILIZE"):
                units[i] = ["WATER"]
        action["farmer"] = units[0]
        action["hands"] = units[1:]

        # 2. buy carrot seed in place of the wheat seed we will not use
        market = []
        want = max(0, _WC_CFG["tiles"] - st["swaps"])
        for o in (action.get("market") or []):
            if not o:
                continue
            o = list(o)
            if o[0] == "BUY_SEED" and len(o) >= 3 and o[1] == "WHEAT" and want > 0 \\
                    and int(seeds.get("CARROT", 0) or 0) < _WC_CFG["buffer"]:
                n = min(max(0, int(o[2])), want)
                if n > 0 and money > _WC_CFG["reserve"]:
                    rest = max(0, int(o[2]) - n)
                    market.append(["BUY_SEED", "CARROT", n])
                    _WC_TELEMETRY["seeds"] += n
                    want -= n
                    if rest:
                        o = ["BUY_SEED", "WHEAT", rest]
                    else:
                        continue
            market.append(o)
        action["market"] = market[:10]
        return action
    except Exception:
        _WC_TELEMETRY["errors"] += 1
        return action


agent.telemetry = {**(getattr(_WC_PARENT, "telemetry", {}) or {}), "wheat_carrot": _WC_TELEMETRY}
kaggle_agent = agent
'''

DEFAULTS = {"from_step": 144, "to_step": 700, "last_day": 29, "min_days": 5, "tiles": 14,
            "buffer": 4, "reserve": 2000, "cap": 4, "harvest_age": 3}
VARIANTS = {
    "wc10": {**DEFAULTS, "tiles": 10},
    "wc12": {**DEFAULTS, "tiles": 12},
    "wc14": dict(DEFAULTS),
    "wc16": {**DEFAULTS, "tiles": 16},
    "wc18": {**DEFAULTS, "tiles": 18},
}


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
    (ROOT / "experiments" / "v43_wheat_carrot_build.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
