"""Analyze the V2 Top-20 development split and compare it with V1 families."""

from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
import json
import math
from pathlib import Path
import statistics

import analyze_super_replays as base
from analyze_top_player_replays import _transition_ledger
from analyze_v27_routes import normalized_action


ROOT = Path(__file__).resolve().parent
FULL = ROOT / "experiments/v2_top20_corpus_manifest.json"
DEV = ROOT / "experiments/v2_top20_development_manifest.json"
STABILITY = ROOT / "experiments/v2_route_stability.json"
FAMILIES = ROOT / "experiments/v2_route_families.json"
ECONOMIC = ROOT / "experiments/v2_top20_economic_waves.json"
CONFIDENCE = ROOT / "experiments/v2_action_confidence.json"
ROUTE_BANK = ROOT / "experiments/v2_route_bank.json"
EXECUTOR = ROOT / "experiments/v2_route_executor.json"
PHASE_OUTPUT = ROOT / "experiments/v2_phase_comparison.json"
OLD_FAMILIES = ROOT / "experiments/super_replay_route_families.json"
OLD_ROUTES = ROOT / "experiments/super_replay_route_executor.json"
OLD_ROUTE_BANK = ROOT / "experiments/super_replay_route_bank.json"

PHASES = {
    "P0_opening_initialization": (0, 96),
    "P1_first_capital_accumulation": (96, 144),
    "P2_first_land_labor_deployment": (144, 240),
    "P3_first_major_crop_wave": (240, 336),
    "P4_midgame_reinvestment": (336, 504),
    "P5_second_major_crop_wave": (504, 648),
    "P6_final_production_liquidation": (648, 719),
}


def _development_manifest():
    full = json.loads(FULL.read_text())
    payload = deepcopy(full)
    payload["episodes"] = [row for row in payload["episodes"] if row.get("split") == "development"]
    payload["selected_episode_ids"] = [row["episode_id"] for row in payload["episodes"]]
    payload["corpus_summary"]["v2_development_unique_episodes"] = len(payload["episodes"])
    payload["corpus_summary"]["v2_final_holdout_unique_episodes"] = len(full["splits"]["final_holdout_episode_ids"])
    DEV.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    return payload


def _vector(route):
    vector = []
    for step in base.CHECKPOINTS:
        anchor = route["expected_state"][step]
        vector.extend([
            anchor.get("hand_count", 0) / 15,
            len(anchor.get("quadrants", [])) / 4,
            anchor.get("animals", {}).get("COW", 0) / 10,
            anchor.get("animals", {}).get("SHEEP", 0) / 10,
            anchor.get("animals", {}).get("GOOSE", 0) / 10,
            anchor.get("crops", {}).get("WHEAT", 0) / 75,
            anchor.get("crops", {}).get("MELON", 0) / 75,
            anchor.get("crops", {}).get("STRAWBERRY", 0) / 75,
            anchor.get("productive", 0) / 100,
        ])
    for name in sorted(route.get("milestones", {})):
        value = route["milestones"].get(name)
        vector.append((value if value is not None else 719) / 719)
    field = Counter(req[0] for action in route["consensus_actions"] for req in [action["farmer"], *action["hands"]])
    market = Counter(order[0] for action in route["consensus_actions"] for order in action["market"])
    vector.extend([field["HARVEST"] / 500, field["WATER"] / 2000, field["FEED"] / 500, market["SELL"] / 300])
    return vector


def _distance(left, right):
    count = min(len(left), len(right))
    return math.sqrt(sum((left[i] - right[i]) ** 2 for i in range(count)) / count)


def _phase_name(step):
    return next(name for name, (lo, hi) in PHASES.items() if lo <= step < hi)


def _phase_economics(route):
    replay = json.loads((ROOT / route["source_replay_path"]).read_text())
    player = int(route["source_player"])
    rows = {}
    for name, (lo, hi) in PHASES.items():
        start_obs = replay["steps"][lo][player]["observation"]
        end_obs = replay["steps"][min(hi, 719)][player]["observation"]
        rows[name] = {
            "start_step": lo, "end_step_exclusive": hi,
            "start_money": float(start_obs["farms"][player]["money"]),
            "end_money": float(end_obs["farms"][player]["money"]),
            "money_change": float(end_obs["farms"][player]["money"] - start_obs["farms"][player]["money"]),
            "start_state": route["expected_state"][lo],
            "end_state": route["expected_state"][min(hi, 718)],
            "gross_revenue": 0, "crop_revenue": 0, "animal_revenue": 0,
            "total_spending": 0, "seed_spending": 0, "feed_spending": 0,
            "animal_spending": 0, "land_spending": 0, "labor_spending": 0,
            "harvests": {}, "plantings": {}, "sales": {}, "sale_revenue": {},
            "movement_actions": 0, "water_actions": 0, "harvest_actions": 0,
            "field_action_slots": 0, "worker_action_slots": 0,
        }
    crop_products = {"WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"}
    for index in range(1, 720):
        step = index - 1
        name = _phase_name(step)
        row = rows[name]
        ledgers, errors = _transition_ledger(replay["steps"][index-1], replay["steps"][index], replay.get("configuration", {}))
        if errors:
            row.setdefault("financial_mismatches", []).extend(errors)
        ledger = ledgers[player]
        sale_revenue = dict(ledger["sale_revenue"])
        revenue = sum(sale_revenue.values())
        row["gross_revenue"] += revenue
        row["crop_revenue"] += sum(value for item, value in sale_revenue.items() if item in crop_products)
        row["animal_revenue"] += revenue - sum(value for item, value in sale_revenue.items() if item in crop_products)
        seed = sum(ledger["seed_spend"].values()); feed = sum(ledger["product_spend"].values())
        animal = sum(ledger["animal_spend"].values()); land = ledger["land_spend"]; labor = ledger["labor_spend"]
        row["seed_spending"] += seed; row["feed_spending"] += feed; row["animal_spending"] += animal
        row["land_spending"] += land; row["labor_spending"] += labor
        row["total_spending"] += seed + feed + animal + land + labor
        for target, source in (("harvests", ledger["harvest_quantity"]), ("plantings", ledger["plant_quantity"]), ("sales", ledger["sale_quantity"]), ("sale_revenue", ledger["sale_revenue"])):
            counter = Counter(row[target]); counter.update(source); row[target] = dict(counter)
        action = normalized_action(replay, player, step)
        requests = [action["farmer"], *action["hands"]]
        row["movement_actions"] += sum(req[0] in {"NORTH", "SOUTH", "EAST", "WEST"} for req in requests)
        row["water_actions"] += sum(req[0] == "WATER" for req in requests)
        row["harvest_actions"] += sum(req[0] == "HARVEST" for req in requests)
        row["field_action_slots"] += len(requests); row["worker_action_slots"] += len(action["hands"])
    for row in rows.values():
        row["net_realized_cash"] = row["gross_revenue"] - row["total_spending"]
        row["ending_hands"] = row["end_state"].get("hand_count", 0)
        row["ending_land"] = len(row["end_state"].get("quadrants", []))
        row["ending_animals"] = row["end_state"].get("animals", {})
        row["ending_crops"] = row["end_state"].get("crops", {})
        row["ending_productive"] = row["end_state"].get("productive", 0)
    return rows


def main():
    manifest = _development_manifest()
    base.CORPUS_MANIFEST = DEV
    base.STABILITY_OUT = STABILITY
    base.FAMILIES_OUT = FAMILIES
    base.WAVES_OUT = ECONOMIC
    base.CONFIDENCE_OUT = CONFIDENCE
    base.ROUTE_BANK_OUT = ROUTE_BANK
    base.CACHE = ROOT / "experiments/v2_top20_analysis_cache.json.partial"
    base.main()

    stability = json.loads(STABILITY.read_text())
    families = json.loads(FAMILIES.read_text())
    bank = json.loads(ROUTE_BANK.read_text())
    old_bank = json.loads(OLD_ROUTES.read_text())
    old_family_routes = [row for row in old_bank["routes"] if row["route_id"].startswith("super_family_")]
    old_vectors = {row["route_id"].removesuffix("_medoid"): _vector(row) for row in old_family_routes}
    stability_by_submission = {row["submission_id"]: row for row in stability["submissions"]}
    family_mapping = []
    for family in families["families"]:
        route = next(row for row in bank["routes"] if row["route_id"] == f"{family['family_id']}_medoid")
        vector = _vector(route)
        nearest, distance = min(((name, _distance(vector, value)) for name, value in old_vectors.items()), key=lambda pair: pair[1])
        classes = Counter(stability_by_submission[value]["classification"] for value in family["submission_ids"])
        relation = "same_known_family" if distance <= 0.04 else "mutated_known_family" if distance <= 0.18 else "completely_new_family"
        family_mapping.append({
            "v2_family_id": family["family_id"], "size": family["size"], "ranks": family["ranks"],
            "nearest_v1_family": nearest, "structural_distance": distance,
            "relation": relation, "stability_classes": dict(classes),
        })
    families["comparison_to_v1"] = family_mapping
    families["meta_movement_summary"] = dict(Counter(row["relation"] for row in family_mapping))
    FAMILIES.write_text(json.dumps(families, indent=2, ensure_ascii=False, sort_keys=True) + "\n")

    phase_rows = []
    for index, route in enumerate(bank["routes"], 1):
        phase_rows.append({
            "route_id": route["route_id"], "source_submission_id": route["source_submission_id"],
            "source_team": route["source_team"], "source_episode_id": route["source_episode_id"],
            "source_final_money": route["source_final_money"], "phases": _phase_economics(route),
        })
        print(f"phase economics {index}/{len(bank['routes'])}", flush=True)
    v1 = next(row for row in json.loads(OLD_ROUTE_BANK.read_text())["routes"] if row["route_id"] == "super_raw_55459817")
    v1_phases = _phase_economics(v1)
    comparisons = []
    for row in phase_rows:
        for name in PHASES:
            candidate = row["phases"][name]; baseline = v1_phases[name]
            comparisons.append({
                "route_id": row["route_id"], "phase": name,
                "net_realized_delta_vs_v1": candidate["net_realized_cash"] - baseline["net_realized_cash"],
                "ending_money_delta_vs_v1": candidate["end_money"] - baseline["end_money"],
                "gross_revenue_delta_vs_v1": candidate["gross_revenue"] - baseline["gross_revenue"],
                "spending_delta_vs_v1": candidate["total_spending"] - baseline["total_spending"],
                "entry_compatibility": {
                    "hands_delta": candidate["start_state"].get("hand_count", 0) - baseline["start_state"].get("hand_count", 0),
                    "land_delta": len(candidate["start_state"].get("quadrants", [])) - len(baseline["start_state"].get("quadrants", [])),
                    "animal_l1": sum(abs(candidate["start_state"].get("animals", {}).get(k, 0) - baseline["start_state"].get("animals", {}).get(k, 0)) for k in set(candidate["start_state"].get("animals", {})) | set(baseline["start_state"].get("animals", {}))),
                    "crop_l1": sum(abs(candidate["start_state"].get("crops", {}).get(k, 0) - baseline["start_state"].get("crops", {}).get(k, 0)) for k in set(candidate["start_state"].get("crops", {})) | set(baseline["start_state"].get("crops", {}))),
                    "money_delta": candidate["start_money"] - baseline["start_money"],
                },
            })
    PHASE_OUTPUT.write_text(json.dumps({
        "schema_version": 1, "phase_definitions": PHASES, "v1_route_id": v1["route_id"],
        "v1_phases": v1_phases, "route_phases": phase_rows,
        "comparisons_vs_v1": sorted(comparisons, key=lambda r: r["net_realized_delta_vs_v1"], reverse=True),
    }, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    minimal = []
    for route in bank["routes"]:
        minimal.append({key: route.get(key) for key in (
            "route_id", "family_id", "source_submission_id", "source_team", "source_episode_id",
            "source_player", "source_seed", "source_replay_path", "source_final_money",
            "consensus_actions", "expected_state", "milestones", "appearance_count",
            "average_source_money", "stability_class",
        ) if key in route})
    EXECUTOR.write_text(json.dumps({"schema_version": 1, "route_count": len(minimal), "routes": minimal}, separators=(",", ":")) + "\n")
    print(json.dumps({
        "development_episodes": len(manifest["episodes"]), "submissions": len(stability["submissions"]),
        "families": len(families["families"]), "routes": len(bank["routes"]),
        "meta_movement": families["meta_movement_summary"],
    }, indent=2))


if __name__ == "__main__":
    main()
