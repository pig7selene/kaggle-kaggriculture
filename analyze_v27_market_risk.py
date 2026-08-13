"""Interpretable opponent-SELL hazard calibration from public replays.

The model deliberately uses only public state at decision time.  It reports
empirical probabilities and Brier scores for 1/4/8/12-turn horizons under a
route-family-held-out split; it is not a black-box policy learner.
"""

from __future__ import annotations

from collections import defaultdict
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CORPUS = ROOT / "experiments/top_player_replays"
OUTPUT = ROOT / "experiments/v27_market_risk_analysis.json"
PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
HORIZONS = (1, 4, 8, 12)
VALIDATION_TEAMS = {"Victor @ Tufa Labs", "Abracadabra", "Valmorlee"}
ANIMAL_PRODUCT = {"GOOSE": "EGG", "COW": "MILK", "SHEEP": "WOOL"}


def _actions(replay, player):
    output = []
    for step in range(719):
        action = replay["steps"][step + 1][player].get("action") or {}
        output.append(list(action.get("market", [])))
    return output


def _visible_features(obs, player, product):
    farm = obs["farms"][player]
    ready = 0
    harvestable_tiles = 0
    for row in farm["tiles"]:
        for tile in row:
            if not isinstance(tile, dict) or tile.get("yield_units", 0) <= 0:
                continue
            item = tile.get("crop") if tile.get("kind") == "PLANT" else ANIMAL_PRODUCT.get(tile.get("animal"))
            if item == product:
                ready += int(tile.get("yield_units", 0))
                harvestable_tiles += 1
    near_shed = sum(tuple(position) in {(4, 4), (5, 4), (4, 5), (5, 5)} for position in [farm["farmer"], *farm.get("hands", [])])
    quote = float(obs["market"]["prices"].get(product, 1))
    initial = 10000.0
    inventory_pressure = max(-1.0, min(1.0, (initial - float(obs["market"]["inventory"].get(product, initial))) / 1000.0))
    return {
        "ready": ready,
        "harvestable_tiles": harvestable_tiles,
        "near_shed": near_shed,
        "quote": quote,
        "inventory_pressure": inventory_pressure,
        "day": int(obs.get("day", 0)),
        "hour": int(obs.get("hour", 0)),
    }


def _bucket(features):
    ready = "ready0" if features["ready"] == 0 else ("ready1_4" if features["ready"] <= 4 else "ready5p")
    shed = "shed0" if features["near_shed"] == 0 else ("shed1" if features["near_shed"] == 1 else "shed2p")
    phase = "early" if features["day"] < 10 else ("mid" if features["day"] < 24 else "late")
    return f"{ready}|{shed}|{phase}"


def _label(actions, step, product, horizon):
    quantity = 0
    first = None
    for future in range(step, min(719, step + horizon)):
        for order in actions[future]:
            if order and order[0] == "SELL" and order[1] == product:
                quantity += int(order[2])
                if first is None:
                    first = future - step + 1
    return quantity > 0, quantity, first


def _brier(rows, model, horizon):
    values = []
    for row in rows:
        key = (row["product"], row["bucket"], horizon)
        product_key = (row["product"], "ALL", horizon)
        probability = model.get(key, model.get(product_key, 0.0))
        values.append((probability - row["labels"][str(horizon)]["sold"]) ** 2)
    return sum(values) / max(1, len(values))


def main():
    manifest = json.loads((CORPUS / "manifest.json").read_text())
    known = {row["team_name"] for row in manifest["players"]}
    rows = []
    flow_examples = []
    seen = set()
    for path in sorted((CORPUS / "replays").glob("episode-*-replay.json")):
        replay = json.loads(path.read_text())
        for player, team in enumerate(replay["info"]["TeamNames"]):
            if team not in known:
                continue
            key = (int(replay["info"]["EpisodeId"]), player)
            if key in seen:
                continue
            seen.add(key)
            actions = _actions(replay, player)
            for step in range(719):
                obs = replay["steps"][step][0]["observation"]
                for product in PRODUCTS:
                    features = _visible_features(obs, player, product)
                    rows.append({
                        "split": "validation" if team in VALIDATION_TEAMS else "training",
                        "team": team, "episode": key[0], "step": step,
                        "product": product, "bucket": _bucket(features),
                        "features": features,
                        "labels": {
                            str(horizon): {
                                "sold": int(_label(actions, step, product, horizon)[0]),
                                "quantity": _label(actions, step, product, horizon)[1],
                            }
                            for horizon in HORIZONS
                        },
                    })
                if step > 0:
                    previous = replay["steps"][step - 1][0]["observation"]
                    for product in PRODUCTS:
                        observed = obs["market"]["inventory"][product] - previous["market"]["inventory"][product]
                        own_orders = actions[step - 1]
                        own_net = sum(
                            int(order[2]) * (1 if order[0] == "SELL" else -1)
                            for order in own_orders
                            if len(order) >= 3 and order[1] == product and order[0] in {"SELL", "BUY_PRODUCT"}
                        )
                        # Town consumption is deterministic from the previous
                        # state; exact product multipliers are intentionally
                        # left as an interval because shop names may duplicate.
                        residual = observed - own_net
                        if residual:
                            flow_examples.append({"episode": key[0], "team": team, "step": step, "product": product, "public_residual": residual})

    training = [row for row in rows if row["split"] == "training"]
    validation = [row for row in rows if row["split"] == "validation"]
    aggregates = defaultdict(lambda: {"count": 0, "positives": 0, "quantity": 0})
    for row in training:
        for horizon in HORIZONS:
            label = row["labels"][str(horizon)]
            for bucket in (row["bucket"], "ALL"):
                value = aggregates[(row["product"], bucket, horizon)]
                value["count"] += 1
                value["positives"] += label["sold"]
                value["quantity"] += label["quantity"]
    model = {}
    table = []
    for key, value in sorted(aggregates.items()):
        product, bucket, horizon = key
        # Beta(1,9) shrinkage reflects the sparse base event rate.
        probability = (value["positives"] + 1) / (value["count"] + 10)
        model[key] = probability
        table.append({
            "product": product, "bucket": bucket, "horizon": horizon,
            "observations": value["count"], "positive_rate": value["positives"] / max(1, value["count"]),
            "smoothed_probability": probability,
            "mean_quantity_unconditional": value["quantity"] / max(1, value["count"]),
            "mean_quantity_if_positive": value["quantity"] / max(1, value["positives"]),
        })
    calibration = []
    for horizon in HORIZONS:
        baseline = sum(row["labels"][str(horizon)]["sold"] for row in training) / max(1, len(training))
        baseline_brier = sum((baseline - row["labels"][str(horizon)]["sold"]) ** 2 for row in validation) / max(1, len(validation))
        calibration.append({
            "horizon": horizon, "training_base_rate": baseline,
            "validation_brier": _brier(validation, model, horizon),
            "validation_constant_base_brier": baseline_brier,
            "validation_observations": len(validation),
        })
    payload = {
        "schema_version": 1,
        "method": "public-state categorical hazard table with Beta shrinkage",
        "training_teams": sorted(known - VALIDATION_TEAMS),
        "validation_teams": sorted(VALIDATION_TEAMS),
        "split_rule": "entire route family held out; no random episode split",
        "features": ["visible ready quantity", "visible harvestable tiles", "workers at shed", "quote", "market inventory pressure", "day/hour"],
        "inference_limit": "Market inventory residual reveals net external flow, but WHEAT/FERTILIZER buy-vs-sell and town consumption make attribution interval-valued.",
        "training_rows": len(training), "validation_rows": len(validation),
        "calibration": calibration,
        "hazard_table": table,
        "nonzero_flow_examples": flow_examples[:500],
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(OUTPUT)
    for row in calibration:
        print(row)


if __name__ == "__main__":
    main()
