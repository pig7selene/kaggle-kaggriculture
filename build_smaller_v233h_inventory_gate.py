"""Build a V233H-0911 variant that will not sell premium goods into a crash.

Three independent lines of evidence point at market inventory relative to the
I0 = 10,000 equilibrium as the signal our agent ignores and the frontier uses:

- branch_tree's five leave-one-out-reliable forks in Majkel's play are gated on
  market_inventory:WHEAT at 9993.0, 9981.5, 9977.5, 9967.5 and 9962.0, all just
  under equilibrium
- the flat G1 market module, free to pick among 58 features, puts five
  inv_excess:* features in its fifteen most-used splits and no shop feature at all
- measured directly in our own official replays, 59 units of standing wool
  surplus takes the price from 199 to 1

Our agent has no such input: it follows its tape and sells whatever the tape
says whatever the price is doing.

The gate added here is deliberately the most conservative intervention that
uses that signal. A premium SELL is skipped while the resource trades below a
fraction of its base price, and the skipped quantity is remembered and released
once the price recovers, or unconditionally near the end of the season. The
downside is bounded by construction: goods held back are sold later at worst
for the floor price they would have fetched now, so the cost is the time value
of a few coins, while the upside is the whole gap between floor and base.

Base prices are read at step 0, where every resource sits at I0 and therefore
quotes exactly its base.

This writes a NEW agent. agents/smaller_market_shock_v233h_non_yarn_0911 is
submitted as 56250442 and is not touched.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "agents" / "smaller_market_shock_v233h_non_yarn_0911"
OUTPUT = ROOT / "agents" / "smaller_market_shock_v233h_gate"
RECEIPT = ROOT / "experiments" / "smaller_v233h_inventory_gate_build.json"
COPY = ("main.py", "policy.py", "actions.json", "settings.json", "LICENSE.txt", "NOTICE.txt")
MEMBERS = COPY + ("router.py",)
EXECUTABLE = ("main.py", "policy.py", "router.py", "actions.json", "settings.json")

LAYER = '''

# V233H-GATE: do not sell a premium good into a crashed market.
# Market inventory is global and its price curve above equilibrium is steep --
# 59 units of standing wool surplus moves the price from 199 to 1 -- so a tape
# that sells regardless of price realises almost nothing on those units. Skipped
# quantity is remembered and released when the price recovers, or at the end of
# the season, so nothing is thrown away.
_GATE_PARENT = agent
_GATE_RESOURCES = ('STRAWBERRY', 'MELON', 'MILK', 'WOOL')
_GATE_THRESHOLD = {threshold!r}
_GATE_RELEASE_STEP = {release_step!r}
_GATE_RELEASE_UNITS = {release_units!r}
_GATE_MAX_ORDERS = 10
_GATE_STATE = {{}}


def _gate_ratio(resource, prices, base):
    reference = base.get(resource)
    if not reference:
        return 1.0
    return float(prices.get(resource, 0)) / float(reference)


def agent(observation, configuration=None):
    action = _GATE_PARENT(observation, configuration)
    step = int(observation.get('step', 0) or 0)
    prices = observation.get('market', {{}}).get('prices', {{}}) or {{}}
    if step == 0 or 'base' not in _GATE_STATE:
        _GATE_STATE.clear()
        _GATE_STATE['base'] = dict(prices)
        _GATE_STATE['held'] = {{}}
        _GATE_STATE['skipped'] = 0
        _GATE_STATE['released'] = 0
    base = _GATE_STATE['base']
    held = _GATE_STATE['held']
    endgame = step >= _GATE_RELEASE_STEP

    # Remove only, never add. The parent's SELL orders are speculative "sell up
    # to N from the shed" instructions, and most of the quantity in them never
    # fills, so re-emitting a held quantity later injects orders the tape never
    # planned and displaces real ones under the ten-order cap -- which starved
    # livestock and cost 92 escapes in a game against zero for the parent.
    # Skipping a sale leaves the goods in the shed, where the parent's own
    # terminal liquidation picks them up, so nothing needs re-emitting.
    result = copy.deepcopy(action)
    orders = [order for order in (result.get('market') or []) if order]
    kept = []
    for order in orders:
        if (not endgame and order and order[0] == 'SELL' and len(order) > 2
                and order[1] in _GATE_RESOURCES
                and _gate_ratio(order[1], prices, base) < _GATE_THRESHOLD):
            held[order[1]] = held.get(order[1], 0) + int(order[2])
            _GATE_STATE['skipped'] += int(order[2])
            continue
        kept.append(order)

    result['market'] = kept
    return result


_GATE_REPORT = dict(getattr(_GATE_PARENT, 'telemetry', {{}}) or {{}})
_GATE_REPORT['gate_state'] = _GATE_STATE
agent.telemetry = _GATE_REPORT
kaggle_agent = agent
'''


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bundle_sha256(directory: Path, names) -> str:
    material = "".join(f"{name}\0{sha256(directory / name)}\n" for name in names).encode()
    return hashlib.sha256(material).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--threshold", type=float, default=0.6,
                        help="sell a premium good only at or above this fraction of base price")
    parser.add_argument("--release-step", type=int, default=700,
                        help="from this step, release everything held regardless of price")
    parser.add_argument("--release-units", type=int, default=2,
                        help="units of a held resource released per step once price recovers")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--receipt", type=Path, default=RECEIPT)
    args = parser.parse_args()

    output = args.output.resolve()
    if output.resolve() == SOURCE.resolve():
        raise RuntimeError("refusing to overwrite the submitted 0911 candidate")
    output.mkdir(parents=True, exist_ok=True)
    for name in COPY:
        shutil.copy2(SOURCE / name, output / name)

    router = (SOURCE / "router.py").read_text()
    if "_GATE_PARENT" in router:
        raise RuntimeError("source router already carries a gate layer")
    layer = LAYER.format(threshold=args.threshold, release_step=args.release_step,
                         release_units=args.release_units)
    (output / "router.py").write_text(router.rstrip() + "\n" + layer)

    receipt = {
        "purpose": "V233H-0911 plus a premium-sale price gate on the shared market",
        "parent": str(SOURCE.relative_to(ROOT)),
        "parent_bundle_sha256": bundle_sha256(SOURCE, sorted(MEMBERS)),
        "parent_executable_bundle_sha256": bundle_sha256(SOURCE, EXECUTABLE),
        "parent_submission_id": 56250442,
        "output": str(output.relative_to(ROOT)) if output.is_relative_to(ROOT) else str(output),
        "gate": {
            "resources": ["STRAWBERRY", "MELON", "MILK", "WOOL"],
            "threshold_fraction_of_base_price": args.threshold,
            "release_step": args.release_step,
            "release_units_per_step": args.release_units,
        },
        "members": {name: sha256(output / name) for name in sorted(MEMBERS)},
        "bundle_sha256": bundle_sha256(output, sorted(MEMBERS)),
        "executable_bundle_sha256": bundle_sha256(output, EXECUTABLE),
        "parent_unchanged": bundle_sha256(SOURCE, sorted(MEMBERS)),
        "kaggle_submission_made": False,
    }
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
