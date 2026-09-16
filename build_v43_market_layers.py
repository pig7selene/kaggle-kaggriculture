"""Market-side tail layers for the V43 room_plus_clamp base.

Every aggregate we can measure -- production verbs per day, money per day,
shed occupancy, end-of-day overflow -- is the same for アルモンド (rank 38,
2902) and V43 room_plus_clamp (our 2677). The one thing that differs is the
shape of the sell orders: 1.5-2x as many SELL orders per day and 2-3x the
posted quantity for the same output, i.e. "sell whatever is in the shed"
rather than the lot the tape recorded. The engine gives that a mechanism:
market inventory never reverts, so each unit sold permanently lowers the
price for both players, and within a step the two players' orders are
matched slot by slot in lockstep. Selling a unit earlier than the opponent,
or in an earlier slot, is a pure transfer from them to us.

Three variants, appended as an EOF wrapper around V43's final ``agent`` (the
overlay stack below it is untouched, and any failure returns the parent's
action unchanged):

  sell_on_arrival  raise each SELL to the full shed stock of that product and
                   add a SELL for every other product in the shed. WHEAT and
                   FERTILIZER are left alone: hands pick them up to FEED and
                   FERTILIZE, so the tape needs them in the shed.
  slot_priority    keep quantities, but order SELLs first, by unit price
                   descending, so premium goods race the opponent's first slots.
  both             the two together.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = Path("/private/tmp/kaggriculture_v43_variants/room_plus_clamp.py")
OUT_DIR = Path("/private/tmp/kaggriculture_v43_variants")
VARIANTS = {
    "sell_on_arrival_v2": {"over_post": True, "add_missing": True, "reorder": False},
    "slot_priority_v2": {"over_post": False, "add_missing": False, "reorder": True},
    "both_v2": {"over_post": True, "add_missing": True, "reorder": True},
}

WRAPPER = '''

# ---------------------------------------------------------------- market layer
# The parent's orders keep their slots and are never dropped: V43's tapes carry
# same-step BUY_PRODUCT -> SELL wheat washes whose legs must stay in order (82
# of them in 4 local games), and slot alignment is part of the lockstep race.
_ML_CFG = @@CFG@@
_ML_PRODUCTS = ("CARROT", "EGG", "FERTILIZER", "MELON", "MILK", "STRAWBERRY", "TOMATO", "WHEAT", "WOOL")
_ML_INPUTS = ("WHEAT", "FERTILIZER")   # picked up from the shed for FEED / FERTILIZE, and washed
_ML_MAX_ORDERS = 10
_ML_PARENT = agent
_ML_TELEMETRY = {"steps": 0, "changed": 0, "raised_units": 0, "added_orders": 0, "reordered": 0, "errors": 0}


def _ml_get(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def agent(observation, configuration=None):
    action = _ML_PARENT(observation, configuration)
    try:
        _ML_TELEMETRY["steps"] += 1
        shed = dict(_ml_get(_ml_get(observation, "private", {}) or {}, "shed", {}) or {})
        prices = dict(_ml_get(_ml_get(observation, "market", {}) or {}, "prices", {}) or {})
        market = [list(o) for o in (action.get("market") or []) if o][:_ML_MAX_ORDERS]
        before = [list(o) for o in market]
        price = lambda item: int(prices.get(item, 0) or 0)
        free_sell = lambda o: (o[0] == "SELL" and len(o) >= 3 and o[1] in _ML_PRODUCTS
                               and o[1] not in _ML_INPUTS)
        planned = {}
        for o in market:
            if o[0] == "SELL" and len(o) >= 3:
                planned[o[1]] = planned.get(o[1], 0) + max(0, int(o[2]))
        if _ML_CFG["over_post"]:
            seen = set()
            for o in market:
                if not free_sell(o) or o[1] in seen:
                    continue
                seen.add(o[1])
                have = int(shed.get(o[1], 0) or 0)
                if have > planned.get(o[1], 0):
                    extra = have - planned.get(o[1], 0)
                    o[2] = max(0, int(o[2])) + extra
                    planned[o[1]] = have
                    _ML_TELEMETRY["raised_units"] += extra
        if _ML_CFG["reorder"]:
            idx = [i for i, o in enumerate(market) if free_sell(o)]
            ordered = sorted((market[i] for i in idx), key=lambda o: -price(o[1]))
            if [market[i] for i in idx] != ordered:
                _ML_TELEMETRY["reordered"] += 1
            for i, o in zip(idx, ordered):
                market[i] = o
        if _ML_CFG["add_missing"]:
            missing = [item for item in _ML_PRODUCTS
                       if item not in _ML_INPUTS and int(shed.get(item, 0) or 0) > 0
                       and item not in planned and price(item) > 1]
            for item in sorted(missing, key=lambda it: -price(it))[:max(0, _ML_MAX_ORDERS - len(market))]:
                market.append(["SELL", item, int(shed.get(item, 0) or 0)])
                _ML_TELEMETRY["added_orders"] += 1
        if market != before:
            _ML_TELEMETRY["changed"] += 1
        action["market"] = market
        return action
    except Exception:
        _ML_TELEMETRY["errors"] += 1
        return action


agent.telemetry = {**(getattr(_ML_PARENT, "telemetry", {}) or {}), "market_layer": _ML_TELEMETRY}
kaggle_agent = agent
'''


def main() -> None:
    source = BASE.read_text()
    if "_ML_PARENT" in source:
        raise RuntimeError("base already carries a market layer")
    receipt = {"base": str(BASE), "base_sha256": hashlib.sha256(BASE.read_bytes()).hexdigest(), "variants": {}}
    for name, cfg in VARIANTS.items():
        out = OUT_DIR / f"{name}.py"
        out.write_text(source.rstrip() + "\n" + WRAPPER.replace("@@CFG@@", repr(cfg)))
        receipt["variants"][name] = {"path": str(out), "cfg": cfg,
                                     "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}
        print(name, out, receipt["variants"][name]["sha256"][:12])
    (ROOT / "experiments" / "v43_market_layers_build.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
