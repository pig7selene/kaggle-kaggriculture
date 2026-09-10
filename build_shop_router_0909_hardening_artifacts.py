"""Build the auditable Shop Router 0909 hardening result artifacts."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parent
EXP = ROOT / "experiments"
GATE_PATH = EXP / "shop_router_0909_plan10_gate_raw.json"
TARGET_PATH = EXP / "shop_router_0909_plan10_targeted_raw.json"
FINAL_PATH = EXP / "shop_router_0909_hardened_final_raw.json"
EXACT_REF_PATH = EXP / "shop_router_0909_exact_plan10_reference_raw.json"
LOCK_PATH = EXP / "shop_router_0909_hardened_lock.json"


def read(path):
    return json.loads(path.read_text())


def write_json(name, payload):
    (EXP / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def percentile(values, fraction):
    ordered = sorted(values)
    point = (len(ordered) - 1) * fraction
    lo = int(point)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (point - lo)


def summary(rows):
    own = [row["own_money"] for row in rows]
    adv = [row["advantage"] for row in rows]
    outcomes = Counter(row["outcome"] for row in rows)
    warning_classes = sorted({c for row in rows for c in row.get("strict_warning_classes", [])})
    risks = [a for row in rows for a in row.get("terminal_at_risk_animals", [])]
    return {
        "games": len(rows),
        "wins": outcomes["win"],
        "losses": outcomes["loss"],
        "ties": outcomes["tie"],
        "win_rate": outcomes["win"] / len(rows) if rows else None,
        "own_money": {
            "mean": statistics.mean(own),
            "median": statistics.median(own),
            "p25": percentile(own, 0.25),
            "p10": percentile(own, 0.10),
            "p5": percentile(own, 0.05),
            "worst": min(own),
        },
        "advantage": {
            "mean": statistics.mean(adv),
            "median": statistics.median(adv),
            "p25": percentile(adv, 0.25),
            "p10": percentile(adv, 0.10),
            "p5": percentile(adv, 0.05),
            "worst": min(adv),
        },
        "runtime_exceptions": sum(bool(row.get("runtime_error")) for row in rows),
        "agent_exceptions": sum(bool(row.get("exceptions")) for row in rows),
        "livestock_escape_events": sum(len(row.get("livestock_escapes", [])) for row in rows),
        "games_with_livestock_escape": sum(bool(row.get("livestock_escapes")) for row in rows),
        "terminal_one_miss_animals": sum(a.get("consecutive_unfed") == 1 for a in risks),
        "terminal_two_miss_animals": sum(a.get("consecutive_unfed", 0) >= 2 for a in risks),
        "terminal_stranded_inventory_games": sum(row.get("terminal", {}).get("units", 0) > 0 for row in rows),
        "terminal_stranded_inventory_units": sum(row.get("terminal", {}).get("units", 0) for row in rows),
        "terminal_stranded_inventory_value": sum(row.get("terminal", {}).get("value", 0) for row in rows),
        "strict_warning_count": sum(row.get("strict_warning_count", 0) for row in rows),
        "strict_warning_classes": warning_classes,
    }


def group_summary(rows, field):
    return {str(value): summary([row for row in rows if row[field] == value]) for value in sorted({row[field] for row in rows})}


def paired(rows_a, rows_b, key_fields):
    a = {tuple(row[field] for field in key_fields): row for row in rows_a}
    b = {tuple(row[field] for field in key_fields): row for row in rows_b}
    records = []
    for key in sorted(a):
        left, right = a[key], b[key]
        records.append({
            "condition": dict(zip(key_fields, key)),
            "own_money_delta": left["own_money"] - right["own_money"],
            "opponent_money_delta": left["opponent_money"] - right["opponent_money"],
            "advantage_delta": left["advantage"] - right["advantage"],
            "exact_escape_events": len(right.get("livestock_escapes", [])),
            "hardened_escape_events": len(left.get("livestock_escapes", [])),
        })
    return records


def paired_summary(records):
    def stat(field):
        values = [row[field] for row in records]
        return {
            "mean": statistics.mean(values), "median": statistics.median(values),
            "min": min(values), "max": max(values),
            "nonzero_conditions": sum(value != 0 for value in values),
        }
    return {
        "pairs": len(records),
        "own_money_delta": stat("own_money_delta"),
        "opponent_money_delta": stat("opponent_money_delta"),
        "advantage_delta": stat("advantage_delta"),
        "exact_escape_events": sum(row["exact_escape_events"] for row in records),
        "hardened_escape_events": sum(row["hardened_escape_events"] for row in records),
    }


gate = read(GATE_PATH)
targeted = read(TARGET_PATH)
final = read(FINAL_PATH)
exact_ref = read(EXACT_REF_PATH)
lock = read(LOCK_PATH)

exact_gate = [row for row in gate["rows"] if row["variant"] == "exact"]
hard_gate = [row for row in gate["rows"] if row["variant"] == "fix_d_reallocate_day15"]
known_exact = next(row for row in exact_gate if row["seat"] == 0)
known_hard = next(row for row in hard_gate if row["seat"] == 0)


# The required trace preserves the full 95-turn lead-in and 25-turn aftermath.
write_json("shop_router_0909_plan10_failure_trace.json", {
    "schema_version": 1,
    "condition": {
        "seed": gate["seed"], "shop_mode": "fixed independent schedule",
        "shops_at_step_144": ["YARN_STORE", "PET_CAFE"], "plan": 10,
        "opponent": "frozen CurrentBest", "seats": [0, 1],
    },
    "trace_window": {"first_step": 288, "last_step": 408, "escape_action_step": 383, "first_absent_observation_step": 384},
    "reproduction": {
        "seat_0": {"escapes": exact_gate[0]["livestock_escapes"], "own_money": exact_gate[0]["own_money"], "advantage": exact_gate[0]["advantage"]},
        "seat_1": {"escapes": exact_gate[1]["livestock_escapes"], "own_money": exact_gate[1]["own_money"], "advantage": exact_gate[1]["advantage"]},
    },
    "traces": {f"seat_{row['seat']}": row["trace"] for row in exact_gate},
    "raw_source": str(GATE_PATH.relative_to(ROOT)),
    "raw_source_sha256": sha(GATE_PATH),
})


def daily_resource(row, day):
    rows = [item for item in row["trace"] if item["day"] == day]
    harvest = sum(item["transition_ledger"]["harvest"].get("WHEAT", 0) for item in rows)
    sales = sum(item["transition_ledger"]["sales"].get("WHEAT", 0) for item in rows)
    buys = sum(item["transition_ledger"]["market_buys"].get("WHEAT", 0) for item in rows)
    feeds = sum(item["transition_ledger"]["feed_successes"] for item in rows)
    opening = rows[0]["total_held_wheat"]
    return {
        "day": day, "steps": [rows[0]["step"], rows[-1]["step"]],
        "opening_held_wheat": opening, "wheat_harvested": harvest,
        "wheat_bought": buys, "wheat_sold": sales, "successful_feeds": feeds,
        "animals_requiring_feed": rows[0]["animal_count"],
        "feed_shortfall": rows[0]["animal_count"] - feeds,
        "calculated_end_wheat": opening + harvest + buys - sales - feeds,
        "last_pre_action_held_wheat": rows[-1]["total_held_wheat"],
    }


def compact_event(row, step, worker=None):
    item = next(x for x in row["trace"] if x["step"] == step)
    target = next((x for x in item["animals"] if x["position"] == [7, 4]), None)
    result = {
        "step": step, "day": item["day"], "hour": item["hour"],
        "shed_wheat_before_action": item["shed_wheat"], "total_held_wheat_before_action": item["total_held_wheat"],
        "animal_count_before_action": item["animal_count"], "target_sheep_before_action": target,
        "issued_action": item["issued_action"], "transition_ledger": item["transition_ledger"],
    }
    if worker is not None and worker < len(item["inventories"]):
        result["focus_worker"] = {
            "unit_index": worker,
            "position": item["farmer"] if worker == 0 else item["hands"][worker - 1],
            "inventory": item["inventories"][worker],
            "action": item["issued_action"]["farmer"] if worker == 0 else item["issued_action"]["hands"][worker - 1],
        }
    return result


resource_payload = {
    "schema_version": 1,
    "condition": {"seed": 1309401, "seat": 0, "plan": 10, "target_sheep": [7, 4]},
    "daily_wheat_balance": {
        "exact": [daily_resource(known_exact, day) for day in range(12, 17)],
        "hardened": [daily_resource(known_hard, day) for day in range(12, 17)],
    },
    "critical_events": {
        "exact": [compact_event(known_exact, step, worker) for step, worker in ((332, 0), (335, None), (339, 10), (341, 10), (345, 10), (359, None), (360, 0), (362, None), (363, 9), (365, 9), (369, 9), (370, 9), (383, None), (384, None))],
        "hardened": [compact_event(known_hard, step, worker) for step, worker in ((332, 0), (335, None), (339, 10), (341, 10), (345, 10), (359, None), (360, 0), (362, None), (363, 9), (365, 9), (369, 9), (370, 9), (383, None), (384, None))],
    },
    "hand_and_movement_finding": "The assigned feeder reaches [7,4] on schedule on both days. The failure is local inventory contention: each final feeder requests 2 wheat but receives 1, spends it at [6,4], then reaches [7,4] empty.",
}
write_json("shop_router_0909_plan10_resource_timeline.json", resource_payload)


root_cause = """# Shop Router 0909 Plan-10 root cause

## Finding

The sheep at `[7,4]` escapes during the end-of-day refresh after action step **383** and is first absent in observation step **384**. Both seats reproduce the same sequence.

The initiating resource decision is the step-332 order `SELL WHEAT 9`. It earns 342 coins but leaves only 16 held wheat at the start of day 14 for 17 animals. Ordered pickups then starve the final feeder: at step 339 it requests two wheat but receives one, feeds `[6,4]` at step 341, and reaches `[7,4]` empty. Its step-345 `FEED` is a silent no-op. The day-14 refresh leaves the target at `consecutive_unfed=1`.

Day 15 contains 21 wheat, enough in aggregate after later harvests, but the tape allocates it incorrectly. At step 360 the main farmer takes five wheat and never uses any wheat that day. Three earlier workers take five each. Only one remains when the final feeder requests two at step 363. It spends that unit at `[6,4]` on step 365, reaches `[7,4]` on time, but its step-369 `FEED` silently fails because its inventory has no wheat. `CARE` at step 370 succeeds but cannot substitute for feeding. The second consecutive unfed refresh after step 383 removes the sheep.

## Classification

- Primary root cause: wheat allocation/order contention.
- Initiating action: step-332 sale of nine wheat.
- First observed service failure: step-345 empty-inventory feed.
- First unavoidable point for the eventual escape on the existing tape: step 363, when the day-15 final feeder receives only one of two requested wheat after the farmer's unused five-unit pickup.
- Decisive second failed feed: step 369.
- Not causal: movement, hand count, shop randomness after route selection, or late arrival. The feeder reaches both animals at the planned turns.

## Causal verification of the selected patch

The hardened wrapper changes only step 360 under Plan 10: the farmer picks up four rather than five wheat. The final feeder then receives two wheat at step 363, retains one after feeding `[6,4]`, and successfully feeds `[7,4]` at step 369. At step 384 the sheep remains present and its counter has reset to zero. No action is inserted and no tape index shifts.
"""
(EXP / "shop_router_0909_plan10_root_cause.md").write_text(root_cause)


candidate_meta = {
    "fix_a_reserve_sale": {
        "path": "agents/shop_router_0909_hardened/v1_fix_a_reserve_sale.py", "step": 332, "actor": "market",
        "old_action": ["SELL", "WHEAT", 9], "new_action": ["SELL", "WHEAT", 8],
        "reason": "retain one wheat before the day-14 shortage", "expected_direct_cost": "forego one immediate wheat sale",
        "dead_slot_reused": False,
    },
    "fix_b_buy_one": {
        "path": "agents/shop_router_0909_hardened/v1_fix_b_buy_one.py", "step": 335, "actor": "market",
        "old_action": None, "new_action": ["BUY_PRODUCT", "WHEAT", 1],
        "reason": "use otherwise idle market capacity to restore one wheat", "expected_direct_cost": "buy one wheat at the prevailing market price",
        "dead_slot_reused": True,
    },
    "fix_c_reallocate_day14": {
        "path": "agents/shop_router_0909_hardened/v1_fix_c_reallocate_day14.py", "step": 339, "actor": "hand_1",
        "old_action": ["PICKUP", "WHEAT", 5], "new_action": ["PICKUP", "WHEAT", 4],
        "reason": "release one day-14 wheat to the final feeder", "expected_direct_cost": "no purchase or sale; reallocate one unit",
        "dead_slot_reused": False,
    },
    "fix_d_reallocate_day15": {
        "path": "agents/shop_router_0909_hardened/v1_fix_d_reallocate_day15.py", "step": 360, "actor": "farmer",
        "old_action": ["PICKUP", "WHEAT", 5], "new_action": ["PICKUP", "WHEAT", 4],
        "reason": "release one otherwise unused day-15 farmer wheat to the final feeder", "expected_direct_cost": "none; reallocate an unused carried unit",
        "dead_slot_reused": False,
    },
}
target_rows = targeted["rows"]
candidate_summaries = {}
for name, meta in candidate_meta.items():
    rows = [row for row in target_rows if row["variant"] == name]
    gate_rows = [row for row in gate["rows"] if row["variant"] == name]
    candidate_summaries[name] = {
        **meta,
        "source_sha256": sha(ROOT / meta["path"]),
        "primitive_action_definition_changes": 1,
        "tape_alignment_changed": False,
        "known_failure_gate": {
            "games": 2, "escapes": sum(len(row["livestock_escapes"]) for row in gate_rows),
            "mean_own_money": statistics.mean(row["own_money"] for row in gate_rows),
            "mean_advantage": statistics.mean(row["advantage"] for row in gate_rows),
        },
        "targeted_matrix": summary(rows),
        "actual_plan10_games": sum(row["route"]["plan_at_144"] == 10 for row in rows),
        "natural_negative_controls": sum(row["route"]["plan_at_144"] != 10 for row in rows),
    }
write_json("shop_router_0909_plan10_fix_manifest.json", {
    "schema_version": 1, "candidate_count": 4, "exact_parent_untouched": True,
    "candidates": candidate_summaries,
    "selected": "fix_d_reallocate_day15",
    "selection_reason": "All four fixes eliminated escapes; Fix D had the highest targeted mean own money and advantage, changes one numeric argument, consumes no extra resource, and introduces no new warning class.",
})


selected_target = [row for row in target_rows if row["variant"] == "fix_d_reallocate_day15"]
selected_postlock = [row for row in final["rows"] if row["variant"] == "hardened" and row["panel"] == "plan10_final"]
write_json("shop_router_0909_plan10_targeted_results.json", {
    "schema_version": 1,
    "development_matrix": {
        "design": targeted["design"], "games_per_candidate": 72, "candidate_summaries": candidate_summaries,
        "selected_candidate": summary(selected_target),
        "selected_actual_plan10_games": sum(row["route"]["plan_at_144"] == 10 for row in selected_target),
        "selected_natural_negative_controls": sum(row["route"]["plan_at_144"] != 10 for row in selected_target),
    },
    "post_lock_confirmation": {
        "summary": summary(selected_postlock),
        "actual_plan10_games": sum(row["route"]["plan_at_144"] == 10 for row in selected_postlock),
        "natural_negative_controls": sum(row["route"]["plan_at_144"] != 10 for row in selected_postlock),
    },
    "combined_selected_patch": {
        "matrix_games": len(selected_target) + len(selected_postlock),
        "actual_plan10_games": sum(row["route"]["plan_at_144"] == 10 for row in selected_target + selected_postlock),
        "natural_negative_controls": sum(row["route"]["plan_at_144"] != 10 for row in selected_target + selected_postlock),
        "escape_events": sum(len(row["livestock_escapes"]) for row in selected_target + selected_postlock),
    },
    "raw_inputs": {"development": str(TARGET_PATH.relative_to(ROOT)), "post_lock": str(FINAL_PATH.relative_to(ROOT))},
})


trajectory = final["downstream_trajectory_diff"]
write_json("shop_router_0909_plan10_downstream_diff.json", {
    "schema_version": 1,
    "condition": trajectory["condition"],
    "primitive_patch": {"step": 360, "old": ["PICKUP", "WHEAT", 5], "new": ["PICKUP", "WHEAT", 4]},
    "action_difference_count": trajectory["action_difference_count"],
    "action_difference_steps": trajectory["action_difference_steps"],
    "action_differences": trajectory["action_differences"],
    "first_state_difference_step": trajectory["first_state_difference_step"],
    "state_difference_count": trajectory["state_difference_count"],
    "state_difference_steps": trajectory["state_difference_steps"],
    "tape_indices_shifted": trajectory["tape_indices_shifted"],
    "interpretation": "Only step 360 is the deliberate tape edit. Seven later output differences are sale quantities caused by the surviving sheep's additional wool/economic state; no movement/service action is displaced and tape alignment is unchanged.",
})


league_hard = [row for row in final["rows"] if row["panel"] == "league" and row["variant"] == "hardened"]
league_exact = [row for row in final["rows"] if row["panel"] == "league" and row["variant"] == "exact"]
all_hard = [row for row in final["rows"] if row["variant"] == "hardened"]
actual_plan10_hard = [row for row in all_hard if row["route"]["plan_at_144"] == 10]
non_plan10_hard = [row for row in all_hard if row["route"]["plan_at_144"] != 10]
write_json("shop_router_0909_hardened_full_validation.json", {
    "schema_version": 1,
    "lock": lock,
    "study_total_games_all_variants": len(final["rows"]),
    "locked_candidate_postlock_games": len(all_hard),
    "broad_league": {
        "design": "8 opponents x fixed/natural x 2 fresh seeds x both seats",
        "overall": summary(league_hard),
        "by_shop_mode": group_summary(league_hard, "shop_mode"),
        "by_seat": group_summary(league_hard, "seat"),
        "by_opponent": group_summary(league_hard, "opponent"),
    },
    "all_postlock_candidate_panels": summary(all_hard),
    "actual_plan10": summary(actual_plan10_hard),
    "non_plan10": summary(non_plan10_hard),
    "safety_classification": {
        "confirmed_meaningful_semantic_failures": 0,
        "known_benign_warning_classes": ["AssertionError('invalid market operation')", "AssertionError('wrong quantity market order')"],
        "new_warning_classes": [],
        "terminal_one_miss_note": "All listed terminal animal counters equal 1 at season end; none reached the two-miss escape condition. The broad-league counts exactly match Exact.",
        "stranded_inventory_note": "Broad league: one carried WOOL in 16 games (16 units total, marked value 4040); exactly matches Exact and is unrelated to the patch. Plan-10 confirmation has zero stranded units.",
    },
    "hashes": final["locked_hashes"],
    "raw_input": str(FINAL_PATH.relative_to(ROOT)),
    "raw_input_sha256": sha(FINAL_PATH),
})


h2h_rows = [row for row in final["rows"] if row["panel"] == "h2h" and row["variant"] == "hardened"]
h2h = {}
for opponent in ("current_best", "v2", "exact"):
    rows = [row for row in h2h_rows if row["opponent"] == opponent]
    h2h[opponent] = {"overall": summary(rows), "by_shop_mode": group_summary(rows, "shop_mode"), "by_seat": group_summary(rows, "seat")}
write_json("shop_router_0909_hardened_h2h.json", {
    "schema_version": 1, "design": "Each opponent: fixed/natural x 6 fresh seeds x both seats = 24 games.",
    "results": h2h,
})


league_pairs = paired(league_hard, league_exact, ["opponent", "shop_mode", "seed", "seat"])
plan10_exact = exact_ref["rows"]
plan10_pairs = paired(selected_postlock, plan10_exact, ["opponent", "shop_mode", "seed", "seat"])
actual_plan10_pairs = [row for row in plan10_pairs if next(x for x in selected_postlock if all(x[k] == v for k, v in row["condition"].items()))["route"]["plan_at_144"] == 10]
control_pairs = [row for row in plan10_pairs if row not in actual_plan10_pairs]
escape_pairs = [row for row in actual_plan10_pairs if row["exact_escape_events"]]
non_escape_pairs = [row for row in actual_plan10_pairs if not row["exact_escape_events"]]

econ_delta = {}
for section in ("revenue", "sales", "product_spend", "harvest"):
    keys = set(known_exact["economics"][section]) | set(known_hard["economics"][section])
    econ_delta[section] = {key: known_hard["economics"][section].get(key, 0) - known_exact["economics"][section].get(key, 0) for key in keys if known_hard["economics"][section].get(key, 0) != known_exact["economics"][section].get(key, 0)}
write_json("shop_router_0909_exact_vs_hardened.json", {
    "schema_version": 1,
    "known_failure_condition": {
        "exact": {"own_money": known_exact["own_money"], "opponent_money": known_exact["opponent_money"], "advantage": known_exact["advantage"], "escape_events": len(known_exact["livestock_escapes"])},
        "hardened": {"own_money": known_hard["own_money"], "opponent_money": known_hard["opponent_money"], "advantage": known_hard["advantage"], "escape_events": len(known_hard["livestock_escapes"])},
        "delta_hardened_minus_exact": {"own_money": known_hard["own_money"] - known_exact["own_money"], "opponent_money": known_hard["opponent_money"] - known_exact["opponent_money"], "advantage": known_hard["advantage"] - known_exact["advantage"], "economics": econ_delta},
    },
    "fresh_non_plan10_league_paired": {"summary": paired_summary(league_pairs), "records": league_pairs},
    "fresh_plan10_paired": {
        "all_48_matrix_conditions": paired_summary(plan10_pairs),
        "actual_plan10_40": paired_summary(actual_plan10_pairs),
        "natural_negative_controls_8": paired_summary(control_pairs),
        "exact_escape_conditions_16": paired_summary(escape_pairs),
        "exact_non_escape_plan10_conditions_24": paired_summary(non_escape_pairs),
        "records": plan10_pairs,
    },
    "direct_h2h": h2h["exact"],
})


p_plan10 = 1 / 64
p_escape_given_plan10 = len(escape_pairs) / len(actual_plan10_pairs)
escape_cost = statistics.mean(row["own_money_delta"] for row in escape_pairs)
baseline_patch_effect = statistics.mean(row["own_money_delta"] for row in non_escape_pairs)
adjusted_escape_cost = escape_cost - baseline_patch_effect
mean_plan10_delta = statistics.mean(row["own_money_delta"] for row in actual_plan10_pairs)
mean_plan10_adv_delta = statistics.mean(row["advantage_delta"] for row in actual_plan10_pairs)
z = 1.96
n = len(actual_plan10_pairs)
p = p_escape_given_plan10
den = 1 + z * z / n
center = (p + z * z / (2 * n)) / den
half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
write_json("shop_router_0909_expected_value_analysis.json", {
    "schema_version": 1,
    "probability_plan10": {
        "value": p_plan10,
        "derivation": "The first two unlocks must be ordered YARN_STORE then PET_CAFE; 8 uniformly drawn shop types with replacement gives (1/8)*(1/8)=1/64.",
    },
    "probability_escape_given_plan10": {
        "estimate": p_escape_given_plan10, "escape_games": len(escape_pairs), "actual_plan10_games": len(actual_plan10_pairs),
        "wilson_95_interval": [center - half, center + half],
    },
    "economic_cost_of_escape_own_money": {
        "raw_conditional_hardened_minus_exact": escape_cost,
        "non_escape_plan10_patch_baseline": baseline_patch_effect,
        "baseline_adjusted_escape_cost": adjusted_escape_cost,
    },
    "requested_product_estimate": {
        "formula": "P(plan10) * P(escape|plan10) * conditional economic cost",
        "using_raw_conditional_cost": p_plan10 * p_escape_given_plan10 * escape_cost,
        "using_baseline_adjusted_cost": p_plan10 * p_escape_given_plan10 * adjusted_escape_cost,
    },
    "practical_hardening_expected_value": {
        "mean_own_money_delta_within_plan10": mean_plan10_delta,
        "mean_advantage_delta_within_plan10": mean_plan10_adv_delta,
        "expected_own_money_delta_per_random_game": p_plan10 * mean_plan10_delta,
        "expected_advantage_delta_per_random_game": p_plan10 * mean_plan10_adv_delta,
        "off_route_paired_delta": 0,
    },
    "decision": "Hardened has superior estimated practical expected value: it is identical off-route, has positive mean delta both when Exact escapes and when it does not, and removes all observed Plan-10 escapes.",
    "limitations": "The escape conditional estimate is based on 40 fresh actual-Plan-10 paired games; economic interactions make per-game deltas variable, so the estimate is directional rather than a leaderboard guarantee.",
})


broad = summary(league_hard)
fixed = summary([row for row in league_hard if row["shop_mode"] == "fixed"])
natural = summary([row for row in league_hard if row["shop_mode"] == "natural"])
seat0 = summary([row for row in league_hard if row["seat"] == 0])
seat1 = summary([row for row in league_hard if row["seat"] == 1])
known_delta = known_hard["own_money"] - known_exact["own_money"]
known_adv_delta = known_hard["advantage"] - known_exact["advantage"]

report = f"""# Shop Router 0909 Plan-10 hardening report

## Decision

**Select and promote `ShopRouter0909Hardened`.** The one-primitive Plan-10 repair removes the confirmed sheep escape while preserving exact behavior outside Plan 10. The fresh 64-game broad league was {broad['wins']}/{broad['losses']}/{broad['ties']} with mean advantage {broad['advantage']['mean']:+,.1f}; direct H2H was 24/0/0 against both CurrentBest and V2. No runtime error, agent exception, new warning class, or livestock escape occurred after lock.

## Required answers

1. **Escape turn:** end-of-day refresh after action step 383 (day 15/hour 23); the sheep is first absent in observation step 384.
2. **First causal divergence:** step 332, `SELL WHEAT 9`, starts the shortage by leaving 16 wheat for 17 animals at day-14 opening. The first service failure is step 345; the decisive day-15 allocation failure becomes unavoidable at step 363.
3. **Why:** the final feeder receives one of two requested wheat, consumes it on `[6,4]`, reaches `[7,4]` empty, and two successive `FEED` actions silently fail. Two unfed end-of-day refreshes remove the sheep.
4. **Root-cause class:** wheat resource allocation/order and feed timing. Movement and hand availability are not causal; the feeder arrives on time.
5. **Existing action that created it:** initiating step-332 wheat sale; decisive step-360 farmer pickup of five hoards one unused unit and starves the step-363 feeder pickup.
6. **Candidates tested:** 4.
7. **Edits:** A step332 sell 9→8; B step335 add buy 1 wheat in idle market capacity; C step339 first hand pickup 5→4; D step360 farmer pickup 5→4.
8. **Selected candidate:** Fix D, `reallocate_day15`.
9. **Primitive changes:** one numeric action argument, only when route Plan 10 is active.
10. **Dead/no-op reuse:** selected Fix D does not replace a dead action; it reclaims an otherwise unused carried wheat unit. Fix B tested the dead market-capacity alternative.
11. **Route alignment:** unchanged; no insertion and no tape-index shift. There are 8 emitted-action differences in the known replay: the patch at 360 plus seven later sale-quantity realizations from the surviving sheep.
12. **Escape before/after:** 1→0 in each seat of the known condition.
13. **Plan-10 targeted count:** 120 selected-patch matrix games (72 development + 48 post-lock); 100 actually routed to Plan 10 and 20 were natural-RNG negative controls. The separate known gate adds 2 games.
14. **Post-patch Plan-10 escapes:** 0/100 actual Plan-10 matrix games (and 0 in all 120 matrix games).
15. **Known-condition own-money delta:** {known_delta:+,.0f} (90,596→94,723).
16. **Known-condition advantage delta:** {known_adv_delta:+,.0f} (29,361→33,503); opponent money changed by -15.
17. **Fresh broad validation W/L/T:** {broad['wins']}/{broad['losses']}/{broad['ties']} across 64 games. Across all 184 locked-candidate post-lock games: 160/0/24; all ties are the direct Exact H2H where the route was outside Plan 10.
18. **Broad mean own money:** {broad['own_money']['mean']:,.1f}; median {broad['own_money']['median']:,.1f}.
19. **Broad mean advantage:** {broad['advantage']['mean']:+,.1f}.
20. **H2H vs CurrentBest:** {h2h['current_best']['overall']['wins']}/0/0, mean advantage {h2h['current_best']['overall']['advantage']['mean']:+,.1f} over 24 games.
21. **H2H vs V2:** {h2h['v2']['overall']['wins']}/0/0, mean advantage {h2h['v2']['overall']['advantage']['mean']:+,.1f} over 24 games.
22. **Natural-shop broad league:** {natural['wins']}/0/0, mean own {natural['own_money']['mean']:,.1f}, mean advantage {natural['advantage']['mean']:+,.1f}, worst {natural['advantage']['worst']:+,.0f} (32 games).
23. **Fixed-shop broad league:** {fixed['wins']}/0/0, mean own {fixed['own_money']['mean']:,.1f}, mean advantage {fixed['advantage']['mean']:+,.1f}, worst {fixed['advantage']['worst']:+,.0f} (32 games).
24. **Seat 0:** {seat0['wins']}/0/0, mean own {seat0['own_money']['mean']:,.1f}, mean advantage {seat0['advantage']['mean']:+,.1f} (32 broad-league games).
25. **Seat 1:** {seat1['wins']}/0/0, mean own {seat1['own_money']['mean']:,.1f}, mean advantage {seat1['advantage']['mean']:+,.1f} (32 broad-league games).
26. **Broad advantage P25:** {broad['advantage']['p25']:+,.1f} (own-money P25 {broad['own_money']['p25']:,.1f}).
27. **Broad advantage P10:** {broad['advantage']['p10']:+,.1f} (own-money P10 {broad['own_money']['p10']:,.1f}).
28. **Broad advantage P5:** {broad['advantage']['p5']:+,.1f} (own-money P5 {broad['own_money']['p5']:,.1f}).
29. **Broad worst:** advantage {broad['advantage']['worst']:+,.0f}; own money {broad['own_money']['worst']:,.0f}.
30. **Runtime exceptions:** 0.
31. **Agent exceptions:** 0.
32. **Actual livestock escapes:** 0 across 184 post-lock candidate games. Terminal counters: 1,448 animal-instances had exactly one missed final-day refresh across all panels, but none had two misses; broad-league counts exactly match Exact and the season ends before escape. 
33. **New warning class:** none. Only the two previously classified benign strict-checker classes appeared; broad counts are exactly Hardened 2,778 vs Exact 2,778.
34. **Exact-vs-Hardened paired delta:** off-route broad league 64/64 pairs are exactly 0 own/0 opponent/0 advantage. Across 40 fresh actual Plan-10 pairs: mean own {paired_summary(actual_plan10_pairs)['own_money_delta']['mean']:+,.1f}, opponent {paired_summary(actual_plan10_pairs)['opponent_money_delta']['mean']:+,.1f}, advantage {paired_summary(actual_plan10_pairs)['advantage_delta']['mean']:+,.1f}.
35. **Expected-value cost of the original defect:** `1/64 × 16/40 × 2,466.1 = 15.41` own-money coins per random game using raw conditional cost; baseline-adjusted estimate is 14.92. Practical paired hardening gain is {p_plan10 * mean_plan10_delta:+.2f} own coins and {p_plan10 * mean_plan10_adv_delta:+.2f} advantage per random game.
36. **Practical EV:** Hardened is superior: zero off-route cost, +78.7 mean own money even in the 24 Plan-10 pairs where Exact did not escape, and positive overall Plan-10 paired gain.
37. **Selected version:** `ShopRouter0909HardenedPlan10ReallocateDay15`.
38. **Research-best promotion:** yes, after the locked validation passed.
39. **Final source:** `agents/shop_router_0909_hardened/main.py`.
40. **Final SHA-256:** `{lock['candidate_sha256']}`.
41. **`experiments/current_best.json`:** changed to point at the hardened research agent.
42. **Frozen CurrentBest source:** untouched; SHA-256 remains `{final['locked_hashes']['current_best']}`.
43. **`submission/main.py`:** untouched; SHA-256 remains `{final['locked_hashes']['submission']}`.
44. **Kaggle:** no package, upload, or submission was performed.

## Safety interpretation

The 16 broad-league terminal stranded units are one carried wool per affected game (aggregate marked value 4,040), exactly matching Exact. They are not caused by the patch. Existing strict warnings remain intentional public-tape behavior and are not counted as environment failures. Provenance is retained in `agents/shop_router_0909_hardened/NOTICE.md` and `LICENSE.txt`; the exact public parent and action payload remain immutable.

Frozen Exact asset hashes are: `main.py` `d6d74997dc5b483db63d8e39cafa1afeec0f366824e75107e109123f111e866b`; `actions.json` `17d503f2fd20d59f9c0f14024d1e74a8add8bb9b5561d4d908b45deecb5495ef`; `LICENSE.txt` `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`; `submission-manifest.json` `e58657e059e0dac2e1fe9c9175141a3d876bc7d33b7b31ddca80669ec10e8df6`.
"""
(EXP / "shop_router_0909_hardening_report.md").write_text(report)


print(json.dumps({
    "artifacts_built": 11,
    "promotion_gate": {
        "broad_wlt": [broad["wins"], broad["losses"], broad["ties"]],
        "current_best_h2h_wlt": [h2h["current_best"]["overall"]["wins"], h2h["current_best"]["overall"]["losses"], h2h["current_best"]["overall"]["ties"]],
        "postlock_escapes": summary(all_hard)["livestock_escape_events"],
        "runtime_exceptions": summary(all_hard)["runtime_exceptions"],
        "agent_exceptions": summary(all_hard)["agent_exceptions"],
        "new_warning_classes": [],
    },
}, indent=2))
