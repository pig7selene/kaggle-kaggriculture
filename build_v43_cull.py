"""Stop paying to keep an animal whose product the town does not buy.

Every team above 92k ends a yarn-free town with no sheep; our chassis keeps six,
because it commits the herd at steps 196-226 when three of the eight shops have
opened and the yarn store usually appears at 288. That purchase cannot be
decided better -- the information does not exist yet -- but the decision to keep
paying for the animal can wait until the town is fully revealed.

By day 20 wool in a yarn-free town sits at $1-5. A sheep then returns about
three more units, some fifteen dollars, while keeping it alive costs a wheat a
day at thirty to forty dollars, plus a feed and a care step. Base production
does not depend on feeding at all -- the engine adds it on the interval
regardless, and feeding only buys the care bonus and prevents the animal
escaping after two dry days -- so an animal whose product has collapsed is
worth strictly less than the wheat it eats.

This turns FEED and CARE into PASS for such animals and lets them go, keeping
the wheat. The test is a live price against the wheat price, so it fires only
where the product really is worthless, and never before the shops are open.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VD = Path("/private/tmp/kaggriculture_v43_variants")

WRAPPER = '''

# ---------------------------------------------------------------- cull
_CU_CFG = @@CFG@@
_CU_PRODUCT = {"SHEEP": ("WOOL", 3), "COW": ("MILK", 2), "GOOSE": ("EGG", 1)}
_CU_SHOP_BUYS = {"BAKERY": ("EGG", "WHEAT"), "PIZZA_SHOP": ("MILK", "TOMATO", "WHEAT"),
                 "BRUNCH_SPOT": ("EGG", "WHEAT", "STRAWBERRY"), "YARN_STORE": ("WOOL",),
                 "ICE_CREAM_SHOP": ("STRAWBERRY", "MILK", "WHEAT"), "PET_CAFE": ("CARROT",),
                 "SMOOTHIE_SHOP": ("STRAWBERRY", "MILK"),
                 "FARMERS_MARKET": ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY")}
_CU_PARENT = agent
_CU_STATE = {}
_CU_TELEMETRY = {"steps": 0, "feeds_dropped": 0, "cares_dropped": 0, "culled_tiles": 0,
                 "errors": 0, "last": ""}


def _cu_get(o, k, d=None):
    return o.get(k, d) if isinstance(o, dict) else getattr(o, k, d)


def agent(observation, configuration=None):
    action = _CU_PARENT(observation, configuration)
    try:
        _CU_TELEMETRY["steps"] += 1
        step = int(_cu_get(observation, "step", -1))
        seat = int(_cu_get(observation, "player", 0) or 0)
        if step == 0:
            _CU_STATE.pop(seat, None)
        if step < _CU_CFG["from_step"]:
            return action
        day = step // 24
        farm = _cu_get(observation, "farms", [])[seat]
        tiles = _cu_get(farm, "tiles")
        positions = [_cu_get(farm, "farmer")] + [list(p) for p in (_cu_get(farm, "hands", []) or [])]
        prices = dict(_cu_get(_cu_get(observation, "market", {}) or {}, "prices", {}) or {})
        wheat = int(prices.get("WHEAT", 30) or 30)
        st = _CU_STATE.setdefault(seat, {"culled": set()})
        units = [action.get("farmer") or ["PASS"]] + list(action.get("hands") or [])
        for i in range(min(len(units), len(positions))):
            u = units[i]
            if not u or u[0] not in ("FEED", "CARE"):
                continue
            pos = positions[i]
            if not isinstance(pos, (list, tuple)):
                continue
            xy = (int(pos[0]), int(pos[1]))
            tile = tiles[xy[1]][xy[0]]
            if not isinstance(tile, dict):
                continue
            animal = tile.get("animal")
            if animal not in _CU_CFG["animals"]:
                continue
            product, interval = _CU_PRODUCT[animal]
            # The town's shop list is stable; a spot price is not. Milk dips to
            # $1 and recovers to $152 within a game, and an earlier version of
            # this layer culled the whole herd on those dips. Judge on demand:
            # no shop in the revealed town consumes the product, so its price
            # cannot recover.
            shops = list(_cu_get(_cu_get(observation, "town", {}) or {}, "unlocked_shops", []) or [])
            buyers = sum(1 for sh in shops if product in _CU_SHOP_BUYS.get(sh, ()))
            price = int(prices.get(product, 0) or 0)
            if buyers > _CU_CFG["max_buyers"] or price > _CU_CFG["max_price"]:
                continue
            days_left = max(0, _CU_CFG["last_day"] - day)
            remaining = (days_left // interval) + int(tile.get("yield_units", 0) or 0)
            worth = remaining * price
            cost = days_left * wheat * _CU_CFG["feed_days_frac"]
            if xy in st["culled"] or worth < cost * _CU_CFG["margin"]:
                st["culled"].add(xy)
                if u[0] == "FEED":
                    _CU_TELEMETRY["feeds_dropped"] += 1
                else:
                    _CU_TELEMETRY["cares_dropped"] += 1
                units[i] = ["PASS"]
                _CU_TELEMETRY["last"] = f"{animal} {product}=${price} buyers={buyers} worth {worth:.0f} vs cost {cost:.0f} day {day}"
        _CU_TELEMETRY["culled_tiles"] = len(st["culled"])
        action["farmer"] = units[0]
        action["hands"] = units[1:]
        return action
    except Exception:
        _CU_TELEMETRY["errors"] += 1
        return action


agent.telemetry = {**(getattr(_CU_PARENT, "telemetry", {}) or {}), "cull": _CU_TELEMETRY}
kaggle_agent = agent
'''

DEFAULTS = {"from_step": 480, "last_day": 29, "max_price": 20, "margin": 1.0,
            "feed_days_frac": 0.5, "animals": ("SHEEP",), "max_buyers": 0}
VARIANTS = {
    "cl_sheep": dict(DEFAULTS),
    "cl_sheep_d16": {**DEFAULTS, "from_step": 384},
    "cl_sheep_p10": {**DEFAULTS, "max_price": 10},
    "cl_all": {**DEFAULTS, "animals": ("SHEEP", "COW", "GOOSE")},
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
    (ROOT / "experiments" / "v43_cull_build.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
