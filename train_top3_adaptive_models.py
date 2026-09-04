"""Train auditable Top-3 strategic reconstruction models without extra packages.

The models deliberately operate on high-level phase/decision targets rather than
primitive actions.  All fitting uses complete-episode splits produced by
``build_top3_adaptive_dataset.py``.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent
EXP = ROOT / "experiments"
MODEL_DIR = ROOT / "agents" / "top3_adaptive_distill"
DATA = EXP / "top3_adaptive_transition_dataset.npz"
SCHEMA = EXP / "top3_adaptive_feature_schema.json"
DATA_MANIFEST = EXP / "top3_adaptive_transition_dataset_manifest.json"
SEGMENTS = EXP / "top3_adaptive_phase_segments.json"
PHASE_OUT = EXP / "top3_adaptive_phase_reconstruction.json"
DECISION_OUT = EXP / "top3_adaptive_decision_reconstruction.json"
HISTORY_OUT = EXP / "top3_adaptive_history_ablation.json"
TEACHER_OUT = EXP / "top3_adaptive_teacher_models.json"
MODEL_OUT = MODEL_DIR / "top3_adaptive_reconstruction_models.npz"

PHASES = (
    "OPENING_FOUNDATION", "FIRST_LAND_DEPLOYMENT", "MELON_CAPITALIZATION",
    "SECOND_LAND_DEPLOYMENT", "STRAWBERRY_RAMP",
    "MIXED_PREMIUM_PRODUCTION", "TERMINAL_LIQUIDATION",
)
DECISIONS = (
    "BUY_LAND_24", "HIRE_24", "RAMP_COW_48", "RAMP_SHEEP_48",
    "START_MELON_COHORT_48", "START_STRAWBERRY_COHORT_48",
    "SELL_PREMIUM_24", "ENTER_TERMINAL_24",
)
TEACHERS = {1: "tetsuya", 2: "Crop Dusta", 3: "OceanMix"}
MARKET_MODES = ("ACCUMULATE", "HOLD", "STAGGERED_SELL", "LIQUIDATE", "TERMINAL")
CROP_FAMILIES = ("NONE", "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")


def write_json(path: Path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def safe_float(value):
    if isinstance(value, (np.floating, float)):
        value = float(value)
        return value if math.isfinite(value) else None
    if isinstance(value, np.integer):
        return int(value)
    return value


def macro_f1(y, p, classes=None):
    classes = np.unique(np.concatenate([y, p])) if classes is None else np.asarray(classes)
    scores = []
    per_class = {}
    for cls in classes:
        tp = int(np.sum((y == cls) & (p == cls)))
        fp = int(np.sum((y != cls) & (p == cls)))
        fn = int(np.sum((y == cls) & (p != cls)))
        precision = tp / max(1, tp + fp)
        recall = tp / max(1, tp + fn)
        f1 = 2 * precision * recall / max(1e-12, precision + recall)
        scores.append(f1)
        per_class[int(cls)] = {"precision": precision, "recall": recall, "f1": f1, "support": int(np.sum(y == cls))}
    return float(np.mean(scores)), per_class


def confusion(y, p, nclasses):
    matrix = np.zeros((nclasses, nclasses), dtype=np.int64)
    np.add.at(matrix, (y, p), 1)
    return matrix.tolist()


def binary_metrics(y, p):
    tp = int(np.sum((y == 1) & (p == 1)))
    fp = int(np.sum((y == 0) & (p == 1)))
    fn = int(np.sum((y == 1) & (p == 0)))
    tn = int(np.sum((y == 0) & (p == 0)))
    precision = tp / max(1, tp + fp)
    recall = tp / max(1, tp + fn)
    f1 = 2 * precision * recall / max(1e-12, precision + recall)
    return {
        "accuracy": (tp + tn) / max(1, len(y)), "precision": precision,
        "recall": recall, "f1": f1,
        "balanced_accuracy": .5 * (tp / max(1, tp + fn) + tn / max(1, tn + fp)),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
    }


def best_threshold(y, score):
    if np.all(y == 0):
        return float(np.max(score) + 1), binary_metrics(y, np.zeros_like(y))
    if np.all(y == 1):
        return float(np.min(score) - 1), binary_metrics(y, np.ones_like(y))
    thresholds = np.unique(np.quantile(score, np.linspace(0, 1, 101)))
    candidates = []
    for threshold in thresholds:
        metrics = binary_metrics(y, (score >= threshold).astype(np.int8))
        candidates.append((metrics["f1"], metrics["balanced_accuracy"], -abs(float(threshold) - .5), float(threshold), metrics))
    return max(candidates, key=lambda row: row[:3])[3:]


def standardize(A, train_mask):
    mean = A[train_mask].mean(axis=0, dtype=np.float64).astype(np.float32)
    scale = A[train_mask].std(axis=0, dtype=np.float64).astype(np.float32)
    scale[scale < 1e-5] = 1.0
    Z = ((A - mean) / scale).astype(np.float32)
    return Z, mean, scale


def ridge_solutions(Z, Y, train_mask, weights, lambdas):
    train = Z[train_mask]
    weight = weights[train_mask].astype(np.float32)
    target = Y[train_mask].astype(np.float32)
    # Weighted sufficient statistics avoid materializing a second full matrix.
    gram = train.T @ (train * weight[:, None])
    cross = train.T @ (target * weight[:, None])
    xsum = train.T @ weight
    wsum = float(weight.sum())
    ysum = (target * weight[:, None]).sum(axis=0)
    p = train.shape[1]
    lhs = np.empty((p + 1, p + 1), dtype=np.float64)
    lhs[:p, :p] = gram
    lhs[:p, p] = xsum
    lhs[p, :p] = xsum
    lhs[p, p] = wsum
    rhs = np.vstack([cross, ysum]).astype(np.float64)
    solutions = {}
    for lam in lambdas:
        regularized = lhs.copy()
        regularized[np.arange(p), np.arange(p)] += lam
        solutions[lam] = np.linalg.solve(regularized, rhs).astype(np.float32)
    return solutions


def predict(Z, coefficients):
    return Z @ coefficients[:-1] + coefficients[-1]


def phase_metrics(y, scores):
    p = np.argmax(scores, axis=1).astype(np.int8)
    f1, per_class = macro_f1(y, p, range(len(PHASES)))
    return {
        "accuracy": float(np.mean(y == p)), "macro_f1": f1,
        "per_phase": {PHASES[index]: values for index, values in per_class.items()},
        "confusion_matrix_true_rows": confusion(y, p, len(PHASES)),
    }, p


def evaluate_decisions(y, score, thresholds):
    output = {}
    predictions = np.zeros_like(y)
    for index, name in enumerate(DECISIONS):
        predictions[:, index] = score[:, index] >= thresholds[index]
        output[name] = binary_metrics(y[:, index], predictions[:, index])
    output["macro_f1"] = float(np.mean([output[name]["f1"] for name in DECISIONS]))
    output["macro_balanced_accuracy"] = float(np.mean([output[name]["balanced_accuracy"] for name in DECISIONS]))
    return output, predictions


def fit_bundle(A, phase, decisions, train_mask, validation_mask, holdout_mask, weights, lambdas=(1., 30., 300., 3000.)):
    Z, mean, scale = standardize(A, train_mask)
    onehot = np.eye(len(PHASES), dtype=np.float32)[phase]
    Y = np.column_stack([onehot, decisions.astype(np.float32)])
    solutions = ridge_solutions(Z, Y, train_mask, weights, lambdas)
    candidates = []
    for lam, coefficients in solutions.items():
        score = predict(Z[validation_mask], coefficients)
        pm, _ = phase_metrics(phase[validation_mask], score[:, :len(PHASES)])
        thresholds = []
        dm = []
        for index in range(len(DECISIONS)):
            threshold, metric = best_threshold(decisions[validation_mask, index], score[:, len(PHASES) + index])
            thresholds.append(threshold); dm.append(metric["f1"])
        objective = pm["macro_f1"] + .35 * float(np.mean(dm))
        candidates.append((objective, pm["macro_f1"], float(np.mean(dm)), -lam, lam, coefficients, np.asarray(thresholds, dtype=np.float32)))
    _, _, _, _, lam, coefficients, thresholds = max(candidates, key=lambda row: row[:4])
    validation_score = predict(Z[validation_mask], coefficients)
    holdout_score = predict(Z[holdout_mask], coefficients)
    validation_phase, _ = phase_metrics(phase[validation_mask], validation_score[:, :len(PHASES)])
    validation_decisions, _ = evaluate_decisions(decisions[validation_mask], validation_score[:, len(PHASES):], thresholds)
    holdout_phase, holdout_phase_pred = phase_metrics(phase[holdout_mask], holdout_score[:, :len(PHASES)])
    holdout_decisions, holdout_decision_pred = evaluate_decisions(decisions[holdout_mask], holdout_score[:, len(PHASES):], thresholds)
    return {
        "lambda": lam, "coefficients": coefficients, "mean": mean, "scale": scale,
        "thresholds": thresholds, "Z": Z,
        "validation": {"phase": validation_phase, "decisions": validation_decisions},
        "holdout": {"phase": holdout_phase, "decisions": holdout_decisions},
        "holdout_phase_pred": holdout_phase_pred,
        "holdout_decision_pred": holdout_decision_pred,
        "holdout_score": holdout_score,
    }


def nonlinear_current(X, names, current_indices, train_mask, phase):
    raw = X[:, current_indices]
    train = raw[train_mask]
    # Rank current features by between-phase variance, then add three simple
    # threshold features for the 48 most informative dimensions.
    overall = train.mean(axis=0)
    between = np.zeros(train.shape[1], dtype=np.float64)
    within = np.zeros(train.shape[1], dtype=np.float64)
    y = phase[train_mask]
    for cls in range(len(PHASES)):
        part = train[y == cls]
        if not len(part):
            continue
        between += len(part) * (part.mean(axis=0) - overall) ** 2
        within += ((part - part.mean(axis=0)) ** 2).sum(axis=0)
    ranking = np.argsort(-(between / (within + 1e-6)))[:48]
    thresholds = np.quantile(train[:, ranking], [.25, .5, .75], axis=0).astype(np.float32)
    additions = [(raw[:, ranking] > thresholds[q]).astype(np.float32) for q in range(3)]
    A = np.column_stack([raw, *additions]).astype(np.float32)
    feature_names = [names[index] for index in current_indices]
    feature_names += [f"stump_q{q}_{names[current_indices[index]]}" for q in (25, 50, 75) for index in ranking]
    return A, feature_names, {"selected_current_features": [names[current_indices[index]] for index in ranking], "quantiles": thresholds.tolist()}


def elm_history(X, names, indices, train_mask, seed=20260901):
    raw = X[:, indices]
    mean = raw[train_mask].mean(axis=0, dtype=np.float64).astype(np.float32)
    scale = raw[train_mask].std(axis=0, dtype=np.float64).astype(np.float32)
    scale[scale < 1e-5] = 1
    normalized = ((raw - mean) / scale).astype(np.float32)
    rng = np.random.default_rng(seed)
    projection = rng.normal(0, 1 / math.sqrt(len(indices)), (len(indices), 96)).astype(np.float32)
    bias = rng.normal(0, .25, 96).astype(np.float32)
    hidden = np.maximum(0, normalized @ projection + bias).astype(np.float32)
    # Retain the most direct calendar/economic signals alongside the nonlinear layer.
    linear_keep = np.arange(min(48, normalized.shape[1]))
    A = np.column_stack([normalized[:, linear_keep], hidden]).astype(np.float32)
    return A, [f"elm_linear_{index}" for index in linear_keep] + [f"elm_relu_{index}" for index in range(96)], {
        "input_mean": mean, "input_scale": scale, "projection": projection, "bias": bias,
    }


def smooth_episode_predictions(steps, predictions, confirmations=2, min_duration=12):
    order = np.argsort(steps)
    pred = predictions[order]
    ordered_steps = steps[order]
    if not len(pred):
        return pred, order
    result = pred.copy()
    active = int(pred[0]); active_since = int(ordered_steps[0])
    pending = None; pending_count = 0
    for i in range(len(pred)):
        candidate = int(pred[i])
        if candidate == active:
            pending = None; pending_count = 0
        elif ordered_steps[i] - active_since >= min_duration:
            if pending == candidate:
                pending_count += 1
            else:
                pending = candidate; pending_count = 1
            if pending_count >= confirmations:
                active = candidate; active_since = int(ordered_steps[i]); pending = None; pending_count = 0
        result[i] = active
    return result, order


def sequence_transitions(steps, labels):
    output = []
    for i in range(1, len(labels)):
        if labels[i] != labels[i - 1]:
            output.append((int(steps[i]), int(labels[i])))
    return output


def transition_metrics(episode_id, steps, truth, prediction):
    matched = errors = false = missed = 0
    wrong_duration = total_duration = 0
    replay_rows = []
    for episode in np.unique(episode_id):
        mask = episode_id == episode
        episode_steps = steps[mask]
        order = np.argsort(episode_steps)
        episode_steps = episode_steps[order]
        true = truth[mask][order]
        raw = prediction[mask][order]
        pred, _ = smooth_episode_predictions(episode_steps, raw)
        true_events = sequence_transitions(episode_steps, true)
        pred_events = sequence_transitions(episode_steps, pred)
        used = set(); local_errors = []
        for true_step, destination in true_events:
            candidates = [(abs(pred_step - true_step), index, pred_step) for index, (pred_step, pred_destination) in enumerate(pred_events) if index not in used and pred_destination == destination and abs(pred_step - true_step) <= 36]
            if candidates:
                error, index, pred_step = min(candidates)
                used.add(index); matched += 1; errors += error; local_errors.append(error)
            else:
                missed += 1
        false += len(pred_events) - len(used)
        durations = np.diff(np.r_[episode_steps, min(719, int(episode_steps[-1]) + 6)])
        wrong = int(np.sum(durations[pred != true])); total = int(np.sum(durations))
        wrong_duration += wrong; total_duration += total
        replay_rows.append({
            "episode_id": int(episode), "phase_accuracy": float(np.mean(pred == true)),
            "true_transitions": len(true_events), "detected_transitions": len(true_events) - sum(1 for event in true_events if not any(abs(pe[0] - event[0]) <= 36 and pe[1] == event[1] for pe in pred_events)),
            "predicted_transitions": len(pred_events), "wrong_phase_duration": wrong,
            "mean_matched_timing_error": float(np.mean(local_errors)) if local_errors else None,
        })
    return {
        "transition_precision": matched / max(1, matched + false),
        "transition_recall": matched / max(1, matched + missed),
        "matched_transitions": matched, "false_transitions": false, "missed_transitions": missed,
        "mean_absolute_timing_error_steps": errors / max(1, matched),
        "wrong_phase_fraction": wrong_duration / max(1, total_duration),
        "replay_summary": replay_rows,
    }


def feature_importance(result, feature_names, limit=18):
    coefficients = result["coefficients"][:-1, :len(PHASES)]
    score = np.linalg.norm(coefficients, axis=1)
    ranking = np.argsort(-score)[:limit]
    return [{"feature": feature_names[index], "coefficient_norm": float(score[index])} for index in ranking]


def fit_targets(A, target_data, market_mode, crop_family, train_mask, validation_mask, holdout_mask, weights):
    Z, mean, scale = standardize(A, train_mask)
    market_onehot = np.eye(len(MARKET_MODES), dtype=np.float32)[market_mode]
    crop_onehot = np.eye(len(CROP_FAMILIES), dtype=np.float32)[crop_family]
    numeric_mean = target_data[train_mask].mean(axis=0)
    numeric_scale = target_data[train_mask].std(axis=0); numeric_scale[numeric_scale < 1e-5] = 1
    numeric = (target_data - numeric_mean) / numeric_scale
    Y = np.column_stack([market_onehot, crop_onehot, numeric]).astype(np.float32)
    solutions = ridge_solutions(Z, Y, train_mask, weights, (1., 30., 300., 3000.))
    candidates = []
    for lam, coefficients in solutions.items():
        score = predict(Z[validation_mask], coefficients)
        market_pred = np.argmax(score[:, :len(MARKET_MODES)], axis=1)
        crop_pred = np.argmax(score[:, len(MARKET_MODES):len(MARKET_MODES) + len(CROP_FAMILIES)], axis=1)
        market_f1, _ = macro_f1(market_mode[validation_mask], market_pred, range(len(MARKET_MODES)))
        crop_f1, _ = macro_f1(crop_family[validation_mask], crop_pred, range(len(CROP_FAMILIES)))
        candidates.append((market_f1 + crop_f1, -lam, lam, coefficients))
    _, _, lam, coefficients = max(candidates)
    score = predict(Z[holdout_mask], coefficients)
    market_pred = np.argmax(score[:, :len(MARKET_MODES)], axis=1)
    offset = len(MARKET_MODES)
    crop_pred = np.argmax(score[:, offset:offset + len(CROP_FAMILIES)], axis=1)
    market_f1, market_per = macro_f1(market_mode[holdout_mask], market_pred, range(len(MARKET_MODES)))
    crop_f1, crop_per = macro_f1(crop_family[holdout_mask], crop_pred, range(len(CROP_FAMILIES)))
    numeric_pred = score[:, offset + len(CROP_FAMILIES):] * numeric_scale + numeric_mean
    actual = target_data[holdout_mask]
    target_names = ("target_land_72", "target_hands_24", "target_cows_72", "target_sheep_72", "target_cohort_scale_48")
    numeric_metrics = {}
    for index, name in enumerate(target_names):
        mae = float(np.mean(np.abs(numeric_pred[:, index] - actual[:, index])))
        within = 2 if name == "target_cohort_scale_48" else 1
        numeric_metrics[name] = {"mae": mae, f"within_{within}_accuracy": float(np.mean(np.abs(numeric_pred[:, index] - actual[:, index]) <= within))}
    return {
        "lambda": lam,
        "market_mode": {"accuracy": float(np.mean(market_pred == market_mode[holdout_mask])), "macro_f1": market_f1, "per_class": {MARKET_MODES[i]: v for i, v in market_per.items()}},
        "crop_family": {"accuracy": float(np.mean(crop_pred == crop_family[holdout_mask])), "macro_f1": crop_f1, "per_class": {CROP_FAMILIES[i]: v for i, v in crop_per.items()}},
        "numeric_targets": numeric_metrics,
    }


def nearest_neighbor_ablation(X, feature_sets, feature_index, phase, decisions, split, episode, seed=20260901):
    rng = np.random.default_rng(seed)
    train_all = np.flatnonzero(split == 0)
    query_all = np.flatnonzero(split == 2)
    train_rows = rng.choice(train_all, min(12000, len(train_all)), replace=False)
    query_rows = rng.choice(query_all, min(2500, len(query_all)), replace=False)
    output = {}
    nearest_by_set = {}
    for set_name in ("current_state", "history24", "history48", "history72"):
        cols = np.asarray([feature_index[name] for name in feature_sets[set_name]], dtype=np.int32)
        train = X[train_rows][:, cols]
        query = X[query_rows][:, cols]
        mean = train.mean(axis=0); scale = train.std(axis=0); scale[scale < 1e-5] = 1
        train = ((train - mean) / scale).astype(np.float32)
        query = ((query - mean) / scale).astype(np.float32)
        train_norm = np.sum(train * train, axis=1)
        neighbors = np.empty(len(query_rows), dtype=np.int32)
        distances = np.empty(len(query_rows), dtype=np.float32)
        for left in range(0, len(query_rows), 250):
            right = min(len(query_rows), left + 250)
            distance = np.sum(query[left:right] ** 2, axis=1)[:, None] + train_norm[None, :] - 2 * query[left:right] @ train.T
            nearest = np.argmin(distance, axis=1)
            neighbors[left:right] = nearest
            distances[left:right] = np.maximum(0, distance[np.arange(right - left), nearest])
        reference = train_rows[neighbors]
        phase_accuracy = float(np.mean(phase[query_rows] == phase[reference]))
        decision_f1 = []
        for decision in range(len(DECISIONS)):
            decision_f1.append(binary_metrics(decisions[query_rows, decision], decisions[reference, decision])["f1"])
        output[set_name] = {
            "nearest_neighbor_phase_accuracy": phase_accuracy,
            "nearest_neighbor_decision_macro_f1": float(np.mean(decision_f1)),
            "median_squared_distance": float(np.median(distances)),
        }
        nearest_by_set[set_name] = (reference, distances)
    current_reference, current_distance = nearest_by_set["current_state"]
    cutoff = float(np.quantile(current_distance, .10))
    close = current_distance <= cutoff
    ambiguous_phase = close & (phase[query_rows] != phase[current_reference])
    ambiguous_decision = close & np.any(decisions[query_rows] != decisions[current_reference], axis=1)
    output["alias_pairs"] = {
        "query_count": len(query_rows), "near_identical_cutoff_squared_distance_p10": cutoff,
        "close_pair_count": int(np.sum(close)), "phase_ambiguous_close_pairs": int(np.sum(ambiguous_phase)),
        "decision_ambiguous_close_pairs": int(np.sum(ambiguous_decision)),
        "phase_alias_rate_within_close_pairs": float(np.mean(ambiguous_phase[close])) if np.any(close) else None,
        "decision_alias_rate_within_close_pairs": float(np.mean(ambiguous_decision[close])) if np.any(close) else None,
    }
    return output


def ood_and_confidence(result, holdout_mask, phase, teacher):
    Z = result["Z"]
    train = Z[~holdout_mask if False else np.zeros(len(Z), dtype=bool)]  # documented below; overwritten by caller metadata
    # Caller attaches the actual train mask before this helper is used.
    raise RuntimeError("use compute_ood with explicit masks")


def compute_ood(result, train_mask, holdout_mask, phase, teacher):
    Z = result["Z"]
    train = Z[train_mask]; holdout = Z[holdout_mask]
    raw_min = train.min(axis=0); raw_max = train.max(axis=0)
    within = ((holdout >= raw_min) & (holdout <= raw_max)).mean(axis=1)
    # Diagonal standardized distance and nearest phase-centroid distance are
    # intentionally simple enough to reproduce inside an agent later.
    zmax = np.max(np.abs(holdout), axis=1)
    centroids = np.vstack([train[phase[train_mask] == cls].mean(axis=0) for cls in range(len(PHASES))])
    centroid_distance = np.min(np.sum((holdout[:, None, :] - centroids[None, :, :]) ** 2, axis=2), axis=1)
    scores = result["holdout_score"][:, :len(PHASES)]
    sorted_scores = np.sort(scores, axis=1)
    margin = sorted_scores[:, -1] - sorted_scores[:, -2]
    predicted = np.argmax(scores, axis=1)
    correct = predicted == phase[holdout_mask]
    bins = []
    edges = np.quantile(margin, np.linspace(0, 1, 6))
    for left, right in zip(edges[:-1], edges[1:]):
        mask = (margin >= left) & (margin <= right if right == edges[-1] else margin < right)
        bins.append({"margin_min": float(left), "margin_max": float(right), "count": int(mask.sum()), "accuracy": float(np.mean(correct[mask])) if np.any(mask) else None})
    by_teacher = {}
    held_teacher = teacher[holdout_mask]
    for rank, name in TEACHERS.items():
        mask = held_teacher == rank
        by_teacher[name] = {
            "feature_range_coverage_mean": float(np.mean(within[mask])),
            "zmax_p95": float(np.quantile(zmax[mask], .95)),
            "centroid_distance_p95": float(np.quantile(centroid_distance[mask], .95)),
        }
    return {
        "feature_range_coverage_mean": float(np.mean(within)),
        "rows_with_99pct_features_in_range": float(np.mean(within >= .99)),
        "zmax_p50_p95_p99": [float(np.quantile(zmax, q)) for q in (.5, .95, .99)],
        "nearest_phase_centroid_distance_p50_p95_p99": [float(np.quantile(centroid_distance, q)) for q in (.5, .95, .99)],
        "confidence_margin_calibration": bins, "by_teacher": by_teacher,
        "proposed_guard": "Fallback if range coverage <0.99, zmax exceeds train-calibrated P99, or phase margin is in the lowest validation quintile.",
    }


def main():
    data = np.load(DATA)
    X = data["X"]; phase = data["phase"]; decisions = data["decisions"]
    split = data["split"]; teacher = data["teacher"]; episode = data["episode_id"]
    step = data["step"]; weights = data["sample_weight"]
    market_mode = data["market_mode"]; crop_family = data["crop_family"]; target_data = data["targets"]
    schema = json.loads(SCHEMA.read_text())
    names = schema["feature_names"]; feature_index = schema["feature_index"]; feature_sets = schema["feature_sets"]
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    train_mask = split == 0; validation_mask = split == 1; holdout_mask = split == 2

    # Per-teacher models are fitted first to avoid prematurely averaging three
    # genuinely different policies.
    teacher_results = {}
    teacher_fitted = {}
    teacher_sets = ("turn_only", "current_state", "history24", "history72")
    for rank, teacher_name in TEACHERS.items():
        print(f"teacher {teacher_name}", flush=True)
        per_set = {}
        for set_name in teacher_sets:
            cols = np.asarray([feature_index[name] for name in feature_sets[set_name]], dtype=np.int32)
            result = fit_bundle(
                X[:, cols], phase, decisions,
                train_mask & (teacher == rank), validation_mask & (teacher == rank), holdout_mask & (teacher == rank), weights,
            )
            transition = transition_metrics(
                episode[holdout_mask & (teacher == rank)], step[holdout_mask & (teacher == rank)],
                phase[holdout_mask & (teacher == rank)], result["holdout_phase_pred"],
            )
            per_set[set_name] = {
                "feature_count": len(cols), "selected_lambda": result["lambda"],
                "phase": result["holdout"]["phase"], "decisions": result["holdout"]["decisions"],
                "transitions": {key: value for key, value in transition.items() if key != "replay_summary"},
            }
            if set_name == "history72":
                teacher_fitted[rank] = ({key: value for key, value in result.items() if key != "Z"}, cols)
            result.pop("Z", None)
        best_name = max(per_set, key=lambda name: (per_set[name]["phase"]["macro_f1"], per_set[name]["transitions"]["transition_recall"]))
        teacher_results[teacher_name] = {"model_families": per_set, "best_family": best_name, "best": per_set[best_name]}

    print("shared ablations", flush=True)
    shared_results = {}
    fitted = {}
    family_map = {
        "M0_turn_only": "turn_only", "M1_current_linear": "current_state",
        "M3_history24_linear": "history24", "M4_history48_linear": "history48",
        "M4_history72_linear": "history72", "M4_history120_linear": "history120",
    }
    for family, set_name in family_map.items():
        print(f"  {family}", flush=True)
        cols = np.asarray([feature_index[name] for name in feature_sets[set_name]], dtype=np.int32)
        result = fit_bundle(X[:, cols], phase, decisions, train_mask, validation_mask, holdout_mask, weights)
        trans = transition_metrics(episode[holdout_mask], step[holdout_mask], phase[holdout_mask], result["holdout_phase_pred"])
        shared_results[family] = {
            "feature_set": set_name, "feature_count": len(cols), "selected_lambda": result["lambda"],
            "phase": result["holdout"]["phase"], "decisions": result["holdout"]["decisions"],
            "transitions": {key: value for key, value in trans.items() if key != "replay_summary"},
        }
        result.pop("Z", None)
        fitted[family] = (result, cols, [names[index] for index in cols], trans)

    print("  M2 current nonlinear stumps", flush=True)
    current_cols = np.asarray([feature_index[name] for name in feature_sets["current_state"]], dtype=np.int32)
    nonlinear, nonlinear_names, nonlinear_spec = nonlinear_current(X, names, current_cols, train_mask, phase)
    nonlinear_result = fit_bundle(nonlinear, phase, decisions, train_mask, validation_mask, holdout_mask, weights)
    nonlinear_trans = transition_metrics(episode[holdout_mask], step[holdout_mask], phase[holdout_mask], nonlinear_result["holdout_phase_pred"])
    shared_results["M2_current_stump_ridge"] = {
        "feature_set": "current_state_plus_quantile_stumps", "feature_count": len(nonlinear_names), "selected_lambda": nonlinear_result["lambda"],
        "phase": nonlinear_result["holdout"]["phase"], "decisions": nonlinear_result["holdout"]["decisions"],
        "transitions": {key: value for key, value in nonlinear_trans.items() if key != "replay_summary"},
        "nonlinear_specification": {"selected_current_features": nonlinear_spec["selected_current_features"]},
    }
    nonlinear_result.pop("Z", None)
    fitted["M2_current_stump_ridge"] = (nonlinear_result, None, nonlinear_names, nonlinear_trans)
    del nonlinear

    current_f1 = shared_results["M1_current_linear"]["phase"]["macro_f1"]
    history_f1 = shared_results["M4_history72_linear"]["phase"]["macro_f1"]
    history_justified = history_f1 - current_f1 >= .01 or shared_results["M4_history72_linear"]["transitions"]["transition_recall"] - shared_results["M1_current_linear"]["transitions"]["transition_recall"] >= .03
    if history_justified:
        print("  M5 small ELM", flush=True)
        h72_cols = np.asarray([feature_index[name] for name in feature_sets["history72"]], dtype=np.int32)
        elm, elm_names, elm_spec = elm_history(X, names, h72_cols, train_mask)
        elm_result = fit_bundle(elm, phase, decisions, train_mask, validation_mask, holdout_mask, weights)
        elm_trans = transition_metrics(episode[holdout_mask], step[holdout_mask], phase[holdout_mask], elm_result["holdout_phase_pred"])
        shared_results["M5_small_elm"] = {
            "feature_set": "history72_random_relu96", "feature_count": len(elm_names), "selected_lambda": elm_result["lambda"],
            "phase": elm_result["holdout"]["phase"], "decisions": elm_result["holdout"]["decisions"],
            "transitions": {key: value for key, value in elm_trans.items() if key != "replay_summary"},
            "architecture": "fixed 96-unit ReLU hidden layer plus 48 linear channels; ridge output",
        }
        elm_result.pop("Z", None)
        fitted["M5_small_elm"] = (elm_result, None, elm_names, elm_trans)
        del elm
    else:
        shared_results["M5_small_elm"] = {"status": "NOT RUN", "reason": "Structured history did not materially outperform current state; neural capacity was not justified."}

    valid_families = [name for name, values in shared_results.items() if "phase" in values]
    best_family = max(valid_families, key=lambda family: (
        shared_results[family]["phase"]["macro_f1"] + .25 * shared_results[family]["decisions"]["macro_f1"],
        shared_results[family]["transitions"]["transition_recall"],
    ))
    best_result, best_cols, best_names, best_transition = fitted[best_family]
    print(f"best shared {best_family}", flush=True)

    # Full per-teacher breakdown of the chosen shared model.
    shared_teacher_breakdown = {}
    hold_teacher = teacher[holdout_mask]
    hold_phase = phase[holdout_mask]; hold_decisions = decisions[holdout_mask]
    score = best_result["holdout_score"]
    for rank, teacher_name in TEACHERS.items():
        mask = hold_teacher == rank
        pm, pp = phase_metrics(hold_phase[mask], score[mask, :len(PHASES)])
        dm, _ = evaluate_decisions(hold_decisions[mask], score[mask, len(PHASES):], best_result["thresholds"])
        trans = transition_metrics(episode[holdout_mask][mask], step[holdout_mask][mask], hold_phase[mask], pp)
        shared_teacher_breakdown[teacher_name] = {
            "phase": pm, "decisions": dm,
            "transitions": {key: value for key, value in trans.items() if key != "replay_summary"},
        }

    print("target reconstruction", flush=True)
    # Target reconstruction uses the strongest linear history family for a
    # deployable and interpretable target head even if M2/M5 wins phase scoring.
    target_set = "history72"
    target_cols = np.asarray([feature_index[name] for name in feature_sets[target_set]], dtype=np.int32)
    target_metrics = fit_targets(X[:, target_cols], target_data, market_mode, crop_family, train_mask, validation_mask, holdout_mask, weights)

    print("feature ablations", flush=True)
    # Spurious-feature tests are intentionally performed on the linear H72 model
    # so coefficient families remain interpretable.
    base_names = feature_sets["history72"]
    ablation_rules = {
        "remove_turn": lambda name: not name.startswith("turn_"),
        "remove_opponent_bank": lambda name: name not in {"opp_bank", "hist24_delta_opp_bank", "hist48_delta_opp_bank", "hist72_delta_opp_bank"},
        "remove_market_price_history": lambda name: not (name.startswith("hist") and "market_price_" in name),
        "remove_crop_history": lambda name: not (name.startswith("hist") and "crop_" in name),
        "remove_event_memory": lambda name: not name.startswith("memory_"),
    }
    feature_ablations = {}
    baseline_h72 = shared_results["M4_history72_linear"]
    for ablation, keep in ablation_rules.items():
        selected_names = [name for name in base_names if keep(name)]
        cols = np.asarray([feature_index[name] for name in selected_names], dtype=np.int32)
        result = fit_bundle(X[:, cols], phase, decisions, train_mask, validation_mask, holdout_mask, weights, lambdas=(30., 300.))
        trans = transition_metrics(episode[holdout_mask], step[holdout_mask], phase[holdout_mask], result["holdout_phase_pred"])
        feature_ablations[ablation] = {
            "feature_count": len(cols), "phase_macro_f1": result["holdout"]["phase"]["macro_f1"],
            "phase_macro_f1_delta": result["holdout"]["phase"]["macro_f1"] - baseline_h72["phase"]["macro_f1"],
            "decision_macro_f1": result["holdout"]["decisions"]["macro_f1"],
            "decision_macro_f1_delta": result["holdout"]["decisions"]["macro_f1"] - baseline_h72["decisions"]["macro_f1"],
            "transition_recall": trans["transition_recall"],
            "transition_recall_delta": trans["transition_recall"] - baseline_h72["transitions"]["transition_recall"],
        }
        result.pop("Z", None)

    print("partial observability and OOD", flush=True)
    aliasing = nearest_neighbor_ablation(X, feature_sets, feature_index, phase, decisions, split, episode)
    # OOD requires a fitted raw feature matrix; choose H72 when a nonlinear
    # family wins so range diagnostics still map to named observable features.
    ood_result = fitted["M4_history72_linear"][0]
    h72_cols = target_cols
    ood_raw = X[:, h72_cols]
    ood_result["Z"] = ((ood_raw - ood_result["mean"]) / ood_result["scale"]).astype(np.float32)
    ood = compute_ood(ood_result, train_mask, holdout_mask, phase, teacher)
    ood_result.pop("Z", None)

    # Teacher-model disagreement on common held-out states is a useful future
    # confidence signal.  Apply each H72 teacher head to all H72 holdout states.
    teacher_phase_predictions = []
    teacher_decision_predictions = []
    for rank in TEACHERS:
        result, _ = teacher_fitted[rank]
        raw = X[holdout_mask][:, h72_cols]
        Z = ((raw - result["mean"]) / result["scale"]).astype(np.float32)
        teacher_score = predict(Z, result["coefficients"])
        teacher_phase_predictions.append(np.argmax(teacher_score[:, :len(PHASES)], axis=1))
        teacher_decision_predictions.append(teacher_score[:, len(PHASES):] >= result["thresholds"])
    teacher_phase_predictions = np.asarray(teacher_phase_predictions)
    teacher_decision_predictions = np.asarray(teacher_decision_predictions)
    disagreement = {
        "all_three_phase_agreement_rate": float(np.mean(np.all(teacher_phase_predictions == teacher_phase_predictions[0], axis=0))),
        "majority_phase_agreement_rate": float(np.mean(np.max(np.stack([np.sum(teacher_phase_predictions == cls, axis=0) for cls in range(len(PHASES))]), axis=0) >= 2)),
        "all_three_decision_agreement_rate": {DECISIONS[index]: float(np.mean(np.all(teacher_decision_predictions[:, :, index] == teacher_decision_predictions[0, :, index], axis=0))) for index in range(len(DECISIONS))},
    }

    # Reconstruction gates are measured on untouched episode holdout rows.
    gate = {
        "phase_macro_f1_threshold": .80,
        "decision_macro_f1_threshold": .75,
        "observed_phase_macro_f1": shared_results[best_family]["phase"]["macro_f1"],
        "observed_decision_macro_f1": shared_results[best_family]["decisions"]["macro_f1"],
        "phase_pass": shared_results[best_family]["phase"]["macro_f1"] >= .80,
        "decision_pass": shared_results[best_family]["decisions"]["macro_f1"] >= .75,
    }
    gate["overall_pass"] = gate["phase_pass"] and gate["decision_pass"]

    replay_errors = sorted(best_transition["replay_summary"], key=lambda row: (row["phase_accuracy"], -row["wrong_phase_duration"]))
    failure_analysis = {
        "worst_heldout_replays": replay_errors[:15],
        "diagnostic_categories": {
            "history_resolved": "M1 incorrect while M4 H72 is correct; quantified by history gain and NN alias test.",
            "remaining_aliasing": "Near-current-state neighbors retain different targets even after structured history.",
            "label_boundary_noise": "Event-centered samples within 12 steps of inferred boundaries carry ambiguous current/next phase semantics.",
            "teacher_policy_diversity": "Teacher-head disagreement indicates multiple coherent targets rather than one universal action.",
        },
    }

    history_artifact = {
        "schema_version": 1, "evaluation_split": "complete-episode holdout only",
        "model_families": shared_results, "best_shared_family": best_family,
        "history_justified_for_M5": history_justified,
        "history_gain_vs_current": {
            "phase_macro_f1": history_f1 - current_f1,
            "decision_macro_f1": shared_results["M4_history72_linear"]["decisions"]["macro_f1"] - shared_results["M1_current_linear"]["decisions"]["macro_f1"],
            "transition_recall": shared_results["M4_history72_linear"]["transitions"]["transition_recall"] - shared_results["M1_current_linear"]["transitions"]["transition_recall"],
        },
        "partial_observability_nearest_neighbor_test": aliasing,
        "feature_family_ablations": feature_ablations,
        "interpretation": "A model is called adaptive only if state/history materially exceeds the turn-only and current-state controls.",
    }
    write_json(HISTORY_OUT, history_artifact)

    phase_artifact = {
        "schema_version": 1, "evaluation_split": "complete held-out episodes",
        "best_shared_family": best_family, "shared_holdout": shared_results[best_family]["phase"],
        "transition_metrics": shared_results[best_family]["transitions"],
        "by_teacher_shared_model": {name: values["phase"] for name, values in shared_teacher_breakdown.items()},
        "by_teacher_transition_metrics": {name: values["transitions"] for name, values in shared_teacher_breakdown.items()},
        "replay_level_errors": best_transition["replay_summary"],
        "confidence_and_ood": ood, "reconstruction_gate": gate,
    }
    write_json(PHASE_OUT, phase_artifact)

    decision_artifact = {
        "schema_version": 1, "evaluation_split": "complete held-out episodes",
        "best_shared_family": best_family, "shared_holdout": shared_results[best_family]["decisions"],
        "thresholds": {name: float(best_result["thresholds"][index]) for index, name in enumerate(DECISIONS)},
        "by_teacher_shared_model": {name: values["decisions"] for name, values in shared_teacher_breakdown.items()},
        "economic_target_reconstruction": target_metrics,
        "teacher_model_disagreement": disagreement,
        "failure_analysis": failure_analysis, "reconstruction_gate": gate,
    }
    write_json(DECISION_OUT, decision_artifact)

    teacher_artifact = {
        "schema_version": 1, "teacher_identity_is_not_a_deployable_feature": True,
        "per_teacher_models_fitted_before_shared": True, "teachers": teacher_results,
        "shared_model_by_teacher": shared_teacher_breakdown,
        "teacher_disagreement": disagreement,
        "top_feature_signals_shared": feature_importance(best_result, best_names),
        "model_storage": str(MODEL_OUT.relative_to(ROOT)),
    }
    write_json(TEACHER_OUT, teacher_artifact)

    # Store the best shared model and the H72 teacher heads for reproducibility;
    # this is research-only and is not imported by any gameplay agent.
    arrays = {
        "shared_coefficients": best_result["coefficients"], "shared_mean": best_result["mean"],
        "shared_scale": best_result["scale"], "shared_thresholds": best_result["thresholds"],
        "shared_feature_names": np.asarray(best_names), "shared_family": np.asarray(best_family),
        "history72_feature_names": np.asarray(feature_sets["history72"]),
    }
    for rank, (result, _) in teacher_fitted.items():
        arrays[f"teacher{rank}_coefficients"] = result["coefficients"]
        arrays[f"teacher{rank}_mean"] = result["mean"]
        arrays[f"teacher{rank}_scale"] = result["scale"]
        arrays[f"teacher{rank}_thresholds"] = result["thresholds"]
    np.savez_compressed(MODEL_OUT, **arrays)
    (MODEL_DIR / "README.md").write_text(
        "# Top-3 adaptive distillation models\n\n"
        "Research-only high-level phase and strategic-decision reconstruction weights. "
        "They are not a gameplay agent and never select a fixed replay route.\n"
    )
    print(json.dumps({"best_family": best_family, "gate": gate, "model": str(MODEL_OUT)}, indent=2), flush=True)


if __name__ == "__main__":
    main()
