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
    "lead4": {"lookahead": 4},
    "lead5": {"lookahead": 5},
    "lead6": {"lookahead": 6},
    "lead8": {"lookahead": 8},
}
LEAD_DEFAULTS = {"items": ("WOOL", "MILK", "STRAWBERRY", "MELON"), "min_price": 2}


ADAPT_WRAPPER = '''

# ---------------------------------------------------------------- adaptive lead
# Against the V43 clone, selling the premium lots the tape schedules five steps
# ahead wins the price race (+1,557 / +1,713 in direct matches). Against an
# opponent that is not racing us for the same lots it costs about 220 a game:
# the town's consumption would have lifted the price in those five steps. So
# the lead is switched on only when the opponent's observed premium sales line
# up with our own tape's lots -- the signature of a V43-lineage agent.
#
# Observation: inventory[t+1] - inventory[t] = our fills + their fills -
# consumption, for units above the $1 floor. Our fills follow from the action
# we return and the chassis's projected shed; consumption from the shop list.
import math as _ad_math
_AD_CFG = @@CFG@@
_AD_PARAMS = {
    "WHEAT": (25, 400, "sqrt", 0.80, "log", 0.20), "CARROT": (35, 450, "log", 0.20, "sqrt", 0.70),
    "TOMATO": (60, 200, "linear", 0.40, "sqrt", 0.60), "STRAWBERRY": (120, 100, "sqrt", 0.70, "linear", 1.60),
    "MELON": (250, 300, "log", 0.20, "sq", 3.60), "EGG": (50, 332, "linear", 0.40, "log", 0.20),
    "MILK": (160, 122, "sqrt", 0.60, "linear", 1.60), "WOOL": (200, 105, "log", 0.20, "sq", 3.20),
    "FERTILIZER": (100, 200, "linear", 0.40, "linear", 0.40)}
_AD_PRODUCTS = tuple(_AD_PARAMS)
_AD_SHOPS = {"BAKERY": ("EGG", "WHEAT"), "PIZZA_SHOP": ("MILK", "TOMATO", "WHEAT"),
             "BRUNCH_SPOT": ("EGG", "WHEAT", "STRAWBERRY"), "YARN_STORE": ("WOOL",),
             "ICE_CREAM_SHOP": ("STRAWBERRY", "MILK", "WHEAT"), "PET_CAFE": ("CARROT",),
             "SMOOTHIE_SHOP": ("STRAWBERRY", "MILK"), "FARMERS_MARKET": ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY")}
_AD_PARENT = agent
_AD_STATE = {}
_AD_TELEMETRY = {"steps": 0, "clone_steps": 0, "other_steps": 0, "led_units": 0, "led_steps": 0,
                 "obs_sales": 0, "matches": 0, "errors": 0, "final_score": None, "first_clone_step": None}


def _ad_shape(f, x):
    x = max(0.0, x)
    if f == "linear": return x
    if f == "sq": return x * x
    if f == "sqrt": return _ad_math.sqrt(x)
    if f == "log": return _ad_math.log(1.0 + x)
    return x


def _ad_price(item, inv):
    base, T, bf, bt, af, at = _AD_PARAMS[item]
    if inv < 10000:
        price = base + bt * base / _ad_shape(bf, T) * _ad_shape(bf, 10000 - inv)
    else:
        price = base - at * base / _ad_shape(af, T) * _ad_shape(af, inv - 10000)
    return max(1, int(round(price)))


def _ad_get(o, k, d=None):
    return o.get(k, d) if isinstance(o, dict) else getattr(o, k, d)


def _ad_consumption(step, shops):
    c = {}
    if step % 4 == 0:
        for sh in shops:
            prods = _AD_SHOPS.get(sh, ())
            m = 2 if len(prods) == 1 else 1
            for it in prods:
                c[it] = c.get(it, 0) + m
    if step % 24 == 0:
        for it in _AD_PRODUCTS:
            if it != "FERTILIZER":
                c[it] = c.get(it, 0) + 1
    return c


def _ad_tape_sells(tape, t, item):
    if not (0 <= t < len(tape)) or not isinstance(tape[t], dict):
        return False
    for o in tape[t].get("market") or []:
        if o and o[0] == "SELL" and len(o) >= 3 and o[1] == item and int(o[2]) > 0:
            return True
    return False


def agent(observation, configuration=None):
    action = _AD_PARENT(observation, configuration)
    try:
        _AD_TELEMETRY["steps"] += 1
        step = int(_ad_get(observation, "step", -1))
        seat = int(_ad_get(observation, "player", 0) or 0)
        if step == 0:
            _AD_STATE.pop(seat, None)
        st = _AD_STATE.setdefault(seat, {"prev": None, "n": 0, "matches": 0})
        inv = dict(_ad_get(_ad_get(observation, "market", {}) or {}, "inventory", {}) or {})
        prices = dict(_ad_get(_ad_get(observation, "market", {}) or {}, "prices", {}) or {})
        shops = list(_ad_get(_ad_get(observation, "town", {}) or {}, "unlocked_shops", []) or [])
        shed = dict(_ad_get(_ad_get(observation, "private", {}) or {}, "shed", {}) or {})
        chassis = _IMPL.chassis
        tape = chassis.routes.get((chassis.players.get(seat) or {}).get("route"))
        market = [list(o) for o in (action.get("market") or []) if o][:10]
        # the parent's own SELL items this step (any quantity: clamped and suppressed
        # orders stay as placeholders) -- a V43-lineage opponent sells the same set
        ref_now = {o[1] for o in market if o[0] == "SELL" and len(o) >= 3}
        st.setdefault("last_led", {})
        # 1. finalize last step's inference: what did the opponent sell, and did it
        #    match what our own chassis was selling at that step?
        prev = st["prev"]
        if prev is not None and prev["step"] == step - 1:
            cons = _ad_consumption(step - 1, prev["shops"])
            for it in _AD_CFG["classify_items"]:
                est = (inv.get(it, 0) - prev["inv"].get(it, 0)) + cons.get(it, 0) - prev["our"].get(it, 0)
                if est >= 1:
                    _AD_TELEMETRY["obs_sales"] += 1
                    # our own recent lead of this item distorts the reference; skip.
                    # The first hours of a day are everyone's post-deposit dump and
                    # carry no signature; skip those too.
                    if step - 1 - st["last_led"].get(it, -99) <= _AD_CFG["led_blackout"]:
                        continue
                    if (step - 1) % 72 <= _AD_CFG["skip_hours"]:
                        continue
                    st["n"] += 1
                    if it in prev["ref"]:
                        st["matches"] += 1
                        _AD_TELEMETRY["matches"] += 1
        # 2. mode with hysteresis: lineage opponent racing our lots, or not
        score = st["matches"] / st["n"] if st["n"] else None
        if st["n"] >= _AD_CFG["min_obs"]:
            if not st.get("clone") and score >= _AD_CFG["enter"]:
                st["clone"] = True
            elif st.get("clone") and score < _AD_CFG["exit"]:
                st["clone"] = False
        clone = bool(st.get("clone"))
        _AD_TELEMETRY["final_score"] = score
        if clone:
            _AD_TELEMETRY["clone_steps"] += 1
            if _AD_TELEMETRY["first_clone_step"] is None:
                _AD_TELEMETRY["first_clone_step"] = step
            target = step + _AD_CFG["lookahead"]
            if tape and target <= 718 and target < len(tape) and isinstance(tape[target], dict):
                planned_now = {}
                for o in market:
                    if o[0] == "SELL" and len(o) >= 3:
                        planned_now[o[1]] = planned_now.get(o[1], 0) + max(0, int(o[2]))
                future = {}
                for o in tape[target].get("market") or []:
                    if o and o[0] == "SELL" and len(o) >= 3 and o[1] in _AD_CFG["items"]:
                        future[o[1]] = future.get(o[1], 0) + max(0, int(o[2]))
                led = False
                for item, fut_qty in future.items():
                    have = int(shed.get(item, 0) or 0) - planned_now.get(item, 0)
                    qty = min(have, fut_qty)
                    if qty <= 0 or int(prices.get(item, 0) or 0) < _AD_CFG["min_price"]:
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
                    _AD_TELEMETRY["led_units"] += qty
                    st["last_led"][item] = step
                    led = True
                if led:
                    _AD_TELEMETRY["led_steps"] += 1
        else:
            _AD_TELEMETRY["other_steps"] += 1
        action["market"] = market
        # 3. our own non-floor fills from the action we are about to return
        view = _View(observation, seat, chassis.cfg)
        projected = dict(chassis._projected_shed(action, view))
        our = {}
        for o in market:
            if o[0] == "SELL" and len(o) >= 3:
                have = max(0, projected.get(o[1], 0))
                n = max(0, min(int(o[2]), have))
                projected[o[1]] = have - n
                start = inv.get(o[1], 0) + our.get(o[1], 0)
                nonfloor = 0
                for k in range(n):
                    if _ad_price(o[1], start + k) > 1:
                        nonfloor += 1
                    else:
                        break
                our[o[1]] = our.get(o[1], 0) + nonfloor
            elif o[0] in ("BUY_PRODUCT", "BUY_ANIMAL") and len(o) >= 3:
                projected[o[1]] = projected.get(o[1], 0) + int(o[2])
        st["prev"] = {"step": step, "inv": inv, "shops": shops, "our": our, "ref": ref_now}
        return action
    except Exception:
        _AD_TELEMETRY["errors"] += 1
        return action


agent.telemetry = {**(getattr(_AD_PARENT, "telemetry", {}) or {}), "adaptive_lead": _AD_TELEMETRY}
kaggle_agent = agent
'''

ADAPTS = {
    "adapt5": {"lookahead": 5, "items": ("WOOL", "MILK", "STRAWBERRY", "MELON"), "min_price": 2,
               "classify_items": ("WOOL", "MILK", "STRAWBERRY", "MELON", "EGG", "CARROT", "TOMATO"),
               "min_obs": 20, "enter": 0.85, "exit": 0.70, "led_blackout": 6, "skip_hours": 1},
}


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
    for name, cfg in ADAPTS.items():
        out = OUT_DIR / f"{name}.py"
        out.write_text(source.rstrip() + "\n" + ADAPT_WRAPPER.replace("@@CFG@@", repr(cfg)))
        receipt["variants"][name] = {"path": str(out), "cfg": cfg,
                                     "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}
        print(name, out, receipt["variants"][name]["sha256"][:12])
    (ROOT / "experiments" / "v43_market_layers_build.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
