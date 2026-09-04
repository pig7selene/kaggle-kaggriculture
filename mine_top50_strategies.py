"""Mine structural strategy knowledge from the current Top-50 corpus.

This is deliberately descriptive.  It consumes only public replay observations,
uses observed bank deltas to reconcile minor server/local price-rounding drift,
and never exposes leaderboard rank to deployable policy code.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import statistics

from analyze_top_player_replays import _new_ledger, _transition_ledger


ROOT = Path(__file__).resolve().parent
EXP = ROOT / "experiments"
MANIFEST = EXP / "top50_corpus_manifest.json"
CACHE = EXP / "top50_analysis_cache.json.partial"
STABILITY = EXP / "top50_route_stability.json"
V2_BANK = EXP / "v2_route_executor.json"
BASELINE_ROUTE_ID = "super_raw_55463387"
PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
CROPS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")
ANIMALS = ("GOOSE", "COW", "SHEEP")
CHECKPOINT_DAYS = (0, 4, 6, 8, 10, 12, 15, 20, 25, 29)


def _write(name, value):
    path = EXP / name
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    return path


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _sha(value):
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _percentile(values, fraction):
    values = sorted(values)
    if not values:
        return None
    point = fraction * (len(values) - 1)
    lo = int(point)
    weight = point - lo
    return values[lo] * (1 - weight) + values[min(lo + 1, len(values) - 1)] * weight


def _plain_counter(value):
    return {key: value[key] for key in sorted(value) if value[key]}


def _inventory(obs):
    private = obs["private"]
    values = Counter(private.get("shed", {}))
    for carried in private.get("inventories", []):
        values.update(carried)
    return values


def _tile_counts(farm):
    crops, animals, structures, cohorts = Counter(), Counter(), Counter(), Counter()
    weeds = productive = 0
    for row in farm["tiles"]:
        for tile in row:
            if not isinstance(tile, dict):
                continue
            if tile.get("kind") == "PLANT":
                crop = tile.get("crop")
                crops[crop] += 1
                cohorts[f"{crop}:{tile.get('planted_day', -1)}"] += 1
                productive += 1
            elif tile.get("kind") in {"COOP", "PASTURE"}:
                structures[tile["kind"]] += 1
                if tile.get("animal"):
                    animals[tile["animal"]] += 1
                    productive += 1
            elif tile.get("kind") == "WEED":
                weeds += 1
    return {
        "crops": _plain_counter(crops), "animals": _plain_counter(animals),
        "structures": _plain_counter(structures), "cohorts": _plain_counter(cohorts),
        "productive": productive, "weeds": weeds,
    }


def _snapshot(replay, player, step):
    obs = replay["steps"][min(step, 719)][player]["observation"]
    farm = obs["farms"][player]
    counts = _tile_counts(farm)
    return {
        "step": min(step, 719), "day": int(obs.get("day", step // 24)),
        "bank": float(farm["money"]), "quadrants": len(farm["unlocked_quadrants"]),
        "hands": len(farm.get("hands", [])), **counts,
    }


def _empty_day(day):
    return {
        "day": day, "bank_start": None, "bank_end": None,
        "sale_quantity": Counter(), "sale_revenue": Counter(), "sale_prices": defaultdict(list),
        "seed_quantity": Counter(), "seed_spend": Counter(),
        "product_quantity": Counter(), "product_spend": Counter(),
        "animal_quantity": Counter(), "animal_spend": Counter(),
        "land_count": 0, "land_spend": 0, "hire_count": 0, "labor_spend": 0,
        "harvest_quantity": Counter(), "plant_quantity": Counter(),
        "structures_built": Counter(), "animals_placed": Counter(),
        "feed_actions": 0, "care_actions": 0, "fertilizer_collected": 0,
        "server_rounding_reconciliation": 0.0, "unallocated_reconciliation": 0.0,
    }


def _economic_timeline(replay, player):
    """Exact bank trajectory with transparent server/local price reconciliation."""
    steps = replay["steps"]
    daily = [_empty_day(day) for day in range(30)]
    reconciliation_events = []
    for index in range(1, len(steps)):
        previous = steps[index - 1]
        current = steps[index]
        obs = previous[player]["observation"]
        day = min(29, int(obs.get("day", (index - 1) // 24)))
        row = daily[day]
        before = float(obs["farms"][player]["money"])
        after = float(current[player]["observation"]["farms"][player]["money"])
        row["bank_start"] = before if row["bank_start"] is None else row["bank_start"]
        row["bank_end"] = after
        ledgers, errors = _transition_ledger(previous, current, replay.get("configuration", {}))
        ledger = ledgers[player]
        spend = (
            sum(ledger["seed_spend"].values()) + sum(ledger["product_spend"].values())
            + sum(ledger["animal_spend"].values()) + ledger["land_spend"] + ledger["labor_spend"]
        )
        predicted_revenue = sum(ledger["sale_revenue"].values())
        exact_cash_revenue = after - before + spend
        residual = exact_cash_revenue - predicted_revenue
        adjusted = Counter(ledger["sale_revenue"])
        if residual and adjusted:
            total = sum(adjusted.values())
            products = sorted(adjusted)
            remaining = residual
            for item in products[:-1]:
                share = residual * adjusted[item] / total if total else 0
                adjusted[item] += share
                remaining -= share
            adjusted[products[-1]] += remaining
        elif residual:
            row["unallocated_reconciliation"] += residual
        if abs(residual) > 1e-9:
            reconciliation_events.append({
                "step": index - 1, "day": day, "player": player,
                "predicted_sale_revenue": predicted_revenue,
                "observed_cash_revenue_after_known_spend": exact_cash_revenue,
                "delta": residual, "sale_products": sorted(adjusted),
                "bank_mismatch_reported": bool(errors),
            })
            row["server_rounding_reconciliation"] += residual
        for key in ("sale_quantity", "seed_quantity", "seed_spend", "product_quantity", "product_spend", "animal_quantity", "animal_spend", "harvest_quantity", "plant_quantity", "structures_built", "animals_placed"):
            row[key].update(ledger[key])
        row["sale_revenue"].update(adjusted)
        for item, values in ledger["sale_prices"].items():
            row["sale_prices"][item].extend(values)
        for key in ("land_count", "land_spend", "hire_count", "labor_spend", "feed_actions", "care_actions", "fertilizer_collected"):
            row[key] += ledger[key]
    # State snapshots give trustworthy daily bank boundaries even when the last
    # transition of one day lands in the first state of the next day.
    for day, row in enumerate(daily):
        states = [state for state in steps if int(state[player]["observation"].get("day", 0)) == day]
        if states:
            row["observed_state_bank_start"] = float(states[0][player]["observation"]["farms"][player]["money"])
            row["observed_state_bank_end"] = float(states[-1][player]["observation"]["farms"][player]["money"])
        row["bank_start"] = row["bank_start"] if row["bank_start"] is not None else row.get("observed_state_bank_start")
        row["bank_end"] = row["bank_end"] if row["bank_end"] is not None else row.get("observed_state_bank_end")
        for key in ("sale_quantity", "sale_revenue", "seed_quantity", "seed_spend", "product_quantity", "product_spend", "animal_quantity", "animal_spend", "harvest_quantity", "plant_quantity", "structures_built", "animals_placed"):
            row[key] = _plain_counter(row[key])
        row["sale_average_prices"] = {
            item: statistics.fmean(values) for item, values in sorted(row["sale_prices"].items()) if values
        }
        del row["sale_prices"]
        row["total_sale_revenue"] = sum(row["sale_revenue"].values())
        row["total_spend"] = sum(row["seed_spend"].values()) + sum(row["product_spend"].values()) + sum(row["animal_spend"].values()) + row["land_spend"] + row["labor_spend"]
    return daily, reconciliation_events


def _segments(snapshots):
    output = []
    for snap in snapshots:
        crops = snap["crops"]
        label = "NONE" if not crops else "+".join(sorted(k for k, v in crops.items() if v == max(crops.values())))
        if output and output[-1]["dominant_crop"] == label:
            output[-1]["end_day"] = snap["day"]
        else:
            output.append({"start_day": snap["day"], "end_day": snap["day"], "dominant_crop": label})
    return output


def _weighted_day(timeline, field, product):
    amount = sum(row[field].get(product, 0) for row in timeline)
    return None if not amount else sum(row["day"] * row[field].get(product, 0) for row in timeline) / amount


def _feature_row(appearance, replay, timeline):
    player = appearance["player"]
    checkpoints = [_snapshot(replay, player, day * 24) for day in CHECKPOINT_DAYS]
    daily_snapshots = [_snapshot(replay, player, day * 24) for day in range(30)]
    sale_quantity, sale_revenue, purchases, spend = Counter(), Counter(), Counter(), Counter()
    harvests, plantings = Counter(), Counter()
    land_steps, buy_animal_steps, hire_steps = [], [], []
    final_plant_step = None
    for step, action in enumerate(appearance["actions"]):
        for order in action["market"]:
            if not order:
                continue
            op = order[0]
            quantity = int(order[2]) if len(order) > 2 else 1
            if op == "BUY_LAND": land_steps.append(step)
            elif op == "BUY_ANIMAL": buy_animal_steps.append({"step": step, "animal": order[1], "quantity": quantity})
            elif op == "HIRE": hire_steps.append(step)
        obs = replay["steps"][step][player]["observation"]
        farm = obs["farms"][player]
        positions = [farm["farmer"], *farm.get("hands", [])]
        for pos, request in zip(positions, [action["farmer"], *action["hands"]]):
            if not request:
                continue
            x, y = pos
            tile = farm["tiles"][y][x]
            if request[0] == "PLANT":
                plantings[request[1]] += 1
                final_plant_step = step
            elif request[0] == "HARVEST" and isinstance(tile, dict):
                if tile.get("kind") == "PLANT": harvests[tile.get("crop")] += 1
                elif tile.get("animal"):
                    harvests[{"COW": "MILK", "SHEEP": "WOOL", "GOOSE": "EGG"}.get(tile["animal"], tile["animal"])] += 1
    for row in timeline:
        sale_quantity.update(row["sale_quantity"]); sale_revenue.update(row["sale_revenue"])
        harvests.update(row["harvest_quantity"]); plantings.update(row["plant_quantity"])
        for item, value in row["seed_quantity"].items(): purchases[f"SEED_{item}"] += value
        for item, value in row["animal_quantity"].items(): purchases[f"ANIMAL_{item}"] += value
        for item, value in row["product_quantity"].items(): purchases[f"PRODUCT_{item}"] += value
        for item, value in row["seed_spend"].items(): spend[f"SEED_{item}"] += value
        for item, value in row["animal_spend"].items(): spend[f"ANIMAL_{item}"] += value
        for item, value in row["product_spend"].items(): spend[f"PRODUCT_{item}"] += value
        spend["LAND"] += row["land_spend"]; spend["LABOR"] += row["labor_spend"]
    final_obs = replay["steps"][-1][player]["observation"]
    terminal = _inventory(final_obs)
    anchors = appearance["anchors"]
    peak = {kind: max((snap.get("animals", {}).get(kind, 0) for snap in anchors), default=0) for kind in ANIMALS}
    peak_crops = {kind: max((snap.get("crops", {}).get(kind, 0) for snap in anchors), default=0) for kind in CROPS}
    max_cohort = max((max(snap.get("cohorts", {}).values(), default=0) for snap in anchors), default=0)
    peak_hands = max((snap.get("hand_count", 0) for snap in anchors), default=0)
    max_productive = max((snap.get("productive", 0) for snap in anchors), default=0)
    vector = []
    for snap in checkpoints:
        vector.extend([
            snap["quadrants"] / 4, snap["hands"] / 15, snap["productive"] / 100,
            *(snap["animals"].get(kind, 0) / 12 for kind in ANIMALS),
            *(snap["crops"].get(kind, 0) / 75 for kind in CROPS),
        ])
    total_revenue = sum(sale_revenue.values()) or 1
    vector.extend([sale_revenue.get(item, 0) / total_revenue for item in PRODUCTS])
    vector.extend([len(land_steps) / 3, max_cohort / 50, (final_plant_step or 0) / 719])
    signature = {
        "land_days": [round(step / 24, 1) for step in land_steps],
        "peak_animals": peak, "peak_crops": peak_crops,
        "peak_hands": peak_hands,
        "max_cohort": max_cohort, "crop_phases": _segments(daily_snapshots),
        "revenue_mix": {item: sale_revenue.get(item, 0) / total_revenue for item in PRODUCTS},
    }
    economic_hash_payload = {
        "land": [round(step / 24, 1) for step in land_steps], "animals": peak,
        "crop_phases": signature["crop_phases"], "peak_hands": signature["peak_hands"],
        "checkpoint_composition": [{"day": s["day"], "crops": s["crops"], "animals": s["animals"], "quadrants": s["quadrants"]} for s in checkpoints],
    }
    return {
        "submission_id": appearance["submission_id"], "team_name": appearance["team_name"],
        "rank": appearance["rank"], "classification": None,
        "representative_episode": appearance["episode_id"], "representative_player": player,
        "average_observed_money": appearance["final_money"],
        "land_purchase_steps": land_steps, "animal_purchase_events": buy_animal_steps,
        "peak_animals": peak, "peak_crops": peak_crops,
        "peak_hands": signature["peak_hands"], "max_productive": max_productive,
        "max_crop_cohort": max_cohort, "crop_phases": signature["crop_phases"],
        "plantings": _plain_counter(plantings), "harvests": _plain_counter(harvests),
        "sale_quantity": _plain_counter(sale_quantity), "sale_revenue": _plain_counter(sale_revenue),
        "total_sale_revenue": sum(sale_revenue.values()), "purchases": _plain_counter(purchases), "spending": _plain_counter(spend),
        "average_realized_prices": {item: sale_revenue[item] / sale_quantity[item] for item in sale_quantity if sale_quantity[item]},
        "harvest_weighted_days": {item: _weighted_day(timeline, "harvest_quantity", item) for item in PRODUCTS},
        "sale_weighted_days": {item: _weighted_day(timeline, "sale_quantity", item) for item in PRODUCTS},
        "final_plant_step": final_plant_step, "terminal_inventory": _plain_counter(terminal),
        "checkpoints": checkpoints, "daily_timeline": timeline,
        "economic_hash": _sha(economic_hash_payload), "vector": vector, "signature": signature,
    }


def _distance(left, right):
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right)) / len(left))


def _cluster(rows):
    names = [str(row["submission_id"]) for row in rows]
    by_name = {str(row["submission_id"]): row for row in rows}
    nearest = []
    for name in names:
        distances = sorted(_distance(by_name[name]["vector"], by_name[other]["vector"]) for other in names if other != name)
        nearest.append(distances[0])
    # Data-derived but conservative: preserve meaningful variants inside the
    # broad Victor family while merging cosmetic route copies.
    threshold = max(0.045, min(0.105, statistics.median(nearest) * 2.0))
    parent = {name: name for name in names}
    def find(value):
        if parent[value] != value: parent[value] = find(parent[value])
        return parent[value]
    def union(a, b):
        a, b = find(a), find(b)
        if a != b: parent[b] = a
    pairwise = []
    for index, left in enumerate(names):
        for right in names[index + 1:]:
            distance = _distance(by_name[left]["vector"], by_name[right]["vector"])
            pairwise.append({"left": int(left), "right": int(right), "distance": distance})
            if distance <= threshold: union(left, right)
    groups = defaultdict(list)
    for name in names: groups[find(name)].append(by_name[name])
    return sorted(groups.values(), key=lambda group: (min(row["rank"] for row in group), -len(group))), threshold, pairwise


def _family_name(group):
    med = min(group, key=lambda left: sum(_distance(left["vector"], right["vector"]) for right in group))
    animals = med["peak_animals"]
    crops = med["peak_crops"]
    animal = max(animals, key=animals.get) if any(animals.values()) else "low_livestock"
    crop = max(crops, key=crops.get) if any(crops.values()) else "low_crop"
    land = len(med["land_purchase_steps"]) + 1
    return f"{animal.lower()}_{crop.lower()}_{land}q"


def _adaptive_analysis(grouped, classifications):
    rows = []
    for submission, appearances in grouped.items():
        phases = {"opening": (0, 160), "expansion": (160, 336), "midgame": (336, 504), "late": (504, 648), "liquidation": (648, 719)}
        phase_agreement = {}
        divergence_events = []
        for name, (lo, hi) in phases.items():
            agreements = []
            for step in range(lo, hi):
                values = Counter(_canonical(row["actions"][step]) for row in appearances)
                agreements.append(values.most_common(1)[0][1] / len(appearances))
                if len(values) > 1 and len(appearances) >= 3:
                    # Explain the largest action split using only contemporaneous observations.
                    majority = values.most_common(1)[0][0]
                    candidates = []
                    for feature, getter in (
                        ("own_bank", lambda a: a["anchors"][step]["money"]),
                        ("milk_price", lambda a: a["anchors"][step]["market_prices"].get("MILK", 0)),
                        ("wool_price", lambda a: a["anchors"][step]["market_prices"].get("WOOL", 0)),
                        ("strawberry_price", lambda a: a["anchors"][step]["market_prices"].get("STRAWBERRY", 0)),
                        ("shops", lambda a: len(a["anchors"][step].get("shops", []))),
                        ("own_productive", lambda a: a["anchors"][step].get("productive", 0)),
                        ("hands", lambda a: a["anchors"][step].get("hand_count", 0)),
                    ):
                        one = [getter(a) for a in appearances if _canonical(a["actions"][step]) == majority]
                        other = [getter(a) for a in appearances if _canonical(a["actions"][step]) != majority]
                        if one and other:
                            scale = statistics.pstdev(one + other) or 1
                            candidates.append((abs(statistics.fmean(one) - statistics.fmean(other)) / scale, feature, statistics.fmean(one), statistics.fmean(other)))
                    if candidates:
                        score, feature, major_value, other_value = max(candidates)
                        if score >= 0.75:
                            divergence_events.append({"step": step, "phase": name, "observable_feature": feature, "standardized_separation": score, "majority_mean": major_value, "alternate_mean": other_value, "action_variants": len(values)})
            phase_agreement[name] = statistics.fmean(agreements)
        rows.append({
            "submission_id": int(submission), "team_name": appearances[0]["team_name"], "rank": appearances[0]["rank"],
            "appearance_count": len(appearances), "classification": classifications[int(submission)],
            "phase_action_agreement": phase_agreement,
            "first_action_divergence_step": next((step for step in range(719) if len({_canonical(a["actions"][step]) for a in appearances}) > 1), None),
            "observable_divergence_hypotheses": sorted(divergence_events, key=lambda x: x["standardized_separation"], reverse=True)[:25],
        })
    return sorted(rows, key=lambda row: row["rank"])


def main():
    manifest = json.loads(MANIFEST.read_text())
    cache = json.loads(CACHE.read_text())
    stability = json.loads(STABILITY.read_text())
    classifications = {row["submission_id"]: row["classification"] for row in stability["submissions"]}
    grouped = defaultdict(list)
    for appearance in cache["appearances"]:
        grouped[str(appearance["submission_id"])].append(appearance)
    features, all_reconciliation = [], []
    for index, (submission, appearances) in enumerate(sorted(grouped.items(), key=lambda pair: pair[1][0]["rank"]), 1):
        stability_row = next(row for row in stability["submissions"] if row["submission_id"] == int(submission))
        representative = next((row for row in appearances if row["episode_id"] == stability_row["representative_episode"]), appearances[0])
        replay = json.loads((ROOT / representative["replay_path"]).read_text())
        timeline, reconciliation = _economic_timeline(replay, representative["player"])
        feature = _feature_row(representative, replay, timeline)
        feature["classification"] = classifications[int(submission)]
        feature["appearances"] = len(appearances)
        feature["average_observed_money"] = statistics.fmean(row["final_money"] for row in appearances)
        feature["median_observed_money"] = statistics.median(row["final_money"] for row in appearances)
        feature["money_p10"] = _percentile([row["final_money"] for row in appearances], .10)
        features.append(feature)
        all_reconciliation.extend({"submission_id": int(submission), "episode_id": representative["episode_id"], **row} for row in reconciliation)
        if index % 10 == 0: print(f"economic features {index}/{len(grouped)}", flush=True)

    families, threshold, pairwise = _cluster(features)
    family_rows = []
    family_by_submission = {}
    for index, group in enumerate(families, 1):
        family_id = f"top50_family_{index:02d}"
        medoid = min(group, key=lambda left: sum(_distance(left["vector"], right["vector"]) for right in group))
        for row in group: family_by_submission[row["submission_id"]] = family_id
        family_rows.append({
            "family_id": family_id, "economic_identity": _family_name(group), "size": len(group),
            "submission_ids": [row["submission_id"] for row in group], "teams": [row["team_name"] for row in group],
            "ranks": [row["rank"] for row in group], "medoid_submission": medoid["submission_id"],
            "classification_counts": dict(Counter(row["classification"] for row in group)),
            "typical_first_land_step": statistics.median(row["land_purchase_steps"][0] for row in group if row["land_purchase_steps"]),
            "typical_second_land_step": statistics.median(row["land_purchase_steps"][1] for row in group if len(row["land_purchase_steps"]) > 1),
            "typical_peak_animals": {kind: statistics.median(row["peak_animals"][kind] for row in group) for kind in ANIMALS},
            "typical_peak_hands": statistics.median(row["peak_hands"] for row in group),
            "typical_peak_crops": {kind: statistics.median(row["peak_crops"][kind] for row in group) for kind in CROPS},
            "average_money": statistics.fmean(row["average_observed_money"] for row in group),
        })

    # Multi-level deduplication.  Route equivalence excludes SELL timing while
    # economic equivalence uses the complete state/composition signature.
    exact = Counter(row["full_hash"] for row in cache["appearances"])
    route = Counter((row["field_hash"], row["non_sell_hash"]) for row in cache["appearances"])
    economic = Counter(row["economic_hash"] for row in features)
    dedup = {
        "schema_version": 1, "manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
        "raw_selected_elite_appearances": manifest["corpus_summary"]["selected_elite_appearances"],
        "action_deduplicated_appearances": len(cache["appearances"]),
        "exact_action_implementations": len(exact), "route_implementations": len(route),
        "economic_implementations": len(economic), "strategy_families": len(family_rows),
        "exact_duplicate_groups": sorted(exact.values(), reverse=True),
        "route_duplicate_groups": sorted(route.values(), reverse=True),
        "economic_duplicate_groups": sorted(economic.values(), reverse=True),
        "definitions": {
            "exact": "all 719 normalized actions identical",
            "route": "all field actions and all non-SELL market actions identical",
            "economic": "same land, livestock, crop-phase, labor, and checkpoint-composition signature",
            "family": "connected components of normalized complete economic-trajectory distance",
        },
    }

    # Equal-family consensus avoids allowing the 46-agent copied family to
    # swamp independent evidence.
    medoids = [next(row for row in features if row["submission_id"] == family["medoid_submission"]) for family in family_rows]
    def pattern(name, selector, value_getter=None):
        used = [row for row in medoids if selector(row)]
        values = [value_getter(row) for row in used] if value_getter else []
        return {"pattern": name, "families_using": len(used), "family_count": len(medoids), "frequency": len(used) / len(medoids), "typical_range": [min(values), max(values)] if values else None, "family_ids": [family_by_submission[row["submission_id"]] for row in used]}
    patterns = [
        pattern("three_or_more_quadrants", lambda r: len(r["land_purchase_steps"]) >= 2, lambda r: r["land_purchase_steps"][1] / 24),
        pattern("first_land_by_day7", lambda r: r["land_purchase_steps"] and r["land_purchase_steps"][0] <= 168, lambda r: r["land_purchase_steps"][0] / 24),
        pattern("second_land_by_day11_5", lambda r: len(r["land_purchase_steps"]) > 1 and r["land_purchase_steps"][1] <= 276, lambda r: r["land_purchase_steps"][1] / 24),
        pattern("eight_or_more_cows", lambda r: r["peak_animals"]["COW"] >= 8, lambda r: r["peak_animals"]["COW"]),
        pattern("mixed_cow_sheep", lambda r: r["peak_animals"]["COW"] >= 4 and r["peak_animals"]["SHEEP"] >= 2),
        pattern("twelve_or_more_hands", lambda r: r["peak_hands"] >= 12, lambda r: r["peak_hands"]),
        pattern("melon_and_strawberry_waves", lambda r: r["peak_crops"]["MELON"] >= 5 and r["peak_crops"]["STRAWBERRY"] >= 5),
        pattern("terminal_liquidation_after_step700", lambda r: any(sum(d["sale_quantity"].values()) for d in r["daily_timeline"][29:]) and max((d["day"] for d in r["daily_timeline"] if sum(d["sale_quantity"].values())), default=0) == 29),
    ]

    # Rank contrast after economic deduplication.
    tiers = {}
    for label, lo, hi in (("top_1_10", 1, 10), ("top_11_25", 11, 25), ("top_26_50", 26, 50)):
        rows = [row for row in features if lo <= row["rank"] <= hi]
        unique = {row["economic_hash"]: row for row in rows}.values()
        tiers[label] = {
            "unique_economic_strategies": len(unique),
            "first_land_step_median": statistics.median(row["land_purchase_steps"][0] for row in unique if row["land_purchase_steps"]),
            "second_land_step_median": statistics.median(row["land_purchase_steps"][1] for row in unique if len(row["land_purchase_steps"]) > 1),
            "peak_cows_median": statistics.median(row["peak_animals"]["COW"] for row in unique),
            "peak_sheep_median": statistics.median(row["peak_animals"]["SHEEP"] for row in unique),
            "peak_hands_median": statistics.median(row["peak_hands"] for row in unique),
            "melon_peak_median": statistics.median(row["peak_crops"]["MELON"] for row in unique),
            "strawberry_peak_median": statistics.median(row["peak_crops"]["STRAWBERRY"] for row in unique),
            "average_money": statistics.fmean(row["average_observed_money"] for row in unique),
        }

    baseline_route = next(row for row in json.loads(V2_BANK.read_text())["routes"] if row["route_id"] == BASELINE_ROUTE_ID)
    baseline_land = [event["step"] for event in baseline_route.get("critical_transactions", []) if event.get("type") == "BUY_LAND"]
    # Use expected-state anchors for a leakage-free structural comparison.
    baseline_anchors = baseline_route["expected_state"]
    baseline_actions = baseline_route.get("actions", baseline_route.get("consensus_actions", []))
    baseline = {
        "source": "agents/super_replay_v2/super_backbone_v2.py", "route_id": BASELINE_ROUTE_ID,
        "land_purchase_steps": [step for step, action in enumerate(baseline_actions) for order in action["market"] if order and order[0] == "BUY_LAND"],
        "peak_animals": {kind: max(anchor.get("animals", {}).get(kind, 0) for anchor in baseline_anchors) for kind in ANIMALS},
        "peak_hands": max(anchor.get("hand_count", 0) for anchor in baseline_anchors),
        "peak_crops": {kind: max(anchor.get("crops", {}).get(kind, 0) for anchor in baseline_anchors) for kind in CROPS},
        "max_productive": max(sum(anchor.get("crops", {}).values()) + sum(anchor.get("animals", {}).values()) for anchor in baseline_anchors),
    }
    differences = []
    for family, medoid in zip(family_rows, medoids):
        differences.append({
            "family_id": family["family_id"], "family_identity": family["economic_identity"],
            "rank_range": [min(family["ranks"]), max(family["ranks"])],
            "differences": {
                "first_land_step": [baseline["land_purchase_steps"][0] if baseline["land_purchase_steps"] else None, medoid["land_purchase_steps"][0] if medoid["land_purchase_steps"] else None],
                "second_land_step": [baseline["land_purchase_steps"][1] if len(baseline["land_purchase_steps"]) > 1 else None, medoid["land_purchase_steps"][1] if len(medoid["land_purchase_steps"]) > 1 else None],
                "peak_animals": {kind: [baseline["peak_animals"][kind], medoid["peak_animals"][kind]] for kind in ANIMALS},
                "peak_hands": [baseline["peak_hands"], medoid["peak_hands"]],
                "peak_crops": {kind: [baseline["peak_crops"][kind], medoid["peak_crops"][kind]] for kind in CROPS},
                "max_productive": [baseline["max_productive"], medoid["max_productive"]],
            },
            "classification": "structural economic difference",
        })

    adaptive = _adaptive_analysis(grouped, classifications)
    adaptive_counts = Counter(row["classification"] for row in adaptive)
    distillation = []
    for row in sorted(patterns, key=lambda x: x["frequency"], reverse=True):
        distillation.append({
            "behavior": row["pattern"], "source_strategy_families": row["family_ids"],
            "frequency": row["frequency"], "estimated_causal_value": "unvalidated hypothesis",
            "conditions_where_useful": "requires paired same-seed testing",
            "conditions_where_harmful": "capital/route incompatibility or shared-market cannibalization",
            "executor_difficulty": "low" if "land" not in row["pattern"] else "medium",
            "safety_risk": "low" if "livestock" not in row["pattern"] and "cows" not in row["pattern"] else "medium",
            "compatibility_with_current_best": "unknown until counterfactual screen",
        })

    _write("top50_deduplication.json", dedup)
    _write("top50_strategy_families.json", {
        "schema_version": 1, "method": "economic-trajectory connected components; threshold derived from nearest-neighbor distances",
        "distance_threshold": threshold, "families": family_rows, "pairwise": pairwise,
        "submission_features": features, "server_rounding_reconciliation": {
            "events": len(all_reconciliation), "absolute_delta": sum(abs(row["delta"]) for row in all_reconciliation),
            "signed_delta": sum(row["delta"] for row in all_reconciliation), "details": all_reconciliation,
            "policy": "observed bank delta is authoritative; residual allocated proportionally only across products sold in the same transition",
        },
    })
    _write("top50_consensus_patterns.json", {"schema_version": 1, "equal_weight_per_unique_family": True, "patterns": patterns, "rank_contrast_after_economic_dedup": tiers})
    _write("top50_adaptive_behavior_analysis.json", {"schema_version": 1, "classification_counts": dict(adaptive_counts), "submissions": adaptive, "feature_policy": "only current/past observable state; no seed, replay id, rank, future shop/price/action, or result features"})
    _write("top50_structural_differences.json", {"schema_version": 1, "actual_baseline": baseline, "family_differences": differences})
    _write("top50_strategy_distillation.json", {"schema_version": 1, "status": "observational hypotheses; causal values filled after counterfactuals", "behaviors": distillation})
    print(f"submissions={len(features)} families={len(family_rows)} fixed={adaptive_counts['A_highly_fixed'] + adaptive_counts['B_fixed_bounded']} adaptive={adaptive_counts['D_state_dependent']} reconciliation_events={len(all_reconciliation)}")


if __name__ == "__main__":
    main()
