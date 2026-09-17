"""Put our sell orders in the earliest market slots.

`_process_market` matches the two players slot by slot: slot 0 runs to
completion, then slot 1, and so on, with both players' slot-i orders quoted
against the same pre-commit inventory. Every unit sold raises that inventory
and lowers the next quote, so within one step an order in an early slot is
filled at a strictly better price than the same order in a late slot, and the
only asymmetry between the two players is which slot their order sits in.

Our own layers append: `_add_sell`, room_guard and the premium lead all do
`market.append(...)`, so the units we work hardest to sell early in *time* are
sold last in *slot*, at the worst price of the step, and they are the first to
be cut by the ten-order cap.

This wrapper reorders the list without changing its content: real sells (a
positive quantity) first, in their original relative order, then BUY_PRODUCT,
which is also quoted off inventory, then everything else. HIRE, BUY_LAND,
BUY_SEED and BUY_ANIMAL are priced independently of the market, so moving them
back costs nothing. Zero-quantity sells -- the chassis's suppression
placeholders -- keep their place among the trailing orders.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VD = Path("/private/tmp/kaggriculture_v43_variants")

WRAPPER = '''

# ---------------------------------------------------------------- slot first
_SF_PARENT = agent
_SF_TELEMETRY = {"steps": 0, "reordered": 0, "moved_orders": 0, "errors": 0}


def agent(observation, configuration=None):
    action = _SF_PARENT(observation, configuration)
    try:
        _SF_TELEMETRY["steps"] += 1
        market = [list(o) for o in (action.get("market") or []) if o]
        if len(market) < 2:
            return action
        sells, buys, rest = [], [], []
        for i, o in enumerate(market):
            if o[0] == "SELL" and len(o) >= 3 and int(o[2]) > 0:
                sells.append((i, o))
            elif o[0] == "BUY_PRODUCT":
                buys.append((i, o))
            else:
                rest.append((i, o))
        new = [o for _, o in sells] + [o for _, o in buys] + [o for _, o in rest]
        if new != market:
            _SF_TELEMETRY["reordered"] += 1
            _SF_TELEMETRY["moved_orders"] += sum(1 for a, b in zip(new, market) if a != b)
        action["market"] = new[:10]
        return action
    except Exception:
        _SF_TELEMETRY["errors"] += 1
        return action


agent.telemetry = {**(getattr(_SF_PARENT, "telemetry", {}) or {}), "slot_first": _SF_TELEMETRY}
kaggle_agent = agent
'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bases", default="room_plus_clamp,lead5,lead8")
    args = parser.parse_args()
    receipt = {}
    for base in args.bases.split(","):
        src = (VD / f"{base}.py").read_text().rstrip()
        if "_SF_PARENT" in src:
            raise RuntimeError(f"{base} already carries the slot layer")
        out = VD / f"{base}_sf.py"
        out.write_text(src + "\n" + WRAPPER)
        receipt[f"{base}_sf"] = {"base": base, "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
                                 "path": str(out)}
        print(f"built {out.name}")
    (ROOT / "experiments" / "v43_slot_first_build.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
