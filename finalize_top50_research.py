"""Assemble required Top-50 research artifacts and the final report."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
EXP = ROOT / "experiments"
BASE = "agents/super_replay_v2/super_backbone_v2.py"
FINAL = "agents/top50_distilled/top50_observable_portfolio.py"


def load(name):
    return json.loads((EXP / name).read_text())


def write(name, value):
    (EXP / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def money(value):
    return f"{value:,.0f}"


def main():
    corpus = load("top50_corpus_manifest.json")
    dedup = load("top50_deduplication.json")
    families = load("top50_strategy_families.json")
    consensus = load("top50_consensus_patterns.json")
    adaptive = load("top50_adaptive_behavior_analysis.json")
    raw = load("top50_raw_parent_league.json")
    cheap_broad = load("top50_candidate_cheap.json")
    cheap = load("top50_candidate_cheap_guard2.json")
    serious_static = load("top50_candidate_serious_guard2.json")
    serious = load("top50_candidate_serious_guard3.json")
    final = load("top50_final_validation.json")
    attribution = load("top50_economic_attribution.json")
    finalist_summary = final["summary"][FINAL]
    baseline_summary = final["summary"][BASE]
    finalist_paired = final["paired_vs_v2"][FINAL]

    raw_best_path = "agents/top50_distilled/raw/super_raw_55859516.py"
    static_paths = {
        "dmitry_safe": "agents/top50_distilled/top50_dmitry_safe.py",
        "hanserong_safe": "agents/top50_distilled/top50_hanserong_safe.py",
        "redblack_safe": "agents/top50_distilled/top50_redblack_safe.py",
    }
    serious_rows = {}
    for name, path in static_paths.items():
        serious_rows[name] = {
            **serious_static["summary"][path],
            **serious_static["paired_vs_v2"][path],
        }
    serious_rows["observable_portfolio"] = {
        **serious["summary"][FINAL], **serious["paired_vs_v2"][FINAL],
    }

    counterfactual = {
        "schema_version": 1,
        "design": "same seed, opponent, seat, and shop regime; candidate versus frozen V2 own-money comparison",
        "results": [
            {
                "hypothesis": "complete Dmitry 8-cow/4-sheep economy",
                "development_pairs": raw["paired_vs_v2"][raw_best_path]["pairs"],
                "development_delta": raw["paired_vs_v2"][raw_best_path]["paired_own_money_delta_mean"],
                "serious_delta_with_narrow_safety": serious_rows["dmitry_safe"]["paired_own_money_delta_mean"],
                "causal_status": "supported",
            },
            {
                "hypothesis": "complete Hanserong 7-cow/6-sheep economy",
                "serious_delta_with_narrow_safety": serious_rows["hanserong_safe"]["paired_own_money_delta_mean"],
                "causal_status": "supported but weaker and less competitive across elite traces",
            },
            {
                "hypothesis": "complete redblack 9-cow/5-sheep economy",
                "serious_delta_with_narrow_safety": serious_rows["redblack_safe"]["paired_own_money_delta_mean"],
                "causal_status": "supported, complementary under dominant-family opening",
            },
            {
                "hypothesis": "observable step-1 selection among coherent complete economies",
                "state_compatibility": "all parents take identical step-0 PASS; selection precedes first divergent action",
                "serious_delta": serious_rows["observable_portfolio"]["paired_own_money_delta_mean"],
                "final_unseen_delta": finalist_paired["paired_own_money_delta_mean"],
                "final_net_advantage_delta": finalist_paired["net_advantage_delta_mean"],
                "causal_status": "supported and locked before final unseen",
            },
            {
                "hypothesis": "broad at-risk feed override",
                "development_delta": cheap_broad["paired_vs_v2"]["agents/top50_distilled/top50_dmitry_safe.py"]["paired_own_money_delta_mean"],
                "causal_status": "rejected; stationary overrides desynchronize fixed route execution",
            },
        ],
        "non_transplanted_consensus": "Land/labor/crop/livestock schedules are coordinated from step 1. Later blind phase splices were rejected as state-incompatible rather than misrepresented as causal tests.",
    }
    write("top50_counterfactual_results.json", counterfactual)

    ablations = {
        "schema_version": 1,
        "serious_static_parent_ablations": serious_rows,
        "safety_ablation": {
            "broad_guard_dmitry_delta": cheap_broad["paired_vs_v2"]["agents/top50_distilled/top50_dmitry_safe.py"]["paired_own_money_delta_mean"],
            "deadline_exact_guard_dmitry_delta": cheap["paired_vs_v2"]["agents/top50_distilled/top50_dmitry_safe.py"]["paired_own_money_delta_mean"],
            "conclusion": "Only deadline/exact audited feed repair preserves route economics.",
        },
        "selector_ablation": {
            "static_dmitry_serious_delta": serious_rows["dmitry_safe"]["paired_own_money_delta_mean"],
            "full_selector_serious_delta": serious_rows["observable_portfolio"]["paired_own_money_delta_mean"],
            "selection_increment": serious_rows["observable_portfolio"]["paired_own_money_delta_mean"] - serious_rows["dmitry_safe"]["paired_own_money_delta_mean"],
            "guard2_p10": serious_static["paired_vs_v2"][FINAL]["paired_own_money_delta_p10"],
            "guard3_p10": serious["paired_vs_v2"][FINAL]["paired_own_money_delta_p10"],
            "conclusion": "Observable family selection adds mean value; separating V2's 2-coin opening from rank-1's 4-coin opening improves tail.",
        },
        "portfolio_oracle": {
            "development_oracle_delta": 8536.222222222223,
            "parents": ["dmitry", "hanserong", "redblack"],
            "selector_justified": True,
        },
    }
    write("top50_ablation_results.json", ablations)

    candidate_results = {
        "schema_version": 1,
        "serious_gate": serious_rows,
        "locked_final": {
            "candidate": FINAL,
            "summary": finalist_summary,
            "paired_vs_v2": finalist_paired,
            "baseline_summary": baseline_summary,
            "parent_usage": dict(Counter(row.get("portfolio_parent") for row in final["games"] if row["candidate"] == FINAL)),
        },
        "promotion_gate": {
            "paired_own_money_at_least_3000": finalist_paired["paired_own_money_delta_mean"] >= 3000,
            "paired_own_money_at_least_5000": finalist_paired["paired_own_money_delta_mean"] >= 5000,
            "direct_v2_decisive_win_rate": 62 / 64,
            "natural_v2_w_l": [32, 0],
            "competitive_p10_improved": finalist_summary["p10"] > baseline_summary["p10"],
            "paired_own_money_p10_positive": finalist_paired["paired_own_money_delta_p10"] > 0,
            "safety_clean": finalist_summary["actual_livestock_escapes"] == 0 and finalist_summary["meaningful_stranding_games"] == 0 and finalist_summary["runtime_failures"] == 0 and finalist_summary["semantic_failures"] == 0,
        },
    }
    write("top50_candidate_results.json", candidate_results)

    selection = {
        "schema_version": 1,
        "selected": FINAL,
        "decision": "promote as local research best",
        "reason": "Final +5,979 paired own money, +8,040 net-advantage delta, 62/2 direct V2, 32/0 natural direct V2, materially improved competitive P10, and clean safety.",
        "caveats": [
            "paired own-money P10 is -8,029 and P5 is -10,620",
            "unseen Top-50 family result is 21/23; one family produces much of the positive elite mean",
            "the architecture improves V2 strongly but does not yet beat a majority of current Top-50 family episodes",
        ],
        "submission_decision": "local research promotion only; submission/main.py remains unchanged and no Kaggle action is authorized",
    }
    write("top50_selection_results.json", selection)

    # Fill the observational distillation table with causal outcomes.
    distillation = load("top50_strategy_distillation.json")
    causal = {
        "three_or_more_quadrants": "already present in V2; no isolated value claimed",
        "first_land_by_day7": "coherent complete parents supported; not independently transplantable",
        "second_land_by_day11_5": "coherent complete parents supported; not independently transplantable",
        "eight_or_more_cows": "not universal; static parent comparison favors condition-dependent 7/8/9-cow economies",
        "mixed_cow_sheep": "supported across all three positive complete parents",
        "twelve_or_more_hands": "supported consensus; lower than V2's 14-hand peak and contributes lower labor cost",
        "melon_and_strawberry_waves": "supported as part of all positive coherent parents",
        "terminal_liquidation_after_step700": "supported; zero meaningful final stranding in locked final",
    }
    for row in distillation["behaviors"]:
        row["estimated_causal_value"] = causal.get(row["behavior"], row["estimated_causal_value"])
        row["compatibility_with_current_best"] = "coherent-parent replacement or pre-divergence selection only"
    distillation["status"] = "causal results incorporated after locked final"
    distillation["strongest_distilled_behavior"] = "observable pre-divergence selection among coherent mixed-livestock economies"
    write("top50_strategy_distillation.json", distillation)

    # Compact report.
    top_adaptive = sorted(
        [row for row in adaptive["submissions"] if row["classification"] == "D_state_dependent"],
        key=lambda row: row["rank"],
    )[:6]
    attr = attribution["delta_finalist_minus_v2"]
    lines = [
        "# Current Top-50 Strategy Mining and Distillation",
        "",
        "## Decision",
        "",
        "**Promote `agents/top50_distilled/top50_observable_portfolio.py` as the local research best.** "
        "This is not a Kaggle package or submission. `submission/main.py` is unchanged.",
        "",
        "## 1. Actual baseline and preservation",
        "",
        "| Item | Path | SHA-256 (raw = LF) |",
        "|---|---|---|",
        "| Frozen baseline | `agents/super_replay_v2/super_backbone_v2.py` | `c39d82b4f796271603e32ea8cb4b70261fbbe3d4e17940886caf5f5a6bd9adef` |",
        "| Historical submission | `submission/main.py` | `a4f753d46a95e8d972098504f4930165e7e66f8ce292092e9ab090e4741310c3` |",
        "| New research best | `agents/top50_distilled/top50_observable_portfolio.py` | `f9ca672848ccffdfe56888d99bcdf5a9d7644062b9eec0cf0cdea13574931233` |",
        "",
        "No completed V5-V8 lineage existed. V3 and V4 were documented rejections, so V2 was the actual baseline.",
        "",
        "## 2. Corpus freshness and coverage",
        "",
        f"Captured `{corpus['captured_at']}` from the current leaderboard: **50 teams**, **249 valid unique full episodes**, "
        f"**408 elite appearances**, and **340 appearances after exact action deduplication**. "
        "A post-lock holdout added 22 unused episodes, two from every refined family.",
        "",
        "| Deduplication level | Unique count |",
        "|---|---:|",
        f"| Exact 719-action implementation | {dedup['exact_action_implementations']} |",
        f"| Field + non-SELL route implementation | {dedup['route_implementations']} |",
        f"| Economic implementation | {dedup['economic_implementations']} |",
        f"| Economic family | {dedup['strategy_families']} |",
        "",
        f"Fixed/bounded: **{adaptive['classification_counts'].get('A_highly_fixed',0) + adaptive['classification_counts'].get('B_fixed_bounded',0)}**; "
        f"phase-fixed: **{adaptive['classification_counts'].get('C_phase_fixed_local',0)}**; strongly state-dependent: **{adaptive['classification_counts'].get('D_state_dependent',0)}**.",
        "",
        "The newest server replays had 266 small local/server price-rounding divergences. Observed bank changes were treated as authoritative and the residual was explicitly recorded; it was never hidden.",
        "",
        "## 3. Strategy families",
        "",
        "| Family | Identity | Teams | Rank span | Land steps | Peak animals (C/S/G) | Hands | Avg replay money |",
        "|---|---|---:|---|---|---|---:|---:|",
    ]
    for row in families["families"]:
        animals = row["typical_peak_animals"]
        lines.append(
            f"| {row['family_id']} | {row['economic_identity']} | {row['size']} | {min(row['ranks'])}-{max(row['ranks'])} | "
            f"{row['typical_first_land_step']:.0f}/{row['typical_second_land_step']:.0f} | "
            f"{animals['COW']:.0f}/{animals['SHEEP']:.0f}/{animals['GOOSE']:.0f} | {row['typical_peak_hands']:.0f} | {money(row['average_money'])} |"
        )
    lines.extend([
        "",
        "A broad copied cow/wheat family contains 38 teams, but rank 1, rank 2, rank 5, rank 18, rank 26, and several livestock-scale variants remain economically distinct.",
        "",
        "## 4. Consensus and rank contrast",
        "",
        "Equal-weighting each family rather than each team gives:",
        "",
    ])
    for pattern in sorted(consensus["patterns"], key=lambda row: row["frequency"], reverse=True):
        lines.append(f"- **{pattern['pattern']}**: {pattern['families_using']}/{pattern['family_count']} families ({pattern['frequency']:.0%}).")
    lines.extend([
        "",
        "Top 1-10 differs mainly through diversity and livestock balance, not universal earlier land: median land timing is still step 150/265. The Top-10 median peak is 6.5 cows versus 9 lower down, suggesting that more cows are not monotonically stronger.",
        "",
        "## 5. Adaptive behavior",
        "",
        "The strongest observable divergences involve current wool/milk/strawberry prices, current productive tiles, current hands, and bank. These are hypotheses, not proof. Representative state-dependent teams:",
        "",
        "| Rank | Team | First divergence | Opening agreement | Midgame agreement |",
        "|---:|---|---:|---:|---:|",
    ])
    for row in top_adaptive:
        lines.append(f"| {row['rank']} | {row['team_name']} | {row['first_action_divergence_step']} | {row['phase_action_agreement']['opening']:.1%} | {row['phase_action_agreement']['midgame']:.1%} |")
    lines.extend([
        "",
        "No deployable branch uses seed, replay ID, rank, future prices/shops/actions, or final result.",
        "",
        "## 6. Raw parents and causal tests",
        "",
        "| Candidate | Serious paired W/L/T | Paired own-money delta | P10 | Safety note |",
        "|---|---:|---:|---:|---|",
    ])
    for name in ("dmitry_safe", "hanserong_safe", "redblack_safe", "observable_portfolio"):
        row = serious_rows[name]
        lines.append(f"| {name} | {row['paired_wins']}/{row['paired_losses']}/{row['paired_ties']} | {money(row['paired_own_money_delta_mean'])} | {money(row['paired_own_money_delta_p10'])} | {'locked clean final' if name == 'observable_portfolio' else 'research parent'} |")
    lines.extend([
        "",
        "The raw Dmitry route first showed +5,323. Its recurring day-28 cow escape was traced to a worker standing on the cow with wheat but collecting fertilizer at step 686. Broad rescue was catastrophic; the exact repair preserved economics. The development D/H/R portfolio oracle was +8,536, enough to justify selection.",
        "",
        "## 7. New architecture",
        "",
        "Four candidate agents were built: three complete, economically distinct elite parents with only exact safety repair (Dmitry 8-cow/4-sheep, Hanserong 7-cow/6-sheep, and redblack 9-cow/5-sheep), plus the observable portfolio selector. A V2 phase-transplant candidate was rejected before implementation because checkpoint crop/livestock state was not compatible with any winning parent; previous V3/V4 evidence already showed that such splices erase the route's coordinated capital plan.",
        "",
        "All parents PASS at step 0. At step 1, before their first economic divergence, the candidate selects one coherent complete economy from the opponent's visible bank and hand count:",
        "",
        "- dominant-family idle opening -> redblack 9-cow/5-sheep economy",
        "- rank-1/rank-5-like opening -> Hanserong 7-cow/6-sheep economy",
        "- otherwise -> Dmitry 8-cow/4-sheep economy",
        "",
        "This is selection among complete coordinated plans, not route splicing.",
        "",
        "## 8. Locked final unseen",
        "",
        "| Metric | V2 | New candidate |",
        "|---|---:|---:|",
        f"| Games | {baseline_summary['games']} | {finalist_summary['games']} |",
        f"| W/L/T | {baseline_summary['wins']}/{baseline_summary['losses']}/{baseline_summary['ties']} | {finalist_summary['wins']}/{finalist_summary['losses']}/{finalist_summary['ties']} |",
        f"| Average money | {money(baseline_summary['average_money'])} | {money(finalist_summary['average_money'])} |",
        f"| Average advantage | {money(baseline_summary['average_advantage'])} | {money(finalist_summary['average_advantage'])} |",
        f"| Advantage P25 | {money(baseline_summary['p25'])} | {money(finalist_summary['p25'])} |",
        f"| Advantage P10 | {money(baseline_summary['p10'])} | {money(finalist_summary['p10'])} |",
        f"| Advantage P5 | {money(baseline_summary['p5'])} | {money(finalist_summary['p5'])} |",
        f"| Worst advantage | {money(baseline_summary['worst'])} | {money(finalist_summary['worst'])} |",
        f"| Actual animal escapes | {baseline_summary['actual_livestock_escapes']} | {finalist_summary['actual_livestock_escapes']} |",
        "",
        f"Paired own-money delta: **+{money(finalist_paired['paired_own_money_delta_mean'])}**; median **+{money(finalist_paired['paired_own_money_delta_median'])}**; "
        f"P10 **{money(finalist_paired['paired_own_money_delta_p10'])}**; P5 **{money(finalist_paired['paired_own_money_delta_p5'])}**; worst **{money(finalist_paired['paired_own_money_delta_worst'])}**. "
        f"Net-advantage delta: **+{money(finalist_paired['net_advantage_delta_mean'])}**.",
        "",
        "Direct V2: **62/2** (fixed 30/2; natural 32/0 at 100,138 average money and +7,734 advantage). Unseen Top-50 families: **21/23** at +12,592 average advantage, versus V2's 12/32 at -1,020. Legacy/adaptive pool: **24/0** at +51,076; its paired own-money delta versus V2 was -3,094, so this win pool is competitive rather than an own-income gain.",
        "",
        "## 9. Economic attribution",
        "",
        f"On the focused 16-condition attribution panel, own money changed {attr['own_money']:+,.0f}, opponent money {attr['opponent_money']:+,.0f}, and net advantage {attr['net_advantage']:+,.0f}. "
        "The main positive revenue shifts were fertilizer, wheat, strawberry, carrot, and melon; milk/wool revenue fell. The candidate spent less on labor but cycled much more wheat/fertilizer product capital. This identifies the gain primarily as **market + capital value**, with a smaller production-mix contribution—not a simple output increase.",
        "",
        "## 10. Ablation",
        "",
        "- Broad risk feeding: rejected (route desynchronization).",
        "- Exact deadline repair: preserves the +5k parent signal and yields zero actual final escapes.",
        f"- Static Dmitry -> full selector adds {ablations['selector_ablation']['selection_increment']:+,.0f} paired money on the serious gate.",
        "- Removing coherent parent identity through blind phase splicing was not attempted because checkpoint livestock/crop states are incompatible.",
        "",
        "## 11. Remaining weaknesses",
        "",
        "1. Paired own-money P10/P5 remain negative, despite substantially better competitive tails.",
        "2. The candidate wins only 21/44 unseen elite-family games; family 08 contributes most of the elite mean.",
        "3. Step-1 selection can react to opening identity but not future shop RNG; natural own-money tails remain market-sensitive.",
        "4. Several state-dependent Top-50 agents vary later market actions in ways not safely transplantable into fixed route state.",
        "5. The candidate is a local research architecture with project-local route assets, not a packaged standalone submission.",
        "",
        "## 12. Promotion and next step",
        "",
        "The local research promotion gate passes on +5k paired mean, 96.9% direct V2 wins, clean natural direct results, major competitive-tail improvement, and perfect safety. It does **not** pass a positive paired-own P10 criterion, so this should be treated as a stronger research best rather than a low-risk final solution.",
        "",
        "Recommended next step: diagnose the eight losing elite families using the locked candidate's real branch choice and build a later, state-compatible market residual—not another broad route splice. Do not package or submit until that tail work is requested.",
    ])
    (EXP / "top50_strategy_mining_report.md").write_text("\n".join(lines) + "\n")
    print(EXP / "top50_strategy_mining_report.md")


if __name__ == "__main__":
    main()
