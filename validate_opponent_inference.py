"""Can the agent see what the opponent sells? Validate the runtime inference.

Within a step the engine runs field actions (hands DROP into the shed), then
the market, then town consumption. So

    inventory[t+1] - inventory[t] = our_fills(t) + their_fills(t) - consumption(t)

for every unit sold above the $1 floor (floor sales do not touch inventory).
Consumption is known from the shop list; our fills follow from the action we
return and the chassis's projected shed. This plays one game with a passive
wrapper that performs the inference online and scores it against the engine's
actual fills (logged by instrumenting `_commit_unit`).
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
import sys

from kaggle_environments import make
import kaggle_environments.envs.kaggriculture.kaggriculture as K

from run_route_remap_pilot import BASE, load_agent

PREM = ("WOOL", "MILK", "STRAWBERRY", "MELON")

# passive inference wrapper appended to the base agent ---------------------------
WRAPPER = '''

_OI_PRODUCTS = ("CARROT", "EGG", "FERTILIZER", "MELON", "MILK", "STRAWBERRY", "TOMATO", "WHEAT", "WOOL")
_OI_SHOPS = {"BAKERY": ["EGG", "WHEAT"], "PIZZA_SHOP": ["MILK", "TOMATO", "WHEAT"],
             "BRUNCH_SPOT": ["EGG", "WHEAT", "STRAWBERRY"], "YARN_STORE": ["WOOL"],
             "ICE_CREAM_SHOP": ["STRAWBERRY", "MILK", "WHEAT"], "PET_CAFE": ["CARROT"],
             "SMOOTHIE_SHOP": ["STRAWBERRY", "MILK"], "FARMERS_MARKET": ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY"]}
_OI_PARENT = agent
_OI_STATE = {}          # seat -> {"prev_inv", "prev_shops", "prev_step", "our_est"}
_OI_LOG = []            # (step, item, est_our_nonfloor, est_opp_nonfloor)


def _oi_get(o, k, d=None):
    return o.get(k, d) if isinstance(o, dict) else getattr(o, k, d)


def _oi_consumption(step, shops):
    c = {}
    if step % 4 == 0:
        for sh in shops:
            prods = _OI_SHOPS.get(sh, [])
            m = 2 if len(prods) == 1 else 1
            for it in prods:
                c[it] = c.get(it, 0) + m
    if step % 24 == 0:
        for it in _OI_PRODUCTS:
            if it != "FERTILIZER":
                c[it] = c.get(it, 0) + 1
    return c


def _oi_price(item, inv):
    return _IMPL.chassis.cfg and market_price(item, inv) if "market_price" in globals() else None


def agent(observation, configuration=None):
    action = _OI_PARENT(observation, configuration)
    try:
        step = int(_oi_get(observation, "step", -1))
        seat = int(_oi_get(observation, "player", 0) or 0)
        inv = dict(_oi_get(_oi_get(observation, "market", {}), "inventory", {}) or {})
        prices = dict(_oi_get(_oi_get(observation, "market", {}), "prices", {}) or {})
        shops = list(_oi_get(_oi_get(observation, "town", {}), "unlocked_shops", []) or [])
        st = _OI_STATE.get(seat)
        # finalize the previous step's inference now that we see its inventory effect
        if st is not None and st["prev_step"] == step - 1:
            cons = _oi_consumption(step - 1, st["prev_shops"])
            for it in _OI_PRODUCTS:
                delta = inv.get(it, 0) - st["prev_inv"].get(it, 0)
                est_opp = delta + cons.get(it, 0) - st["our_est"].get(it, 0)
                _OI_LOG.append((step - 1, seat, it, st["our_est"].get(it, 0), est_opp))
        # our own non-floor fills this step, from the chassis's projected shed
        view = _View(observation, seat, _IMPL.chassis.cfg)
        projected = dict(_IMPL.chassis._projected_shed(action, view))
        our = {}
        for o in action.get("market") or []:
            if not o:
                continue
            if o[0] == "SELL" and len(o) >= 3:
                have = max(0, projected.get(o[1], 0))
                n = max(0, min(int(o[2]), have))
                projected[o[1]] = have - n
                # units that sell at the floor do not move inventory
                start = inv.get(o[1], 0) + our.get(o[1], 0)
                nonfloor = 0
                for k in range(n):
                    if _MP(o[1], start + k) > 1:
                        nonfloor += 1
                    else:
                        break
                our[o[1]] = our.get(o[1], 0) + nonfloor
            elif o[0] in ("BUY_PRODUCT", "BUY_ANIMAL") and len(o) >= 3:
                projected[o[1]] = projected.get(o[1], 0) + int(o[2])
        _OI_STATE[seat] = {"prev_inv": inv, "prev_shops": shops, "prev_step": step, "our_est": our}
    except Exception as exc:
        _OI_LOG.append(("error", repr(exc)[:120]))
    return action


agent.oi_log = _OI_LOG
kaggle_agent = agent
'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--opponent", type=Path, default=BASE)
    parser.add_argument("--seed", type=int, default=4242)
    args = parser.parse_args()

    # engine instrumentation: ground-truth fills per (step, seat, item, price)
    truth = []
    cur = {"step": None, "farms": None}
    orig_pm, orig_cu = K._process_market, K._commit_unit

    def pm(state, env):
        cur["step"] = int(state[0].observation.step)
        cur["farms"] = [id(f) for f in state[0].observation.farms]
        return orig_pm(state, env)

    def cu(op, item, price, farm, private, market, shed_capacity=100):
        ok = orig_cu(op, item, price, farm, private, market, shed_capacity)
        if ok and op == "SELL":
            truth.append((cur["step"], cur["farms"].index(id(farm)), item, price))
        return ok

    K._process_market, K._commit_unit = pm, cu

    src = BASE.read_text().rstrip() + "\n" + WRAPPER
    # the wrapper needs the engine's price function; V43 defines none, so bind ours
    src = src.replace("_MP(o[1], start + k)", "_OI_MARKET_PRICE(o[1], start + k)")
    wrapped = Path("/private/tmp/kaggriculture_v43_variants/_infer_probe.py")
    wrapped.write_text(src)
    probe = load_agent(wrapped, f"probe:{args.seed}")
    import importlib
    mod = sys.modules[[k for k in sys.modules if k.startswith("remap_") and getattr(sys.modules[k], "_OI_LOG", None) is not None][-1]]
    mod._OI_MARKET_PRICE = K.market_price
    opp = load_agent(args.opponent, f"opp:{args.seed}")
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": args.seed}, debug=False)
    env.run([probe, opp])
    last = env.steps[-1]
    print(f"probe(base) vs {args.opponent.parent.name} seed {args.seed}: money {last[0]['reward']:,.0f} / {last[1]['reward']:,.0f}")

    true_nf = defaultdict(int)     # (step, seat, item) -> non-floor fills
    for s, p, it, pr in truth:
        if pr > 1:
            true_nf[(s, p, it)] += 1
    errors = [e for e in mod._OI_LOG if e[0] == "error"]
    rows = [e for e in mod._OI_LOG if e[0] != "error"]
    print(f"inference rows {len(rows)} | wrapper errors {len(errors)} {errors[:2]}")
    for label, items in (("premium", PREM), ("all", tuple(K.MARKET_PARAMS))):
        our_err = opp_err = our_tot = opp_tot = 0
        hit = miss = false = 0
        for step, seat, it, our_est, opp_est in rows:
            if it not in items:
                continue
            t_our = true_nf[(step, seat, it)]
            t_opp = true_nf[(step, 1 - seat, it)]
            our_err += abs(our_est - t_our); opp_err += abs(opp_est - t_opp)
            our_tot += t_our; opp_tot += t_opp
            if t_opp > 0 and opp_est > 0: hit += 1
            elif t_opp > 0: miss += 1
            elif opp_est > 0: false += 1
        print(f"[{label}] our fills: abs err {our_err} / {our_tot} units | opponent fills: abs err {opp_err} / {opp_tot} units | "
              f"opponent sale steps: hit {hit} miss {miss} false {false}")


if __name__ == "__main__":
    main()
