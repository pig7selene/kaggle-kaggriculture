"""One extra hand a day whose only job is to fertilize the tape's wheat.

Every strong V43 fork fertilizes far more than the tape (Driz Lo 147 times a
game to the tape's 91) and it is the one edit they all share. The tape leaves
115 of its 148 wheat harvests unfertilized at a mean yield of 3.7 of 6; in the
yield window each watering adds one unit, or two when fertilized, so a
fertilized tile gives about two more wheat. Fertilizer itself is nearly free:
the two V43s glut it to $1-3 by mid-game. Inserting FERTILIZE into the tape's
own unit routes is not possible -- a unit stands on young wheat with fertilizer
in hand and a spare step only five times a game -- so this layer hires one more
hand after the tape's hires, buys the day's fertilizer, has the hand pick it up
at the shed where it spawns, and walks it round the unfertilized wheat tiles
aged one to three days, nearest first. Nothing on the tape changes, and since
FERTILIZE does not alter tile occupancy the shared weed RNG -- and so the town
-- is the same as without the layer.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VD = Path("/private/tmp/kaggriculture_v43_variants")

WRAPPER = '''

# ---------------------------------------------------------------- fertilizer hand
_FH_CFG = @@CFG@@
_FH_PARENT = agent
_FH_STATE = {}
_FH_TELEMETRY = {"steps": 0, "hires": 0, "hire_cost": 0, "bought": 0, "picked": 0, "fertilized": 0,
                 "no_targets_days": 0, "idle": 0, "errors": 0, "hire_hours": {}}
_FH_ACCESS = [(4, 4), (5, 4), (4, 5), (5, 5)]
_FH_FIB = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610]


def _fh_get(o, k, d=None):
    return o.get(k, d) if isinstance(o, dict) else getattr(o, k, d)


def _fh_toward(pos, tgt):
    dx, dy = tgt[0] - pos[0], tgt[1] - pos[1]
    if dx == 0 and dy == 0:
        return None
    if abs(dx) >= abs(dy):
        return "EAST" if dx > 0 else "WEST"
    return "SOUTH" if dy > 0 else "NORTH"


def _fh_last_hire_hour(seat, day):
    try:
        ch = _IMPL.chassis
        route = (ch.players.get(seat) or {}).get("route")
        tape = ch.routes.get(route)
        last = -1
        for h in range(24):
            idx = day * 24 + h
            a = tape[idx] if idx < len(tape) else None
            if isinstance(a, dict) and any(o and o[0] == "HIRE" for o in (a.get("market") or [])):
                last = h
        return last
    except Exception:
        return 6


def _fh_state(seat, step):
    st = _FH_STATE.get(seat)
    if st is None or step < st["last_step"]:
        st = {"last_step": step, "hire_day": -1, "hire_hour": None, "base_hands": None, "done": set()}
        _FH_STATE[seat] = st
    st["last_step"] = step
    return st


def _fh_targets(tiles, day, hour, prices):
    """Jobs for the hand today: (x, y, kind, priority). kind is FERT or WATER."""
    out = []
    fert_price = int(prices.get("FERTILIZER", 100) or 100)
    for y, row in enumerate(tiles):
        for x, t in enumerate(row):
            if not isinstance(t, dict) or t.get("kind") != "PLANT":
                continue
            crop = t.get("crop")
            age = day - int(t.get("planted_day", day))
            unfert = int(t.get("fertilized_until_day", -1)) < day
            if unfert and crop in _FH_CFG["crops"] and age in _FH_CFG["ages"] and fert_price <= _FH_CFG["fert_max_price"]:
                out.append((x, y, "FERT", {2: 0, 1: 1, 3: 2}.get(age, 3)))
            if unfert and crop == "STRAWBERRY" and _FH_CFG["straw_days"] and day in _FH_CFG["straw_days"] \
                    and fert_price <= _FH_CFG["straw_max_price"] and (t.get("watered_today") or hour < 12):
                out.append((x, y, "FERT", -1))
            if hour >= _FH_CFG["water_from_hour"] and not t.get("watered_today") and crop in ("WHEAT", "CARROT"):
                w0 = 2 if crop == "WHEAT" else 2
                w1 = 4 if crop == "WHEAT" else 3
                if w0 <= age <= w1:
                    out.append((x, y, "WATER", 5))
    return out


def agent(observation, configuration=None):
    action = _FH_PARENT(observation, configuration)
    try:
        _FH_TELEMETRY["steps"] += 1
        step = int(_fh_get(observation, "step", -1))
        seat = int(_fh_get(observation, "player", 0) or 0)
        st = _fh_state(seat, step)
        day, hour = step // 24, step % 24
        if step < _FH_CFG["from_step"] or day > _FH_CFG["last_day"]:
            return action
        farm = _fh_get(observation, "farms", [])[seat]
        money = float(_fh_get(farm, "money", 0) or 0)
        tiles = _fh_get(farm, "tiles")
        hands = [tuple(h) for h in (_fh_get(farm, "hands", []) or [])]
        hires_today = int(_fh_get(farm, "hires_today", 0) or 0)
        private = _fh_get(observation, "private", {}) or {}
        shed = dict(_fh_get(private, "shed", {}) or {})
        invs = list(_fh_get(private, "inventories", []) or [])
        prices = dict(_fh_get(_fh_get(observation, "market", {}) or {}, "prices", {}) or {})
        market = [list(o) for o in (action.get("market") or []) if o]
        front = []

        if st["hire_day"] != day:
            st["hire_hour"] = _fh_last_hire_hour(seat, day) + 1
        targets = _fh_targets(tiles, day, hour, prices)
        fert_jobs = [t for t in targets if t[2] == "FERT"]
        if hour == st["hire_hour"] and st["hire_day"] != day:
            st["hire_day"] = day
            st["done"] = set()
            n_pending = sum(1 for o in market if o[0] == "HIRE")
            cost = _FH_FIB[min(hires_today + n_pending, len(_FH_FIB) - 1)]
            fert_price = int(prices.get("FERTILIZER", 100) or 100)
            # expected jobs: fertilizations now, plus late waterings if enabled (about 3 a day)
            expect = len(fert_jobs) + (3 if _FH_CFG["water_from_hour"] < 24 else 0)
            need = max(0, len(fert_jobs) - int(shed.get("FERTILIZER", 0) or 0))
            if expect >= _FH_CFG["min_jobs"] and money >= cost + need * fert_price + _FH_CFG["reserve"] and cost <= _FH_CFG["max_hire_cost"]:
                st["base_hands"] = len(hands) + n_pending
                front.append(["HIRE"])
                if need > 0:
                    front.append(["BUY_PRODUCT", "FERTILIZER", need])
                    _FH_TELEMETRY["bought"] += need
                _FH_TELEMETRY["hires"] += 1
                _FH_TELEMETRY["hire_cost"] += cost
                hh = str(st["hire_hour"])
                _FH_TELEMETRY["hire_hours"][hh] = _FH_TELEMETRY["hire_hours"].get(hh, 0) + 1
            else:
                st["base_hands"] = None
                if expect < _FH_CFG["min_jobs"]:
                    _FH_TELEMETRY["no_targets_days"] += 1
        if st["base_hands"] is not None and st["hire_day"] == day and hour > st["hire_hour"]:
            i = st["base_hands"]
            if i < len(hands):
                pos = hands[i]
                inv = invs[i + 1] if i + 1 < len(invs) else {}
                carrying = int(inv.get("FERTILIZER", 0) or 0)
                hand_actions = list(action.get("hands") or [])
                while len(hand_actions) < len(hands):
                    hand_actions.append(["PASS"])
                act = None
                todo = [t for t in targets if (t[0], t[1], t[2]) not in st["done"]]
                fert_todo = [t for t in todo if t[2] == "FERT"]
                water_todo = [t for t in todo if t[2] == "WATER"]
                here_f = [t for t in fert_todo if (t[0], t[1]) == pos]
                here_w = [t for t in water_todo if (t[0], t[1]) == pos]
                if here_f and carrying > 0:
                    act = ["FERTILIZE"]
                    st["done"].add((pos[0], pos[1], "FERT"))
                    _FH_TELEMETRY["fertilized"] += 1
                elif here_w:
                    act = ["WATER"]
                    st["done"].add((pos[0], pos[1], "WATER"))
                    _FH_TELEMETRY["watered"] = _FH_TELEMETRY.get("watered", 0) + 1
                elif fert_todo and carrying == 0 and int(shed.get("FERTILIZER", 0) or 0) > 0:
                    if pos in _FH_ACCESS:
                        k = min(int(shed.get("FERTILIZER", 0) or 0), len(fert_todo))
                        act = ["PICKUP", "FERTILIZER", k]
                        _FH_TELEMETRY["picked"] += k
                    else:
                        tgt = min(_FH_ACCESS, key=lambda a: abs(a[0] - pos[0]) + abs(a[1] - pos[1]))
                        act = [_fh_toward(pos, tgt)]
                else:
                    cand = (fert_todo if carrying > 0 else []) + water_todo
                    if cand:
                        tgt = min(cand, key=lambda t: (t[3], abs(t[0] - pos[0]) + abs(t[1] - pos[1])))
                        act = [_fh_toward(pos, (tgt[0], tgt[1]))]
                if act is None or act == [None]:
                    act = ["PASS"]
                    _FH_TELEMETRY["idle"] += 1
                hand_actions[i] = act
                action["hands"] = hand_actions
        if front:
            action["market"] = (front + market)[:10]
        return action
    except Exception:
        _FH_TELEMETRY["errors"] += 1
        return action


agent.telemetry = {**(getattr(_FH_PARENT, "telemetry", {}) or {}), "fert_hand": _FH_TELEMETRY}
kaggle_agent = agent
'''

BASE = {"from_step": 144, "last_day": 27, "reserve": 500, "max_hire_cost": 233, "crops": ("WHEAT",), "ages": (1, 2, 3),
        "fert_max_price": 30, "straw_days": (), "straw_max_price": 0, "water_from_hour": 24, "min_jobs": 3}
VARIANTS = {
    "fh_cheap30": dict(BASE),
    "fh_cheap30_water": {**BASE, "water_from_hour": 17},
    "fh_cheap45_water": {**BASE, "fert_max_price": 45, "water_from_hour": 17},
    "fh_straw": {**BASE, "fert_max_price": 0, "straw_days": tuple(range(14, 21)), "straw_max_price": 95},
    "fh_straw_cheap30": {**BASE, "straw_days": tuple(range(14, 21)), "straw_max_price": 95},
}

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="lead5")
    a = ap.parse_args()
    src = (VD / f"{a.base}.py").read_text().rstrip()
    receipt = {}
    for name, cfg in VARIANTS.items():
        out = VD / f"{a.base}_{name}.py"
        out.write_text(src + "\n" + WRAPPER.replace("@@CFG@@", repr(cfg)))
        receipt[out.stem] = {"base": a.base, "cfg": cfg, "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}
        print("built", out.name)
    (ROOT / "experiments" / "v43_fert_hand_build.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
