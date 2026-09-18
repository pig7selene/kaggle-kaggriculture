"""Keep sheep instead of geese where the town pays for wool.

Two clones of the same public chassis met in a yarn town and the whole result
was one decision: the opponent ran eight cows and nine sheep on nineteen
pastures, we ran eight cows, six sheep and three geese on fourteen pastures and
five coops. Feeding, care and harvests were identical to the step. They sold 160
wool to our 96 at the same $233 a unit, worth +14,897; our 75 eggs at $51 came
to +3,822. The game ended -10,326.

Wool only holds that price where a yarn store keeps consuming it -- in other
towns it collapses to a few dollars and eggs are the better animal. So this
swaps the tape's geese for sheep, and its coops for pastures, only when the
town has a yarn store and the board actually prices wool far above eggs. A coop
and a pasture occupy a tile the same way, so the empty-tile count, and with it
the shared weed draw and the shop schedule, are untouched. A sheep costs 500
against a goose's 300, so the gate also needs the money to be there.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VD = Path("/private/tmp/kaggriculture_v43_variants")

WRAPPER = '''

# ---------------------------------------------------------------- herd swap
_HS_CFG = @@CFG@@
_HS_PARENT = agent
_HS_STATE = {}
_HS_TELEMETRY = {"steps": 0, "active_games": 0, "buy_swapped": 0, "place_swapped": 0,
                 "pickup_swapped": 0, "build_swapped": 0, "errors": 0, "reason": ""}


def _hs_get(o, k, d=None):
    return o.get(k, d) if isinstance(o, dict) else getattr(o, k, d)


def _hs_should(observation, seat, step):
    """Judge at the moment the decision is taken, not earlier.

    Shops unlock one every three days, so at step 144 the yarn store that makes
    wool worth $233 has usually not appeared yet; the tape buys its geese and
    builds its coops around steps 240 to 275, which is when the town is known.
    Once a swap has been made the answer is held, so a game never ends up half
    swapped.
    """
    st = _HS_STATE.get(seat)
    if st is not None and st.get("locked"):
        return st["on"]
    shops = list(_hs_get(_hs_get(observation, "town", {}) or {}, "unlocked_shops", []) or [])
    prices = dict(_hs_get(_hs_get(observation, "market", {}) or {}, "prices", {}) or {})
    yarn = sum(1 for s in shops if s == "YARN_STORE")
    wool = int(prices.get("WOOL", 0) or 0)
    egg = int(prices.get("EGG", 0) or 0)
    if _HS_CFG["mode"] == "sheep_to_cow":
        # Every top team ends a yarn-free town with no sheep at all, and wool
        # there ends at $1-5 because nothing consumes it. The decision cannot
        # wait for that price: the tape buys its sheep around steps 196 to 226,
        # when wool is still near its $200 base and only three of the eight
        # shops have opened. So judge on the shops actually revealed -- no yarn
        # store among them is the best evidence available at the time -- and
        # unlike the reverse swap this does not depend on the rival, since the
        # price is set by the town's demand rather than by our supply.
        on = yarn <= _HS_CFG["max_yarn"] and len(shops) >= _HS_CFG["min_shops"]
    else:
        on = yarn >= _HS_CFG["min_yarn"] and wool >= _HS_CFG["min_wool"] and wool >= _HS_CFG["ratio"] * max(1, egg)
    _HS_STATE[seat] = {"on": on, "locked": False, "why": f"yarn={yarn} wool={wool} egg={egg} step={step}"}
    return on


def agent(observation, configuration=None):
    action = _HS_PARENT(observation, configuration)
    try:
        _HS_TELEMETRY["steps"] += 1
        step = int(_hs_get(observation, "step", -1))
        seat = int(_hs_get(observation, "player", 0) or 0)
        if step == 0:
            _HS_STATE.pop(seat, None)
        if step < _HS_CFG["from_step"]:
            return action
        if not _hs_should(observation, seat, step):
            return action
        farm = _hs_get(observation, "farms", [])[seat]
        money = float(_hs_get(farm, "money", 0) or 0)
        private = _hs_get(observation, "private", {}) or {}
        shed = dict(_hs_get(private, "shed", {}) or {})
        market = []
        for o in (action.get("market") or []):
            if not o:
                continue
            o = list(o)
            if _HS_CFG["mode"] == "sheep_to_cow" and o[0] == "BUY_ANIMAL" and len(o) >= 3 and o[1] == "SHEEP":
                n = max(0, int(o[2]))
                st = _HS_STATE.get(seat) or {}
                # a cow is 400 against a sheep's 500, so this never costs more
                o = ["BUY_ANIMAL", _HS_CFG["into"], n]
                _HS_TELEMETRY["buy_swapped"] += n
                if not st.get("locked"):
                    st["locked"] = True
                    _HS_STATE[seat] = st
                    _HS_TELEMETRY["active_games"] += 1
                    _HS_TELEMETRY["reason"] = st.get("why", "")
                market.append(o)
                continue
            if _HS_CFG["mode"] == "goose_to_sheep" and o[0] == "BUY_ANIMAL" and len(o) >= 3 and o[1] == "GOOSE":
                n = max(0, int(o[2]))
                st = _HS_STATE.get(seat) or {}
                # All or nothing. A half-swapped herd is strictly worse than
                # either plan: the geese we no longer buy still have PLACE
                # actions waiting for them, those fail, and the farm ends three
                # animals short. Once the first purchase is swapped the game is
                # committed, and the rest follow regardless of the cash gate.
                if st.get("locked") or money >= 500 * n + _HS_CFG["reserve"]:
                    o = ["BUY_ANIMAL", "SHEEP", n]
                    _HS_TELEMETRY["buy_swapped"] += n
                    if not st.get("locked"):
                        st["locked"] = True
                        _HS_STATE[seat] = st
                        _HS_TELEMETRY["active_games"] += 1
                        _HS_TELEMETRY["reason"] = st.get("why", "")
                else:
                    # cannot fund the first swap: abandon the idea for this game
                    st["on"] = False
                    st["locked"] = True
                    _HS_STATE[seat] = st
            market.append(o)
        action["market"] = market
        units = [action.get("farmer") or ["PASS"]] + list(action.get("hands") or [])
        have_goose = int(shed.get("GOOSE", 0) or 0)
        for i, u in enumerate(units):
            if not u:
                continue
            if _HS_CFG["mode"] == "goose_to_sheep" and u[0] == "BUILD_COOP" and _HS_STATE.get(seat, {}).get("locked"):
                units[i] = ["BUILD_PASTURE"]
                _HS_TELEMETRY["build_swapped"] += 1
            elif _HS_CFG["mode"] == "sheep_to_cow" and u[0] in ("PICKUP", "PLACE") and len(u) >= 2 and u[1] == "SHEEP":
                if _HS_STATE.get(seat, {}).get("locked") and int(shed.get("SHEEP", 0) or 0) <= 0:
                    units[i] = [u[0], _HS_CFG["into"]] + list(u[2:])
                    _HS_TELEMETRY["pickup_swapped" if u[0] == "PICKUP" else "place_swapped"] += 1
            elif _HS_CFG["mode"] == "goose_to_sheep" and u[0] in ("PICKUP", "PLACE") and len(u) >= 2 and u[1] == "GOOSE":
                if _HS_STATE.get(seat, {}).get("locked") and have_goose <= 0:
                    units[i] = [u[0], "SHEEP"] + list(u[2:])
                    _HS_TELEMETRY["pickup_swapped" if u[0] == "PICKUP" else "place_swapped"] += 1
        action["farmer"] = units[0]
        action["hands"] = units[1:]
        return action
    except Exception:
        _HS_TELEMETRY["errors"] += 1
        return action


agent.telemetry = {**(getattr(_HS_PARENT, "telemetry", {}) or {}), "herd_swap": _HS_TELEMETRY}
kaggle_agent = agent
'''

DEFAULTS = {"from_step": 144, "mode": "goose_to_sheep", "min_yarn": 1, "min_wool": 150,
            "ratio": 2.5, "reserve": 1500, "max_yarn": 0, "max_wool": 40, "into": "COW", "min_shops": 3}
VARIANTS = {
    "sc_cow": {**DEFAULTS, "mode": "sheep_to_cow", "into": "COW", "min_shops": 3},
    "sc_goose": {**DEFAULTS, "mode": "sheep_to_cow", "into": "GOOSE", "min_shops": 3},
    "sc_cow_s4": {**DEFAULTS, "mode": "sheep_to_cow", "into": "COW", "min_shops": 4},
    "hs_y1": {**DEFAULTS},
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
    (ROOT / "experiments" / "v43_herd_swap_build.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
