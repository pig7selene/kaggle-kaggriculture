"""Audit teacher-state coverage and CurrentBest executor compatibility.

This script never changes actions.  It observes the frozen CurrentBest in a
small diagnostic panel, projects its public histories into the reconstruction
model, and measures whether a future controller would be in-distribution.
"""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from runpy import run_path

import numpy as np
from kaggle_environments import make

from build_top3_adaptive_dataset import current_features, history_features, action_events
from analyze_v27_routes import normalized_action
from run_post_opening_validation import _load_opponent


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "experiments/top3_adaptive_deployment_audit.json"
BASELINE = "agents/top50_distilled/top50_observable_portfolio.py"
OPPONENTS = {
    "CurrentBest_mirror": BASELINE,
    "tetsuya_medoid": "agents/top3_tuned/raw_rank1_tetsuya.py",
    "CropDusta_medoid": "agents/top3_tuned/raw_rank2_crop_dusta.py",
    "OceanMix_medoid": "agents/top3_tuned/raw_rank3_oceanmix.py",
}
SEEDS = (3910701, 3910702)


def predict(Z, coefficients):
    return Z @ coefficients[:-1] + coefficients[-1]


def load_fresh(path):
    return run_path(str(ROOT / path))["agent"]


def run_game(opponent_path, seed, seat):
    candidate = load_fresh(BASELINE)
    opponent = _load_opponent(opponent_path)
    pair = [opponent, opponent]
    pair[seat] = candidate
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=True)
    env.run(pair)
    replay = env.toJSON()
    actions = [normalized_action(replay, seat, step) for step in range(719)]
    base = [current_features(replay["steps"][step][seat]["observation"], seat) for step in range(719)]
    events = action_events(actions)
    rows = [{**base[step], **history_features(base, events, step)} for step in range(0, 719, 6)]
    final = env.steps[-1]
    return {
        "seed": seed, "seat": seat, "features": rows,
        "money": float(final[seat].reward), "opponent_money": float(final[1 - seat].reward),
        "parent": candidate.telemetry.get("portfolio_parent"),
    }


def main():
    schema = json.loads((ROOT / "experiments/top3_adaptive_feature_schema.json").read_text())
    data = np.load(ROOT / "experiments/top3_adaptive_transition_dataset.npz")
    model = np.load(ROOT / "agents/top3_adaptive_distill/top3_adaptive_reconstruction_models.npz")
    feature_index = schema["feature_index"]
    shared_names = model["shared_feature_names"].astype(str).tolist()
    shared_cols = np.asarray([feature_index[name] for name in shared_names], dtype=np.int32)
    train_mask = data["split"] == 0
    train_Z = ((data["X"][train_mask][:, shared_cols] - model["shared_mean"]) / model["shared_scale"]).astype(np.float32)
    train_min = train_Z.min(axis=0); train_max = train_Z.max(axis=0)
    train_zmax_p99 = float(np.quantile(np.max(np.abs(train_Z), axis=1), .99))
    validation_Z = ((data["X"][data["split"] == 1][:, shared_cols] - model["shared_mean"]) / model["shared_scale"]).astype(np.float32)
    validation_score = predict(validation_Z, model["shared_coefficients"])[:, :7]
    validation_margin = np.sort(validation_score, axis=1)[:, -1] - np.sort(validation_score, axis=1)[:, -2]
    margin_guard = float(np.quantile(validation_margin, .20))

    h72_names = model["history72_feature_names"].astype(str).tolist()
    games = []
    for opponent_name, opponent_path in OPPONENTS.items():
        for seed in SEEDS:
            for seat in (0, 1):
                result = run_game(opponent_path, seed, seat)
                feature_rows = result.pop("features")
                raw = np.asarray([[row[name] for name in shared_names] for row in feature_rows], dtype=np.float32)
                Z = ((raw - model["shared_mean"]) / model["shared_scale"]).astype(np.float32)
                score = predict(Z, model["shared_coefficients"])
                phase_score = score[:, :7]
                ordered = np.sort(phase_score, axis=1)
                margin = ordered[:, -1] - ordered[:, -2]
                coverage = ((Z >= train_min) & (Z <= train_max)).mean(axis=1)
                zmax = np.max(np.abs(Z), axis=1)
                eligible = (coverage >= .99) & (zmax <= train_zmax_p99) & (margin >= margin_guard)

                h72_raw = np.asarray([[row[name] for name in h72_names] for row in feature_rows], dtype=np.float32)
                teacher_phase = []
                teacher_decisions = []
                for rank in (1, 2, 3):
                    teacher_Z = ((h72_raw - model[f"teacher{rank}_mean"]) / model[f"teacher{rank}_scale"]).astype(np.float32)
                    teacher_score = predict(teacher_Z, model[f"teacher{rank}_coefficients"])
                    teacher_phase.append(np.argmax(teacher_score[:, :7], axis=1))
                    teacher_decisions.append(teacher_score[:, 7:] >= model[f"teacher{rank}_thresholds"])
                teacher_phase = np.asarray(teacher_phase)
                teacher_decisions = np.asarray(teacher_decisions)
                result.update({
                    "opponent": opponent_name, "sample_rows": len(Z),
                    "feature_range_coverage_mean": float(np.mean(coverage)),
                    "zmax_p95": float(np.quantile(zmax, .95)),
                    "confidence_margin_mean": float(np.mean(margin)),
                    "ood_confidence_eligible_rate": float(np.mean(eligible)),
                    "all_three_phase_agreement_rate": float(np.mean(np.all(teacher_phase == teacher_phase[0], axis=0))),
                    "all_three_decision_agreement_rate": float(np.mean(np.all(teacher_decisions == teacher_decisions[0], axis=0))),
                })
                games.append(result)
                print(f"deployment audit {len(games)}/{len(OPPONENTS)*len(SEEDS)*2}", flush=True)

    def mean(field, rows):
        return float(np.mean([row[field] for row in rows]))

    by_opponent = {}
    for name in OPPONENTS:
        rows = [row for row in games if row["opponent"] == name]
        by_opponent[name] = {
            "games": len(rows), "feature_range_coverage_mean": mean("feature_range_coverage_mean", rows),
            "ood_confidence_eligible_rate": mean("ood_confidence_eligible_rate", rows),
            "all_three_phase_agreement_rate": mean("all_three_phase_agreement_rate", rows),
            "all_three_decision_agreement_rate": mean("all_three_decision_agreement_rate", rows),
        }

    executor = {
        "baseline": BASELINE,
        "architecture": "step-1 selection among three complete replay backbones, followed by fixed route actions plus bounded repair",
        "decision_compatibility": {
            "BUY_LAND_24": {"class": "NEEDS_NEW_EXECUTOR", "reason": "extra land has no deploy/plant/water route and changes every downstream position anchor"},
            "HIRE_24": {"class": "BOUNDED_SUPPRESSION_ONLY", "reason": "extra hands have no assigned work; fewer hands drop expected route actions"},
            "RAMP_COW_48": {"class": "NEEDS_NEW_EXECUTOR", "reason": "requires coordinated pasture build, pickup/place, wheat logistics and permanent service routes"},
            "RAMP_SHEEP_48": {"class": "NEEDS_NEW_EXECUTOR", "reason": "requires coordinated pasture build, pickup/place, feed/care/fertilizer and harvest routes"},
            "START_MELON_COHORT_48": {"class": "NEEDS_NEW_EXECUTOR", "reason": "requires seed procurement, tile allocation, planting, watering and harvest continuation"},
            "START_STRAWBERRY_COHORT_48": {"class": "NEEDS_NEW_EXECUTOR", "reason": "requires recurring-crop territory and permanent harvest/water scheduling"},
            "SELL_PREMIUM_24": {"class": "PARAMETERIZABLE_WITHIN_EXISTING_SELL_SLOTS_ONLY", "reason": "quantity/timing can be adjusted only when a coherent route already delivers inventory to shed"},
            "ENTER_TERMINAL_24": {"class": "NEEDS_NEW_EXECUTOR", "reason": "stopping planting and draining all field/shed inventory requires coordinated whole-route retiming"},
        },
        "fixed_route_switching_forbidden": True,
        "conclusion": "No reconstructed high-impact land/livestock/crop target can be causally rolled out in CurrentBest without first building a target-driven low-level executor. A fixed Top3 continuation would repeat the already rejected route-splicing failure.",
    }
    payload = {
        "schema_version": 1, "purpose": "read-only deployment-distribution and executor compatibility audit",
        "diagnostic_games": games, "by_opponent": by_opponent,
        "overall": {
            "games": len(games), "feature_range_coverage_mean": mean("feature_range_coverage_mean", games),
            "ood_confidence_eligible_rate": mean("ood_confidence_eligible_rate", games),
            "all_three_phase_agreement_rate": mean("all_three_phase_agreement_rate", games),
            "all_three_decision_agreement_rate": mean("all_three_decision_agreement_rate", games),
        },
        "guards": {"range_coverage_min": .99, "teacher_train_zmax_p99": train_zmax_p99, "validation_phase_margin_p20": margin_guard},
        "executor_compatibility": executor,
    }
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload["overall"], indent=2), flush=True)


if __name__ == "__main__":
    main()
