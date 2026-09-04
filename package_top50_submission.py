"""Package the locked Top-50 observable portfolio as one standalone file.

This is a mechanical deployment transform.  It embeds the three exact route
payloads, reuses the proven standalone Stage-3 executor, and preserves the
locked safety wrappers and selector verbatim in behavior.
"""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import zlib

import package_v27_submission as template


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "agents/top50_distilled/top50_observable_portfolio.py"
ROUTE_BANK = ROOT / "experiments/top50_route_bank.json"
OUTPUT = ROOT / "submission/main.py"
EXPECTED_SOURCE_SHA = "f9ca672848ccffdfe56888d99bcdf5a9d7644062b9eec0cf0cdea13574931233"
ROUTE_IDS = {
    "dmitry": "super_raw_55859516",
    "hanserong": "super_raw_55886665",
    "redblack": "super_raw_55890191",
}


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _wrapped_payload(value):
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    packed = base64.b64encode(zlib.compress(canonical, 9)).decode()
    wrapped = "\n".join(
        f'    "{packed[index:index + 100]}"'
        for index in range(0, len(packed), 100)
    )
    return canonical, packed, wrapped


def main():
    actual = _sha256(SOURCE)
    if actual != EXPECTED_SOURCE_SHA:
        raise SystemExit(
            f"locked source hash mismatch: expected {EXPECTED_SOURCE_SHA}, got {actual}"
        )

    rows = {
        row["route_id"]: row
        for row in json.loads(ROUTE_BANK.read_text())["routes"]
    }
    routes = {}
    for name, route_id in ROUTE_IDS.items():
        row = rows[route_id]
        minimal = {
            "route_id": row["route_id"],
            "consensus_actions": row["consensus_actions"],
            "expected_state": row["expected_state"],
        }
        if len(minimal["consensus_actions"]) != 719:
            raise SystemExit(f"{name} action route is not 719 steps")
        if len(minimal["expected_state"]) != 719:
            raise SystemExit(f"{name} expected-state route is not 719 steps")
        routes[route_id] = minimal

    # Render the already-proven standalone Stage-3 executor, gated by the
    # locked portfolio source hash, then mechanically widen its route payload.
    template.SOURCE = SOURCE
    template.MANIFEST = ROUTE_BANK
    template.OUTPUT = OUTPUT
    template.EXPECTED_SOURCE_SHA = EXPECTED_SOURCE_SHA
    template.ROUTE_ID = ROUTE_IDS["dmitry"]
    template.main()

    text = OUTPUT.read_text()
    text = text.replace(
        '"""Standalone Kaggriculture agent: frozen Victor V27 route + weed repair.\n\n'
        "Generated from agents/v27_replay_weed_guard.py. The static route is embedded;\n"
        "there are no repository, replay-file, manifest, network, or cwd dependencies.\n"
        '"""',
        '"""Standalone locked Top-50 observable portfolio for Kaggriculture.\n\n'
        "Three complete route economies, exact bounded safety repairs, and the\n"
        "validated step-1 observable selector are embedded in this file.\n"
        "There are no repository, replay-file, manifest, network, or cwd dependencies.\n"
        '"""',
    )

    canonical, packed, wrapped = _wrapped_payload(routes)
    payload_start = text.index("_PACKED_ROUTE = (")
    payload_end = text.index("\n\nSTAGE_NAME", payload_start)
    replacement = (
        "_PACKED_ROUTES = (\n"
        + wrapped
        + "\n)\n"
        + "_ROUTES = json.loads(zlib.decompress(b64decode(_PACKED_ROUTES)).decode())"
    )
    text = text[:payload_start] + replacement + text[payload_end:]
    text = text.replace(
        "def make_v27_agent():\n    route = _ROUTE",
        "def make_v27_agent(route_id):\n    route = _ROUTES[route_id]",
    )

    portfolio_tail = r'''
def _make_safe(route_id, exact_rescues=()):
    base = make_v27_agent(route_id)
    exact_rescues = {tuple(value) for value in exact_rescues}

    def safe_agent(obs):
        output = deepcopy(base(obs))
        player = obs["player"]
        farm = obs["farms"][player]
        positions = [farm["farmer"], *farm.get("hands", [])]
        inventories = obs["private"]["inventories"]
        actions = [output.get("farmer", ["PASS"]), *output.get("hands", [])]
        actions.extend([["PASS"]] * max(0, len(positions) - len(actions)))
        for index, position in enumerate(positions):
            x, y = position
            tile = farm["tiles"][y][x]
            if not isinstance(tile, dict) or not tile.get("animal") or tile.get("fed_today"):
                continue
            urgent = int(tile.get("consecutive_unfed", 0)) >= 1
            if not urgent:
                continue
            exact = (int(obs["step"]), int(x), int(y)) in exact_rescues
            if int(obs.get("hour", 0)) < 22 and not exact:
                continue
            if int(inventories[index].get("WHEAT", 0)) > 0:
                actions[index] = ["FEED"]
        output["farmer"], output["hands"] = actions[0], actions[1:len(positions)]
        return output

    safe_agent.telemetry = base.telemetry
    safe_agent.base = base
    safe_agent.safety_policy = "hour-22 deadline or audited exact miss; co-located worker with carried wheat only"
    return safe_agent


PARENTS = {
    "dmitry": _make_safe("super_raw_55859516", exact_rescues=((686, 2, 4),)),
    "hanserong": _make_safe("super_raw_55886665", exact_rescues=((25, 4, 4),)),
    "redblack": _make_safe("super_raw_55890191"),
}
telemetry = {}
selected_name = None


def _select(obs):
    other = obs["farms"][1 - obs["player"]]
    money = float(other["money"])
    hands = len(other.get("hands", []))
    if money >= 2500 and hands == 0:
        return "redblack"
    if money >= 1500 and hands >= 6:
        return "hanserong"
    if 3 < money <= 10 and hands >= 5:
        return "hanserong"
    return "dmitry"


def agent(obs):
    global selected_name
    step = int(obs.get("step", 0))
    if step == 0:
        selected_name = None
        outputs = {name: parent(obs) for name, parent in PARENTS.items()}
        output = outputs["dmitry"]
    else:
        if selected_name is None:
            selected_name = _select(obs)
        output = PARENTS[selected_name](obs)
    source = PARENTS[selected_name or "dmitry"].telemetry
    telemetry.clear()
    telemetry.update(deepcopy(source))
    telemetry["portfolio_parent"] = selected_name or "pending"
    telemetry["selector_step"] = 1
    return output


agent.telemetry = telemetry
agent.parents = PARENTS
agent.feature_policy = "visible opponent money and hand count at step 1 only"
'''
    if "agent = make_v27_agent()" not in text:
        raise SystemExit("standalone executor tail anchor missing")
    text = text.replace("agent = make_v27_agent()", portfolio_tail.strip())
    OUTPUT.write_text(text)

    normalized = text.replace('"\n    "', "")
    if packed not in normalized:
        raise SystemExit("embedded portfolio route payload mismatch")
    forbidden = ("/Users/", "agents/", "experiments/", ".json", ".pkl", ".pickle")
    found = [value for value in forbidden if value in text]
    if found:
        raise SystemExit(f"standalone output contains forbidden local references: {found}")

    print(f"research_source_sha256={actual}")
    print(f"routes_canonical_sha256={hashlib.sha256(canonical).hexdigest()}")
    for name, route_id in ROUTE_IDS.items():
        route = routes[route_id]
        print(f"{name}_actions_sha256={_digest(route['consensus_actions'])}")
        print(f"{name}_expected_state_sha256={_digest(route['expected_state'])}")
    print(f"submission_size_bytes={OUTPUT.stat().st_size}")
    print(f"submission_sha256={_sha256(OUTPUT)}")


if __name__ == "__main__":
    main()
