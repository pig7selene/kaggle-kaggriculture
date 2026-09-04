"""Build event-driven strategic labels and deployable history features for Top 3."""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from analyze_v27_routes import normalized_action


ROOT = Path(__file__).resolve().parent
EXP = ROOT / "experiments"
MANIFEST = EXP / "top3_adaptive_corpus_manifest.json"
ONTOLOGY = EXP / "top3_adaptive_strategy_ontology.json"
SEGMENTS = EXP / "top3_adaptive_phase_segments.json"
DATASET_MANIFEST = EXP / "top3_adaptive_transition_dataset_manifest.json"
FEATURE_SCHEMA = EXP / "top3_adaptive_feature_schema.json"
LEAKAGE = EXP / "top3_adaptive_feature_leakage_audit.json"
DATASET = EXP / "top3_adaptive_transition_dataset.npz"

PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
CROPS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")
ANIMALS = ("GOOSE", "COW", "SHEEP")
PHASES = (
    "OPENING_FOUNDATION",
    "FIRST_LAND_DEPLOYMENT",
    "MELON_CAPITALIZATION",
    "SECOND_LAND_DEPLOYMENT",
    "STRAWBERRY_RAMP",
    "MIXED_PREMIUM_PRODUCTION",
    "TERMINAL_LIQUIDATION",
)
MARKET_MODES = ("ACCUMULATE", "HOLD", "STAGGERED_SELL", "LIQUIDATE", "TERMINAL")
DECISIONS = (
    "BUY_LAND_24", "HIRE_24", "RAMP_COW_48", "RAMP_SHEEP_48",
    "START_MELON_COHORT_48", "START_STRAWBERRY_COHORT_48",
    "SELL_PREMIUM_24", "ENTER_TERMINAL_24",
)
HORIZONS = (24, 48, 72, 120)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def sha(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def inventory(obs):
    values = Counter(obs["private"].get("shed", {}))
    for carried in obs["private"].get("inventories", []):
        values.update(carried)
    return values


def farm_features(farm, day, prefix):
    crops, animals, structures = Counter(), Counter(), Counter()
    productive = weeds = ready = critical = animal_due = 0
    crop_age_sum = Counter()
    for row in farm["tiles"]:
        for tile in row:
            if not isinstance(tile, dict):
                continue
            kind = tile.get("kind")
            if kind == "PLANT":
                crop = tile.get("crop")
                crops[crop] += 1; productive += 1
                crop_age_sum[crop] += max(0, day - int(tile.get("planted_day", day)))
                ready += int(tile.get("yield_units", 0) > 0)
                critical += int(not tile.get("watered_today") and int(tile.get("consecutive_unwatered", 0)) >= 1)
            elif kind in {"COOP", "PASTURE"}:
                structures[kind] += 1
                if tile.get("animal"):
                    animals[tile["animal"]] += 1; productive += 1
                    animal_due += int(not tile.get("fed_today") or not tile.get("cared_today"))
            elif kind == "WEED":
                weeds += 1
    output = {
        f"{prefix}_bank": float(farm["money"]),
        f"{prefix}_hands": len(farm.get("hands", [])),
        f"{prefix}_hires_today": int(farm.get("hires_today", 0)),
        f"{prefix}_quadrants": len(farm.get("unlocked_quadrants", [])),
        f"{prefix}_productive": productive, f"{prefix}_weeds": weeds,
        f"{prefix}_ready_tiles": ready, f"{prefix}_critical_tiles": critical,
        f"{prefix}_animal_service_due": animal_due,
    }
    for crop in CROPS:
        output[f"{prefix}_crop_{crop.lower()}"] = crops[crop]
        output[f"{prefix}_crop_{crop.lower()}_mean_age"] = crop_age_sum[crop] / max(1, crops[crop])
    for animal in ANIMALS:
        output[f"{prefix}_animal_{animal.lower()}"] = animals[animal]
    output[f"{prefix}_pastures"] = structures["PASTURE"]
    output[f"{prefix}_coops"] = structures["COOP"]
    return output


def current_features(obs, player):
    day = int(obs.get("day", int(obs.get("step", 0)) // 24))
    step = int(obs.get("step", day * 24 + int(obs.get("hour", 0))))
    values = {
        "turn_step": step, "turn_day": day, "turn_hour": int(obs.get("hour", step % 24)),
        "turn_remaining": 719 - step,
        "turn_day_sin": math.sin(2 * math.pi * day / 30),
        "turn_day_cos": math.cos(2 * math.pi * day / 30),
    }
    values.update(farm_features(obs["farms"][player], day, "own"))
    values.update(farm_features(obs["farms"][1 - player], day, "opp"))
    private_inventory = inventory(obs)
    for product in PRODUCTS:
        values[f"own_inventory_{product.lower()}"] = private_inventory[product]
    for crop in CROPS:
        values[f"own_seed_{crop.lower()}"] = int(obs["private"].get("seeds", {}).get(crop, 0))
    for product in PRODUCTS:
        values[f"market_price_{product.lower()}"] = float(obs["market"]["prices"].get(product, 0))
        values[f"market_inventory_{product.lower()}"] = float(obs["market"]["inventory"].get(product, 0))
    shops = Counter(obs["town"].get("unlocked_shops", []))
    values["town_shop_instances"] = sum(shops.values())
    for shop in ("BAKERY", "CAFE", "RESTAURANT", "GROCERY", "DAIRY", "TEXTILE", "FERTILIZER_SHOP"):
        values[f"town_{shop.lower()}"] = shops[shop]
    return values


def action_events(actions):
    events = []
    for step, action in enumerate(actions):
        row = Counter()
        for order in action["market"]:
            if not order:
                continue
            op = order[0]; item = order[1] if len(order) > 1 else ""
            quantity = int(order[2]) if len(order) > 2 else 1
            row[f"market_{op.lower()}"] += quantity
            if item:
                row[f"market_{op.lower()}_{item.lower()}"] += quantity
        for request in [action["farmer"], *action["hands"]]:
            if not request:
                continue
            op = request[0]; item = request[1] if len(request) > 1 else ""
            row[f"field_{op.lower()}"] += 1
            if item:
                row[f"field_{op.lower()}_{item.lower()}"] += 1
        events.append(row)
    return events


def first_step(events, key, minimum=0):
    return next((step for step in range(minimum, len(events)) if events[step][key] > 0), None)


def phase_plan(actions, base):
    events = action_events(actions)
    land_steps = [step for step, row in enumerate(events) if row["market_buy_land"]]
    first_land = land_steps[0] if land_steps else 144
    second_land = land_steps[1] if len(land_steps) > 1 else 264
    melon = first_step(events, "market_sell_melon", max(0, first_land))
    strawberry = first_step(events, "market_sell_strawberry", max(0, first_land))
    melon = melon if melon is not None else 719
    strawberry = strawberry if strawberry is not None else 719
    plant_steps = [step for step, row in enumerate(events) if row["field_plant"]]
    last_plant = max(plant_steps, default=624)
    # Terminal is learned as the observed cessation of planting plus liquidation,
    # not a fixed calendar label.  Cap prevents one late cleanup plant from
    # swallowing the entire terminal phase.
    terminal = min(696, max(600, last_plant + 1))
    labels = []
    for step in range(719):
        if step >= terminal:
            label = "TERMINAL_LIQUIDATION"
        elif step < first_land:
            label = "OPENING_FOUNDATION"
        elif step < second_land:
            label = "MELON_CAPITALIZATION" if step >= melon else "FIRST_LAND_DEPLOYMENT"
        elif step < min(melon, strawberry):
            label = "SECOND_LAND_DEPLOYMENT"
        elif step < max(melon, strawberry):
            label = "MELON_CAPITALIZATION" if melon < strawberry else "STRAWBERRY_RAMP"
        else:
            # Keep a bounded ramp window after the second premium family starts;
            # later observations are stable mixed production.
            label = "STRAWBERRY_RAMP" if step < max(melon, strawberry) + 72 else "MIXED_PREMIUM_PRODUCTION"
        labels.append(label)
    boundaries = [0]
    for step in range(1, 719):
        if labels[step] != labels[step - 1]:
            boundaries.append(step)
    boundaries.append(719)
    segments = []
    for left, right in zip(boundaries, boundaries[1:]):
        entry = base[left]
        exit_state = base[min(right - 1, 718)]
        decisions = Counter()
        for row in events[left:right]:
            for key, value in row.items():
                if key.startswith("market_buy_") or key.startswith("market_sell_") or key.startswith("field_plant_"):
                    decisions[key] += value
        segments.append({
            "start_step": left, "end_step": right - 1, "phase": labels[left],
            "economic_state_at_entry": {key: entry[key] for key in entry if key in {
                "turn_day", "own_bank", "own_hands", "own_quadrants", "own_productive",
                "own_animal_cow", "own_animal_sheep", "own_crop_wheat", "own_crop_melon", "own_crop_strawberry",
            }},
            "economic_state_at_exit": {key: exit_state[key] for key in exit_state if key in {
                "turn_day", "own_bank", "own_hands", "own_quadrants", "own_productive",
                "own_animal_cow", "own_animal_sheep", "own_crop_wheat", "own_crop_melon", "own_crop_strawberry",
            }},
            "major_decisions": dict(sorted(decisions.items())),
            "transition_trigger": (
                "episode_start" if left == 0 else
                "first_land_executed" if left == first_land else
                "second_land_executed" if left == second_land else
                "first_melon_realization" if left == melon else
                "first_strawberry_realization" if left == strawberry else
                "planting_ceased_and_liquidation_began" if left == terminal else
                "premium_ramp_completed"
            ),
        })
    return labels, segments, events, {
        "first_land": first_land, "second_land": second_land,
        "first_melon_sale": None if melon == 719 else melon,
        "first_strawberry_sale": None if strawberry == 719 else strawberry,
        "last_plant": last_plant, "terminal_start": terminal,
    }


def rolling_event_count(events, step, horizon, key):
    return sum(events[index][key] for index in range(max(0, step - horizon), step))


def history_features(base, events, step):
    output = {}
    trend_keys = [
        "own_bank", "opp_bank", "own_hands", "opp_hands", "own_quadrants", "opp_quadrants",
        "own_productive", "opp_productive", "own_animal_cow", "own_animal_sheep",
        "opp_animal_cow", "opp_animal_sheep", "own_crop_wheat", "own_crop_melon",
        "own_crop_strawberry", "opp_crop_melon", "opp_crop_strawberry",
        "own_inventory_milk", "own_inventory_wool", "own_inventory_strawberry", "own_inventory_melon",
    ] + [f"market_price_{item.lower()}" for item in PRODUCTS] + [f"market_inventory_{item.lower()}" for item in PRODUCTS]
    event_keys = [
        "market_buy_land", "market_hire", "market_buy_animal_cow", "market_buy_animal_sheep",
        "field_plant_wheat", "field_plant_melon", "field_plant_strawberry",
        "field_harvest", "field_feed", "field_care",
        "market_sell_melon", "market_sell_strawberry", "market_sell_milk", "market_sell_wool", "market_sell_fertilizer",
    ]
    for horizon in HORIZONS:
        previous = base[max(0, step - horizon)]
        for key in trend_keys:
            output[f"hist{horizon}_delta_{key}"] = base[step][key] - previous[key]
        for product in PRODUCTS:
            key = f"market_price_{product.lower()}"
            values = [base[index][key] for index in range(max(0, step - horizon), step + 1)]
            output[f"hist{horizon}_min_{key}"] = min(values)
            output[f"hist{horizon}_max_{key}"] = max(values)
        for key in event_keys:
            output[f"hist{horizon}_count_{key}"] = rolling_event_count(events, step, horizon, key)
    for key in ("market_buy_land", "market_hire", "market_buy_animal_cow", "market_buy_animal_sheep", "field_plant", "market_sell"):
        last = next((index for index in range(step - 1, -1, -1) if events[index][key] > 0), None)
        output[f"memory_since_{key}"] = 720 if last is None else step - last
    return output


def future_count(events, step, horizon, key):
    return sum(events[index][key] for index in range(step, min(719, step + horizon)))


def targets_for_step(base, events, labels, step):
    future24 = min(718, step + 24)
    future48 = min(718, step + 48)
    future72 = min(718, step + 72)
    valuable_inventory = sum(base[step].get(f"own_inventory_{item.lower()}", 0) for item in ("MELON", "STRAWBERRY", "MILK", "WOOL"))
    premium_sold = sum(future_count(events, step, 24, f"market_sell_{item.lower()}") for item in ("MELON", "STRAWBERRY", "MILK", "WOOL"))
    total_sold = sum(future_count(events, step, 24, f"market_sell_{item.lower()}") for item in PRODUCTS)
    if labels[step] == "TERMINAL_LIQUIDATION":
        market_mode = "TERMINAL"
    elif total_sold >= 15:
        market_mode = "LIQUIDATE"
    elif premium_sold > 0:
        market_mode = "STAGGERED_SELL"
    elif valuable_inventory >= 8:
        market_mode = "HOLD"
    else:
        market_mode = "ACCUMULATE"
    decisions = {
        "BUY_LAND_24": int(base[future24]["own_quadrants"] > base[step]["own_quadrants"]),
        "HIRE_24": int(future_count(events, step, 24, "market_hire") > 0),
        "RAMP_COW_48": int(base[future48]["own_animal_cow"] > base[step]["own_animal_cow"]),
        "RAMP_SHEEP_48": int(base[future48]["own_animal_sheep"] > base[step]["own_animal_sheep"]),
        "START_MELON_COHORT_48": int(future_count(events, step, 48, "field_plant_melon") >= 4 and rolling_event_count(events, step, 24, "field_plant_melon") < 4),
        "START_STRAWBERRY_COHORT_48": int(future_count(events, step, 48, "field_plant_strawberry") >= 4 and rolling_event_count(events, step, 24, "field_plant_strawberry") < 4),
        "SELL_PREMIUM_24": int(premium_sold > 0),
        "ENTER_TERMINAL_24": int(labels[step] != "TERMINAL_LIQUIDATION" and labels[future24] == "TERMINAL_LIQUIDATION"),
    }
    crop_counts = {crop: future_count(events, step, 48, f"field_plant_{crop.lower()}") for crop in CROPS}
    dominant_crop = max(CROPS, key=lambda crop: (crop_counts[crop], -CROPS.index(crop))) if max(crop_counts.values()) else "NONE"
    return {
        "phase": labels[step], "next_phase_24": labels[future24], "market_mode": market_mode,
        "target_land_72": int(base[future72]["own_quadrants"]),
        "target_hands_24": int(max(base[index]["own_hands"] for index in range(step, future24 + 1))),
        "target_cows_72": int(base[future72]["own_animal_cow"]),
        "target_sheep_72": int(base[future72]["own_animal_sheep"]),
        "target_crop_family_48": dominant_crop,
        "target_cohort_scale_48": int(sum(crop_counts.values())),
        **decisions,
    }


def grouped_split(appearances):
    by_teacher = defaultdict(lambda: defaultdict(list))
    for row in appearances:
        by_teacher[row["team"]][row["action_hash"]].append(row)
    assignment = {}
    audit = {}
    for teacher, groups in by_teacher.items():
        target = {"train": .60 * sum(map(len, groups.values())), "validation": .20 * sum(map(len, groups.values())), "holdout": .20 * sum(map(len, groups.values()))}
        counts = Counter()
        ordered = sorted(groups.items(), key=lambda item: (-len(item[1]), hashlib.sha256(item[0].encode()).hexdigest()))
        for action_hash, rows in ordered:
            split = max(target, key=lambda name: target[name] - counts[name])
            for row in rows:
                assignment[(row["episode_id"], row["seat"])] = split
            counts[split] += len(rows)
        audit[teacher] = {"episodes": sum(counts.values()), "split_counts": dict(counts), "action_hash_groups": len(groups)}
    return assignment, audit


def main():
    manifest = json.loads(MANIFEST.read_text())
    selected = {int(row["selected_submission_id"]): row for row in manifest["submissions"]}
    appearances = []
    for episode in manifest["episodes"]:
        if not episode["replay_valid"] or episode["duplicate_status"] != "unique":
            continue
        for appearance in episode["appearances"]:
            submission = int(appearance["submission_id"])
            if submission in selected and appearance["is_selected_elite_submission"]:
                appearances.append({
                    "episode_id": int(episode["episode_id"]), "seat": int(appearance["seat"]),
                    "team": appearance["team_name"], "rank": int(appearance["leaderboard_rank"]),
                    "submission_id": submission, "action_hash": appearance["action_hash"],
                    "replay_path": episode["replay_path"], "seed": int(episode["seed"]),
                })
    split_assignment, split_audit = grouped_split(appearances)
    phase_rows = []
    all_feature_dicts = []
    all_target_dicts = []
    metadata = []
    episode_rows = []
    for index, appearance in enumerate(sorted(appearances, key=lambda row: (row["rank"], row["episode_id"])), 1):
        replay = json.loads((ROOT / appearance["replay_path"]).read_text())
        player = appearance["seat"]
        actions = [normalized_action(replay, player, step) for step in range(719)]
        base = [current_features(replay["steps"][step][player]["observation"], player) for step in range(719)]
        labels, segments, events, milestones = phase_plan(actions, base)
        phase_rows.append({**appearance, "split": split_assignment[(appearance["episode_id"], player)], "milestones": milestones, "segments": segments})
        event_steps = {segment["start_step"] for segment in segments}
        for step, event in enumerate(events):
            if any(event[key] for key in (
                "market_buy_land", "market_buy_animal_cow", "market_buy_animal_sheep",
                "field_plant_melon", "field_plant_strawberry", "market_sell_melon", "market_sell_strawberry",
            )):
                event_steps.add(step)
        sample_steps = set(range(0, 719, 6))
        for event_step in event_steps:
            for offset in (-24, -12, -6, 0, 6, 12, 24):
                if 0 <= event_step + offset < 719:
                    sample_steps.add(event_step + offset)
        split = split_assignment[(appearance["episode_id"], player)]
        for step in sorted(sample_steps):
            features = {**base[step], **history_features(base, events, step)}
            targets = targets_for_step(base, events, labels, step)
            all_feature_dicts.append(features); all_target_dicts.append(targets)
            transition_distance = min(abs(step - segment["start_step"]) for segment in segments)
            metadata.append((appearance["rank"], appearance["episode_id"], player, step, split, transition_distance, appearance["action_hash"]))
        episode_rows.append({
            **appearance, "split": split, "sample_rows": len(sample_steps),
            "phase_transitions": len(segments) - 1, "major_event_steps": sorted(event_steps),
        })
        if index % 10 == 0:
            print(f"dataset episodes {index}/{len(appearances)}", flush=True)
    feature_names = sorted(all_feature_dicts[0])
    current_names = sorted(key for key in feature_names if not key.startswith("hist") and not key.startswith("memory_"))
    turn_names = sorted(key for key in current_names if key.startswith("turn_"))
    history_sets = {
        "turn_only": turn_names,
        "current_state": current_names,
        "history24": current_names + sorted(key for key in feature_names if key.startswith("hist24_") or key.startswith("memory_")),
        "history48": current_names + sorted(key for key in feature_names if key.startswith(("hist24_", "hist48_")) or key.startswith("memory_")),
        "history72": current_names + sorted(key for key in feature_names if key.startswith(("hist24_", "hist48_", "hist72_")) or key.startswith("memory_")),
        "history120": feature_names,
    }
    feature_index = {name: index for index, name in enumerate(feature_names)}
    X = np.asarray([[row[name] for name in feature_names] for row in all_feature_dicts], dtype=np.float32)
    split_vocab = ("train", "validation", "holdout")
    teacher = np.asarray([row[0] for row in metadata], dtype=np.int8)
    episode_id = np.asarray([row[1] for row in metadata], dtype=np.int64)
    seat = np.asarray([row[2] for row in metadata], dtype=np.int8)
    step = np.asarray([row[3] for row in metadata], dtype=np.int16)
    split = np.asarray([split_vocab.index(row[4]) for row in metadata], dtype=np.int8)
    transition_distance = np.asarray([row[5] for row in metadata], dtype=np.int16)
    phase = np.asarray([PHASES.index(row["phase"]) for row in all_target_dicts], dtype=np.int8)
    next_phase = np.asarray([PHASES.index(row["next_phase_24"]) for row in all_target_dicts], dtype=np.int8)
    market_mode = np.asarray([MARKET_MODES.index(row["market_mode"]) for row in all_target_dicts], dtype=np.int8)
    crop_vocab = ("NONE", *CROPS)
    crop_family = np.asarray([crop_vocab.index(row["target_crop_family_48"]) for row in all_target_dicts], dtype=np.int8)
    decisions = np.asarray([[row[name] for name in DECISIONS] for row in all_target_dicts], dtype=np.int8)
    targets = np.asarray([[
        row["target_land_72"], row["target_hands_24"], row["target_cows_72"],
        row["target_sheep_72"], row["target_cohort_scale_48"],
    ] for row in all_target_dicts], dtype=np.float32)
    sample_weight = np.asarray([3.0 if distance <= 12 else 1.0 for distance in transition_distance], dtype=np.float32)
    np.savez_compressed(
        DATASET, X=X, teacher=teacher, episode_id=episode_id, seat=seat, step=step,
        split=split, transition_distance=transition_distance, sample_weight=sample_weight,
        phase=phase, next_phase=next_phase, market_mode=market_mode, crop_family=crop_family,
        decisions=decisions, targets=targets,
    )
    ontology = {
        "schema_version": 1, "derivation": "Event-driven reconstruction from current Top3 forensic dossiers and 220 current-version public trajectories.",
        "phases": [
            {"name": "OPENING_FOUNDATION", "objective": "establish mixed livestock/feed/crop foundation before first land", "entry": "episode start", "exit": "first land executed"},
            {"name": "FIRST_LAND_DEPLOYMENT", "objective": "service first 50-tile economy and accumulate second-land capital", "entry": "first land", "exit": "melon realization or second land"},
            {"name": "MELON_CAPITALIZATION", "objective": "realize the early melon cohort and recycle cash", "entry": "first melon sale before both premium families active", "exit": "second land or strawberry realization"},
            {"name": "SECOND_LAND_DEPLOYMENT", "objective": "populate and service the three-quadrant economy", "entry": "second land", "exit": "first premium cohort realization"},
            {"name": "STRAWBERRY_RAMP", "objective": "bring recurring strawberry capacity online while retaining feed/livestock service", "entry": "first strawberry realization or second premium family", "exit": "bounded ramp completed"},
            {"name": "MIXED_PREMIUM_PRODUCTION", "objective": "run diversified crops and animals with market-aware realization", "entry": "both premium crop families active", "exit": "planting ceases and terminal liquidation begins"},
            {"name": "TERMINAL_LIQUIDATION", "objective": "stop unrecoverable planting, harvest, empty inventories", "entry": "observed last planting plus liquidation", "exit": "episode end"},
        ],
        "strategic_targets": ["target_land_72", "target_hands_24", "target_cows_72", "target_sheep_72", "target_crop_family_48", "target_cohort_scale_48", "market_mode"],
        "major_decisions": list(DECISIONS), "market_modes": list(MARKET_MODES),
        "redecision_events": ["six-turn observation grid for reconstruction", "start of day", "land/animal purchase", "premium cohort launch", "premium realization", "phase transition"],
    }
    write_json(ONTOLOGY, ontology)
    write_json(SEGMENTS, {
        "schema_version": 1, "appearance_count": len(phase_rows), "phases": list(PHASES),
        "segmentation_rule": "Actual land, crop-realization and planting-cessation events; terminal cessation is conservatively clipped to steps 600..696. Labels are not based solely on turn and never use teacher identity.",
        "appearances": phase_rows,
    })
    class_counts = lambda values, vocab: {name: int(np.sum(values == index)) for index, name in enumerate(vocab)}
    write_json(DATASET_MANIFEST, {
        "schema_version": 1, "dataset_path": str(DATASET.relative_to(ROOT)),
        "rows": int(len(X)), "features": len(feature_names), "sample_stride": 6,
        "event_center_offsets": [-24, -12, -6, 0, 6, 12, 24],
        "episodes": episode_rows, "split_method": "complete episode; identical teacher action hashes kept in one split",
        "split_audit": split_audit,
        "row_split_counts": {name: int(np.sum(split == index)) for index, name in enumerate(split_vocab)},
        "phase_counts": class_counts(phase, PHASES), "market_mode_counts": class_counts(market_mode, MARKET_MODES),
        "decision_positive_counts": {name: int(np.sum(decisions[:, index])) for index, name in enumerate(DECISIONS)},
        "target_names": ["target_land_72", "target_hands_24", "target_cows_72", "target_sheep_72", "target_cohort_scale_48"],
        "crop_family_vocab": list(crop_vocab), "teacher_rank_map": {"1": "tetsuya", "2": "Crop Dusta", "3": "OceanMix"},
    })
    feature_groups = {
        "turn": turn_names,
        "current_own": [name for name in current_names if name.startswith("own_")],
        "current_opponent": [name for name in current_names if name.startswith("opp_")],
        "current_market": [name for name in current_names if name.startswith("market_")],
        "current_town": [name for name in current_names if name.startswith("town_")],
        "history": [name for name in feature_names if name.startswith("hist")],
        "event_memory": [name for name in feature_names if name.startswith("memory_")],
    }
    write_json(FEATURE_SCHEMA, {
        "schema_version": 1, "feature_names": feature_names, "feature_index": feature_index,
        "feature_sets": history_sets, "groups": feature_groups,
        "deployability": "Every feature is present in current observation or reconstructable from the agent's own past observations/actions.",
        "history_horizons": list(HORIZONS), "dtype": "float32",
    })
    # Seed *inventory* is observable and deployable.  The forbidden seed is the
    # environment RNG seed, so audit that exact family rather than rejecting
    # legitimate ``own_seed_*`` features.
    forbidden = ("environment_seed", "replay", "episode_id", "team", "teacher", "rank", "future", "final_score", "submission")
    violations = [name for name in feature_names if any(token in name.lower() for token in forbidden)]
    write_json(LEAKAGE, {
        "schema_version": 1, "status": "PASS" if not violations else "FAIL",
        "forbidden_feature_families": list(forbidden), "violations": violations,
        "teacher_identity_usage": "Used only to fit/evaluate separate teacher models; absent from X and forbidden in shared/deployment models.",
        "target_lookahead": "Future windows are labels only and are never included in X.",
        "split_integrity": split_audit,
        "manual_audit": {
            "environment_seed_in_X": False, "replay_or_episode_id_in_X": False,
            "teacher_or_rank_in_X": False, "future_shop_or_price_in_X": False,
            "final_outcome_in_X": False, "ground_truth_previous_phase_in_X": False,
        },
    })
    manifest["distillation_audit"] = {
        "current_version_confidence": "HIGH_EXACT_SUBMISSION_ID",
        "usable_teacher_appearances": len(appearances), "excluded_identical_full_replays": 1,
        "split_audit": split_audit, "dataset_sha256": hashlib.sha256(DATASET.read_bytes()).hexdigest(),
    }
    write_json(MANIFEST, manifest)
    print(DATASET)
    print(f"appearances={len(appearances)} rows={len(X)} features={len(feature_names)}")
    print(json.dumps(split_audit, indent=2))


if __name__ == "__main__":
    main()
