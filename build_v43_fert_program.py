"""Keep the fertilizer and put it on the wheat, the way the rank-15 fork does.

Over 99 of its own games Driz Lo beats V43-lineage opponents 52-6 with a mean
margin of +3,828, where our five-step lead manages +2,440 at 75%. Its farm is
the tape's -- same plantings, same builds, same land steps -- and the edit is
one coupled programme: fertilize 151 times a game against the tape's 85, post
28 fewer fertilizer sell orders, and water, feed and care about 107 fewer times.

The steps are there. Of the tape's 995 waterings, 68 are yield-neutral and safe
to drop: a non-ongoing crop outside its yield window that was watered
yesterday, plus nine that land on an already-watered tile. Dying needs two
consecutive dry days, so skipping one costs nothing, and the unit is already
standing on the tile -- replacing WATER with FERTILIZE moves no one.

The binding constraint is stock: the tape sells 285 fertilizer units a game and
holds almost none, so at 34 of those 64 moments there is no fertilizer in the
hand or the shed. This layer keeps a reserve back from the sell orders, tops
units up when they idle next to the shed, and spends it on wheat and carrot
whose yield window is still ahead. A fertilized wheat tile ends at the cap of
six against four unfertilized; a carrot at four against three.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VD = Path("/private/tmp/kaggriculture_v43_variants")

WRAPPER = '''

# ---------------------------------------------------------------- fertilizer programme
_FP_CFG = @@CFG@@
# crop -> (first day a watering adds yield, last useful day, max_yield, ongoing)
_FP_CROPS = {"WHEAT": (2, 4, 6, False), "CARROT": (2, 3, 4, False), "MELON": (6, 12, 6, False),
             "STRAWBERRY": (10, 28, 4, True), "TOMATO": (8, 28, 4, True)}
_FP_ACCESS = {(4, 4), (5, 4), (4, 5), (5, 5)}
_FP_PARENT = agent
_FP_TELEMETRY = {"steps": 0, "substituted": 0, "picked": 0, "held_back": 0, "no_stock": 0,
                 "by_crop": {}, "errors": 0}


def _fp_get(o, k, d=None):
    return o.get(k, d) if isinstance(o, dict) else getattr(o, k, d)


def _fp_skippable(tile, day):
    """A watering that adds no yield and cannot kill the plant."""
    if not isinstance(tile, dict) or tile.get("kind") != "PLANT":
        return False
    if tile.get("watered_today"):
        return True
    spec = _FP_CROPS.get(tile.get("crop"))
    if spec is None:
        return False
    if spec[3]:
        return False                       # an ongoing crop's watering always feeds production
    age = day - int(tile.get("planted_day", day))
    if age >= spec[0]:
        return False                       # inside the yield window: every watering pays
    return int(tile.get("consecutive_unwatered", 0) or 0) == 0


def _fp_wants_fertilizer(tile, day, prices):
    """Worth a fertilizer only if the extra units it buys are worth more than
    selling the fertilizer. One application covers three days: for wheat that is
    the whole yield window and takes a tile from four units to the cap of six;
    for an ongoing crop it doubles one or two production days. Either way count
    one extra unit conservatively and compare prices."""
    spec = _FP_CROPS.get(tile.get("crop")) if isinstance(tile, dict) else None
    if spec is None or tile.get("kind") != "PLANT":
        return False
    if int(tile.get("fertilized_until_day", -1)) >= day:
        return False
    age = day - int(tile.get("planted_day", day))
    if age > spec[1] or int(tile.get("yield_units", 0) or 0) >= spec[2]:
        return False
    if spec[3] and age + 1 < spec[0]:
        return False                       # ongoing, first yield still more than a day away
    crop_price = int(prices.get(tile.get("crop"), 0) or 0)
    fert_price = int(prices.get("FERTILIZER", 0) or 0)
    return crop_price >= _FP_CFG["value_ratio"] * max(1, fert_price)


def agent(observation, configuration=None):
    action = _FP_PARENT(observation, configuration)
    try:
        _FP_TELEMETRY["steps"] += 1
        step = int(_fp_get(observation, "step", -1))
        if step < _FP_CFG["from_step"] or step > 718:
            return action
        day = step // 24
        seat = int(_fp_get(observation, "player", 0) or 0)
        farm = _fp_get(observation, "farms", [])[seat]
        tiles = _fp_get(farm, "tiles")
        positions = [_fp_get(farm, "farmer")] + [list(p) for p in (_fp_get(farm, "hands", []) or [])]
        private = _fp_get(observation, "private", {}) or {}
        shed = dict(_fp_get(private, "shed", {}) or {})
        invs = list(_fp_get(private, "inventories", []) or [])
        prices = dict(_fp_get(_fp_get(observation, "market", {}) or {}, "prices", {}) or {})
        units = [action.get("farmer") or ["PASS"]] + list(action.get("hands") or [])
        stock = int(shed.get("FERTILIZER", 0) or 0)
        cheap = int(prices.get("FERTILIZER", 999) or 999) <= _FP_CFG["max_price"]

        for i in range(min(len(units), len(positions))):
            u = units[i]
            pos = positions[i]
            if not u or not isinstance(pos, (list, tuple)):
                continue
            x, y = int(pos[0]), int(pos[1])
            tile = tiles[y][x]
            inv = invs[i] if i < len(invs) else {}
            carrying = int(inv.get("FERTILIZER", 0) or 0)
            # 1. a yield-neutral watering becomes a fertilization, in place
            if u[0] == "WATER" and _fp_skippable(tile, day) and _fp_wants_fertilizer(tile, day, prices):
                if carrying > 0:
                    units[i] = ["FERTILIZE"]
                    _FP_TELEMETRY["substituted"] += 1
                    crop = tile.get("crop")
                    _FP_TELEMETRY["by_crop"][crop] = _FP_TELEMETRY["by_crop"].get(crop, 0) + 1
                    continue
                _FP_TELEMETRY["no_stock"] += 1
            # 1b. an idle step on a tile that wants fertilizer, at no cost at all
            if u[0] in ("PASS",) and carrying > 0 and _fp_wants_fertilizer(tile, day, prices):
                units[i] = ["FERTILIZE"]
                _FP_TELEMETRY["substituted"] += 1
                crop = tile.get("crop")
                _FP_TELEMETRY["by_crop"][crop] = _FP_TELEMETRY["by_crop"].get(crop, 0) + 1
                continue
            # 2. an idle step beside the shed tops the unit up
            if _FP_CFG["top_up"] and u[0] in ("PASS",) and (x, y) in _FP_ACCESS \\
                    and stock > 0 and carrying < _FP_CFG["carry"]:
                take = min(stock, _FP_CFG["carry"] - carrying)
                units[i] = ["PICKUP", "FERTILIZER", take]
                stock -= take
                _FP_TELEMETRY["picked"] += take
        action["farmer"] = units[0]
        action["hands"] = units[1:]

        # 3. hold a reserve back from the sell orders, while fertilizer is dear
        if _FP_CFG["reserve"] and cheap is False:
            market = [list(o) for o in (action.get("market") or []) if o]
            keep = _FP_CFG["reserve"]
            for o in market:
                if o[0] == "SELL" and len(o) >= 3 and o[1] == "FERTILIZER" and int(o[2]) > 0:
                    room = max(0, int(shed.get("FERTILIZER", 0) or 0) - keep)
                    new = min(int(o[2]), room)
                    if new < int(o[2]):
                        _FP_TELEMETRY["held_back"] += int(o[2]) - new
                        o[2] = new
            action["market"] = market
        return action
    except Exception:
        _FP_TELEMETRY["errors"] += 1
        return action


agent.telemetry = {**(getattr(_FP_PARENT, "telemetry", {}) or {}), "fert_program": _FP_TELEMETRY}
kaggle_agent = agent
'''

DEFAULTS = {"from_step": 144, "max_price": 40, "reserve": 0, "carry": 3, "top_up": False, "value_ratio": 2.0}
VARIANTS = {
    "fv_r30": {**DEFAULTS, "value_ratio": 3.0},
    "fv_r20": {**DEFAULTS, "value_ratio": 2.0},
    "fv_off": {**DEFAULTS, "value_ratio": 9999.0},
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="dl_g50")
    a = ap.parse_args()
    src = (VD / f"{a.base}.py").read_text().rstrip()
    receipt = {}
    for name, cfg in VARIANTS.items():
        out = VD / f"{a.base}_{name}.py"
        out.write_text(src + "\n" + WRAPPER.replace("@@CFG@@", repr(cfg)))
        receipt[out.stem] = {"base": a.base, "cfg": cfg, "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}
        print("built", out.name)
    (ROOT / "experiments" / "v43_fert_program_build.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
