"""Build exact economic timelines for selected public Kaggriculture replays."""

import argparse
import json
import statistics
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path

from kaggle_environments.envs.kaggriculture import kaggriculture as game


ROOT = Path(__file__).resolve().parent
DEFAULT_CORPUS = ROOT / "experiments" / "top_player_replays"
DEFAULT_OUTPUT = ROOT / "experiments" / "top_player_replay_analysis.json"
DEFAULT_TIMELINES = ROOT / "experiments" / "top_player_replay_timelines.md"
PREMIUM_PRODUCTS = {"MELON", "STRAWBERRY", "MILK", "WOOL"}


def _plain_counter(values):
    return {key: values[key] for key in sorted(values) if values[key]}


def _farm_snapshot(farm):
    crops = Counter()
    animals = Counter()
    structures = Counter()
    productive = 0
    for row in farm["tiles"]:
        for tile in row:
            if not isinstance(tile, dict):
                continue
            if tile.get("kind") == "PLANT":
                crops[tile["crop"]] += 1
                productive += 1
            elif tile.get("kind") in {"COOP", "PASTURE"}:
                structures[tile["kind"]] += 1
                if tile.get("animal"):
                    animals[tile["animal"]] += 1
                    productive += 1
    return {
        "crops": _plain_counter(crops),
        "animals": _plain_counter(animals),
        "structures": _plain_counter(structures),
        "productive_tiles": productive,
        "quadrants": len(farm.get("unlocked_quadrants", [])),
        "unlocked_quadrants": list(farm.get("unlocked_quadrants", [])),
        "hands": len(farm.get("hands", [])),
    }


def _new_ledger():
    return {
        "sale_quantity": Counter(),
        "sale_revenue": Counter(),
        "sale_prices": defaultdict(list),
        "seed_quantity": Counter(),
        "seed_spend": Counter(),
        "product_quantity": Counter(),
        "product_spend": Counter(),
        "animal_quantity": Counter(),
        "animal_spend": Counter(),
        "land_spend": 0,
        "land_count": 0,
        "labor_spend": 0,
        "hire_count": 0,
        "harvest_quantity": Counter(),
        "plant_quantity": Counter(),
        "structures_built": Counter(),
        "animals_placed": Counter(),
        "feed_actions": 0,
        "care_actions": 0,
        "fertilizer_collected": 0,
    }


def _apply_field_actions(farms, privates, actions, day, turns_per_day, shed_capacity):
    """Apply public unit actions and record only effects visible in replay state."""
    ledgers = [_new_ledger() for _ in farms]
    board_size = len(farms[0]["tiles"])
    for player, action in enumerate(actions):
        action = action if isinstance(action, dict) else {}
        farmer_action = action.get("farmer", ["PASS"])
        hand_actions = action.get("hands", [])
        hand_actions = hand_actions if isinstance(hand_actions, list) else []
        unit_count = 1 + len(farms[player].get("hands", []))
        unit_actions = [farmer_action, *hand_actions]
        unit_actions.extend([["PASS"]] * max(0, unit_count - len(unit_actions)))
        unit_actions = unit_actions[:unit_count]
        plant_demand = Counter(
            unit_action[1]
            for unit_action in unit_actions
            if isinstance(unit_action, list)
            and len(unit_action) >= 2
            and unit_action[0] == "PLANT"
        )
        blocked = {
            crop
            for crop, count in plant_demand.items()
            if count > privates[player].get("seeds", {}).get(crop, 0)
        }
        for unit_index, original in enumerate(unit_actions):
            unit_action = original
            if (
                isinstance(original, list)
                and len(original) >= 2
                and original[0] == "PLANT"
                and original[1] in blocked
            ):
                unit_action = ["PASS"]
            inventory = privates[player]["inventories"][unit_index]
            before_inventory = dict(inventory)
            farm = farms[player]
            position = farm["farmer"] if unit_index == 0 else farm["hands"][unit_index - 1]
            x, y = position
            before_tile = deepcopy(farm["tiles"][y][x])
            game._apply_unit_action(
                farm,
                privates[player],
                unit_index,
                unit_action,
                board_size,
                day,
                turns_per_day,
                shed_capacity,
            )
            after_tile = farm["tiles"][y][x]
            after_inventory = privates[player]["inventories"][unit_index]
            op = unit_action[0] if isinstance(unit_action, list) and unit_action else "PASS"
            if op == "HARVEST":
                for item in set(before_inventory) | set(after_inventory):
                    gained = after_inventory.get(item, 0) - before_inventory.get(item, 0)
                    if gained > 0:
                        ledgers[player]["harvest_quantity"][item] += gained
            elif op == "PLANT" and before_tile is None and isinstance(after_tile, dict):
                if after_tile.get("kind") == "PLANT":
                    ledgers[player]["plant_quantity"][after_tile["crop"]] += 1
            elif op in {"BUILD_COOP", "BUILD_PASTURE"}:
                kind = "COOP" if op == "BUILD_COOP" else "PASTURE"
                if before_tile is None and isinstance(after_tile, dict) and after_tile.get("kind") == kind:
                    ledgers[player]["structures_built"][kind] += 1
            elif op == "PLACE" and isinstance(after_tile, dict) and after_tile.get("animal"):
                previous_animal = before_tile.get("animal") if isinstance(before_tile, dict) else None
                if after_tile["animal"] != previous_animal:
                    ledgers[player]["animals_placed"][after_tile["animal"]] += 1
            elif op == "FEED" and isinstance(after_tile, dict):
                if after_tile.get("fed_today") and not (
                    isinstance(before_tile, dict) and before_tile.get("fed_today")
                ):
                    ledgers[player]["feed_actions"] += 1
            elif op == "CARE" and isinstance(after_tile, dict):
                if after_tile.get("cared_today") and not (
                    isinstance(before_tile, dict) and before_tile.get("cared_today")
                ):
                    ledgers[player]["care_actions"] += 1
            elif op == "COLLECT_FERTILIZER":
                gained = after_inventory.get("FERTILIZER", 0) - before_inventory.get("FERTILIZER", 0)
                ledgers[player]["fertilizer_collected"] += max(0, gained)
    return ledgers


def _process_market(farms, privates, market, actions, configuration, ledgers):
    max_orders = int(configuration.get("maxMarketOrdersPerTurn", 10))
    hire_mult = int(configuration.get("farmHandCostMult", 1))
    shed_capacity = int(configuration.get("shedCapacity", 100))
    board_size = int(configuration.get("boardSize", 10))
    queues = []
    for action in actions:
        orders = action.get("market", []) if isinstance(action, dict) else []
        queues.append(list(orders)[:max_orders] if isinstance(orders, list) else [])

    for order_index in range(max((len(queue) for queue in queues), default=0)):
        order_states = []
        for queue in queues:
            order_states.append(
                game._parse_order(queue[order_index]) if order_index < len(queue) else None
            )
        for player, order in enumerate(order_states):
            if order is None:
                continue
            before_money = farms[player]["money"]
            if order["type"] == "HIRE":
                game._do_hire(farms[player], privates[player], board_size, hire_mult)
                cost = before_money - farms[player]["money"]
                if cost > 0:
                    ledgers[player]["labor_spend"] += cost
                    ledgers[player]["hire_count"] += 1
                order_states[player] = None
            elif order["type"] == "BUY_LAND":
                game._do_buy_land(farms[player], board_size)
                cost = before_money - farms[player]["money"]
                if cost > 0:
                    ledgers[player]["land_spend"] += cost
                    ledgers[player]["land_count"] += 1
                order_states[player] = None

        while True:
            quoted = [None] * len(farms)
            for player, order in enumerate(order_states):
                if order is None or order.get("remaining", 0) <= 0:
                    continue
                op, item = order["type"], order["item"]
                if op == "SELL" and item in game.PRODUCTS:
                    price = game.market_price(item, market["inventory"][item], market.get("params"))
                elif op == "BUY_PRODUCT" and item in {"WHEAT", "FERTILIZER"}:
                    price = game.market_price(item, market["inventory"][item] - 1, market.get("params"))
                elif op == "BUY_SEED" and item in game.CROPS:
                    price = game.CROPS[item]["seed"]
                elif op == "BUY_ANIMAL" and item in game.ANIMALS:
                    price = game.ANIMALS[item]["cost"]
                else:
                    order_states[player] = None
                    continue
                quoted[player] = (op, item, price, order)
            if all(quote is None for quote in quoted):
                break
            committed = False
            for player, quote in enumerate(quoted):
                if quote is None:
                    continue
                op, item, price, order = quote
                if game._commit_unit(
                    op,
                    item,
                    price,
                    farms[player],
                    privates[player],
                    market,
                    shed_capacity,
                ):
                    order["remaining"] -= 1
                    committed = True
                    ledger = ledgers[player]
                    if op == "SELL":
                        ledger["sale_quantity"][item] += 1
                        ledger["sale_revenue"][item] += price
                        ledger["sale_prices"][item].append(price)
                    elif op == "BUY_SEED":
                        ledger["seed_quantity"][item] += 1
                        ledger["seed_spend"][item] += price
                    elif op == "BUY_PRODUCT":
                        ledger["product_quantity"][item] += 1
                        ledger["product_spend"][item] += price
                    elif op == "BUY_ANIMAL":
                        ledger["animal_quantity"][item] += 1
                        ledger["animal_spend"][item] += price
                else:
                    order_states[player] = None
            if not committed:
                break
        game._refresh_prices(market)


def _transition_ledger(previous_states, current_states, configuration):
    previous_obs = previous_states[0]["observation"]
    actions = [state.get("action") or {} for state in current_states]
    farms = deepcopy(previous_obs["farms"])
    privates = [deepcopy(state["observation"]["private"]) for state in previous_states]
    market = deepcopy(previous_obs["market"])
    day = int(previous_obs.get("day", previous_obs.get("step", 0) // 24))
    turns_per_day = int(configuration.get("turnsPerDay", 24))
    shed_capacity = int(configuration.get("shedCapacity", 100))
    ledgers = _apply_field_actions(
        farms, privates, actions, day, turns_per_day, shed_capacity
    )
    _process_market(farms, privates, market, actions, configuration, ledgers)
    mismatches = []
    next_farms = current_states[0]["observation"]["farms"]
    for player, farm in enumerate(farms):
        observed = float(next_farms[player]["money"])
        predicted = float(farm["money"])
        if abs(observed - predicted) > 1e-9:
            mismatches.append({"player": player, "predicted": predicted, "observed": observed})
    return ledgers, mismatches


def _new_daily(day):
    return {
        "day": day,
        "bank_start": None,
        "bank_end": None,
        "max_hands": 0,
        "farm": {},
        "seed_purchases": Counter(),
        "seed_spending": Counter(),
        "feed_purchases": Counter(),
        "feed_spending": Counter(),
        "animal_purchases": Counter(),
        "animal_spending": Counter(),
        "land_purchases": 0,
        "land_spending": 0,
        "hires": 0,
        "labor_spending": 0,
        "harvests": Counter(),
        "plantings": Counter(),
        "structures_built": Counter(),
        "animals_placed": Counter(),
        "feed_actions": 0,
        "care_actions": 0,
        "fertilizer_collected": 0,
        "sales": Counter(),
        "sale_revenue": Counter(),
        "sale_events": [],
    }


def _add_ledger(daily, ledger, day, hour):
    daily["seed_purchases"].update(ledger["seed_quantity"])
    daily["seed_spending"].update(ledger["seed_spend"])
    daily["feed_purchases"].update(ledger["product_quantity"])
    daily["feed_spending"].update(ledger["product_spend"])
    daily["animal_purchases"].update(ledger["animal_quantity"])
    daily["animal_spending"].update(ledger["animal_spend"])
    daily["land_purchases"] += ledger["land_count"]
    daily["land_spending"] += ledger["land_spend"]
    daily["hires"] += ledger["hire_count"]
    daily["labor_spending"] += ledger["labor_spend"]
    daily["harvests"].update(ledger["harvest_quantity"])
    daily["plantings"].update(ledger["plant_quantity"])
    daily["structures_built"].update(ledger["structures_built"])
    daily["animals_placed"].update(ledger["animals_placed"])
    daily["feed_actions"] += ledger["feed_actions"]
    daily["care_actions"] += ledger["care_actions"]
    daily["fertilizer_collected"] += ledger["fertilizer_collected"]
    daily["sales"].update(ledger["sale_quantity"])
    daily["sale_revenue"].update(ledger["sale_revenue"])
    for product, quantity in ledger["sale_quantity"].items():
        prices = ledger["sale_prices"][product]
        daily["sale_events"].append({
            "day": day,
            "hour": hour,
            "product": product,
            "quantity": quantity,
            "revenue": ledger["sale_revenue"][product],
            "average_price": statistics.fmean(prices),
            "min_price": min(prices),
            "max_price": max(prices),
        })


def _serialize_daily(daily):
    output = dict(daily)
    for key in (
        "seed_purchases", "seed_spending", "feed_purchases", "feed_spending",
        "animal_purchases", "animal_spending", "harvests", "plantings",
        "structures_built", "animals_placed", "sales", "sale_revenue",
    ):
        output[key] = _plain_counter(output[key])
    output["total_sale_revenue"] = sum(output["sale_revenue"].values())
    output["total_capital_spending"] = (
        sum(output["seed_spending"].values())
        + sum(output["feed_spending"].values())
        + sum(output["animal_spending"].values())
        + output["land_spending"]
        + output["labor_spending"]
    )
    return output


def _phase_segments(timeline):
    labels = []
    for row in timeline:
        crops = row["farm"].get("crops", {})
        if not crops:
            label = "NONE"
        else:
            maximum = max(crops.values())
            label = "+".join(sorted(crop for crop, count in crops.items() if count == maximum))
        labels.append((row["day"], label))
    segments = []
    for day, label in labels:
        if not segments or segments[-1]["dominant_crop"] != label:
            segments.append({"start_day": day, "end_day": day, "dominant_crop": label})
        else:
            segments[-1]["end_day"] = day
    return segments


def _weighted_day(timeline, field, product):
    total = sum(row[field].get(product, 0) for row in timeline)
    if not total:
        return None
    return sum(row["day"] * row[field].get(product, 0) for row in timeline) / total


def _appearance_summary(episode_id, player, team_names, timeline, final_money):
    opponent = team_names[1 - player]
    other_money = final_money[1 - player]
    sale_quantity = Counter()
    sale_revenue = Counter()
    harvest_quantity = Counter()
    seed_quantity = Counter()
    seed_spending = Counter()
    feed_quantity = Counter()
    feed_spending = Counter()
    animal_quantity = Counter()
    animal_spending = Counter()
    sale_events = []
    investment_events = []
    for row in timeline:
        sale_quantity.update(row["sales"])
        sale_revenue.update(row["sale_revenue"])
        harvest_quantity.update(row["harvests"])
        seed_quantity.update(row["seed_purchases"])
        seed_spending.update(row["seed_spending"])
        feed_quantity.update(row["feed_purchases"])
        feed_spending.update(row["feed_spending"])
        animal_quantity.update(row["animal_purchases"])
        animal_spending.update(row["animal_spending"])
        sale_events.extend(row["sale_events"])
        investment_cost = row["land_spending"] + sum(row["animal_spending"].values())
        if investment_cost:
            recent = timeline[max(0, row["day"] - 2): row["day"] + 1]
            recent_revenue = Counter()
            for recent_row in recent:
                recent_revenue.update(recent_row["sale_revenue"])
            investment_events.append({
                "day": row["day"],
                "land_spending": row["land_spending"],
                "animal_spending": row["animal_spending"],
                "total_investment": investment_cost,
                "bank_start": row["bank_start"],
                "same_day_sale_revenue": row["total_sale_revenue"],
                "previous_two_days_plus_same_day_revenue": sum(recent_revenue.values()),
                "recent_revenue_by_product": _plain_counter(recent_revenue),
            })
    land_days = [row["day"] for row in timeline for _ in range(row["land_purchases"])]
    peak_animals = Counter()
    peak_crops = Counter()
    for row in timeline:
        for animal, count in row["farm"].get("animals", {}).items():
            peak_animals[animal] = max(peak_animals[animal], count)
        for crop, count in row["farm"].get("crops", {}).items():
            peak_crops[crop] = max(peak_crops[crop], count)
    animal_purchase_events = [
        {"day": row["day"], "animals": row["animal_purchases"], "spending": row["animal_spending"]}
        for row in timeline if row["animal_purchases"]
    ]
    structure_events = [
        {"day": row["day"], "structures": row["structures_built"]}
        for row in timeline if row["structures_built"]
    ]
    premium_holding = {}
    for product in sorted(PREMIUM_PRODUCTS):
        harvest_day = _weighted_day(timeline, "harvests", product)
        sale_day = _weighted_day(timeline, "sales", product)
        premium_holding[product] = {
            "weighted_harvest_day": harvest_day,
            "weighted_sale_day": sale_day,
            "weighted_lag_days": (
                sale_day - harvest_day if sale_day is not None and harvest_day is not None else None
            ),
        }
    return {
        "episode_id": episode_id,
        "player_index": player,
        "opponent": opponent,
        "result": "win" if final_money[player] > other_money else "loss" if final_money[player] < other_money else "tie",
        "final_money": final_money[player],
        "opponent_money": other_money,
        "land_purchase_days": land_days,
        "final_quadrants": timeline[-1]["farm"]["quadrants"],
        "max_quadrants": max(row["farm"]["quadrants"] for row in timeline),
        "max_hands": max(row["max_hands"] for row in timeline),
        "total_hires": sum(row["hires"] for row in timeline),
        "peak_animals": _plain_counter(peak_animals),
        "animal_purchase_events": animal_purchase_events,
        "structure_events": structure_events,
        "peak_crops": _plain_counter(peak_crops),
        "crop_phases": _phase_segments(timeline),
        "max_productive_tiles": max(row["farm"]["productive_tiles"] for row in timeline),
        "seed_purchases": _plain_counter(seed_quantity),
        "seed_spending": _plain_counter(seed_spending),
        "feed_purchases": _plain_counter(feed_quantity),
        "feed_spending": _plain_counter(feed_spending),
        "animal_purchases": _plain_counter(animal_quantity),
        "animal_spending": _plain_counter(animal_spending),
        "harvest_quantities": _plain_counter(harvest_quantity),
        "sale_quantities": _plain_counter(sale_quantity),
        "sale_revenue": _plain_counter(sale_revenue),
        "total_sale_revenue": sum(sale_revenue.values()),
        "milk_revenue": sale_revenue["MILK"],
        "egg_revenue": sale_revenue["EGG"],
        "wool_revenue": sale_revenue["WOOL"],
        "fertilizer_revenue": sale_revenue["FERTILIZER"],
        "sale_events": sorted(sale_events, key=lambda event: (event["day"], event["hour"])),
        "major_sales": sorted(sale_events, key=lambda event: event["revenue"], reverse=True)[:12],
        "premium_holding": premium_holding,
        "investment_events": investment_events,
        "timeline": timeline,
    }


def _median(values):
    return statistics.median(values) if values else None


def _range(values):
    return [min(values), max(values)] if values else None


def _aggregate_player(metadata, appearances):
    land_by_number = defaultdict(list)
    cow_first_days = []
    cow_peaks = []
    for appearance in appearances:
        for index, day in enumerate(appearance["land_purchase_days"], 1):
            land_by_number[index].append(day)
        cow_peaks.append(appearance["peak_animals"].get("COW", 0))
        cow_events = [
            event["day"] for event in appearance["animal_purchase_events"]
            if event["animals"].get("COW", 0)
        ]
        if cow_events:
            cow_first_days.append(min(cow_events))
    final_money = [appearance["final_money"] for appearance in appearances]
    max_hands = [appearance["max_hands"] for appearance in appearances]
    final_quadrants = [appearance["final_quadrants"] for appearance in appearances]
    productive = [appearance["max_productive_tiles"] for appearance in appearances]
    return {
        **metadata,
        "episodes_analyzed": len(appearances),
        "episode_ids": [appearance["episode_id"] for appearance in appearances],
        "wins": sum(appearance["result"] == "win" for appearance in appearances),
        "losses": sum(appearance["result"] == "loss" for appearance in appearances),
        "average_final_money": statistics.fmean(final_money),
        "final_money_range": _range(final_money),
        "final_quadrant_distribution": dict(sorted(Counter(final_quadrants).items())),
        "land_purchase_timing": {
            str(index): {"median": _median(days), "range": _range(days), "observations": days}
            for index, days in sorted(land_by_number.items())
        },
        "cow_peak_median": _median(cow_peaks),
        "cow_peak_range": _range(cow_peaks),
        "first_cow_purchase_day_median": _median(cow_first_days),
        "first_cow_purchase_day_range": _range(cow_first_days),
        "max_hands_median": _median(max_hands),
        "max_hands_range": _range(max_hands),
        "max_productive_tiles_median": _median(productive),
        "max_productive_tiles_range": _range(productive),
        "appearances": appearances,
    }


def analyze(corpus, output, timeline_report):
    manifest = json.loads((corpus / "manifest.json").read_text())
    selected = {player["team_name"]: player for player in manifest["players"]}
    appearances_by_team = defaultdict(list)
    replay_records = []
    total_mismatches = []
    replay_paths = sorted((corpus / "replays").glob("episode-*-replay.json"))
    expected_ids = set(manifest["unique_episode_ids"])
    observed_ids = set()
    for path in replay_paths:
        replay = json.loads(path.read_text())
        episode_id = int(replay["info"]["EpisodeId"])
        observed_ids.add(episode_id)
        steps = replay["steps"]
        team_names = list(replay["info"]["TeamNames"])
        player_count = len(team_names)
        configuration = dict(replay.get("configuration", {}))
        daily = [[_new_daily(day) for day in range(30)] for _ in range(player_count)]
        for state_index, states in enumerate(steps):
            obs = states[0]["observation"]
            day = min(29, int(obs.get("day", obs.get("step", state_index) // 24)))
            for player in range(player_count):
                farm = obs["farms"][player]
                row = daily[player][day]
                money = float(farm["money"])
                if row["bank_start"] is None:
                    row["bank_start"] = money
                row["bank_end"] = money
                row["max_hands"] = max(row["max_hands"], len(farm.get("hands", [])))
                row["farm"] = _farm_snapshot(farm)
        mismatch_count = 0
        for index in range(1, len(steps)):
            previous_obs = steps[index - 1][0]["observation"]
            day = min(29, int(previous_obs.get("day", (index - 1) // 24)))
            hour = int(previous_obs.get("hour", (index - 1) % 24))
            ledgers, mismatches = _transition_ledger(steps[index - 1], steps[index], configuration)
            mismatch_count += len(mismatches)
            for mismatch in mismatches:
                total_mismatches.append({"episode_id": episode_id, "step": index, **mismatch})
            for player, ledger in enumerate(ledgers):
                _add_ledger(daily[player][day], ledger, day, hour)
        final_money = [float(state["reward"]) for state in steps[-1]]
        replay_records.append({
            "episode_id": episode_id,
            "team_names": team_names,
            "seed": replay["info"].get("seed"),
            "final_money": final_money,
            "financial_reconstruction_mismatches": mismatch_count,
        })
        for player, team_name in enumerate(team_names):
            if team_name not in selected:
                continue
            timeline = [_serialize_daily(row) for row in daily[player]]
            appearances_by_team[team_name].append(
                _appearance_summary(episode_id, player, team_names, timeline, final_money)
            )
    if observed_ids != expected_ids:
        missing = sorted(expected_ids - observed_ids)
        extra = sorted(observed_ids - expected_ids)
        raise RuntimeError(f"corpus mismatch: missing={missing}, extra={extra}")
    players = []
    for metadata in manifest["players"]:
        appearances = sorted(
            appearances_by_team[metadata["team_name"]], key=lambda row: row["episode_id"]
        )
        if len(appearances) < 4:
            raise RuntimeError(
                f"expected at least four appearances for {metadata['team_name']}, "
                f"got {len(appearances)}"
            )
        players.append(_aggregate_player(metadata, appearances))
    analysis = {
        "schema_version": 1,
        "corpus_manifest": str((corpus / "manifest.json").relative_to(ROOT)),
        "unique_replays": len(replay_records),
        "selected_players": len(players),
        "selected_player_appearances": sum(len(player["appearances"]) for player in players),
        "financial_reconstruction_mismatches": total_mismatches,
        "replays": sorted(replay_records, key=lambda row: row["episode_id"]),
        "players": players,
    }
    output.write_text(json.dumps(analysis, indent=2) + "\n")
    timeline_report.write_text(_timeline_markdown(analysis))
    print(
        f"Analyzed {analysis['unique_replays']} replays, "
        f"{analysis['selected_player_appearances']} selected-player appearances; "
        f"money reconstruction mismatches={len(total_mismatches)}"
    )
    print(f"Saved {output}")
    print(f"Saved {timeline_report}")
    return analysis


def _timeline_markdown(analysis):
    lines = [
        "# Top-player replay timelines",
        "",
        "This is the analyzer-generated factual companion to the curated meta review.",
        "Sale revenue is reconstructed unit-by-unit with the environment's price function",
        "and validated against every observed bank transition.",
        "",
    ]
    for player in analysis["players"]:
        lines.extend([
            f"## {player['team_name']} — rating {player['leaderboard_score']}",
            "",
            "| Episode | Opponent | Result | Money | Land days | Peak animals | Max hands | Max productive |",
            "| ---: | --- | --- | ---: | --- | --- | ---: | ---: |",
        ])
        for appearance in player["appearances"]:
            lines.append(
                f"| {appearance['episode_id']} | {appearance['opponent']} | {appearance['result']} | "
                f"{appearance['final_money']:.0f} | {appearance['land_purchase_days'] or 'none'} | "
                f"{appearance['peak_animals'] or 'none'} | {appearance['max_hands']} | "
                f"{appearance['max_productive_tiles']} |"
            )
        lines.extend(["", "### Daily timelines", ""])
        for appearance in player["appearances"]:
            lines.extend([
                f"#### Episode {appearance['episode_id']} vs {appearance['opponent']}",
                "",
                "| Day | Bank | Q | Hands | Crops | Animals | Plants | Harvests | Sales/revenue | Capital spend |",
                "| ---: | ---: | ---: | ---: | --- | --- | --- | --- | --- | ---: |",
            ])
            for row in appearance["timeline"]:
                sales = ", ".join(
                    f"{item} {quantity}/${row['sale_revenue'].get(item, 0)}"
                    for item, quantity in row["sales"].items()
                ) or "-"
                lines.append(
                    f"| {row['day']} | {row['bank_end']:.0f} | {row['farm']['quadrants']} | "
                    f"{row['max_hands']} | {row['farm'].get('crops', {}) or '-'} | "
                    f"{row['farm'].get('animals', {}) or '-'} | {row['plantings'] or '-'} | "
                    f"{row['harvests'] or '-'} | {sales} | {row['total_capital_spending']:.0f} |"
                )
            lines.append("")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--timeline-report", type=Path, default=DEFAULT_TIMELINES)
    args = parser.parse_args()
    analyze(args.corpus.resolve(), args.output.resolve(), args.timeline_report.resolve())


if __name__ == "__main__":
    main()
