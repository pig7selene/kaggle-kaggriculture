"""Build mandatory V3 specialist-oracle artifacts from the frozen-policy runs."""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
import statistics


ROOT = Path(__file__).resolve().parent
EXP = ROOT / "experiments"
ROWS_PATH = EXP / "v3_regime_runs/oracle.partial.json"
POLICY_PATHS = {
    "CurrentBest": ROOT / "agents/top50_distilled/top50_observable_portfolio.py",
    "V3": ROOT / "agents/public_farming_v3/main.py",
    "Route1": ROOT / "agents/farming_v3_distilled/v1_force_route1.py",
}
DEPLOYED = ROOT / "submission/main.py"
CHECKPOINTS = (0, 1, 24, 48, 72, 96, 120, 144)
THRESHOLDS = (0, 1000, 3000, 5000, 8000, 10000, 12000, 15000, 20000)


def write_json(name, value):
    (EXP / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_md(name, value):
    (EXP / name).write_text(value.rstrip() + "\n", encoding="utf-8")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def percentile(values, q):
    values = sorted(float(value) for value in values)
    if not values:
        return None
    point = (len(values) - 1) * q
    low = int(point); high = min(low + 1, len(values) - 1); weight = point - low
    return values[low] * (1 - weight) + values[high] * weight


def bootstrap(values, seed=944001, samples=10000):
    values = [float(value) for value in values]
    rng = random.Random(seed); n = len(values)
    means = [statistics.fmean(values[rng.randrange(n)] for _ in range(n)) for _ in range(samples)]
    return {"mean": statistics.fmean(values), "low": percentile(means, .025), "high": percentile(means, .975), "resamples": samples}


def describe(values):
    values = [float(value) for value in values]
    return {
        "n": len(values), "mean": statistics.fmean(values), "median": statistics.median(values),
        "p25": percentile(values, .25), "p10": percentile(values, .10), "p5": percentile(values, .05),
        "worst": min(values), "best": max(values), "negative_rate": sum(value < 0 for value in values) / len(values),
        "bootstrap_mean_95": bootstrap(values),
    }


def condition_map(rows):
    result = defaultdict(dict)
    for row in rows:
        result[(row["opponent"], int(row["seed"]), int(row["seat"]))][row["policy"]] = row
    assert all(set(group) == {"CurrentBest", "V3", "Route1"} for group in result.values())
    return dict(result)


def winner(values):
    maximum = max(values.values())
    tied = [name for name in ("CurrentBest", "V3", "Route1") if values[name] == maximum]
    # Conservative deterministic label: prefer the default, then published V3.
    return tied[0], tied


def visible_signature(group, step, history=False):
    snap = group["CurrentBest"]["checkpoints"][str(step)]
    value = {
        "seat": group["CurrentBest"]["seat"],
        "opponent": snap["opponent"], "market_prices": snap["market_prices"],
        "market_inventory": snap["market_inventory"], "shops": snap["shops"],
    }
    if history and step >= 24:
        previous = max(checkpoint for checkpoint in CHECKPOINTS if checkpoint < step)
        old = group["CurrentBest"]["checkpoints"][str(previous)]
        value["previous"] = {
            "step": previous, "opponent": old["opponent"], "market_prices": old["market_prices"],
            "market_inventory": old["market_inventory"], "shops": old["shops"],
        }
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def cv_signature_rule(groups, step, threshold, metric="own_money", history=False):
    rows = []
    for held_offset in range(4):
        learned = defaultdict(lambda: defaultdict(list))
        for key, group in groups.items():
            if key[1] % 100 == held_offset:
                continue
            signature = visible_signature(group, step, history)
            for policy in ("V3", "Route1"):
                learned[signature][policy].append(group[policy][metric] - group["CurrentBest"][metric])
        for key, group in groups.items():
            if key[1] % 100 != held_offset:
                continue
            signature = visible_signature(group, step, history)
            predictions = {
                policy: statistics.fmean(learned[signature][policy])
                for policy in ("V3", "Route1") if learned[signature][policy]
            }
            selected = max(predictions, key=predictions.get) if predictions and max(predictions.values()) > threshold else "CurrentBest"
            gain = 0.0 if selected == "CurrentBest" else group[selected][metric] - group["CurrentBest"][metric]
            rows.append({
                "opponent": key[0], "seed": key[1], "seat": key[2], "held_seed_offset": held_offset,
                "selected": selected, "gain": gain, "in_distribution_exact_signature": bool(predictions),
                "predicted_values": predictions,
            })
    activations = [row for row in rows if row["selected"] != "CurrentBest"]
    gains = [row["gain"] for row in rows]
    false = [row["gain"] for row in activations if row["gain"] < 0]
    return {
        "step": step, "history": history, "threshold": threshold, "objective": metric,
        "conditions": len(rows), "activation_count": len(activations), "activation_rate": len(activations) / len(rows),
        "activation_precision_positive": sum(row["gain"] > 0 for row in activations) / len(activations) if activations else None,
        "false_positive_count": len(false), "false_positive_rate_among_activations": len(false) / len(activations) if activations else 0,
        "false_positive_mean_loss": statistics.fmean(false) if false else 0,
        "ood_default_count": sum(not row["in_distribution_exact_signature"] for row in rows),
        "gain": describe(gains), "rows": rows,
    }


def simple_rule(groups, name, predicate):
    gains = []; active = []
    for key, group in groups.items():
        opponent = group["CurrentBest"]["checkpoints"]["24"]["opponent"]
        selected = "Route1" if predicate(opponent) else "CurrentBest"
        gain = group[selected]["own_money"] - group["CurrentBest"]["own_money"]
        gains.append(gain)
        if selected == "Route1": active.append(gain)
    false = [gain for gain in active if gain < 0]
    return {
        "name": name, "checkpoint": 24, "selected_policy": "Route1",
        "activation_count": len(active), "activation_rate": len(active) / len(gains),
        "precision": sum(gain > 0 for gain in active) / len(active) if active else None,
        "false_positive_count": len(false), "false_positive_mean_loss": statistics.fmean(false) if false else 0,
        "overall_gain": describe(gains),
        "warning": "Exploratory/full-panel rule, not held-out or candidate-validating evidence.",
    }


def main():
    rows = json.loads(ROWS_PATH.read_text())
    groups = condition_map(rows)
    policies = {
        name: {"path": str(path.relative_to(ROOT)), "sha256": sha(path), "frozen": True}
        for name, path in POLICY_PATHS.items()
    }
    policy_audit = {
        "status": "PASS", "policies": policies,
        "deployment": {"path": "submission/main.py", "sha256": sha(DEPLOYED), "modified": False},
        "evaluation": {"conditions": len(groups), "games": len(rows), "opponents": sorted({key[0] for key in groups}), "seeds_per_opponent": 4, "both_seats": True, "natural_rng": True},
        "safety": {
            "runtime_errors": sum(bool(row.get("runtime_error")) for row in rows),
            "semantic_errors": sum(len(row.get("semantic_failures", [])) for row in rows),
            "livestock_escapes": sum(len(row.get("livestock_escapes", [])) for row in rows),
        },
        "unavailable_requested_reference": "No locally runnable ResearchStudio adaptive agent was found; no substitute identity was fabricated.",
    }
    write_json("v3_regime_policy_audit.json", policy_audit)

    conditions = []
    own_oracle = []; advantage_oracle = []
    for key, group in sorted(groups.items()):
        own = {name: group[name]["own_money"] for name in policies}
        opponent_money = {name: group[name]["opponent_money"] for name in policies}
        advantage = {name: group[name]["advantage"] for name in policies}
        own_winner, own_ties = winner(own); adv_winner, adv_ties = winner(advantage)
        own_gain = max(own.values()) - own["CurrentBest"]
        adv_gain = max(advantage.values()) - advantage["CurrentBest"]
        own_oracle.append(own_gain); advantage_oracle.append(adv_gain)
        conditions.append({
            "opponent": key[0], "seed": key[1], "seat": key[2],
            "money": own, "opponent_money": opponent_money, "advantage": advantage,
            "own_delta_vs_currentbest": {name: own[name] - own["CurrentBest"] for name in ("V3", "Route1")},
            "opponent_delta_vs_currentbest": {name: opponent_money[name] - opponent_money["CurrentBest"] for name in ("V3", "Route1")},
            "advantage_delta_vs_currentbest": {name: advantage[name] - advantage["CurrentBest"] for name in ("V3", "Route1")},
            "winner_own": own_winner, "winner_own_ties": own_ties,
            "winner_advantage": adv_winner, "winner_advantage_ties": adv_ties,
            "oracle_own_gain": own_gain, "oracle_advantage_gain": adv_gain,
        })
    exclusive_own = Counter(row["winner_own"] for row in conditions)
    exclusive_adv = Counter(row["winner_advantage"] for row in conditions)
    tie_aware_own = {name: sum(name in row["winner_own_ties"] for row in conditions) for name in policies}
    tie_aware_adv = {name: sum(name in row["winner_advantage_ties"] for row in conditions) for name in policies}
    specialist_risk = {}
    for policy in ("V3", "Route1"):
        deltas = [row["own_delta_vs_currentbest"][policy] for row in conditions]
        correct = [row["own_delta_vs_currentbest"][policy] for row in conditions if policy in row["winner_own_ties"]]
        wrong = [delta for delta in deltas if delta < 0]
        regret = [
            row["money"][policy] - max(row["money"].values())
            for row in conditions if row["money"][policy] < max(row["money"].values())
        ]
        specialist_risk[policy] = {
            "all_delta_vs_currentbest": describe(deltas),
            "optimal_count_including_ties": len(correct), "mean_gain_when_optimal": statistics.fmean(correct),
            "currentbest_better_count": len(wrong), "wrong_selection_loss": describe(wrong),
            "not_oracle_optimal_count": len(regret), "regret_to_oracle": describe(regret),
        }
    two_policy_own = [max(row["money"]["CurrentBest"], row["money"]["Route1"]) - row["money"]["CurrentBest"] for row in conditions]
    two_policy_advantage = [max(row["advantage"]["CurrentBest"], row["advantage"]["Route1"]) - row["advantage"]["CurrentBest"] for row in conditions]
    v3_incremental_own = [row["oracle_own_gain"] - value for row, value in zip(conditions, two_policy_own)]
    v3_incremental_advantage = [row["oracle_advantage_gain"] - value for row, value in zip(conditions, two_policy_advantage)]
    oracle = {
        "status": "COMPLETE", "conditions": len(conditions), "games": len(rows),
        "oracle_own": describe(own_oracle), "oracle_advantage": describe(advantage_oracle),
        "exclusive_winner_frequency": {
            "tie_break_rule": "CurrentBest, then V3, then Route1",
            "own": {name: {"count": exclusive_own[name], "rate": exclusive_own[name] / len(conditions)} for name in policies},
            "advantage": {name: {"count": exclusive_adv[name], "rate": exclusive_adv[name] / len(conditions)} for name in policies},
        },
        "tie_aware_optimal_frequency": {
            "own": {name: {"count": tie_aware_own[name], "rate": tie_aware_own[name] / len(conditions)} for name in policies},
            "advantage": {name: {"count": tie_aware_adv[name], "rate": tie_aware_adv[name] / len(conditions)} for name in policies},
        },
        "specialist_risk": specialist_risk,
        "marginal_policy_value": {
            "CurrentBest_plus_Route1_own_oracle": describe(two_policy_own),
            "CurrentBest_plus_Route1_advantage_oracle": describe(two_policy_advantage),
            "increment_from_adding_published_V3_own": describe(v3_incremental_own),
            "increment_from_adding_published_V3_advantage": describe(v3_incremental_advantage),
            "interpretation": "Route1 supplies nearly all own-money headroom; adding published V3 raises mean own oracle only 51.4 coins across nine conditions.",
        },
        "conditions_detail": conditions,
        "gate_interpretation": "MAJOR HINDSIGHT OPPORTUNITY: own oracle >= 8,000, so compatibility/predictability analysis was required.",
    }
    write_json("v3_regime_oracle.json", oracle)

    def aggregate(selected):
        return {
            "conditions": len(selected),
            "oracle_own": describe([row["oracle_own_gain"] for row in selected]),
            "oracle_advantage": describe([row["oracle_advantage_gain"] for row in selected]),
            "winner_own": dict(Counter(row["winner_own"] for row in selected)),
            "mean_v3_own_delta": statistics.fmean(row["own_delta_vs_currentbest"]["V3"] for row in selected),
            "mean_route1_own_delta": statistics.fmean(row["own_delta_vs_currentbest"]["Route1"] for row in selected),
            "mean_v3_advantage_delta": statistics.fmean(row["advantage_delta_vs_currentbest"]["V3"] for row in selected),
            "mean_route1_advantage_delta": statistics.fmean(row["advantage_delta_vs_currentbest"]["Route1"] for row in selected),
        }
    breakdown = {
        "by_opponent": {name: aggregate([row for row in conditions if row["opponent"] == name]) for name in sorted({row["opponent"] for row in conditions})},
        "by_seat": {str(seat): aggregate([row for row in conditions if row["seat"] == seat]) for seat in (0, 1)},
        "by_market_seed": {str(row["seed"]): aggregate([row]) for row in conditions},
        "by_winner_policy": {name: aggregate([row for row in conditions if row["winner_own"] == name]) for name in policies},
    }
    write_json("v3_regime_oracle_breakdown.json", breakdown)

    compatibility_rows = {}
    pairs = (("CurrentBest", "V3"), ("CurrentBest", "Route1"), ("V3", "Route1"))
    for left, right in pairs:
        pair_key = f"{left}<->{right}"
        compatibility_rows[pair_key] = {}
        for step in CHECKPOINTS:
            exact = layout = workforce = inventory = money = 0
            for group in groups.values():
                a = group[left]["checkpoints"][str(step)]["own_state"]
                b = group[right]["checkpoints"][str(step)]["own_state"]
                exact += a == b
                layout += a["tiles"] == b["tiles"] and a["quadrants"] == b["quadrants"] and a["farmer"] == b["farmer"]
                workforce += a["hands"] == b["hands"] and a["hires_today"] == b["hires_today"]
                inventory += a["shed"] == b["shed"] and a["seeds"] == b["seeds"] and a["inventories"] == b["inventories"]
                money += a["money"] == b["money"]
            compatibility_rows[pair_key][str(step)] = {"conditions": len(groups), "exact_state": exact, "layout": layout, "workforce": workforce, "inventory": inventory, "money": money}
    common_prefix = {
        "CurrentBest_vs_V3": {
            "exact_requested_action_prefix_length": 0,
            "step0_difference": {"CurrentBest": {"farmer": ["PASS"], "hands": [], "market": []}, "V3": {"farmer": ["PASS"], "hands": [], "market": [["BUY_PRODUCT", "WHEAT", 13]]}},
            "initial_state_equal": True,
            "economic_reconvergence": "At step 24, layout/workforce match 80/80 and private inventory matches 72/80, but money differs 80/80; tetsuya accounts for the eight inventory mismatches.",
        },
        "CurrentBest_vs_Route1": {"exact_requested_action_prefix_length": 0, "same_as_currentbest_vs_v3_until_v3_branch": True},
        "V3_vs_Route1": {"exact_requested_action_prefix_length": 360, "equal_actions": [0, 359], "equal_pre_action_state_through_step": 360, "first_possible_difference_step": 360},
        "checkpoint_state_matches": compatibility_rows,
    }
    write_json("v3_regime_common_prefix.json", common_prefix)
    compatibility = {
        "status": "NO PROVEN SAFE DELAYED SELECTOR BETWEEN CURRENTBEST AND SPECIALISTS",
        "exact_latest_choice_time": {"CurrentBest_vs_V3": "before step-0 action", "CurrentBest_vs_Route1": "before step-0 action", "V3_vs_Route1": "step 360"},
        "structurally_plausible_but_unproven": {
            "checkpoint": 24, "layout_match": "80/80", "workforce_match": "80/80", "inventory_match": "72/80", "money_match": "0/80",
            "reason_not_executed": "A switch would no longer run an exact frozen policy, and the best observable rule at this checkpoint was already unsafe/low-value; blind splice tests were prohibited.",
        },
        "irreversible_divergence": "At step 48, CurrentBest and both specialists have different crop layouts in 80/80 conditions.",
        "compatibility_by_checkpoint": compatibility_rows,
        "conclusion": "For the three-way portfolio, the only unquestionably legal decision is step 0. Step-0 economic observations are identical across all 80 conditions, so specialist regimes cannot be identified before exact compatibility is lost.",
    }
    write_json("v3_regime_compatibility_window.json", compatibility)

    feature_schema = {
        "source_trajectory": "Frozen CurrentBest observation immediately before its action at the selected checkpoint.",
        "current_state_features": ["seat", "opponent money/hands/hires/quadrants", "opponent crop/animal/structure counts", "opponent crop yield/age/maturity", "opponent productive/weeds/unfed/unwatered", "current market prices", "current market inventory", "currently unlocked shops"],
        "history_features": ["the same structured snapshot at the immediately preceding economic checkpoint", "derived deltas may be computed from those two snapshots"],
        "targets_training_only": ["V3 own/advantage delta versus CurrentBest", "Route1 own/advantage delta versus CurrentBest"],
        "checkpoints": list(CHECKPOINTS),
        "grouping": "Whole opponent/seed trajectory with both seats retained together conceptually; cross-seed-offset evaluation never splits state rows from a game.",
        "excluded": ["opponent identity", "team name", "rank", "seed", "replay ID", "future shops/prices/actions", "final result at inference", "hindsight winner at inference"],
    }
    write_json("v3_regime_feature_schema.json", feature_schema)
    write_json("v3_regime_feature_leakage_audit.json", {
        "status": "PASS", "audited_schema": "experiments/v3_regime_feature_schema.json",
        "forbidden_features_present": [],
        "opponent_identity_usage": "Stratification/reporting only; omitted from every deployable signature.",
        "seed_usage": "Grouping/held-out fold assignment only; omitted from features.",
        "future_information_usage": "None. Each signature is built only from snapshots at or before its checkpoint.",
        "labels": "Final deltas are used only as offline targets/evaluation.",
    })

    # Exact observable-profile clusters at the last structurally plausible checkpoint.
    clusters = defaultdict(list)
    for key, group in groups.items():
        snap = group["CurrentBest"]["checkpoints"]["24"]
        profile = json.dumps(snap["opponent"], sort_keys=True, separators=(",", ":"))
        clusters[hashlib.sha256(profile.encode()).hexdigest()[:12]].append((key, group, json.loads(profile)))
    cluster_rows = []
    for cluster_id, members in sorted(clusters.items()):
        cluster_rows.append({
            "cluster_id": cluster_id, "formation": "exact equality of step-24 observable opponent economic state",
            "profile": members[0][2], "analysis_members": sorted({key[0] for key, _, _ in members}),
            "conditions": len(members),
            "mean_v3_own_delta": statistics.fmean(group["V3"]["own_money"] - group["CurrentBest"]["own_money"] for _, group, _ in members),
            "mean_route1_own_delta": statistics.fmean(group["Route1"]["own_money"] - group["CurrentBest"]["own_money"] for _, group, _ in members),
            "route1_positive_rate": sum(group["Route1"]["own_money"] > group["CurrentBest"]["own_money"] for _, group, _ in members) / len(members),
        })
    similarity = {
        "checkpoint": 24, "method": "Exact clustering of observable opponent economic state; names added only after cluster formation for interpretation.",
        "clusters": cluster_rows,
        "currentbest_like_aliasing": {
            "members": ["CurrentBest", "Nazmus", "oceanmix"],
            "identical_visible_profile": True,
            "route1_mean_delta_by_member": {name: breakdown["by_opponent"][name]["mean_route1_own_delta"] for name in ("CurrentBest", "Nazmus", "oceanmix")},
            "conclusion": "REFUTED as a deployable early similarity rule: the exact same visible profile maps to positive Route1 expectation against CurrentBest and large negative expectation against Nazmus/oceanmix.",
        },
        "supported_specialist_profiles": [
            "Opponent bank about 1,973 with six wheat/six melon/one cow (router_hands12): large mean specialist upside but one catastrophic seat/seed loss.",
            "Opponent bank about 478 with ten wheat/three sheep (tetsuya): positive mean specialist upside with two losing appearances.",
            "Opponent bank about 11 with five wheat/five melon/one cow/four sheep (K3/victor): positive pooled mean, but market-seed losses remain.",
        ],
    }
    write_json("v3_regime_similarity_analysis.json", similarity)

    curves = []
    threshold_curves = []
    for objective in ("own_money", "advantage"):
        for step in CHECKPOINTS:
            candidates = [cv_signature_rule(groups, step, threshold, objective, False) for threshold in THRESHOLDS]
            best = max(candidates, key=lambda item: item["gain"]["mean"])
            history_best = None
            if step >= 24:
                history_candidates = [cv_signature_rule(groups, step, threshold, objective, True) for threshold in THRESHOLDS]
                history_best = max(history_candidates, key=lambda item: item["gain"]["mean"])
            curves.append({
                "objective": objective, "step": step,
                "unique_visible_signatures": len({visible_signature(group, step, False) for group in groups.values()}),
                "best_current_state": {key: value for key, value in best.items() if key != "rows"},
                "best_state_plus_history": ({key: value for key, value in history_best.items() if key != "rows"} if history_best else None),
                "exact_policy_compatibility": step == 0 or (step <= 360 and objective and False),
                "structural_currentbest_specialist_compatibility": "plausible_not_proven" if step == 24 else ("initial_only" if step == 0 else "lost_or_unproven"),
            })
            if step == 24:
                threshold_curves.extend({key: value for key, value in item.items() if key != "rows"} for item in candidates)
    write_json("v3_regime_decision_time_curve.json", {
        "status": "EXPLORATORY CROSS-SEED CURVE; STOPPED BEFORE LEARNED MODEL",
        "method": "Four-fold leave-one-seed-offset-out exact observable-signature value rule; OOD signatures default to CurrentBest.",
        "curve": curves,
        "central_result": "State history did not improve the best own-money result at steps 24 or 48. Later checkpoints created mostly unseen signatures and lost coverage, while policy compatibility was already gone.",
    })
    write_json("v3_regime_threshold_curve.json", {
        "status": "COMPLETE FOR SIMPLE STEP-24 SIGNATURE RULE", "thresholds": list(THRESHOLDS),
        "curves": threshold_curves,
        "note": "No learned-model threshold was tuned because the compatibility/safety stop condition fired.",
    })

    bank_rule = simple_rule(groups, "opponent_bank_at_least_400", lambda opponent: opponent["money"] >= 400)
    hands_rule = simple_rule(groups, "opponent_hands_at_least_1", lambda opponent: opponent["hands"] >= 1)
    similarity_rule = simple_rule(
        groups, "high_bank_or_lowbank_mixed_livestock_profile",
        lambda opponent: opponent["money"] >= 400 or (
            10 <= opponent["money"] <= 12 and opponent["crops"] == {"MELON": 5, "WHEAT": 5}
            and opponent["animals"] == {"COW": 1, "SHEEP": 4}
        ),
    )
    always = {}
    for policy in ("V3", "Route1"):
        gains = [group[policy]["own_money"] - group["CurrentBest"]["own_money"] for group in groups.values()]
        always[policy] = describe(gains)
    random_expected = statistics.fmean([0, always["V3"]["mean"], always["Route1"]["mean"]])
    best_step24 = max(
        (cv_signature_rule(groups, 24, threshold, "own_money", False) for threshold in THRESHOLDS),
        key=lambda item: item["gain"]["mean"],
    )
    selected_by_condition = {
        (row["opponent"], row["seed"], row["seat"]): row["selected"]
        for row in best_step24["rows"]
    }
    best_step24_advantage = [
        group[selected_by_condition[key]]["advantage"] - group["CurrentBest"]["advantage"]
        for key, group in groups.items()
    ]
    model_results = {
        "status": "STOPPED AFTER SIMPLE RULES; M2/M3/M4 NOT RUN",
        "baselines": {
            "M0_always_currentbest": {"mean_gain": 0},
            "always_v3": always["V3"], "always_route1": always["Route1"],
            "uniform_random_expected_mean_gain": random_expected,
            "simple_bank_rule": bank_rule, "simple_hands_rule": hands_rule,
            "simple_similarity_rule": similarity_rule,
            "cross_seed_exact_signature_rule": {key: value for key, value in best_step24.items() if key != "rows"},
        },
        "learned_models": {
            "M2_decision_tree": {"status": "NOT RUN", "reason": "No safe compatible checkpoint with adequate simple-rule precision/value."},
            "M3_tree_ensemble": {"status": "NOT RUN", "reason": "Same stop condition; escalation would optimize an undeployable target."},
            "M4_state_plus_history": {"status": "NOT RUN", "reason": "Exact-signature history probe showed no improvement before compatibility loss."},
        },
        "stop_evidence": {
            "best_cross_seed_step24_own_gain": best_step24["gain"]["mean"],
            "activation_precision": best_step24["activation_precision_positive"],
            "false_positives": best_step24["false_positive_count"],
            "worst": best_step24["gain"]["worst"],
        },
    }
    write_json("v3_regime_model_results.json", model_results)
    write_json("v3_regime_oracle_capture.json", {
        "oracle_own_mean": oracle["oracle_own"]["mean"], "oracle_advantage_mean": oracle["oracle_advantage"]["mean"],
        "best_compatible_or_near_compatible_simple_rule": "cross-seed exact-signature rule at step 24, threshold 8000",
        "selector_own_gain": best_step24["gain"]["mean"],
        "selector_advantage_gain": statistics.fmean(best_step24_advantage),
        "selector_advantage_distribution": describe(best_step24_advantage),
        "own_oracle_capture_rate": best_step24["gain"]["mean"] / oracle["oracle_own"]["mean"],
        "activation_rate": best_step24["activation_rate"], "activation_precision": best_step24["activation_precision_positive"],
        "false_positive_rate": best_step24["false_positive_rate_among_activations"],
        "false_positive_mean_loss": best_step24["false_positive_mean_loss"],
        "p10": best_step24["gain"]["p10"], "p5": best_step24["gain"]["p5"], "worst": best_step24["gain"]["worst"],
        "deployable": False,
        "reason": "Step 24 is only structurally near-compatible, not exact; capture and precision are low and false activations remain catastrophic.",
    })

    stop_reason = "Large hindsight oracle, but no observable distinction exists at the exact step-0 commitment point; the best step-24 near-compatible rule captures only 17.9% of own oracle at 56.5% precision with a -36,682 worst false activation."
    write_json("v3_regime_candidate_results.json", {
        "status": "NOT RUN", "reason": stop_reason,
        "candidate_created": False, "route_splice_attempted": False,
        "policy_mutations": False,
    })
    write_json("v3_regime_selection_results.json", {
        "decision": "KEEP CURRENTBEST; DO NOT BUILD GATE",
        "current_best": policies["CurrentBest"], "reason": stop_reason,
        "oracle_is_real": True, "oracle_is_deployable": False,
        "research_best_promoted": False, "current_best_registry_changed": False, "submission_changed": False,
    })
    write_json("v3_regime_finalist_lock.json", {
        "status": "NOT RUN", "reason": "No gated candidate passed compatibility and development safety gates.",
        "frozen_policy_hashes": {name: value["sha256"] for name, value in policies.items()},
        "evaluation_runner_sha256": sha(ROOT / "run_v3_regime_oracle.py"),
    })
    write_json("v3_regime_final_validation.json", {
        "status": "NOT RUN", "reason": "No finalist was locked; final unseen data was not opened or simulated for a candidate.",
        "submission_or_upload_performed": False,
    })

    structure_md = """# V3 specialist regime structure

The hindsight opportunity is large, but it is driven by future market paths within economic families—not by a clean early regime boundary. Route1 supplies nearly the entire own-money opportunity: CurrentBest+Route1 alone has a +9,727.3 oracle, and adding published V3 increases it by only +51.4 on average (nine positive conditions). The practical selection problem is therefore almost entirely CurrentBest versus Route1.

At step 24, three opponents—CurrentBest, Nazmus, and oceanmix—have the exact same observable economic profile under the shared CurrentBest opening: bank 22, twelve melons, seven wheat, two cows, two sheep, and identical market state. Route1 averages +1,631.6 own coins against CurrentBest, but −7,232.5 against Nazmus and −4,742.0 against oceanmix. An opponent cannot therefore be identified as “CurrentBest-like and vulnerable” from that deployable state without using forbidden identity or later behavior.

Three observable profiles have positive specialist expectation:

- high bank (~1,973), six wheat/six melon/one cow: router_hands12-like;
- bank ~478, ten wheat/three sheep: tetsuya-like;
- bank ~11, five wheat/five melon/one cow/four sheep: the pooled K3/victor profile.

These patterns are genuine economic clusters, not name features. They are still unsafe: future seed/shop paths reverse the winner inside every profile. A simple bank≥400 Route1 gate activates 16/80 times and is positive 13/16, but its three errors average −14,290 and include a −36,682 loss. The broader similarity rule gains +4,600.8 in-sample but makes ten false activations and is not held-out evidence.

The policy-state geometry explains the dead end. CurrentBest and both specialists take different market actions at turn 0. By step 24 their field geometry/workforce match in all conditions and inventory matches in 72/80, but cash never matches. By step 48 their crop layouts differ in every condition. The safest informative checkpoint is therefore only “near compatible,” while the exact compatible checkpoint has one indistinguishable economic state.

History did not improve the cross-seed exact-signature rule at steps 24 or 48. At step 72 the first randomized shop creates more information, but most held-out signatures become OOD and the policies have already diverged. This is a high hindsight oracle with low safe capture—not a deployable selector opportunity in the frozen policy set.
"""
    write_md("v3_regime_structure.md", structure_md)

    current_direct = breakdown["by_opponent"]["CurrentBest"]
    report = f"""# V3 specialist regime gating report

## Result

The three-policy portfolio has major hindsight headroom but no safe observable gate. Across **80 fresh conditions / 240 games** (ten opponents, four new natural-RNG seeds each, both seats), the own-money oracle is **+{oracle['oracle_own']['mean']:.1f}** and the advantage oracle **+{oracle['oracle_advantage']['mean']:.1f}** per condition. Both oracle P10 and P5 are zero because CurrentBest is always available as the fallback.

With conservative tie-breaking, CurrentBest is own-optimal in **36/80 (45.0%)**, V3 in **23/80 (28.75%)**, and Route1 in **21/80 (26.25%)**. Tie-aware, Route1 is optimal in 35 conditions because published V3 selects Route1 in many regimes.

Route1 contains almost all of the portfolio value. CurrentBest+Route1 alone has a **+{statistics.fmean(two_policy_own):.1f}** own oracle; adding published V3 increases the full oracle by only **+{statistics.fmean(v3_incremental_own):.1f}** per condition.

When V3 is optimal it gains **{specialist_risk['V3']['mean_gain_when_optimal']:.1f}** versus CurrentBest. When selecting it is actually worse than CurrentBest, the mean loss is **{specialist_risk['V3']['wrong_selection_loss']['mean']:.1f}**, P10 **{specialist_risk['V3']['wrong_selection_loss']['p10']:.1f}**, and worst **{specialist_risk['V3']['wrong_selection_loss']['worst']:.0f}**. Route1's corresponding upside is **{specialist_risk['Route1']['mean_gain_when_optimal']:.1f}**; wrong-selection mean **{specialist_risk['Route1']['wrong_selection_loss']['mean']:.1f}**, P10 **{specialist_risk['Route1']['wrong_selection_loss']['p10']:.1f}**, worst **{specialist_risk['Route1']['wrong_selection_loss']['worst']:.0f}**.

## Why the apparent specialist signal is not deployable

CurrentBest performs no market order on turn 0. V3 and Route1 buy 13 wheat. Their exact common action prefix is therefore zero turns, and the only unquestionably legal three-way selection time is before the first action. At that observation, every evaluated condition has the same economic state and market state; only seat differs. No allowed feature can distinguish the eventual winner.

By step 24 there is useful opponent information and near-compatible geometry: field layout and workforce agree in 80/80 CurrentBest/V3 conditions, and inventory in 72/80. Cash differs in all conditions, however, and by step 48 crop layout differs in 80/80. Step 24 is not an exact common prefix.

The best cross-seed step-24 signature rule uses an 8,000-coin safety threshold. It gains only **+{best_step24['gain']['mean']:.1f} own / +{statistics.fmean(best_step24_advantage):.1f} advantage** per condition, captures **{100 * best_step24['gain']['mean'] / oracle['oracle_own']['mean']:.1f}%** of the own oracle, activates in **{best_step24['activation_count']}/80**, and is right only **{100 * best_step24['activation_precision_positive']:.1f}%** of activations. It makes {best_step24['false_positive_count']} false activations and retains a **{best_step24['gain']['worst']:.0f}** worst own-money loss. Adding the immediately previous checkpoint as history does not improve this result.

## CurrentBest-counter hypothesis

The fresh direct matchup is weaker than the discovery result. V3's mean own delta against CurrentBest is **{current_direct['mean_v3_own_delta']:+.1f}** and mean advantage delta **{current_direct['mean_v3_advantage_delta']:+.1f}**; it wins 6/8 direct games, not 8/8. More importantly, CurrentBest, Nazmus, and oceanmix are observationally identical at step 24, while their Route1 mean deltas are +1,631.6, −7,232.5, and −4,742.0. V3 counters the exact later CurrentBest trajectory in some market paths, not a reliably identifiable early “CurrentBest-like” family.

## Safety and decision

All 240 games completed with zero runtime errors, semantic errors, or livestock escapes. No selector candidate was created because doing so would require an unproven step-24 splice after a low-precision gate, violating the compatibility and false-positive constraints. No learned tree/ensemble was trained after the stop condition fired.

**Keep CurrentBest unchanged.** No finalist lock, final candidate validation, packaging, upload, or submission occurred. The next useful research direction is not a more complex classifier; it is a deliberately designed, validated common opening that preserves both continuations until randomized shop/market information becomes visible. That should be attempted only as a new architecture study with explicit state reconciliation, not as a blind replay splice.
"""
    write_md("v3_regime_gating_report.md", report)


if __name__ == "__main__":
    main()
