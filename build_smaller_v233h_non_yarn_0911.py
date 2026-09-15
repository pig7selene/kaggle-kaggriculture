"""Build a V233H candidate with compatible Shop Router 0911 non-Yarn routes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import runpy
import shutil


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "agents" / "smaller_market_shock_v233h_safe"
# Persisted in-repo copy; see agents/_donors/DONOR_MANIFEST.json for provenance.
# The former source was /private/tmp/kaggriculture_shop_router_0911_simple/main.py,
# which macOS reaps.  The bytes are identical to that original.
DONOR = ROOT / "agents" / "_donors" / "shop_router_0911_simple" / "main.py"
OUTPUT = ROOT / "agents" / "smaller_market_shock_v233h_non_yarn_0911"
RECEIPT = ROOT / "experiments" / "smaller_v233h_non_yarn_0911_build.json"
FILES = ("main.py", "policy.py", "settings.json", "LICENSE.txt", "NOTICE.txt")
YARN = "YARN_STORE"
BLACKLIST = {
    ("BRUNCH_SPOT", "BRUNCH_SPOT"),
    ("BRUNCH_SPOT", "ICE_CREAM_SHOP"),
    ("FARMERS_MARKET", "FARMERS_MARKET"),
    ("FARMERS_MARKET", "ICE_CREAM_SHOP"),
    ("ICE_CREAM_SHOP", "FARMERS_MARKET"),
    ("PET_CAFE", "PIZZA_SHOP"),
    ("SMOOTHIE_SHOP", "FARMERS_MARKET"),
}
ROUTER_INSERTION_POINT = "}\n\n\nclass FarmView:"
V233_ELIGIBILITY_POINT = "def _v233_eligible(obs,native):\n"
HAND_NORMALIZER = r'''

# V233H-0911: normalize donor hand slots to the observed hired-hand count.
_V0911_PARENT = agent

def agent(observation, configuration=None):
    action = _V0911_PARENT(observation, configuration)
    result = copy.deepcopy(action)
    expected = len(observation['farms'][observation['player']].get('hands', []))
    hands = list(result.get('hands') or [])[:expected]
    hands += [['PASS'] for _ in range(expected - len(hands))]
    result['hands'] = hands
    return result

agent.telemetry = _V0911_PARENT.telemetry
kaggle_agent = agent
'''
NOTICE_ADDENDUM = """
V233H-0911, September 13 2026: added non-Yarn continuations.

This bundle carries 21 action tapes, not the 13 of the parent. Tapes 0-12 are
unchanged from A Smaller Market Shock and its Shop Router 0909 ancestry, and
still serve every Yarn-related first-shop pair. Tapes 13-20 are eight complete
continuations taken verbatim from a second public Apache-2.0 notebook:

  yhay81, Shop Router 0911 Simple
  https://www.kaggle.com/code/yhay81/shop-router-0911-simple

They are reached only through 42 non-Yarn first-shop pairs. Seven further
non-Yarn pairs were measured as negative locally and deliberately left on the
inherited tape 0.

Changes made here, not inherited: the SHOP_PLANS route map is extended with
those 42 pairs; the V233 six-sheep investment is gated off on exactly those
routes; and donor hand slots are normalised to the observed hired-hand count.
No inherited routing, repair, sale, liquidation or feed rule was modified, and
no donor source file is redistributed other than the eight tapes above.
"""


EXECUTABLE_MEMBERS = ("main.py", "policy.py", "router.py", "actions.json", "settings.json")


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _bundle_sha256(directory, names):
    """Same digest convention as package_smaller_v233h_safe.source_identity."""
    material = "".join(f"{name}\0{_sha256(directory / name)}\n" for name in names).encode()
    return hashlib.sha256(material).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _field(action):
    return [action.get("farmer"), *(action.get("hands") or [])]


def _display(path):
    """Repo-relative where possible, so receipts stay portable."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def main(output=OUTPUT, receipt_path=RECEIPT):
    donor = runpy.run_path(str(DONOR))
    donor_tapes = donor["_TAPES"]
    donor_routes = donor["_ROUTES"]
    source_tapes = json.loads((SOURCE / "actions.json").read_text())
    all_non_yarn_routes = {
        tuple(pair): int(plan)
        for pair, plan in donor_routes.items()
        if YARN not in pair
    }
    non_yarn_routes = {
        pair: plan
        for pair, plan in all_non_yarn_routes.items()
        if pair not in BLACKLIST
    }
    donor_plans = sorted(set(non_yarn_routes.values()))
    if len(all_non_yarn_routes) != 49:
        raise RuntimeError(
            f"expected 49 donor non-Yarn routes, found {len(all_non_yarn_routes)}"
        )
    if set(BLACKLIST) - set(all_non_yarn_routes):
        raise RuntimeError("blacklist contains an unknown donor route")

    plan_map = {
        donor_plan: len(source_tapes) + index
        for index, donor_plan in enumerate(donor_plans)
    }
    for step in range(144):
        if _canonical(_field(donor_tapes[0][step])) != _canonical(_field(source_tapes[0][step])):
            raise RuntimeError(f"opening field incompatibility at step {step}")

    combined_tapes = list(source_tapes)
    combined_tapes.extend(donor_tapes[plan] for plan in donor_plans)
    candidate_routes = {
        pair: plan_map[donor_plan]
        for pair, donor_plan in non_yarn_routes.items()
    }
    route_literal = "}\n\nSHOP_PLANS.update({\n" + "\n".join(
        f"    {pair!r}: {candidate_routes[pair]},"
        for pair in sorted(candidate_routes)
    ) + "\n})\n\n\nclass FarmView:"

    output.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        shutil.copy2(SOURCE / name, output / name)
    # Apache-2.0 attribution: this bundle redistributes eight donor tapes that
    # the inherited NOTICE does not cover.  NOTICE.txt is never read at runtime,
    # so this is documentation only and leaves behaviour untouched.
    (output / "NOTICE.txt").write_text(
        (SOURCE / "NOTICE.txt").read_text().rstrip() + "\n" + NOTICE_ADDENDUM
    )
    (output / "actions.json").write_text(
        json.dumps(combined_tapes, separators=(",", ":")) + "\n"
    )
    source_router = (SOURCE / "router.py").read_text()
    if source_router.count(ROUTER_INSERTION_POINT) != 1:
        raise RuntimeError("router insertion point is not unique")
    candidate_router = source_router.replace(ROUTER_INSERTION_POINT, route_literal, 1)
    tape_guard = "len(self.tapes) != 13"
    tape_message = 'raise ValueError("Expected 13 complete, 719-turn action tapes")'
    if candidate_router.count(tape_guard) != 1 or candidate_router.count(tape_message) != 1:
        raise RuntimeError("source tape-count guard changed")
    candidate_router = candidate_router.replace(
        tape_guard, f"len(self.tapes) != {len(combined_tapes)}", 1
    ).replace(
        tape_message,
        f'raise ValueError("Expected {len(combined_tapes)} complete, 719-turn action tapes")',
        1,
    )
    if candidate_router.count(V233_ELIGIBILITY_POINT) != 1:
        raise RuntimeError("V233 eligibility point changed")
    sheep_disabled_pairs = "{" + ",".join(
        repr(pair) for pair in sorted(candidate_routes)
    ) + "}"
    candidate_router = candidate_router.replace(
        V233_ELIGIBILITY_POINT,
        V233_ELIGIBILITY_POINT
        + "    if tuple(obs['town']['unlocked_shops'][:2]) in "
        + sheep_disabled_pairs
        + ":return False\n",
        1,
    )
    candidate_router = candidate_router.rstrip() + HAND_NORMALIZER
    (output / "router.py").write_text(candidate_router)

    receipt = {
        "purpose": "V233H plus compatible Shop Router 0911 non-Yarn continuations",
        "source": _display(SOURCE),
        "source_main_sha256": _sha256(SOURCE / "main.py"),
        "source_router_sha256": _sha256(SOURCE / "router.py"),
        "source_actions_sha256": _sha256(SOURCE / "actions.json"),
        "donor": _display(DONOR),
        "donor_sha256": _sha256(DONOR),
        "opening_field_equivalence_steps": 144,
        "opening_state_probe": "verified separately against pass at seed 441901",
        "retained_yarn_routes": 15,
        "added_non_yarn_routes": len(candidate_routes),
        "added_non_yarn_pairs": [list(pair) for pair in sorted(candidate_routes)],
        "blacklisted_non_yarn_pairs": [list(pair) for pair in sorted(BLACKLIST)],
        "v233_sheep_gate": "disabled only on enabled 0911 routes",
        "hand_action_normalization": True,
        "added_donor_plans": donor_plans,
        "candidate_plan_indices": plan_map,
        "total_candidate_tapes": len(combined_tapes),
        "output": _display(output),
        "members": {
            path.name: {"sha256": _sha256(path), "bytes": path.stat().st_size}
            for path in sorted(output.iterdir()) if path.is_file()
        },
        # Hash of only the files the engine actually executes.  NOTICE.txt and
        # LICENSE.txt are documentation, so this digest is what binds a strategy
        # result to a candidate: it is stable across attribution edits.
        "executable_members": EXECUTABLE_MEMBERS,
        "executable_bundle_sha256": _bundle_sha256(output, EXECUTABLE_MEMBERS),
        "kaggle_submission_made": False,
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=OUTPUT,
        help="candidate directory to write (override to verify a rebuild without clobbering)",
    )
    parser.add_argument("--receipt", type=Path, default=RECEIPT, help="build receipt to write")
    args = parser.parse_args()
    main(args.output.resolve(), args.receipt.resolve())
