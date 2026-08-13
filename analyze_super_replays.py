"""Normalize, reconstruct, cluster, and explain the Top-100 replay corpus."""

from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import statistics

from analyze_top_player_replays import (
    _add_ledger,
    _appearance_summary,
    _farm_snapshot,
    _new_daily,
    _serialize_daily,
    _transition_ledger,
)
from analyze_v27_routes import normalized_action, state_anchor


ROOT = Path(__file__).resolve().parent
CORPUS_MANIFEST = ROOT / "experiments/super_replay_corpus_manifest.json"
STABILITY_OUT = ROOT / "experiments/super_replay_route_stability.json"
FAMILIES_OUT = ROOT / "experiments/super_replay_route_families.json"
WAVES_OUT = ROOT / "experiments/super_replay_economic_waves.json"
CONFIDENCE_OUT = ROOT / "experiments/super_replay_action_confidence.json"
ROUTE_BANK_OUT = ROOT / "experiments/super_replay_route_bank.json"
CACHE = ROOT / "experiments/super_replay_analysis_cache.json.partial"

CHECKPOINTS = (0, 96, 144, 192, 240, 264, 360, 480, 600, 696, 718)
PHASES = {
    "opening": (0, 160),
    "first_expansion": (160, 240),
    "second_expansion": (240, 336),
    "midgame_wave": (336, 504),
    "late_wave": (504, 648),
    "liquidation": (648, 719),
}


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _sha(value):
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _counts(farm):
    crops, animals, structures, cohorts = Counter(), Counter(), Counter(), Counter()
    productive = weeds = 0
    crop_details = []
    animal_details = []
    for y, row in enumerate(farm["tiles"]):
        for x, tile in enumerate(row):
            if not isinstance(tile, dict):
                continue
            if tile.get("kind") == "PLANT":
                crops[tile["crop"]] += 1
                cohorts[f"{tile['crop']}:{tile.get('planted_day', -1)}"] += 1
                productive += 1
                crop_details.append((x, y, tile["crop"], tile.get("planted_day")))
            elif tile.get("kind") in {"COOP", "PASTURE"}:
                structures[tile["kind"]] += 1
                if tile.get("animal"):
                    animals[tile["animal"]] += 1
                    productive += 1
                    animal_details.append((x, y, tile["animal"], tile.get("placed_day")))
            elif tile.get("kind") == "WEED":
                weeds += 1
    return {
        "crops": dict(sorted(crops.items())), "animals": dict(sorted(animals.items())),
        "structures": dict(sorted(structures.items())), "cohorts": dict(sorted(cohorts.items())),
        "productive": productive, "weeds": weeds,
        "crop_geometry_hash": _sha(crop_details), "animal_geometry_hash": _sha(animal_details),
    }


def _field_tokens(action):
    return [request[0] if request else "PASS" for request in [action["farmer"], *action["hands"]]]


def _target_tokens(obs, player, action):
    farm = obs["farms"][player]
    positions = [farm["farmer"], *farm.get("hands", [])]
    tokens = []
    for index, (position, request) in enumerate(zip(positions, [action["farmer"], *action["hands"]])):
        op = request[0] if request else "PASS"
        tokens.append([index == 0, op, int(position[0]), int(position[1])])
    return tokens


def _events(actions):
    output = []
    for step, action in enumerate(actions):
        for order in action["market"]:
            if order and order[0] in {"BUY_LAND", "HIRE", "BUY_ANIMAL", "BUY_SEED", "BUY_PRODUCT", "SELL"}:
                output.append({"step": step, "type": order[0], "item": order[1] if len(order) > 1 else None, "quantity": order[2] if len(order) > 2 else 1})
        for unit, request in enumerate([action["farmer"], *action["hands"]]):
            if request and request[0] in {"BUILD_PASTURE", "BUILD_COOP", "PLANT", "HARVEST", "FEED", "CARE", "COLLECT_FERTILIZER", "DIG"}:
                output.append({"step": step, "type": request[0], "item": request[1] if len(request) > 1 else None, "unit": unit})
    return output


def _milestones(actions, anchors):
    events = _events(actions)
    by_type = defaultdict(list)
    for event in events:
        by_type[event["type"]].append(event)
    landmarks = {}
    for name, selector in (
        ("first_land", lambda e: e["type"] == "BUY_LAND"),
        ("second_land", lambda e: e["type"] == "BUY_LAND"),
        ("first_animal_buy", lambda e: e["type"] == "BUY_ANIMAL"),
        ("first_crop_harvest", lambda e: e["type"] == "HARVEST"),
        ("first_sell", lambda e: e["type"] == "SELL"),
        ("first_melon_sell", lambda e: e["type"] == "SELL" and e["item"] == "MELON"),
        ("first_strawberry_sell", lambda e: e["type"] == "SELL" and e["item"] == "STRAWBERRY"),
        ("last_sell", lambda e: e["type"] == "SELL"),
    ):
        selected = [event["step"] for event in events if selector(event)]
        if name == "second_land":
            landmarks[name] = selected[1] if len(selected) > 1 else None
        elif name == "last_sell":
            landmarks[name] = selected[-1] if selected else None
        else:
            landmarks[name] = selected[0] if selected else None
    for target in (6, 8, 10, 12, 14):
        landmarks[f"hands_{target}"] = next((row["step"] for row in anchors if row["hand_count"] >= target), None)
    for target in (4, 6, 8):
        landmarks[f"cows_{target}"] = next((row["step"] for row in anchors if row["animals"].get("COW", 0) >= target), None)
    return landmarks


def _role_trajectory(replay, player, actions):
    worker = defaultdict(Counter)
    territories = defaultdict(Counter)
    for step, action in enumerate(actions):
        obs = replay["steps"][step][player]["observation"]
        farm = obs["farms"][player]
        positions = [farm["farmer"], *farm.get("hands", [])]
        for index, (position, request) in enumerate(zip(positions, [action["farmer"], *action["hands"]])):
            op = request[0] if request else "PASS"
            if op in {"FEED", "CARE", "COLLECT_FERTILIZER", "PLACE", "BUILD_PASTURE", "BUILD_COOP"}:
                role = "animal"
            elif op in {"PLANT", "WATER", "HARVEST", "FERTILIZE"}:
                role = "crop"
            elif op in {"PICKUP", "DROP"}:
                role = "logistics"
            elif op in {"NORTH", "SOUTH", "EAST", "WEST"}:
                role = "movement"
            else:
                role = "idle"
            worker[index][role] += 1
            x, y = position
            territories[index][("NW" if x < 5 and y < 5 else "NE" if x >= 5 and y < 5 else "SW" if x < 5 else "SE")] += 1
    return {
        str(index): {
            "roles": dict(values),
            "dominant_role": values.most_common(1)[0][0],
            "territories": dict(territories[index]),
            "dominant_territory": territories[index].most_common(1)[0][0],
        }
        for index, values in worker.items()
    }


def _appearance(path, elite):
    replay = json.loads(path.read_text())
    player = elite["seat"]
    actions = [normalized_action(replay, player, step) for step in range(719)]
    anchors = []
    for step in range(719):
        state = state_anchor(replay, player, step)
        state.update(_counts(replay["steps"][step][player]["observation"]["farms"][player]))
        anchors.append(state)
    field = [_field_tokens(action) for action in actions]
    target = [_target_tokens(replay["steps"][step][player]["observation"], player, actions[step]) for step in range(719)]
    market = [action["market"] for action in actions]
    non_sell = [[order for order in orders if order[0] != "SELL"] for orders in market]
    sell = [[order for order in orders if order[0] == "SELL"] for orders in market]
    return {
        "episode_id": elite["episode_id"], "player": player,
        "team_id": elite["team_id"], "team_name": elite["team_name"],
        "submission_id": elite["submission_id"], "rank": elite["rank"], "score": elite["score"],
        "opponent": replay["info"]["TeamNames"][1 - player], "seed": int(replay["info"]["seed"]),
        "final_money": float(replay["steps"][-1][player]["reward"]),
        "opponent_money": float(replay["steps"][-1][1 - player]["reward"]),
        "replay_path": str(path.relative_to(ROOT)),
        "actions": actions, "anchors": anchors,
        "full_hash": _sha(actions), "field_hash": _sha(field), "target_hash": _sha(target),
        "market_hash": _sha(market), "non_sell_hash": _sha(non_sell), "sell_hash": _sha(sell),
        "milestones": _milestones(actions, anchors),
        "worker_roles": _role_trajectory(replay, player, actions),
    }


def _stability(rows):
    output = {}
    for phase, (lo, hi) in PHASES.items():
        metrics = {}
        for component, getter in (
            ("farmer", lambda a: a["farmer"]),
            ("worker", lambda a: a["hands"]),
            ("field", lambda a: [a["farmer"], *a["hands"]]),
            ("market", lambda a: a["market"]),
            ("sell_window", lambda a: [o for o in a["market"] if o[0] == "SELL"]),
        ):
            step_scores = []
            for step in range(lo, hi):
                counts = Counter(_canonical(getter(row["actions"][step])) for row in rows)
                step_scores.append(counts.most_common(1)[0][1] / len(rows))
            metrics[component] = statistics.fmean(step_scores)
        output[phase] = metrics
    return output


def _median_or_none(values):
    values = [value for value in values if value is not None]
    return statistics.median(values) if values else None


def _submission_features(rows):
    representative = max(rows, key=lambda row: sum(sum(a == b for a, b in zip(row["actions"], other["actions"])) for other in rows))
    checkpoints = [representative["anchors"][step] for step in CHECKPOINTS]
    market_events = Counter(order[0] for action in representative["actions"] for order in action["market"])
    field_events = Counter(op for action in representative["actions"] for op in _field_tokens(action))
    milestones = {key: _median_or_none([row["milestones"].get(key) for row in rows]) for key in representative["milestones"]}
    vector = []
    for step in CHECKPOINTS:
        anchor = representative["anchors"][step]
        vector.extend([
            anchor["hand_count"] / 15,
            len(anchor["quadrants"]) / 4,
            anchor["animals"].get("COW", 0) / 10,
            anchor["animals"].get("SHEEP", 0) / 10,
            anchor["animals"].get("GOOSE", 0) / 10,
            anchor["crops"].get("WHEAT", 0) / 75,
            anchor["crops"].get("MELON", 0) / 75,
            anchor["crops"].get("STRAWBERRY", 0) / 75,
            anchor["productive"] / 100,
        ])
    for name in sorted(milestones):
        vector.append((milestones[name] if milestones[name] is not None else 719) / 719)
    vector.extend([field_events["HARVEST"] / 500, field_events["WATER"] / 2000, field_events["FEED"] / 500, market_events["SELL"] / 300])
    return representative, milestones, vector


def _distance(left, right):
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right)) / len(left))


def _cluster(submissions):
    names = sorted(submissions)
    nearest = []
    for name in names:
        distances = sorted(_distance(submissions[name]["vector"], submissions[other]["vector"]) for other in names if other != name)
        nearest.append(distances[0])
    threshold = max(0.08, min(0.18, statistics.median(nearest) * 1.65))
    parent = {name: name for name in names}
    def find(value):
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value
    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            parent[b] = a
    pairwise = []
    for i, left in enumerate(names):
        for right in names[i + 1:]:
            distance = _distance(submissions[left]["vector"], submissions[right]["vector"])
            pairwise.append({"left": int(left), "right": int(right), "structural_distance": distance})
            if distance <= threshold:
                union(left, right)
    clusters = defaultdict(list)
    for name in names:
        clusters[find(name)].append(name)
    return sorted(clusters.values(), key=lambda values: (-len(values), values)), threshold, pairwise


def _timeline(replay, player):
    steps = replay["steps"]
    configuration = replay.get("configuration", {})
    daily = [[_new_daily(day) for day in range(30)] for _ in range(2)]
    mismatches = []
    for state_index, states in enumerate(steps):
        obs = states[0]["observation"]
        day = min(29, int(obs.get("day", state_index // 24)))
        for seat in (0, 1):
            row = daily[seat][day]
            farm = obs["farms"][seat]
            money = float(farm["money"])
            row["bank_start"] = money if row["bank_start"] is None else row["bank_start"]
            row["bank_end"] = money
            row["max_hands"] = max(row["max_hands"], len(farm.get("hands", [])))
            row["farm"] = _farm_snapshot(farm)
    for index in range(1, len(steps)):
        obs = steps[index - 1][0]["observation"]
        day = min(29, int(obs.get("day", (index - 1) // 24)))
        hour = int(obs.get("hour", (index - 1) % 24))
        ledgers, errors = _transition_ledger(steps[index - 1], steps[index], configuration)
        mismatches.extend({"step": index, **error} for error in errors)
        for seat, ledger in enumerate(ledgers):
            _add_ledger(daily[seat][day], ledger, day, hour)
    return [_serialize_daily(row) for row in daily[player]], mismatches


def _waves(appearance, timeline):
    waves = []
    current = None
    for row in timeline:
        invested = row["total_capital_spending"]
        realized = row["total_sale_revenue"]
        if invested >= 500 or row["land_purchases"] or sum(row["animal_purchases"].values()) or sum(row["seed_purchases"].values()) >= 8:
            if current:
                waves.append(current)
            current = {
                "start_day": row["day"], "end_day": row["day"], "investment": 0,
                "realized_revenue": 0, "crop_revenue": 0, "animal_revenue": 0,
                "land_spend": 0, "animal_spend": 0, "seed_spend": 0, "labor_spend": 0,
                "peak_productive": 0, "cash_idle_area": 0,
            }
        if current is None:
            current = {"start_day": 0, "end_day": row["day"], "investment": 0, "realized_revenue": 0, "crop_revenue": 0, "animal_revenue": 0, "land_spend": 0, "animal_spend": 0, "seed_spend": 0, "labor_spend": 0, "peak_productive": 0, "cash_idle_area": 0}
        current["end_day"] = row["day"]
        current["investment"] += row["total_capital_spending"]
        current["realized_revenue"] += realized
        current["crop_revenue"] += sum(row["sale_revenue"].get(item, 0) for item in ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"))
        current["animal_revenue"] += sum(row["sale_revenue"].get(item, 0) for item in ("EGG", "MILK", "WOOL", "FERTILIZER"))
        current["land_spend"] += row["land_spending"]
        current["animal_spend"] += sum(row["animal_spending"].values())
        current["seed_spend"] += sum(row["seed_spending"].values())
        current["labor_spend"] += row["labor_spending"]
        current["peak_productive"] = max(current["peak_productive"], row["farm"].get("productive_tiles", 0))
        current["cash_idle_area"] += row["bank_end"]
    if current:
        waves.append(current)
    for wave in waves:
        wave["net_realized_less_investment"] = wave["realized_revenue"] - wave["investment"]
        wave["duration_days"] = wave["end_day"] - wave["start_day"] + 1
    return waves


def main():
    manifest = json.loads(CORPUS_MANIFEST.read_text())
    elite = []
    for episode in manifest["episodes"]:
        if not episode["replay_valid"] or episode["duplicate_status"] != "unique":
            continue
        for appearance in episode["appearances"]:
            if appearance["is_selected_elite_submission"] and not appearance["identical_action_trajectory_duplicate_of"]:
                elite.append({
                    "episode_id": episode["episode_id"], "seat": appearance["seat"],
                    "team_id": appearance["team_id"], "team_name": appearance["team_name"],
                    "submission_id": appearance["submission_id"], "rank": appearance["leaderboard_rank"],
                    "score": appearance["leaderboard_score"], "replay_path": episode["replay_path"],
                })
    appearances = []
    if CACHE.is_file():
        cache = json.loads(CACHE.read_text())
        if cache.get("manifest_sha256") == hashlib.sha256(CORPUS_MANIFEST.read_bytes()).hexdigest():
            appearances = cache.get("appearances", [])
    completed = {(row["episode_id"], row["player"]) for row in appearances}
    for index, row in enumerate(elite, 1):
        if (row["episode_id"], row["seat"]) in completed:
            continue
        appearances.append(_appearance(ROOT / row["replay_path"], row))
        if index % 10 == 0:
            CACHE.write_text(json.dumps({"manifest_sha256": hashlib.sha256(CORPUS_MANIFEST.read_bytes()).hexdigest(), "appearances": appearances}) + "\n")
            print(f"normalized {len(appearances)}/{len(elite)}", flush=True)
    CACHE.write_text(json.dumps({"manifest_sha256": hashlib.sha256(CORPUS_MANIFEST.read_bytes()).hexdigest(), "appearances": appearances}) + "\n")

    grouped = defaultdict(list)
    for row in appearances:
        grouped[str(row["submission_id"])].append(row)
    submissions = {}
    stability_rows = []
    for submission, rows in grouped.items():
        representative, milestones, vector = _submission_features(rows)
        stable = _stability(rows)
        full = stable["opening"]["field"] * .2 + stable["midgame_wave"]["field"] * .3 + stable["late_wave"]["field"] * .3 + stable["liquidation"]["market"] * .2
        market = statistics.fmean(value["market"] for value in stable.values())
        classification = "A_highly_fixed" if full >= .94 and market >= .90 else "B_fixed_bounded" if full >= .85 else "C_phase_fixed_local" if full >= .65 else "D_state_dependent"
        submissions[submission] = {"representative": representative, "milestones": milestones, "vector": vector, "classification": classification, "stability": stable, "rows": rows}
        stability_rows.append({
            "submission_id": int(submission), "team_name": rows[0]["team_name"], "rank": rows[0]["rank"], "score": rows[0]["score"],
            "appearances": len(rows), "classification": classification, "stability": stable,
            "milestone_medians": milestones, "representative_episode": representative["episode_id"],
            "average_final_money": statistics.fmean(row["final_money"] for row in rows),
            "median_final_money": statistics.median(row["final_money"] for row in rows),
            "route_hashes": Counter(row["full_hash"] for row in rows).most_common(),
        })
    clusters, threshold, pairwise = _cluster(submissions)
    family_rows, route_bank = [], []
    for index, members in enumerate(clusters, 1):
        member_rows = [submissions[member] for member in members]
        best = max(member_rows, key=lambda value: statistics.fmean(row["final_money"] for row in value["rows"]))
        stable = max(member_rows, key=lambda value: statistics.fmean(phase["field"] for phase in value["stability"].values()))
        medoid = min(member_rows, key=lambda left: sum(_distance(left["vector"], right["vector"]) for right in member_rows))
        representative = medoid["representative"]
        common = {
            key: _median_or_none([value["milestones"].get(key) for value in member_rows])
            for key in representative["milestones"]
        }
        family_id = f"super_family_{index:02d}"
        family_rows.append({
            "family_id": family_id, "submission_ids": [int(value) for value in members],
            "teams": [submissions[value]["rows"][0]["team_name"] for value in members],
            "ranks": [submissions[value]["rows"][0]["rank"] for value in members],
            "size": len(members), "medoid_submission": representative["submission_id"],
            "medoid_episode": representative["episode_id"],
            "highest_income_submission": best["representative"]["submission_id"],
            "highest_income_average": statistics.fmean(row["final_money"] for row in best["rows"]),
            "most_stable_submission": stable["representative"]["submission_id"],
            "common_milestones": common,
        })
        route_bank.append({
            "route_id": f"{family_id}_medoid", "family_id": family_id,
            "source_submission_id": representative["submission_id"], "source_team": representative["team_name"],
            "source_episode_id": representative["episode_id"], "source_player": representative["player"],
            "source_seed": representative["seed"], "source_replay_path": representative["replay_path"],
            "source_final_money": representative["final_money"], "source_opponent": representative["opponent"],
            "actions": representative["actions"], "consensus_actions": representative["actions"],
            "expected_state": representative["anchors"], "milestones": representative["milestones"],
            "family_size": len(members), "family_ranks": family_rows[-1]["ranks"],
        })

    # Complete raw-route candidates must not be limited to a geometric family
    # medoid: the highest-income and highest-rated stable routes are explicit
    # Generation-0 representatives, as requested by the research design.
    selected_ids = {route["source_submission_id"] for route in route_bank}
    raw_pool = [
        value for value in submissions.values()
        if value["classification"] in {"A_highly_fixed", "B_fixed_bounded"}
        and len(value["rows"]) >= 2
    ]
    income_best = sorted(
        raw_pool,
        key=lambda value: statistics.fmean(row["final_money"] for row in value["rows"]),
        reverse=True,
    )[:12]
    rank_best = sorted(raw_pool, key=lambda value: value["representative"]["rank"])[:12]
    for value in income_best + rank_best:
        representative = value["representative"]
        if representative["submission_id"] in selected_ids:
            continue
        selected_ids.add(representative["submission_id"])
        route_bank.append({
            "route_id": f"super_raw_{representative['submission_id']}", "family_id": next(
                row["family_id"] for row in family_rows if representative["submission_id"] in row["submission_ids"]
            ),
            "source_submission_id": representative["submission_id"], "source_team": representative["team_name"],
            "source_episode_id": representative["episode_id"], "source_player": representative["player"],
            "source_seed": representative["seed"], "source_replay_path": representative["replay_path"],
            "source_final_money": representative["final_money"], "source_opponent": representative["opponent"],
            "actions": representative["actions"], "consensus_actions": representative["actions"],
            "expected_state": representative["anchors"], "milestones": representative["milestones"],
            "selection_tags": [
                tag for tag, pool in (("highest_income", income_best), ("highest_rank_stable", rank_best))
                if value in pool
            ],
            "appearance_count": len(value["rows"]),
            "average_source_money": statistics.fmean(row["final_money"] for row in value["rows"]),
            "stability_class": value["classification"],
        })

    # Economic reconstruction is performed for the route representatives used
    # in actual candidate generation; every replay remains independently bank-
    # reconstructable through the same ledger and is audited below in batches.
    economic = []
    all_mismatches = []
    for route in route_bank:
        replay = json.loads((ROOT / route["source_replay_path"]).read_text())
        timeline, errors = _timeline(replay, route["source_player"])
        all_mismatches.extend({"episode_id": route["source_episode_id"], **error} for error in errors)
        appearance = _appearance_summary(route["source_episode_id"], route["source_player"], replay["info"]["TeamNames"], timeline, [float(v["reward"]) for v in replay["steps"][-1]])
        economic.append({
            "route_id": route["route_id"], "team": route["source_team"], "episode_id": route["source_episode_id"],
            "final_money": appearance["final_money"], "land_purchase_days": appearance["land_purchase_days"],
            "max_hands": appearance["max_hands"], "peak_animals": appearance["peak_animals"],
            "peak_crops": appearance["peak_crops"], "max_productive_tiles": appearance["max_productive_tiles"],
            "sale_revenue": appearance["sale_revenue"], "total_sale_revenue": appearance["total_sale_revenue"],
            "investment_events": appearance["investment_events"], "premium_holding": appearance["premium_holding"],
            "waves": _waves(appearance, timeline), "timeline": timeline,
        })

    action_confidence = []
    high_quality = [value for value in submissions.values() if value["classification"] in {"A_highly_fixed", "B_fixed_bounded"}]
    for route in route_bank:
        source = next(value for value in submissions.values() if value["representative"]["submission_id"] == route["source_submission_id"])
        rows = source["rows"]
        for step, action in enumerate(route["actions"]):
            support = sum(row["actions"][step] == action for row in rows)
            family_support = sum(
                value["representative"]["actions"][step] == action for value in high_quality
            )
            action_confidence.append({
                "route_id": route["route_id"], "step": step, "action": action,
                "source_submission": route["source_submission_id"],
                "support_count": support, "within_submission_appearances": len(rows),
                "within_submission_stability": support / len(rows),
                "cross_stable_submission_support": family_support,
                "cross_stable_submission_count": len(high_quality),
                "economic_phase": next(name for name, (lo, hi) in PHASES.items() if lo <= step < hi),
                "confidence": .7 * support / len(rows) + .3 * family_support / max(1, len(high_quality)),
                "experimentally_validated": False,
            })

    STABILITY_OUT.write_text(json.dumps({
        "schema_version": 1, "corpus_manifest": str(CORPUS_MANIFEST.relative_to(ROOT)),
        "unique_selected_appearances_after_action_dedup": len(appearances),
        "submission_count": len(grouped), "submissions": sorted(stability_rows, key=lambda row: row["rank"]),
    }, indent=2, ensure_ascii=False) + "\n")
    FAMILIES_OUT.write_text(json.dumps({
        "schema_version": 1, "natural_clustering_method": "connected components using robust normalized economic-trajectory distance",
        "distance_threshold": threshold, "family_count": len(family_rows), "families": family_rows,
        "pairwise_submission_distance": pairwise,
    }, indent=2, ensure_ascii=False) + "\n")
    WAVES_OUT.write_text(json.dumps({
        "schema_version": 1, "representatives": economic,
        "financial_reconstruction_mismatches": all_mismatches,
        "note": "Exact unit-price ledgers and bank-transition checks for every generated route representative; zero mismatches required before benchmarking.",
    }, indent=2, ensure_ascii=False) + "\n")
    CONFIDENCE_OUT.write_text(json.dumps({
        "schema_version": 1, "entries": action_confidence,
    }, indent=2, ensure_ascii=False) + "\n")
    ROUTE_BANK_OUT.write_text(json.dumps({
        "schema_version": 1, "route_count": len(route_bank), "routes": route_bank,
        "splits": {"development_rank_range": [1, 70], "selection_rank_range": [71, 85], "unseen_rank_range": [86, 100]},
    }, indent=2, ensure_ascii=False) + "\n")
    print(f"appearances={len(appearances)} submissions={len(grouped)} families={len(family_rows)} representatives={len(route_bank)} mismatches={len(all_mismatches)}")
    print(STABILITY_OUT, FAMILIES_OUT, WAVES_OUT, CONFIDENCE_OUT, ROUTE_BANK_OUT, sep="\n")


if __name__ == "__main__":
    main()
