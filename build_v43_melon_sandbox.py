"""Farm the fourth quadrant with our own hands while the tape runs the other three.

The V43 tape is the same farm in every town and every product it makes is
pushed past its price cliff by the two copies of it in the game. Melons are
different: no shop buys them, no V43 sells them, and the glut curve is
quadratic, so the first hundred fetch about 210 each. A melon tile needs one
watering a day and gives six units after twelve days.

The tape never touches the south-east quadrant -- it buys two quadrants at
steps 150 and 265 and its recorded paths avoid locked land -- so that quadrant
is a sandbox. From step 266 this layer buys it, hires its own hands at hour 3
(after the tape's hour-0 and hour-1 hires, so the tape's hand indices are
untouched), plants melons on the tiles nearest the shed, waters them daily,
harvests, walks the crop to the shed and sells it the same step. After the
melon harvest a carrot goes in if there are days enough for it.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VD = Path("/private/tmp/kaggriculture_v43_variants")

WRAPPER = '''
# ---------------------------------------------------------------- melon sandbox
_MS_CFG = @@CFG@@
_MS_PARENT = agent
_MS_STATE = {}
_MS_TELEMETRY = {"steps": 0, "land": 0, "hires": 0, "seeds": 0, "planted": 0, "watered": 0, "harvested": 0,
                 "harvest_units": 0, "delivered": 0, "sold": 0, "dug": 0, "errors": 0, "idle": 0, "hire_hours": {}}
_MS_ACCESS = [(4, 4), (5, 4), (4, 5), (5, 5)]
_MS_CROP = {"MELON": {"first": 6, "last": 12, "yield": 6, "seed": 80},
            "CARROT": {"first": 2, "last": 3, "yield": 2, "seed": 20}}


def _ms_get(o, k, d=None):
    return o.get(k, d) if isinstance(o, dict) else getattr(o, k, d)


def _ms_tiles(n):
    cand = [(x, y) for y in range(5, 10) for x in range(5, 10) if (x, y) != (5, 5)]
    cand.sort(key=lambda p: (abs(p[0] - 5) + abs(p[1] - 5), p[1], p[0] if p[1] % 2 else -p[0]))
    return cand[:n]


def _ms_toward(pos, tgt):
    dx, dy = tgt[0] - pos[0], tgt[1] - pos[1]
    if dx == 0 and dy == 0:
        return None
    if abs(dx) >= abs(dy):
        return "EAST" if dx > 0 else "WEST"
    return "SOUTH" if dy > 0 else "NORTH"


def _ms_last_hire_hour(seat, day):
    # hour of the tape's last HIRE today on the route this seat plays; -1 if none
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


def _ms_state(seat, step):
    st = _MS_STATE.get(seat)
    if st is None or step < st["last_step"]:
        st = {"last_step": step, "bought": False, "active_from": None, "tiles": {}, "base_hands": None,
              "hire_day": -1, "hire_hour": None, "seed_orders": 0}
        _MS_STATE[seat] = st
    st["last_step"] = step
    return st


def agent(observation, configuration=None):
    action = _MS_PARENT(observation, configuration)
    try:
        _MS_TELEMETRY["steps"] += 1
        step = int(_ms_get(observation, "step", -1))
        seat = int(_ms_get(observation, "player", 0) or 0)
        st = _ms_state(seat, step)
        if step < _MS_CFG["buy_step"]:
            return action
        day, hour = step // 24, step % 24
        farm = _ms_get(observation, "farms", [])[seat]
        money = float(_ms_get(farm, "money", 0) or 0)
        quads = list(_ms_get(farm, "unlocked_quadrants", []) or [])
        tiles = _ms_get(farm, "tiles")
        hands = [tuple(h) for h in (_ms_get(farm, "hands", []) or [])]
        private = _ms_get(observation, "private", {}) or {}
        shed = dict(_ms_get(private, "shed", {}) or {})
        seeds = dict(_ms_get(private, "seeds", {}) or {})
        invs = list(_ms_get(private, "inventories", []) or [])
        market = [list(o) for o in (action.get("market") or []) if o]
        front = []
        n_tiles = _MS_CFG["tiles_per_hand"] * _MS_CFG["hands"]

        if len(quads) == 3 and not st["bought"] and money >= 4000 + _MS_CFG["reserve"]:
            front.append(["BUY_LAND"])
            st["bought"] = True
            _MS_TELEMETRY["land"] += 1
        if len(quads) >= 4 and st["active_from"] is None:
            st["active_from"] = step
            for p in _ms_tiles(n_tiles):
                st["tiles"][p] = {"crop": None, "planted_day": None, "watered_day": -1}
            k = min(n_tiles + 2, int(max(0, money - _MS_CFG["reserve"]) // 80))
            if k > 0:
                front.append(["BUY_SEED", "MELON", k])
                _MS_TELEMETRY["seeds"] += k
        if st["active_from"] is None:
            action["market"] = (front + market)[:10]
            return action
        days_left = 29 - day

        if st["hire_day"] != day:
            st["hire_hour"] = _ms_last_hire_hour(seat, day) + 1
        if hour == st["hire_hour"] and st["hire_day"] != day and day <= 28:
            st["base_hands"] = len(hands)
            for _ in range(_MS_CFG["hands"]):
                front.append(["HIRE"])
            st["hire_day"] = day
            _MS_TELEMETRY["hires"] += _MS_CFG["hands"]
            hh = str(st["hire_hour"])
            _MS_TELEMETRY["hire_hours"][hh] = _MS_TELEMETRY["hire_hours"].get(hh, 0) + 1
        ours = []
        if st["base_hands"] is not None and st["hire_day"] == day and hour > st["hire_hour"]:
            ours = list(range(st["base_hands"], min(len(hands), st["base_hands"] + _MS_CFG["hands"])))

        for p, t in st["tiles"].items():
            tile = tiles[p[1]][p[0]] if tiles else None
            if isinstance(tile, dict) and tile.get("kind") == "PLANT":
                if t["crop"] != tile.get("crop"):
                    t.update({"crop": tile.get("crop"), "planted_day": day})
            elif isinstance(tile, dict) and tile.get("kind") == "WEED":
                t["crop"] = "WEED"
            elif t["crop"] is not None:
                t.update({"crop": None, "planted_day": None})

        def task_for(p):
            t = st["tiles"][p]
            tile = tiles[p[1]][p[0]]
            if t["crop"] == "WEED":
                return ["DIG"], 3
            if t["crop"] is None:
                if days_left >= _MS_CROP["MELON"]["last"] + 1 and int(seeds.get("MELON", 0) or 0) > 0:
                    return ["PLANT", "MELON"], 4
                if days_left >= _MS_CROP["CARROT"]["last"] + 1 and int(seeds.get("CARROT", 0) or 0) > 0:
                    return ["PLANT", "CARROT"], 4
                return None, 9
            crop = _MS_CROP.get(t["crop"])
            if crop is None:
                return None, 9
            age = day - (t["planted_day"] if t["planted_day"] is not None else day)
            yu = int(tile.get("yield_units", 0) or 0) if isinstance(tile, dict) else 0
            # the board is the source of truth: a tile planted today already counts
            # one unwatered day and dies tonight unless watered before the day ends
            watered = bool(isinstance(tile, dict) and tile.get("watered_today")) or t["watered_day"] == day
            streak = int(tile.get("consecutive_unwatered", 0) or 0) if isinstance(tile, dict) else 0
            if yu >= crop["yield"] or (age > crop["last"] and yu > 0) or (age == crop["last"] and watered and yu > 0):
                return ["HARVEST"], 2
            if not watered:
                return ["WATER"], (0 if streak >= 1 else 1)
            return None, 9

        if days_left < _MS_CROP["MELON"]["last"] + 1 and days_left >= _MS_CROP["CARROT"]["last"] + 1:
            empty = sum(1 for t in st["tiles"].values() if t["crop"] is None)
            have = int(seeds.get("CARROT", 0) or 0)
            if empty > have and st["seed_orders"] < 6 and money > _MS_CFG["reserve"]:
                front.append(["BUY_SEED", "CARROT", empty - have])
                st["seed_orders"] += 1

        hand_actions = list(action.get("hands") or [])
        while len(hand_actions) < len(hands):
            hand_actions.append(["PASS"])
        claimed = set()
        for i in ours:
            pos = hands[i]
            inv = invs[i + 1] if i + 1 < len(invs) else {}
            carrying = int(inv.get("MELON", 0) or 0) + int(inv.get("CARROT", 0) or 0)
            act = None
            urgent = [p for p in st["tiles"] if task_for(p) == (["WATER"], 0)]
            if carrying > 0 and (hour >= _MS_CFG["deliver_hour"] or (carrying >= _MS_CFG["deliver_at"] and not urgent)):
                if pos in _MS_ACCESS:
                    item = "MELON" if inv.get("MELON") else "CARROT"
                    act = ["PLACE", item, int(inv.get(item, 0))]
                    _MS_TELEMETRY["delivered"] += int(inv.get(item, 0))
                else:
                    tgt = min(_MS_ACCESS, key=lambda a: abs(a[0] - pos[0]) + abs(a[1] - pos[1]))
                    act = [_ms_toward(pos, tgt)]
            if act is None:
                here = task_for(pos)[0] if (pos in st["tiles"] and pos not in claimed) else None
                if here:
                    act = here
                    claimed.add(pos)
                else:
                    todo = [(task_for(p)[1], abs(p[0] - pos[0]) + abs(p[1] - pos[1]), p)
                            for p in st["tiles"] if p not in claimed and task_for(p)[0]]
                    if todo:
                        todo.sort()
                        tgt = todo[0][2]
                        claimed.add(tgt)
                        mv = _ms_toward(pos, tgt)
                        act = [mv] if mv else task_for(tgt)[0]
            if act is None:
                act = ["PASS"]
                _MS_TELEMETRY["idle"] += 1
            if act[0] == "WATER":
                st["tiles"][pos]["watered_day"] = day
                _MS_TELEMETRY["watered"] += 1
            elif act[0] == "PLANT":
                st["tiles"][pos].update({"crop": act[1], "planted_day": day, "watered_day": -1})
                _MS_TELEMETRY["planted"] += 1
            elif act[0] == "HARVEST":
                _MS_TELEMETRY["harvested"] += 1
                tile = tiles[pos[1]][pos[0]]
                _MS_TELEMETRY["harvest_units"] += int(tile.get("yield_units", 0) or 0) if isinstance(tile, dict) else 0
            elif act[0] == "DIG":
                _MS_TELEMETRY["dug"] += 1
            hand_actions[i] = act
        action["hands"] = hand_actions

        sells = []
        for item in ("MELON", "CARROT"):
            n = int(shed.get(item, 0) or 0)
            planned = sum(int(o[2]) for o in market if o[0] == "SELL" and len(o) > 2 and o[1] == item)
            if n > planned:
                sells.append(["SELL", item, n - planned])
                _MS_TELEMETRY["sold"] += n - planned
        orders = front + sells + market
        if len(orders) > 10:
            keep = [o for o in orders if not (o[0] == "SELL" and len(o) > 2 and int(o[2]) <= 0)]
            orders = keep if len(keep) <= 10 else keep[:10]
        action["market"] = orders
        return action
    except Exception:
        _MS_TELEMETRY["errors"] += 1
        return action


agent.telemetry = {**(getattr(_MS_PARENT, "telemetry", {}) or {}), "melon": _MS_TELEMETRY}
kaggle_agent = agent
'''

BASE = {"buy_step": 266, "reserve": 1500, "deliver_hour": 21, "deliver_at": 6}
VARIANTS = {
    "ms7x1": {**BASE, "tiles_per_hand": 7, "hands": 1},
    "ms5x1": {**BASE, "tiles_per_hand": 5, "hands": 1},
    "ms7x2": {**BASE, "tiles_per_hand": 7, "hands": 2},
    "ms9x2": {**BASE, "tiles_per_hand": 9, "hands": 2},
    "ms_land": {**BASE, "tiles_per_hand": 0, "hands": 0},
    "ms_hire": {**BASE, "tiles_per_hand": 0, "hands": 1},
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
    (ROOT / "experiments" / "v43_melon_sandbox_build.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
