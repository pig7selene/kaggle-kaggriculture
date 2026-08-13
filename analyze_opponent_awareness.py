"""Diagnose opponent-awareness evidence in public Kaggriculture replays.

The analysis deliberately uses only public farm state and action-derived
history for opponent signals.  Replay-private inventories are used by the
environment transaction reconstructor only to validate actual public actions;
they are never exposed as model features.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from kaggle_environments.envs.kaggriculture import kaggriculture as game

from analyze_top_player_replays import (
    _add_ledger,
    _farm_snapshot,
    _new_daily,
    _serialize_daily,
    _transition_ledger,
)


ROOT = Path(__file__).resolve().parent
NEWEST_DIR = ROOT / "experiments" / "kaggle_episodes" / "submission_55429527"
TOP_DIR = ROOT / "experiments" / "top_player_replays"
DEFAULT_OUTPUT = ROOT / "experiments" / "opponent_aware_diagnosis.json"
DEFAULT_REPORT = ROOT / "experiments" / "opponent_aware_diagnosis.md"
OUR_TEAM = "Selene"
PRODUCTS = tuple(game.PRODUCTS)
CROPS = tuple(game.CROPS)
ANIMAL_PRODUCTS = {animal: data["product"] for animal, data in game.ANIMALS.items()}
LAND_BOOK_VALUE = {1: 0, 2: 1000, 3: 3000, 4: 7000}


def _plain(values):
    return {key: values[key] for key in sorted(values) if values[key]}


def _pearson(xs, ys):
    if len(xs) < 3 or len(xs) != len(ys):
        return None
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    dx = [value - mx for value in xs]
    dy = [value - my for value in ys]
    denominator = math.sqrt(sum(value * value for value in dx) * sum(value * value for value in dy))
    if denominator <= 1e-12:
        return 0.0
    return sum(left * right for left, right in zip(dx, dy)) / denominator


def _percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = fraction * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _farm_detail(farm, day, horizon=3):
    snapshot = _farm_snapshot(farm)
    maturing_tiles = Counter()
    maturing_units = Counter()
    ready_now = Counter()
    livestock_due = Counter()
    for row in farm["tiles"]:
        for tile in row:
            if not isinstance(tile, dict):
                continue
            if tile.get("kind") == "PLANT":
                crop = tile["crop"]
                data = game.CROPS[crop]
                age = day - int(tile.get("planted_day", day))
                if tile.get("yield_units", 0) > 0 and age >= data["first_yield_day"]:
                    ready_now[crop] += int(tile.get("yield_units", 0))
                if data["ongoing"]:
                    first = int(data["first_yield_day"])
                    interval = int(data["interval"])
                    for future_age in range(age + 1, age + horizon + 1):
                        if future_age >= first and (future_age - first) % interval == 0:
                            maturing_units[crop] += 1
                            maturing_tiles[crop] += 1
                            break
                else:
                    peak = int(data["max_yield_day"])
                    delta = peak - age
                    if 0 <= delta <= horizon:
                        maturing_tiles[crop] += 1
                        # Watering state is public, but the maximum-yield estimate
                        # is the most stable supply-pressure signal across policies.
                        maturing_units[crop] += int(data["max_yield"])
            elif tile.get("kind") in {"COOP", "PASTURE"} and tile.get("animal"):
                animal = tile["animal"]
                data = game.ANIMALS[animal]
                placed = int(tile.get("placed_day", day))
                product = data["product"]
                for future_day in range(day + 1, day + horizon + 1):
                    since_first = future_day - placed - int(data["first_yield_day"])
                    if since_first >= 0 and since_first % int(data["interval"]) == 0:
                        livestock_due[product] += 1
    snapshot.update(
        {
            "maturing_soon_tiles": _plain(maturing_tiles),
            "maturing_soon_units": _plain(maturing_units),
            "ready_now_units": _plain(ready_now),
            "livestock_due_soon": _plain(livestock_due),
        }
    )
    return snapshot


def _extend_daily(day):
    row = _new_daily(day)
    row.update(
        {
            "market_start": None,
            "market_end": None,
            "town_shops_end": [],
            "estimated_unsold_flow": {},
            "estimated_inventory_value": 0.0,
            "estimated_equity": 0.0,
            "cumulative_sale_revenue": {},
            "cumulative_capital_spending": 0.0,
        }
    )
    return row


def _reconstruct(path):
    replay = json.loads(path.read_text(encoding="utf-8"))
    steps = replay["steps"]
    names = list(replay["info"]["TeamNames"])
    configuration = dict(replay.get("configuration", {}))
    day_count = int(configuration.get("episodeSteps", 720)) // int(configuration.get("turnsPerDay", 24))
    daily = [[_extend_daily(day) for day in range(day_count)] for _ in names]
    for state_index, states in enumerate(steps):
        obs = states[0]["observation"]
        day = min(day_count - 1, int(obs.get("day", obs.get("step", state_index) // 24)))
        market = {
            "inventory": dict(obs["market"]["inventory"]),
            "prices": dict(obs["market"]["prices"]),
        }
        for player, farm in enumerate(obs["farms"]):
            row = daily[player][day]
            money = float(farm["money"])
            if row["bank_start"] is None:
                row["bank_start"] = money
                row["market_start"] = market
            row["bank_end"] = money
            row["market_end"] = market
            row["town_shops_end"] = list(obs.get("town", {}).get("unlocked_shops", []))
            row["max_hands"] = max(row["max_hands"], len(farm.get("hands", [])))
            row["farm"] = _farm_detail(farm, day)

    mismatches = []
    for index in range(1, len(steps)):
        previous_obs = steps[index - 1][0]["observation"]
        day = min(day_count - 1, int(previous_obs.get("day", (index - 1) // 24)))
        hour = int(previous_obs.get("hour", (index - 1) % 24))
        ledgers, transition_mismatches = _transition_ledger(
            steps[index - 1], steps[index], configuration
        )
        for mismatch in transition_mismatches:
            mismatches.append({"step": index, **mismatch})
        for player, ledger in enumerate(ledgers):
            _add_ledger(daily[player][day], ledger, day, hour)

    final_money = [float(state["reward"]) for state in steps[-1]]
    timelines = []
    for player, rows in enumerate(daily):
        cumulative_sales = Counter()
        cumulative_capital = 0.0
        unsold = Counter()
        serialized = []
        for row in rows:
            item = _serialize_daily(row)
            cumulative_sales.update(item["sale_revenue"])
            cumulative_capital += item["total_capital_spending"]
            for product, quantity in item["harvests"].items():
                unsold[product] += quantity
            for product, quantity in item["sales"].items():
                unsold[product] = max(0, unsold[product] - quantity)
            item["cumulative_sale_revenue"] = _plain(cumulative_sales)
            item["cumulative_capital_spending"] = cumulative_capital
            item["estimated_unsold_flow"] = _plain(unsold)
            prices = (item.get("market_end") or {}).get("prices", {})
            inventory_value = sum(unsold[product] * prices.get(product, 0) for product in unsold)
            farm = item["farm"]
            crop_book = sum(
                count * game.CROPS[crop]["seed"] for crop, count in farm.get("crops", {}).items()
            )
            animal_book = sum(
                count * game.ANIMALS[animal]["cost"]
                for animal, count in farm.get("animals", {}).items()
            )
            land_book = LAND_BOOK_VALUE.get(farm.get("quadrants", 1), 0)
            item["estimated_inventory_value"] = inventory_value
            item["estimated_equity"] = (
                float(item["bank_end"] or 0) + inventory_value + crop_book + animal_book + land_book
            )
            serialized.append(item)
        timelines.append(serialized)

    return {
        "episode_id": int(replay["info"]["EpisodeId"]),
        "seed": replay["info"].get("seed"),
        "team_names": names,
        "final_money": final_money,
        "timelines": timelines,
        "financial_reconstruction_mismatches": mismatches,
    }


def _weighted_average_price(timeline, product):
    quantity = sum(row["sales"].get(product, 0) for row in timeline)
    revenue = sum(row["sale_revenue"].get(product, 0) for row in timeline)
    return revenue / quantity if quantity else None


def _first_durable_positive(values, threshold=0.0, required_fraction=0.80):
    for day, value in enumerate(values):
        tail = values[day:]
        if value >= threshold and sum(candidate > 0 for candidate in tail) / len(tail) >= required_fraction:
            if all(candidate > 0 for candidate in tail[-3:]):
                return day
    return None


def _classify_loss(our, opponent, decisive_day):
    categories = []
    final_our, final_opp = our[-1], opponent[-1]
    opp_crop_revenue = sum(
        sum(row["sale_revenue"].get(crop, 0) for row in opponent) for crop in CROPS
    )
    our_crop_revenue = sum(
        sum(row["sale_revenue"].get(crop, 0) for row in our) for crop in CROPS
    )
    livestock_products = set(ANIMAL_PRODUCTS.values()) | {"FERTILIZER"}
    opp_animal_revenue = sum(
        sum(row["sale_revenue"].get(product, 0) for row in opponent)
        for product in livestock_products
    )
    our_animal_revenue = sum(
        sum(row["sale_revenue"].get(product, 0) for row in our)
        for product in livestock_products
    )
    if decisive_day is not None and decisive_day <= 10:
        categories.append("opening / early compounding")
    day = min(29, decisive_day if decisive_day is not None else 20)
    if (
        opponent[day]["farm"]["quadrants"] > our[day]["farm"]["quadrants"]
        or opponent[day]["farm"]["productive_tiles"] - our[day]["farm"]["productive_tiles"] >= 10
        or opponent[day]["max_hands"] - our[day]["max_hands"] >= 3
    ):
        categories.append("land/labor scaling")
    if opp_crop_revenue - our_crop_revenue >= 5000:
        categories.append("crop choice")
    if opp_animal_revenue - our_animal_revenue >= 3000:
        categories.append("livestock")
    common_products = [product for product in PRODUCTS if _weighted_average_price(our, product) is not None and _weighted_average_price(opponent, product) is not None]
    if common_products:
        price_edges = [
            _weighted_average_price(opponent, product) - _weighted_average_price(our, product)
            for product in common_products
        ]
        if statistics.fmean(price_edges) >= 25:
            categories.append("market timing")
    if decisive_day is not None and decisive_day >= 26:
        categories.append("endgame liquidation")
    if (
        final_our["farm"]["productive_tiles"] >= final_opp["farm"]["productive_tiles"]
        and sum(final_our["cumulative_sale_revenue"].values()) + 5000 < sum(final_opp["cumulative_sale_revenue"].values())
    ):
        categories.append("routing/execution")
    return categories or ["mixed / no single dominant mechanism"]


def _episode_diagnosis(record, our_team):
    if our_team not in record["team_names"]:
        return None
    ours = record["team_names"].index(our_team)
    theirs = 1 - ours
    our = record["timelines"][ours]
    opponent = record["timelines"][theirs]
    final_gap = record["final_money"][ours] - record["final_money"][theirs]
    winner = ours if final_gap > 0 else theirs if final_gap < 0 else None
    equity_gap_opp = [opp["estimated_equity"] - me["estimated_equity"] for me, opp in zip(our, opponent)]
    bank_gap_opp = [float(opp["bank_end"]) - float(me["bank_end"]) for me, opp in zip(our, opponent)]
    decisive_threshold = max(2500.0, abs(final_gap) * 0.08)
    decisive = _first_durable_positive(equity_gap_opp, decisive_threshold) if winner == theirs else None
    durable_bank = _first_durable_positive(bank_gap_opp, 0.0) if winner == theirs else None
    our_revenue = Counter()
    opponent_revenue = Counter()
    for row in our:
        our_revenue.update(row["sale_revenue"])
    for row in opponent:
        opponent_revenue.update(row["sale_revenue"])
    return {
        "episode_id": record["episode_id"],
        "seed": record["seed"],
        "our_seat": ours,
        "opponent": record["team_names"][theirs],
        "result": "win" if final_gap > 0 else "loss" if final_gap < 0 else "tie",
        "our_final_money": record["final_money"][ours],
        "opponent_final_money": record["final_money"][theirs],
        "final_advantage": final_gap,
        "decisive_equity_gap_day": decisive,
        "durable_bank_gap_day": durable_bank,
        "loss_classification": _classify_loss(our, opponent, decisive) if final_gap < 0 else [],
        "our_sale_revenue": _plain(our_revenue),
        "opponent_sale_revenue": _plain(opponent_revenue),
        "our_timeline": our,
        "opponent_timeline": opponent,
    }


def _future_sales(timeline, day, product, horizon=3):
    return sum(
        timeline[index]["sales"].get(product, 0)
        for index in range(day + 1, min(len(timeline), day + horizon + 1))
    )


def _signal_study(records):
    rows = []
    for record in records:
        for player, timeline in enumerate(record["timelines"]):
            for day in range(len(timeline) - 3):
                farm = timeline[day]["farm"]
                for product in PRODUCTS:
                    crop_area = farm.get("crops", {}).get(product, 0) if product in CROPS else 0
                    maturing = farm.get("maturing_soon_units", {}).get(product, 0)
                    livestock_due = farm.get("livestock_due_soon", {}).get(product, 0)
                    recent_sales = sum(
                        timeline[index]["sales"].get(product, 0)
                        for index in range(max(0, day - 1), day + 1)
                    )
                    rows.append(
                        {
                            "episode_id": record["episode_id"],
                            "player": player,
                            "day": day,
                            "product": product,
                            "crop_area": crop_area,
                            "maturing_soon": maturing,
                            "livestock_due": livestock_due,
                            "recent_sales": recent_sales,
                            "future_sales": _future_sales(timeline, day, product),
                        }
                    )
    results = {}
    for product in PRODUCTS:
        product_rows = [row for row in rows if row["product"] == product]
        signals = {}
        for signal in ("crop_area", "maturing_soon", "livestock_due", "recent_sales"):
            xs = [row[signal] for row in product_rows]
            ys = [row["future_sales"] for row in product_rows]
            positive_x = [value for value in xs if value > 0]
            high_cut = _percentile(positive_x, 0.75) if positive_x else None
            high_rows = [row for row in product_rows if high_cut is not None and row[signal] >= high_cut]
            low_rows = [row for row in product_rows if not row[signal]]
            signals[signal] = {
                "correlation_with_next_3d_sales": _pearson(xs, ys),
                "high_signal_cutoff": high_cut,
                "mean_future_sales_when_high": statistics.fmean(row["future_sales"] for row in high_rows) if high_rows else None,
                "mean_future_sales_when_zero": statistics.fmean(row["future_sales"] for row in low_rows) if low_rows else None,
                "high_signal_observations": len(high_rows),
                "total_observations": len(product_rows),
            }
        results[product] = signals
    return {"observations": len(rows), "by_product": results}


def _pairwise_l1(vectors):
    if len(vectors) < 2:
        return 0.0
    distances = []
    for left_index, left in enumerate(vectors):
        for right in vectors[left_index + 1:]:
            keys = set(left) | set(right)
            distances.append(sum(abs(left.get(key, 0) - right.get(key, 0)) for key in keys))
    return statistics.fmean(distances) if distances else 0.0


def _template_study(top_records, manifest):
    selected = {row["team_name"]: row for row in manifest["players"]}
    appearances = defaultdict(list)
    for record in top_records:
        for player, name in enumerate(record["team_names"]):
            if name in selected:
                appearances[name].append(
                    {
                        "episode_id": record["episode_id"],
                        "opponent": record["team_names"][1 - player],
                        "timeline": record["timelines"][player],
                        "opponent_timeline": record["timelines"][1 - player],
                    }
                )
    players = []
    centered_samples = {"crop_area": defaultdict(list), "planting": defaultdict(list), "selling": defaultdict(list)}
    for name, games in appearances.items():
        land_schedules = []
        animal_purchase_schedules = []
        daily_crop_variation = []
        daily_planting_variation = []
        daily_sale_variation = []
        daily_hand_range = []
        for game_row in games:
            timeline = game_row["timeline"]
            land_schedules.append([row["day"] for row in timeline for _ in range(row["land_purchases"])])
            animal_purchase_schedules.append(
                [(row["day"], animal, quantity) for row in timeline for animal, quantity in row["animal_purchases"].items()]
            )
        for day in range(30):
            crop_vectors = [game_row["timeline"][day]["farm"].get("crops", {}) for game_row in games]
            planting_vectors = [game_row["timeline"][day]["plantings"] for game_row in games]
            sale_vectors = [game_row["timeline"][day]["sales"] for game_row in games]
            hand_values = [game_row["timeline"][day]["max_hands"] for game_row in games]
            daily_crop_variation.append(_pairwise_l1(crop_vectors))
            daily_planting_variation.append(_pairwise_l1(planting_vectors))
            daily_sale_variation.append(_pairwise_l1(sale_vectors))
            daily_hand_range.append(max(hand_values) - min(hand_values))
            # Demean within agent/day to remove the shared template before
            # correlating an opponent signal with the player's deviation.
            for crop in CROPS:
                opp_values = [game_row["opponent_timeline"][day]["farm"].get("crops", {}).get(crop, 0) for game_row in games]
                own_area = [game_row["timeline"][day]["farm"].get("crops", {}).get(crop, 0) for game_row in games]
                own_plant = [game_row["timeline"][day]["plantings"].get(crop, 0) for game_row in games]
                own_sell = [game_row["timeline"][day]["sales"].get(crop, 0) for game_row in games]
                if len(games) >= 2:
                    opp_mean = statistics.fmean(opp_values)
                    for label, values in (("crop_area", own_area), ("planting", own_plant), ("selling", own_sell)):
                        own_mean = statistics.fmean(values)
                        centered_samples[label][crop].extend(
                            (opp - opp_mean, own - own_mean) for opp, own in zip(opp_values, values)
                        )
        players.append(
            {
                "team_name": name,
                "leaderboard_score": selected[name]["leaderboard_score"],
                "appearances": len(games),
                "land_schedules": land_schedules,
                "identical_land_schedule": len({tuple(value) for value in land_schedules}) == 1,
                "animal_purchase_schedules": animal_purchase_schedules,
                "mean_daily_crop_composition_l1": statistics.fmean(daily_crop_variation),
                "mean_daily_planting_l1": statistics.fmean(daily_planting_variation),
                "mean_daily_sale_l1": statistics.fmean(daily_sale_variation),
                "max_daily_hand_range": max(daily_hand_range),
            }
        )
    correlations = {}
    for decision, by_crop in centered_samples.items():
        correlations[decision] = {}
        for crop, pairs in by_crop.items():
            correlations[decision][crop] = {
                "within_agent_day_correlation_with_opponent_crop_area": _pearson(
                    [pair[0] for pair in pairs], [pair[1] for pair in pairs]
                ),
                "observations": len(pairs),
            }
    return {
        "players": sorted(players, key=lambda row: row["leaderboard_score"], reverse=True),
        "within_agent_reactivity": correlations,
    }


def _summary_markdown(result):
    lines = [
        "# Opponent-awareness replay diagnosis",
        "",
        "This is the factual, pre-implementation diagnosis. Opponent features use only",
        "public farm state and public action history; replay-private inventory is excluded.",
        "",
        "## Newest submission episodes",
        "",
        f"Submission: {result['newest_submission']['submission_id']} (public score {result['newest_submission']['public_score']})",
        "",
        "| Episode | Opponent | Seat | Result | Final money | Advantage | Decisive equity day | Durable bank day | Classification |",
        "| ---: | --- | ---: | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in result["newest_submission"]["episodes"]:
        lines.append(
            f"| {row['episode_id']} | {row['opponent']} | {row['our_seat']} | {row['result']} | "
            f"{row['our_final_money']:.0f} | {row['final_advantage']:+.0f} | "
            f"{row['decisive_equity_gap_day'] if row['decisive_equity_gap_day'] is not None else '-'} | "
            f"{row['durable_bank_gap_day'] if row['durable_bank_gap_day'] is not None else '-'} | "
            f"{', '.join(row['loss_classification']) or '-'} |"
        )
    losses = [row for row in result["newest_submission"]["episodes"] if row["result"] == "loss"]
    decisive = [row["decisive_equity_gap_day"] for row in losses if row["decisive_equity_gap_day"] is not None]
    lines.extend(
        [
            "",
            f"Median decisive equity-gap day across classifiable losses: **{statistics.median(decisive) if decisive else 'n/a'}**.",
            "",
            "## High-rated-agent template check",
            "",
            "| Player | Rating | Games | Identical land schedule | Mean crop L1/day | Mean planting L1/day | Mean sale L1/day | Max hand range |",
            "| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in result["top_template_study"]["players"]:
        lines.append(
            f"| {row['team_name']} | {row['leaderboard_score']:.1f} | {row['appearances']} | "
            f"{row['identical_land_schedule']} | {row['mean_daily_crop_composition_l1']:.2f} | "
            f"{row['mean_daily_planting_l1']:.2f} | {row['mean_daily_sale_l1']:.2f} | "
            f"{row['max_daily_hand_range']} |"
        )
    lines.extend(
        [
            "",
            "## Public-signal predictive checks",
            "",
            "Correlation is with the same player's actual sales during the next three days.",
            "",
            "| Product | Crop area r | Maturing-soon r | Livestock-due r | Recent-sales r |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for product, signals in result["signal_predictiveness"]["by_product"].items():
        def fmt(name):
            value = signals[name]["correlation_with_next_3d_sales"]
            return "-" if value is None else f"{value:+.3f}"
        lines.append(
            f"| {product} | {fmt('crop_area')} | {fmt('maturing_soon')} | "
            f"{fmt('livestock_due')} | {fmt('recent_sales')} |"
        )
    lines.extend(
        [
            "",
            "Complete 30-day timelines for both players and exact economic ledgers are in",
            "`experiments/opponent_aware_diagnosis.json`.",
            "",
        ]
    )
    return "\n".join(lines)


def analyze(newest_dir, top_dir, output, report):
    newest_paths = sorted((newest_dir / "replays").glob("episode-*-replay.json"))
    top_paths = sorted((top_dir / "replays").glob("episode-*-replay.json"))
    if not newest_paths or not top_paths:
        raise RuntimeError("newest or top-player replay corpus is empty")
    newest_records = [_reconstruct(path) for path in newest_paths]
    top_records = [_reconstruct(path) for path in top_paths]
    manifest = json.loads((top_dir / "manifest.json").read_text(encoding="utf-8"))
    episode_diagnoses = [
        diagnosis for record in newest_records
        if (diagnosis := _episode_diagnosis(record, OUR_TEAM)) is not None
    ]
    mismatches = [
        {"corpus": corpus, "episode_id": record["episode_id"], **mismatch}
        for corpus, records in (("newest", newest_records), ("top", top_records))
        for record in records
        for mismatch in record["financial_reconstruction_mismatches"]
    ]
    result = {
        "schema_version": 1,
        "method": {
            "opponent_information": "public farms plus action-derived public history only",
            "maturing_horizon_days": 3,
            "estimated_inventory": "cumulative observed harvest minus successful sales; upper-bound flow estimate",
            "decisive_gap": "first equity-proxy lead over max(2500, 8% final gap) positive on >=80% of remaining days and final 3 days",
        },
        "newest_submission": {
            "submission_id": 55429527,
            "public_score": 741.0,
            "episodes": sorted(episode_diagnoses, key=lambda row: row["episode_id"]),
            "wins": sum(row["result"] == "win" for row in episode_diagnoses),
            "losses": sum(row["result"] == "loss" for row in episode_diagnoses),
            "ties": sum(row["result"] == "tie" for row in episode_diagnoses),
        },
        "top_template_study": _template_study(top_records, manifest),
        "signal_predictiveness": _signal_study([*newest_records, *top_records]),
        "financial_reconstruction_mismatches": mismatches,
        "source_replays": {
            "newest": [record["episode_id"] for record in newest_records],
            "top": [record["episode_id"] for record in top_records],
        },
    }
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    report.write_text(_summary_markdown(result), encoding="utf-8")
    print(
        f"Analyzed {len(newest_records)} newest and {len(top_records)} top-player replays; "
        f"financial mismatches={len(mismatches)}"
    )
    print(f"Saved {output}")
    print(f"Saved {report}")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--newest-dir", type=Path, default=NEWEST_DIR)
    parser.add_argument("--top-dir", type=Path, default=TOP_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    analyze(args.newest_dir.resolve(), args.top_dir.resolve(), args.output.resolve(), args.report.resolve())


if __name__ == "__main__":
    main()
