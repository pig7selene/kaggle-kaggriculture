"""Trace livestock cash flows in local matches and the Hubbahub replay.

The environment exposes public bank balances but not a transaction ledger.  This
script temporarily wraps the environment's own market commit functions while a
game is running, so every reported dollar is an executed transaction rather
than the notional value of a submitted order.
"""

from __future__ import annotations

import argparse
import copy
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from kaggle_environments import make
from kaggle_environments.envs.kaggriculture import kaggriculture as game

from benchmark import ROOT, _load_agent


EXPERIMENTS = ROOT / "experiments"
PRODUCTS = tuple(game.PRODUCTS)
CROP_PRODUCTS = set(game.CROPS)
ANIMAL_PRODUCTS = {data["product"] for data in game.ANIMALS.values()}
ANIMAL_COSTS = {name: data["cost"] for name, data in game.ANIMALS.items()}
SEED_COSTS = {name: data["seed"] for name, data in game.CROPS.items()}


class TransactionTracer:
    def __init__(self):
        self.events = []
        self.step = 0
        self.player_for_farm = {}
        self._originals = {}

    def _record(self, player, kind, amount, item=None):
        self.events.append(
            {
                "step": self.step,
                "day": self.step // 24,
                "player": player,
                "kind": kind,
                "item": item,
                "amount": float(amount),
            }
        )

    def install(self):
        self._originals = {
            "process": game._process_market,
            "commit": game._commit_unit,
            "hire": game._do_hire,
            "land": game._do_buy_land,
        }
        tracer = self

        def process_market(state, env):
            obs = state[0].observation
            tracer.step = int(obs.step)
            tracer.player_for_farm = {
                id(farm): player for player, farm in enumerate(obs.farms)
            }
            return tracer._originals["process"](state, env)

        def commit_unit(op, item, price, farm, private, market, shed_capacity=100):
            ok = tracer._originals["commit"](
                op, item, price, farm, private, market, shed_capacity
            )
            if ok:
                player = tracer.player_for_farm[id(farm)]
                if op == "SELL":
                    tracer._record(player, "sale", price, item)
                elif op == "BUY_SEED":
                    tracer._record(player, "seed_spending", price, item)
                elif op == "BUY_ANIMAL":
                    tracer._record(player, "animal_spending", price, item)
                elif op == "BUY_PRODUCT":
                    tracer._record(player, "product_spending", price, item)
            return ok

        def do_hire(farm, private, board_size, mult=game.FARM_HAND_COST_MULT):
            before = float(farm["money"])
            tracer._originals["hire"](farm, private, board_size, mult)
            spent = before - float(farm["money"])
            if spent > 0:
                tracer._record(tracer.player_for_farm[id(farm)], "labor_spending", spent)

        def do_land(farm, board_size):
            before = float(farm["money"])
            tracer._originals["land"](farm, board_size)
            spent = before - float(farm["money"])
            if spent > 0:
                tracer._record(tracer.player_for_farm[id(farm)], "land_spending", spent)

        game._process_market = process_market
        game._commit_unit = commit_unit
        game._do_hire = do_hire
        game._do_buy_land = do_land

    def restore(self):
        if not self._originals:
            return
        game._process_market = self._originals["process"]
        game._commit_unit = self._originals["commit"]
        game._do_hire = self._originals["hire"]
        game._do_buy_land = self._originals["land"]


def _run_traced(agents, seed):
    tracer = TransactionTracer()
    tracer.install()
    try:
        env = make(
            "kaggriculture",
            configuration={"episodeSteps": 720, "seed": int(seed)},
            debug=True,
        )
        env.run(agents)
    finally:
        tracer.restore()
    final = env.steps[-1]
    if len(env.steps) != 720 or [state.status for state in final] != ["DONE", "DONE"]:
        raise RuntimeError("traced game did not complete normally")
    return env, tracer.events


def _held_products(private, farm):
    counts = Counter()
    for product in PRODUCTS:
        counts[product] += private["shed"].get(product, 0)
    for inventory in private["inventories"]:
        for product in PRODUCTS:
            counts[product] += inventory.get(product, 0)
    unharvested = Counter()
    for row in farm["tiles"]:
        for tile in row:
            if not isinstance(tile, dict) or tile.get("yield_units", 0) <= 0:
                continue
            if tile.get("kind") == "PLANT":
                unharvested[tile["crop"]] += tile["yield_units"]
            elif tile.get("animal") in game.ANIMALS:
                product = game.ANIMALS[tile["animal"]]["product"]
                unharvested[product] += tile["yield_units"]
    return counts, unharvested


def _snapshot(state, player, day):
    obs = state[player].observation
    farm = obs["farms"][player]
    private = obs["private"]
    crop_tiles = Counter()
    animals = Counter()
    structures = Counter()
    for row in farm["tiles"]:
        for tile in row:
            if not isinstance(tile, dict):
                continue
            if tile.get("kind") == "PLANT":
                crop_tiles[tile["crop"]] += 1
            elif tile.get("kind") in {"COOP", "PASTURE"}:
                structures[tile["kind"]] += 1
                if tile.get("animal"):
                    animals[tile["animal"]] += 1
    liquid, unharvested = _held_products(private, farm)
    prices = obs["market"]["prices"]
    liquid_value = sum(liquid[p] * prices[p] for p in PRODUCTS)
    unharvested_value = sum(unharvested[p] * prices[p] for p in PRODUCTS)
    return {
        "day": day,
        "bank": float(farm["money"]),
        "crop_tiles": dict(crop_tiles),
        "animal_tiles": dict(animals),
        "structures": dict(structures),
        "productive_tiles": sum(crop_tiles.values()) + sum(animals.values()),
        "liquid_inventory": dict(liquid),
        "unharvested_inventory": dict(unharvested),
        "liquid_inventory_value": float(liquid_value),
        "unharvested_inventory_value": float(unharvested_value),
        "total_inventory_value": float(liquid_value + unharvested_value),
        "economic_position": float(farm["money"] + liquid_value + unharvested_value),
        "hands": len(farm["hands"]),
        "quadrants": len(farm["unlocked_quadrants"]),
    }


def _event_rows(events, player):
    rows = []
    cumulative_income = 0.0
    cumulative_spending = 0.0
    grouped = defaultdict(list)
    for event in events:
        if event["player"] == player:
            grouped[event["day"]].append(event)
    for day in range(30):
        values = {
            "crop_revenue": 0.0,
            "animal_revenue": 0.0,
            "fertilizer_revenue": 0.0,
            "seed_spending": 0.0,
            "animal_purchase_spending": 0.0,
            "structure_spending": 0.0,
            "labor_spending": 0.0,
            "land_spending": 0.0,
            "feed_purchase_spending": 0.0,
            "other_product_spending": 0.0,
        }
        sold = Counter()
        for event in grouped[day]:
            kind = event["kind"]
            item = event["item"]
            amount = event["amount"]
            if kind == "sale":
                sold[item] += 1
                if item in CROP_PRODUCTS:
                    values["crop_revenue"] += amount
                elif item in ANIMAL_PRODUCTS:
                    values["animal_revenue"] += amount
                elif item == "FERTILIZER":
                    values["fertilizer_revenue"] += amount
            elif kind == "seed_spending":
                values["seed_spending"] += amount
            elif kind == "animal_spending":
                values["animal_purchase_spending"] += amount
            elif kind == "labor_spending":
                values["labor_spending"] += amount
            elif kind == "land_spending":
                values["land_spending"] += amount
            elif kind == "product_spending":
                target = (
                    "feed_purchase_spending"
                    if item == "WHEAT"
                    else "other_product_spending"
                )
                values[target] += amount
        income = (
            values["crop_revenue"]
            + values["animal_revenue"]
            + values["fertilizer_revenue"]
        )
        spending = sum(value for key, value in values.items() if key.endswith("spending"))
        cumulative_income += income
        cumulative_spending += spending
        rows.append(
            {
                "day": day,
                **values,
                "products_sold": dict(sold),
                "daily_income": income,
                "daily_spending": spending,
                "daily_net_cashflow": income - spending,
                "cumulative_income": cumulative_income,
                "cumulative_spending": cumulative_spending,
            }
        )
    return rows


def _snapshots(env, player):
    result = []
    for day in range(30):
        index = min((day + 1) * 24, len(env.steps) - 1)
        result.append(_snapshot(env.steps[index], player, day))
    return result


def _player_trace(env, events, player):
    economic = _event_rows(events, player)
    snapshots = _snapshots(env, player)
    for row, snapshot in zip(economic, snapshots):
        row.update(snapshot)
    sales = [
        event
        for event in events
        if event["player"] == player and event["kind"] == "sale"
    ]
    sale_units = Counter(event["item"] for event in sales)
    sale_revenue = Counter()
    sale_step_weight = Counter()
    for event in sales:
        sale_revenue[event["item"]] += event["amount"]
        sale_step_weight[event["item"]] += event["step"]
    timing = {
        product: {
            "units": sale_units[product],
            "revenue": float(sale_revenue[product]),
            "weighted_sale_step": sale_step_weight[product] / sale_units[product],
            "first_sale_step": min(
                event["step"] for event in sales if event["item"] == product
            ),
            "last_sale_step": max(
                event["step"] for event in sales if event["item"] == product
            ),
        }
        for product in sorted(sale_units)
    }
    return {"days": economic, "sale_timing": timing}


def _mean(values):
    return statistics.fmean(values) if values else 0.0


def _aggregate_matches(matches):
    roles = ("baseline", "livestock_proxy")
    daily = []
    for day in range(30):
        row = {"day": day}
        for role in roles:
            role_rows = [match[role]["days"][day] for match in matches]
            keys = [
                "bank",
                "crop_revenue",
                "animal_revenue",
                "fertilizer_revenue",
                "seed_spending",
                "animal_purchase_spending",
                "structure_spending",
                "labor_spending",
                "land_spending",
                "feed_purchase_spending",
                "daily_income",
                "daily_spending",
                "daily_net_cashflow",
                "cumulative_income",
                "cumulative_spending",
                "productive_tiles",
                "liquid_inventory_value",
                "unharvested_inventory_value",
                "total_inventory_value",
                "economic_position",
            ]
            for key in keys:
                row[f"{role}_{key}"] = _mean([value[key] for value in role_rows])
        row["bank_gap_proxy_minus_baseline"] = (
            row["livestock_proxy_bank"] - row["baseline_bank"]
        )
        row["income_gap_proxy_minus_baseline"] = (
            row["livestock_proxy_cumulative_income"]
            - row["baseline_cumulative_income"]
        )
        row["economic_position_gap_proxy_minus_baseline"] = (
            row["livestock_proxy_economic_position"]
            - row["baseline_economic_position"]
        )
        daily.append(row)
    return daily


def _durable_crossover(rows, key):
    for row in rows:
        day = row["day"]
        if row[key] > 0 and all(later[key] > 0 for later in rows[day:]):
            return day
    return None


def _matched_diagnosis(seed_start, seeds):
    baseline_path = ROOT / "agents" / "adaptive_c_phased.py"
    proxy_path = ROOT / "agents" / "proxies" / "livestock_crop.py"
    matches = []
    for seed in range(seed_start, seed_start + seeds):
        for baseline_seat in (0, 1):
            baseline = _load_agent(str(baseline_path))
            proxy = _load_agent(str(proxy_path))
            agents = [proxy, proxy]
            agents[baseline_seat] = baseline
            env, events = _run_traced(agents, seed)
            proxy_seat = 1 - baseline_seat
            matches.append(
                {
                    "seed": seed,
                    "baseline_seat": baseline_seat,
                    "baseline": _player_trace(env, events, baseline_seat),
                    "livestock_proxy": _player_trace(env, events, proxy_seat),
                    "final_advantage_proxy": (
                        float(env.steps[-1][proxy_seat].reward)
                        - float(env.steps[-1][baseline_seat].reward)
                    ),
                }
            )
            print(f"diagnosis seed={seed} baseline_seat={baseline_seat}", flush=True)
    daily = _aggregate_matches(matches)
    final_advantages = [match["final_advantage_proxy"] for match in matches]
    crossover_days = []
    for match in matches:
        rows = []
        for day in range(30):
            proxy = match["livestock_proxy"]["days"][day]
            baseline = match["baseline"]["days"][day]
            rows.append({"day": day, "gap": proxy["bank"] - baseline["bank"]})
        crossover_days.append(_durable_crossover(rows, "gap"))
    return {
        "seeds": list(range(seed_start, seed_start + seeds)),
        "positions": [0, 1],
        "games": len(matches),
        "average_final_advantage_proxy": _mean(final_advantages),
        "min_final_advantage_proxy": min(final_advantages),
        "max_final_advantage_proxy": max(final_advantages),
        "aggregate_durable_bank_crossover_day": _durable_crossover(
            daily, "bank_gap_proxy_minus_baseline"
        ),
        "aggregate_durable_income_crossover_day": _durable_crossover(
            daily, "income_gap_proxy_minus_baseline"
        ),
        "aggregate_durable_economic_position_crossover_day": _durable_crossover(
            daily, "economic_position_gap_proxy_minus_baseline"
        ),
        "per_game_durable_bank_crossover_days": crossover_days,
        "daily": daily,
        "matches": matches,
    }


def _successful_unit_events(replay, player):
    result = []
    for index in range(1, len(replay["steps"])):
        pre = replay["steps"][index - 1][player]["observation"]
        post = replay["steps"][index][player]["observation"]
        action = replay["steps"][index][player].get("action") or {}
        positions = [pre["farms"][player]["farmer"], *pre["farms"][player]["hands"]]
        unit_actions = [action.get("farmer", ["PASS"]), *action.get("hands", [])]
        for unit_index, unit_action in enumerate(unit_actions[: len(positions)]):
            if not isinstance(unit_action, list) or not unit_action:
                continue
            op = unit_action[0]
            x, y = positions[unit_index]
            before = pre["farms"][player]["tiles"][y][x]
            after = post["farms"][player]["tiles"][y][x]
            successful = False
            if op == "BUILD_PASTURE":
                successful = before is None and isinstance(after, dict) and after.get("kind") == "PASTURE"
            elif op == "BUILD_COOP":
                successful = before is None and isinstance(after, dict) and after.get("kind") == "COOP"
            elif op == "PLACE" and len(unit_action) > 1 and unit_action[1] in game.ANIMALS:
                successful = isinstance(after, dict) and after.get("animal") == unit_action[1]
            elif op == "FEED":
                successful = isinstance(before, dict) and before.get("animal") and not before.get("fed_today", False)
            elif op == "CARE":
                successful = isinstance(before, dict) and before.get("animal") and not before.get("cared_today", False)
            elif op == "COLLECT_FERTILIZER":
                successful = isinstance(before, dict) and before.get("fertilizer_available", False)
            elif op == "HARVEST":
                successful = isinstance(before, dict) and before.get("animal") and before.get("yield_units", 0) > 0
            if successful:
                result.append(
                    {
                        "step": index - 1,
                        "day": (index - 1) // 24,
                        "hour": (index - 1) % 24,
                        "unit": unit_index,
                        "op": op,
                        "argument": unit_action[1] if len(unit_action) > 1 else None,
                        "position": [x, y],
                        "animal": before.get("animal") if isinstance(before, dict) else after.get("animal") if isinstance(after, dict) else None,
                        "yield_before": before.get("yield_units", 0) if isinstance(before, dict) else 0,
                    }
                )
    return result


def _replay_agent(actions):
    def agent(obs):
        index = min(int(obs.get("step", 0)) + 1, len(actions) - 1)
        return copy.deepcopy(actions[index])

    return agent


def _hubbahub_analysis():
    replay_path = (
        EXPERIMENTS
        / "kaggle_episodes"
        / "submission_55412009"
        / "replays"
        / "episode-91705498-replay.json"
    )
    replay = json.loads(replay_path.read_text(encoding="utf-8"))
    seed = int(replay["info"]["seed"])
    actions = [
        [state[player].get("action") or {"farmer": ["PASS"], "hands": [], "market": []} for state in replay["steps"]]
        for player in range(2)
    ]
    env, events = _run_traced([_replay_agent(actions[0]), _replay_agent(actions[1])], seed)
    expected = [float(value) for value in replay["rewards"]]
    actual = [float(state.reward) for state in env.steps[-1]]
    if actual != expected:
        raise RuntimeError(f"Hubbahub replay did not reproduce: expected={expected} actual={actual}")
    player = 0
    trace = _player_trace(env, events, player)
    unit_events = _successful_unit_events(replay, player)
    animal_events = [event for event in unit_events if event["animal"] or event["op"] in {"BUILD_PASTURE", "BUILD_COOP", "PLACE"}]
    purchases = [
        event
        for event in events
        if event["player"] == player and event["kind"] in {"animal_spending", "product_spending"}
    ]
    totals = Counter()
    for row in trace["days"]:
        for key in (
            "crop_revenue",
            "animal_revenue",
            "fertilizer_revenue",
            "seed_spending",
            "animal_purchase_spending",
            "labor_spending",
            "land_spending",
            "feed_purchase_spending",
        ):
            totals[key] += row[key]
    animal_direct_net = (
        totals["animal_revenue"]
        + totals["fertilizer_revenue"]
        - totals["animal_purchase_spending"]
        - totals["feed_purchase_spending"]
    )
    return {
        "episode_id": replay["id"],
        "seed": seed,
        "team": replay["info"]["TeamNames"][player],
        "final_money": actual[player],
        "transaction_totals": dict(totals),
        "animal_direct_net_cash": animal_direct_net,
        "animal_direct_share_of_final_money_above_start": animal_direct_net / (actual[player] - 3000),
        "sale_timing": trace["sale_timing"],
        "days": trace["days"],
        "successful_animal_unit_events": animal_events,
        "purchase_events": purchases,
    }


def _write_markdown(path, diagnosis, hubbahub):
    lines = [
        "# Livestock gap diagnosis",
        "",
        "All cash flows below are executed unit transactions recorded from the environment, not submitted-order notionals.",
        "",
        "## Matched local diagnosis",
        "",
        f"- Games: {diagnosis['games']} ({len(diagnosis['seeds'])} seeds, both seats)",
        f"- Mean final proxy advantage: {diagnosis['average_final_advantage_proxy']:+.2f}",
        f"- Durable average bank crossover: day {diagnosis['aggregate_durable_bank_crossover_day']}",
        f"- Durable cumulative-income crossover: day {diagnosis['aggregate_durable_income_crossover_day']}",
        f"- Durable bank-plus-inventory crossover: day {diagnosis['aggregate_durable_economic_position_crossover_day']}",
        "",
        "### Day-by-day economic decomposition",
        "",
        "B = phased baseline; L = livestock proxy. Inventory includes shed, carried, and harvest-ready product valued at the current market price.",
        "",
        "| Day | B bank | L bank | L-B bank | B crop rev | L crop rev | L animal rev | L fert rev | B seed | L seed | L animals | B labor | L labor | L land | L feed | B productive | L productive | B inv value | L inv value | L-B cumulative income |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in diagnosis["daily"]:
        lines.append(
            "| {day} | {baseline_bank:.0f} | {livestock_proxy_bank:.0f} | {bank_gap_proxy_minus_baseline:+.0f} | "
            "{baseline_crop_revenue:.0f} | {livestock_proxy_crop_revenue:.0f} | {livestock_proxy_animal_revenue:.0f} | "
            "{livestock_proxy_fertilizer_revenue:.0f} | {baseline_seed_spending:.0f} | {livestock_proxy_seed_spending:.0f} | "
            "{livestock_proxy_animal_purchase_spending:.0f} | {baseline_labor_spending:.0f} | {livestock_proxy_labor_spending:.0f} | "
            "{livestock_proxy_land_spending:.0f} | {livestock_proxy_feed_purchase_spending:.0f} | "
            "{baseline_productive_tiles:.1f} | {livestock_proxy_productive_tiles:.1f} | "
            "{baseline_total_inventory_value:.0f} | {livestock_proxy_total_inventory_value:.0f} | {income_gap_proxy_minus_baseline:+.0f} |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Hubbahub cow economy",
            "",
            f"- Replay: {hubbahub['episode_id']} (reproduced exactly at {hubbahub['final_money']:.0f} final coins)",
            f"- Direct animal-linked net cash: {hubbahub['animal_direct_net_cash']:+.0f}",
            f"- Direct share of money earned above the 3,000 start: {hubbahub['animal_direct_share_of_final_money_above_start'] * 100:.1f}%",
            "",
            "| Component | Coins |",
            "| --- | ---: |",
        ]
    )
    for key, value in hubbahub["transaction_totals"].items():
        lines.append(f"| {key.replace('_', ' ')} | {value:.0f} |")
    lines.extend(["", "### Successful cow-work events by day", "", "| Day | Build | Place | Feed | Care | Milk harvest | Fertilizer collect |", "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |"])
    counts = defaultdict(Counter)
    for event in hubbahub["successful_animal_unit_events"]:
        counts[event["day"]][event["op"]] += 1
    for day in sorted(counts):
        count = counts[day]
        lines.append(
            f"| {day} | {count['BUILD_PASTURE']} | {count['PLACE']} | {count['FEED']} | {count['CARE']} | {count['HARVEST']} | {count['COLLECT_FERTILIZER']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-start", type=int, default=8000)
    parser.add_argument("--seeds", type=int, default=16)
    parser.add_argument("--stem", default="livestock_gap_diagnosis")
    args = parser.parse_args()
    diagnosis = _matched_diagnosis(args.seed_start, args.seeds)
    hubbahub = _hubbahub_analysis()
    result = {
        "schema_version": 1,
        "diagnosis": diagnosis,
        "hubbahub": hubbahub,
    }
    json_path = EXPERIMENTS / f"{args.stem}.json"
    md_path = EXPERIMENTS / f"{args.stem}.md"
    json_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    _write_markdown(md_path, diagnosis, hubbahub)
    print(f"Saved {json_path}")
    print(f"Saved {md_path}")


if __name__ == "__main__":
    main()
