"""Bounded V4 research modules layered on the immutable V2 backbone."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from runpy import run_path


ROOT = Path(__file__).resolve().parents[2]
PREMIUM = ("MELON", "STRAWBERRY", "MILK", "WOOL")
BASE_PRICE = {"MELON": 250, "STRAWBERRY": 120, "MILK": 160, "WOOL": 200}
ANIMAL_PRODUCT = {"GOOSE": "EGG", "COW": "MILK", "SHEEP": "WOOL"}
SHED_TILES = {(4, 4), (5, 4), (4, 5), (5, 5)}


def _v2():
    return run_path(str(ROOT / "agents/super_replay_v2/super_backbone_v2.py"))["agent"]


def _nazmus(raw=False):
    if not raw:
        return run_path(str(ROOT / "agents/super_replay_v3/v3_raw_55445174.py"))["agent"]
    bank = json.loads((ROOT / "experiments/v3_route_executor.json").read_text())
    route = next(row for row in bank["routes"] if row["route_id"] == "v3_raw_55445174")
    route = {
        **route, "actions": route["consensus_actions"], "critical_transactions": [],
        "variation_class_by_step": ["source_route"] * 719, "stability": {},
    }
    builder = run_path(str(ROOT / "agents/v27_backbone_common.py"))["make_v27_agent"]
    return builder(stage=0, route_override=route)


def _visible_ready(farm):
    ready = Counter()
    for row in farm["tiles"]:
        for tile in row:
            if not isinstance(tile, dict) or int(tile.get("yield_units", 0)) <= 0:
                continue
            item = tile.get("crop") if tile.get("kind") == "PLANT" else ANIMAL_PRODUCT.get(tile.get("animal"))
            if item:
                ready[item] += int(tile.get("yield_units", 0))
    return ready


def _visible_capacity(farm):
    capacity = Counter()
    for row in farm["tiles"]:
        for tile in row:
            if not isinstance(tile, dict):
                continue
            item = tile.get("crop") if tile.get("kind") == "PLANT" else ANIMAL_PRODUCT.get(tile.get("animal"))
            if item:
                capacity[item] += 1
    return capacity


def _market_sell_quantity(market, item):
    return sum(int(order[2]) for order in market if order and order[0] == "SELL" and order[1] == item)


def _append_sell(action, item, quantity):
    if quantity <= 0 or len(action["market"]) >= 10:
        return False
    action["market"].append(["SELL", item, int(quantity)])
    return True


def make_agent(*, module="V2", market_policy=None, cow_target=8, endgame=None, crop_wave=None):
    base = _nazmus(raw=(module == "N0")) if module.startswith("N") else _v2()
    state = {}
    telemetry = {}

    def reset():
        state.clear()
        state.update({
            "previous_market_inventory": None,
            "previous_prices": None,
            "nazmus_rescue": {},
        })
        telemetry.clear()
        telemetry.update({
            "module": module, "calls": 0, "backbone_actions_requested": 0,
            "backbone_actions_unchanged": 0, "dynamic_overrides": 0,
            "market_overrides": 0, "endgame_overrides": 0,
            "capital_overrides": 0, "crop_wave_overrides": 0,
            "livestock_rescue_overrides": 0, "override_log": [],
        })

    def log(obs, original, output, trigger, category, detail=None):
        if output == original:
            return
        telemetry["dynamic_overrides"] += 1
        telemetry[f"{category}_overrides"] += 1
        telemetry["override_log"].append({
            "step": int(obs["step"]), "day": int(obs["day"]), "hour": int(obs["hour"]),
            "trigger": trigger, "original": deepcopy(original), "override": deepcopy(output),
            "quotes": {item: int(obs["market"]["prices"].get(item, 0)) for item in PREMIUM},
            "market_inventory": {item: int(obs["market"]["inventory"].get(item, 0)) for item in PREMIUM},
            "detail": detail or {},
        })

    def market_control(obs, original, output):
        if not market_policy or not 336 <= int(obs["step"]) <= 671:
            return output
        me = obs["farms"][obs["player"]]
        other = obs["farms"][1 - obs["player"]]
        ready = _visible_ready(other)
        capacity = _visible_capacity(other)
        previous_inventory = state.get("previous_market_inventory") or obs["market"]["inventory"]
        previous_prices = state.get("previous_prices") or obs["market"]["prices"]
        changed = []
        if market_policy in {"hold_floor", "hold_low", "hold_safe"}:
            threshold_fraction = 0.10 if market_policy == "hold_floor" else 0.25
            shed_total = sum(int(value) for value in obs["private"]["shed"].values())
            safe_limit = 60 if market_policy == "hold_safe" else 78
            rewritten = []
            for order in output["market"]:
                if not order or order[0] != "SELL" or order[1] not in PREMIUM:
                    rewritten.append(order)
                    continue
                item = order[1]
                quote = int(obs["market"]["prices"].get(item, 1))
                if quote < BASE_PRICE[item] * threshold_fraction and shed_total <= safe_limit:
                    changed.append({
                        "item": item, "suppressed_quantity": int(order[2]), "quote": quote,
                        "shed_total": shed_total, "safe_limit": safe_limit,
                    })
                else:
                    rewritten.append(order)
            output["market"] = rewritten
            # A recovery does not need to wait for the original commodity's
            # next hard-coded slot: use an otherwise legal market-action slot.
            for item in PREMIUM:
                available = int(obs["private"]["shed"].get(item, 0)) - _market_sell_quantity(output["market"], item)
                quote = int(obs["market"]["prices"].get(item, 1))
                if available > 0 and quote >= BASE_PRICE[item] * threshold_fraction and len(output["market"]) < 10:
                    if _append_sell(output, item, available):
                        changed.append({"item": item, "recovery_sale": available, "quote": quote})
            if changed:
                log(obs, original, output, f"market:{market_policy}", "market", {"changes": changed})
            return output
        for item in PREMIUM:
            shed = int(obs["private"]["shed"].get(item, 0))
            already = _market_sell_quantity(output["market"], item)
            available = max(0, shed - already)
            if available <= 0:
                continue
            quote = int(obs["market"]["prices"].get(item, 1))
            inv_jump = int(obs["market"]["inventory"].get(item, 0)) - int(previous_inventory.get(item, 0))
            quote_drop = int(previous_prices.get(item, quote)) - quote
            pressure = ready[item] >= 4 or (capacity[item] >= 8 and ready[item] > 0) or inv_jump >= 4
            if market_policy == "day_boundary":
                trigger = int(obs["hour"]) <= 1
            elif market_policy == "visible_pressure":
                trigger = pressure and (int(obs["hour"]) <= 3 or quote_drop > 0 or inv_jump > 0)
            elif market_policy == "pressure_or_fair":
                trigger = pressure or quote >= BASE_PRICE[item]
            elif market_policy == "visible_pressure_half":
                trigger = pressure and (int(obs["hour"]) <= 3 or quote_drop > 0 or inv_jump > 0)
            else:
                trigger = False
            if not trigger:
                continue
            quantity = max(1, available // 2) if market_policy == "visible_pressure_half" else available
            if _append_sell(output, item, quantity):
                changed.append({
                    "item": item, "quantity": quantity, "quote": quote,
                    "opponent_ready": ready[item], "opponent_capacity": capacity[item],
                    "market_inventory_jump": inv_jump, "quote_drop": quote_drop,
                    "expected_next_v2_sale": _next_sale_step(base, int(obs["step"]), item),
                })
        if changed:
            log(obs, original, output, f"market:{market_policy}", "market", {"sales": changed})
        return output

    def capital_control(obs, original, output):
        if cow_target >= 8:
            return output
        bought_before = 1 + (1 if int(obs["step"]) >= 120 else 0) + (4 if int(obs["step"]) >= 192 else 0)
        # The only V2 cow purchase that exceeds six is the two-cow order at
        # step 192.  Quantity limiting preserves order position and all other
        # capital decisions.
        market = []
        changed = []
        remaining = max(0, int(cow_target) - min(6, bought_before))
        for order in output["market"]:
            if order and order[0] == "BUY_ANIMAL" and order[1] == "COW" and int(obs["step"]) == 192:
                keep = min(int(order[2]), remaining)
                if keep:
                    market.append(["BUY_ANIMAL", "COW", keep])
                changed.append({"original_quantity": int(order[2]), "kept_quantity": keep})
            else:
                market.append(order)
        output["market"] = market
        if changed:
            log(obs, original, output, f"capital:cows{cow_target}", "capital", {"orders": changed})
        return output

    def endgame_control(obs, original, output):
        if not endgame:
            return output
        step = int(obs["step"])
        removed = []
        if endgame == "no_day29_hires" and step >= 696:
            kept = []
            for order in output["market"]:
                if order and order[0] == "HIRE":
                    removed.append(order)
                else:
                    kept.append(order)
            output["market"] = kept
        elif endgame == "no_seed_after_day25" and step >= 600:
            kept = []
            for order in output["market"]:
                if order and order[0] == "BUY_SEED":
                    removed.append(order)
                else:
                    kept.append(order)
            output["market"] = kept
        elif endgame == "liquidate_from_day27" and step >= 648:
            for item in PREMIUM:
                remaining = int(obs["private"]["shed"].get(item, 0)) - _market_sell_quantity(output["market"], item)
                if remaining > 0 and _append_sell(output, item, remaining):
                    removed.append(["ADDED_SELL", item, remaining])
        if removed:
            log(obs, original, output, f"endgame:{endgame}", "endgame", {"changes": removed, "turns_remaining": 719 - step})
        return output

    def wave_control(obs, original, output):
        if not crop_wave:
            return output
        changes = []
        if crop_wave == "wheat40_day20" and int(obs["step"]) == 481:
            for order in output["market"]:
                if order and order[0] == "BUY_SEED" and order[1] == "WHEAT" and int(order[2]) == 46:
                    order[2] = 40
                    changes.append({"order": "BUY_SEED_WHEAT", "from": 46, "to": 40})
        elif crop_wave == "wheat34_day20" and int(obs["step"]) == 481:
            for order in output["market"]:
                if order and order[0] == "BUY_SEED" and order[1] == "WHEAT" and int(order[2]) == 46:
                    order[2] = 34
                    changes.append({"order": "BUY_SEED_WHEAT", "from": 46, "to": 34})
        if changes:
            log(obs, original, output, f"crop_wave:{crop_wave}", "crop_wave", {"changes": changes})
        return output

    def nazmus_rescue(obs, original, output):
        if module != "N2":
            return output
        me = obs["farms"][obs["player"]]
        positions = [me["farmer"], *me["hands"]]
        inventories = obs["private"]["inventories"]
        fields = [output["farmer"], *output["hands"]]
        active = state["nazmus_rescue"]

        # Continue the exact short transaction: hold on the shed-animal tile,
        # buy wheat, pick it up next turn, feed immediately after pickup.
        for index, position in enumerate(positions):
            key = tuple(position)
            phase = active.get(key)
            x, y = position
            tile = me["tiles"][y][x]
            if phase == "pickup" and isinstance(tile, dict) and tile.get("animal") and obs["private"]["shed"].get("WHEAT", 0) > 0:
                fields[index] = ["PICKUP", "WHEAT", 1]
                active[key] = "feed"
            elif phase == "feed" and isinstance(tile, dict) and tile.get("animal") and inventories[index].get("WHEAT", 0) > 0:
                fields[index] = ["FEED"]
                active.pop(key, None)

        new_starts = []
        if int(obs["hour"]) >= 7:
            for index, position in enumerate(positions):
                key = tuple(position)
                if key not in SHED_TILES or key in active:
                    continue
                x, y = position
                tile = me["tiles"][y][x]
                if not isinstance(tile, dict) or tile.get("animal") != "COW":
                    continue
                if tile.get("fed_today") or int(tile.get("consecutive_unfed", 0)) < 1:
                    continue
                if inventories[index].get("WHEAT", 0) > 0:
                    continue
                fields[index] = ["PASS"]
                active[key] = "pickup"
                new_starts.append({"unit": index, "position": list(position), "animal": "COW"})
        if new_starts:
            need = len(new_starts)
            if len(output["market"]) < 10:
                output["market"].append(["BUY_PRODUCT", "WHEAT", need])
        output["farmer"], output["hands"] = fields[0], fields[1:]
        if new_starts or output != original:
            log(obs, original, output, "livestock:imminent_known_shed_cow", "livestock_rescue", {"started": new_starts, "active": {str(k): v for k, v in active.items()}})
        return output

    def agent(obs):
        if int(obs.get("step", 0)) == 0 or not state:
            reset()
        telemetry["calls"] += 1
        original = deepcopy(base(obs))
        telemetry["backbone_actions_requested"] += 1
        output = deepcopy(original)
        output = capital_control(obs, original, output)
        output = wave_control(obs, original, output)
        output = market_control(obs, original, output)
        output = endgame_control(obs, original, output)
        output = nazmus_rescue(obs, original, output)
        if output == original:
            telemetry["backbone_actions_unchanged"] += 1
        state["previous_market_inventory"] = dict(obs["market"]["inventory"])
        state["previous_prices"] = dict(obs["market"]["prices"])
        return output

    agent.telemetry = telemetry
    agent.base = base
    agent.module = module
    return agent


def _next_sale_step(base, step, item):
    route = getattr(base, "route", {})
    actions = route.get("consensus_actions") or route.get("actions") or []
    for future in range(step + 1, min(len(actions), step + 49)):
        if any(order and order[0] == "SELL" and order[1] == item for order in actions[future].get("market", [])):
            return future
    return None
