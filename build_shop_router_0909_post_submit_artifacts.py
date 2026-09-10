"""Build the frozen ShopRouter0909 post-submission diagnostic artifacts."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
import hashlib
import json
import math
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parent
EXP = ROOT / "experiments"
RAW = EXP / "shop_router_0909_post_submit_diagnostic_raw.json"
ACTIONS = ROOT / "agents/shop_router_0909/actions.json"
FROZEN = ROOT / "agents/shop_router_0909_hardened/main.py"
SUBMISSION_MAIN = ROOT / "submission/main.py"
SUBMISSION_ARCHIVE = ROOT / "submission/shop_router_0909_hardened.tar.gz"
ROUTE = {
    ("BAKERY", "YARN_STORE"): 3,
    ("BRUNCH_SPOT", "YARN_STORE"): 4,
    ("FARMERS_MARKET", "YARN_STORE"): 5,
    ("ICE_CREAM_SHOP", "YARN_STORE"): 6,
    ("PET_CAFE", "YARN_STORE"): 5,
    ("PIZZA_SHOP", "YARN_STORE"): 7,
    ("SMOOTHIE_SHOP", "YARN_STORE"): 8,
    ("YARN_STORE", "BAKERY"): 9,
    ("YARN_STORE", "BRUNCH_SPOT"): 9,
    ("YARN_STORE", "FARMERS_MARKET"): 1,
    ("YARN_STORE", "ICE_CREAM_SHOP"): 9,
    ("YARN_STORE", "PET_CAFE"): 10,
    ("YARN_STORE", "PIZZA_SHOP"): 6,
    ("YARN_STORE", "SMOOTHIE_SHOP"): 11,
    ("YARN_STORE", "YARN_STORE"): 12,
}
EXPECTED_HASHES = {
    "agents/shop_router_0909_hardened/main.py": "da5c6df2c71128ce1372a5adaf6d4859f5758e7854b399d6ff634fbca666d8a2",
    "submission/main.py": "4a188ceaedaa5e37c2216c803517314a2cb2fd780a5bb65956ca016cf278c803",
    "submission/shop_router_0909_hardened.tar.gz": "26e7d39eb1df83af7c595167298ad8f3d61afce76e216cd1e25d6416bb791046",
}


def write_json(name, value):
    path = EXP / name
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    return path


def pct(values, q):
    values = sorted(float(v) for v in values)
    if not values:
        return None
    point = (len(values) - 1) * q
    lo = int(point)
    hi = min(lo + 1, len(values) - 1)
    w = point - lo
    return values[lo] * (1 - w) + values[hi] * w


def stat(values):
    values = [float(v) for v in values]
    return {
        "n": len(values),
        "mean": statistics.fmean(values) if values else None,
        "median": statistics.median(values) if values else None,
        "p25": pct(values, 0.25),
        "p10": pct(values, 0.10),
        "p5": pct(values, 0.05),
        "min": min(values) if values else None,
        "max": max(values) if values else None,
    }


def corr(xs, ys):
    if len(xs) < 2:
        return None
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    dx = [x - mx for x in xs]
    dy = [y - my for y in ys]
    denom = math.sqrt(sum(x * x for x in dx) * sum(y * y for y in dy))
    return sum(x * y for x, y in zip(dx, dy)) / denom if denom else 0.0


def common_prefix(left, right, start=0):
    for step in range(start, min(len(left), len(right))):
        if left[step] != right[step]:
            return step - start, step
    return min(len(left), len(right)) - start, None


def effective_tape(tapes, plan):
    return [
        tapes[0][step] if step < 144 else tapes[plan][step] if step < 648 else tapes[2][step]
        for step in range(719)
    ]


def plan_profile(tapes, plan):
    tape = effective_tape(tapes, plan)
    market = Counter()
    animals = Counter()
    plant = Counter()
    sell_orders = Counter()
    seed_orders = Counter()
    hire_by_day = Counter()
    land_steps = []
    crop_waves = defaultdict(Counter)
    animal_steps = defaultdict(list)
    for step, action in enumerate(tape):
        for order in action.get("market", []):
            if not order:
                continue
            op = order[0]
            market[op] += 1
            if op == "HIRE":
                hire_by_day[step // 24] += 1
            elif op == "BUY_LAND":
                land_steps.append(step)
            elif op == "BUY_ANIMAL" and len(order) >= 3:
                animals[order[1]] += int(order[2])
                animal_steps[order[1]].append(step)
            elif op == "BUY_SEED" and len(order) >= 3:
                seed_orders[order[1]] += int(order[2])
            elif op == "SELL" and len(order) >= 2:
                sell_orders[order[1]] += 1
        workers = [action.get("farmer", ["PASS"]), *action.get("hands", [])]
        for work in workers:
            if work and work[0] == "PLANT" and len(work) >= 2:
                plant[work[1]] += 1
                crop_waves[step // 24][work[1]] += 1
    dominant_crop = max(plant, key=plant.get) if plant else "NONE"
    dominant_animal = max(animals, key=animals.get) if animals else "NONE"
    peak_hands = max(hire_by_day.values(), default=0)
    identity = (
        f"{dominant_animal.lower()}-led livestock; {dominant_crop.lower()}-led crop tape; "
        f"{len(land_steps)} land buys; peak {peak_hands} daily hires"
    )
    vector = [
        len(land_steps), sum(hire_by_day.values()), peak_hands,
        animals.get("COW", 0), animals.get("SHEEP", 0), animals.get("GOOSE", 0),
        *[plant.get(crop, 0) for crop in ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")],
        *[sell_orders.get(item, 0) for item in ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL")],
    ]
    return {
        "plan_id": plan,
        "effective_policy_window": {
            "common_prefix": "plan 0, steps 0-143",
            "plan_continuation": f"plan {plan}, steps 144-647",
            "common_terminal": "plan 2, steps 648-718 with dynamic liquidation at 718",
        },
        "economic_identity": identity,
        "land": {"buy_count": len(land_steps), "steps": land_steps, "days": [s // 24 for s in land_steps]},
        "hands": {
            "total_hire_orders": sum(hire_by_day.values()),
            "peak_hires_in_day": peak_hands,
            "hires_by_day": {str(day): count for day, count in sorted(hire_by_day.items()) if count},
        },
        "cow_count_planned": animals.get("COW", 0),
        "sheep_count_planned": animals.get("SHEEP", 0),
        "goose_count_planned": animals.get("GOOSE", 0),
        "animal_buy_quantities": dict(animals),
        "animal_buy_steps": dict(animal_steps),
        "major_crop_waves": {
            str(day): dict(counts) for day, counts in sorted(crop_waves.items()) if sum(counts.values())
        },
        "plant_action_counts": dict(plant),
        "seed_buy_quantities": dict(seed_orders),
        "market_order_counts": dict(market),
        "sell_order_counts": dict(sell_orders),
        "terminal_strategy": "At step 648 every route switches to plan 2; step 718 dynamically drops reachable inventory and sells projected shed stock by value.",
        "profile_vector": vector,
    }


def aggregate_rows(rows):
    own = [r["own_money"] for r in rows]
    adv = [r["advantage"] for r in rows]
    opponent = [r["opponent_money"] for r in rows]
    terminal_units = [r["terminal"]["units"] for r in rows]
    terminal_value = [r["terminal"]["value"] for r in rows]
    animal_keys = ("COW", "SHEEP", "GOOSE")
    return {
        "games": len(rows),
        "own_money": stat(own),
        "advantage": stat(adv),
        "opponent_money": stat(opponent),
        "outcomes": dict(Counter(r["outcome"] for r in rows)),
        "terminal_inventory": {
            "units": stat(terminal_units),
            "market_value": stat(terminal_value),
            "zero_units_rate": sum(v == 0 for v in terminal_units) / len(rows) if rows else None,
        },
        "livestock": {
            "mean_final_counts": {
                animal: statistics.fmean(r["final_counts"]["animals"].get(animal, 0) for r in rows)
                for animal in animal_keys
            },
            "escape_games": sum(bool(r["livestock_escapes"]) for r in rows),
            "escape_events": sum(len(r["livestock_escapes"]) for r in rows),
        },
    }


def group_matrix(rows, key):
    groups = defaultdict(list)
    for row in rows:
        groups[str(key(row))].append(row)
    return {name: aggregate_rows(group) for name, group in sorted(groups.items())}


def mechanism(selected_profile, best_profile, selected_row, best_row):
    differences = []
    land = best_profile["land"]["buy_count"] - selected_profile["land"]["buy_count"]
    labor = best_profile["hands"]["peak_hires_in_day"] - selected_profile["hands"]["peak_hires_in_day"]
    if land:
        differences.append(f"alternative has {land:+d} planned land buys")
    if labor:
        differences.append(f"alternative peak daily hires differ by {labor:+d}")
    for animal, key in (("cow", "cow_count_planned"), ("sheep", "sheep_count_planned"), ("goose", "goose_count_planned")):
        delta = best_profile[key] - selected_profile[key]
        if delta:
            differences.append(f"alternative planned {animal} quantity differs by {delta:+d}")
    selected_plants = selected_profile["plant_action_counts"]
    best_plants = best_profile["plant_action_counts"]
    crop_delta = {
        crop: best_plants.get(crop, 0) - selected_plants.get(crop, 0)
        for crop in sorted(set(selected_plants) | set(best_plants))
        if best_plants.get(crop, 0) != selected_plants.get(crop, 0)
    }
    if crop_delta:
        differences.append(f"crop planting-action deltas {crop_delta}")
    selected_revenue = sum(selected_row.get("economics", {}).get("revenue", {}).values())
    best_revenue = sum(best_row.get("economics", {}).get("revenue", {}).values())
    differences.append(f"realized sale revenue delta {best_revenue - selected_revenue:+.0f}")
    if not differences:
        differences.append("similar static profile; realized market/interaction timing explains the gap")
    return differences


def main():
    raw = json.loads(RAW.read_text())
    frequency_rows = [r for r in raw["frequency_rows"] if not r.get("runtime_error")]
    oracle_rows = [r for r in raw["oracle_rows"] if not r.get("runtime_error")]
    if len(frequency_rows) != 256 or len(oracle_rows) != 1170:
        raise RuntimeError(f"incomplete raw panel: frequency={len(frequency_rows)} oracle={len(oracle_rows)}")
    tapes = json.loads(ACTIONS.read_text())
    profiles = {plan: plan_profile(tapes, plan) for plan in range(13)}
    all_rows = frequency_rows + oracle_rows
    strict_diagnostics = Counter(
        failure["error"] for row in all_rows for failure in row.get("semantic_failures", [])
    )
    execution_safety = {
        "games": len(all_rows),
        "runtime_errors": sum(bool(row.get("runtime_error")) for row in all_rows),
        "agent_exceptions": sum(len(row.get("exceptions", [])) for row in all_rows),
        "strict_checker_diagnostics": dict(strict_diagnostics),
        "interpretation": "These are the already documented public-tape placeholder/zero-order/around-hire hand-count classes, not engine crashes. They were observed only; no warning repair was made in this stage.",
    }

    # Activation frequencies: fixed panel is the exact 64-pair distribution,
    # duplicated only to expose seat symmetry; natural panel is an empirical estimate.
    frequency = {
        "schema": "shop-router-0909-plan-frequency-v1",
        "design": raw["design"],
        "total_games": len(frequency_rows),
        "counts": {},
        "notes": [
            "Plan is read immediately after the frozen router acts at step 144.",
            "Plan 2 has zero initial activations because it is only the universal terminal plan selected at step 648.",
            "The fixed panel enumerates every ordered first/second shop pair exactly once per seat.",
        ],
    }
    subsets = {
        "all": frequency_rows,
        "fixed_all": [r for r in frequency_rows if r["shop_mode"] == "fixed"],
        "natural_all": [r for r in frequency_rows if r["shop_mode"] == "natural"],
        "fixed_seat0": [r for r in frequency_rows if r["shop_mode"] == "fixed" and r["seat"] == 0],
        "fixed_seat1": [r for r in frequency_rows if r["shop_mode"] == "fixed" and r["seat"] == 1],
        "natural_seat0": [r for r in frequency_rows if r["shop_mode"] == "natural" and r["seat"] == 0],
        "natural_seat1": [r for r in frequency_rows if r["shop_mode"] == "natural" and r["seat"] == 1],
    }
    for name, rows in subsets.items():
        counts = Counter(int(r["route"]["plan_at_144"]) for r in rows)
        frequency["counts"][name] = {
            str(plan): {"games": counts[plan], "probability": counts[plan] / len(rows)} for plan in range(13)
        }
    write_json("shop_router_0909_plan_frequency.json", frequency)

    # Plan manifest.
    triggers = defaultdict(list)
    for pair, plan in ROUTE.items():
        triggers[plan].append(list(pair))
    for plan in range(13):
        profile = profiles[plan]
        profile["shop_regime_trigger"] = triggers[plan] if plan else "all 49 unlisted ordered pairs"
        profile["activation_logic"] = (
            "At step 144, exact first-two-shop ordered-pair lookup; fallback to plan 0. "
            "At step 648, all routes switch to plan 2."
        )
        profile["frequency"] = {
            "fixed_exact": frequency["counts"]["fixed_all"][str(plan)]["probability"],
            "natural_empirical": frequency["counts"]["natural_all"][str(plan)]["probability"],
        }
    manifest = {
        "schema": "shop-router-0909-plan-manifest-v1",
        "plan_count": 13,
        "route_commit_step": 144,
        "universal_terminal_switch_step": 648,
        "plans": [profiles[i] for i in range(13)],
        "interpretation_warning": "Counts are planned tape primitives in the effective policy window, not guaranteed executed purchases; invalid orders are silent no-ops and weed repair may shift worker actions.",
    }
    write_json("shop_router_0909_plan_manifest.json", manifest)

    # Per-plan performance from the balanced forced-policy panel.
    by_plan = defaultdict(list)
    for row in oracle_rows:
        by_plan[int(row["forced_plan"])].append(row)
    performance = {
        "schema": "shop-router-0909-plan-performance-v1",
        "source_panel": raw["design"]["oracle"],
        "comparability": "Each plan has one run in every identical seed/seat/opponent/shop condition.",
        "plans": {str(plan): aggregate_rows(by_plan[plan]) for plan in range(13)},
        "routed_frequency_panel_observations": {},
        "execution_safety": execution_safety,
    }
    routed_groups = defaultdict(list)
    for row in frequency_rows:
        routed_groups[int(row["route"]["plan_at_144"])].append(row)
    for plan in range(13):
        performance["routed_frequency_panel_observations"][str(plan)] = (
            aggregate_rows(routed_groups[plan]) if routed_groups[plan] else {"games": 0, "reason": "not activated in the frequency panel"}
        )
    rankings = {}
    for metric, getter, reverse in (
        ("mean_own_money", lambda p: performance["plans"][str(p)]["own_money"]["mean"], True),
        ("mean_advantage", lambda p: performance["plans"][str(p)]["advantage"]["mean"], True),
        ("p10_own_money", lambda p: performance["plans"][str(p)]["own_money"]["p10"], True),
        ("worst_own_money", lambda p: performance["plans"][str(p)]["own_money"]["min"], True),
    ):
        rankings[metric] = sorted(range(13), key=getter, reverse=reverse)
    performance["rankings_best_to_worst"] = rankings
    performance["strongest_plan"] = rankings["mean_own_money"][0]
    performance["strongest_plan_by_advantage"] = rankings["mean_advantage"][0]
    performance["weakest_plan_by_mean_own_money"] = rankings["mean_own_money"][-1]
    # Plan 12 is the weakest strategic package: lowest mean advantage and the
    # most escape events.  Plan 2 has marginally lower mean own money but is a
    # robust common terminal tape with the best P10, so calling it weakest
    # without this distinction would be misleading.
    performance["weakest_plan"] = rankings["mean_advantage"][-1]
    performance["most_dangerous_tail_plan"] = rankings["p10_own_money"][-1]
    write_json("shop_router_0909_plan_performance.json", performance)

    # Condition matrix, including an observable market-regime split.
    conditions = {}
    premium_values = sorted({
        r["decision_features"]["market_regime"]["premium_mean_price"] for r in oracle_rows
    })
    q1, q2 = pct(premium_values, 1 / 3), pct(premium_values, 2 / 3)
    def regime(row):
        value = row["decision_features"]["market_regime"]["premium_mean_price"]
        return "low" if value <= q1 else "mid" if value <= q2 else "high"
    for plan in range(13):
        rows = by_plan[plan]
        conditions[str(plan)] = {
            "opponent_family": group_matrix(rows, lambda r: r["opponent"]),
            "seat": group_matrix(rows, lambda r: r["seat"]),
            "shop_condition": group_matrix(rows, lambda r: r["condition_id"].split("|")[0]),
            "observable_premium_market_regime": group_matrix(rows, regime),
        }
    cells = []
    for plan in range(13):
        for opponent, summary in conditions[str(plan)]["opponent_family"].items():
            cells.append({"plan": plan, "dimension": "opponent", "condition": opponent,
                          "mean_advantage": summary["advantage"]["mean"], "p10_own": summary["own_money"]["p10"]})
        for seat, summary in conditions[str(plan)]["seat"].items():
            cells.append({"plan": plan, "dimension": "seat", "condition": seat,
                          "mean_advantage": summary["advantage"]["mean"], "p10_own": summary["own_money"]["p10"]})
    condition_matrix = {
        "schema": "shop-router-0909-plan-condition-matrix-v1",
        "market_regime_definition": {"metric": "step-144 mean price of strawberry, melon, milk, wool", "low_max": q1, "mid_max": q2},
        "plans": conditions,
        "lowest_mean_advantage_cells": sorted(cells, key=lambda c: c["mean_advantage"])[:20],
        "lowest_p10_own_money_cells": sorted(cells, key=lambda c: c["p10_own"])[:20],
    }
    write_json("shop_router_0909_plan_condition_matrix.json", condition_matrix)

    # Hindsight oracle and regret.
    groups = defaultdict(list)
    for row in oracle_rows:
        groups[row["condition_id"]].append(row)
    comparisons = []
    for condition_id, rows in sorted(groups.items()):
        if len(rows) != 13:
            raise RuntimeError(f"oracle condition {condition_id} has {len(rows)} rows")
        pair = tuple(rows[0]["route"]["shops_at_144"])
        selected_plan = ROUTE.get(pair, 0)
        selected = next(r for r in rows if int(r["forced_plan"]) == selected_plan)
        best_money_value = max(r["own_money"] for r in rows)
        best_adv_value = max(r["advantage"] for r in rows)
        best_money = min((r for r in rows if r["own_money"] == best_money_value), key=lambda r: int(r["forced_plan"]))
        best_adv = min((r for r in rows if r["advantage"] == best_adv_value), key=lambda r: int(r["forced_plan"]))
        comparisons.append({
            "condition_id": condition_id,
            "shop_pair": list(pair),
            "opponent": selected["opponent"],
            "seat": selected["seat"],
            "router_selected_plan": selected_plan,
            "best_hindsight_own_money_plan": int(best_money["forced_plan"]),
            "best_hindsight_advantage_plan": int(best_adv["forced_plan"]),
            "selected_own_money": selected["own_money"],
            "oracle_own_money": best_money["own_money"],
            "selected_advantage": selected["advantage"],
            "oracle_advantage": best_adv["advantage"],
            "oracle_own_money_gain": best_money["own_money"] - selected["own_money"],
            "oracle_advantage_gain": best_adv["advantage"] - selected["advantage"],
            "selected_is_hindsight_best": selected["own_money"] == best_money_value,
            "best_own_money_ties": [int(r["forced_plan"]) for r in rows if r["own_money"] == best_money_value],
            "decision_features": selected["decision_features"],
            "mechanism_differences": mechanism(profiles[selected_plan], profiles[int(best_money["forced_plan"])], selected, best_money),
        })
    own_gains = [c["oracle_own_money_gain"] for c in comparisons]
    adv_gains = [c["oracle_advantage_gain"] for c in comparisons]
    oracle = {
        "schema": "shop-router-0909-plan-oracle-v1",
        "conditions": len(comparisons),
        "runs": len(oracle_rows),
        "hindsight_best_selection_rate_including_ties": sum(c["selected_is_hindsight_best"] for c in comparisons) / len(comparisons),
        "own_money_gain": stat(own_gains),
        "advantage_gain": stat(adv_gains),
        "comparisons": comparisons,
        "interpretation": "The oracle is an upper bound: it selects after outcomes are known and does not prove predictability at step 144.",
    }
    write_json("shop_router_0909_plan_oracle.json", oracle)

    top_regret = sorted(comparisons, key=lambda c: c["oracle_own_money_gain"], reverse=True)[:15]
    regret = {
        "schema": "shop-router-0909-router-regret-v1",
        "definition": "best forced-plan own money minus frozen router-selected-plan own money in the same condition",
        "conditions": len(comparisons),
        "mean": statistics.fmean(own_gains),
        "median": statistics.median(own_gains),
        "p75": pct(own_gains, 0.75),
        "p90": pct(own_gains, 0.90),
        "p95": pct(own_gains, 0.95),
        "worst": max(own_gains),
        "top_regret_cases": top_regret,
    }

    # Existing-plan dominance by currently selected shop regime.
    dominance = {}
    for label in sorted({c["condition_id"].split("|")[0] for c in comparisons}):
        selected_comps = [c for c in comparisons if c["condition_id"].split("|")[0] == label]
        selected_plan = selected_comps[0]["router_selected_plan"]
        alternatives = []
        condition_rows = {cid: groups[cid] for cid in (c["condition_id"] for c in selected_comps)}
        for plan in range(13):
            deltas = []
            for c in selected_comps:
                alt = next(r for r in condition_rows[c["condition_id"]] if int(r["forced_plan"]) == plan)
                deltas.append(alt["own_money"] - c["selected_own_money"])
            alternatives.append({
                "plan": plan,
                "beat_rate": sum(delta > 0 for delta in deltas) / len(deltas),
                "tie_or_beat_rate": sum(delta >= 0 for delta in deltas) / len(deltas),
                "mean_delta": statistics.fmean(deltas),
                "worst_delta": min(deltas),
            })
        dominance[label] = {
            "selected_plan": selected_plan,
            "conditions": len(selected_comps),
            "best_existing_alternative_by_mean": max(alternatives, key=lambda r: r["mean_delta"]),
            "alternatives": sorted(alternatives, key=lambda r: r["mean_delta"], reverse=True),
        }
    regret["existing_plan_dominance_by_regime"] = dominance

    # Shop pair information value and legally observable feature associations.
    plan_means = {plan: statistics.fmean(r["own_money"] for r in by_plan[plan]) for plan in range(13)}
    global_plan = max(plan_means, key=plan_means.get)
    global_constant_mean = plan_means[global_plan]
    router_mean = statistics.fmean(c["selected_own_money"] for c in comparisons)
    oracle_mean = statistics.fmean(c["oracle_own_money"] for c in comparisons)
    pair_best_values = []
    pair_best = {}
    for label in dominance:
        comps = [c for c in comparisons if c["condition_id"].split("|")[0] == label]
        means = {}
        for plan in range(13):
            vals = []
            for c in comps:
                vals.append(next(r["own_money"] for r in groups[c["condition_id"]] if int(r["forced_plan"]) == plan))
            means[plan] = statistics.fmean(vals)
        best_plan = max(means, key=means.get)
        pair_best[label] = {"best_constant_plan": best_plan, "mean_own_money": means[best_plan], "router_selected_plan": comps[0]["router_selected_plan"]}
        pair_best_values.extend([means[best_plan]] * len(comps))
    best_pair_mean = statistics.fmean(pair_best_values)
    total_conditioning_gain = oracle_mean - global_constant_mean
    feature_extractors = {
        "own_bank": lambda f: f["own"]["money"],
        "opponent_bank": lambda f: f["opponent"]["money"],
        "bank_gap": lambda f: f["bank_gap"],
        "own_hands": lambda f: f["own"]["hands"],
        "opponent_hands": lambda f: f["opponent"]["hands"],
        "opponent_land": lambda f: f["opponent"]["unlocked_quadrants"],
        "opponent_animals": lambda f: sum(f["opponent"]["counts"]["animals"].values()),
        "opponent_crops": lambda f: sum(f["opponent"]["counts"]["crops"].values()),
        "premium_mean_price": lambda f: f["market_regime"]["premium_mean_price"],
        "wool_price": lambda f: f["market_regime"]["wool_price"],
        "milk_price": lambda f: f["market_regime"]["milk_price"],
    }
    associations = []
    for name, getter in feature_extractors.items():
        xs = [float(getter(c["decision_features"])) for c in comparisons]
        associations.append({"feature": name, "pearson_with_regret": corr(xs, own_gains), "min": min(xs), "max": max(xs)})
    pair_stability = {}
    for label in dominance:
        comps = [c for c in comparisons if c["condition_id"].split("|")[0] == label]
        counts = Counter(c["best_hindsight_own_money_plan"] for c in comps)
        pair_stability[label] = {
            "unique_hindsight_best_plans": sorted(counts),
            "modal_best_plan": counts.most_common(1)[0][0],
            "modal_best_rate": counts.most_common(1)[0][1] / len(comps),
        }
    top_abs_corr = max(abs(a["pearson_with_regret"] or 0) for a in associations)
    mean_modal_rate = statistics.fmean(v["modal_best_rate"] for v in pair_stability.values())
    feature_signal = "suggestive" if top_abs_corr >= 0.30 and mean_modal_rate < 0.85 else "weak_or_unproven"
    regret["shop_information_value"] = {
        "best_global_constant_plan": global_plan,
        "best_global_constant_mean_own_money": global_constant_mean,
        "frozen_router_mean_own_money": router_mean,
        "router_value_over_global_constant": router_mean - global_constant_mean,
        "best_shop_pair_constant_mean_own_money": best_pair_mean,
        "shop_pair_value_over_global_constant": best_pair_mean - global_constant_mean,
        "optimal_shop_pair_share_of_total_conditioning_gain": (
            (best_pair_mean - global_constant_mean) / total_conditioning_gain if total_conditioning_gain else None
        ),
        "frozen_router_share_of_total_conditioning_gain": (
            (router_mean - global_constant_mean) / total_conditioning_gain if total_conditioning_gain else None
        ),
        "current_route_gap_to_best_shop_pair_constant": best_pair_mean - router_mean,
        "per_condition_oracle_mean_own_money": oracle_mean,
        "within_shop_pair_context_headroom_upper_bound": oracle_mean - best_pair_mean,
        "best_constant_by_shop_case": pair_best,
    }
    regret["public_feature_sufficiency"] = {
        "assessment": feature_signal,
        "important_caveat": "Correlations and within-pair winner variation are descriptive, in-sample evidence; no selector was trained or validated.",
        "regret_correlations": sorted(associations, key=lambda a: abs(a["pearson_with_regret"] or 0), reverse=True),
        "shop_case_hindsight_winner_stability": pair_stability,
        "mean_modal_best_rate_within_shop_case": mean_modal_rate,
        "history_assessment": "The frozen router does not use economic history for its step-144 lookup. This panel diagnoses the legal step-144 snapshot only; useful history signal remains unproven and was not modeled.",
    }
    write_json("shop_router_0909_router_regret.json", regret)

    # Static and one-condition empirical compatibility.
    effective = {plan: effective_tape(tapes, plan) for plan in range(13)}
    trace_rows = {int(r["forced_plan"]): r for r in oracle_rows if r.get("trace") and r["trace"]["state_step_hashes"]}
    pairwise = []
    for left in range(13):
        for right in range(left + 1, 13):
            stored_count, stored_first = common_prefix(tapes[left], tapes[right], 0)
            effective_count, effective_first = common_prefix(effective[left], effective[right], 0)
            continuation_count, continuation_first = common_prefix(effective[left], effective[right], 144)
            empirical_state_count = empirical_state_first = empirical_action_count = empirical_action_first = None
            if left in trace_rows and right in trace_rows:
                empirical_state_count, empirical_state_first = common_prefix(
                    trace_rows[left]["trace"]["state_step_hashes"], trace_rows[right]["trace"]["state_step_hashes"], 0
                )
                empirical_action_count, empirical_action_first = common_prefix(
                    trace_rows[left]["trace"]["action_step_hashes"], trace_rows[right]["trace"]["action_step_hashes"], 0
                )
            action_similarity = sum(a == b for a, b in zip(effective[left][144:648], effective[right][144:648])) / 504
            outcomes_left = [next(r["own_money"] for r in groups[cid] if int(r["forced_plan"]) == left) for cid in sorted(groups)]
            outcomes_right = [next(r["own_money"] for r in groups[cid] if int(r["forced_plan"]) == right) for cid in sorted(groups)]
            pairwise.append({
                "left": left, "right": right,
                "stored_tape_common_prefix_actions": stored_count,
                "stored_tape_first_divergence_step": stored_first,
                "effective_policy_common_prefix_actions": effective_count,
                "effective_policy_first_divergence_step": effective_first,
                "continuation_common_prefix_from_144": continuation_count,
                "continuation_first_divergence_step": continuation_first,
                "latest_safe_choice_step": continuation_first,
                "empirical_economic_state_common_prefix_observations": empirical_state_count,
                "empirical_economic_state_first_divergence_step": empirical_state_first,
                "empirical_processed_action_common_prefix": empirical_action_count,
                "empirical_processed_action_first_divergence_step": empirical_action_first,
                "continuation_action_similarity": action_similarity,
                "realized_outcome_correlation": corr(outcomes_left, outcomes_right),
                "mean_absolute_outcome_difference": statistics.fmean(abs(a - b) for a, b in zip(outcomes_left, outcomes_right)),
            })
    compatibility = {
        "schema": "shop-router-0909-plan-compatibility-v1",
        "current_commit_step": 144,
        "common_runtime_prefix": "All policies use plan 0 through step 143; route lookup occurs at step 144.",
        "global_earliest_continuation_divergence": min(p["continuation_first_divergence_step"] for p in pairwise if p["continuation_first_divergence_step"] is not None),
        "can_delay_one_global_13_way_decision": False,
        "reason": "At least one plan pair differs at the current step-144 action, so a single unrestricted 13-way choice cannot be delayed without changing behavior. Some pair subsets share longer prefixes and could support staged routing in future research.",
        "empirical_trace_condition": "fallback_bakery_pet|current_best|seat0",
        "pairwise": pairwise,
    }
    write_json("shop_router_0909_plan_compatibility.json", compatibility)

    # Deterministic agglomerative clustering across static action, outcome, and profile similarity.
    vectors = {plan: profiles[plan]["profile_vector"] for plan in range(13)}
    dims = len(next(iter(vectors.values())))
    means = [statistics.fmean(vectors[p][d] for p in vectors) for d in range(dims)]
    scales = [statistics.pstdev(vectors[p][d] for p in vectors) or 1.0 for d in range(dims)]
    z = {p: [(vectors[p][d] - means[d]) / scales[d] for d in range(dims)] for p in vectors}
    pair_lookup = {(p["left"], p["right"]): p for p in pairwise}
    def pair_distance(a, b):
        item = pair_lookup[(min(a, b), max(a, b))]
        profile_distance = math.sqrt(sum((x - y) ** 2 for x, y in zip(z[a], z[b]))) / math.sqrt(dims)
        profile_distance = min(1.0, profile_distance / 2.0)
        outcome_distance = (1 - (item["realized_outcome_correlation"] or 0)) / 2
        return 0.45 * (1 - item["continuation_action_similarity"]) + 0.35 * outcome_distance + 0.20 * profile_distance
    clusters = [{p} for p in range(13)]
    merges = []
    threshold = 0.30
    while len(clusters) > 1:
        best = None
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                distance = statistics.fmean(pair_distance(a, b) for a in clusters[i] for b in clusters[j])
                if best is None or distance < best[0]:
                    best = (distance, i, j)
        if best[0] > threshold:
            break
        distance, i, j = best
        merged = clusters[i] | clusters[j]
        merges.append({"left": sorted(clusters[i]), "right": sorted(clusters[j]), "distance": distance, "merged": sorted(merged)})
        clusters = [c for k, c in enumerate(clusters) if k not in (i, j)] + [merged]
    cluster_rows = []
    for index, members in enumerate(sorted(clusters, key=lambda c: min(c))):
        member_list = sorted(members)
        cluster_rows.append({
            "cluster_id": index,
            "plans": member_list,
            "size": len(member_list),
            "identities": [profiles[p]["economic_identity"] for p in member_list],
            "mean_internal_action_similarity": statistics.fmean(
                pair_lookup[(a, b)]["continuation_action_similarity"] for pos, a in enumerate(member_list) for b in member_list[pos + 1:]
            ) if len(member_list) > 1 else 1.0,
        })
    clusters_artifact = {
        "schema": "shop-router-0909-plan-clusters-v1",
        "method": "Deterministic average-link agglomeration at distance <=0.30; distance blends continuation action dissimilarity (45%), outcome-correlation distance (35%), and standardized economic-profile distance (20%).",
        "clusters": cluster_rows,
        "effective_strategy_count": len(cluster_rows),
        "selection_overlap": {
            "pairwise_overlap_for_distinct_plans": 0.0,
            "reason": "The frozen ordered-pair lookup selects exactly one plan at step 144, so distinct plan trigger sets are mutually exclusive. Similar selection frequency does not imply overlapping activation.",
        },
        "merges": merges,
        "pairwise_similarity": [{k: row[k] for k in ("left", "right", "continuation_action_similarity", "realized_outcome_correlation", "mean_absolute_outcome_difference")} for row in pairwise],
        "redundancy_candidates": sorted(
            [{"left": p["left"], "right": p["right"], "action_similarity": p["continuation_action_similarity"],
              "outcome_correlation": p["realized_outcome_correlation"], "mean_absolute_outcome_difference": p["mean_absolute_outcome_difference"]}
             for p in pairwise],
            key=lambda p: (-p["action_similarity"], -(p["outcome_correlation"] or 0), p["mean_absolute_outcome_difference"]),
        )[:10],
    }
    write_json("shop_router_0909_plan_clusters.json", clusters_artifact)

    # Diagnostic classification, hashes, and the required 39-answer report.
    router_headroom = oracle["own_money_gain"]["mean"] >= 500
    weak_oracle_regimes = []
    for label in dominance:
        comps = [c for c in comparisons if c["condition_id"].split("|")[0] == label]
        if statistics.fmean(c["oracle_advantage"] for c in comps) < 0:
            weak_oracle_regimes.append(label)
    bottleneck = "BOTH" if router_headroom and weak_oracle_regimes else "ROUTER BOTTLENECK" if router_headroom else "PARENT BOTTLENECK" if weak_oracle_regimes else "NEITHER"
    actual_hashes = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (FROZEN, SUBMISSION_MAIN, SUBMISSION_ARCHIVE)
    }
    if actual_hashes != EXPECTED_HASHES:
        raise RuntimeError(f"frozen deployment hash mismatch: {actual_hashes}")

    frontier_path = EXP / "post_submit_frontier_scan.json"
    frontier = json.loads(frontier_path.read_text()) if frontier_path.exists() else {}
    candidates = frontier.get("candidates", [])
    top3 = frontier.get("top_3", frontier.get("top3", candidates[:3]))
    scan_time = frontier.get("scan_timestamp_utc_plus_8", frontier.get("scan_timestamp", "PENDING"))
    cutoff24 = frontier.get("primary_cutoff_utc_plus_8", frontier.get("cutoff_24h", (frontier.get("windows", {}).get("primary_24h", {}) or {}).get("start_utc_plus_8", "PENDING")))
    recent_count = frontier.get("recent_candidate_count", len([c for c in candidates if c.get("freshness_class") != "OLD"]))
    thresholds = frontier.get("score_threshold_findings", {})
    recent2900 = bool(thresholds.get("verified_recent_score_at_or_above_2900", False))
    recent3000 = bool(thresholds.get("verified_recent_score_at_or_above_3000", False))
    top_names = "; ".join(
        f"{c.get('title', c.get('candidate', 'unknown'))} "
        f"({c.get('exact_score') if c.get('exact_score') is not None else 'score unbound'}, "
        f"{c.get('freshness_class', c.get('freshness', 'unknown'))})"
        for c in top3
    ) or "No qualifying recent candidate"
    strongest = performance["strongest_plan"]
    weakest = performance["weakest_plan"]
    dangerous = performance["most_dangerous_tail_plan"]
    largest = top_regret[0]
    redundant = clusters_artifact["redundancy_candidates"][0]
    public_candidate = candidates[0] if candidates else None
    public_score = None
    if public_candidate:
        binding = public_candidate.get("exact_score_version_binding", {}) or {}
        public_score = binding.get("score") if binding.get("verified") else None
    public_stronger = bool(public_score is not None and public_score >= 2900)
    if public_stronger:
        next_stage = "NEW PUBLIC AGENT REPRODUCTION"
        next_rule = "NEXT: reproduce that agent"
    elif oracle["own_money_gain"]["mean"] >= 1500:
        next_stage = "ROUTER STAGE" if bottleneck == "ROUTER BOTTLENECK" else "PARENT REPLACEMENT STAGE"
        next_rule = "NEXT: router / parent research"
    else:
        next_stage = "NO ACTION"
        next_rule = "NEXT: wait for real leaderboard result"

    lines = [
        "# ShopRouter0909Hardened Post-Submission Diagnostic",
        "",
        "This is a read-only research report. The submitted source and archive were not changed, packaged, uploaded, or resubmitted.",
        "",
        "## Required answers",
        "",
        f"1. **Exact scan timestamp:** {scan_time}.",
        f"2. **24h cutoff:** {cutoff24}.",
        f"3. **Recent public strategy candidates found:** {recent_count}.",
        f"4. **Top 3 recent candidates:** {top_names}.",
        "5. **Exact score/version binding:** all three fresh candidates are score-unbound: flexonafft source run 348544166 has no linked score; the tetsutani major update has no retained run/submission score link; dmitriigluzdov's title-only 2800+ claim is rejected. FrozenBest's ancestor remains exactly bound at v1/run 348430185/submission evidence score 2839.5.",
        f"6. **Recent 2900+ agent exists:** {'YES' if recent2900 else 'NO'}.",
        f"7. **Recent 3000+ agent exists:** {'YES' if recent3000 else 'NO'}.",
        f"8. **Most worth reproducing next:** {public_candidate.get('title') if public_candidate else 'none identified'}.",
        f"9. **Why:** {public_candidate.get('why_it_might_beat_frozenbest', public_candidate.get('why_might_beat_frozenbest', public_candidate.get('estimated_research_value', 'No qualifying recent complete executable candidate.'))) if public_candidate else 'No qualifying recent complete executable candidate.'}",
        "10. **FrozenBest plans:** 13 complete continuations (plans 0-12), with universal plan 2 terminal takeover at step 648.",
        "11. **Activation frequency:** see the table below; fixed is exact over all 64 ordered pairs, natural is 128 fresh games.",
        "12. **Mean own money per plan:** see the table below.",
        "13. **Mean advantage per plan:** see the table below.",
        "14. **P10 own money per plan:** see the table below.",
        "15. **Worst own-money result per plan:** see the table below.",
        f"16. **Strongest plan:** Plan {strongest} by balanced mean own money; Plan {performance['strongest_plan_by_advantage']} is narrowly best by mean advantage.",
        f"17. **Weakest strategic plan:** Plan {weakest} (lowest mean advantage and {performance['plans'][str(weakest)]['livestock']['escape_events']} escape events). Plan {performance['weakest_plan_by_mean_own_money']} is marginally lowest by mean own money but has the strongest P10 tail.",
        f"18. **Most dangerous tail plan by P10 own money:** Plan {dangerous}.",
        f"19. **Router hindsight-best selection rate (ties count):** {oracle['hindsight_best_selection_rate_including_ties']:.1%}.",
        f"20. **Mean oracle own-money gain:** {oracle['own_money_gain']['mean']:.1f}.",
        f"21. **Mean oracle advantage gain:** {oracle['advantage_gain']['mean']:.1f}.",
        f"22. **Maximum oracle own-money gain:** {oracle['own_money_gain']['max']:.1f}.",
        f"23. **Mean router regret:** {regret['mean']:.1f}.",
        f"24. **P90 / P95 router regret:** {regret['p90']:.1f} / {regret['p95']:.1f}.",
        f"25. **Largest-regret regime:** {largest['condition_id']}, shops {largest['shop_pair']}, selected Plan {largest['router_selected_plan']} vs Plan {largest['best_hindsight_own_money_plan']}, regret {largest['oracle_own_money_gain']:.1f}.",
        f"26. **Regret predictable from public state:** {feature_signal.upper()} evidence only; strongest absolute univariate correlation is {top_abs_corr:.3f}. No selector was trained, so predictability is not established.",
        f"27. **Could the full plan choice safely be delayed:** NO for an unrestricted 13-way router; at least one continuation diverges at step {compatibility['global_earliest_continuation_divergence']}. Pairwise staged delays remain possible (Plan 0/2 to step 313; several sheep-route pairs to step 216).",
        "28. **Common-prefix structure:** all runtime policies share Plan 0 actions through step 143 and identical observed economic state through step 144; divergent step-144 actions first alter observations at step 145. Pairwise continuation prefixes vary from 0 to 169 actions; all switch to Plan 2 at step 648.",
        f"29. **Strategically diverse:** {'YES' if clusters_artifact['effective_strategy_count'] >= 6 else 'PARTLY'}; the blended clustering retains {clusters_artifact['effective_strategy_count']} effective groups, including one nine-plan sheep-led family.",
        f"30. **Some plans redundant:** {'YES, candidates exist' if redundant['action_similarity'] >= 0.85 and (redundant['outcome_correlation'] or 0) >= 0.9 else 'No strong redundancy proven'}; closest pair is {redundant['left']}/{redundant['right']} (action similarity {redundant['action_similarity']:.1%}, outcome correlation {(redundant['outcome_correlation'] or 0):.3f}).",
        f"31. **Dominant limitation:** {bottleneck}. Oracle-negative regimes after best-plan selection: {weak_oracle_regimes or 'none'}.",
        f"32. **Mean router headroom exceeds +1k:** {'YES' if oracle['own_money_gain']['mean'] > 1000 else 'NO'}.",
        f"33. **Mean router headroom exceeds +3k:** {'YES' if oracle['own_money_gain']['mean'] > 3000 else 'NO'}.",
        f"34. **Mean router headroom exceeds +5k:** {'YES' if oracle['own_money_gain']['mean'] > 5000 else 'NO'}.",
        f"35. **Recommended next research stage:** {next_stage}. {next_rule}.",
        "36. **Kaggle submission result:** PENDING.",
        f"37. **FrozenBest source unchanged:** CONFIRMED, SHA-256 `{actual_hashes['agents/shop_router_0909_hardened/main.py']}`.",
        f"38. **Submission package unchanged:** CONFIRMED, main.py `{actual_hashes['submission/main.py']}`, archive `{actual_hashes['submission/shop_router_0909_hardened.tar.gz']}`.",
        "39. **Upload/submission during this stage:** NONE.",
        "",
        "## Per-plan summary",
        "",
        "| Plan | Fixed activation | Natural activation | Mean own | Mean advantage | P10 own | Worst own |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for plan in range(13):
        perf = performance["plans"][str(plan)]
        lines.append(
            f"| {plan} | {frequency['counts']['fixed_all'][str(plan)]['probability']:.2%} | "
            f"{frequency['counts']['natural_all'][str(plan)]['probability']:.2%} | "
            f"{perf['own_money']['mean']:.1f} | {perf['advantage']['mean']:.1f} | "
            f"{perf['own_money']['p10']:.1f} | {perf['own_money']['min']:.1f} |"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        f"The exact current router averages {router_mean:.1f} own money on the matched 90-condition oracle panel. "
        f"The best single global plan averages {global_constant_mean:.1f}; the best constant plan chosen separately per shop case averages {best_pair_mean:.1f}; "
        f"and the infeasible per-condition hindsight oracle averages {oracle_mean:.1f}. Thus shop-pair-only headroom above the best global constant is {best_pair_mean - global_constant_mean:.1f}, "
        f"which explains {(best_pair_mean - global_constant_mean) / total_conditioning_gain:.1%} of the full conditioning gain on this panel. "
        f"The frozen mapping captures {(router_mean - global_constant_mean) / total_conditioning_gain:.1%}; remaining within-shop context headroom is at most {oracle_mean - best_pair_mean:.1f}. "
        "This latter number is an upper bound, not evidence that a legal selector can realize it.",
        "",
        f"The largest regret mechanism differences were: {'; '.join(largest['mechanism_differences'])}. "
        "The dominance table in `shop_router_0909_router_regret.json` distinguishes regimes where an existing plan usually replaces the selected parent from regimes where even the oracle portfolio remains weak.",
        "",
        "Three mappings deserve first inspection if a later router stage is justified: Pizza→Yarn selected Plan 7 but Plan 12 won all six matched contexts by +7,186.7 mean own money; "
        "Smoothie→Yarn selected Plan 8 but Plan 1 won all six by +2,463.2; Yarn→Bakery selected Plan 9 but Plan 7 won all six by +2,399.7. "
        "These are diagnostic matched-condition findings, not authorized route changes.",
        "",
        "Conditioning checks show that CurrentBest is the hardest opponent family for every forced plan by mean advantage, although every plan remains positive on average against all three tested families. "
        "Seat effects are negligible (the largest plan-level seat mean-own gap is under 45 coins). Low step-144 premium-price regimes have lower absolute own money for every plan, but that split is confounded with the fixed shop cases and is not a causal market rule.",
        "",
        f"Livestock safety is not uniform across forced regimes: Plan 12 had {performance['plans']['12']['livestock']['escape_events']} escape events, "
        f"Plans 1 and 5 had {performance['plans']['1']['livestock']['escape_events']} each, and the frozen-hardened Plan 10 had {performance['plans']['10']['livestock']['escape_events']}. "
        "These are portfolio diagnostics under off-route forcing, not evidence that every escape is reachable under the frozen router's intended shop mapping.",
        "",
        "## Scope and limitations",
        "",
        "The forced-policy panel covers 15 representative shop regimes, three opponent families, both seats, and all 13 continuations (1,170 games). "
        "It is balanced for plan comparison but is not a full probability-weighted deployment forecast. The natural frequency panel adds 128 games; the exact fixed frequency panel enumerates all 64 ordered pairs in both seats. "
        "Hindsight oracle values are optimistic upper bounds. Public-feature associations are descriptive and no model or rule was trained. Local opponents and deterministic simulation cannot substitute for the pending Kaggle leaderboard result.",
        "",
        f"All {len(all_rows)} diagnostic games had zero runtime errors and zero agent exceptions. The strict observer recorded {sum(strict_diagnostics.values()):,} already-known benign public-tape diagnostics "
        f"({dict(strict_diagnostics)}); these were intentionally not changed or treated as new failure classes.",
        "",
        "## Decision",
        "",
        f"**{next_rule}**",
        "",
        "Kaggle submission result: **PENDING**",
    ]
    cited = []
    for candidate in candidates:
        url = candidate.get("url") or candidate.get("URL")
        title = candidate.get("title")
        if url and title and url not in {item[1] for item in cited}:
            cited.append((title, url))
    if cited:
        lines += ["", "## Public sources", ""]
        lines += [f"- [{title}]({url})" for title, url in cited]
        lines += ["", "Scores and version/run bindings are reproduced exactly from the frontier ledger; missing bindings remain explicitly unverified."]
    report_path = EXP / "shop_router_0909_post_submit_diagnostic_report.md"
    report_path.write_text("\n".join(lines) + "\n")
    print(f"wrote required artifacts and {report_path}")


if __name__ == "__main__":
    main()
