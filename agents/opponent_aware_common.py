"""Conservative opponent-aware ablations around router_replay_hands12.

The frozen routed agent is loaded into a private runpy namespace.  The wrapper
changes only crop scoring, sale filtering, and/or relative-state hiring.  The
territory router, worker zones, animal specialists, crop task priority, animal
service batching, land ceiling, animal schedule, and phase schedule are left
untouched.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict, deque
from copy import deepcopy
from runpy import run_path


SOURCE_PATH = "agents/router_replay_hands12.py"
PRESSURE_SCALES = {
    "WHEAT": 24.0,
    "CARROT": 14.0,
    "TOMATO": 10.0,
    "STRAWBERRY": 12.0,
    "MELON": 30.0,
    "EGG": 10.0,
    "MILK": 9.0,
    "WOOL": 7.0,
    "FERTILIZER": 24.0,
}
PREMIUM_PRODUCTS = {"MELON", "STRAWBERRY", "MILK", "WOOL"}


def _fib(index):
    a, b = 1, 1
    for _ in range(index):
        a, b = b, a + b
    return a


def _is_plant(tile):
    return isinstance(tile, dict) and tile.get("kind") == "PLANT"


def _is_animal(tile):
    return bool(
        isinstance(tile, dict)
        and tile.get("kind") in {"COOP", "PASTURE"}
        and tile.get("animal")
    )


class OpponentState:
    """Public-only rolling opponent state and experiment instrumentation."""

    def __init__(self):
        self.last_step = -1
        self.last_market_inventory = None
        self.last_own_sales = Counter()
        self.recent_inferred_sales = defaultdict(lambda: deque(maxlen=48))
        self.first_shed_step = {}
        self.pending_sales = []
        self.latest_switches = {}
        self.metrics = self._fresh_metrics()

    @staticmethod
    def _fresh_metrics():
        return {
            "crop_switches": 0,
            "crop_switches_by_pair": Counter(),
            "crop_switch_events": [],
            "held_unit_turns": 0,
            "hold_events": 0,
            "sale_quantity": Counter(),
            "sale_revenue_notional": Counter(),
            "sale_prices": defaultdict(list),
            "pre_shock_sale_quantity": Counter(),
            "confirmed_price_drops_after_sale": 0,
            "relative_hires_added": 0,
            "relative_hire_events": [],
            "relative_state_by_day": [],
            "pressure_observations": Counter(),
            "pressure_level_observations": Counter(),
        }

    def reset(self):
        self.__init__()

    def observe(self, obs):
        step = int(obs.get("step", obs["day"] * 24 + obs["hour"]))
        if step == 0 or step <= self.last_step:
            self.reset()
        inventory = obs["market"]["inventory"]
        if self.last_market_inventory is not None:
            for product, current in inventory.items():
                increase = max(
                    0,
                    int(current) - int(self.last_market_inventory.get(product, current))
                    - int(self.last_own_sales.get(product, 0)),
                )
                self.recent_inferred_sales[product].append(increase)
        for product in inventory:
            if product not in self.recent_inferred_sales:
                self.recent_inferred_sales[product] = deque(maxlen=48)
            elif self.last_market_inventory is None:
                self.recent_inferred_sales[product].append(0)
        self.last_market_inventory = dict(inventory)
        self.last_own_sales = Counter()
        self.latest_switches = {}
        self.last_step = step

        shed = obs["private"]["shed"]
        for product, quantity in shed.items():
            if quantity > 0:
                self.first_shed_step.setdefault(product, step)
            else:
                self.first_shed_step.pop(product, None)

        prices = obs["market"]["prices"]
        remaining = []
        for event in self.pending_sales:
            if step - event["step"] < 48:
                remaining.append(event)
                continue
            future_price = prices.get(event["product"], event["price"])
            if future_price <= event["price"] * 0.85:
                self.metrics["confirmed_price_drops_after_sale"] += 1
        self.pending_sales = remaining

        if obs.get("hour") == 23:
            player = obs["player"]
            me = obs["farms"][player]
            opponent = obs["farms"][1 - player]
            self.metrics["relative_state_by_day"].append(
                {
                    "day": int(obs["day"]),
                    "bank_gap": float(me["money"] - opponent["money"]),
                    "land_gap": len(me["unlocked_quadrants"]) - len(opponent["unlocked_quadrants"]),
                    "labor_gap": len(me.get("hands", [])) - len(opponent.get("hands", [])),
                    "productive_gap": _productive(me) - _productive(opponent),
                    "livestock_gap": _animal_count(me) - _animal_count(opponent),
                }
            )

    def recent_sales(self, product):
        values = self.recent_inferred_sales.get(product, ())
        return sum(list(values)[-24:])

    def register_action(self, obs, action, pressure):
        me = obs["farms"][obs["player"]]
        unit_positions = [tuple(me["farmer"])] + [tuple(value) for value in me.get("hands", [])]
        unit_actions = [action.get("farmer", ["PASS"]), *action.get("hands", [])]
        for position, unit_action in zip(unit_positions, unit_actions):
            event = self.latest_switches.get(position)
            if not event or not isinstance(unit_action, list) or len(unit_action) < 2:
                continue
            if unit_action[0] != "PLANT" or unit_action[1] != event["to"]:
                continue
            self.metrics["crop_switches"] += 1
            self.metrics["crop_switches_by_pair"][f"{event['from']}->{event['to']}"] += 1
            if len(self.metrics["crop_switch_events"]) < 200:
                self.metrics["crop_switch_events"].append(event)
        own_sales = Counter()
        for order in action.get("market", []):
            if not isinstance(order, list) or len(order) < 3 or order[0] != "SELL":
                continue
            product, quantity = order[1], int(order[2])
            price = float(obs["market"]["prices"].get(product, 0))
            own_sales[product] += quantity
            self.metrics["sale_quantity"][product] += quantity
            self.metrics["sale_revenue_notional"][product] += quantity * price
            self.metrics["sale_prices"][product].append(price)
            if pressure.get(product, {}).get("level") == "HIGH":
                self.metrics["pre_shock_sale_quantity"][product] += quantity
                self.pending_sales.append(
                    {"step": self.last_step, "product": product, "quantity": quantity, "price": price}
                )
            if obs["private"]["shed"].get(product, 0) <= quantity:
                self.first_shed_step.pop(product, None)
        self.last_own_sales = own_sales

    def serialize_metrics(self):
        output = deepcopy(self.metrics)
        for key in (
            "crop_switches_by_pair",
            "sale_quantity",
            "sale_revenue_notional",
            "pre_shock_sale_quantity",
            "pressure_observations",
            "pressure_level_observations",
        ):
            output[key] = dict(output[key])
        output["sale_prices"] = {
            product: list(values) for product, values in output["sale_prices"].items()
        }
        return output


def _productive(farm):
    return sum(
        _is_plant(tile) or _is_animal(tile)
        for row in farm["tiles"] for tile in row
    )


def _animal_count(farm):
    return sum(_is_animal(tile) for row in farm["tiles"] for tile in row)


def _pressure(obs, state):
    """Estimate LOW/MEDIUM/HIGH public supply pressure for the next 3 days."""
    opponent = obs["farms"][1 - obs["player"]]
    day = int(obs["day"])
    raw = Counter()
    visible_area = Counter()
    for row in opponent["tiles"]:
        for tile in row:
            if _is_plant(tile):
                crop = tile["crop"]
                visible_area[crop] += 1
                data = _crop_data(crop)
                age = day - int(tile.get("planted_day", day))
                if tile.get("yield_units", 0) > 0 and age >= data["first"]:
                    raw[crop] += 0.35 * int(tile.get("yield_units", 0))
                if data["ongoing"]:
                    for future_age in range(age + 1, age + 4):
                        if future_age >= data["first"] and (future_age - data["first"]) % data["interval"] == 0:
                            raw[crop] += 1
                            break
                elif 0 <= data["peak"] - age <= 3:
                    raw[crop] += data["yield"]
            elif _is_animal(tile):
                animal = tile["animal"]
                data = _animal_data(animal)
                placed = int(tile.get("placed_day", day))
                for future_day in range(day + 1, day + 4):
                    since_first = future_day - placed - data["first"]
                    if since_first >= 0 and since_first % data["interval"] == 0:
                        raw[data["product"]] += 1
                raw["FERTILIZER"] += 0.40
    products = set(PRESSURE_SCALES)
    result = {}
    for product in products:
        area_prior = 0.0
        if product in visible_area:
            area_prior = visible_area[product] * (0.12 if product in {"WHEAT", "CARROT"} else 0.18)
        recent = state.recent_sales(product)
        amount = float(raw[product]) + area_prior + min(PRESSURE_SCALES[product], recent) * 0.35
        score = amount / PRESSURE_SCALES[product]
        level = "LOW" if score < 0.35 else "MEDIUM" if score < 0.90 else "HIGH"
        result[product] = {
            "amount": amount,
            "score": score,
            "level": level,
            "visible_area": int(visible_area[product]),
            "recent_inferred_sales": int(recent),
        }
    return result


def _crop_data(crop):
    # Kept local so the wrapper remains independent of an environment import.
    values = {
        "WHEAT": (2, 4, 6, False, 0),
        "CARROT": (2, 3, 4, False, 0),
        "TOMATO": (8, 8, 4, True, 1),
        "STRAWBERRY": (10, 10, 4, True, 2),
        "MELON": (10, 12, 6, False, 0),
    }[crop]
    return {"first": values[0], "peak": values[1], "yield": values[2], "ongoing": values[3], "interval": values[4]}


def _animal_data(animal):
    values = {
        "GOOSE": (4, 1, "EGG"),
        "COW": (8, 2, "MILK"),
        "SHEEP": (6, 3, "WOOL"),
    }[animal]
    return {"first": values[0], "interval": values[1], "product": values[2]}


def _crop_adjustment(pressure_score):
    # Smooth, bounded modifier: opponent information shifts an economic score
    # but cannot prohibit a crop or erase the replay-derived phase prior.
    return max(0.76, min(1.05, 1.05 * math.exp(-0.22 * pressure_score)))


def _make_crop_planner(namespace, state, *, record):
    original = namespace["_plan_crops"]
    economics = namespace["_candidate_economics"]
    crops = tuple(namespace["CROPS"])
    is_plant = namespace["_is_plant"]
    yield_before = namespace["_crop_yield_before"]

    def opponent_plan(obs, crop_positions, config):
        base_choices = original(obs, crop_positions, config)
        if obs["day"] < 6 or not base_choices:
            return base_choices
        pressure = _pressure(obs, state)
        tiles = obs["farms"][obs["player"]]["tiles"]
        planned = {crop: 0 for crop in crops}
        for position in crop_positions:
            tile = tiles[position[1]][position[0]]
            if is_plant(tile):
                planned[tile["crop"]] += 1
        for crop in base_choices.values():
            planned[crop] += 1
        empty_count = sum(not is_plant(tiles[y][x]) for x, y in base_choices)
        switch_budget = max(1, math.ceil(empty_count * 0.25))
        switches = 0
        choices = dict(base_choices)
        for position in sorted(base_choices, key=lambda value: namespace["ROUTE_ORDER"].get(value, 999)):
            if switches >= switch_budget:
                break
            x, y = position
            if is_plant(tiles[y][x]):
                continue
            base_crop = base_choices[position]
            ranked = []
            for crop in crops:
                if yield_before(crop, 28 - obs["day"])[0] <= 0:
                    continue
                item = economics(obs, crop, max(0, planned[crop] - (crop == base_crop)), config)
                if item is None:
                    continue
                phase_prior = 1.16 if crop == base_crop else 0.92
                adjusted = item["score"] * phase_prior * _crop_adjustment(pressure[crop]["score"])
                ranked.append((adjusted, item["profit"], crop, item["score"] * phase_prior))
            if not ranked:
                continue
            best = max(ranked)
            base_rows = [row for row in ranked if row[2] == base_crop]
            base_score = base_rows[0][0] if base_rows else 0.0
            if best[2] != base_crop and best[0] >= base_score * 1.08:
                choices[position] = best[2]
                planned[base_crop] = max(0, planned[base_crop] - 1)
                planned[best[2]] += 1
                switches += 1
                if record:
                    state.latest_switches[position] = {
                        "step": int(obs.get("step", 0)),
                        "day": int(obs["day"]),
                        "position": list(position),
                        "from": base_crop,
                        "to": best[2],
                        "from_pressure": pressure[base_crop]["level"],
                        "to_pressure": pressure[best[2]]["level"],
                        "adjusted_score_ratio": best[0] / max(1e-9, base_score),
                    }
        return choices

    return opponent_plan


def _make_sell_policy(namespace, state):
    original = namespace["_sell_orders"]
    base_prices = namespace["BASE_PRICES"]

    def opponent_sell(obs, config):
        orders = original(obs, config)
        if obs["day"] < 12:
            return orders
        step = int(obs.get("step", obs["day"] * 24 + obs["hour"]))
        pressure = _pressure(obs, state)
        occupied = sum(obs["private"]["shed"].values())
        forced = step >= 672 or occupied >= 72
        filtered = []
        for order in orders:
            if not isinstance(order, list) or len(order) < 3 or order[0] != "SELL":
                filtered.append(order)
                continue
            product, quantity = order[1], int(order[2])
            if product not in PREMIUM_PRODUCTS or forced:
                filtered.append(order)
                continue
            level = pressure[product]["level"]
            price = float(obs["market"]["prices"][product])
            base = float(base_prices[product])
            first_step = state.first_shed_step.get(product, step)
            age_days = (step - first_step) / 24.0
            should_hold = (
                (level == "LOW" and price < base * 1.02 and age_days < 2.0)
                or (level == "MEDIUM" and price < base * 0.90 and age_days < 1.0)
            )
            if should_hold:
                state.metrics["held_unit_turns"] += quantity
                state.metrics["hold_events"] += 1
            else:
                filtered.append(order)
        return filtered

    return opponent_sell


def _extra_relative_hire(obs, action, state):
    player = obs["player"]
    me = obs["farms"][player]
    opponent = obs["farms"][1 - player]
    if obs["day"] < 6 or obs["day"] >= 26 or len(action.get("market", [])) >= 10:
        return
    current = int(me.get("hires_today", 0))
    queued = sum(order and order[0] == "HIRE" for order in action.get("market", []))
    next_hire = current + queued
    if next_hire >= 12:
        return
    productive_gap = _productive(opponent) - _productive(me)
    labor_gap = len(opponent.get("hands", [])) - len(me.get("hands", []))
    land_gap = len(opponent.get("unlocked_quadrants", [])) - len(me.get("unlocked_quadrants", []))
    behind = productive_gap >= 12 or labor_gap >= 4 or (land_gap > 0 and productive_gap >= 7)
    cost = _fib(next_hire)
    if behind and me["money"] >= cost + 500:
        action["market"].append(["HIRE"])
        state.metrics["relative_hires_added"] += 1
        if len(state.metrics["relative_hire_events"]) < 200:
            state.metrics["relative_hire_events"].append(
                {
                    "step": int(obs.get("step", 0)),
                    "day": int(obs["day"]),
                    "cost": cost,
                    "productive_gap": productive_gap,
                    "labor_gap": labor_gap,
                    "land_gap": land_gap,
                }
            )


def make_agent(*, crop=False, selling=False, reinvestment=False):
    namespace = run_path(SOURCE_PATH)
    routed = namespace["agent"]
    state = OpponentState()

    router_source = routed.__globals__["SOURCE"]
    economic_sources = []
    seen = set()
    for component in routed.base_agent.components.values():
        source = component.__globals__
        if id(source) not in seen:
            seen.add(id(source))
            economic_sources.append(source)

    if crop:
        router_source["_plan_crops"] = _make_crop_planner(router_source, state, record=True)
        for source in economic_sources:
            source["_plan_crops"] = _make_crop_planner(source, state, record=False)
    if selling:
        for source in economic_sources:
            source["_sell_orders"] = _make_sell_policy(source, state)

    def opponent_agent(obs):
        state.observe(obs)
        pressure = _pressure(obs, state)
        for product, item in pressure.items():
            state.metrics["pressure_observations"][product] += 1
            state.metrics["pressure_level_observations"][f"{product}:{item['level']}"] += 1
        action = routed(obs)
        if reinvestment:
            _extra_relative_hire(obs, action, state)
        state.register_action(obs, action, pressure)
        return action

    opponent_agent.config = deepcopy(getattr(routed, "config", {}))
    opponent_agent.base_agent = routed
    opponent_agent.opponent_features = {
        "crop": bool(crop),
        "selling": bool(selling),
        "reinvestment": bool(reinvestment),
    }
    opponent_agent.get_metrics = state.serialize_metrics
    return opponent_agent
