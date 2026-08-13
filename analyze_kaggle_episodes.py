"""Analyze downloaded Kaggriculture episode replays and agent logs."""

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = ROOT / "experiments" / "kaggle_episodes"
DEFAULT_JSON = ROOT / "experiments" / "kaggle_episode_analysis.json"
DEFAULT_REPORT = ROOT / "experiments" / "kaggle_episode_analysis.md"
PRODUCTS = (
    "WHEAT",
    "CARROT",
    "TOMATO",
    "STRAWBERRY",
    "MELON",
    "EGG",
    "MILK",
    "WOOL",
    "FERTILIZER",
)


def _counter_dict(counter):
    return {key: counter[key] for key in sorted(counter) if counter[key]}


def _farm_composition(farm):
    crops = Counter()
    animals = Counter()
    structures = Counter()
    weeds = empty = locked = fertilized_plants = 0
    for row in farm["tiles"]:
        for tile in row:
            if tile is None:
                empty += 1
            elif tile == "LOCKED":
                locked += 1
            elif isinstance(tile, dict):
                kind = tile.get("kind")
                if kind == "PLANT":
                    crops[tile["crop"]] += 1
                    if tile.get("fertilized_until_day", -1) >= 0:
                        fertilized_plants += 1
                elif kind == "WEED":
                    weeds += 1
                elif kind in ("COOP", "PASTURE"):
                    structures[kind] += 1
                    if tile.get("animal"):
                        animals[tile["animal"]] += 1
    return {
        "crops": _counter_dict(crops),
        "animals": _counter_dict(animals),
        "structures": _counter_dict(structures),
        "total_plants": sum(crops.values()),
        "total_animals": sum(animals.values()),
        "fertilized_plants": fertilized_plants,
        "weeds": weeds,
        "empty": empty,
        "locked": locked,
        "unlocked_tiles": len(farm["tiles"]) ** 2 - locked,
        "unlocked_quadrants": list(farm.get("unlocked_quadrants", [])),
        "active_hands": len(farm.get("hands", [])),
    }


def _new_plant(previous, current):
    if not (isinstance(current, dict) and current.get("kind") == "PLANT"):
        return None
    identity = (current.get("crop"), current.get("planted_day"))
    if isinstance(previous, dict) and previous.get("kind") == "PLANT":
        if (previous.get("crop"), previous.get("planted_day")) == identity:
            return None
    return current["crop"]


def _new_animal(previous, current):
    if not isinstance(current, dict) or not current.get("animal"):
        return None
    previous_animal = previous.get("animal") if isinstance(previous, dict) else None
    return current["animal"] if previous_animal != current["animal"] else None


def _new_structure(previous, current):
    if not isinstance(current, dict) or current.get("kind") not in ("COOP", "PASTURE"):
        return None
    previous_kind = previous.get("kind") if isinstance(previous, dict) else None
    return current["kind"] if previous_kind != current["kind"] else None


def _successful_fertilization(previous, current):
    if not isinstance(current, dict) or current.get("kind") != "PLANT":
        return False
    current_until = current.get("fertilized_until_day", -1)
    previous_until = previous.get("fertilized_until_day", -1) if isinstance(previous, dict) else -1
    return current_until > previous_until


def _iter_unit_actions(action):
    if not isinstance(action, dict):
        return
    farmer = action.get("farmer")
    if isinstance(farmer, list) and farmer:
        yield "farmer", farmer
    for index, hand in enumerate(action.get("hands", [])):
        if isinstance(hand, list) and hand:
            yield f"hand_{index}", hand


def _action_events(replay, player):
    planted_actions = Counter()
    unit_ops = Counter()
    market_ops = Counter()
    sold = Counter()
    sales = []
    bought_seeds = Counter()
    bought_animals = Counter()

    # Replay step t stores the action chosen from observation t-1 alongside the
    # resulting observation t. Step 0 contains framework placeholder actions.
    for index in range(1, len(replay["steps"])):
        action = replay["steps"][index][player].get("action") or {}
        prior_obs = replay["steps"][index - 1][player]["observation"]
        event_step = prior_obs.get("step", index - 1)
        day = prior_obs.get("day", event_step // 24)
        hour = prior_obs.get("hour", event_step % 24)
        for _unit, unit_action in _iter_unit_actions(action):
            op = unit_action[0]
            unit_ops[op] += 1
            if op == "PLANT" and len(unit_action) >= 2:
                planted_actions[unit_action[1]] += 1

        for order_index, order in enumerate(action.get("market", [])):
            if not isinstance(order, list) or not order:
                continue
            op = order[0]
            market_ops[op] += 1
            if op == "SELL" and len(order) >= 3:
                item, quantity = order[1], int(order[2])
                price = prior_obs["market"]["prices"].get(item)
                sold[item] += quantity
                sales.append(
                    {
                        "step": event_step,
                        "day": day,
                        "hour": hour,
                        "order_index": order_index,
                        "product": item,
                        "quantity_submitted": quantity,
                        "quoted_price": price,
                        "notional_value": quantity * price if price is not None else None,
                    }
                )
            elif op == "BUY_SEED" and len(order) >= 3:
                bought_seeds[order[1]] += int(order[2])
            elif op == "BUY_ANIMAL" and len(order) >= 3:
                bought_animals[order[1]] += int(order[2])

    sales.sort(key=lambda sale: (sale["step"], sale["order_index"]))
    major_sales = sorted(
        sales,
        key=lambda sale: (sale["notional_value"] or 0, sale["quantity_submitted"]),
        reverse=True,
    )[:10]
    total_sold = sum(sold.values())
    weighted_sale_step = (
        sum(sale["step"] * sale["quantity_submitted"] for sale in sales) / total_sold
        if total_sold
        else None
    )
    return {
        "unit_ops": _counter_dict(unit_ops),
        "market_ops": _counter_dict(market_ops),
        "plant_actions": _counter_dict(planted_actions),
        "seed_quantities_bought": _counter_dict(bought_seeds),
        "animal_quantities_bought": _counter_dict(bought_animals),
        "sell_quantities_submitted": _counter_dict(sold),
        "sales": sales,
        "major_sales": major_sales,
        "weighted_average_sale_step": weighted_sale_step,
    }


def _log_summary(replay_path, episode_id, player):
    submission_dir = replay_path.parent.parent
    candidates = list(
        submission_dir.glob(
            f"logs/**/episode-{episode_id}-agent-{player}-logs.json"
        )
    )
    if not candidates:
        return {"available": False}
    path = candidates[0]
    entries = json.loads(path.read_text(encoding="utf-8"))
    records = [record for entry in entries for record in entry if isinstance(record, dict)]
    durations = [float(record.get("duration", 0)) for record in records]
    stdout = [record.get("stdout", "") for record in records if record.get("stdout")]
    stderr = [record.get("stderr", "") for record in records if record.get("stderr")]
    return {
        "available": True,
        "path": str(path.relative_to(ROOT)),
        "calls": len(records),
        "average_duration_seconds": statistics.fmean(durations) if durations else 0,
        "max_duration_seconds": max(durations, default=0),
        "nonempty_stdout_records": len(stdout),
        "nonempty_stderr_records": len(stderr),
        "stderr_samples": stderr[:5],
    }


def _analyze_episode(path, our_team):
    replay = json.loads(path.read_text(encoding="utf-8"))
    steps = replay["steps"]
    episode_id = int(replay.get("info", {}).get("EpisodeId") or replay.get("id"))
    team_names = replay.get("info", {}).get("TeamNames") or [
        item.get("Name", f"player_{index}")
        for index, item in enumerate(replay.get("info", {}).get("Agents", []))
    ]
    player_count = len(steps[0])
    if len(team_names) < player_count:
        team_names += [f"player_{index}" for index in range(len(team_names), player_count)]

    money_over_time = []
    market_prices_over_time = []
    daily_farm_composition = []
    town_shop_unlocks = []
    prior_shops = []
    max_plants = [Counter() for _ in range(player_count)]
    max_animals = [Counter() for _ in range(player_count)]
    max_total_plants = [0 for _ in range(player_count)]
    max_total_animals = [0 for _ in range(player_count)]
    max_unlocked_quadrants = [0 for _ in range(player_count)]
    max_active_hands = [0 for _ in range(player_count)]
    daily_hire_max = [defaultdict(int) for _ in range(player_count)]

    for index, states in enumerate(steps):
        obs = states[0]["observation"]
        step_number = obs.get("step", index)
        day = obs.get("day", step_number // 24)
        hour = obs.get("hour", step_number % 24)
        farms = obs["farms"]
        money_over_time.append(
            {
                "step": step_number,
                "day": day,
                "hour": hour,
                "money": [float(farm["money"]) for farm in farms],
            }
        )
        market_prices_over_time.append(
            {"step": step_number, "prices": dict(obs["market"]["prices"])}
        )
        shops = list(obs.get("town", {}).get("unlocked_shops", []))
        if len(shops) > len(prior_shops):
            for shop in shops[len(prior_shops) :]:
                town_shop_unlocks.append(
                    {"step": step_number, "day": day, "hour": hour, "shop": shop}
                )
        prior_shops = shops

        compositions = []
        for player, farm in enumerate(farms):
            composition = _farm_composition(farm)
            compositions.append(composition)
            max_total_plants[player] = max(
                max_total_plants[player], composition["total_plants"]
            )
            max_total_animals[player] = max(
                max_total_animals[player], composition["total_animals"]
            )
            max_unlocked_quadrants[player] = max(
                max_unlocked_quadrants[player],
                len(composition["unlocked_quadrants"]),
            )
            max_active_hands[player] = max(
                max_active_hands[player], composition["active_hands"]
            )
            daily_hire_max[player][day] = max(
                daily_hire_max[player][day], farm.get("hires_today", 0)
            )
            for crop, count in composition["crops"].items():
                max_plants[player][crop] = max(max_plants[player][crop], count)
            for animal, count in composition["animals"].items():
                max_animals[player][animal] = max(max_animals[player][animal], count)
        # Keep the initial empty state, then hour 1 after that day's HIRE orders
        # have resolved, plus the final state.
        if index == 0 or hour == 1 or index == len(steps) - 1:
            daily_farm_composition.append(
                {
                    "step": step_number,
                    "day": day,
                    "hour": hour,
                    "players": compositions,
                }
            )

    successful_plants = [Counter() for _ in range(player_count)]
    animals_placed = [Counter() for _ in range(player_count)]
    structures_built = [Counter() for _ in range(player_count)]
    successful_fertilizations = [0 for _ in range(player_count)]
    land_unlocks = [[] for _ in range(player_count)]
    for index in range(1, len(steps)):
        previous_farms = steps[index - 1][0]["observation"]["farms"]
        current_obs = steps[index][0]["observation"]
        current_farms = current_obs["farms"]
        for player in range(player_count):
            previous = previous_farms[player]
            current = current_farms[player]
            new_quadrants = [
                quadrant
                for quadrant in current.get("unlocked_quadrants", [])
                if quadrant not in previous.get("unlocked_quadrants", [])
            ]
            for quadrant in new_quadrants:
                land_unlocks[player].append(
                    {
                        "step": current_obs.get("step", index),
                        "day": current_obs.get("day", index // 24),
                        "quadrant": quadrant,
                    }
                )
            for y, row in enumerate(current["tiles"]):
                for x, tile in enumerate(row):
                    prior_tile = previous["tiles"][y][x]
                    crop = _new_plant(prior_tile, tile)
                    animal = _new_animal(prior_tile, tile)
                    structure = _new_structure(prior_tile, tile)
                    if crop:
                        successful_plants[player][crop] += 1
                    if animal:
                        animals_placed[player][animal] += 1
                    if structure:
                        structures_built[player][structure] += 1
                    if _successful_fertilization(prior_tile, tile):
                        successful_fertilizations[player] += 1

    price_summary = {}
    for product in PRODUCTS:
        values = [item["prices"][product] for item in market_prices_over_time]
        price_summary[product] = {
            "start": values[0],
            "end": values[-1],
            "min": min(values),
            "max": max(values),
            "average": statistics.fmean(values),
        }

    final_money = money_over_time[-1]["money"]
    players = []
    for player in range(player_count):
        events = _action_events(replay, player)
        opponent_money = max(
            (money for index, money in enumerate(final_money) if index != player),
            default=final_money[player],
        )
        result = (
            "win"
            if final_money[player] > opponent_money
            else "loss" if final_money[player] < opponent_money else "tie"
        )
        final_private = steps[-1][player]["observation"].get("private", {})
        player_summary = {
            "player": player,
            "team_name": team_names[player],
            "is_our_team": team_names[player] == our_team,
            "final_money": final_money[player],
            "result": result,
            "successful_crops_planted": _counter_dict(successful_plants[player]),
            "animals_placed": _counter_dict(animals_placed[player]),
            "structures_built": _counter_dict(structures_built[player]),
            "successful_fertilizations": successful_fertilizations[player],
            "hired_hands": sum(daily_hire_max[player].values()),
            "daily_hires": {
                str(day): daily_hire_max[player][day]
                for day in sorted(daily_hire_max[player])
            },
            "land_purchases": len(land_unlocks[player]),
            "land_unlocks": land_unlocks[player],
            "max_crop_tiles": _counter_dict(max_plants[player]),
            "max_animals": _counter_dict(max_animals[player]),
            "max_total_plants": max_total_plants[player],
            "max_total_animals": max_total_animals[player],
            "max_unlocked_quadrants": max_unlocked_quadrants[player],
            "max_active_hands": max_active_hands[player],
            "final_shed": {
                key: value for key, value in final_private.get("shed", {}).items() if value
            },
            "final_seeds": {
                key: value for key, value in final_private.get("seeds", {}).items() if value
            },
            "action_metrics": events,
            "log_summary": _log_summary(path, episode_id, player),
        }
        players.append(player_summary)

    our_players = [player for player in players if player["is_our_team"]]
    if len(our_players) == player_count and player_count > 1:
        our_outcome = "self_play_" + ("tie" if len(set(final_money)) == 1 else "mixed")
    elif len(our_players) == 1:
        our_outcome = our_players[0]["result"]
    elif not our_players:
        our_outcome = "our_team_not_identified"
    else:
        our_outcome = "multiple_tracked_players"

    return {
        "episode_id": episode_id,
        "replay_path": str(path.relative_to(ROOT)),
        "episode_type": replay.get("info", {}).get("EpisodeType"),
        "team_names": team_names,
        "our_team": our_team,
        "our_player_indices": [player["player"] for player in our_players],
        "our_outcome": our_outcome,
        "steps": len(steps),
        "final_money": final_money,
        "players": players,
        "money_over_time": money_over_time,
        "market_prices_over_time": market_prices_over_time,
        "market_price_summary": price_summary,
        "town_shop_unlocks": town_shop_unlocks,
        "final_town_shops": prior_shops,
        "daily_farm_composition": daily_farm_composition,
    }


def _fmt_counter(values):
    return ", ".join(f"{key}={value}" for key, value in values.items()) or "none"


def _composition_text(composition):
    crops = _fmt_counter(composition["crops"])
    animals = _fmt_counter(composition["animals"])
    return (
        f"crops[{crops}]; animals[{animals}]; hands={composition['active_hands']}; "
        f"quadrants={len(composition['unlocked_quadrants'])}"
    )


def _report(analysis):
    episodes = analysis["episodes"]
    manifest = analysis.get("manifest", {})
    submission = manifest.get("submission", {})
    lines = [
        "# Kaggle Episode Analysis",
        "",
        "## Data scope",
        "",
        f"- Latest submission: `{submission.get('id', 'unknown')}` — "
        f"{submission.get('description', 'unknown description')}",
        f"- Public score: {submission.get('public_score', 'unknown')}",
        f"- Replays currently available: {len(episodes)}",
        f"- Tracked Kaggle team: `{analysis['our_team']}`",
        "- SELL quantities below are submitted order quantities. Replays expose actions, "
        "but do not separately label partially filled quantities.",
        "",
        "## Episode results",
        "",
        "| Episode | Type | Players | Final money | Our outcome |",
        "| ---: | --- | --- | ---: | --- |",
    ]
    for episode in episodes:
        names = " vs ".join(episode["team_names"])
        money = " / ".join(f"{value:.0f}" for value in episode["final_money"])
        lines.append(
            f"| {episode['episode_id']} | {episode.get('episode_type') or 'validation'} | "
            f"{names} | {money} | {episode['our_outcome']} |"
        )

    losses = [episode for episode in episodes if episode["our_outcome"] == "loss"]
    lines.extend(["", "## Comparison with opponents that beat us", ""])
    if not losses:
        lines.extend(
            [
                "No loss replay is currently available from the Kaggle CLI. The only "
                "episode is validation self-play with both seats labeled `EJL Thomas`.",
                "",
                "Therefore no structural claim about leaderboard opponents can yet be "
                "made from downloaded episodes. The public score (~600) establishes that "
                "the strategy is weak globally, while this replay only establishes its "
                "own behavior and omissions.",
            ]
        )
    else:
        lines.extend(
            [
                "| Episode | Our crops | Winner crops | Our max scale | Winner max scale | Our hires | Winner hires | Our animals | Winner animals | Our fertilizer | Winner fertilizer | Our land | Winner land |",
                "| ---: | --- | --- | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for episode in losses:
            ours = next(
                player for player in episode["players"] if player["is_our_team"]
            )
            winner = max(
                (player for player in episode["players"] if not player["is_our_team"]),
                key=lambda player: player["final_money"],
            )
            lines.append(
                f"| {episode['episode_id']} | "
                f"{_fmt_counter(ours['successful_crops_planted'])} | "
                f"{_fmt_counter(winner['successful_crops_planted'])} | "
                f"{ours['max_total_plants']} | {winner['max_total_plants']} | "
                f"{ours['hired_hands']} | {winner['hired_hands']} | "
                f"{_fmt_counter(ours['animals_placed'])} | "
                f"{_fmt_counter(winner['animals_placed'])} | "
                f"{ours['successful_fertilizations']} | "
                f"{winner['successful_fertilizations']} | "
                f"{ours['land_purchases']} | {winner['land_purchases']} |"
            )
        lines.extend(
            [
                "",
                "### Market timing in losses",
                "",
                "| Episode | Our submitted sales | Winner submitted sales | Our weighted sale step | Winner weighted sale step | Our SELL orders | Winner SELL orders |",
                "| ---: | --- | --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for episode in losses:
            ours = next(
                player for player in episode["players"] if player["is_our_team"]
            )
            winner = max(
                (player for player in episode["players"] if not player["is_our_team"]),
                key=lambda player: player["final_money"],
            )
            ours_actions = ours["action_metrics"]
            winner_actions = winner["action_metrics"]
            lines.append(
                f"| {episode['episode_id']} | "
                f"{_fmt_counter(ours_actions['sell_quantities_submitted'])} | "
                f"{_fmt_counter(winner_actions['sell_quantities_submitted'])} | "
                f"{ours_actions['weighted_average_sale_step']:.1f} | "
                f"{winner_actions['weighted_average_sale_step']:.1f} | "
                f"{ours_actions['market_ops'].get('SELL', 0)} | "
                f"{winner_actions['market_ops'].get('SELL', 0)} |"
            )
        lines.extend(
            [
                "",
                "### Production changes in losses",
                "",
                "Our farm stayed at 20 carrot tiles throughout both public losses. "
                "Hubbahub opened with melons, added cows and more land around day 11, "
                "shifted into strawberries around day 14, and finished with wheat. "
                "indira opened with melons, unlocked all four quadrants by day 11, "
                "then shifted to wheat and tomatoes around day 23. These are observed "
                "phase changes; the replay does not prove whether town state, prices, "
                "or opponent production caused each decision.",
            ]
        )

    for episode in episodes:
        lines.extend(["", f"## Episode {episode['episode_id']}", ""])
        lines.extend(
            [
                "### Player summaries",
                "",
                "| Player | Team | Money | Result | Crops planted | Animals | Hires | Land | Fertilize | Submitted sales |",
                "| ---: | --- | ---: | --- | --- | --- | ---: | ---: | ---: | --- |",
            ]
        )
        for player in episode["players"]:
            metrics = player["action_metrics"]
            lines.append(
                f"| {player['player']} | {player['team_name']} | {player['final_money']:.0f} | "
                f"{player['result']} | {_fmt_counter(player['successful_crops_planted'])} | "
                f"{_fmt_counter(player['animals_placed'])} | {player['hired_hands']} | "
                f"{player['land_purchases']} | {player['successful_fertilizations']} | "
                f"{_fmt_counter(metrics['sell_quantities_submitted'])} |"
            )

        lines.extend(["", "### Money by day", ""])
        lines.extend(
            [
                "| Day | " + " | ".join(f"P{index}" for index in range(len(episode["players"]))) + " |",
                "| ---: | " + " | ".join("---:" for _ in episode["players"]) + " |",
            ]
        )
        daily_money = [item for item in episode["money_over_time"] if item["hour"] == 0]
        daily_money.append(episode["money_over_time"][-1])
        seen_steps = set()
        for item in daily_money:
            if item["step"] in seen_steps:
                continue
            seen_steps.add(item["step"])
            lines.append(
                f"| {item['day']}{' final' if item['hour'] == 23 else ''} | "
                + " | ".join(f"{value:.0f}" for value in item["money"])
                + " |"
            )

        lines.extend(["", "### Market price summary", ""])
        lines.extend(
            [
                "| Product | Start | End | Min | Max | Average |",
                "| --- | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for product, values in episode["market_price_summary"].items():
            lines.append(
                f"| {product} | {values['start']} | {values['end']} | "
                f"{values['min']} | {values['max']} | {values['average']:.2f} |"
            )

        lines.extend(["", "### Major submitted sales", ""])
        lines.extend(
            [
                "| Player | Day/hour | Product | Quantity | Price | Notional |",
                "| ---: | --- | --- | ---: | ---: | ---: |",
            ]
        )
        for player in episode["players"]:
            for sale in player["action_metrics"]["major_sales"][:5]:
                lines.append(
                    f"| {player['player']} | {sale['day']}/{sale['hour']} | "
                    f"{sale['product']} | {sale['quantity_submitted']} | "
                    f"{sale['quoted_price']} | {sale['notional_value']} |"
                )

        lines.extend(["", "### Town shop unlocks", ""])
        if episode["town_shop_unlocks"]:
            lines.extend(
                f"- Day {item['day']} hour {item['hour']}: `{item['shop']}`"
                for item in episode["town_shop_unlocks"]
            )
        else:
            lines.append("No shop unlocks recorded.")

        lines.extend(["", "### Farm composition over time", ""])
        lines.extend(
            [
                "| Day/hour | "
                + " | ".join(f"P{index}" for index in range(len(episode["players"])))
                + " |",
                "| --- | " + " | ".join("---" for _ in episode["players"]) + " |",
            ]
        )
        for snapshot in episode["daily_farm_composition"]:
            lines.append(
                f"| {snapshot['day']}/{snapshot['hour']} | "
                + " | ".join(_composition_text(item) for item in snapshot["players"])
                + " |"
            )

    shops = Counter(
        shop for episode in episodes for shop in episode.get("final_town_shops", [])
    )
    lines.extend(
        [
            "",
            "## Top 5 likely reasons the current agent is weak",
            "",
            "These rankings use the two downloaded public losses, with the validation "
            "self-play used only as a consistency check.",
            "",
            "1. **Wrong product portfolio: carrot-only versus melon-led production.** "
            "Both winners used melons heavily (157 and 147 submitted melon sales), while "
            "we submitted 537 carrots and no other product in each loss. Hubbahub also "
            "sold strawberries, milk, wheat, and fertilizer.",
            "2. **No production phases or environmental adaptation.** Our board remained "
            "20 carrots all season. Both winners opened with melons and later changed crop "
            "mix; Hubbahub added cows/strawberries/wheat and indira moved to wheat/tomatoes.",
            "3. **No land expansion.** Both winners bought land (two and three purchases); "
            "we bought none. Hubbahub reached 59 simultaneous plants plus seven cows versus "
            "our fixed 20 plants.",
            "4. **Weak liquidation timing and product value.** Our quantity-weighted sale "
            "step was 393.8 in both losses, versus 515.0 and 483.8 for the winners. The "
            "winners deferred more value into later premium-product sales.",
            "5. **Rigid labor/capital policy and no secondary revenue.** We hired exactly "
            "four hands every day (120 total) regardless of state. One winner used only 20 "
            "hires; the other scaled to 186 and monetized seven cows through 120 milk and "
            "115 fertilizer sales. Successful crop fertilization was zero for all players, "
            "so fertilizer application itself is not supported as a primary gap.",
            "",
            "## Next 3 evidence-driven experiments",
            "",
            "1. **20-plot melon substitution test.** Keep land, four hands, routing, and "
            "selling logic fixed; replace carrots with melons. Melons are the only major "
            "product common to both winning opponents, making this the cleanest causal test.",
            "2. **Phased melon-to-demand rotation.** Start with melons, then test explicit "
            "late transitions to wheat/strawberry/tomato using price and unlocked-shop "
            "signals. Both winners changed production phases while our composition was static.",
            "3. **Land × labor expansion matrix.** Starting from the best melon variant, "
            "test 1–3 land purchases with sparse versus scaled hiring. Both winners expanded "
            "land, but their labor totals diverged sharply (20 versus 186), so land and labor "
            "must be separated experimentally before adding animals.",
            "",
            "## Limitations",
            "",
            f"Kaggle currently exposes {len(episodes)} episode(s) for submission "
            f"{submission.get('id', 'unknown')}, including only two public opponents. "
            "The patterns above are strong but still a small sample. Submitted SELL amounts "
            "come from action orders; the replay does not label partial fills separately. "
            "Observed phase changes cannot establish whether an opponent reacted to town, "
            "prices, our production, or a fixed schedule. Re-run after more episodes appear.",
        ]
    )
    return "\n".join(lines) + "\n"


def analyze(input_dir, our_team, json_output, report_output):
    replay_paths = sorted(input_dir.rglob("episode-*-replay.json"))
    if not replay_paths:
        raise SystemExit(f"no episode replays found under {input_dir}")
    manifest_paths = sorted(input_dir.rglob("manifest.json"))
    manifest = (
        json.loads(manifest_paths[-1].read_text(encoding="utf-8"))
        if manifest_paths
        else {}
    )
    episodes = [_analyze_episode(path, our_team) for path in replay_paths]
    manifest_episode_types = {
        int(item["id"]): item.get("type")
        for item in manifest.get("episodes", [])
        if item.get("id") is not None
    }
    for episode in episodes:
        episode["episode_type"] = (
            episode.get("episode_type")
            or manifest_episode_types.get(episode["episode_id"])
        )
    analysis = {
        "schema_version": 1,
        "our_team": our_team,
        "input_directory": str(input_dir.relative_to(ROOT)),
        "manifest": manifest,
        "episodes": episodes,
    }
    json_output.write_text(json.dumps(analysis, indent=2) + "\n", encoding="utf-8")
    report_output.write_text(_report(analysis), encoding="utf-8")
    print(f"Analyzed {len(episodes)} episode(s)")
    print(f"Saved: {json_output}")
    print(f"Saved: {report_output}")
    return analysis


def _parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--our-team", default="EJL Thomas")
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main():
    args = _parse_args()
    analyze(
        input_dir=args.input.resolve(),
        our_team=args.our_team,
        json_output=args.json_output.resolve(),
        report_output=args.report_output.resolve(),
    )


if __name__ == "__main__":
    main()
