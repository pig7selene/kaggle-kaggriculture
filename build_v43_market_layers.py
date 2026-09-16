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
        "slot_priority_v3": {"over_post": False, "add_missing": False, "reorder": True},
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
        # zero-quantity SELLs are V43's slot-alignment placeholders (sell_lead
        # suppression); they must stay where they are or they push real orders back
        free_sell = lambda o: (o[0] == "SELL" and len(o) >= 3 and o[1] in _ML_PRODUCTS
                               and o[1] not in _ML_INPUTS and int(o[2]) > 0)
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


GATE_WRAPPER = '''

# ---------------------------------------------------------------- price gate
# Premium goods have cliff-shaped oversupply curves (WOOL reaches the $1 floor
# 59 units above equilibrium, STRAWBERRY 62, MILK 76) and the town consumes
# them back only every 4 steps. A tape sells at recorded steps whatever the
# price; this holds premium stock while the quote is below `low` x base and
# releases the whole stock once it is at or above `high` x base. Holding is
# allowed only with shed room to spare, never in the last two hours of a day
# (room_guard and the tape's own end-of-day sells run unmodified) and never on
# the final day. Parent orders keep their slots; a held SELL becomes qty 0.
_PG_CFG = @@CFG@@
_PG_BASE = {"WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120, "MELON": 250,
            "EGG": 50, "MILK": 160, "WOOL": 200, "FERTILIZER": 100}
_PG_PRODUCTS = tuple(_PG_BASE)
_PG_MAX_ORDERS = 10
_PG_PARENT = agent
_PG_TELEMETRY = {"steps": 0, "held_units": 0, "held_steps": 0, "released_units": 0,
                 "release_orders": 0, "errors": 0}


def _pg_get(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def agent(observation, configuration=None):
    action = _PG_PARENT(observation, configuration)
    try:
        _PG_TELEMETRY["steps"] += 1
        step = int(_pg_get(observation, "step", -1))
        shed = dict(_pg_get(_pg_get(observation, "private", {}) or {}, "shed", {}) or {})
        prices = dict(_pg_get(_pg_get(observation, "market", {}) or {}, "prices", {}) or {})
        market = [list(o) for o in (action.get("market") or []) if o][:_PG_MAX_ORDERS]
        shed_total = sum(int(shed.get(p, 0) or 0) for p in _PG_PRODUCTS)
        hour = step % 72
        can_hold = (step <= _PG_CFG["last_hold_step"] and hour < 70
                    and shed_total <= _PG_CFG["hold_max_shed"])
        held_any = False
        for item in _PG_CFG["items"]:
            have = int(shed.get(item, 0) or 0)
            if have <= 0:
                continue
            price = int(prices.get(item, 0) or 0)
            base = _PG_BASE[item]
            sells = [o for o in market if o[0] == "SELL" and len(o) >= 3 and o[1] == item]
            planned = sum(max(0, int(o[2])) for o in sells)
            if price < _PG_CFG["low"] * base and can_hold:
                if planned > 0:
                    for o in sells:
                        o[2] = 0
                    _PG_TELEMETRY["held_units"] += min(planned, have)
                    held_any = True
            elif price >= _PG_CFG["high"] * base and have > planned:
                extra = have - planned
                if sells:
                    sells[0][2] = max(0, int(sells[0][2])) + extra
                elif len(market) < _PG_MAX_ORDERS:
                    market.append(["SELL", item, extra])
                    _PG_TELEMETRY["release_orders"] += 1
                else:
                    continue
                _PG_TELEMETRY["released_units"] += extra
        if held_any:
            _PG_TELEMETRY["held_steps"] += 1
        action["market"] = market
        return action
    except Exception:
        _PG_TELEMETRY["errors"] += 1
        return action


agent.telemetry = {**(getattr(_PG_PARENT, "telemetry", {}) or {}), "price_gate": _PG_TELEMETRY}
kaggle_agent = agent
'''

GATES = {
    "gate_35_70": {"low": 0.35, "high": 0.70},
    "gate_50_80": {"low": 0.50, "high": 0.80},
}
GATE_DEFAULTS = {"items": ("WOOL", "MILK", "STRAWBERRY", "MELON"), "hold_max_shed": 60, "last_hold_step": 647}


LEAD_WRAPPER = '''

# ---------------------------------------------------------------- premium lead
# V43's sell_lead posts next step's lots one step early; a V43-lineage opponent
# does the same, so both sell the same premium item in the same slot and share
# every price tick. Selling the lot the tape schedules `lookahead` steps ahead
# puts us alone in front of any clone, and costs nothing against anyone else.
# Reads the live route from the chassis; parent orders keep their slots.
_PL_CFG = @@CFG@@
_PL_PARENT = agent
_PL_TELEMETRY = {"steps": 0, "led_units": 0, "led_steps": 0, "no_route": 0, "errors": 0}


def _pl_get(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def agent(observation, configuration=None):
    action = _PL_PARENT(observation, configuration)
    try:
        _PL_TELEMETRY["steps"] += 1
        step = int(_pl_get(observation, "step", -1))
        target = step + _PL_CFG["lookahead"]
        if step < 0 or target > 718:
            return action
        seat = int(_pl_get(observation, "player", 0) or 0)
        chassis = _IMPL.chassis
        st = chassis.players.get(seat) or {}
        tape = chassis.routes.get(st.get("route"))
        if not tape or target >= len(tape) or not isinstance(tape[target], dict):
            _PL_TELEMETRY["no_route"] += 1
            return action
        shed = dict(_pl_get(_pl_get(observation, "private", {}) or {}, "shed", {}) or {})
        prices = dict(_pl_get(_pl_get(observation, "market", {}) or {}, "prices", {}) or {})
        market = [list(o) for o in (action.get("market") or []) if o][:10]
        planned_now = {}
        for o in market:
            if o[0] == "SELL" and len(o) >= 3:
                planned_now[o[1]] = planned_now.get(o[1], 0) + max(0, int(o[2]))
        future = {}
        for o in tape[target].get("market") or []:
            if o and o[0] == "SELL" and len(o) >= 3 and o[1] in _PL_CFG["items"]:
                future[o[1]] = future.get(o[1], 0) + max(0, int(o[2]))
        led = False
        for item, fut_qty in future.items():
            have = int(shed.get(item, 0) or 0) - planned_now.get(item, 0)
            qty = min(have, fut_qty)
            if qty <= 0 or int(prices.get(item, 0) or 0) < _PL_CFG["min_price"]:
                continue
            merged = False
            for o in market:
                if o[0] == "SELL" and len(o) >= 3 and o[1] == item:
                    o[2] = max(0, int(o[2])) + qty
                    merged = True
                    break
            if not merged:
                if len(market) >= 10:
                    continue
                market.append(["SELL", item, qty])
            _PL_TELEMETRY["led_units"] += qty
            led = True
        if led:
            _PL_TELEMETRY["led_steps"] += 1
        action["market"] = market
        return action
    except Exception:
        _PL_TELEMETRY["errors"] += 1
        return action


agent.telemetry = {**(getattr(_PL_PARENT, "telemetry", {}) or {}), "premium_lead": _PL_TELEMETRY}
kaggle_agent = agent
'''

LEADS = {
    "lead2": {"lookahead": 2},
    "lead3": {"lookahead": 3},
}
LEAD_DEFAULTS = {"items": ("WOOL", "MILK", "STRAWBERRY", "MELON"), "min_price": 2}


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
    for name, cfg in GATES.items():
        full = {**GATE_DEFAULTS, **cfg}
        out = OUT_DIR / f"{name}.py"
        out.write_text(source.rstrip() + "\n" + GATE_WRAPPER.replace("@@CFG@@", repr(full)))
        receipt["variants"][name] = {"path": str(out), "cfg": full,
                                     "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}
        print(name, out, receipt["variants"][name]["sha256"][:12])
    for name, cfg in LEADS.items():
        full = {**LEAD_DEFAULTS, **cfg}
        out = OUT_DIR / f"{name}.py"
        out.write_text(source.rstrip() + "\n" + LEAD_WRAPPER.replace("@@CFG@@", repr(full)))
        receipt["variants"][name] = {"path": str(out), "cfg": full,
                                     "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}
        print(name, out, receipt["variants"][name]["sha256"][:12])
    (ROOT / "experiments" / "v43_market_layers_build.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
