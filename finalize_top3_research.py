"""Lock the Top-3 forensic stage, write causal decisions, and retain CurrentBest."""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parent
EXP = ROOT / "experiments"


def load(name):
    return json.loads((EXP / name).read_text())


def write(name, value):
    (EXP / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def file_sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def paired_common_raw(raw, candidate_path, baseline_path):
    games = raw["games"]
    allowed = {"K3", "Lifecycle", "PublicOpening"}
    def key(row):
        return row["opponent"], row["seed"], row["seat"], row["shop_mode"]
    candidate = {key(row): row for row in games if row["candidate"] == candidate_path and row["opponent"] in allowed}
    baseline = {key(row): row for row in games if row["candidate"] == baseline_path and row["opponent"] in allowed}
    values = [candidate[key]["money"] - baseline[key]["money"] for key in sorted(candidate.keys() & baseline.keys())]
    return {
        "pairs": len(values), "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values), "ties": sum(value == 0 for value in values),
        "mean": statistics.fmean(values), "median": statistics.median(values),
        "p10_nearest_rank": sorted(values)[max(0, int(.10 * (len(values) - 1)))], "worst": min(values),
    }


def split_ablation(ablation, name):
    path = ablation["candidates"][name]
    baseline_path = ablation["candidates"]["CurrentBest"]
    def condition(row):
        return "|".join(row["key"].split("|")[2:])
    baseline = {condition(row): row for row in ablation["games"] if row["candidate"] == baseline_path}
    candidate = {condition(row): row for row in ablation["games"] if row["candidate"] == path}
    output = {}
    for mode in ("fixed", "natural"):
        deltas = [candidate[key]["money"] - baseline[key]["money"] for key in candidate.keys() & baseline.keys() if f"|{mode}|" in f"|{key}|"]
        output[mode] = {
            "pairs": len(deltas), "wins": sum(value > 0 for value in deltas),
            "losses": sum(value < 0 for value in deltas), "ties": sum(value == 0 for value in deltas),
            "mean": statistics.fmean(deltas), "worst": min(deltas),
        }
    return output


def main():
    version = load("top3_version_audit.json")
    direct = load("top3_direct_comparison.json")
    adaptive = load("top3_adaptive_divergence_map.json")
    raw = load("top3_raw_parent_league.json")
    ablation = load("top3_ablation_results.json")
    decomposition = load("top3_counterfactual_decomposition.json")
    current = load("current_best.json")
    top = {row["rank"]: row for row in direct["top3"]}
    adaptive_by_rank = {row["rank"]: row for row in adaptive["strategies"]}
    baseline_path = current["agent_path"]
    rank1_common = paired_common_raw(raw, "agents/top3_tuned/raw_rank1_tetsuya.py", baseline_path)
    rank2_common = paired_common_raw(raw, "agents/top3_tuned/raw_rank2_crop_dusta.py", baseline_path)
    rank3_common = paired_common_raw(raw, "agents/top3_tuned/raw_rank3_oceanmix.py", baseline_path)

    hypotheses = [
        {
            "id": "H1_rank1_sheep_fertilizer_compounding",
            "hypothesis": "Rank1's sheep/wool/fertilizer-heavy capital engine is a transferable improvement over the portfolio's existing livestock mix.",
            "source_rank": 1, "tier_before_test": "B",
            "replay_evidence": {
                "episodes": top[1]["episodes"], "median_peak_sheep": top[1]["peak_animals"]["SHEEP"]["median"],
                "mean_wool_revenue": top[1]["commodity"]["WOOL"]["mean_revenue"],
                "mean_fertilizer_revenue": top[1]["commodity"]["FERTILIZER"]["mean_revenue"],
            },
            "economic_rationale": "Wool and fertilizer diversify away from milk/melon gluts and finance the fixed day-7/day-10 land schedule.",
            "counterfactual_implementation": "Use the complete Rank1 medoid continuation, preserving its animals, crops, labor and sales rather than swapping single animal orders.",
            "development_result": {"initial_common_hard_panel": rank1_common, "raw_league_overall": raw["summary"]["Rank1_public_medoid"]},
            "fresh_result": decomposition["scenario_summary"]["rank1_medoid_vs_baseline"],
            "safety": "Failed: fresh reconstruction lost six animals in four paired games; broader raw league lost 16.",
            "evidence_label": "REPLICATED_IN_ONE_SPLIT_NOT_GENERALIZED", "decision": "REJECT",
        },
        {
            "id": "H2_rank3_opening_parent_swap",
            "hypothesis": "For the public step-1 3000-money/0-hand opening, replace redblack with the complete Rank1 economy.",
            "source_rank": 1, "tier_before_test": "B",
            "replay_evidence": "Rank1 medoid beat Rank3 medoid 8-0 with +47,011 mean advantage in the initial controlled league.",
            "economic_rationale": "Rank1's diversified three-quadrant economy appeared to dominate Rank3's more synchronized melon/strawberry route.",
            "counterfactual_implementation": "A_rank3_swap; both parents pass at step 0, so the continuation starts from a compatible state.",
            "development_result": ablation["paired_vs_current_best"]["A_rank3_swap"],
            "fresh_result": decomposition["scenario_summary"]["rank3_signature"],
            "safety": "Failed: animal escapes and catastrophic P10.",
            "evidence_label": "CAUSALLY_NEGATIVE", "decision": "REJECT",
            "failure_mechanism": "The same step-1 signature also aliases CurrentBest; new market paths break the fixed Rank1 medoid's coordinated crop/livestock schedule by day 4.",
        },
        {
            "id": "H3_k3_opening_parent_swap",
            "hypothesis": "For the exact public step-1 <=3-money/4-hand opening, replace Dmitry with Rank1.",
            "source_rank": 1, "tier_before_test": "B",
            "replay_evidence": "Initial common K3 conditions showed Rank1 earning about 24.4k more own money than CurrentBest.",
            "economic_rationale": "The wool/fertilizer route seemed to exploit K3's market footprint better than Dmitry.",
            "counterfactual_implementation": "B_k3_swap with every non-selected branch frozen.",
            "development_result": ablation["paired_vs_current_best"]["B_k3_swap"],
            "fresh_result": decomposition["scenario_summary"]["k3_signature"],
            "safety": "Failed: ten animal escapes in four decomposed pairs.",
            "evidence_label": "CAUSALLY_NEGATIVE", "decision": "REJECT",
        },
        {
            "id": "H4_continuing_observable_adaptation",
            "hypothesis": "Continuing state-dependent decisions after the opening, rather than one step-1 selection followed by a fixed route, is a genuine shared Top3 advantage.",
            "source_rank": "1/2/3", "tier_before_test": "A_observed",
            "replay_evidence": {row["rank"]: {"classification": row["classification"], "unique_routes": row["unique_action_trajectories"], "first_divergence": row["first_any_full_action_divergence"]} for row in adaptive["strategies"]},
            "economic_rationale": "Visible bank, inventory, price and opponent-production differences alter feasible feed, cohort and liquidation schedules.",
            "counterfactual_implementation": "The most conservative available proxy was a complete public medoid parent. It failed because it omitted the source's later branches.",
            "development_result": "All fixed-medoid substitutions failed; no simple trigger separated the routes without state aliasing.",
            "fresh_result": "Not causally isolated; source policy is not public.",
            "safety": "Do not invent a hidden adaptive rule from episode id/seed/future state.",
            "evidence_label": "OBSERVED_SHARED_NOT_YET_CAUSAL", "decision": "DEFER",
        },
        {
            "id": "H5_rank2_early_land_wheat_throughput",
            "hypothesis": "Rank2's day-5/day-8 land timing and high wheat throughput transfer profitably.",
            "source_rank": 2, "tier_before_test": "C",
            "replay_evidence": {"land": top[2]["land_purchase_timing"], "mean_wheat_revenue": top[2]["commodity"]["WHEAT"]["mean_revenue"]},
            "economic_rationale": "Earlier capacity can produce more crop cycles, but it requires heavy feed/product buying and labor.",
            "counterfactual_implementation": "Complete Rank2 public medoid, because land alone is not state compatible with the downstream route.",
            "development_result": {"initial_common_hard_panel": rank2_common, "raw_league": raw["summary"]["Rank2_public_medoid"]},
            "fresh_result": decomposition["scenario_summary"]["rank2_medoid_vs_baseline"],
            "safety": "Failed: 16 escapes in four fresh pairs and 212 in the broad raw league.",
            "evidence_label": "CORRELATED_NOT_GENERALIZED", "decision": "REJECT",
        },
        {
            "id": "H6_premium_staggering_and_externality",
            "hypothesis": "Top3 premium sale staggering improves realization and can also lower opponent prices.",
            "source_rank": "1/2/3", "tier_before_test": "C",
            "replay_evidence": {row["team"]: {item: row["commodity"][item] for item in ("MELON", "STRAWBERRY", "MILK", "WOOL")} for row in direct["top3"]},
            "economic_rationale": "Premium price curves punish synchronized gluts; observed own-sale steps immediately reduce price, especially melon/strawberry/wool.",
            "counterfactual_implementation": "Not implemented: pooled inventory and simultaneous town/opponent orders prevent identifying a safe isolated sale phase from this corpus.",
            "development_result": None, "fresh_result": None,
            "safety": "A single SELL transplant would violate coherent-phase and no-hidden-state rules.",
            "evidence_label": "OBSERVED_CORRELATION", "decision": "DEFER",
        },
        {
            "id": "H7_rank3_lower_labor_cost",
            "hypothesis": "Rank3's lower labor spend is a transferable efficiency gain.",
            "source_rank": 3, "tier_before_test": "C",
            "replay_evidence": {"mean_labor_spend": top[3]["mean_labor_spending"], "median_productive": top[3]["max_productive"]["median"]},
            "economic_rationale": "Similar productive scale with lower hire cost can raise net income if crop servicing remains adequate.",
            "counterfactual_implementation": "Complete Rank3 medoid; isolated hand deletion would invalidate routing.",
            "development_result": {"initial_common_hard_panel": rank3_common, "raw_league": raw["summary"]["Rank3_public_medoid"]},
            "fresh_result": decomposition["scenario_summary"]["rank3_medoid_vs_baseline"],
            "safety": "No escapes, but own money did not generalize and stranding appeared in raw league.",
            "evidence_label": "REPLICATED_IN_ONE_SPLIT_NOT_GENERALIZED", "decision": "REJECT",
        },
    ]
    write("top3_causal_hypotheses.json", {"schema_version": 1, "hypotheses": hypotheses})

    candidate_rows = []
    for name in ("A_rank3_swap", "B_k3_swap", "C_combined"):
        path = ablation["candidates"][name]
        candidate_rows.append({
            "name": name, "path": path, "sha256": file_sha(path),
            "motivation": {
                "A_rank3_swap": "Rank1 8-0 initial medoid result versus Rank3 public opening",
                "B_k3_swap": "Rank1 initial own-money gain versus exact K3 public opening",
                "C_combined": "interaction ablation of the two individually motivated branches",
            }[name],
            "dimensions_changed": {
                "A_rank3_swap": ["parent selected for exact 3000-money/0-hand step-1 state"],
                "B_k3_swap": ["parent selected for exact <=3-money/4-hand step-1 state"],
                "C_combined": ["both exact parent-selection branches"],
            }[name],
            "all_other_economics_frozen": True,
            "development": ablation["paired_vs_current_best"][name],
            "rng_breakdown": split_ablation(ablation, name),
            "decision": "REJECT",
        })
    write("top3_microtuning_candidates.json", {"schema_version": 1, "candidates": candidate_rows, "serious_finalist": None})

    gate_reason = (
        "Every evidence-backed candidate failed the small development gate: zero positive paired own-money conditions, "
        "large negative means/P10, and livestock escapes. Per the locked stop rule no candidate was allowed to consume "
        "validation, selection, or final-unseen seeds."
    )
    write("top3_validation_results.json", {
        "schema_version": 1, "status": "NOT_RUN_STOP_RULE", "reason": gate_reason,
        "development_artifact": "experiments/top3_ablation_results.json",
        "validation_seeds_remain_unconsumed": list(range(1262100, 1262104)) + list(range(1262200, 1262204)),
        "candidate_advanced": None,
    })
    write("top3_selection_results.json", {
        "schema_version": 1, "status": "NOT_RUN_NO_VALIDATED_CANDIDATE", "reason": gate_reason,
        "selection_seeds_remain_unconsumed": list(range(1263100, 1263108)) + list(range(1263200, 1263208)),
        "selected_candidate": None,
    })
    lock = {
        "schema_version": 1, "locked_finalist": None, "promotion": False,
        "retained_research_best": {"path": baseline_path, "sha256": file_sha(baseline_path), "version": current["agent_version"]},
        "reference_control": {"path": current["previous_best_path"], "sha256": file_sha(current["previous_best_path"])},
        "rejected_candidates": [{"path": row["path"], "sha256": row["sha256"]} for row in candidate_rows],
        "reason": gate_reason,
        "submission_main_untouched_sha256": file_sha("submission/main.py"),
    }
    write("top3_finalist_lock.json", lock)
    write("top3_final_validation.json", {
        "schema_version": 1, "status": "NOT_RUN_NO_LOCKED_FINALIST", "reason": gate_reason,
        "final_unseen_seeds_remain_unconsumed": list(range(1264100, 1264112)) + list(range(1264200, 1264212)),
        "retained_research_best": lock["retained_research_best"],
        "development_natural_rng": {name: split_ablation(ablation, name)["natural"] for name in ("A_rank3_swap", "B_k3_swap", "C_combined")},
        "safety_of_retained_best_in_development": {
            "runtime_failures": ablation["summary"]["CurrentBest"]["runtime_failures"],
            "semantic_failures": ablation["summary"]["CurrentBest"]["semantic_failures"],
            "actual_livestock_escapes": ablation["summary"]["CurrentBest"]["actual_livestock_escapes"],
            "meaningful_stranding_games": ablation["summary"]["CurrentBest"]["meaningful_stranding_games"],
        },
    })

    rows = direct["top3"]
    report = [
        "# Current Top-3 forensic research and evidence-based micro-tuning", "",
        "## Executive result", "",
        f"The current live Top 3 at `{version['leaderboard_captured_at']}` were **{rows[0]['team']}**, **{rows[1]['team']}**, and **{rows[2]['team']}**. I analyzed 30 exact-current-submission appearances per team (90 total, 87 unique replay files). The central frontier pattern is continued observable-state adaptation after a stable opening, not a single superior fixed route.", "",
        f"No micro-tuned candidate survived the development gate. The research best remains `{baseline_path}` at SHA-256 `{file_sha(baseline_path)}`. `submission/main.py` was not modified; its SHA-256 remains `{file_sha('submission/main.py')}`.", "",
        "## 1. Snapshot, version purity, and baseline", "",
        "| Rank | Team | Submission | Public score | Available public episodes | Analyzed |", "|---:|---|---:|---:|---:|---:|",
    ]
    for row in version["current_versions"]:
        report.append(f"| {row['rank']} | {row['team']} | {row['submission_id']} | {row['public_score']} | {row['available_public_episodes']} | {row['analyzed_current_version_appearances']} |")
    report += [
        "", "All appearances were attributed by exact public submission ID. Alternate active versions were excluded. Seventeen single-agent trajectories were exact action duplicates, but they were retained for economic analysis because market/opponent paths differed; no full replay was duplicated.", "",
        f"Current baseline: `{baseline_path}` (`{file_sha(baseline_path)}`), a step-1 observable selector over complete Dmitry/Hanserong/redblack replay parents. Reference control: `{current['previous_best_path']}` (`{file_sha(current['previous_best_path'])}`).", "",
        "## 2. Fixed versus adaptive", "",
        "| Rank | Classification | Distinct full routes | First action divergence | Opening farmer/crop/market agreement | Late field/market agreement |", "|---:|---|---:|---:|---|---|",
    ]
    for row in adaptive["strategies"]:
        opening = row["component_agreement_by_phase"]["opening"]
        late = row["component_agreement_by_phase"]["late_production"]
        report.append(f"| {row['rank']} | {row['classification']} | {row['unique_action_trajectories']}/{row['episodes']} | {row['first_any_full_action_divergence']} | {opening['farmer']:.1%} / {opening['crop']:.1%} / {opening['market']:.1%} | {late['crop']:.1%} / {late['market']:.1%} |")
    report += [
        "", "Rank 1 is phase-adaptive, Rank 2 strongly adaptive, and Rank 3 phase-adaptive with 17 exact route duplicates. Their openings are highly stable, but after reinvestment the field routes diverge sharply. The largest branches separate on current bank, prices, inventory, opponent animal/crop composition, and shop state. No simple rule reached causal status: episode ID, seed, future shops/prices, and final outcome were never used.", "",
        "## 3. Complete economic strategies", "",
        "| Rank | Land steps | Peak hands | Median cows/sheep/geese | Median peak wheat/melon/strawberry | Productive | Mean public money | Mean realized revenue |", "|---:|---|---:|---|---|---:|---:|---:|",
    ]
    for row in rows:
        land = ", ".join(str(int(value["median_step"])) for _, value in sorted(row["land_purchase_timing"].items()))
        animals = f"{row['peak_animals']['COW']['median']}/{row['peak_animals']['SHEEP']['median']}/{row['peak_animals']['GOOSE']['median']}"
        crops = f"{row['peak_crops']['WHEAT']['median']}/{row['peak_crops']['MELON']['median']}/{row['peak_crops']['STRAWBERRY']['median']}"
        report.append(f"| {row['rank']} | {land} | {row['max_hands']['median']} | {animals} | {crops} | {row['max_productive']['median']} | {row['money']['mean']:.0f} | {row['mean_total_sale_revenue']:.0f} |")
    report += [
        "", "### Rank 1 — tetsuya", "",
        f"Rank 1 opens with mixed livestock but is uniquely sheep/wool/fertilizer heavy. It hires earlier, buys land exactly at steps 168 and 240 (days 7 and 10), carries median peaks of {top[1]['peak_animals']['COW']['median']} cows and {top[1]['peak_animals']['SHEEP']['median']} sheep, then runs wheat, melon and strawberry cohorts over about {top[1]['max_productive']['median']:.0f} productive tiles. Mean wool, fertilizer, milk, strawberry and melon revenue are {top[1]['commodity']['WOOL']['mean_revenue']:.0f}, {top[1]['commodity']['FERTILIZER']['mean_revenue']:.0f}, {top[1]['commodity']['MILK']['mean_revenue']:.0f}, {top[1]['commodity']['STRAWBERRY']['mean_revenue']:.0f}, and {top[1]['commodity']['MELON']['mean_revenue']:.0f}. The capital model is diversification: wool/fertilizer cash supports land and labor while crop cohorts prevent dependence on milk alone.", "",
        "### Rank 2 — Crop Dusta", "",
        f"Rank 2 buys land earliest (steps {int(top[2]['land_purchase_timing']['1']['median_step'])} and {int(top[2]['land_purchase_timing']['2']['median_step'])}), ramps mixed livestock, and spends heavily on market wheat/feed ({sum(top[2]['mean_feed_spending'].values()):.0f} mean). It reaches {top[2]['max_productive']['median']:.0f} productive tiles and is the most state-dependent strategy. Its unusually high wheat realization is paired with high spending; the complete public medoid did not transfer safely.", "",
        "### Rank 3 — OceanMix", "",
        f"Rank 3 follows the most repeatable public skeleton: land at steps 150 and 265, exactly 12 peak hands, median 7 cows and 6 sheep, a 12-melon wave, then roughly 38 strawberries plus 40 wheat. It has the lowest mean labor spend ({top[3]['mean_labor_spending']:.0f}) and short premium holding, but greater synchronized-sale overlap and stronger immediate price impact.", "",
        "The complete day-by-day cash, assets, cohort windows, worker actions, animal service, realized prices, hold times, and endgame cutoffs are in the three dedicated dossiers:", "",
        "- `experiments/top3_rank1_strategy_dossier.md`", "- `experiments/top3_rank2_strategy_dossier.md`", "- `experiments/top3_rank3_strategy_dossier.md`", "",
        "## 4. Shared core, Rank-1 uniqueness, and market externality", "",
        "All three use three quadrants, a 12-hand ceiling, mixed cows and sheep, wheat→melon→strawberry-capable crop succession, recurring animal service, staggered within-season realization, and terminal liquidation. Most of that vocabulary already exists in CurrentBest. The important missing behavior is continued state-conditioned branching after expansion; CurrentBest commits at step 1.", "",
        f"Rank 1 uniquely emphasizes wool/fertilizer: mean wool revenue {top[1]['commodity']['WOOL']['mean_revenue']:.0f} and fertilizer revenue {top[1]['commodity']['FERTILIZER']['mean_revenue']:.0f}, while retaining broader crop diversification and earlier labor. This is OBSERVED, not proven causal.", "",
        "Premium sales are not held for many days: median weighted holds are generally below one day. Immediate observed price changes after own sale steps are largest for melon, strawberry and wool. Rank 3 has especially high same-turn sale overlap (melon about 86%, strawberry about 50%), consistent with aggressive joint-market pressure, but town consumption and simultaneous opponent orders prevent assigning the full price delta to its own action.", "",
        "## 5. Direct controlled league", "",
        "| Agent | W/L/T | Avg money | Avg advantage | P10 | P5 | Route fidelity | Actual escapes |", "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, row in sorted(raw["summary"].items(), key=lambda item: item[1]["average_advantage"], reverse=True):
        report.append(f"| {name} | {row['wins']}/{row['losses']}/{row['ties']} | {row['average_money']:.0f} | {row['average_advantage']:.0f} | {row['p10_advantage']:.0f} | {row['p5_advantage']:.0f} | {row['route_fidelity']:.3%} | {row['livestock_escapes']} |")
    report += [
        "", f"The Rank-1 medoid was strongest over the broad initial panel, but it split 4–4 directly with CurrentBest and had mean direct advantage {raw['controlled_h2h_matrix']['Rank1_public_medoid']['CurrentBest']['average_advantage']:.0f}. Its positive initial common-hard paired own-money result ({rank1_common['mean']:.0f}) reversed on fresh K3 attribution seeds ({decomposition['scenario_summary']['rank1_medoid_vs_baseline']['own_money_delta_mean']:.0f}). Rank 2's fixed medoid was especially unsafe because the real Rank-2 policy is strongly adaptive; this does not imply the leaderboard agent itself is weak.", "",
        "## 6. Advantage traced backward and difference-of-differences", "",
        "Matched K3 decompositions show the fixed medoids first acquire a durable bank difference from CurrentBest around day 19.5 (Rank 1), day 14 (Rank 2), and day 15 (Rank 3). On the fresh attribution split all three fixed medoids ended below CurrentBest in own money: Rank 1 −14,995, Rank 2 −23,954, Rank 3 −10,304. Rank 3 nevertheless improved net advantage by +8,139 because it also reduced opponent realization—evidence of a shared-market externality, not higher own income.", "",
        "Public replay difference-of-differences is intentionally not called causal: opponent and shop paths are uncontrolled. The consistent association is that Top‑3 economies reach 72–75 productive tiles, mix animals, and branch after expansion; the causal transplant of one fixed medoid failed.", "",
        "## 7. Causal hypotheses and micro-tuning", "",
        "| Hypothesis | Evidence status | Decision |", "|---|---|---|",
    ]
    for hypothesis in hypotheses:
        report.append(f"| {hypothesis['id']} | {hypothesis['evidence_label']} | {hypothesis['decision']} |")
    report += [
        "", "Only three narrow candidates were built: A swapped the exact Rank‑3-opening branch, B swapped the exact K3-opening branch, and C combined them. No economic parameter, route body, late phase, submission file, or source baseline was altered.", "",
        "| Candidate | Paired own W/L/T | Mean delta | P10 | Natural mean | Safety |", "|---|---:|---:|---:|---:|---|",
    ]
    for name in ("A_rank3_swap", "B_k3_swap", "C_combined"):
        pair = ablation["paired_vs_current_best"][name]
        natural = split_ablation(ablation, name)["natural"]
        safety = ablation["summary"][name]["actual_livestock_escapes"]
        report.append(f"| {name} | {pair['own_wins']}/{pair['own_losses']}/{pair['own_ties']} | {pair['own_money_delta_mean']:.0f} | {pair['own_money_delta_p10']:.0f} | {natural['mean']:.0f} | {safety} escapes |")
    report += [
        "", "A and B looked plausible only because of one initial split. Fresh development seeds exposed state aliasing and missing adaptive branches. Their bank deficits become durable by day 4; the candidate crop/livestock schedules then fail to realize the coordinated Rank‑1 economy. C combines both failures non-additively and is worst.", "",
        "## 8. Selection, safety, and promotion", "",
        "No candidate reached validation. This is a deliberate sequential gate, not missing work: validation/selection/final seeds remain untouched after every candidate produced zero positive changed-condition paired results, catastrophic tails, and animal escapes. CurrentBest had zero runtime failures, zero semantic failures, zero escapes, and zero meaningful stranding in the development panel.", "",
        "**Promotion decision: no promotion.** The strongest tuned candidate is therefore the unchanged CurrentBest. There is no tuned H2H versus Top‑3 to report beyond the rejected development ablations. Nothing was packaged or submitted.", "",
        "## 9. Answers to the 30 final questions", "",
        "1. Current Top1/2/3: tetsuya / Crop Dusta / OceanMix.",
        "2. Episodes: 30 current-version appearances each.",
        "3. Adaptive: phase-adaptive / strongly adaptive / phase-adaptive.",
        "4–6. Complete economies: summarized above; exact daily/cohort ledgers are in the three dossiers.",
        "7. Shared core: three quadrants, 12 hands, mixed cows/sheep, diversified wheat/melon/strawberry, recurrent services, staggered sales, terminal liquidation, ongoing adaptation.",
        "8. Rank1 distinction: sheep/wool/fertilizer weighting, earlier labor, broader diversification, later first land than Rank2.",
        "9. Versus CurrentBest: Top3 continue branching; CurrentBest selects one complete parent at step 1.",
        "10. Fixed medoid durable divergence on matched K3: days 19.5 / 14 / 15; failed micro branches diverge by day 4.",
        "11. Correlated: animal mix, early land, lower labor, sale overlap and public final money.",
        "12. Causally positive: none generalized; initial split positives reversed.",
        "13. Generalized behaviors: none entered a candidate.",
        "14. Strongest initial local Top3 medoid: Rank1 overall; direct CurrentBest matchup was 4–4 and unsafe.",
        "15. CurrentBest weakness: premature one-shot selection and no later state branching; no safe micro fix identified.",
        "16. Tested dimensions: only two exact parent-selection branches and their interaction.",
        "17. Surviving modifications: none.",
        "18. Strongest tuned candidate: unchanged CurrentBest.",
        "19. Paired own-money delta vs CurrentBest: 0 for retained baseline; A/B/C were −19,609 / −14,180 / −33,789.",
        "20. H2H vs CurrentBest: no new finalist; A lost 0–8 when its aliased branch activated, B tied because that signature did not activate in mirror, C lost 0–8.",
        "21–23. H2H vs Rank1/2/3: unchanged CurrentBest development results were 4–4, 8–0, and 2–6 respectively on eight games each.",
        "24. Natural RNG: A/B/C paired own deltas −21,668 / −15,978 / −37,646; all rejected.",
        f"25–26. P10/P5: retained CurrentBest development advantage P10 {ablation['summary']['CurrentBest']['p10_advantage']:.0f}, P5 {ablation['summary']['CurrentBest']['p5_advantage']:.0f}; no finalist advanced.",
        "27. Safety: retained CurrentBest had zero runtime, semantic, escape, and meaningful-stranding failures; all candidates had escapes.",
        "28. Attribution: failed swaps lost primarily crop revenue (−46.7k to −76.9k) plus livestock revenue in the hardest aliases; full decomposition is machine-readable.",
        "29. New research best: no.",
        "30. Remaining unexplained about Top1: the exact current-observation policy that chooses livestock/crop/service/sale branches after expansion. Public medoids prove the economic family but not the hidden decision function.", "",
        "## 10. Artifacts", "",
        "The version audit, adaptive divergence map, direct comparison, shared core, Rank‑1 unique analysis, causal table, raw league, ablations, counterfactual decomposition, stop-rule validation artifacts, and finalist lock are all under `experiments/`. The corpus remains Top‑3-only for hypothesis generation.", "",
    ]
    (EXP / "top3_forensic_research_report.md").write_text("\n".join(report))

    log_path = EXP / "log.md"
    log = log_path.read_text()
    marker = "## 2026-09-01 — Current Top-3 forensic research"
    entry = f"""

{marker}

- Baseline: `{baseline_path}` (`{file_sha(baseline_path)}`); Super Replay V2 retained as control.
- Live snapshot: tetsuya / Crop Dusta / OceanMix at {version['leaderboard_captured_at']}; 30 exact-current-version appearances each.
- Finding: all three stabilize the opening then branch materially; a public medoid is not the hidden adaptive policy.
- Raw league: Rank1 medoid led the broad initial panel but split 4–4 with CurrentBest, showed tail risk, and lost livestock.
- Microtuning: exact Rank3 branch swap, exact K3 branch swap, and combination all failed development (paired mean deltas −19,609 / −14,180 / −33,789; all had escapes).
- Decision: no validation consumption, no finalist, no promotion. CurrentBest remains unchanged. `submission/main.py` untouched at `{file_sha('submission/main.py')}`. Nothing submitted.
- Report: `experiments/top3_forensic_research_report.md`.
"""
    if marker not in log:
        log_path.write_text(log.rstrip() + entry + "\n")
    print(EXP / "top3_forensic_research_report.md")
    print("promotion=false retained", baseline_path, file_sha(baseline_path))


if __name__ == "__main__":
    main()
