"""Lock the Top-3 adaptive distillation research stage and write its report."""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import statistics

import numpy as np


ROOT = Path(__file__).resolve().parent
EXP = ROOT / "experiments"
BASELINE = ROOT / "agents/top50_distilled/top50_observable_portfolio.py"
SUBMISSION = ROOT / "submission/main.py"
PHASES = (
    "OPENING_FOUNDATION", "FIRST_LAND_DEPLOYMENT", "MELON_CAPITALIZATION",
    "SECOND_LAND_DEPLOYMENT", "STRAWBERRY_RAMP", "MIXED_PREMIUM_PRODUCTION",
    "TERMINAL_LIQUIDATION",
)
DECISIONS = (
    "BUY_LAND_24", "HIRE_24", "RAMP_COW_48", "RAMP_SHEEP_48",
    "START_MELON_COHORT_48", "START_STRAWBERRY_COHORT_48",
    "SELL_PREMIUM_24", "ENTER_TERMINAL_24",
)
TEACHERS = {1: "tetsuya", 2: "Crop Dusta", 3: "OceanMix"}


def load(name):
    return json.loads((EXP / name).read_text())


def write(name, value):
    (EXP / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pct(value):
    return "N/A" if value is None else f"{100 * value:.1f}%"


def f3(value):
    return "N/A" if value is None else f"{value:.3f}"


def decision_branch_analysis(data):
    output = {}
    decisions = data["decisions"]; teacher = data["teacher"]
    episode = data["episode_id"]; step = data["step"]
    for rank, teacher_name in TEACHERS.items():
        episodes = np.unique(episode[teacher == rank])
        rows = {}
        for index, decision in enumerate(DECISIONS):
            signatures, onsets = [], []
            for episode_id in episodes:
                mask = (teacher == rank) & (episode == episode_id) & (step % 6 == 0)
                order = np.argsort(step[mask])
                turns = step[mask][order]; values = decisions[mask, index][order]
                signatures.append(tuple(int(value) for value in values))
                onset = turns[(values == 1) & np.r_[True, values[:-1] == 0]]
                onsets.append(tuple(int(value) for value in onset))
            counts = Counter(onsets)
            meaningful = [pattern for pattern, count in counts.items() if count / len(episodes) >= .05]
            rows[decision] = {
                "binary_sequence_count": len(set(signatures)),
                "onset_pattern_count": len(counts),
                "meaningful_onset_pattern_count_min5pct": len(meaningful),
                "top_onset_patterns": [{"steps": list(pattern), "episodes": count} for pattern, count in counts.most_common(6)],
            }
        variable = [name for name, row in rows.items() if row["meaningful_onset_pattern_count_min5pct"] >= 2]
        output[teacher_name] = {"decision_families": rows, "genuinely_variable_decision_families": variable, "count": len(variable)}
    return output


def active_phase_metrics(phase_reconstruction, data):
    output = {}
    split = data["split"]; teacher = data["teacher"]; phase = data["phase"]
    for rank, name in TEACHERS.items():
        mask = (split == 2) & (teacher == rank)
        supports = np.bincount(phase[mask], minlength=len(PHASES))
        metrics = phase_reconstruction["by_teacher_shared_model"][name]
        active = [metrics["per_phase"][phase_name]["f1"] for index, phase_name in enumerate(PHASES) if supports[index] > 0]
        output[name] = {
            "strict_all_ontology_macro_f1": metrics["macro_f1"],
            "active_phase_macro_f1": float(np.mean(active)),
            "active_phases": [phase_name for index, phase_name in enumerate(PHASES) if supports[index] > 0],
            "holdout_support": {phase_name: int(supports[index]) for index, phase_name in enumerate(PHASES)},
        }
    return output


def milestone_summary(segments):
    output = {}
    for name in TEACHERS.values():
        rows = [row for row in segments["appearances"] if row["team"] == name]
        signatures = Counter(tuple(segment["phase"] for segment in row["segments"]) for row in rows)
        milestones = {}
        for key in ("first_land", "second_land", "first_melon_sale", "first_strawberry_sale", "terminal_start"):
            values = [row["milestones"][key] for row in rows if row["milestones"][key] is not None]
            milestones[key] = {
                "min_step": min(values), "median_step": statistics.median(values),
                "max_step": max(values), "unique_steps": len(set(values)),
            }
        output[name] = {
            "episodes": len(rows), "phase_signature_count": len(signatures),
            "phase_signatures": [{"sequence": list(sequence), "episodes": count} for sequence, count in signatures.most_common()],
            "milestones": milestones,
        }
    return output


def coefficient_signals(model):
    weights = model["shared_coefficients"][:-1]
    names = model["shared_feature_names"].astype(str)
    output = {}
    for index, decision in enumerate(DECISIONS):
        column = weights[:, len(PHASES) + index]
        ranking = np.argsort(-np.abs(column))[:12]
        output[decision] = [{"feature": str(names[row]), "coefficient": float(column[row])} for row in ranking]
    return output


def main():
    corpus = load("top3_adaptive_corpus_manifest.json")
    dataset_manifest = load("top3_adaptive_transition_dataset_manifest.json")
    segments = load("top3_adaptive_phase_segments.json")
    phase_reconstruction = load("top3_adaptive_phase_reconstruction.json")
    decision_reconstruction = load("top3_adaptive_decision_reconstruction.json")
    history = load("top3_adaptive_history_ablation.json")
    teachers = load("top3_adaptive_teacher_models.json")
    deployment = load("top3_adaptive_deployment_audit.json")
    data = np.load(EXP / "top3_adaptive_transition_dataset.npz")
    model = np.load(ROOT / "agents/top3_adaptive_distill/top3_adaptive_reconstruction_models.npz")

    branches = decision_branch_analysis(data)
    phase_active = active_phase_metrics(phase_reconstruction, data)
    milestones = milestone_summary(segments)
    signals = coefficient_signals(model)
    segments["segmentation_rule"] = "Actual land, crop-realization and planting-cessation events; terminal cessation is conservatively clipped to steps 600..696. Labels are not based solely on turn and never use teacher identity."
    write("top3_adaptive_phase_segments.json", segments)
    teachers["strategic_branch_analysis"] = branches
    teachers["active_phase_metrics"] = phase_active
    teachers["decision_feature_signals"] = signals
    write("top3_adaptive_teacher_models.json", teachers)

    # The aggregate reconstruction gate passes, but the deployable control gate
    # remains selective: one teacher and several target heads miss threshold.
    decision_by_teacher = decision_reconstruction["by_teacher_shared_model"]
    selective_gate = {
        "aggregate_phase_macro_f1": phase_reconstruction["shared_holdout"]["macro_f1"],
        "aggregate_decision_macro_f1": decision_reconstruction["shared_holdout"]["macro_f1"],
        "all_teacher_active_phase_f1_at_least_0_80": all(row["active_phase_macro_f1"] >= .80 for row in phase_active.values()),
        "all_teacher_decision_f1_at_least_0_75": all(decision_by_teacher[name]["macro_f1"] >= .75 for name in TEACHERS.values()),
        "teacher_decision_macro_f1": {name: decision_by_teacher[name]["macro_f1"] for name in TEACHERS.values()},
        "weak_shared_heads": {
            name: metrics["f1"] for name, metrics in decision_reconstruction["shared_holdout"].items()
            if isinstance(metrics, dict) and metrics.get("f1", 1) < .75
        },
        "crop_family_macro_f1": decision_reconstruction["economic_target_reconstruction"]["crop_family"]["macro_f1"],
        "market_mode_strict_macro_f1": decision_reconstruction["economic_target_reconstruction"]["market_mode"]["macro_f1"],
        "cohort_scale_within_2_accuracy": decision_reconstruction["economic_target_reconstruction"]["numeric_targets"]["target_cohort_scale_48"]["within_2_accuracy"],
        "verdict": "SELECTIVE_RECONSTRUCTION_PASS_FULL_CONTROLLER_FAIL",
        "reason": "Phase and aggregate event reconstruction pass, but Crop Dusta decisions, terminal/sheep/cohort heads, crop family, market mode and cohort scale are not uniformly reliable.",
    }

    counterfactuals = {
        "schema_version": 1, "status": "NOT RUN",
        "reason": "No causally meaningful Top3 strategic alternative is safely executable by the frozen CurrentBest backbone. Land/livestock/crop/terminal changes require a new target-driven executor; fixed replay switching is forbidden and previously caused catastrophic continuation mismatch. The only bounded sell-slot adjustment lacks a reliable market-mode/quantity head, so testing it would be manual guessing rather than distilled-policy counterfactual evaluation.",
        "reconstruction_gate": selective_gate,
        "executor_compatibility": deployment["executor_compatibility"],
        "same_state_rollout_pairs": 0, "paired_final_money_delta": None,
        "causally_supported_decision_types": [],
        "important_distinction": "The earlier fixed-route counterfactual losses are contextual evidence, not values of this distilled policy.",
    }
    write("top3_adaptive_counterfactuals.json", counterfactuals)

    oracle = {
        "schema_version": 1, "status": "NOT RUN",
        "reason": "A hindsight oracle requires at least two coherent executable high-level continuations from the same state. CurrentBest exposes no such target interface, and route medoid substitution is explicitly disallowed.",
        "alternatives": ["KEEP_CURRENTBEST"], "oracle_gain": None,
        "fitted_q_justified": False,
        "fitted_q_reason": "No executable (state, strategic action, return) counterfactual dataset and no measured oracle headroom.",
    }
    write("top3_adaptive_oracle.json", oracle)

    hybrid_candidates = {
        "schema_version": 1, "status": "NOT BUILT",
        "reason": "Stopped at executor compatibility gate before modifying gameplay behavior.",
        "concepts": {
            "H1_consensus_safe": {"status": "DESIGN_ONLY", "control": "delegate only on Top3 agreement + OOD/confidence pass", "blocker": "no target-driven executor"},
            "H2_top1_distilled": {"status": "DESIGN_ONLY", "control": "causally validated tetsuya dimensions only", "blocker": "no causal counterfactual values and no target-driven executor"},
            "H3_value_gated_adaptive": {"status": "DESIGN_ONLY", "control": "delegate only when fitted-Q advantage clears threshold", "blocker": "no executable action portfolio/oracle/Q data"},
        },
        "projected_observation_eligibility_not_delegation": deployment["overall"]["ood_confidence_eligible_rate"],
        "projected_teacher_phase_consensus": deployment["overall"]["all_three_phase_agreement_rate"],
    }
    write("top3_adaptive_hybrid_candidates.json", hybrid_candidates)

    common_not_run = {
        "schema_version": 1, "status": "NOT RUN",
        "reason": "No gameplay hybrid passed the reconstruction + causal + executor gates; running selection games would not test an adaptive distilled policy.",
        "games": 0,
    }
    write("top3_adaptive_hybrid_results.json", {**common_not_run, "metrics": {"delegation_rate": None, "fallback_rate": None, "paired_money_delta": None, "advantage_delta": None, "h2h": None, "p10": None, "p5": None}})
    write("top3_adaptive_decision_attribution.json", {**common_not_run, "leave_one_decision_out": [], "most_valuable_decision": None})
    write("top3_adaptive_selection_results.json", {**common_not_run, "selection_winner": None})

    baseline_sha = digest(BASELINE)
    submission_sha = digest(SUBMISSION)
    finalist = {
        "schema_version": 1, "status": "NO_NEW_FINALIST",
        "promoted": False, "current_research_best": str(BASELINE.relative_to(ROOT)),
        "current_research_best_sha256": baseline_sha,
        "reason": "Adaptive reconstruction is scientifically useful but no causal executable hybrid exists. Frozen CurrentBest remains the evidence-backed best.",
        "submission_main_modified": False, "submission_main_sha256": submission_sha,
    }
    write("top3_adaptive_finalist_lock.json", finalist)
    write("top3_adaptive_final_validation.json", {
        "schema_version": 1, "status": "NOT RUN", "reason": "No finalist was built or locked.",
        "games": 0, "runtime_errors": None, "semantic_errors": None,
        "livestock_escapes": None, "meaningful_stranding": None,
        "baseline_source_integrity": {"path": str(BASELINE.relative_to(ROOT)), "sha256": baseline_sha, "matches_expected": baseline_sha == "f9ca672848ccffdfe56888d99bcdf5a9d7644062b9eec0cf0cdea13574931233"},
        "submission_unchanged_by_stage": {"path": str(SUBMISSION.relative_to(ROOT)), "sha256": submission_sha},
    })

    replay_rows = phase_reconstruction["replay_level_errors"]
    mean_replay_accuracy = statistics.fmean(row["phase_accuracy"] for row in replay_rows)
    worst_replay_accuracy = min(row["phase_accuracy"] for row in replay_rows)
    model_rows = history["model_families"]
    current = model_rows["M1_current_linear"]
    h120 = model_rows["M4_history120_linear"]
    turn = model_rows["M0_turn_only"]
    decision_shared = decision_reconstruction["shared_holdout"]
    branch_count_text = ", ".join(name + " " + str(row["count"]) for name, row in branches.items())

    report = []
    report += [
        "# Top-3 Adaptive Policy Distillation", "",
        "## Executive conclusion", "",
        "The strategic reconstruction study succeeded, but the gameplay-transfer stage correctly stopped. "
        f"On complete held-out episodes, the best structured-history model reached **{h120['phase']['macro_f1']:.3f} phase macro-F1**, "
        f"**{h120['decisions']['macro_f1']:.3f} major-decision macro-F1**, and **{h120['transitions']['transition_recall']:.3f} transition recall** with "
        f"{h120['transitions']['mean_absolute_timing_error_steps']:.1f} steps mean timing error. History adds real signal: current-state-only was "
        f"{current['phase']['macro_f1']:.3f}/{current['decisions']['macro_f1']:.3f}, while turn-only was {turn['phase']['macro_f1']:.3f}/{turn['decisions']['macro_f1']:.3f}.", "",
        "This is not yet a deployable adaptive agent. Crop Dusta's held-out decision F1 is below the gate, crop/market/cohort target heads are weak, and the frozen CurrentBest is a selector over complete replay routes—not a target-driven executor. Buying different land, animals or crops would leave it without coherent construction, routing, service and harvesting continuations. Building a hybrid now would therefore repeat the route-splicing error in a less obvious form.", "",
        "**Decision:** no new agent, no promotion, no submission change. The next architecture must be a safe target-driven executor before counterfactual policy improvement can resume.", "",
        "## 1. Corpus and version purity", "",
        "| Teacher | Current submission | Available | Used | Confidence |", "|---|---:|---:|---:|---|",
    ]
    for row in sorted(corpus["submissions"], key=lambda item: item["rank"]):
        used = milestones[row["team_name"]]["episodes"]
        report.append(f"| {row['team_name']} | {row['selected_submission_id']} | {row['available_completed_public_episodes']} | {used} | exact submission ID / high |")
    report += [
        "", f"The refresh captured {sum(row['available_completed_public_episodes'] for row in corpus['submissions'])} teacher appearances and retained **{sum(row['episodes'] for row in milestones.values())} version-pure appearances** after excluding one identical full-replay duplicate. The 219 appearances refer to 215 unique valid replay files; all replay acquisition was read-only.", "",
        "## 2. Strategic ontology and observed phases", "",
        "The event-driven ontology separates seven mutually exclusive economic phases: opening foundation, first-land deployment, melon capitalization, second-land deployment, strawberry ramp, mixed premium production, and terminal liquidation. Livestock ramp, hiring, crop cohorts, land targets and market mode are parallel target/decision axes rather than forced mutually exclusive phases.", "",
        "| Teacher | Dominant phase sequence | First land | Second land | Phase signatures |", "|---|---|---:|---:|---:|",
    ]
    for name, row in milestones.items():
        dominant = " → ".join(row["phase_signatures"][0]["sequence"])
        report.append(f"| {name} | {dominant} | {row['milestones']['first_land']['median_step']:.0f} | {row['milestones']['second_land']['median_step']:.0f} | {row['phase_signature_count']} |")
    report += [
        "", "These boundaries come primarily from executed land purchases, premium-product realization and planting cessation; only terminal cessation is conservatively clipped to steps 600–696. They are not assigned solely from turn. The limited phase-signature diversity is itself an important result: adaptation is concentrated inside phases—livestock targets, crop cohorts and selling—not in wholesale route changes.", "",
        "## 3. Genuine adaptive branches", "",
        "A branch family is counted as genuinely variable only when at least two onset patterns each occur in at least 5% of that teacher's corpus. This avoids calling one-off action jitter a strategy branch.", "",
        "| Teacher | Variable strategic families | Count | Reconstructable at F1 ≥ .75 |", "|---|---|---:|---:|",
    ]
    reconstructable = {}
    for name, branch in branches.items():
        scores = decision_by_teacher[name]
        supported = [decision for decision in branch["genuinely_variable_decision_families"] if scores[decision]["f1"] >= .75]
        reconstructable[name] = supported
        report.append(f"| {name} | {', '.join(branch['genuinely_variable_decision_families'])} | {branch['count']} | {len(supported)} ({', '.join(supported)}) |")
    report += [
        "", "The main branch points are livestock ramps in roughly steps 0–234, melon/strawberry cohort starts in steps 0–312, premium-sale waves around steps 132–306, and OceanMix's variable terminal transition around steps 642–654. First-land, daily-hire continuity and several teacher-specific cohort timings are mostly fixed and should not be mislabeled as adaptive.", "",
        "## 4. What public signals predict decisions", "",
        "The strongest shared linear signals are correlational diagnostics, not causal rules:", "",
        "- Land: owned quadrants/productive tiles, recent feed load, fertilizer inventory and melon-price history.",
        "- Cow ramp: wheat price, current cows/pastures, time since cow/land purchase, recent hiring and shop count.",
        "- Sheep ramp: multi-horizon milk/melon price history and recent labor scaling.",
        "- Crop cohorts: existing cohort size, recent same-crop planting, owned land and wheat/melon price history.",
        "- Premium selling: recent melon price range, recent feed/hire history and productive-tile load.",
        "- Terminal: strawberry-count deltas, planting/harvest/sale history and late product prices.", "",
        "Feature ablations show no single shortcut dominates: removing turn changes H72 phase F1 by only "
        f"{history['feature_family_ablations']['remove_turn']['phase_macro_f1_delta']:+.3f}; removing opponent bank changes it by "
        f"{history['feature_family_ablations']['remove_opponent_bank']['phase_macro_f1_delta']:+.3f}. The gain comes from the combined trajectory summary, although feature correlations remain too diffuse to be treated as an economic law.", "",
        "## 5. Reconstruction results", "",
        "| Model | Inputs | Phase F1 | Decision F1 | Transition recall | Timing error |", "|---|---|---:|---:|---:|---:|",
    ]
    for family in ("M0_turn_only", "M1_current_linear", "M2_current_stump_ridge", "M3_history24_linear", "M4_history48_linear", "M4_history72_linear", "M4_history120_linear", "M5_small_elm"):
        row = model_rows[family]
        if "phase" not in row:
            report.append(f"| {family} | — | NOT RUN | — | — | — |")
        else:
            report.append(f"| {family} | {row['feature_set']} | {row['phase']['macro_f1']:.3f} | {row['decisions']['macro_f1']:.3f} | {row['transitions']['transition_recall']:.3f} | {row['transitions']['mean_absolute_timing_error_steps']:.1f} |")
    report += [
        "", f"Held-out replay-level smoothed phase accuracy averages {mean_replay_accuracy:.3f}, has median {statistics.median(row['phase_accuracy'] for row in replay_rows):.3f}, and worst {worst_replay_accuracy:.3f}. The worst replay accumulated {max(row['wrong_phase_duration'] for row in replay_rows)} wrong-phase steps. A small nonlinear ELM regressed versus linear structured history, so GRU/temporal escalation is not justified.", "",
        "### Per-teacher reconstruction", "",
        "| Teacher | Active-phase F1 | Decision F1 | Transition recall |", "|---|---:|---:|---:|",
    ]
    for name in TEACHERS.values():
        report.append(f"| {name} | {phase_active[name]['active_phase_macro_f1']:.3f} | {decision_by_teacher[name]['macro_f1']:.3f} | {phase_reconstruction['by_teacher_transition_metrics'][name]['transition_recall']:.3f} |")
    report += ["", "Shared major-decision heads:", "", "| Decision | Precision | Recall | F1 |", "|---|---:|---:|---:|"]
    for name in DECISIONS:
        row = decision_shared[name]
        report.append(f"| {name} | {row['precision']:.3f} | {row['recall']:.3f} | {row['f1']:.3f} |")
    targets = decision_reconstruction["economic_target_reconstruction"]
    report += [
        "", f"Target quality is uneven: land MAE {targets['numeric_targets']['target_land_72']['mae']:.3f}, hands MAE {targets['numeric_targets']['target_hands_24']['mae']:.3f}, cows MAE {targets['numeric_targets']['target_cows_72']['mae']:.3f}, sheep MAE {targets['numeric_targets']['target_sheep_72']['mae']:.3f}; but crop-family macro-F1 is {targets['crop_family']['macro_f1']:.3f}, market-mode strict macro-F1 {targets['market_mode']['macro_f1']:.3f}, and cohort scale is within two plants only {pct(targets['numeric_targets']['target_cohort_scale_48']['within_2_accuracy'])}.", "",
        "## 6. History, aliasing, confidence and OOD", "",
        f"History raises phase F1 by {history['history_gain_vs_current']['phase_macro_f1']:+.3f}, decision F1 by {history['history_gain_vs_current']['decision_macro_f1']:+.3f}, and transition recall by {history['history_gain_vs_current']['transition_recall']:+.3f} over current state. Nearest-neighbor decision F1 rises from {history['partial_observability_nearest_neighbor_test']['current_state']['nearest_neighbor_decision_macro_f1']:.3f} at current state to {history['partial_observability_nearest_neighbor_test']['history48']['nearest_neighbor_decision_macro_f1']:.3f} at 48 turns. Among the closest 10% of current-state pairs, {pct(history['partial_observability_nearest_neighbor_test']['alias_pairs']['decision_alias_rate_within_close_pairs'])} still have different decisions; structured history resolves part, not all, of this aliasing.", "",
        f"On held-out teacher states, mean feature-range coverage is {pct(phase_reconstruction['confidence_and_ood']['feature_range_coverage_mean'])}. On 16 read-only CurrentBest diagnostic games, coverage is {pct(deployment['overall']['feature_range_coverage_mean'])}, but only {pct(deployment['overall']['ood_confidence_eligible_rate'])} of sampled states pass range + distance + confidence guards. All three teacher heads agree on phase only {pct(deployment['overall']['all_three_phase_agreement_rate'])} of CurrentBest states and on all decision bits {pct(deployment['overall']['all_three_decision_agreement_rate'])}. These are eligibility diagnostics, not actual delegation rates.", "",
        "## 7. Failure analysis", "",
        "- Crop Dusta is the reconstruction bottleneck: decision macro-F1 0.742; melon-cohort F1 0.328, sheep 0.669, cow 0.715, terminal 0.625.",
        "- Shared terminal F1 is 0.682 and shared melon-cohort F1 0.733; both miss the intended robust-control threshold.",
        "- Market HOLD never appears in this corpus, and staggered selling is too rare to reconstruct; a high overall market accuracy therefore overstates mode coverage.",
        "- The model uses its own past feed/hire/plant/sale behavior to identify trajectory state. That memory is deployable, but a CurrentBest continuation does not automatically become a Top3-compatible continuation.",
        "- Teacher disagreement is substantial for cow, sheep and strawberry decisions; this reflects multiple coherent economies and prevents blind averaging.", "",
        "## 8. Executor compatibility and causal gate", "",
        "CurrentBest selects Dmitry/Hanserong/redblack at step 1 and then follows a complete replay action backbone. It can repair weeds, a few transactions and imminent animal misses, but it cannot accept abstract targets. Compatibility is:", "",
        "| Decision | Executor class |", "|---|---|",
    ]
    for name, row in deployment["executor_compatibility"]["decision_compatibility"].items():
        report.append(f"| {name} | {row['class']} — {row['reason']} |")
    report += [
        "", "Therefore same-state strategic counterfactuals, the executable portfolio oracle, fitted-Q and gameplay hybrids were **NOT RUN**. This is not a compute shortcut: there is no coherent alternative continuation to roll out. Adding one land/cow/seed order while retaining the old route would measure executor breakage, while switching to a Top3 replay route would violate the core no-splicing rule.", "",
        "## 9. Required 40-point status", "",
        f"1. Corpus: 219 teacher appearances (86 tetsuya, 66 Crop Dusta, 67 OceanMix), 215 unique valid replay files.",
        "2. Version confidence: high, exact current submission IDs captured at refresh time.",
        "3. Ontology: seven event phases, seven target axes and eight major decision labels.",
        "4. Teacher phases: table in §2; adaptation is mainly within-phase.",
        f"5. Genuine adaptive branch families: {branch_count_text}.",
        "6. Important branch points: livestock ramps, crop cohort launches, premium sale waves and OceanMix terminal timing.",
        "7. Predictive public signals: own capacity/history, feed/hire events, commodity price/inventory history, opponent trajectory and shops; details in §4.",
        f"8. Current-state reconstruction: phase {current['phase']['macro_f1']:.3f}, decisions {current['decisions']['macro_f1']:.3f}.",
        f"9. History reconstruction: phase {h120['phase']['macro_f1']:.3f}, decisions {h120['decisions']['macro_f1']:.3f}.",
        f"10. History ablation: +{history['history_gain_vs_current']['phase_macro_f1']:.3f} phase F1 and +{history['history_gain_vs_current']['decision_macro_f1']:.3f} decision F1 over current state.",
        f"11. Turn-only baseline: phase {turn['phase']['macro_f1']:.3f}, decisions {turn['decisions']['macro_f1']:.3f}.",
        f"12. tetsuya: active phase {phase_active['tetsuya']['active_phase_macro_f1']:.3f}, decisions {decision_by_teacher['tetsuya']['macro_f1']:.3f}.",
        f"13. Crop Dusta: active phase {phase_active['Crop Dusta']['active_phase_macro_f1']:.3f}, decisions {decision_by_teacher['Crop Dusta']['macro_f1']:.3f}.",
        f"14. OceanMix: active phase {phase_active['OceanMix']['active_phase_macro_f1']:.3f}, decisions {decision_by_teacher['OceanMix']['macro_f1']:.3f}.",
        f"15. Major-decision shared macro-F1: {decision_shared['macro_f1']:.3f}; individual table in §5.",
        f"16. Transition timing: recall {h120['transitions']['transition_recall']:.3f}, mean absolute error {h120['transitions']['mean_absolute_timing_error_steps']:.1f} steps.",
        f"17. Remaining aliasing: {pct(history['partial_observability_nearest_neighbor_test']['alias_pairs']['decision_alias_rate_within_close_pairs'])} of closest current-state pairs disagree on a decision.",
        f"18. OOD coverage: teacher holdout {pct(phase_reconstruction['confidence_and_ood']['feature_range_coverage_mean'])}; CurrentBest guard eligibility {pct(deployment['overall']['ood_confidence_eligible_rate'])}.",
        "19. Counterfactual value: NOT RUN—no coherent executable target alternative.",
        "20. High-level portfolio oracle: NOT RUN—only KEEP_CURRENTBEST is executable.",
        "21. Fitted-Q: not justified; no action-return dataset or measured oracle headroom.",
        "22. Hybrid architectures: H1/H2/H3 specified as designs, none built.",
        "23. Strongest hybrid: none.",
        "24. Delegation rate: not measured; no controller. Guard eligibility is 63.5%, not delegation.",
        "25. CurrentBest fallback rate: not measured; would be 100% because no safe delegation was enabled.",
        "26. Paired own-money delta: NOT RUN.",
        "27. Advantage delta: NOT RUN.",
        "28. H2H vs CurrentBest: NOT RUN.",
        "29. H2H vs Rank1: NOT RUN.",
        "30. H2H vs Rank2: NOT RUN.",
        "31. H2H vs Rank3: NOT RUN.",
        "32. Natural RNG: 16 diagnostic observation-only games; no candidate result claimed.",
        "33. P10: NOT RUN.",
        "34. P5: NOT RUN.",
        "35. Safety: no new agent existed to validate; frozen source was not modified.",
        "36. Most valuable learned adaptive decision: none causally established; land timing is best reconstructed but not transferable yet.",
        "37. Largest wrong-branch failure: Crop Dusta melon cohort (F1 0.328), followed by its terminal/sheep/cow targets.",
        "38. Promotion: no; CurrentBest remains frozen.",
        f"39. Current best: `{BASELINE.relative_to(ROOT)}`, SHA-256 `{baseline_sha}`.",
        "40. Recommended next architecture: a safe target-driven economic executor with explicit land/structure/animal/crop commitments and replanning, validated first by exact checkpoint resume and same-state bounded target counterfactuals. Reuse the distilled model only as a guarded target proposer after that executor independently proves coherence.", "",
        "## 10. Final lock", "",
        f"- Frozen research best: `{BASELINE.relative_to(ROOT)}` (`{baseline_sha}`).",
        f"- `submission/main.py` was not modified by this stage; observed SHA-256 `{submission_sha}`.",
        "- No Kaggle submission or upload was performed.",
    ]
    (EXP / "top3_adaptive_distillation_report.md").write_text("\n".join(report) + "\n")

    summary = {
        "corpus_appearances": 219, "best_phase_macro_f1": h120["phase"]["macro_f1"],
        "best_decision_macro_f1": h120["decisions"]["macro_f1"],
        "history_phase_gain": history["history_gain_vs_current"]["phase_macro_f1"],
        "counterfactual_status": counterfactuals["status"], "promoted": False,
        "baseline_sha256": baseline_sha, "submission_sha256": submission_sha,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
