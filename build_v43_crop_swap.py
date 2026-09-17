"""Plant a different crop on tiles the tape would sow with wheat.

V43's plan sows 163 wheat, 33 strawberry, 31 carrot and 12 melon per game, and
sells 672 wheat units at 43 (1.73 of base) against 129 strawberries at 114.
A wheat tile turns over every three days for one unit each time; a strawberry
tile yields four units once, but each unit is worth three to four times as
much, so per tile-day the swap is favourable as long as the extra supply does
not crash the price -- strawberry's above-equilibrium curve is linear at 1.92
per unit, which is a cliff, and the market sits within 40 units of equilibrium.
Only a measurement settles it, so this is parameterised.

The swap is surgical: the tape's PLANT action keeps its step and its tile, only
the crop name changes, and the seeds for it are bought a few steps ahead out of
cash above a floor. A failed PLANT consumes no seed, and an ongoing crop keeps
its tile, so the tape's later plantings there simply do nothing while its
WATER and HARVEST visits keep working. Nothing else in the trajectory moves.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT_DIR = Path("/private/tmp/kaggriculture_v43_variants")

WRAPPER = '''

# ---------------------------------------------------------------- crop swap
_CS_CFG = @@CFG@@
_CS_SEED_COST = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "MELON": 80, "STRAWBERRY": 100}
_CS_PARENT = agent
_CS_STATE = {}
_CS_TELEMETRY = {"steps": 0, "swapped": 0, "seeds_bought": 0, "seed_orders": 0,
                 "blocked_no_seed": 0, "errors": 0}


def _cs_get(o, k, d=None):
    return o.get(k, d) if isinstance(o, dict) else getattr(o, k, d)


def _cs_planned(tape, t, crop):
    """How many PLANT <crop> actions the tape issues at step t."""
    if not (0 <= t < len(tape)) or not isinstance(tape[t], dict):
        return 0
    n = 0
    for u in [tape[t].get("farmer")] + list(tape[t].get("hands") or []):
        if isinstance(u, (list, tuple)) and len(u) >= 2 and u[0] == "PLANT" and u[1] == crop:
            n += 1
    return n


def agent(observation, configuration=None):
    action = _CS_PARENT(observation, configuration)
    try:
        _CS_TELEMETRY["steps"] += 1
        step = int(_cs_get(observation, "step", -1))
        seat = int(_cs_get(observation, "player", 0) or 0)
        if step == 0:
            _CS_STATE.pop(seat, None)
        st = _CS_STATE.setdefault(seat, {"swapped": 0})
        day = step // 24
        chassis = _IMPL.chassis
        tape = chassis.routes.get((chassis.players.get(seat) or {}).get("route"))
        private = _cs_get(observation, "private", {}) or {}
        seeds = dict(_cs_get(private, "seeds", {}) or {})
        farms = _cs_get(observation, "farms", []) or []
        money = float(farms[seat].get("money", 0)) if len(farms) > seat else 0.0
        budget = _CS_CFG["max_subs"] - st["swapped"]
        to_crop, from_crop = _CS_CFG["to_crop"], _CS_CFG["from_crop"]

        # buy the seeds a few steps before the plantings that will need them
        if tape and budget > 0 and _CS_CFG["day_from"] <= day + 1 <= _CS_CFG["day_to"]:
            upcoming = 0
            for t in range(step + 1, min(step + _CS_CFG["lookahead"], 718) + 1):
                if _CS_CFG["day_from"] <= t // 24 <= _CS_CFG["day_to"]:
                    upcoming += _cs_planned(tape, t, from_crop)
            want = min(upcoming, budget) - int(seeds.get(to_crop, 0))
            cost = _CS_SEED_COST.get(to_crop, 100)
            afford = int(max(0.0, money - _CS_CFG["cash_floor"]) // cost)
            n = max(0, min(want, afford, _CS_CFG["max_seeds_per_step"]))
            if n > 0:
                market = action.setdefault("market", [])
                if len(market) < 10:
                    market.append(["BUY_SEED", to_crop, n])
                    _CS_TELEMETRY["seeds_bought"] += n
                    _CS_TELEMETRY["seed_orders"] += 1

        # swap this step's plantings, never more than the seeds in hand: the
        # engine drops *every* PLANT of a crop whose requests exceed its seeds
        if _CS_CFG["day_from"] <= day <= _CS_CFG["day_to"] and budget > 0:
            have = int(seeds.get(to_crop, 0))
            if have > 0:
                units = [action.get("farmer")] + list(action.get("hands") or [])
                for i, u in enumerate(units):
                    if have <= 0 or budget <= 0:
                        break
                    if isinstance(u, (list, tuple)) and len(u) >= 2 and u[0] == "PLANT" and u[1] == from_crop:
                        new = list(u)
                        new[1] = to_crop
                        if i == 0:
                            action["farmer"] = new
                        else:
                            action["hands"][i - 1] = new
                        have -= 1
                        budget -= 1
                        st["swapped"] += 1
                        _CS_TELEMETRY["swapped"] += 1
            else:
                _CS_TELEMETRY["blocked_no_seed"] += _cs_planned(
                    [action], 0, from_crop) if isinstance(action, dict) else 0
        return action
    except Exception:
        _CS_TELEMETRY["errors"] += 1
        return action


agent.telemetry = {**(getattr(_CS_PARENT, "telemetry", {}) or {}), "crop_swap": _CS_TELEMETRY}
kaggle_agent = agent
'''

VARIANTS = {
    "swap_straw_10_15": {"to_crop": "STRAWBERRY", "day_from": 10, "day_to": 15, "max_subs": 40},
    "swap_straw_12_18": {"to_crop": "STRAWBERRY", "day_from": 12, "day_to": 18, "max_subs": 40},
    "swap_straw_small": {"to_crop": "STRAWBERRY", "day_from": 10, "day_to": 15, "max_subs": 15},
    "swap_tomato_10_18": {"to_crop": "TOMATO", "day_from": 10, "day_to": 18, "max_subs": 40},
    "swap_carrot_10_18": {"to_crop": "CARROT", "day_from": 10, "day_to": 18, "max_subs": 40},
}
DEFAULTS = {"from_crop": "WHEAT", "lookahead": 6, "cash_floor": 3000, "max_seeds_per_step": 6}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=OUT_DIR / "room_plus_clamp.py")
    args = parser.parse_args()
    source = args.base.read_text().rstrip()
    if "_CS_PARENT" in source:
        raise RuntimeError("base already carries a crop swap")
    receipt = {"base": str(args.base), "variants": {}}
    for name, cfg in VARIANTS.items():
        full = {**DEFAULTS, **cfg}
        out = OUT_DIR / f"{name}.py"
        out.write_text(source + "\n" + WRAPPER.replace("@@CFG@@", repr(full)))
        receipt["variants"][name] = {"path": str(out), "cfg": full,
                                     "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}
        print(name, out, receipt["variants"][name]["sha256"][:12])
    (ROOT / "experiments" / "v43_crop_swap_build.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
