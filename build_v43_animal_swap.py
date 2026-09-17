"""Buy the animal the town will pay for.

Shipped's money runs from 49k to 177k by town, and its farm is the same in all
of them. Cows and sheep share the pasture, and FEED, CARE and HARVEST read the
animal on the tile rather than the tape, so the choice between them is the one
farm decision that can follow the town without touching a single tape action:
after step 144 the tape still buys four cows, four sheep and three geese, and
the first two shops are known by then. Wool sells only to a YARN_STORE; milk to
PIZZA_SHOP, ICE_CREAM_SHOP and SMOOTHIE_SHOP. A cow also costs 400 to a
sheep's 500 and yields every two days to a sheep's three.

The wrapper rewrites BUY_ANIMAL, PICKUP and PLACE for SHEEP/COW after step 144
according to the shops unlocked at that moment, consistently so the animal we
pick up is the one we bought. Surplus milk sells through the tape's own
shed-clamped SELL MILK orders.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VD = Path("/private/tmp/kaggriculture_v43_variants")

WRAPPER = '''

# ---------------------------------------------------------------- animal swap
_AS_CFG = @@CFG@@
_AS_MILK = {"PIZZA_SHOP", "ICE_CREAM_SHOP", "SMOOTHIE_SHOP"}
_AS_WOOL = {"YARN_STORE"}
_AS_PARENT = agent
_AS_TELEMETRY = {"steps": 0, "rewrites": 0, "sheep_to_cow": 0, "cow_to_sheep": 0, "errors": 0}


def _as_get(o, k, d=None):
    return o.get(k, d) if isinstance(o, dict) else getattr(o, k, d)


def _as_preferred(shops):
    s = set(shops)
    milk, wool = bool(s & _AS_MILK), bool(s & _AS_WOOL)
    if _AS_CFG["cow_if_noyarn"] and not wool:
        return "COW"
    if _AS_CFG["sheep_if_yarn_nomilk"] and wool and not milk:
        return "SHEEP"
    if _AS_CFG["by_count"] and milk != wool:
        return "COW" if milk else "SHEEP"
    return None


def agent(observation, configuration=None):
    action = _AS_PARENT(observation, configuration)
    try:
        _AS_TELEMETRY["steps"] += 1
        step = int(_as_get(observation, "step", -1))
        if step < 144:
            return action
        shops = list(_as_get(_as_get(observation, "town", {}) or {}, "unlocked_shops", []) or [])
        pref = _as_preferred(shops)
        if pref is None:
            return action
        other = "SHEEP" if pref == "COW" else "COW"
        def fix(a):
            if a and len(a) >= 2 and a[0] in ("PICKUP", "PLACE") and a[1] == other:
                _AS_TELEMETRY["rewrites"] += 1
                return [a[0], pref] + list(a[2:])
            return a
        action["farmer"] = fix(action.get("farmer") or ["PASS"])
        action["hands"] = [fix(h) for h in (action.get("hands") or [])]
        market = []
        for o in (action.get("market") or []):
            if o and o[0] == "BUY_ANIMAL" and len(o) >= 2 and o[1] == other:
                _AS_TELEMETRY["rewrites"] += 1
                _AS_TELEMETRY["sheep_to_cow" if pref == "COW" else "cow_to_sheep"] += int(o[2]) if len(o) > 2 else 1
                o = [o[0], pref] + list(o[2:])
            market.append(o)
        action["market"] = market
        return action
    except Exception:
        _AS_TELEMETRY["errors"] += 1
        return action


agent.telemetry = {**(getattr(_AS_PARENT, "telemetry", {}) or {}), "animal_swap": _AS_TELEMETRY}
kaggle_agent = agent
'''

VARIANTS = {
    "as_cow": {"cow_if_noyarn": True, "sheep_if_yarn_nomilk": False, "by_count": False},
    "as_both": {"cow_if_noyarn": True, "sheep_if_yarn_nomilk": True, "by_count": False},
    "as_count": {"cow_if_noyarn": False, "sheep_if_yarn_nomilk": False, "by_count": True},
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bases", default="lead5,room_plus_clamp")
    a = ap.parse_args()
    receipt = {}
    for base in a.bases.split(","):
        src = (VD / f"{base}.py").read_text().rstrip()
        for name, cfg in VARIANTS.items():
            out = VD / f"{base}_{name}.py"
            out.write_text(src + "\n" + WRAPPER.replace("@@CFG@@", repr(cfg)))
            receipt[out.stem] = {"base": base, "cfg": cfg, "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}
            print("built", out.name)
    (ROOT / "experiments" / "v43_animal_swap_build.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
