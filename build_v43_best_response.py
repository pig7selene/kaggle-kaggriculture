"""Sell against the opponent we can actually predict, instead of a fixed lead.

Three quarters of our online opponents are the shipped V43 notebook, whose tape,
router and layers we hold, and whose fills we can infer from the market: the
inventory an observation reports moves by our fills plus theirs minus the town's
consumption, and reading it back recovered their premium fills to 24 units in
654. The market itself is a known deterministic function -- price depends on
inventory alone, the town consumes on a fixed schedule, and orders are matched
unit by unit against a shared book.

So the quantity to sell this step is not a guess. For each product, project the
inventory over the next day: the opponent's scheduled lots (their route, taken
from the first two shops, plus the one-step lead their sell_lead applies), the
town's consumption every four steps, and our own tape's plan. Then pick, among
a small set of candidate quantities, the one maximising our revenue minus
theirs over that horizon, subject to the shed and the ten-order cap.

The five-step lead is one constant approximation of this, and it is worth
+2,597 against shipped; the two mistakes of the earlier planner are fixed here,
which were that it had no opponent term at all and that it treated a day as 72
steps rather than 24, so its horizon spanned three days and it starved the shed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VD = Path("/private/tmp/kaggriculture_v43_variants")

WRAPPER = '''

# ---------------------------------------------------------------- best response
import math as _br_math
_BR_CFG = @@CFG@@
_BR_P = {"WHEAT": (25, 400, "sqrt", 0.80, "log", 0.20), "CARROT": (35, 450, "hinge", 1.00, "sqrt", 0.70),
         "TOMATO": (60, 200, "hinge", 0.40, "sqrt", 0.60), "STRAWBERRY": (120, 100, "sqrt", 0.70, "linear", 1.60),
         "MELON": (250, 300, "log", 0.20, "sq", 3.60), "EGG": (50, 332, "hinge", 0.40, "log", 0.20),
         "MILK": (160, 122, "sqrt", 0.60, "linear", 1.60), "WOOL": (200, 105, "log", 0.20, "sq", 3.20),
         "FERTILIZER": (100, 200, "linear", 0.40, "linear", 0.40)}
_BR_ITEMS = _BR_CFG["items"]
_BR_SHOPS = {"BAKERY": ("EGG", "WHEAT"), "PIZZA_SHOP": ("MILK", "TOMATO", "WHEAT"),
             "BRUNCH_SPOT": ("EGG", "WHEAT", "STRAWBERRY"), "YARN_STORE": ("WOOL",),
             "ICE_CREAM_SHOP": ("STRAWBERRY", "MILK", "WHEAT"), "PET_CAFE": ("CARROT",),
             "SMOOTHIE_SHOP": ("STRAWBERRY", "MILK"),
             "FARMERS_MARKET": ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY")}
_BR_CENTRE = tuple(k for k in _BR_P if k != "FERTILIZER")
_BR_PARENT = agent
_BR_STATE = {}
_BR_TELEMETRY = {"steps": 0, "planned": 0, "added_units": 0, "held_units": 0, "no_route": 0, "errors": 0}
_BR_HINGE = 8.0


def _br_shape(f, x, T):
    x = max(0.0, x)
    if f == "linear":
        return x
    if f == "sq":
        return x * x
    if f == "sqrt":
        return _br_math.sqrt(x)
    if f == "log":
        return _br_math.log(1.0 + x)
    if f == "hinge":
        if not T or T <= 0:
            return x
        u = x / T
        return u + _BR_HINGE * max(0.0, u - 1.0) ** 2
    return x


def _br_price(item, inv):
    base, T, bf, bt, af, at = _BR_P[item]
    if inv < 10000:
        amp = bt * base / _br_shape(bf, T, T)
        p = base + amp * _br_shape(bf, 10000 - inv, T)
    else:
        amp = at * base / _br_shape(af, T, T)
        p = base - amp * _br_shape(af, inv - 10000, T)
    return max(1, int(round(p)))


def _br_get(o, k, d=None):
    return o.get(k, d) if isinstance(o, dict) else getattr(o, k, d)


def _br_consumption(step, shops, item):
    n = 0
    if step % 4 == 0:
        for sh in shops:
            prods = _BR_SHOPS.get(sh, ())
            if item in prods:
                n += 2 if len(prods) == 1 else 1
    if step % 24 == 0 and item in _BR_CENTRE:
        n += 1
    return n


def _br_tape_sells(tape, t, item):
    if not (0 <= t < len(tape)) or not isinstance(tape[t], dict):
        return 0
    return sum(max(0, int(o[2])) for o in tape[t].get("market") or []
               if o and o[0] == "SELL" and len(o) >= 3 and o[1] == item)


def _br_value(item, inv0, ours, opp, cons, ours_now, have):
    """Our revenue minus the opponent's over the horizon when the lot sold now is
    `ours_now` instead of the tape's `ours[0]`.

    The difference is *moved*, not created: selling more now empties the shed for
    the tape's nearest later lots, which is what happens in the game, and selling
    less defers the remainder to the next one. Without that conservation every
    extra unit looks like pure gain and the optimum degenerates to emptying the
    shed each step -- the sell-on-arrival layer, already measured worse than a
    flat five-step lead.
    """
    plan = list(ours)
    plan[0] = min(ours_now, have)
    moved = plan[0] - ours[0]
    k = 1
    while moved > 0 and k < len(plan):
        take = min(moved, plan[k])
        plan[k] -= take
        moved -= take
        k += 1
    if moved < 0 and len(plan) > 1:
        plan[1] += -moved
    inv = inv0
    mine = theirs = 0.0
    for i in range(len(plan)):
        q_mine, q_opp = plan[i], opp[i]
        u = 0
        while u < q_mine or u < q_opp:
            price = _br_price(item, inv)
            if u < q_mine:
                mine += price
                if price > 1:
                    inv += 1
            if u < q_opp:
                theirs += price
                if price > 1:
                    inv += 1
            u += 1
        inv -= cons[i]
    # stock still unsold when the window closes is not worthless. Without a
    # residual the optimiser sees no value beyond the horizon and drags every
    # lot into it, which is why the longer horizon scored better.
    unsold = max(0, sum(ours) - sum(plan))
    if _BR_CFG.get("residual"):
        mine += _BR_CFG["residual"] * unsold * _br_price(item, inv)
    return mine - _BR_CFG["opp_weight"] * theirs


def agent(observation, configuration=None):
    action = _BR_PARENT(observation, configuration)
    try:
        _BR_TELEMETRY["steps"] += 1
        step = int(_br_get(observation, "step", -1))
        seat = int(_br_get(observation, "player", 0) or 0)
        if step == 0:
            _BR_STATE.pop(seat, None)
        if step < _BR_CFG["from_step"] or step > 718 - 2:
            return action
        chassis = _IMPL.chassis
        st = chassis.players.get(seat) or {}
        tape = chassis.routes.get(st.get("route"))
        if not tape:
            _BR_TELEMETRY["no_route"] += 1
            return action
        shops = list(_br_get(_br_get(observation, "town", {}) or {}, "unlocked_shops", []) or [])
        inv_all = dict(_br_get(_br_get(observation, "market", {}) or {}, "inventory", {}) or {})
        prices = dict(_br_get(_br_get(observation, "market", {}) or {}, "prices", {}) or {})
        shed = dict(_br_get(_br_get(observation, "private", {}) or {}, "shed", {}) or {})
        market = [list(o) for o in (action.get("market") or []) if o][:10]
        planned = {}
        for o in market:
            if o[0] == "SELL" and len(o) >= 3:
                planned[o[1]] = planned.get(o[1], 0) + max(0, int(o[2]))
        H = _BR_CFG["horizon"]
        changed = False
        for item in _BR_ITEMS:
            have = int(shed.get(item, 0) or 0)
            if have <= 0:
                continue
            # the opponent runs the same tape on the same town, one step ahead of
            # its own lots where sell_lead applies
            raw = [_br_tape_sells(tape, step + i, item) for i in range(H + 1)]
            cons = [_br_consumption(step + i, shops, item) for i in range(H)]
            # the opponent is shipped V43 on the same town and therefore the same
            # route, with sell_lead on: the lot due at t+1 is sold at t and
            # suppressed at t+1, never counted twice
            opp, carried = [0] * H, 0
            for i in range(H):
                t = step + i
                q = raw[i] - carried
                carried = 0
                if t % 4 != 0 and t + 1 <= 718:
                    carried = raw[i + 1]
                    q += carried
                opp[i] = max(0, q)
            ours = raw[:H]
            inv0 = int(inv_all.get(item, 10000))
            base_q = planned.get(item, 0)
            best_q, best_v = base_q, _br_value(item, inv0, ours, opp, cons, base_q, have)
            for q in range(0, have + 1, max(1, _BR_CFG["grid"])):
                if q == base_q:
                    continue
                v = _br_value(item, inv0, ours, opp, cons, q, have)
                if v > best_v + _BR_CFG["tolerance"]:
                    best_q, best_v = q, v
            if best_q == base_q or int(prices.get(item, 0) or 0) < 1:
                continue
            delta = best_q - base_q
            if delta > 0:
                _BR_TELEMETRY["added_units"] += delta
            else:
                _BR_TELEMETRY["held_units"] += -delta
            first = True
            for o in market:
                if o[0] == "SELL" and len(o) >= 3 and o[1] == item:
                    o[2] = best_q if first else 0
                    first = False
            if first and best_q > 0 and len(market) < 10:
                market.append(["SELL", item, best_q])
            changed = True
        if changed:
            _BR_TELEMETRY["planned"] += 1
        action["market"] = market[:10]
        return action
    except Exception:
        _BR_TELEMETRY["errors"] += 1
        return action


agent.telemetry = {**(getattr(_BR_PARENT, "telemetry", {}) or {}), "best_response": _BR_TELEMETRY}
kaggle_agent = agent
'''

PREM = ("WOOL", "MILK", "STRAWBERRY", "MELON")
ALL = ("WOOL", "MILK", "STRAWBERRY", "MELON", "CARROT", "EGG", "TOMATO")
BASE = {"items": PREM, "grid": 1, "tolerance": 1.0, "opp_weight": 1.0, "residual": 1.0, "from_step": 144}
VARIANTS = {
    "brr_h24": {**BASE, "horizon": 24},
    "brr_h48": {**BASE, "horizon": 48},
    "brr_h72": {**BASE, "horizon": 72},
    "brr_h48_r05": {**BASE, "horizon": 48, "residual": 0.5},
    "brr_h48_noopp": {**BASE, "horizon": 48, "opp_weight": 0.0},
    "brr_h48_all": {**BASE, "horizon": 48, "items": ALL},
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="room_plus_clamp")
    args = parser.parse_args()
    src = (VD / f"{args.base}.py").read_text().rstrip()
    receipt = {}
    for name, cfg in VARIANTS.items():
        out = VD / f"{name}.py"
        out.write_text(src + "\n" + WRAPPER.replace("@@CFG@@", repr(cfg)))
        receipt[name] = {"cfg": cfg, "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}
        print("built", out.name)
    (ROOT / "experiments" / "v43_best_response_build.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
