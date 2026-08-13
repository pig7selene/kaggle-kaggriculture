"""V27 replay backbone with strictly staged, bounded correction modules.

This is research infrastructure, not a submission bundle.  Normal execution is
the public replay route.  Each numbered stage adds exactly the correction named
in ``STAGE_NAMES``; no existing online crop planner/router is consulted unless
K9 enters its one-way catastrophic FALLBACK mode.
"""

from __future__ import annotations

from copy import deepcopy
from itertools import permutations
import json
import math
from pathlib import Path
from runpy import run_path

from kaggle_environments.envs.kaggriculture import kaggriculture as _game


ROOT = Path(__file__).resolve().parents[1]
ROUTE_BANK = json.loads((ROOT / "experiments/v27_route_manifest.json").read_text())
RISK_PATH = ROOT / "experiments/v27_market_risk_analysis.json"
RISK_TABLE = {}
if RISK_PATH.is_file():
    for row in json.loads(RISK_PATH.read_text()).get("hazard_table", []):
        RISK_TABLE[(row["product"], row["bucket"], int(row["horizon"]))] = float(row["smoothed_probability"])
DEFAULT_ROUTE_ID = "v27_family_3_victor_at_tufa_labs"

STAGE_NAMES = {
    0: "K0_raw_single_trace",
    1: "K1_multi_replay_stable_backbone",
    2: "K2_anchors_worker_matching",
    3: "K3_weed_transaction_repair",
    4: "K4_critical_capital_repair",
    5: "K5_cost_aware_hire",
    6: "K6_hard_survival_guards",
    7: "K7_current_sell_reordering",
    8: "K8_future_sell_slot_assignment",
    9: "K9_one_way_fallback",
}

MOVES = {"NORTH", "SOUTH", "EAST", "WEST"}
BUILD = {"BUILD_COOP", "BUILD_PASTURE"}
CROPS = set(_game.CROPS)
ANIMALS = set(_game.ANIMALS)
PRODUCTS = set(_game.PRODUCTS)
SHED_TILES = {(4, 4), (5, 4), (4, 5), (5, 5)}
LAND_COSTS = (1000, 2000, 4000)


def _route(route_id):
    for candidate in ROUTE_BANK["routes"]:
        if candidate["route_id"] == route_id:
            return candidate
    raise KeyError(route_id)


def _fib(index):
    a, b = 1, 1
    for _ in range(max(0, int(index))):
        a, b = b, a + b
    return a


def _blank_metrics(stage, route):
    return {
        "stage": STAGE_NAMES[stage],
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


def _structures(farm):
    out = {"COOP": 0, "PASTURE": 0}
    for row in farm["tiles"]:
        for tile in row:
            if isinstance(tile, dict) and tile.get("kind") in out:
                out[tile["kind"]] += 1
    return out


def _crops(farm):
    out = {}
    for row in farm["tiles"]:
        for tile in row:
            if isinstance(tile, dict) and tile.get("kind") == "PLANT":
                crop = tile.get("crop")
                out[crop] = out.get(crop, 0) + 1
    return out


def _owned(obs, item):
    private = obs["private"]
    count = int(private.get("shed", {}).get(item, 0))
    count += sum(int(inventory.get(item, 0)) for inventory in private.get("inventories", []))
    if item in ANIMALS:
        count += _animal_counts(obs["farms"][obs["player"]]).get(item, 0)
    return count


def _count_for_confirmation(obs, order):
    op = order[0]
    if op == "BUY_LAND":
        return len(obs["farms"][obs["player"]]["unlocked_quadrants"])
    if op == "HIRE":
        return len(obs["farms"][obs["player"]]["hands"])
    if op == "BUY_ANIMAL":
        return _owned(obs, order[1])
    if op == "BUY_SEED":
        return int(obs["private"]["seeds"].get(order[1], 0))
    if op == "BUY_PRODUCT":
        return _owned(obs, order[1])
    return 0


def _expected_count(expected, order):
    op = order[0]
    if op == "BUY_LAND":
        return len(expected.get("quadrants", []))
    if op == "HIRE":
        return int(expected.get("hand_count", 0))
    item = order[1]
    if op == "BUY_SEED":
        return int(expected.get("seeds", {}).get(item, 0))
    count = int(expected.get("shed", {}).get(item, 0))
    count += sum(int(inventory.get(item, 0)) for inventory in expected.get("inventories", []))
    if op == "BUY_ANIMAL":
        count += int(expected.get("animals", {}).get(item, 0))
    return count


def _critical(order):
    if not order:
        return False
    if order[0] in {"BUY_LAND", "BUY_ANIMAL", "HIRE"}:
        return True
    if order[0] == "BUY_PRODUCT" and order[1] == "WHEAT":
        return True
    return order[0] == "BUY_SEED" and int(order[2]) >= 5


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
    """Return actual-index -> expected-index with position/continuity priority."""
    if len(actual) == len(expected) and all(list(a) == list(e) for a, e in zip(actual, expected)):
        return list(range(len(actual))), 0, 0
    unused = set(range(len(expected)))
    mapping = [None] * len(actual)
    total_error = 0
    rematches = 0
    # Exact positions and prior ownership first.
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


def _sell_revenue(item, quantity, inventory, params=None):
    revenue = 0
    inv = int(inventory)
    terminal = _game.market_price(item, inv, params)
    for _ in range(max(0, int(quantity))):
        price = _game.market_price(item, inv, params)
        revenue += price
        if price > 1:
            inv += 1
        terminal = _game.market_price(item, inv, params)
    return revenue, terminal, inv


def _simulate_own_market(obs, orders):
    """Exact one-player sequence; opponent scenarios are layered by K8."""
    money = float(obs["farms"][obs["player"]]["money"])
    shed = dict(obs["private"]["shed"])
    seeds = dict(obs["private"]["seeds"])
    inventory = dict(obs["market"]["inventory"])
    params = obs["market"].get("params")
    revenue = 0.0
    sell_detail = []
    hires = int(obs["farms"][obs["player"]].get("hires_today", 0))
    quadrants = len(obs["farms"][obs["player"]]["unlocked_quadrants"])
    for order in list(orders)[:10]:
        if not order:
            continue
        op = order[0]
        if op == "HIRE":
            cost = _fib(hires)
            if money >= cost:
                money -= cost
                hires += 1
        elif op == "BUY_LAND":
            index = quadrants - 1
            if index < len(LAND_COSTS) and money >= LAND_COSTS[index]:
                money -= LAND_COSTS[index]
                quadrants += 1
        elif op == "SELL" and order[1] in PRODUCTS:
            item, requested = order[1], int(order[2])
            quantity = min(requested, int(shed.get(item, 0)))
            value, terminal, end_inventory = _sell_revenue(item, quantity, inventory[item], params)
            money += value
            revenue += value
            shed[item] = int(shed.get(item, 0)) - quantity
            inventory[item] = end_inventory
            sell_detail.append({"item": item, "quantity": quantity, "revenue": value, "terminal_quote": terminal})
        elif op == "BUY_SEED" and order[1] in CROPS:
            item = order[1]
            cost = int(_game.CROPS[item]["seed"])
            quantity = min(int(order[2]), int(money // cost))
            money -= quantity * cost
            seeds[item] = seeds.get(item, 0) + quantity
        elif op == "BUY_ANIMAL" and order[1] in ANIMALS:
            item = order[1]
            cost = int(_game.ANIMALS[item]["cost"])
            room = max(0, 100 - sum(shed.values()))
            quantity = min(int(order[2]), int(money // cost), room)
            money -= quantity * cost
            shed[item] = shed.get(item, 0) + quantity
        elif op == "BUY_PRODUCT" and order[1] in {"WHEAT", "FERTILIZER"}:
            item = order[1]
            committed = 0
            for _ in range(int(order[2])):
                price = _game.market_price(item, inventory[item] - 1, params)
                if money < price or sum(shed.values()) >= 100:
                    break
                money -= price
                shed[item] = shed.get(item, 0) + 1
                inventory[item] -= 1
                committed += 1
    return {"money": money, "sell_revenue": revenue, "sell_detail": sell_detail, "inventory": inventory}


def _reorder_current_sells(obs, market):
    slots = [index for index, order in enumerate(market) if order and order[0] == "SELL"]
    if len(slots) < 2 or len(slots) > 7:
        result = _simulate_own_market(obs, market)
        return market, result, result
    original = _simulate_own_market(obs, market)
    sell_orders = [market[index] for index in slots]
    best_market, best = list(market), original
    for candidate_orders in permutations(sell_orders):
        candidate = deepcopy(market)
        for index, order in zip(slots, candidate_orders):
            candidate[index] = list(order)
        result = _simulate_own_market(obs, candidate)
        # Stable tie-break keeps the source ordering.
        if result["money"] > best["money"] + 1e-9:
            best_market, best = candidate, result
    return best_market, original, best


def _future_slot_assignment(obs, market, route_actions, reservations, hazard=None):
    """Bounded 12-turn reassignment among already existing SELL slots only."""
    step = int(obs["step"])
    current_slots = [index for index, order in enumerate(market) if order and order[0] == "SELL"]
    if not current_slots:
        return market, 0
    future_products = []
    for future_step in range(step + 1, min(719, step + 13)):
        for index, order in enumerate(route_actions[future_step]["market"]):
            if order and order[0] == "SELL":
                future_products.append((future_step, index, order[1], int(order[2])))
    if not future_products:
        return market, 0
    changed = 0
    output = deepcopy(market)
    prices = obs["market"]["prices"]
    shed = obs["private"]["shed"]
    # Only pull forward a route-planned batch when it is already in the shed,
    # has higher current capital value, and the displaced batch has a real
    # future slot.  No slot or non-SELL action is created/moved.
    for slot in current_slots:
        current = output[slot]
        best = None
        for future_step, future_index, item, requested in future_products:
            if item == current[1] or shed.get(item, 0) <= 0:
                continue
            quantity = min(requested, int(shed.get(item, 0)))
            immediate = _sell_revenue(item, quantity, obs["market"]["inventory"][item], obs["market"].get("params"))[0]
            old = _sell_revenue(current[1], min(int(current[2]), int(shed.get(current[1], 0))), obs["market"]["inventory"][current[1]], obs["market"].get("params"))[0]
            hazard_probability = float((hazard or {}).get(item, 0.0))
            # Stage B is intentionally conservative: a future route batch is
            # pulled forward only under calibrated opponent-first pressure and
            # a material current-capital benefit.  This prevents speculative
            # slot churn in the source trace.
            capital_gain = immediate - old
            threshold = max(500.0, old * 0.18)
            if hazard_probability >= 0.65 and capital_gain > threshold:
                score = capital_gain * (0.5 + hazard_probability)
                if best is None or score > best[0]:
                    best = (score, future_step, future_index, item, quantity)
        if best is not None:
            _, future_step, future_index, item, quantity = best
            reservations[(future_step, future_index)] = list(current)
            output[slot] = ["SELL", item, quantity]
            changed += 1
    return output, changed


def _opponent_hazard(obs):
    player = int(obs["player"])
    farm = obs["farms"][1 - player]
    ready = {item: 0 for item in PRODUCTS}
    animal_product = {"GOOSE": "EGG", "COW": "MILK", "SHEEP": "WOOL"}
    for row in farm["tiles"]:
        for tile in row:
            if not isinstance(tile, dict) or tile.get("yield_units", 0) <= 0:
                continue
            item = tile.get("crop") if tile.get("kind") == "PLANT" else animal_product.get(tile.get("animal"))
            if item in ready:
                ready[item] += int(tile.get("yield_units", 0))
    near = sum(tuple(position) in SHED_TILES for position in [farm["farmer"], *farm.get("hands", [])])
    phase = "early" if obs["day"] < 10 else ("mid" if obs["day"] < 24 else "late")
    output = {}
    for item in PRODUCTS:
        ready_bucket = "ready0" if ready[item] == 0 else ("ready1_4" if ready[item] <= 4 else "ready5p")
        shed_bucket = "shed0" if near == 0 else ("shed1" if near == 1 else "shed2p")
        bucket = f"{ready_bucket}|{shed_bucket}|{phase}"
        output[item] = RISK_TABLE.get((item, bucket, 12), RISK_TABLE.get((item, "ALL", 12), 0.0))
    return output


def _sanitize(obs, action):
    """Schema-only rollback; never erase a valid replay no-op.

    The engine intentionally accepts surplus FEED/FERTILIZE arguments and
    sequential same-tile actions can make a later request a harmless no-op.
    Replacing those in TRACK would damage fidelity, so state legality is left
    to bounded modules and only irreparably malformed output is sanitized.
    """
    me = obs["farms"][obs["player"]]
    required = len(me["hands"])
    hands = list(action.get("hands", []))
    hands.extend([["PASS"]] * max(0, required - len(hands)))
    fields = [action.get("farmer", ["PASS"]), *hands[:required]]
    sanitized = 0
    valid_unit = MOVES | {"PASS", "PLANT", "WATER", "HARVEST", "FERTILIZE", "DIG", "BUILD_COOP", "BUILD_PASTURE", "PICKUP", "DROP", "PLACE", "FEED", "CARE", "COLLECT_FERTILIZER"}
    for index, value in enumerate(fields):
        if not isinstance(value, list) or not value or value[0] not in valid_unit:
            fields[index] = ["PASS"]
            sanitized += 1
    market = []
    valid_market = {"HIRE", "BUY_LAND", "BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL"}
    for order in list(action.get("market", []))[:10]:
        if not isinstance(order, list) or not order or order[0] not in valid_market:
            sanitized += 1
            continue
        market.append(deepcopy(order))
    return {"farmer": fields[0], "hands": fields[1:], "market": market}, sanitized


def make_v27_agent(
    stage=9,
    route_id=DEFAULT_ROUTE_ID,
    fallback_path="agents/lifecycle_lc_combined.py",
    route_override=None,
):
    stage = int(stage)
    route = route_override if route_override is not None else _route(route_id)
    route_actions = route["actions"] if stage == 0 else route["consensus_actions"]
    fallback = None
    if stage >= 9:
        fallback = run_path(str(ROOT / fallback_path))["agent"]

    state = {}
    telemetry = _blank_metrics(stage, route)

    def reset():
        state.clear()
        state.update({
            "mode": "TRACK", "previous_mapping": {}, "repair_queues": {},
            "repair_started": {}, "pending": [], "failed_milestones": 0,
            "sell_reservations": {}, "positional_bad_streak": 0,
        })
        telemetry.clear()
        telemetry.update(_blank_metrics(stage, route))

    def failure(module):
        telemetry["module_errors"][module] = telemetry["module_errors"].get(module, 0) + 1

    def choose_route_action(obs):
        step = min(int(obs["step"]), 718)
        action = deepcopy(route_actions[step])
        required = len(obs["farms"][obs["player"]]["hands"])
        if stage < 2:
            hands = list(action.get("hands", []))
            hands.extend([["PASS"]] * max(0, required - len(hands)))
            action["hands"] = hands[:required]
            return action, list(range(min(required, len(hands))))

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
        if stage < 3:
            return action
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

    def confirm_and_repair_market(obs, action):
        if stage < 4:
            return action
        step = int(obs["step"])
        survivors = []
        for pending in state["pending"]:
            if step <= pending["planned_step"]:
                survivors.append(pending)
                continue
            actual = _count_for_confirmation(obs, pending["order"])
            if actual >= pending["expected"]:
                telemetry["critical_confirmed"] += 1
                telemetry["critical_events"].append({"step": step, "event": "confirmed", "order": pending["order"], "delay": step - pending["planned_step"]})
                if pending.get("retried"):
                    telemetry["repair_success"] += 1
                    telemetry["repair_durations"].append(step - pending["planned_step"])
                continue
            if step > pending["deadline"] or (pending["order"][0] == "HIRE" and obs["hour"] == 0):
                telemetry["critical_failed"] += 1
                telemetry["repair_abort"] += 1
                state["failed_milestones"] += 1
                telemetry["critical_events"].append({"step": step, "event": "aborted", "order": pending["order"], "delay": step - pending["planned_step"]})
                continue
            survivors.append(pending)
        state["pending"] = survivors

        market = deepcopy(action["market"])
        for pending in state["pending"]:
            if pending.get("last_retry") == step or any(order == pending["order"] for order in market):
                continue
            if len(market) >= 10:
                continue
            # Existing sells remain first so their cash can fund the retry.
            insert = 1 + max((i for i, order in enumerate(market) if order and order[0] == "SELL"), default=-1)
            market.insert(insert, deepcopy(pending["order"]))
            pending["last_retry"] = step
            pending["retried"] = True
            telemetry["repairs"]["capital"] += 1
            telemetry["critical_events"].append({"step": step, "event": "retry", "order": pending["order"], "delay": step - pending["planned_step"]})
            if pending["order"][0] == "HIRE":
                telemetry["hire_retried"] += 1
        action["market"] = market[:10]
        return action

    def cost_aware_hires(obs, action):
        if stage < 5:
            return action
        step = int(obs["step"])
        me = obs["farms"][obs["player"]]
        target = route["expected_state"][min(718, step + 1)].get("hand_count", 0)
        projected = len(me["hands"])
        hires_today = int(me.get("hires_today", 0))
        money = float(me["money"])
        sale_cash = sum(
            min(int(order[2]), int(obs["private"]["shed"].get(order[1], 0))) * obs["market"]["prices"].get(order[1], 1) * 0.85
            for order in action["market"] if order and order[0] == "SELL"
        )
        budget = money + sale_cash
        reserve = 0
        for future in range(step, min(719, step + 9)):
            for order in route_actions[future]["market"]:
                if order[0] == "BUY_LAND":
                    index = len(me["unlocked_quadrants"]) - 1
                    reserve = max(reserve, LAND_COSTS[index] if index < 3 else 0)
                elif order[0] == "BUY_ANIMAL":
                    reserve = max(reserve, int(order[2]) * int(_game.ANIMALS[order[1]]["cost"]))
        output = []
        accepted = 0
        for order in action["market"]:
            if not order or order[0] != "HIRE":
                output.append(order)
                continue
            telemetry["hire_planned"] += 1
            cost = _fib(hires_today + accepted)
            remaining = max(0, 23 - int(obs["hour"]))
            urgent = sum(
                bool(isinstance(tile, dict)
                and ((tile.get("kind") == "PLANT" and not tile.get("watered_today", False))
                     or (tile.get("animal") and not tile.get("fed_today", False))))
                for row in me["tiles"] for tile in row
            )
            value = remaining * 18 + min(urgent, remaining) * 20
            capital_opportunity = max(0.0, reserve - (budget - cost)) * 0.15
            proceed = projected + accepted < target and budget >= cost and value > cost + capital_opportunity
            if proceed:
                output.append(order)
                budget -= cost
                accepted += 1
                telemetry["hire_executed"] += 1
                telemetry["hire_spend_estimate"] += cost
            else:
                telemetry["hire_suppressed"] += 1
                telemetry["repairs"]["hire"] += 1
        action["market"] = output
        return action

    def survival_guards(obs, action):
        if stage < 6:
            return action
        me = obs["farms"][obs["player"]]
        positions = [me["farmer"], *me["hands"]]
        inventories = obs["private"]["inventories"]
        fields = [action["farmer"], *action["hands"]]
        planned_by_position = {}
        for position, planned in zip(positions, fields):
            planned_by_position.setdefault(tuple(position), []).append(planned[0] if planned else "PASS")
        for index, (position, inventory) in enumerate(zip(positions, inventories)):
            x, y = position
            tile = me["tiles"][y][x]
            planned = fields[index]
            if not isinstance(tile, dict):
                continue
            if (
                tile.get("animal") and not tile.get("fed_today", False)
                and tile.get("consecutive_unfed", 0) >= 1 and obs["hour"] == 23
                and inventory.get("WHEAT", 0) > 0 and planned[0] != "FEED"
                and "FEED" not in planned_by_position.get(tuple(position), [])
                and (
                    int(obs["step"]) >= 718
                    or sum(_animal_counts(me).values())
                    <= sum(route["expected_state"][int(obs["step"]) + 1].get("animals", {}).values())
                )
            ):
                fields[index] = ["FEED"]
                telemetry["repairs"]["survival"] += 1
                telemetry["safety_events"].append({"step": int(obs["step"]), "unit": index, "reason": "imminent_animal_escape", "overridden": planned})
            elif (
                tile.get("kind") == "PLANT" and not tile.get("watered_today", False)
                and tile.get("consecutive_unwatered", 0) >= 1 and obs["hour"] == 23
                and planned[0] != "WATER"
                and "WATER" not in planned_by_position.get(tuple(position), [])
                and _anchor_error(obs, route["expected_state"][int(obs["step"])])["crop_l1"] > 0
            ):
                fields[index] = ["WATER"]
                telemetry["repairs"]["survival"] += 1
                telemetry["safety_events"].append({"step": int(obs["step"]), "unit": index, "reason": "imminent_crop_death", "overridden": planned})
            elif planned[0] == "HARVEST" and tile.get("kind") == "PLANT":
                crop = tile.get("crop")
                data = _game.CROPS[crop]
                age = obs["day"] - tile.get("planted_day", obs["day"])
                if (
                    not data.get("ongoing") and not tile.get("watered_today", False)
                    and math.ceil(data["max_yield_day"] / 2) <= age <= data["max_yield_day"]
                    and tile.get("yield_units", 0) < data["max_yield"] and obs["hour"] <= 21
                ):
                    fields[index] = ["WATER"]
                    telemetry["repairs"]["survival"] += 1
                    telemetry["safety_events"].append({"step": int(obs["step"]), "unit": index, "reason": "destructive_harvest_veto", "overridden": planned})
        action["farmer"], action["hands"] = fields[0], fields[1:]
        return action

    def market_optimization(obs, action):
        if stage < 7:
            return action
        try:
            reordered, original, optimized = _reorder_current_sells(obs, action["market"])
            telemetry["original_sell_revenue_estimate"] += original["sell_revenue"]
            telemetry["optimized_sell_revenue_estimate"] += optimized["sell_revenue"]
            for detail in original["sell_detail"]:
                current = obs["market"]["prices"].get(detail["item"], 1)
                telemetry["exact_self_impact"] += detail["quantity"] * current - detail["revenue"]
            if reordered != action["market"]:
                telemetry["sell_reorders"] += 1
            action["market"] = reordered
        except Exception:
            failure("current_sell_reordering")
        if stage >= 8:
            try:
                # Honor a previously displaced batch only at the exact existing
                # route SELL slot; otherwise the route market stays untouched.
                step = int(obs["step"])
                for index, order in enumerate(action["market"]):
                    replacement = state["sell_reservations"].pop((step, index), None)
                    if replacement and order[0] == "SELL" and obs["private"]["shed"].get(replacement[1], 0) > 0:
                        action["market"][index] = replacement
                action["market"], changed = _future_slot_assignment(
                    obs, action["market"], route_actions, state["sell_reservations"], hazard=_opponent_hazard(obs)
                )
                telemetry["future_sell_assignments"] += changed
            except Exception:
                failure("future_sell_assignment")
        return action

    def mark_transactions(obs, action):
        if stage < 4:
            return
        step = int(obs["step"])
        if step >= 718:
            return
        next_expected = route["expected_state"][step + 1]
        for order in action["market"]:
            if not _critical(order):
                continue
            # Do not duplicate an already pending identical milestone.
            if any(value["order"] == order for value in state["pending"]):
                continue
            before = _count_for_confirmation(obs, order)
            expected = _expected_count(next_expected, order)
            # The public route contains speculative/no-op orders. A milestone
            # is repairable only when its own source trajectory confirms that
            # this order was expected to change the relevant state.
            if expected <= before:
                continue
            max_delay = min(8, 23 - obs["hour"]) if order[0] == "HIRE" else 8
            state["pending"].append({
                "order": deepcopy(order), "planned_step": step,
                "expected": expected, "deadline": step + max_delay,
            })

    def maybe_fallback(obs):
        if stage < 9 or state["mode"] == "FALLBACK":
            return
        step = int(obs["step"])
        expected = route["expected_state"][step]
        error = _anchor_error(obs, expected)
        positional = telemetry["position_error_sum"] / max(1, telemetry["position_error_observations"])
        due_land_steps = [
            value["step"] for value in route["critical_transactions"]
            if value["order"][0] == "BUY_LAND" and value["step"] <= step
        ]
        latest_due_land = max(due_land_steps, default=None)
        if error["quadrant_delta"] < 0 and latest_due_land is not None and step - latest_due_land > 8:
            reason = "land_milestone_overdue"
        elif state["failed_milestones"] >= 2:
            reason = "multiple_critical_failures"
        elif sum(bool(queue) for queue in state["repair_queues"].values()) >= 3:
            reason = "repair_queue_saturation"
        elif positional > 3.5 and step > 72:
            state["positional_bad_streak"] += 1
            if state["positional_bad_streak"] < 12:
                return
            reason = "persistent_worker_position_drift"
        else:
            state["positional_bad_streak"] = 0
            return
        state["mode"] = "FALLBACK"
        telemetry["fallback_step"] = step
        telemetry["fallback_reason"] = reason

    def agent(obs):
        if int(obs.get("step", 0)) == 0 or not state:
            reset()
        telemetry["calls"] += 1
        step = min(int(obs["step"]), 718)
        telemetry["anchor_error"].append(_anchor_error(obs, route["expected_state"][step]))
        maybe_fallback(obs)
        if state["mode"] == "FALLBACK":
            telemetry["mode_steps"]["FALLBACK"] += 1
            try:
                output = fallback(obs)
            except Exception:
                failure("fallback")
                output = {"farmer": ["PASS"], "hands": [["PASS"] for _ in obs["farms"][obs["player"]]["hands"]], "market": []}
            output, changes = _sanitize(obs, output)
            telemetry["semantic_sanitizations"] += changes
            return output

        original, mapping = choose_route_action(obs)
        output = deepcopy(original)
        output = weed_repair(obs, output, mapping)
        output = confirm_and_repair_market(obs, output)
        output = cost_aware_hires(obs, output)
        output = survival_guards(obs, output)
        output = market_optimization(obs, output)
        mark_transactions(obs, output)
        active_repairs = any(state["repair_queues"].values()) or any(value.get("retried") for value in state["pending"])
        mode = "REPAIR" if active_repairs else "TRACK"
        state["mode"] = mode
        telemetry["mode_steps"][mode] += 1

        if stage >= 9:
            output, changes = _sanitize(obs, output)
            telemetry["semantic_sanitizations"] += changes

        # Fidelity is measured against the selected K1 backbone before any
        # correction. Hand requests use the actual-output cardinality.
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
    agent.stage = stage
    agent.stage_name = STAGE_NAMES[stage]
    return agent
