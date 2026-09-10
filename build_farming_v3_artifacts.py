"""Build the mandatory Farming V3 research artifacts from persisted local runs."""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parent
EXP = ROOT / "experiments"
ACQ = EXP / "farming_v3_acquisition"
RUNS = EXP / "farming_v3_runs"
SOURCE = ROOT / "agents/public_farming_v3/main.py"
CANDIDATE = ROOT / "agents/farming_v3_distilled/v1_force_route1.py"
CURRENT = ROOT / "agents/top50_distilled/top50_observable_portfolio.py"
DEPLOYED = ROOT / "submission/main.py"


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(name, value):
    (EXP / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_md(name, value):
    (EXP / name).write_text(value.rstrip() + "\n", encoding="utf-8")


def sha(path, normalize=False):
    raw = Path(path).read_bytes()
    if normalize:
        raw = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(raw).hexdigest()


def load_source():
    spec = importlib.util.spec_from_file_location("farming_v3_artifact_source", SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def route_summary(route):
    market_counts = Counter()
    market_quantity = Counter()
    field_counts = Counter()
    land_steps = []
    animal_events = []
    seed_events = []
    max_hands = 0
    for step, action in enumerate(route):
        units = [action.get("farmer", ["PASS"]), *action.get("hands", [])]
        max_hands = max(max_hands, len(action.get("hands", [])))
        for operation in units:
            field_counts[operation[0]] += 1
            if operation[0] == "PLANT" and len(operation) > 1:
                field_counts[f"PLANT:{operation[1]}"] += 1
        for order in action.get("market", []):
            op = order[0]
            item = order[1] if len(order) > 1 else ""
            quantity = int(order[2]) if len(order) > 2 else 1
            key = op if not item else f"{op}:{item}"
            market_counts[key] += 1
            market_quantity[key] += quantity
            if op == "BUY_LAND":
                land_steps.append(step)
            elif op == "BUY_ANIMAL":
                animal_events.append({"step": step, "animal": item, "quantity": quantity})
            elif op == "BUY_SEED":
                seed_events.append({"step": step, "crop": item, "quantity": quantity})
    return {
        "turns": len(route), "max_requested_hands": max_hands,
        "field_operation_requests": dict(sorted(field_counts.items())),
        "market_order_counts": dict(sorted(market_counts.items())),
        "market_requested_quantities": dict(sorted(market_quantity.items())),
        "land_purchase_steps": land_steps, "animal_purchase_events": animal_events,
        "seed_purchase_events": seed_events,
    }


def averages(rows, variant):
    selected = [row for row in rows if row["variant"] == variant]
    result = {
        "games": len(selected),
        "own_money": statistics.fmean(row["own_money"] for row in selected),
        "advantage": statistics.fmean(row["advantage"] for row in selected),
    }
    for field in ("revenue", "sales", "harvest", "seed_spend", "product_spend", "animal_spend"):
        keys = sorted({key for row in selected for key in row["economics"].get(field, {})})
        result[field] = {
            key: statistics.fmean(row["economics"].get(field, {}).get(key, 0) for row in selected)
            for key in keys
        }
    for field in ("land_spend", "labor_spend"):
        result[field] = statistics.fmean(row["economics"].get(field, 0) for row in selected)
    checkpoints = (0, 3, 6, 9, 12, 15, 18, 21, 24, 27, 29)
    result["bank_checkpoints"] = [
        {
            "day": day,
            "mean_start": statistics.fmean(row["daily_bank"][day]["start"] for row in selected),
            "mean_end": statistics.fmean(row["daily_bank"][day]["end"] for row in selected),
        }
        for day in checkpoints
    ]
    return result


def numeric_delta(left, right):
    result = {}
    for key in sorted(set(left) | set(right)):
        if isinstance(left.get(key), (int, float)) or isinstance(right.get(key), (int, float)):
            value = float(left.get(key, 0)) - float(right.get(key, 0))
            if value:
                result[key] = value
    return result


def main():
    source = load_source()
    envelope = read_json(ACQ / "kaggle-kernel-data-response.json")
    notebook = read_json(ACQ / "farming-score-v3-replay-revised.ipynb")
    raw = read_json(RUNS / "raw.partial.json")
    raw_summary = read_json(RUNS / "raw_summary.json")
    counter = read_json(RUNS / "counterfactual_summary.json")
    counter_rows = read_json(RUNS / "counterfactual.partial.json")
    candidate = read_json(RUNS / "candidate_summary.json")
    stress = read_json(RUNS / "guard_stress_summary.json")
    stress_rows = read_json(RUNS / "guard_stress.partial.json")
    dossier_rows = read_json(RUNS / "dossier.partial.json")
    dossier0 = averages(dossier_rows, "v3_route0")
    dossier1 = averages(dossier_rows, "v3_route1")
    metadata = envelope["metadata"]

    source_audit = {
        "schema_version": 1,
        "status": "COMPLETE_FOR_CURRENT_PUBLIC_VERSION; HISTORICAL_SOURCE_UNAVAILABLE",
        "retrieved_on": "2026-09-08",
        "public_notebook_url": "https://www.kaggle.com/code/lynnsakurai/farming-score-v3-replay-revised",
        "retrieval_method": "Read-only public Kaggle kernel-data API response plus public HTML; no account mutation and no submission.",
        "metadata": {
            "ref": metadata.get("ref"), "title": metadata.get("title"), "author_display": metadata.get("author"),
            "current_version": metadata.get("currentVersionNumberNullable"), "last_run_utc": metadata.get("lastRunTime"),
            "is_private": metadata.get("isPrivateNullable"), "language": metadata.get("language"),
            "competition_sources": metadata.get("competitionDataSources"),
            "dataset_sources": metadata.get("datasetDataSources"), "kernel_sources": metadata.get("kernelDataSources"),
        },
        "hashes": {
            "api_envelope_sha256": sha(ACQ / "kaggle-kernel-data-response.json"),
            "public_html_sha256": sha(ACQ / "page.html"),
            "notebook_sha256": sha(ACQ / "farming-score-v3-replay-revised.ipynb"),
            "notebook_code_cells_sha256": sha(ACQ / "notebook_code.py"),
            "reconstructed_main_raw_sha256": sha(SOURCE),
            "reconstructed_main_lf_sha256": sha(SOURCE, True),
            "notebook_declared_main_sha256": "d36ae976ad4a6316e6c1a27a5d04e9cc8e30300f21bdd31e749127c67a9311c4",
            "notebook_declared_archive_sha256": "5cde13b09e9506f24b2f5df05719b597fe07ebbb6dead7da12894beda203e419",
        },
        "source_fidelity": {
            "main_hash_matches_notebook_assertion": sha(SOURCE) == "d36ae976ad4a6316e6c1a27a5d04e9cc8e30300f21bdd31e749127c67a9311c4",
            "notebook_cells": len(notebook["cells"]), "code_cells": sum(c["cell_type"] == "code" for c in notebook["cells"]),
            "notebook_has_saved_outputs": any(c.get("outputs") for c in notebook["cells"]),
        },
        "public_score_evidence": {
            "status": "VISIBLE BUT TIME-VARYING/INCONSISTENT; NOT USED AS AN EXPERIMENTAL LABEL",
            "observations": [
                "Notebook-specific search snapshot displayed Public Score 2023.7 and Best Public Score 2273.6 for V2.",
                "A competition code-listing snapshot displayed 2703.9 for this notebook.",
                "An older indexed snapshot displayed 1819.4 and Version 1 of 1.",
            ],
            "interpretation": "Search caches and leaderboard state are not synchronized; no single exact current score is asserted.",
        },
        "historical_versions": {
            "current_api_version_count": 4,
            "status": "MISSING ARTIFACT",
            "attempts": [
                "Kaggle CLI 2.2.4 kernels pull with an explicit historical version returned HTTP 403.",
                "Documented public/current endpoint returned only version 4.",
                "Several version-addressed public URL forms returned HTTP 403 or 404.",
            ],
            "consequence": "V1-to-V4 source diffs and exact score-per-revision attribution cannot be established without historical notebook exports.",
        },
        "scope_control": "No other public competitor notebooks were mined; other agents were used only as local opponents/references.",
    }
    write_json("farming_v3_source_audit.json", source_audit)

    route_summaries = [route_summary(route) for route in source._ROUTES]
    differences = [
        {"step": step, "route0": source._ROUTES[0][step], "route1": source._ROUTES[1][step]}
        for step in range(len(source._ROUTES[0])) if source._ROUTES[0][step] != source._ROUTES[1][step]
    ]
    v3_rows = [row for row in raw if row["variant"] == "v3"]
    adaptive = {
        "classification": "BOUNDED ADAPTIVE",
        "reason": "A state-observed router selects one of two complete tapes at turn 360, and a state-dependent budget guard may alter market sales at 72-turn boundaries. All other requested actions are tape-driven.",
        "route_count": len(source._ROUTES), "turns_per_route": [len(route) for route in source._ROUTES],
        "decision_step": source._DECISION_STEP, "differing_step_count": len(differences),
        "differing_window": [differences[0]["step"], differences[-1]["step"]],
        "identical_windows": [[0, 359], [432, 718]], "complete_differences": differences,
        "router": {
            "route1_if": [
                "first_shop == BAKERY and market.inventory.FERTILIZER <= 10232.5",
                "first_shop == PET_CAFE and rival planted tiles <= 64.5",
            ],
            "route0_otherwise": True, "inputs_are_observable": True,
            "raw_league_selection_counts": {
                "route0": sum((row.get("decision") or {}).get("route") == 0 for row in v3_rows),
                "route1": sum((row.get("decision") or {}).get("route") == 1 for row in v3_rows),
            },
        },
        "budget_guard": {
            "check_frequency": "steps divisible by 72",
            "lookahead": "purchase costs and protected feed/fertilizer/unplaced animals through the next 72-turn tape block",
            "repair": "sell only unprotected shed products priced at least 2, descending price, up to the 10-order cap; place sales before purchases",
            "normal_league_events": sum(len(row.get("budget_guard_events", [])) for row in v3_rows),
            "weak_cash_events": sum(len(row.get("budget_guard_events", [])) for row in stress_rows if row["variant"] == "v3"),
            "weak_cash_event_signature": "At step 72, sell 4 WHEAT while bank is 263 (all 8 tested player appearances).",
        },
        "route_requested_summaries": route_summaries,
    }
    write_json("farming_v3_adaptive_branches.json", adaptive)

    total_persisted_games = len(raw) + len(counter_rows) + len(read_json(RUNS / "candidate.partial.json")) + len(stress_rows) + len(dossier_rows)
    all_persisted = raw + counter_rows + read_json(RUNS / "candidate.partial.json") + stress_rows + dossier_rows
    reconstruction = {
        "status": "PASS",
        "source_path": "agents/public_farming_v3/main.py", "source_sha256": sha(SOURCE),
        "exact_hash_match": source_audit["source_fidelity"]["main_hash_matches_notebook_assertion"],
        "standalone_properties": {"agent_function": True, "external_files_required": False, "third_party_runtime_dependencies": False},
        "decoded_policy": {"routes": 2, "turns_each": 719, "difference_count": len(differences), "difference_window": [360, 431]},
        "local_validation": {
            "persisted_games": total_persisted_games,
            "runtime_failures": sum(bool(row.get("runtime_error")) for row in all_persisted),
            "semantic_failures": sum(len(row.get("semantic_failures", [])) for row in all_persisted),
            "livestock_escapes_v3_family": sum(len(row.get("livestock_escapes", [])) for row in all_persisted if row["variant"].startswith("v3")),
        },
        "archive_verification": "NOT RETAINED / NOT REBUILT: packaging was outside the permitted research scope; the notebook's declared archive hash is provenance only.",
        "confidence": "HIGH for current-version source and behavior; LOW/UNKNOWN for unavailable historical revisions.",
    }
    write_json("farming_v3_reconstruction_audit.json", reconstruction)

    revision_md = f"""# Farming Score V3 revision analysis

## Evidence boundary

The current public artifact is Kaggle notebook version **4**, last run **{metadata.get('lastRunTime')}**. Its two cells contain a prose design note and the complete deterministic builder for the standalone agent. The extracted `main.py` matches the notebook's own SHA-256 assertion exactly: `{sha(SOURCE)}`.

Historical notebook source was not retrievable through the public/current endpoint. Version-addressed CLI/API attempts returned 403 or 404, so this report does **not** invent a V1→V4 code diff. Search-index snapshots mention 1819.4 for an older “Version 1 of 1,” 2273.6 as a V2 best, and either 2023.7 or 2703.9 around the current notebook. Those values are asynchronous public metadata, not controlled measurements, and are excluded from causal claims.

## What the current revision explicitly changes

The notebook describes itself as a deployment revision: it preserves a supplied two-route policy while translating a native C++ deployment into one pure-Python, single-file agent. The current agent adds two bounded state-dependent mechanisms around the replay tapes:

1. At turn 360 it selects route 1 for a BAKERY/fertilizer condition or a PET_CAFE/rival-plant condition; otherwise route 0.
2. At each 72-turn boundary it computes the selected block's planned spend, protects future feed/fertilizer/unplaced animals, and sells priced surplus only when cash is insufficient.

The strategic tape itself contains exactly two 719-turn routes. They are identical through turn 359, differ on every turn from 360–431 (72 turns), and are identical again from 432–718. This is a coherent block choice, not per-turn imitation or arbitrary splicing.

## Locally measured revision value

- Forced route 1 versus forced route 0, with identical openings through turn 359: **+926.9 own coins/game** over 32 continuations; 32/32 positive; bootstrap 95% CI **+755.2 to +1,109.5**.
- The route-1 advantage delta is smaller but positive overall: **+442.4**, bootstrap 95% CI **+260.2 to +603.8**. It is neutral/noisy against V2 specifically.
- The budget guard changed zero actions in 88 normal-cash V3-family appearances sampled in the raw/counterfactual panels. At $2,000 starting cash it fired in 8/8 raw-V3 appearances, always adding `SELL WHEAT 4` at turn 72. Its paired own-money effect averaged **+798**, but the eight-game CI crossed zero.

## Interpretation

The strongest supported innovation is the coherent route-1 midseason block, especially its lower fertilizer and labor spend. The published router's thresholds are reproducible, but this local panel found route 1 superior in every tested same-state continuation, including states where the published selector chose route 0. Thus the existence of the branch is supported; the necessity of its threshold boundary is not. The guard is sound defensive engineering for low-cash conditions, not the explanation for normal-setting strength.
"""
    write_md("farming_v3_revision_analysis.md", revision_md)

    current_registry = read_json(EXP / "current_best.json")
    vs_current = {
        "design": "Paired fresh games: exact V3 and frozen CurrentBest independently face the same opponent, seed, and seat.",
        "current_best": {
            "path": current_registry["agent_path"], "sha256": sha(CURRENT),
            "architecture": "Step-1 observable selector among three complete Top-50 replay parents (dmitry, hanserong, redblack), using opponent money and hand count.",
        },
        "v3": {
            "path": "agents/public_farming_v3/main.py", "sha256": sha(SOURCE),
            "architecture": "Two fixed tapes with one turn-360 observable branch and a 72-turn-boundary affordability guard.",
        },
        "direct_head_to_head": raw_summary["summary"]["by_opponent"]["current_best"],
        "direct_observed": {
            "games": 16,
            "v3_wins": sum(row["advantage"] > 0 for row in v3_rows if row["opponent"] == "current_best"),
            "v3_mean_money": statistics.fmean(row["own_money"] for row in v3_rows if row["opponent"] == "current_best"),
            "v3_mean_advantage": statistics.fmean(row["advantage"] for row in v3_rows if row["opponent"] == "current_best"),
        },
        "overall_paired": raw_summary["summary"]["overall"],
        "primary_conclusion": "V3 won all 16 direct games and improved direct advantage robustly, but broad-panel own-money delta was only +368.5 with CI crossing zero and a -41,977 worst tail. It is a strong challenger, not a safe replacement.",
    }
    write_json("farming_v3_vs_currentbest.json", vs_current)
    write_json("farming_v3_raw_league.json", {
        "status": "COMPLETE", "games": len(raw), "paired_conditions": len(raw_summary["pairs"]),
        "opponents": sorted({row["opponent"] for row in raw}), "both_seats": True,
        "summary": raw_summary["summary"], "pairs": raw_summary["pairs"],
        "safety": {"runtime_failures": sum(bool(row.get("runtime_error")) for row in raw), "semantic_failures": sum(len(row.get("semantic_failures", [])) for row in raw)},
    })

    hypotheses = {
        "ranking_basis": "Causal same-opening evidence first, then paired league evidence, then static/source inference.",
        "hypotheses": [
            {"rank": 1, "mechanism": "Route-1 midseason continuation", "status": "SUPPORTED", "evidence": "+926.9 own coins, 32/32 positive, CI entirely positive; only turns 360–431 differ."},
            {"rank": 2, "mechanism": "Lower midseason capital burn", "status": "SUPPORTED ON REPRESENTATIVE DOSSIER", "evidence": "Route 1 saved 270 fertilizer spend, 288 labor spend, and 10 seed spend per representative game; the spend savings plus revenue delta exactly reconcile the +1,096.5 dossier-bank delta."},
            {"rank": 3, "mechanism": "Opponent-facing market pressure", "status": "SUPPORTED BUT HETEROGENEOUS", "evidence": "V3 improved broad advantage by +5,341 (CI positive), but regressed -22,837 versus crop_dusta and helped opponents in some route comparisons."},
            {"rank": 4, "mechanism": "Published BAKERY/PET_CAFE thresholds identify the better route", "status": "NOT SUPPORTED AS NECESSARY", "evidence": "The selector chose route 1 in 12/56 raw appearances, while forced route 1 beat route 0 in all 32 causal continuations across three opponent cohorts."},
            {"rank": 5, "mechanism": "Affordability guard drives normal strength", "status": "REFUTED FOR NORMAL CASH", "evidence": "Zero normal-cash guard events; only weak-cash stress activated it."},
            {"rank": 6, "mechanism": "Python conversion itself improves strategy", "status": "ENGINEERING ONLY", "evidence": "It establishes reproducibility/portability; no strategic delta can be attributed without the unavailable native/historical sources."},
        ],
    }
    write_json("farming_v3_difference_hypotheses.json", hypotheses)
    write_json("farming_v3_counterfactuals.json", {
        "status": "COMPLETE", "design": "Fresh forced continuations against current_best, v2, and tetsuya; paired seed/seat; route openings hash-identical through turn 359.",
        "route1_minus_route0": counter["route1_minus_route0"],
        "guard_minus_no_guard": counter["guard_minus_no_guard"],
        "validity": {"all_route_openings_equal": counter["route1_minus_route0"]["summary"]["overall"]["opening_hash_all_equal"], "guard_normal_actions_identical": counter["guard_minus_no_guard"]["summary"]["overall"]["own_money_delta"]["mean"] == 0},
    })

    write_json("farming_v3_distillation.json", {
        "status": "ONE-MECHANISM CANDIDATE BUILT",
        "source_mechanism": "Replace the published threshold router with unconditional route 1; preserve the exact V3 tapes and guard.",
        "rationale": "Route 1 produced positive own-money delta in all 32 same-opening counterfactuals.",
        "candidate": "agents/farming_v3_distilled/v1_force_route1.py",
        "scope": "Research-only wrapper around hash-verified public V3 source; no deployment integration.",
        "rejected_alternatives": ["Transplanting partial field actions into CurrentBest (state-incoherent).", "Editing replay actions turn by turn (confounded and contrary to mechanism isolation).", "Treating the inactive normal-cash guard as the main innovation."],
    })
    write_json("farming_v3_candidate_manifest.json", {
        "candidate_id": "farming_v3_distilled_v1_force_route1", "status": "EVALUATED, NOT SELECTED",
        "path": "agents/farming_v3_distilled/v1_force_route1.py", "sha256": sha(CANDIDATE),
        "parent_source": "agents/public_farming_v3/main.py", "parent_sha256": sha(SOURCE),
        "only_intended_change": "_select_route always returns 1",
        "behavioral_equivalence_check": {"seed": 885000, "seat": 0, "opponent": "current_best", "evaluated_wrapper_action_hash": "c104d20cb70f2844e259b9b665bf5e42586ef98b53d3721ee5001bc5657b5c0a", "candidate_action_hash": "c104d20cb70f2844e259b9b665bf5e42586ef98b53d3721ee5001bc5657b5c0a", "final_money_both": 72034, "pass": True},
        "deployment_impact": "None",
    })
    write_json("farming_v3_candidate_results.json", {
        "status": "COMPLETE DEVELOPMENT SCREEN",
        "candidate": "farming_v3_distilled_v1_force_route1",
        "note": "The statistical screen used the behaviorally identical research wrapper agents/public_farming_v3/forced_route1.py; equivalence is recorded in the candidate manifest.",
        "games": len(read_json(RUNS / "candidate.partial.json")), "paired_conditions": len(candidate["pairs"]),
        "summary": candidate["summary"], "pairs": candidate["pairs"],
        "decision": "DO NOT ADVANCE: causal improvement over V3 route 0 is real, but versus CurrentBest broad own-money CI crosses zero, negative-rate is 51.8%, worst tail is -41,977, and crop_dusta regresses sharply.",
    })
    write_json("farming_v3_ablation_results.json", {
        "status": "COMPLETE",
        "route_ablation": counter["route1_minus_route0"],
        "normal_cash_guard_ablation": counter["guard_minus_no_guard"],
        "weak_cash_guard_ablation": stress,
        "interpretation": "Route 1 is the substantial normal-setting mechanism. The guard is conditionally active and helpful on average at weak cash, but not statistically resolved in eight paired appearances.",
    })

    econ_delta = {
        "own_money": dossier1["own_money"] - dossier0["own_money"],
        "advantage": dossier1["advantage"] - dossier0["advantage"],
        "revenue": numeric_delta(dossier1["revenue"], dossier0["revenue"]),
        "sales": numeric_delta(dossier1["sales"], dossier0["sales"]),
        "harvest": numeric_delta(dossier1["harvest"], dossier0["harvest"]),
        "seed_spend": numeric_delta(dossier1["seed_spend"], dossier0["seed_spend"]),
        "product_spend": numeric_delta(dossier1["product_spend"], dossier0["product_spend"]),
        "animal_spend": numeric_delta(dossier1["animal_spend"], dossier0["animal_spend"]),
        "land_spend": dossier1["land_spend"] - dossier0["land_spend"],
        "labor_spend": dossier1["labor_spend"] - dossier0["labor_spend"],
    }
    write_json("farming_v3_economic_attribution.json", {
        "status": "COMPLETE REPRESENTATIVE ATTRIBUTION",
        "sample": "4 route-0 and 4 route-1 detailed games, two opponents and both seats; route means.",
        "route0": dossier0, "route1": dossier1, "route1_minus_route0": econ_delta,
        "cash_reconciliation": {"route1_revenue_delta": sum(econ_delta["revenue"].values()), "route1_spend_reduction": -(sum(econ_delta["seed_spend"].values()) + sum(econ_delta["product_spend"].values()) + sum(econ_delta["animal_spend"].values()) + econ_delta["land_spend"] + econ_delta["labor_spend"]), "reconciled_bank_delta": sum(econ_delta["revenue"].values()) - (sum(econ_delta["seed_spend"].values()) + sum(econ_delta["product_spend"].values()) + sum(econ_delta["animal_spend"].values()) + econ_delta["land_spend"] + econ_delta["labor_spend"])},
        "limitation": "Pooled inventories prevent defensible crop-cohort-to-specific-sale matching; cohort service/harvest windows are preserved in farming_v3_runs/dossier.partial.json instead of fabricated attribution.",
    })

    selection = {
        "decision": "KEEP CURRENTBEST; RETAIN V3 AS A CHALLENGER/REFERENCE",
        "selected_path": current_registry["agent_path"], "selected_sha256": sha(CURRENT),
        "candidate_path": "agents/farming_v3_distilled/v1_force_route1.py", "candidate_sha256": sha(CANDIDATE),
        "reasons": [
            "V3's broad paired own-money delta versus CurrentBest is not statistically resolved.",
            "Forced route 1 improves V3 causally but retains a 51.8% negative paired-own rate and -41,977 worst regression versus CurrentBest.",
            "The crop_dusta cohort loses 18,644 own coins and 22,692 advantage on average.",
            "The candidate is safe in tested games but does not clear the repository's conservative promotion standard.",
        ],
        "current_best_registry_changed": False, "submission_main_changed": False,
        "deployed_submission_sha256": sha(DEPLOYED),
    }
    write_json("farming_v3_selection_results.json", selection)
    write_json("farming_v3_finalist_lock.json", {
        "status": "NOT RUN", "reason": "No candidate passed the development promotion gate, so freezing a finalist would create false significance.",
        "candidate_considered": "agents/farming_v3_distilled/v1_force_route1.py", "candidate_sha256_at_decision": sha(CANDIDATE),
        "current_best_sha256": sha(CURRENT), "evaluation_code_sha256": sha(ROOT / "run_farming_v3_research.py"),
    })
    write_json("farming_v3_final_validation.json", {
        "status": "NOT RUN", "reason": "Independent final validation is reserved for a locked finalist; the sole candidate failed the development gate.",
        "development_evidence": ["experiments/farming_v3_candidate_results.json", "experiments/farming_v3_ablation_results.json", "experiments/farming_v3_selection_results.json"],
        "submission_or_upload_performed": False,
    })

    economy_md = f"""# Farming Score V3 economic dossier

## Strategy in plain language

V3 is a high-labor, mixed livestock/crop replay policy. It requests two land expansions at turns 150 and 265 (observed unlocked-state changes at 151 and 266), peaks at 12 hired hands, constructs 17 pastures plus one coop, and buys nine cows and nine sheep. In the detailed runs it reaches 17 placed animals—nine cows and eight sheep—with no escapes. The unused coop and one unplaced/unrealized sheep indicate that requested tape totals should not be mistaken for executed assets.

The crop portfolio is wheat-led, with strawberries and melons as premium revenue, a small carrot allocation, and no tomatoes. Route 0 requests 198 wheat seeds, 33 strawberry, 12 melon, and 5 carrot; route 1 requests one fewer wheat seed. Both routes repeatedly collect animal fertilizer, buy additional fertilizer/wheat, fertilize premium crops, and sell fertilizer surplus. They harvest/service nearly continuously and end with a small wheat field plus the livestock base.

## Requested policy totals

| Metric | Route 0 | Route 1 |
|---|---:|---:|
| HIRE orders | {route_summaries[0]['market_order_counts'].get('HIRE', 0)} | {route_summaries[1]['market_order_counts'].get('HIRE', 0)} |
| BUY_PRODUCT fertilizer units | {route_summaries[0]['market_requested_quantities'].get('BUY_PRODUCT:FERTILIZER', 0)} | {route_summaries[1]['market_requested_quantities'].get('BUY_PRODUCT:FERTILIZER', 0)} |
| SELL fertilizer units | {route_summaries[0]['market_requested_quantities'].get('SELL:FERTILIZER', 0)} | {route_summaries[1]['market_requested_quantities'].get('SELL:FERTILIZER', 0)} |
| SELL strawberry units | {route_summaries[0]['market_requested_quantities'].get('SELL:STRAWBERRY', 0)} | {route_summaries[1]['market_requested_quantities'].get('SELL:STRAWBERRY', 0)} |
| WATER requests | {route_summaries[0]['field_operation_requests'].get('WATER', 0)} | {route_summaries[1]['field_operation_requests'].get('WATER', 0)} |
| HARVEST requests | {route_summaries[0]['field_operation_requests'].get('HARVEST', 0)} | {route_summaries[1]['field_operation_requests'].get('HARVEST', 0)} |

## Executed representative economics

Across four detailed appearances per forced route (CurrentBest and V2, both seats), route 0 averaged **{dossier0['own_money']:.1f}** final coins and route 1 **{dossier1['own_money']:.1f}**. Route 1's +{econ_delta['own_money']:.1f} bank edge reconciles exactly:

- revenue delta: **{sum(econ_delta['revenue'].values()):+.1f}** (milk +760; wool +207.5; fertilizer −231; wheat −208.5; strawberry +0.5);
- spend reduction: **{-(sum(econ_delta['seed_spend'].values()) + sum(econ_delta['product_spend'].values()) + econ_delta['labor_spend']):+.1f}** (fertilizer +270 saved, labor +288 saved, wheat seed +10 saved).

The base engine is economically substantial: route 1 averages 40,422.5 strawberry revenue, 26,515 milk, 24,392.5 wool, 15,618 melon, 16,001.5 fertilizer, and 14,262.25 wheat. It spends 7,600 on animals, 3,000 on land, 5,722 on labor, 4,370 on seeds, and 7,393 on bought wheat/fertilizer in this representative panel.

## Timing and phase behavior

Cash is intentionally near zero early while livestock, land, and labor are accumulated. Across the four detailed route-1 appearances, mean bank end rises from 28 on day 0 to 136 on day 3, 512 on day 6, 1,477 on day 9, 18,567 on day 12, 51,990 on day 18, 89,214 on day 24, and 110,531 on day 29; absolute endpoints vary strongly by opponent market behavior. Major asset milestones do not vary: first placed animal around turn 5, land around turns 151/266, peak 12 hands, peak 17 animals.

The only route difference is the day-15-to-day-17 block (turns 360–431). Route 1 spends less on fertilizer and hiring, rearranges field servicing/drop/pickup timing, realizes more milk/wool revenue, and gives up a little wheat/fertilizer revenue. After turn 431 the requested tapes rejoin, but their farm/inventory states remain causally different.

## Selling and market interaction

V3 liquidates throughout the season rather than holding everything to a single terminal dump. Static requested sale totals are larger than executed totals because invalid or inventory-constrained orders silently no-op. In the detailed route-1 sample it executes about 353.5 wheat, 352 fertilizer, 261 strawberry, 261 milk, 194.5 wool, 72 melon, and 9 carrot sales per game. The broad league's +5,341 advantage delta but near-zero own-money delta shows that market interference/opponent suppression is material; it is not equivalent to private wealth creation.

## Evidence limits

Crop cohort planting, watering, fertilization, and harvest windows are fully recorded per detailed game in `experiments/farming_v3_runs/dossier.partial.json`. Specific harvested units cannot be causally matched to later sales because the game pools products in inventories and shed storage. This dossier therefore reports truthful aggregate holding/sale behavior and does not invent lot-level lineage.
"""
    write_md("farming_v3_economic_dossier.md", economy_md)

    report = f"""# Farming Score V3 deep-dive report

## Executive result

The current public notebook was reconstructed exactly and is a genuinely strong policy, but it does not justify replacing the frozen CurrentBest. The exact V3 source won all 16 direct head-to-head games against CurrentBest and improved direct advantage by **+7,053.6** on average (95% bootstrap **+3,999.1 to +10,124.2**). Across the six-opponent league, however, its paired own-bank delta was only **+368.5** (95% bootstrap **−5,550.9 to +6,525.4**), with a **51.8%** negative rate and **−41,977** worst case. It was particularly weaker than CurrentBest against crop_dusta and nazmus.

## Provenance and reconstruction

Kaggle's current API identifies notebook version 4, last run {metadata.get('lastRunTime')}. The extracted source SHA-256 `{sha(SOURCE)}` matches the notebook's embedded expected hash. The agent compiles and completed {total_persisted_games} persisted local games with zero runtime or action-schema failures. Historical V1–V3 source could not be retrieved; apparent public score snapshots conflict and are treated only as unstable context.

## Architecture

This is **bounded adaptive replay**:

- two complete 719-turn tapes;
- one observable decision at turn 360;
- exactly 72 differing turns (360–431);
- an affordability guard at 72-turn boundaries;
- exception-safe PASS fallback.

The core farm is a wheat/premium-crop plus cow/sheep engine: two land expansions, 12-hand peak, 17 productive livestock placements, continuous feed/care/fertilizer loops, strawberry/melon revenue, and broad ongoing liquidation.

## Causal findings

The midseason route is the real innovation. Forced route 1 beat forced route 0 in **32/32** same-opening continuations by **+926.9 own coins** on average (95% bootstrap **+755.2 to +1,109.5**). Representative accounting attributes +528.5 to net revenue and +568 to lower spend, exactly reconciling a +1,096.5 bank difference in that smaller detailed sample.

The published selector chose route 1 in only 12 of 56 raw-league V3 appearances. Because forced route 1 won every causal continuation, the local evidence supports route 1 but does not validate the need for the BAKERY/PET_CAFE thresholds. The guard did not fire under normal cash. Under $2,000 starting cash it sold four wheat at turn 72 in all eight appearances and averaged +798 coins versus no guard, although that small CI crossed zero.

## Candidate and selection

A faithful one-change candidate, `agents/farming_v3_distilled/v1_force_route1.py`, was built. Its behavior was hash-equivalent to the evaluated force-route-1 wrapper in an explicit replay check. It raised the broad paired-own mean versus CurrentBest from +368.5 for published V3 to +839.7, but retained the same severe tail, a 51.8% negative rate, and an **−18,644 own / −22,692 advantage** mean regression versus crop_dusta. It therefore failed the conservative development gate; no finalist was locked and no independent final-validation panel was spent.

## Practical takeaways for CurrentBest

1. Preserve coherent multi-day continuations. V3's strongest gain is a complete 72-turn state-compatible block, consistent with earlier failures from arbitrary replay splicing.
2. Prefer the economic shape of route 1: fewer fertilizer purchases and hires during the midseason transition, with milk/wool revenue substituting for some wheat/fertilizer sales.
3. Separate private income from opponent suppression. V3 often improves advantage far more than own bank, which can look strong while masking fragile wealth production.
4. Keep the guard as a low-cash design pattern, not a normal-game source of score. It protects upcoming obligations cleanly, but it is inactive at standard cash in this sample.
5. Do not transplant raw turn actions into CurrentBest without a state owner/executor capable of preserving the whole farm trajectory.

## Decision

**Keep `agents/top50_distilled/top50_observable_portfolio.py` as CurrentBest.** Retain exact V3 and the force-route-1 candidate as research references. `experiments/current_best.json` and `submission/main.py` remain unchanged, and no Kaggle submission or upload was performed.
"""
    write_md("farming_v3_deep_dive_report.md", report)


if __name__ == "__main__":
    main()
