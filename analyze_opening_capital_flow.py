"""Reconstruct exact day 0-10 capital flows from public Kaggriculture replays.

The JSON output is the audit artifact.  Each ``economic_turns`` row describes
one transition whose action had a successful economic effect, with the replay
bank immediately before and after that transition.  The Markdown file is a
human-readable rendering of the representative corpus and aggregate funding
milestones.
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from analyze_top_player_replays import _farm_snapshot, _transition_ledger


ROOT = Path(__file__).resolve().parent
DEFAULT_CORPUS = ROOT / "experiments" / "top_player_replays"
DEFAULT_JSON = ROOT / "experiments" / "opening_capital_flow_top.json"
DEFAULT_MARKDOWN = ROOT / "experiments" / "opening_capital_flow_top.md"
REPRESENTATIVE_EPISODES = {91866168, 91869967, 91870919, 91870920}


def _plain(counter):
    return {key: counter[key] for key in sorted(counter) if counter[key]}


def _ledger_dict(ledger):
    sales = []
    for product, quantity in sorted(ledger["sale_quantity"].items()):
        prices = ledger["sale_prices"][product]
        sales.append(
            {
                "item": product,
                "quantity": quantity,
                "revenue": ledger["sale_revenue"][product],
                "unit_prices": list(prices),
                "average_price": statistics.fmean(prices),
            }
        )
    result = {
        "crops_planted": _plain(ledger["plant_quantity"]),
        "items_harvested": _plain(ledger["harvest_quantity"]),
        "fertilizer_collected": ledger["fertilizer_collected"],
        "structures_built": _plain(ledger["structures_built"]),
        "animals_placed": _plain(ledger["animals_placed"]),
        "feed_actions": ledger["feed_actions"],
        "care_actions": ledger["care_actions"],
        "sales": sales,
        "seed_bought": _plain(ledger["seed_quantity"]),
        "seed_spending": _plain(ledger["seed_spend"]),
        "feed_bought": _plain(ledger["product_quantity"]),
        "feed_spending": _plain(ledger["product_spend"]),
        "animals_bought": _plain(ledger["animal_quantity"]),
        "animal_spending": _plain(ledger["animal_spend"]),
        "hands_hired": ledger["hire_count"],
        "labor_spending": ledger["labor_spend"],
        "land_bought": ledger["land_count"],
        "land_spending": ledger["land_spend"],
    }
    result["sale_revenue"] = sum(event["revenue"] for event in sales)
    result["total_spending"] = (
        sum(result["seed_spending"].values())
        + sum(result["feed_spending"].values())
        + sum(result["animal_spending"].values())
        + result["labor_spending"]
        + result["land_spending"]
    )
    return result


def _has_event(ledger):
    ignored = {"feed_actions", "care_actions"}
    return any(value for key, value in ledger.items() if key not in ignored)


def _accumulate(capital, ledger):
    for event in ledger["sales"]:
        capital["revenue_by_product"][event["item"]] += event["revenue"]
    for product, amount in ledger["seed_spending"].items():
        capital["seed_spending"][product] += amount
    for product, amount in ledger["feed_spending"].items():
        capital["feed_spending"][product] += amount
    for animal, amount in ledger["animal_spending"].items():
        capital["animal_spending"][animal] += amount
    capital["labor_spending"] += ledger["labor_spending"]
    capital["land_spending"] += ledger["land_spending"]


def _capital_snapshot(capital, bank):
    revenue = sum(capital["revenue_by_product"].values())
    spending = (
        sum(capital["seed_spending"].values())
        + sum(capital["feed_spending"].values())
        + sum(capital["animal_spending"].values())
        + capital["labor_spending"]
        + capital["land_spending"]
    )
    return {
        "starting_money": 3000,
        "revenue_by_product": _plain(capital["revenue_by_product"]),
        "total_revenue": revenue,
        "seed_spending": _plain(capital["seed_spending"]),
        "feed_spending": _plain(capital["feed_spending"]),
        "animal_spending": _plain(capital["animal_spending"]),
        "labor_spending": capital["labor_spending"],
        "land_spending": capital["land_spending"],
        "total_spending": spending,
        "reconstructed_bank": 3000 + revenue - spending,
        "observed_bank": bank,
    }


def _analyze_appearance(path, replay, player):
    episode_id = int(replay["info"]["EpisodeId"])
    names = list(replay["info"]["TeamNames"])
    steps = replay["steps"]
    configuration = dict(replay.get("configuration", {}))
    capital = {
        "revenue_by_product": Counter(),
        "seed_spending": Counter(),
        "feed_spending": Counter(),
        "animal_spending": Counter(),
        "labor_spending": 0,
        "land_spending": 0,
    }
    turns = []
    milestones = []
    mismatch_count = 0
    land_number = 0
    reached_eight_cows = False
    for index in range(1, len(steps)):
        previous = steps[index - 1][0]["observation"]
        day = int(previous.get("day", previous.get("step", index - 1) // 24))
        if day > 10:
            break
        hour = int(previous.get("hour", (index - 1) % 24))
        ledgers, mismatches = _transition_ledger(steps[index - 1], steps[index], configuration)
        mismatch_count += len(mismatches)
        ledger = _ledger_dict(ledgers[player])
        before_farm = previous["farms"][player]
        after_farm = steps[index][0]["observation"]["farms"][player]
        before_bank = float(before_farm["money"])
        after_bank = float(after_farm["money"])
        _accumulate(capital, ledger)
        if _has_event(ledger):
            turns.append(
                {
                    "step": int(previous.get("step", index - 1)),
                    "day": day,
                    "hour": hour,
                    "bank_before": before_bank,
                    "bank_after": after_bank,
                    "bank_delta": after_bank - before_bank,
                    "events": ledger,
                    "farm_after": _farm_snapshot(after_farm),
                }
            )
        if ledger["land_bought"]:
            for _ in range(ledger["land_bought"]):
                land_number += 1
                milestones.append(
                    {
                        "milestone": f"land_{land_number}",
                        "step": int(previous.get("step", index - 1)),
                        "day": day,
                        "hour": hour,
                        "bank_before_turn": before_bank,
                        "bank_after_turn": after_bank,
                        "farm_after": _farm_snapshot(after_farm),
                        "capital_through_event": _capital_snapshot(capital, after_bank),
                    }
                )
        animals = _farm_snapshot(after_farm)["animals"]
        if animals.get("COW", 0) >= 8 and not reached_eight_cows:
            reached_eight_cows = True
            milestones.append(
                {
                    "milestone": "eight_cows",
                    "step": int(previous.get("step", index - 1)),
                    "day": day,
                    "hour": hour,
                    "bank_before_turn": before_bank,
                    "bank_after_turn": after_bank,
                    "farm_after": _farm_snapshot(after_farm),
                    "capital_through_event": _capital_snapshot(capital, after_bank),
                }
            )
    checkpoints = []
    for day in range(11):
        observations = [
            states[0]["observation"]
            for states in steps
            if int(states[0]["observation"].get("day", -1)) == day
        ]
        if not observations:
            continue
        start = observations[0]["farms"][player]
        next_day = next(
            (
                states[0]["observation"]["farms"][player]
                for states in steps
                if int(states[0]["observation"].get("day", -1)) == day + 1
            ),
            observations[-1]["farms"][player],
        )
        checkpoints.append(
            {
                "day": day,
                "bank_start": float(start["money"]),
                "bank_after_day": float(next_day["money"]),
                "max_hands": max(len(obs["farms"][player].get("hands", [])) for obs in observations),
                "farm_start": _farm_snapshot(start),
                "farm_after_day": _farm_snapshot(next_day),
            }
        )
    final_opening_farm = checkpoints[-1]["farm_after_day"]
    return {
        "episode_id": episode_id,
        "seed": replay["info"].get("seed"),
        "player": player,
        "team_name": names[player],
        "opponent": names[1 - player],
        "source_replay": str(path.relative_to(ROOT)),
        "financial_reconstruction_mismatches": mismatch_count,
        "economic_turns": turns,
        "milestones": milestones,
        "daily_checkpoints": checkpoints,
        "capital_through_day_10": _capital_snapshot(
            capital, checkpoints[-1]["bank_after_day"]
        ),
        "farm_after_day_10": final_opening_farm,
    }


def _median(values):
    return statistics.median(values) if values else None


def _aggregate(appearances):
    by_milestone = defaultdict(list)
    for appearance in appearances:
        for milestone in appearance["milestones"]:
            by_milestone[milestone["milestone"]].append(milestone)
    milestone_summary = {}
    for name, events in sorted(by_milestone.items()):
        revenue_products = defaultdict(list)
        for event in events:
            revenue = event["capital_through_event"]["revenue_by_product"]
            for product in {key for row in events for key in row["capital_through_event"]["revenue_by_product"]}:
                revenue_products[product].append(revenue.get(product, 0))
        milestone_summary[name] = {
            "appearances": len(events),
            "median_day": _median([row["day"] for row in events]),
            "day_range": [min(row["day"] for row in events), max(row["day"] for row in events)],
            "median_hour": _median([row["hour"] for row in events]),
            "median_bank_after": _median([row["bank_after_turn"] for row in events]),
            "median_cumulative_revenue_by_product": {
                product: _median(values) for product, values in sorted(revenue_products.items())
            },
            "median_total_revenue": _median(
                [row["capital_through_event"]["total_revenue"] for row in events]
            ),
            "median_total_spending": _median(
                [row["capital_through_event"]["total_spending"] for row in events]
            ),
        }
    checkpoints = {}
    for day in range(11):
        rows = [
            checkpoint
            for appearance in appearances
            for checkpoint in appearance["daily_checkpoints"]
            if checkpoint["day"] == day
        ]
        if not rows:
            continue
        checkpoints[str(day)] = {
            "appearances": len(rows),
            "median_bank_start": _median([row["bank_start"] for row in rows]),
            "median_bank_after_day": _median([row["bank_after_day"] for row in rows]),
            "median_max_hands": _median([row["max_hands"] for row in rows]),
            "median_productive_tiles_after_day": _median(
                [row["farm_after_day"]["productive_tiles"] for row in rows]
            ),
            "median_quadrants_after_day": _median(
                [row["farm_after_day"]["quadrants"] for row in rows]
            ),
            "median_cows_after_day": _median(
                [row["farm_after_day"]["animals"].get("COW", 0) for row in rows]
            ),
            "median_sheep_after_day": _median(
                [row["farm_after_day"]["animals"].get("SHEEP", 0) for row in rows]
            ),
        }
    return {"milestones": milestone_summary, "daily_checkpoints": checkpoints}


def _event_text(events):
    pieces = []
    for key, label in (
        ("crops_planted", "plant"),
        ("items_harvested", "harvest"),
        ("animals_bought", "buy animal"),
        ("animals_placed", "place animal"),
        ("seed_bought", "buy seed"),
        ("feed_bought", "buy feed"),
    ):
        if events[key]:
            pieces.append(f"{label} {events[key]}")
    if events["fertilizer_collected"]:
        pieces.append(f"collect fertilizer {events['fertilizer_collected']}")
    for sale in events["sales"]:
        pieces.append(
            f"sell {sale['quantity']} {sale['item']} for ${sale['revenue']} "
            f"@ {sale['unit_prices']}"
        )
    if events["hands_hired"]:
        pieces.append(f"hire {events['hands_hired']} (${events['labor_spending']})")
    if events["land_bought"]:
        pieces.append(f"buy land {events['land_bought']} (${events['land_spending']})")
    if events["structures_built"]:
        pieces.append(f"build {events['structures_built']}")
    return "; ".join(pieces)


def _write_markdown(output, analysis):
    lines = [
        "# Top-player opening capital-flow audit",
        "",
        "This audit reconstructs successful actions by replaying every public action against the prior replay state. Bank values are the observed values immediately before and after the whole turn; multiple simultaneous market orders can share one row.",
        "",
        f"- Public appearances audited: {len(analysis['all_selected_appearances'])}",
        f"- Representative appearances rendered turn-by-turn: {len(analysis['representative_appearances'])}",
        f"- Financial reconstruction mismatches: {analysis['financial_reconstruction_mismatches']}",
        "",
        "## Aggregate funding milestones",
        "",
        "| Milestone | n | Typical time | Median bank after | Median cumulative sales |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, row in analysis["aggregate"]["milestones"].items():
        lines.append(
            f"| {name} | {row['appearances']} | day {row['median_day']}, hour {row['median_hour']} | "
            f"${row['median_bank_after']:,.0f} | ${row['median_total_revenue']:,.0f} |"
        )
    lines.extend(["", "### Median cumulative revenue available at each milestone", ""])
    products = sorted(
        {
            product
            for row in analysis["aggregate"]["milestones"].values()
            for product in row["median_cumulative_revenue_by_product"]
        }
    )
    lines.append("| Milestone | " + " | ".join(products) + " |")
    lines.append("|---|" + "---:|" * len(products))
    for name, row in analysis["aggregate"]["milestones"].items():
        values = [row["median_cumulative_revenue_by_product"].get(product, 0) for product in products]
        lines.append(f"| {name} | " + " | ".join(f"${value:,.0f}" for value in values) + " |")
    for appearance in analysis["representative_appearances"]:
        lines.extend(
            [
                "",
                f"## {appearance['team_name']} — episode {appearance['episode_id']} seat {appearance['player']}",
                "",
                f"Opponent: {appearance['opponent']}; seed: {appearance['seed']}.",
                "",
                "| Day/hour | Bank before → after | Successful economic events |",
                "|---|---:|---|",
            ]
        )
        for turn in appearance["economic_turns"]:
            lines.append(
                f"| {turn['day']}/{turn['hour']:02d} | ${turn['bank_before']:,.0f} → "
                f"${turn['bank_after']:,.0f} | {_event_text(turn['events'])} |"
            )
        lines.extend(["", "Milestone funding:", ""])
        for milestone in appearance["milestones"]:
            capital = milestone["capital_through_event"]
            lines.append(
                f"- **{milestone['milestone']}** at day {milestone['day']}, hour {milestone['hour']}: "
                f"bank ${milestone['bank_before_turn']:,.0f} → ${milestone['bank_after_turn']:,.0f}; "
                f"cumulative sales ${capital['total_revenue']:,.0f} {capital['revenue_by_product']}; "
                f"cumulative spending ${capital['total_spending']:,.0f}."
            )
    output.write_text("\n".join(lines) + "\n")


def analyze(corpus, json_output, markdown_output):
    manifest = json.loads((corpus / "manifest.json").read_text())
    selected = {row["team_name"] for row in manifest["players"]}
    all_appearances = []
    representative = []
    for path in sorted((corpus / "replays").glob("episode-*-replay.json")):
        replay = json.loads(path.read_text())
        episode_id = int(replay["info"]["EpisodeId"])
        for player, name in enumerate(replay["info"]["TeamNames"]):
            if name not in selected:
                continue
            appearance = _analyze_appearance(path, replay, player)
            all_appearances.append(appearance)
            if episode_id in REPRESENTATIVE_EPISODES:
                representative.append(appearance)
    analysis = {
        "schema_version": 1,
        "scope": "days 0-10 inclusive",
        "corpus_manifest": str((corpus / "manifest.json").relative_to(ROOT)),
        "representative_episode_ids": sorted(REPRESENTATIVE_EPISODES),
        "financial_reconstruction_mismatches": sum(
            row["financial_reconstruction_mismatches"] for row in all_appearances
        ),
        "aggregate": _aggregate(all_appearances),
        "representative_appearances": representative,
        "all_selected_appearances": [
            {
                key: row[key]
                for key in (
                    "episode_id", "seed", "player", "team_name", "opponent",
                    "financial_reconstruction_mismatches", "milestones",
                    "daily_checkpoints", "capital_through_day_10", "farm_after_day_10",
                )
            }
            for row in all_appearances
        ],
    }
    json_output.write_text(json.dumps(analysis, indent=2) + "\n")
    _write_markdown(markdown_output, analysis)
    return analysis


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    analysis = analyze(args.corpus, args.json, args.markdown)
    print(
        f"audited {len(analysis['all_selected_appearances'])} appearances; "
        f"rendered {len(analysis['representative_appearances'])}; "
        f"mismatches={analysis['financial_reconstruction_mismatches']}"
    )


if __name__ == "__main__":
    main()
