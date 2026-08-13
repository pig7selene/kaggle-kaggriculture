"""Reproducibly package the frozen K3 V27 agent as one standalone file."""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import textwrap
import zlib


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "agents/v27_replay_weed_guard.py"
MANIFEST = ROOT / "experiments/v27_route_manifest.json"
OUTPUT = ROOT / "submission/main.py"
EXPECTED_SOURCE_SHA = "dc0100ec0d029a6362f92618429b09d7baba5b8a5257f20a61385fe82afeda51"
ROUTE_ID = "v27_family_3_victor_at_tufa_labs"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    actual = sha256(SOURCE)
    if actual != EXPECTED_SOURCE_SHA:
        raise SystemExit(f"frozen source hash mismatch: expected {EXPECTED_SOURCE_SHA}, got {actual}")

    bank = json.loads(MANIFEST.read_text())
    source_route = next(row for row in bank["routes"] if row["route_id"] == ROUTE_ID)
    route = {
        "route_id": source_route["route_id"],
        "consensus_actions": source_route["consensus_actions"],
        "expected_state": source_route["expected_state"],
    }
    packed = base64.b64encode(
        zlib.compress(json.dumps(route, sort_keys=True, separators=(",", ":")).encode(), 9)
    ).decode()
    wrapped = "\n".join(f'    "{packed[index:index + 100]}"' for index in range(0, len(packed), 100))

    output = '''\
"""Standalone Kaggriculture agent: frozen Victor V27 route + weed repair.

Generated from agents/v27_replay_weed_guard.py. The static route is embedded;
there are no repository, replay-file, manifest, network, or cwd dependencies.
"""

from base64 import b64decode
from copy import deepcopy
import json
import zlib

from kaggle_environments.envs.kaggriculture import kaggriculture as _game


_PACKED_ROUTE = (
__PACKED__
)
_ROUTE = json.loads(zlib.decompress(b64decode(_PACKED_ROUTE)).decode())

STAGE_NAME = "K3_weed_transaction_repair"
MOVES = {"NORTH", "SOUTH", "EAST", "WEST"}
BUILD = {"BUILD_COOP", "BUILD_PASTURE"}
CROPS = set(_game.CROPS)
ANIMALS = set(_game.ANIMALS)
SHED_TILES = {(4, 4), (5, 4), (4, 5), (5, 5)}


def _blank_metrics(route):
    return {
        "stage": STAGE_NAME,
        "route_id": route["route_id"],
        "calls": 0,
        "mode_steps": {"TRACK": 0, "REPAIR": 0, "FALLBACK": 0},
        "farmer_route_matches": 0,
        "farmer_route_requests": 0,
        "hand_route_matches": 0,
        "hand_route_requests": 0,
        "market_route_matches": 0,
        "market_route_requests": 0,
        "all_route_matches": 0,
        "all_route_requests": 0,
        "worker_rematches": 0,
        "dropped_route_actions": 0,
        "extra_worker_passes": 0,
        "position_error_sum": 0,
        "position_error_observations": 0,
        "anchor_error": [],
        "repairs": {"weed": 0, "capital": 0, "hire": 0, "survival": 0},
        "repair_durations": [],
        "repair_success": 0,
        "repair_abort": 0,
        "critical_confirmed": 0,
        "critical_failed": 0,
        "critical_events": [],
        "hire_planned": 0,
        "hire_executed": 0,
        "hire_suppressed": 0,
        "hire_retried": 0,
        "hire_spend_estimate": 0,
        "sell_reorders": 0,
        "future_sell_assignments": 0,
        "original_sell_revenue_estimate": 0.0,
        "optimized_sell_revenue_estimate": 0.0,
        "exact_self_impact": 0.0,
        "fallback_step": None,
        "fallback_reason": None,
        "module_errors": {},
        "semantic_sanitizations": 0,
        "safety_events": [],
    }


def _animal_counts(farm):
    out = {animal: 0 for animal in ANIMALS}
    for row in farm["tiles"]:
        for tile in row:
            if isinstance(tile, dict) and tile.get("animal") in out:
                out[tile["animal"]] += 1
    return out


def _crops(farm):
    out = {}
    for row in farm["tiles"]:
        for tile in row:
            if isinstance(tile, dict) and tile.get("kind") == "PLANT":
                crop = tile.get("crop")
                out[crop] = out.get(crop, 0) + 1
    return out


def _priority(action):
    op = action[0] if action else "PASS"
    return {
        "FEED": 100, "WATER": 95, "PLACE": 90, "BUILD_PASTURE": 88,
        "BUILD_COOP": 88, "HARVEST": 75, "PLANT": 70, "PICKUP": 65,
        "DROP": 62, "CARE": 55, "COLLECT_FERTILIZER": 50,
        "FERTILIZE": 45, "DIG": 40, "NORTH": 25, "SOUTH": 25,
        "EAST": 25, "WEST": 25, "PASS": 0,
    }.get(op, 10)


def _distance(left, right):
    return abs(int(left[0]) - int(right[0])) + abs(int(left[1]) - int(right[1]))


def _match_workers(actual, expected, expected_actions, previous):
    if len(actual) == len(expected) and all(list(a) == list(e) for a, e in zip(actual, expected)):
        return list(range(len(actual))), 0, 0
    unused = set(range(len(expected)))
    mapping = [None] * len(actual)
    total_error = 0
    rematches = 0
    for actual_index, position in enumerate(actual):
        prior = previous.get(actual_index)
        if prior in unused and list(position) == list(expected[prior]):
            mapping[actual_index] = prior
            unused.remove(prior)
    for actual_index, position in enumerate(actual):
        if mapping[actual_index] is not None or not unused:
            continue
        prior = previous.get(actual_index)
        choice = min(
            unused,
            key=lambda expected_index: (
                _distance(position, expected[expected_index])
                - (2 if prior == expected_index else 0)
                - min(1.5, _priority(expected_actions[expected_index]) / 100),
                -_priority(expected_actions[expected_index]),
                expected_index,
            ),
        )
        mapping[actual_index] = choice
        unused.remove(choice)
        total_error += _distance(position, expected[choice])
        rematches += prior is not None and prior != choice
    return mapping, total_error, rematches


def _unit_legal(obs, unit_index, action):
    if not isinstance(action, list) or not action:
        return False
    me = obs["farms"][obs["player"]]
    positions = [me["farmer"], *me["hands"]]
    inventories = obs["private"].get("inventories", [])
    if unit_index >= len(positions):
        return False
    x, y = positions[unit_index]
    tile = me["tiles"][y][x]
    inventory = inventories[unit_index] if unit_index < len(inventories) else {}
    op = action[0]
    if op == "PASS":
        return True
    if op in MOVES:
        dx = {"WEST": -1, "EAST": 1}.get(op, 0)
        dy = {"NORTH": -1, "SOUTH": 1}.get(op, 0)
        return 0 <= x + dx < len(me["tiles"][0]) and 0 <= y + dy < len(me["tiles"])
    if op == "PLANT":
        return tile is None and len(action) == 2 and obs["private"]["seeds"].get(action[1], 0) > 0
    if op == "WATER":
        return isinstance(tile, dict) and tile.get("kind") == "PLANT" and not tile.get("watered_today", False)
    if op == "HARVEST":
        if not isinstance(tile, dict) or tile.get("yield_units", 0) <= 0:
            return False
        if tile.get("kind") != "PLANT":
            return bool(tile.get("animal"))
        crop = tile.get("crop")
        return obs["day"] - tile.get("planted_day", obs["day"]) >= _game.CROPS[crop]["first_yield_day"]
    if op == "FERTILIZE":
        return isinstance(tile, dict) and tile.get("kind") == "PLANT" and inventory.get("FERTILIZER", 0) > 0
    if op == "DIG":
        return tile not in (None, "LOCKED") and not (isinstance(tile, dict) and tile.get("animal"))
    if op in BUILD:
        return tile is None
    if op == "PICKUP":
        return (x, y) in SHED_TILES and len(action) >= 2 and obs["private"]["shed"].get(action[1], 0) > 0
    if op == "DROP":
        return (x, y) in SHED_TILES and bool(inventory)
    if op == "PLACE":
        if len(action) < 2:
            return False
        item = action[1]
        if item in ANIMALS:
            return isinstance(tile, dict) and tile.get("kind") == _game.ANIMALS[item]["structure"] and not tile.get("animal") and inventory.get(item, 0) > 0
        return (x, y) in SHED_TILES and inventory.get(item, 0) > 0
    if op == "FEED":
        return isinstance(tile, dict) and bool(tile.get("animal")) and not tile.get("fed_today", False) and inventory.get("WHEAT", 0) > 0
    if op == "CARE":
        return isinstance(tile, dict) and bool(tile.get("animal")) and not tile.get("cared_today", False)
    if op == "COLLECT_FERTILIZER":
        return isinstance(tile, dict) and bool(tile.get("animal")) and tile.get("fertilizer_available", False)
    return False


def _anchor_error(obs, expected):
    me = obs["farms"][obs["player"]]
    expected_crops = expected.get("crops", {})
    actual_crops = _crops(me)
    expected_animals = expected.get("animals", {})
    actual_animals = _animal_counts(me)
    return {
        "step": int(obs["step"]),
        "money_delta": float(me["money"]) - float(expected.get("money", me["money"])),
        "hand_delta": len(me["hands"]) - int(expected.get("hand_count", 0)),
        "quadrant_delta": len(me["unlocked_quadrants"]) - len(expected.get("quadrants", [])),
        "crop_l1": sum(abs(actual_crops.get(item, 0) - expected_crops.get(item, 0)) for item in CROPS),
        "animal_l1": sum(abs(actual_animals.get(item, 0) - expected_animals.get(item, 0)) for item in ANIMALS),
    }


def make_v27_agent():
    route = _ROUTE
    route_actions = route["consensus_actions"]
    state = {}
    telemetry = _blank_metrics(route)

    def reset():
        state.clear()
        state.update({
            "mode": "TRACK", "previous_mapping": {}, "repair_queues": {},
            "repair_started": {}, "pending": [], "failed_milestones": 0,
            "sell_reservations": {}, "positional_bad_streak": 0,
        })
        telemetry.clear()
        telemetry.update(_blank_metrics(route))

    def choose_route_action(obs):
        step = min(int(obs["step"]), 718)
        action = deepcopy(route_actions[step])
        expected = route["expected_state"][step]
        expected_positions = expected.get("hands", [])
        expected_actions = list(action.get("hands", []))
        actual_positions = obs["farms"][obs["player"]]["hands"]
        mapping, error, rematches = _match_workers(
            actual_positions, expected_positions, expected_actions, state["previous_mapping"]
        )
        state["previous_mapping"] = {index: value for index, value in enumerate(mapping) if value is not None}
        telemetry["worker_rematches"] += rematches
        telemetry["position_error_sum"] += error
        telemetry["position_error_observations"] += max(1, len(actual_positions))
        actual_actions = []
        for expected_index in mapping:
            actual_actions.append(deepcopy(expected_actions[expected_index]) if expected_index is not None else ["PASS"])
        if len(expected_actions) > len(actual_actions):
            telemetry["dropped_route_actions"] += len(expected_actions) - len(actual_actions)
        if len(actual_actions) > len(expected_actions):
            telemetry["extra_worker_passes"] += len(actual_actions) - len(expected_actions)
        action["hands"] = actual_actions
        return action, mapping

    def weed_repair(obs, action, mapping):
        step = int(obs["step"])
        me = obs["farms"][obs["player"]]
        positions = [me["farmer"], *me["hands"]]
        fields = [action["farmer"], *action["hands"]]
        identities = [-1, *[value if value is not None else 1000 + index for index, value in enumerate(mapping)]]
        if obs["hour"] == 0:
            for identity, queue in list(state["repair_queues"].items()):
                if queue:
                    telemetry["repair_abort"] += 1
                state["repair_queues"].pop(identity, None)
                state["repair_started"].pop(identity, None)
        for unit_index, (identity, position) in enumerate(zip(identities, positions)):
            planned = fields[unit_index]
            queue = state["repair_queues"].setdefault(identity, [])
            if queue:
                if step - state["repair_started"].get(identity, step) >= 8:
                    queue.clear()
                    telemetry["repair_abort"] += 1
                    state["repair_started"].pop(identity, None)
                    continue
                if planned[0] != "PASS" and len(queue) < 8:
                    queue.append(deepcopy(planned))
                queued = queue[0]
                if _unit_legal(obs, unit_index, queued):
                    fields[unit_index] = queue.pop(0)
                    if not queue:
                        telemetry["repair_success"] += 1
                        telemetry["repair_durations"].append(step - state["repair_started"].pop(identity, step))
                else:
                    fields[unit_index] = ["PASS"]
                continue
            x, y = position
            tile = me["tiles"][y][x]
            if planned[0] in ({"PLANT"} | BUILD) and isinstance(tile, dict) and tile.get("kind") == "WEED":
                state["repair_queues"][identity] = [deepcopy(planned)]
                state["repair_started"][identity] = step
                fields[unit_index] = ["DIG"]
                telemetry["repairs"]["weed"] += 1
        action["farmer"], action["hands"] = fields[0], fields[1:]
        return action

    def agent(obs):
        if int(obs.get("step", 0)) == 0 or not state:
            reset()
        telemetry["calls"] += 1
        step = min(int(obs["step"]), 718)
        telemetry["anchor_error"].append(_anchor_error(obs, route["expected_state"][step]))
        original, mapping = choose_route_action(obs)
        output = weed_repair(obs, deepcopy(original), mapping)
        mode = "REPAIR" if any(state["repair_queues"].values()) else "TRACK"
        state["mode"] = mode
        telemetry["mode_steps"][mode] += 1
        telemetry["farmer_route_requests"] += 1
        telemetry["farmer_route_matches"] += output["farmer"] == original["farmer"]
        telemetry["market_route_requests"] += 1
        telemetry["market_route_matches"] += output["market"] == original["market"]
        telemetry["hand_route_requests"] += len(original["hands"])
        telemetry["hand_route_matches"] += sum(a == b for a, b in zip(output["hands"], original["hands"]))
        pieces = 2 + len(original["hands"])
        matches = (output["farmer"] == original["farmer"]) + (output["market"] == original["market"])
        matches += sum(a == b for a, b in zip(output["hands"], original["hands"]))
        telemetry["all_route_requests"] += pieces
        telemetry["all_route_matches"] += matches
        return output

    agent.telemetry = telemetry
    agent.route = route
    agent.stage = 3
    agent.stage_name = STAGE_NAME
    return agent


agent = make_v27_agent()
'''.replace("__PACKED__", wrapped)
    OUTPUT.write_text(textwrap.dedent(output))
    print(OUTPUT)
    print(f"source_sha256={actual}")
    print(f"submission_sha256={sha256(OUTPUT)}")


if __name__ == "__main__":
    main()
