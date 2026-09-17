"""Empty the shed at the start of the last day instead of through it.

At step 648 both agents hold about ninety units and both spend the final day
selling them off, so the premium price index over that day is 0.61 for us and
for the opponent alike; the chassis's own `terminal_liquidation` waits until
718, the worst moment of all. The market matches the two players unit by unit
against a shared inventory, so the seller who empties first takes the day-nine
prices and leaves the crash to the other -- the same mechanism the five-step
lead exploits, applied to the single largest lot in the game.

From `start` on, this posts the whole shed every step (premium first, then the
rest by unit value), letting the parent's own orders follow. Nothing is held
back: anything unsold at 719 is worth nothing anyway.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VD = Path("/private/tmp/kaggriculture_v43_variants")

WRAPPER = '''

# ---------------------------------------------------------------- early terminal
_ET_CFG = @@CFG@@
_ET_BASE = {"WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120, "MELON": 250,
            "EGG": 50, "MILK": 160, "WOOL": 200, "FERTILIZER": 100}
_ET_PARENT = agent
_ET_TELEMETRY = {"steps": 0, "active": 0, "units_posted": 0, "orders": 0, "errors": 0}


def _et_get(o, k, d=None):
    return o.get(k, d) if isinstance(o, dict) else getattr(o, k, d)


def agent(observation, configuration=None):
    action = _ET_PARENT(observation, configuration)
    try:
        _ET_TELEMETRY["steps"] += 1
        step = int(_et_get(observation, "step", -1))
        if step < _ET_CFG["start"] or step > 718:
            return action
        shed = dict(_et_get(_et_get(observation, "private", {}) or {}, "shed", {}) or {})
        prices = dict(_et_get(_et_get(observation, "market", {}) or {}, "prices", {}) or {})
        market = [list(o) for o in (action.get("market") or []) if o]
        planned = {}
        for o in market:
            if o[0] == "SELL" and len(o) >= 3:
                planned[o[1]] = planned.get(o[1], 0) + max(0, int(o[2]))
        extra = []
        for item in sorted(_ET_BASE, key=lambda i: -(prices.get(i, 0) or 0)):
            have = int(shed.get(item, 0) or 0) - planned.get(item, 0)
            if have <= 0:
                continue
            extra.append(["SELL", item, have])
            _ET_TELEMETRY["units_posted"] += have
            _ET_TELEMETRY["orders"] += 1
        if extra:
            _ET_TELEMETRY["active"] += 1
        # our own sells first: an early slot is filled against a lower inventory
        sells = [o for o in market if o[0] == "SELL" and len(o) >= 3 and int(o[2]) > 0]
        others = [o for o in market if o not in sells]
        action["market"] = (sells + extra + others)[:10]
        return action
    except Exception:
        _ET_TELEMETRY["errors"] += 1
        return action


agent.telemetry = {**(getattr(_ET_PARENT, "telemetry", {}) or {}), "early_terminal": _ET_TELEMETRY}
kaggle_agent = agent
'''

VARIANTS = {"et648": 648, "et672": 672, "et696": 696, "et624": 624}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bases", default="room_plus_clamp,lead5")
    args = parser.parse_args()
    receipt = {}
    for base in args.bases.split(","):
        src = (VD / f"{base}.py").read_text().rstrip()
        for name, start in VARIANTS.items():
            out = VD / f"{base}_{name}.py"
            out.write_text(src + "\n" + WRAPPER.replace("@@CFG@@", repr({"start": start})))
            receipt[out.stem] = {"base": base, "start": start,
                                 "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}
            print("built", out.name)
    (ROOT / "experiments" / "v43_early_terminal_build.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
