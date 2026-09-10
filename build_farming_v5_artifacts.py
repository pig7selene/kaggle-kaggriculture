"""Build the Farming V5 research artifacts from frozen public source and local runs.

This is a reporting-only script.  It does not edit agents, package submissions, or
contact Kaggle.  All empirical claims are derived from the saved raw/dossier runs.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import statistics
import sys
from typing import Any


ROOT = Path(__file__).resolve().parent
EXP = ROOT / "experiments"
RUNS = EXP / "farming_v5_runs"
ACQ = EXP / "farming_v5_acquisition"
V5 = ROOT / "agents/public_farming_v5"
V1 = ROOT / "agents/public_farming_v5_v1"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(name: str, payload: Any) -> None:
    (EXP / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_text(name: str, text: str) -> None:
    (EXP / name).write_text(text.rstrip() + "\n")


def pct(values: list[float], q: float) -> float | None:
    if not values:
        return None
    xs = sorted(values)
    pos = (len(xs) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return xs[lo]
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def descriptive(values: list[float]) -> dict[str, Any]:
    return {
        "n": len(values),
        "mean": statistics.fmean(values) if values else None,
        "median": statistics.median(values) if values else None,
        "p25": pct(values, .25),
        "p10": pct(values, .10),
        "p5": pct(values, .05),
        "worst": min(values) if values else None,
        "best": max(values) if values else None,
    }


def mean_dict(rows: list[dict[str, Any]], key: str) -> dict[str, float]:
    names = sorted({name for row in rows for name in row["economics"].get(key, {})})
    return {
        name: statistics.fmean(float(row["economics"].get(key, {}).get(name, 0)) for row in rows)
        for name in names
    }


def mean_scalar(rows: list[dict[str, Any]], key: str) -> float:
    return statistics.fmean(float(row["economics"].get(key, 0)) for row in rows)


def subtract_dict(left: dict[str, float], right: dict[str, float]) -> dict[str, float]:
    return {key: left.get(key, 0) - right.get(key, 0) for key in sorted(set(left) | set(right))}


def package_files(root: Path) -> list[Path]:
    return sorted(
        path for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.name != "PUBLIC_ARCHIVE_SHA256.txt"
    )


def load_module(path: Path, name: str):
    for module_name in list(sys.modules):
        if module_name.startswith(("e7", "optimized_pkg", "late_bundle", "complete_terminal")):
            sys.modules.pop(module_name, None)
    sys.path.insert(0, str(path))
    sys.path.insert(0, str(path / "agents"))
    try:
        spec = importlib.util.spec_from_file_location(name, path / "main.py")
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        policy = module.kaggriculture_agent.__globals__["_policy"]
        complete = policy.__globals__["_MODULE"]
        e773 = complete.PARENT.PARENT.PARENT.PARENT.PARENT
        return module, e773
    finally:
        sys.path.pop(0)
        sys.path.pop(0)


def synthetic_window_test(root: Path, name: str) -> dict[str, Any]:
    _, e773 = load_module(root, name)
    board = [[None] * 10 for _ in range(10)]
    farms = [{"tiles": board}, {"tiles": board}]

    def obs(shops: list[str]) -> dict[str, Any]:
        return {
            "farms": farms,
            "town": {"unlocked_shops": shops},
            "market": {"prices": {"MILK": 160, "WOOL": 200}},
        }

    e773._reset(0)
    root_target = e773._assign_bundle(obs(["PIZZA_SHOP", "PIZZA_SHOP"]), 0, "cow150")
    follow_target = e773._assign_bundle(obs(["YARN_STORE", "YARN_STORE"]), 0, "cow169")
    return {
        "root_state": "dairy pressure; source COW retained",
        "later_state": "wool pressure crosses replacement threshold",
        "cow150_target": root_target,
        "cow169_target": follow_target,
        "decision_rows": e773._STATE[0]["decision_rows"],
    }


def main() -> None:
    raw = json.loads((RUNS / "raw.partial.json").read_text())
    summary = json.loads((RUNS / "raw_summary.json").read_text())
    dossier = json.loads((RUNS / "dossier.partial.json").read_text())
    view = json.loads((ACQ / "kaggle-view-model-response.json").read_text())
    view1 = json.loads((ACQ / "kaggle-view-model-v1-response.json").read_text())

    groups = defaultdict(list)
    for row in raw:
        groups[row["variant"]].append(row)
    details = defaultdict(list)
    for row in dossier:
        details[row["variant"]].append(row)

    source_artifacts = []
    for path in sorted(ACQ.iterdir()):
        if path.is_file():
            source_artifacts.append({
                "path": str(path.relative_to(ROOT)),
                "sha256": sha(path),
                "bytes": path.stat().st_size,
                "role": "public Kaggle metadata/source snapshot",
            })
    current_members = {str(p.relative_to(V5)): sha(p) for p in package_files(V5)}
    v1_members = {str(p.relative_to(V1)): sha(p) for p in package_files(V1)}
    changed_members = [p for p in sorted(set(current_members) | set(v1_members)) if current_members.get(p) != v1_members.get(p)]

    source_audit = {
        "research_mode": "read-only public acquisition; no upload, mutation, packaging, or submission",
        "retrieved_on_local_date": "2026-09-09 Asia/Shanghai",
        "notebook": {
            "id": 132738338,
            "owner_display_name": "Arlene",
            "owner_username": "lynnsakurai",
            "slug": "farming-score-v5-timing-optimized",
            "url": "https://www.kaggle.com/code/lynnsakurai/farming-score-v5-timing-optimized",
            "current_public_version": 2,
            "current_run_id": 346466052,
            "current_run_date": view["kernelRun"]["dateEvaluated"],
            "public_score_metadata": {"best_visible_score": 2016.7, "score_version": 1, "current_v2_score": None},
            "license": {"explicit_field_found": False, "note": "No explicit notebook license field was exposed by the preserved public metadata; attribution is retained."},
        },
        "versions": [
            {
                "version": 1,
                "run_id": 346428459,
                "run_date": view1["kernelRun"]["dateEvaluated"],
                "notebook_sha256": sha(ACQ / "farming-score-v5-timing-optimized-v1.ipynb"),
                "archive_sha256": "41509dacec22f6652628dc692d5c9c0bc453457e541c4b43cfd9b3a73ffbc5df",
            },
            {
                "version": 2,
                "run_id": 346466052,
                "run_date": view["kernelRun"]["dateEvaluated"],
                "notebook_sha256": sha(ACQ / "farming-score-v5-timing-optimized.ipynb"),
                "archive_sha256": "35143710b4b493e2e94a68efa21aa03fc3833318fef52645b8e58d5ffeb4bf9e",
            },
        ],
        "dependencies": {
            "competition_inputs": [{"source_id": 147734, "version_id": 20046115, "mount_slug": "competitions/kaggriculture"}],
            "linked_datasets": [],
            "linked_kernel_dependencies": [],
            "embedded_attributed_traces": [
                {"author": "Kenjo1209", "episode": 102192548, "seat": 1, "sha256": current_members["artifacts/e751_current_top10_tapes/episode_102192548_seat1.py"]},
                {"author": "NIklitaCheporev", "episode": 101408728, "seat": 1, "sha256": current_members["artifacts/e706_top10_tapes/episode_101408728_seat1.py"]},
            ],
        },
        "externally_acquired_artifacts": source_artifacts,
        "local_reconstruction": {
            "path": "agents/public_farming_v5",
            "main_py_sha256": sha(V5 / "main.py"),
            "optimized_entry_sha256": sha(V5 / "optimized_pkg/entry.py"),
            "member_count": len(current_members),
            "member_sha256": current_members,
        },
    }
    write_json("farming_v5_source_audit.json", source_audit)

    runtime_failures = [r for r in raw if r.get("runtime_error") or r.get("exceptions")]
    semantic_failures = [r for r in raw if r.get("semantic_failures")]
    reconstruction = {
        "status": "PASS with stated evidence boundary",
        "public_archive_sha256_declared_and_verified": "35143710b4b493e2e94a68efa21aa03fc3833318fef52645b8e58d5ffeb4bf9e",
        "archive_members_verified": len(current_members),
        "local_main_py_sha256": sha(V5 / "main.py"),
        "reconstructed_single_file_main_sha256": "e8498c67914ecc607ae69fde25a728361eb5acea94c00ecc85deffbdafe50413",
        "public_member_hashes": current_members,
        "compile_import": "PASS",
        "corrected_local_games": {"raw": len(raw), "dossier": len(dossier), "total": len(raw) + len(dossier)},
        "runtime_failures": len(runtime_failures),
        "semantic_action_schema_failures": len(semantic_failures),
        "equivalence_claim": "The local tree is byte-for-byte the archive reconstructed from public notebook source. No public replay/action trace was exposed for external behavioral comparison, so behavioral equivalence beyond exact source reconstruction is not independently proven.",
        "harness_correction": "An initial run imported colliding package module names across v1/v2 workers. It is preserved only as raw_loader_collision_audit.json and excluded. The corrected loader purged modules and all reported results use raw.partial.json.",
        "safety_is_not_reconstruction": "Livestock escapes are faithful public-policy behavior, not a reconstruction mismatch.",
    }
    write_json("farming_v5_reconstruction_audit.json", reconstruction)

    absolute = {variant: descriptive([float(r["own_money"]) for r in rows]) for variant, rows in groups.items()}
    safety = {}
    for variant, rows in groups.items():
        events = [e for r in rows for e in r.get("livestock_escapes", [])]
        safety[variant] = {
            "games": len(rows),
            "runtime_failures": sum(bool(r.get("runtime_error") or r.get("exceptions")) for r in rows),
            "semantic_failures": sum(bool(r.get("semantic_failures")) for r in rows),
            "games_with_escape": sum(bool(r.get("livestock_escapes")) for r in rows),
            "escape_events": len(events),
        }
    direct = {}
    for key in ("v5_minus_current_best", "v5_minus_v3"):
        target = "current_best" if key.endswith("current_best") else "v3"
        direct[key] = next(x for name, x in summary[key]["summary"]["by_opponent"].items() if name == target)

    raw_league = {
        "design": {
            "fresh_seed_range": "920000-series, four seeds per opponent",
            "opponents": ["current_best", "v3", "crop_dusta", "nazmus", "k3", "tetsuya"],
            "seats": [0, 1],
            "variants": ["current_best", "v3", "v5_v1", "v5"],
            "conditions_per_variant": 48,
            "games_total": len(raw),
        },
        "absolute_own_money": absolute,
        "paired": summary,
        "mandatory_direct_h2h": direct,
        "safety": safety,
        "primary_conclusion": "V5 is not robustly stronger: its +1136 mean own-money delta versus CurrentBest has a CI crossing zero, negative median, severe paired tail, negative advantage delta, and 40/48 escape failures.",
        "raw_data": "experiments/farming_v5_runs/raw.partial.json",
    }
    write_json("farming_v5_raw_league.json", raw_league)

    v5_v1 = summary["v5_minus_v1"]
    prefix_v1 = Counter(p["exact_action_common_prefix"] for p in v5_v1["pairs"])
    prefix_cb = Counter(p["exact_action_common_prefix"] for p in summary["v5_minus_current_best"]["pairs"])
    prefix_v3 = Counter(p["exact_action_common_prefix"] for p in summary["v5_minus_v3"]["pairs"])
    synthetic = {
        "v1": synthetic_window_test(V1, "farming_v5_v1_synthetic"),
        "v2": synthetic_window_test(V5, "farming_v5_v2_synthetic"),
    }
    write_json("farming_v5_timing_diff.json", {
        "natural_revision": "public V5 version 1 -> public V5 version 2",
        "changed_archive_members": changed_members,
        "changed_member_count": len(changed_members),
        "v1_changed_sha256": v1_members[changed_members[0]],
        "v2_changed_sha256": current_members[changed_members[0]],
        "source_change": {
            "root": "cow150",
            "followups": ["cow169", "cow176"],
            "rule": "Reuse the animal direction chosen after the second-shop information window for the later day-6-to-9 cow bundles, while preserving the COW->SHEEP cap of 3.",
            "unchanged": ["purchase turns", "quantities", "routes", "feed/service", "land", "labor", "crops", "sales", "terminal frontier"],
        },
        "controlled_reverse_ablation_v2_minus_v1": {
            "conditions": 48,
            "action_common_prefix_distribution": dict(prefix_v1),
            "actions_changed": sum(p["exact_action_common_prefix"] < 719 for p in v5_v1["pairs"]),
            "own_money_delta": v5_v1["summary"]["overall"]["own_money_delta"],
            "advantage_delta": v5_v1["summary"]["overall"]["advantage_delta"],
            "causal_value_on_panel": 0,
        },
        "synthetic_semantic_test": {
            "purpose": "Capability test only; not an economic result.",
            "v1_result": synthetic["v1"],
            "v2_result": synthetic["v2"],
            "interpretation": "When the root prefers COW and later visible pressure flips to wool, v1 switches cow169 to SHEEP while v2 keeps the COW commitment. The code is behaviorally capable, but no tested natural game reached a value-changing divergence.",
        },
    })

    compatibility = {
        "current_best_vs_v5": {
            "conditions": 48,
            "common_prefix_distribution": dict(sorted(prefix_cb.items())),
            "interpretation": "Compatibility is sometimes long (72-154 turns) but not universally safe; 8/48 conditions diverge at step 1 and no deployable pre-commit gate follows from this panel.",
        },
        "v3_vs_v5": {
            "conditions": 48,
            "common_prefix_distribution": dict(sorted(prefix_v3.items())),
            "first_realized_divergence": 0,
            "v3_step0": {"farmer": ["PASS"], "hands": [], "market": [["BUY_PRODUCT", "WHEAT", 13]]},
            "v5_step0": {"farmer": ["PASS"], "hands": [], "market": []},
            "interpretation": "There is no shared behavioral prefix. V3 and V5 are unrelated policy lineages, so V3->V5 is a structural comparison, not a clean timing ablation.",
        },
        "v1_vs_v2": {"conditions": 48, "common_prefix_distribution": dict(prefix_v1), "interpretation": "Exact action identity through all 719 agent decisions."},
    }
    write_json("farming_v5_compatibility.json", compatibility)

    vs_v3 = {
        "causal_warning": "The prompt's assumed natural V3->V5 revision relationship is false in the retrieved source. V5 derives from attributed Kenjo/Niklita traces and a wrapper stack; public V3 is a different policy. Only V5 v1->v2 is a natural source ablation.",
        "paired_results": summary["v5_minus_v3"],
        "direct_h2h_when_opponent_is_v3": direct["v5_minus_v3"],
        "first_realized_divergence": compatibility["v3_vs_v5"],
        "revision_map": [
            {"phase": "step 0 capital", "class": "STRUCTURAL", "v3": "BUY_PRODUCT WHEAT 13", "v5": "no order", "timing_delta": None, "economic_meaning": "Different starting economy; not evidence for moving a shared action."},
            {"phase": "land", "class": "STRUCTURAL", "v3": "requests BUY_LAND at 150 and 265", "v5": "same request turns", "timing_delta": 0, "economic_meaning": "No V5 land-timing innovation."},
            {"phase": "livestock", "class": "ADAPTIVE", "v3": "fixed cow/sheep programme reaching about 17 animals", "v5": "registered COW/SHEEP bundle substitution, about 14 animals", "timing_delta": "purchase nodes partly overlap; direction and later programme differ", "economic_meaning": "Different livestock economy and lifecycle output."},
            {"phase": "crops", "class": "STRUCTURAL", "v3": "distinct wheat/strawberry cohorts", "v5": "Kenjo/Niklita-derived crop route with later/route-dependent strawberries", "timing_delta": "not isolatable", "economic_meaning": "Production and labor composition change together."},
            {"phase": "market", "class": "MARKET", "v3": "different sell route and volumes", "v5": "sale-allocation wrappers at conserved nodes", "timing_delta": "not a same-output timing comparison", "economic_meaning": "Quantity, production, and shared-market effects are confounded."},
            {"phase": "repair", "class": "REPAIR", "v3": "own executor/repair system", "v5": "weed, placement funding, latent-pasture and delivery repair wrappers", "timing_delta": None, "economic_meaning": "State recovery architecture differs."},
            {"phase": "terminal", "class": "TERMINAL", "v3": "different late programme", "v5": "complete observable inventory sell frontier at step 718", "timing_delta": "frontier-specific", "economic_meaning": "Low-risk liquidation logic, not isolated against V3."},
        ],
        "causal_chain_boundary": "Step 0 creates immediate cash/inventory divergence, after which assets, production, market exposure, and final money all differ. Because the entire policies differ, final deltas cannot be assigned causally to the step-0 wheat purchase or any single timing event.",
    }
    write_json("farming_v5_vs_v3.json", vs_v3)

    tail = {
        "absolute_own_money": {"v3": absolute["v3"], "v5": absolute["v5"]},
        "paired_v5_minus_v3": summary["v5_minus_v3"]["summary"],
        "finding": "V5 has a better absolute P10/P5/worst than V3 on this panel, but paired V5-V3 deltas still have P10 -18,789, P5 -24,313.05 and worst -26,581; direct V3 H2H is 0-8. This is not a reliable tail repair.",
        "crop_dusta": {
            "v5_minus_current_best": summary["v5_minus_current_best"]["summary"]["by_opponent"]["crop_dusta"],
            "v5_minus_v3": summary["v5_minus_v3"]["summary"]["by_opponent"]["crop_dusta"],
            "interpretation": "V5 gains own money versus CurrentBest in Crop Dusta conditions, but loses advantage because Crop Dusta benefits more from the shared market; H2H is 2-6. The weakness is not repaired.",
        },
    }
    write_json("farming_v5_tail_repair_analysis.json", tail)

    mechanisms = [
        {
            "rank": 1,
            "mechanism": "v2 post-shop-2 animal-direction window commitment",
            "class": "TIMING_ONLY / ADAPTIVE",
            "v3_behavior": "not present; unrelated lineage",
            "v5_behavior": "cow150 direction is reused at cow169/cow176 subject to cap",
            "causal_value_vs_v3": None,
            "causal_value_v2_vs_v1": {"own_money": 0, "advantage": 0, "conditions": 48},
            "tail_effect": 0,
            "market_effect": 0,
            "current_best_compatibility": "not justified for transplant",
            "implementation_difficulty": "low",
            "confidence": "high that it was inactive/economically null on the panel",
            "decision": "REJECT",
        },
        {
            "rank": 2,
            "mechanism": "v1 information-maturity gate from cow88 to cow150",
            "class": "ADAPTIVE / CAPITAL-SEQUENCING",
            "v3_behavior": "not present",
            "v5_behavior": "non-Yarn early signal is deferred until the second shop; direct Yarn evidence may act at cow88",
            "causal_value_vs_v3": None,
            "tail_effect": "not isolated",
            "market_effect": "changes milk/wool exposure when triggered",
            "current_best_compatibility": "unknown",
            "implementation_difficulty": "medium",
            "confidence": "high source confidence, low value confidence because pre-gate public version is unavailable",
            "decision": "DO NOT TRANSFER",
        },
        {
            "rank": 3,
            "mechanism": "registered route-compatible COW/SHEEP bundle substitution",
            "class": "ADAPTIVE / STRUCTURAL / MARKET",
            "v3_behavior": "fixed different livestock programme",
            "v5_behavior": "observable shop, price, and opponent supply pressure relabels conserved bundles with caps",
            "causal_value_vs_v3": "confounded by complete-policy difference",
            "tail_effect": "full V5 has bad paired tails and escape failures",
            "market_effect": "material but not isolated",
            "current_best_compatibility": "not established",
            "implementation_difficulty": "high",
            "confidence": "medium mechanism description; low causal value confidence",
            "decision": "REJECT AS TRANSFER",
        },
        {
            "rank": 4,
            "mechanism": "step-718 complete terminal sell frontier",
            "class": "TERMINAL / MARKET",
            "v3_behavior": "different terminal route",
            "v5_behavior": "sells all visible sellable shed inventory at the last actionable step",
            "causal_value_vs_v3": "not isolated",
            "tail_effect": "V5 mean remaining terminal value is about 112 coins, so residual is small but nonzero",
            "market_effect": "late liquidation only",
            "current_best_compatibility": "conceptually high but already part of the inherited lineage and not proven as a V5 revision",
            "implementation_difficulty": "low",
            "confidence": "medium",
            "decision": "NO NEW TRANSPLANT",
        },
        {
            "rank": 5,
            "mechanism": "complete V5 economy",
            "class": "STRUCTURAL",
            "v3_behavior": "public V3 economy",
            "v5_behavior": "guarded replay plus multiple adaptive/repair wrappers",
            "causal_value_vs_v3": {"own_mean": 3918.0625, "advantage_mean": -7586.2292, "note": "descriptive paired complete-policy comparison, not causal mechanism value"},
            "tail_effect": "poor paired tail; 40/48 escape failures",
            "market_effect": "opponent externality makes own and advantage conclusions disagree",
            "current_best_compatibility": "unsafe/inconsistent",
            "implementation_difficulty": "very high",
            "confidence": "high rejection confidence",
            "decision": "REJECT",
        },
    ]
    write_json("farming_v5_mechanism_table.json", {"value_types": {"compounding": "more lifecycle output from earlier productive assets", "market": "same/changed output realized under different shared prices", "capital_sequencing": "commitment timing changes later affordability"}, "ranked_mechanisms": mechanisms, "single_strongest_change": "No positive causal mechanism qualified. The only exact public revision, v2 window commitment, is worth exactly 0 coins on all 48 paired conditions."})

    counterfactuals = {
        "exact_reverse_ablation": {"experiment": "current V5 v2 -> public V5 v1", "source_scope": changed_members, "results": v5_v1, "conclusion": "Zero action, own-money, opponent-money, advantage, and tail effect in every tested condition."},
        "synthetic_state_counterfactual": synthetic,
        "v3_forward_transplants": {"status": "NOT RUN", "reason": "V3 is not V5's parent, so source-level forward transplants would combine unrelated economies and would not isolate the public v2 timing change."},
        "current_best_transplants": {"status": "NOT RUN", "reason": "The only exact timing revision produced 0 value; no repeatable approximately +1k signal met the prerequisite for CurrentBest modification."},
    }
    write_json("farming_v5_counterfactuals.json", counterfactuals)
    write_json("farming_v5_ablation_results.json", {"status": "STOPPED AFTER EXACT NATURAL ABLATION", "completed": counterfactuals["exact_reverse_ablation"], "not_run": [counterfactuals["v3_forward_transplants"], counterfactuals["current_best_transplants"]], "reason": "Scientific stop rule: raw V5 is not robustly stronger, has critical safety failures, and the isolated v2 mechanism has a repeatable signal of 0 rather than >=+1k."})

    def econ_variant(variant: str) -> dict[str, Any]:
        rows = details[variant]
        return {
            "conditions": len(rows),
            "own_money_mean": statistics.fmean(r["own_money"] for r in rows),
            "advantage_mean": statistics.fmean(r["advantage"] for r in rows),
            "revenue": mean_dict(rows, "revenue"),
            "harvest": mean_dict(rows, "harvest"),
            "sales": mean_dict(rows, "sales"),
            "sale_average_prices": mean_dict(rows, "sale_average_prices"),
            "sale_day_weighted": mean_dict(rows, "sale_day_weighted"),
            "seed_spend": mean_dict(rows, "seed_spend"),
            "product_spend": mean_dict(rows, "product_spend"),
            "animal_spend": mean_dict(rows, "animal_spend"),
            "land_spend": mean_scalar(rows, "land_spend"),
            "labor_spend": mean_scalar(rows, "labor_spend"),
            "peak_hands_mean": statistics.fmean(r["milestones"]["peak_hands"] for r in rows),
            "peak_animals_mean": statistics.fmean(r["milestones"]["peak_animals"] for r in rows),
            "terminal_remaining_value_mean": statistics.fmean(r["terminal"]["value"] for r in rows),
            "escape_events": sum(len(r["livestock_escapes"]) for r in rows),
        }

    ev5 = econ_variant("v5")
    ev3 = econ_variant("v3")
    ecb = econ_variant("current_best")
    def econ_delta(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
        return {
            "own_money_mean": left["own_money_mean"] - right["own_money_mean"],
            "advantage_mean": left["advantage_mean"] - right["advantage_mean"],
            "revenue": subtract_dict(left["revenue"], right["revenue"]),
            "harvest": subtract_dict(left["harvest"], right["harvest"]),
            "sales": subtract_dict(left["sales"], right["sales"]),
            "seed_spend": subtract_dict(left["seed_spend"], right["seed_spend"]),
            "product_spend": subtract_dict(left["product_spend"], right["product_spend"]),
            "animal_spend": subtract_dict(left["animal_spend"], right["animal_spend"]),
            "land_spend": left["land_spend"] - right["land_spend"],
            "labor_spend": left["labor_spend"] - right["labor_spend"],
        }

    economic_attribution = {
        "scope": "Descriptive six-condition dossier (three opponents x both seats, one fresh seed each). Do not substitute these means for the 48-condition broad estimates.",
        "variants": {"v5": ev5, "v3": ev3, "current_best": ecb},
        "deltas": {"v5_minus_v3": econ_delta(ev5, ev3), "v5_minus_current_best": econ_delta(ev5, ecb)},
        "attribution": "Against V3 in the dossier, V5 gives up milk, wool, and strawberry revenue, uses fewer animals, and spends slightly more on labor; this is a complete-economy composition difference, not a timing-only gain. Against CurrentBest, V5's higher wool and lower milk mix is partly market/opponent dependent. The exact v2 timing revision changes none of these quantities.",
    }
    write_json("farming_v5_economic_attribution.json", economic_attribution)

    timing_attribution = {
        "scope": "Exact v1->v2 causal attribution plus descriptive V3/V5 timing comparison",
        "events": [
            {"event": "first animal signal", "v3_timing": "not comparable", "v5_timing": "cow88; direct Yarn may act, otherwise non-Yarn signal deferred", "timing_shift": None, "direct_downstream_value": None, "indirect_capital_effect": "unknown", "market_effect": "milk/wool exposure", "confidence": "source-high, value-low"},
            {"event": "post-second-shop commitment", "v3_timing": "not present", "v5_v1_timing": "independent decisions at 150, 169, 176", "v5_v2_timing": "decision at 150 reused at 169 and 176 subject to cap", "timing_shift": "later decisions committed to earlier information window", "direct_downstream_value": 0, "indirect_capital_effect": 0, "market_effect": 0, "confidence": "high across 48 exact pairs"},
            {"event": "land expansion", "v3_timing": [150, 265], "v5_timing": [150, 265], "timing_shift": [0, 0], "direct_downstream_value": 0, "indirect_capital_effect": 0, "market_effect": 0, "confidence": "high"},
            {"event": "labor", "v3_timing": "distinct fixed route; dossier labor spend 5914 mean", "v5_timing": "distinct route; dossier labor spend 6387 mean", "timing_shift": "structural/not isolated", "direct_downstream_value": None, "indirect_capital_effect": "confounded", "market_effect": "indirect", "confidence": "descriptive"},
            {"event": "livestock purchases", "v3_timing": {"cow": [1,65,88,150,169,176,195], "sheep": [1,195,217,226,241,265]}, "v5_timing": {"adaptive_cow_possible": [1,66,88,150,169,176,195,313], "adaptive_sheep_possible": [1,150,169,195,313]}, "timing_shift": "not timing-only; source animal direction and whole later route differ", "direct_downstream_value": None, "indirect_capital_effect": "confounded", "market_effect": "large mix effect", "confidence": "descriptive"},
            {"event": "crop cohorts", "v3_timing": "early melon day 0; distinct strawberry/wheat route", "v5_timing": "same early melon window; route-dependent later strawberries and wheat", "timing_shift": "structural/not isolated", "direct_downstream_value": None, "indirect_capital_effect": "confounded", "market_effect": "production and timing both change", "confidence": "descriptive"},
            {"event": "terminal liquidation", "v3_timing": "different route", "v5_timing": "complete frontier at step 718", "timing_shift": "frontier-specific", "direct_downstream_value": "not isolated; V5 residual terminal value mean ~112", "indirect_capital_effect": 0, "market_effect": "last-turn sale", "confidence": "medium"},
        ],
        "name_explanation": "In the actual public v2 revision, 'Timing Optimized' means stabilizing a livestock-direction decision at the step-150 second-shop information window and carrying it through the step-169/176 bundle window. It does not move land, hires, animal purchase turns, crops, sells, or terminal cutoff. In the tested natural games the new commitment never changed an action, so the measured economic value is 0.",
    }
    write_json("farming_v5_timing_attribution.json", timing_attribution)

    not_run_reason = "Scientific stop rule: no isolated V5 mechanism achieved a repeatable approximately +1k signal; raw V5 was statistically uncertain, tail-unsafe, and had livestock escapes in 40/48 games."
    write_json("farming_v5_candidate_manifest.json", {"status": "NOT RUN", "reason": not_run_reason, "candidates_built": [], "agents_modified": [], "submission_modified": False})
    write_json("farming_v5_candidate_results.json", {"status": "NOT RUN", "reason": not_run_reason, "results": []})
    write_json("farming_v5_selection_results.json", {"status": "NOT RUN", "reason": "No candidate passed the prerequisite into selection.", "selected": None, "current_best_remains": "agents/top50_distilled/top50_observable_portfolio.py"})
    write_json("farming_v5_finalist_lock.json", {"status": "NOT RUN", "reason": "No finalist existed; locking a nonexistent candidate would fabricate a stage.", "finalist": None})
    write_json("farming_v5_final_validation.json", {"status": "NOT RUN", "reason": "No finalist existed. No validation, final-unseen, packaging, upload, or submission was performed.", "results": []})

    timing_md = f"""# Farming V5 timing forensics

## Finding

The exact public v2 change is much narrower than the title suggests. Version 1 already deferred an immature non-Yarn signal at the `cow88` registered bundle until the second shop could be seen at `cow150`. Version 2 adds one commitment: the direction chosen at `cow150` is reused at `cow169` and `cow176`, subject to the maximum three COW-to-SHEEP substitutions.

Nothing else moved in the public v1→v2 archive: only `agents/e773a_demand_aligned_pasture_network.py` changed. Land, hire, animal purchase nodes, quantities, routes, feeding, crops, sales, and terminal liquidation are byte-identical.

## Exact controlled result

Across 48 same-seed/opponent/seat pairs, v1 and v2 had a 719-action common prefix in every game. Own-money delta, opponent-money delta, advantage delta, and every tail statistic were exactly zero. A synthetic state confirms the code can matter: when `cow150` prefers COW and later wool pressure flips, v1 changes `cow169` to SHEEP while v2 keeps COW. That is a semantic capability test, not economic evidence.

## Broader timing dimensions

| Dimension | V3 | V5 | Finding |
|---|---|---|---|
| Land | orders at 150, 265 | orders at 150, 265 | no change |
| Labor | different replay schedule; mean dossier spend 5,914 | different replay schedule; mean 6,387 | structural, not isolated timing |
| Livestock | fixed programme, about 17 peak animals | conserved adaptive bundles, about 14 peak animals | direction/mix and programme differ; not timing-only |
| Melon | day-0 cohort, harvest around 245–264 | same core day-0 window | no current v2 change |
| Strawberry/Wheat | V3-specific cohorts | Kenjo/Niklita-derived cohorts | structural route difference |
| Sell/hold | V3-specific production and sale route | conserved sale-allocation wrappers | quantity and production confounded |
| Terminal | different route | full sell frontier at 718 | coherent but not isolated as a v2 revision |

## Same-turn semantics and execution failure

The harness uses the environment's real ordered market actions, affordability, expenses, and sales. The initial cross-version module-loader collision was corrected and its output excluded. In corrected runs, the major safety defect is real: in 40/48 V5 games, at step 210 the actor on pasture `[5,3]` requests `FEED` without carried wheat; the silent no-op leads to escape at the end of step 215. This is an executor/resource failure, not a timing gain.

## Why the name?

Empirically, “Timing Optimized” refers to **when visible shop evidence is considered mature and how long the resulting livestock direction remains committed**. It is not a general retiming of the farm economy. The public v2 refinement contributed {v5_v1['summary']['overall']['own_money_delta']['mean']:.0f} measured coins on this panel.
"""
    write_text("farming_v5_timing_forensics.md", timing_md)

    dossier_md = f"""# Farming V5 economic dossier

## Policy classification

V5 is a **bounded state-adaptive guarded replay**. Its base is a replay/network assembled from attributed NIklitaCheporev and Kenjo1209 traces. Wrappers add sale allocation, weed and funding repair, observable demand-aligned COW/SHEEP substitution, a terminal animal frontier, latent-pasture activation/exact delivery, late-bundle diversification, and a final complete liquidation frontier. It uses public observation only—no opponent identity, hidden seed, reward, or future state.

## Economic phases

1. **Opening and first quadrant:** commit the day-0 melon and wheat geometry, begin the animal/structure route, and build low-cost labor.
2. **First production waves:** harvest/rotate wheat, service livestock, collect fertilizer, and sell into predefined nodes with funding repair.
3. **Information window:** `cow88` uses only direct Yarn evidence early; `cow150` sees the later shop state. V2 holds that direction through the `cow169`/`cow176` window.
4. **Expansion and strawberry buildout:** request land at steps 150 and 265; add later strawberry/wheat cohorts and continue bounded livestock substitutions.
5. **Mature economy:** monetize strawberry, milk, wool, fertilizer, wheat, and the melon cohort while the repair wrappers keep the replay feasible.
6. **Endgame:** stop through the inherited late programme and sell all visible sellable shed inventory at step 718.

## Mean six-condition dossier

| Metric | CurrentBest | V3 | V5 |
|---|---:|---:|---:|
| Final own money | {ecb['own_money_mean']:.0f} | {ev3['own_money_mean']:.0f} | {ev5['own_money_mean']:.0f} |
| Advantage | {ecb['advantage_mean']:.0f} | {ev3['advantage_mean']:.0f} | {ev5['advantage_mean']:.0f} |
| Peak hands | {ecb['peak_hands_mean']:.1f} | {ev3['peak_hands_mean']:.1f} | {ev5['peak_hands_mean']:.1f} |
| Peak animals | {ecb['peak_animals_mean']:.1f} | {ev3['peak_animals_mean']:.1f} | {ev5['peak_animals_mean']:.1f} |
| Land spend | {ecb['land_spend']:.0f} | {ev3['land_spend']:.0f} | {ev5['land_spend']:.0f} |
| Labor spend | {ecb['labor_spend']:.0f} | {ev3['labor_spend']:.0f} | {ev5['labor_spend']:.0f} |
| Escape events | {ecb['escape_events']} | {ev3['escape_events']} | {ev5['escape_events']} |

The detailed commodity-level revenue, harvest, sales, realized prices, weighted sale days, and spending are preserved in `farming_v5_economic_attribution.json`.

## Crop cohorts

- **Melon:** the main 12-tile cohort is planted on day 0 (roughly steps 4–19), harvested around steps 245–264, and yields about 72 units. It is not the v2 innovation.
- **Strawberry:** multiple ongoing cohorts begin around the midgame and sell through roughly steps 381–701. Compared with V3, timing and quantities differ as part of another route, so there is no clean timing-only value estimate.
- **Wheat:** repeated small cohorts support both sales and livestock feed. Purchases/seeding continue late. At step 210 the exact-delivery system can still leave a pasture actor without carried feed, causing the documented escape.

## Livestock, labor, land, and market

The registered adaptive bundles are `cow88` (1), `cow150` (2), `cow169` (1), `cow176` (1), and `sheep313` (1). COW→SHEEP substitutions are capped at three and SHEEP→COW at one. The pressure score is `2*YARN_STORE + WOOL_price/200` versus `PIZZA + ICE_CREAM + SMOOTHIE + MILK_price/160`, adjusted by visible opponent cow/sheep balance.

Land timing is exactly the same as V3 and CurrentBest at requests 150/265. V5 typically reaches 12 hands. Its sale logic changes market exposure and can raise own money while helping the opponent even more: versus Crop Dusta, V5's paired own delta over CurrentBest is positive but its advantage delta is strongly negative.

## Terminal

The step-718 frontier is sensible and leaves only about {ev5['terminal_remaining_value_mean']:.0f} coins of mean measured sellable terminal value in the dossier. It was not introduced by the v2 timing change and was not isolated as a transferable gain.
"""
    write_text("farming_v5_economic_dossier.md", dossier_md)

    report = f"""# Farming Score V5: Timing Optimized — deep forensic report

## Executive decision

**No candidate was built or promoted. CurrentBest remains frozen.** The exact public V5 v2 mechanism produced zero behavioral/economic difference across 48 paired conditions. Full V5 averaged **+1,136 own coins** versus CurrentBest but **−3,494 advantage**, had a negative median own delta, a 95% bootstrap interval crossing zero, severe downside, and livestock escapes in 40/48 games. The scientific stop rule fired.

## 1–5. Source, reconstruction, name, and architecture

1. The notebook is Arlene (`lynnsakurai`), *Farming Score V5: Timing Optimized*, current public version 2, run 346466052, dated 2026-09-01.
2. Public v2 archive SHA: `35143710b4b493e2e94a68efa21aa03fc3833318fef52645b8e58d5ffeb4bf9e`; local `main.py`: `{sha(V5 / 'main.py')}`; reconstructed single-file main: `e8498c67914ecc607ae69fde25a728361eb5acea94c00ecc85deffbdafe50413`.
3. Reconstruction passed exact archive/member verification, compile/import, and 216 corrected local games with zero runtime/schema failures. No public replay was exposed, so independent public-action equivalence is not claimed beyond exact public-source reconstruction.
4. “Timing Optimized” means: decide the livestock direction at the step-150 second-shop information window, then reuse it for step-169/176 registered bundles, subject to the substitution cap. It does not retime purchases or the rest of the economy.
5. V5 is bounded state-adaptive guarded replay, not a fixed replay and not a free planner.

## 6–9. Economy, phases, V3 relationship, first divergence

6. The complete economy combines replayed melon/wheat/strawberry cohorts, pasture livestock, fertilizer, up to 12 hands, two land expansions, conserved sale nodes, repair wrappers, and step-718 liquidation.
7. Its phases are opening geometry, first production, shop-information window, land/strawberry buildout, mature multi-product monetization, and terminal liquidation.
8. There is no clean V3→V5 timing revision map: the retrieved V5 is a Kenjo/Niklita-derived lineage. Land timing is unchanged; livestock/crops/market/repair/terminal logic is structurally different. The genuine natural revision is public V5 v1→v2.
9. V3 and V5 diverge at step 0 in every pair: V3 buys 13 wheat; V5 places no market order. The full downstream chain is confounded, so this is not assigned as the cause of the final delta.

## 10–18. Controlled league

10. V5−V3 own money: mean **+3,918**, median +4,498, bootstrap 95% CI **[−1,231, +9,285]**.
11. V5−V3 advantage: mean **−7,586**, CI **[−12,430, −3,137]**.
12. V5−CurrentBest own money: mean **+1,136**, median −592, CI **[−4,964, +7,350]**.
13. V5−CurrentBest advantage: mean **−3,494**, CI **[−8,793, +1,120]**.
14. Broad paired V5−V3 advantage W/L/T is 12/36/0; direct games versus V3 are **0/8/0**.
15. Broad paired V5−CurrentBest advantage W/L/T is 26/22/0; direct games versus CurrentBest are **4/4/0**.
16. V5 absolute own-money P10/P5/worst are **61,146 / 56,727 / 51,527**. Paired V5−CurrentBest P10/P5/worst are **−16,798 / −38,192 / −45,241**.
17. V5 improves V3's absolute tail levels on this panel, but the paired tail remains bad and direct V3 H2H is 0–8. It did not reliably repair V3's failure regimes.
18. Crop Dusta is not repaired: V5−CurrentBest own delta is +14,184, but advantage is −13,561 and direct broad-condition H2H is 2–6; the opponent benefits even more from the shared market.

## 19–28. Timing and causal mechanisms

19. Land: no change—requests remain 150 and 265.
20. Labor: no isolated optimization; V5's distinct route spends about 6,387 versus V3's 5,914 in the dossier.
21. Livestock: the meaningful source change is evidence timing/commitment at cow88/cow150/cow169/cow176, not earlier purchases. V5 also has fewer animals and an unrelated programme.
22. Crops: no v1→v2 change. V3/V5 strawberry and wheat differences are structural; the core early melon cohort is similar.
23. Market: no v1→v2 change. Full-policy shared-market effects explain why own-money and advantage conclusions disagree.
24. Terminal: V5 sells visible inventory at 718; useful in principle, but unchanged v1→v2 and not isolated versus V3.
25. No positive V5 mechanism qualified as strongest. The most important exact public change is the shop-window commitment only because it is the sole v2 revision.
26. Its measured causal value is **exactly 0 coins**: v1 and v2 were action-identical in all 48 conditions.
27. Rejected: full V5 economy, adaptive pasture substitution as a transplant, the unisolated cow88 maturity gate, and terminal frontier as a claimed new V5 gain.
28. Nothing transferred to CurrentBest; its source remains unchanged.

## 29–40. Candidate funnel and safety

29. Candidate agents built: none.
30. Strongest candidate: none; CurrentBest remains the reference.
31–39. Candidate paired deltas, H2H, natural RNG, broad results, P10/P5/worst: **NOT RUN**, because no candidate entered the funnel.
40. Full V5 has 0 runtime and schema failures but fails safety: 40 escapes in 40/48 games, always at step 215 on pasture `[5,3]` (32 COW, 8 SHEEP). At step 210 it requests FEED without carried wheat, a silent no-op; the animal escapes at end of day.

## 41–46. Attribution and decision

41. Economic attribution: in the six-condition dossier V5 trails V3 mainly in milk, wool, and strawberry revenue, uses fewer animals, and spends somewhat more on labor. The full commodity tables are in the attribution artifact.
42. Timing attribution: only the v2 step-150 commitment is causal and exactly tested; it changes zero natural actions and is worth zero. All V3/V5 timing comparisons are descriptive because lineage and quantities change together.
43. New research best promoted: **No**.
44. Promoted path/SHA: not applicable. Frozen CurrentBest remains `agents/top50_distilled/top50_observable_portfolio.py`, SHA `f9ca672848ccffdfe56888d99bcdf5a9d7644062b9eec0cf0cdea13574931233`.
45. Unexplained: the original author's private/public leaderboard motivation for v2 and regimes outside the tested panel where the commitment triggers economically. The notebook's current v2 score was not public in retrieved metadata.
46. Best next direction: independently repair and test the step-210 exact-feed delivery defect **only if** future evidence makes the complete V5 economy strategically attractive; otherwise study a different public lineage with a source-identifiable, behaviorally active revision. Do not transplant the zero-value window commitment.

## Frozen-state assurance

- CurrentBest raw/LF SHA: `f9ca672848ccffdfe56888d99bcdf5a9d7644062b9eec0cf0cdea13574931233`.
- `experiments/current_best.json` SHA: `789842d027703a66f083f3ff0ffc541172d7fd1c76819732075e04fbddb1c521`.
- `submission/main.py` raw/LF SHA: `789bb9bbd5122eb4891983e776a13777328e3e87736cbbc0b4bc86d13fc33f9b`.
- No candidate, package, upload, submission, or Kaggle write API was used.
"""
    write_text("farming_v5_deep_dive_report.md", report)


if __name__ == "__main__":
    main()
