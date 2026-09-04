# Current Top-3 forensic research and evidence-based micro-tuning

## Executive result

The current live Top 3 at `2026-09-01T07:39:57.571562+00:00` were **tetsuya**, **Crop Dusta**, and **OceanMix**. I analyzed 30 exact-current-submission appearances per team (90 total, 87 unique replay files). The central frontier pattern is continued observable-state adaptation after a stable opening, not a single superior fixed route.

No micro-tuned candidate survived the development gate. The research best remains `agents/top50_distilled/top50_observable_portfolio.py` at SHA-256 `f9ca672848ccffdfe56888d99bcdf5a9d7644062b9eec0cf0cdea13574931233`. `submission/main.py` was not modified; its SHA-256 remains `789bb9bbd5122eb4891983e776a13777328e3e87736cbbc0b4bc86d13fc33f9b`.

## 1. Snapshot, version purity, and baseline

| Rank | Team | Submission | Public score | Available public episodes | Analyzed |
|---:|---|---:|---:|---:|---:|
| 1 | tetsuya | 55905066 | 2939.7 | 86 | 30 |
| 2 | Crop Dusta | 55929317 | 2870.8 | 64 | 30 |
| 3 | OceanMix | 55926618 | 2862.3 | 67 | 30 |

All appearances were attributed by exact public submission ID. Alternate active versions were excluded. Seventeen single-agent trajectories were exact action duplicates, but they were retained for economic analysis because market/opponent paths differed; no full replay was duplicated.

Current baseline: `agents/top50_distilled/top50_observable_portfolio.py` (`f9ca672848ccffdfe56888d99bcdf5a9d7644062b9eec0cf0cdea13574931233`), a step-1 observable selector over complete Dmitry/Hanserong/redblack replay parents. Reference control: `agents/super_replay_v2/super_backbone_v2.py` (`c39d82b4f796271603e32ea8cb4b70261fbbe3d4e17940886caf5f5a6bd9adef`).

## 2. Fixed versus adaptive

| Rank | Classification | Distinct full routes | First action divergence | Opening farmer/crop/market agreement | Late field/market agreement |
|---:|---|---:|---:|---|---|
| 1 | PHASE_ADAPTIVE | 30/30 | 31 | 96.9% / 96.1% / 98.7% | 19.9% / 68.1% |
| 2 | STRONGLY_ADAPTIVE | 30/30 | 15 | 98.6% / 95.3% / 97.1% | 20.6% / 41.1% |
| 3 | PHASE_ADAPTIVE | 13/30 | 25 | 99.7% / 99.0% / 92.4% | 41.4% / 58.4% |

Rank 1 is phase-adaptive, Rank 2 strongly adaptive, and Rank 3 phase-adaptive with 17 exact route duplicates. Their openings are highly stable, but after reinvestment the field routes diverge sharply. The largest branches separate on current bank, prices, inventory, opponent animal/crop composition, and shop state. No simple rule reached causal status: episode ID, seed, future shops/prices, and final outcome were never used.

## 3. Complete economic strategies

| Rank | Land steps | Peak hands | Median cows/sheep/geese | Median peak wheat/melon/strawberry | Productive | Mean public money | Mean realized revenue |
|---:|---|---:|---|---|---:|---:|---:|
| 1 | 168, 240 | 12.0 | 6.0/6.0/1.0 | 51.0/12.0/35.5 | 73.0 | 105386 | 147906 |
| 2 | 121, 199 | 12.0 | 7.0/6.0/1.5 | 38.0/7.0/24.5 | 75.0 | 95081 | 188461 |
| 3 | 150, 265 | 12.0 | 7.0/6.0/0.0 | 40.0/12.0/38.0 | 75.0 | 92114 | 118145 |

### Rank 1 — tetsuya

Rank 1 opens with mixed livestock but is uniquely sheep/wool/fertilizer heavy. It hires earlier, buys land exactly at steps 168 and 240 (days 7 and 10), carries median peaks of 6.0 cows and 6.0 sheep, then runs wheat, melon and strawberry cohorts over about 73 productive tiles. Mean wool, fertilizer, milk, strawberry and melon revenue are 30694, 27851, 23513, 28870, and 12567. The capital model is diversification: wool/fertilizer cash supports land and labor while crop cohorts prevent dependence on milk alone.

### Rank 2 — Crop Dusta

Rank 2 buys land earliest (steps 121 and 199), ramps mixed livestock, and spends heavily on market wheat/feed (71646 mean). It reaches 75 productive tiles and is the most state-dependent strategy. Its unusually high wheat realization is paired with high spending; the complete public medoid did not transfer safely.

### Rank 3 — OceanMix

Rank 3 follows the most repeatable public skeleton: land at steps 150 and 265, exactly 12 peak hands, median 7 cows and 6 sheep, a 12-melon wave, then roughly 38 strawberries plus 40 wheat. It has the lowest mean labor spend (5398) and short premium holding, but greater synchronized-sale overlap and stronger immediate price impact.

The complete day-by-day cash, assets, cohort windows, worker actions, animal service, realized prices, hold times, and endgame cutoffs are in the three dedicated dossiers:

- `experiments/top3_rank1_strategy_dossier.md`
- `experiments/top3_rank2_strategy_dossier.md`
- `experiments/top3_rank3_strategy_dossier.md`

## 4. Shared core, Rank-1 uniqueness, and market externality

All three use three quadrants, a 12-hand ceiling, mixed cows and sheep, wheat→melon→strawberry-capable crop succession, recurring animal service, staggered within-season realization, and terminal liquidation. Most of that vocabulary already exists in CurrentBest. The important missing behavior is continued state-conditioned branching after expansion; CurrentBest commits at step 1.

Rank 1 uniquely emphasizes wool/fertilizer: mean wool revenue 30694 and fertilizer revenue 27851, while retaining broader crop diversification and earlier labor. This is OBSERVED, not proven causal.

Premium sales are not held for many days: median weighted holds are generally below one day. Immediate observed price changes after own sale steps are largest for melon, strawberry and wool. Rank 3 has especially high same-turn sale overlap (melon about 86%, strawberry about 50%), consistent with aggressive joint-market pressure, but town consumption and simultaneous opponent orders prevent assigning the full price delta to its own action.

## 5. Direct controlled league

| Agent | W/L/T | Avg money | Avg advantage | P10 | P5 | Route fidelity | Actual escapes |
|---|---:|---:|---:|---:|---:|---:|---:|
| Rank1_public_medoid | 50/6/0 | 105865 | 34627 | 1533 | -27877 | 99.846% | 16 |
| CurrentBest | 48/8/0 | 92319 | 22463 | -4826 | -14790 | 99.967% | 0 |
| Rank3_public_medoid | 44/12/0 | 87389 | 13563 | -13949 | -75429 | 99.794% | 0 |
| V2 | 28/28/0 | 86015 | 11080 | -18066 | -25464 | 99.936% | 0 |
| Rank2_public_medoid | 24/32/0 | 75573 | -7132 | -41540 | -47291 | 99.975% | 212 |

The Rank-1 medoid was strongest over the broad initial panel, but it split 4–4 directly with CurrentBest and had mean direct advantage -5537. Its positive initial common-hard paired own-money result (20083) reversed on fresh K3 attribution seeds (-14995). Rank 2's fixed medoid was especially unsafe because the real Rank-2 policy is strongly adaptive; this does not imply the leaderboard agent itself is weak.

## 6. Advantage traced backward and difference-of-differences

Matched K3 decompositions show the fixed medoids first acquire a durable bank difference from CurrentBest around day 19.5 (Rank 1), day 14 (Rank 2), and day 15 (Rank 3). On the fresh attribution split all three fixed medoids ended below CurrentBest in own money: Rank 1 −14,995, Rank 2 −23,954, Rank 3 −10,304. Rank 3 nevertheless improved net advantage by +8,139 because it also reduced opponent realization—evidence of a shared-market externality, not higher own income.

Public replay difference-of-differences is intentionally not called causal: opponent and shop paths are uncontrolled. The consistent association is that Top‑3 economies reach 72–75 productive tiles, mix animals, and branch after expansion; the causal transplant of one fixed medoid failed.

## 7. Causal hypotheses and micro-tuning

| Hypothesis | Evidence status | Decision |
|---|---|---|
| H1_rank1_sheep_fertilizer_compounding | REPLICATED_IN_ONE_SPLIT_NOT_GENERALIZED | REJECT |
| H2_rank3_opening_parent_swap | CAUSALLY_NEGATIVE | REJECT |
| H3_k3_opening_parent_swap | CAUSALLY_NEGATIVE | REJECT |
| H4_continuing_observable_adaptation | OBSERVED_SHARED_NOT_YET_CAUSAL | DEFER |
| H5_rank2_early_land_wheat_throughput | CORRELATED_NOT_GENERALIZED | REJECT |
| H6_premium_staggering_and_externality | OBSERVED_CORRELATION | DEFER |
| H7_rank3_lower_labor_cost | REPLICATED_IN_ONE_SPLIT_NOT_GENERALIZED | REJECT |

Only three narrow candidates were built: A swapped the exact Rank‑3-opening branch, B swapped the exact K3-opening branch, and C combined them. No economic parameter, route body, late phase, submission file, or source baseline was altered.

| Candidate | Paired own W/L/T | Mean delta | P10 | Natural mean | Safety |
|---|---:|---:|---:|---:|---|
| A_rank3_swap | 0/16/32 | -19609 | -73493 | -21668 | 22 escapes |
| B_k3_swap | 0/8/40 | -14180 | -79297 | -15978 | 26 escapes |
| C_combined | 0/24/24 | -33789 | -85186 | -37646 | 48 escapes |

A and B looked plausible only because of one initial split. Fresh development seeds exposed state aliasing and missing adaptive branches. Their bank deficits become durable by day 4; the candidate crop/livestock schedules then fail to realize the coordinated Rank‑1 economy. C combines both failures non-additively and is worst.

## 8. Selection, safety, and promotion

No candidate reached validation. This is a deliberate sequential gate, not missing work: validation/selection/final seeds remain untouched after every candidate produced zero positive changed-condition paired results, catastrophic tails, and animal escapes. CurrentBest had zero runtime failures, zero semantic failures, zero escapes, and zero meaningful stranding in the development panel.

**Promotion decision: no promotion.** The strongest tuned candidate is therefore the unchanged CurrentBest. There is no tuned H2H versus Top‑3 to report beyond the rejected development ablations. Nothing was packaged or submitted.

## 9. Answers to the 30 final questions

1. Current Top1/2/3: tetsuya / Crop Dusta / OceanMix.
2. Episodes: 30 current-version appearances each.
3. Adaptive: phase-adaptive / strongly adaptive / phase-adaptive.
4–6. Complete economies: summarized above; exact daily/cohort ledgers are in the three dossiers.
7. Shared core: three quadrants, 12 hands, mixed cows/sheep, diversified wheat/melon/strawberry, recurrent services, staggered sales, terminal liquidation, ongoing adaptation.
8. Rank1 distinction: sheep/wool/fertilizer weighting, earlier labor, broader diversification, later first land than Rank2.
9. Versus CurrentBest: Top3 continue branching; CurrentBest selects one complete parent at step 1.
10. Fixed medoid durable divergence on matched K3: days 19.5 / 14 / 15; failed micro branches diverge by day 4.
11. Correlated: animal mix, early land, lower labor, sale overlap and public final money.
12. Causally positive: none generalized; initial split positives reversed.
13. Generalized behaviors: none entered a candidate.
14. Strongest initial local Top3 medoid: Rank1 overall; direct CurrentBest matchup was 4–4 and unsafe.
15. CurrentBest weakness: premature one-shot selection and no later state branching; no safe micro fix identified.
16. Tested dimensions: only two exact parent-selection branches and their interaction.
17. Surviving modifications: none.
18. Strongest tuned candidate: unchanged CurrentBest.
19. Paired own-money delta vs CurrentBest: 0 for retained baseline; A/B/C were −19,609 / −14,180 / −33,789.
20. H2H vs CurrentBest: no new finalist; A lost 0–8 when its aliased branch activated, B tied because that signature did not activate in mirror, C lost 0–8.
21–23. H2H vs Rank1/2/3: unchanged CurrentBest development results were 4–4, 8–0, and 2–6 respectively on eight games each.
24. Natural RNG: A/B/C paired own deltas −21,668 / −15,978 / −37,646; all rejected.
25–26. P10/P5: retained CurrentBest development advantage P10 -6506, P5 -8081; no finalist advanced.
27. Safety: retained CurrentBest had zero runtime, semantic, escape, and meaningful-stranding failures; all candidates had escapes.
28. Attribution: failed swaps lost primarily crop revenue (−46.7k to −76.9k) plus livestock revenue in the hardest aliases; full decomposition is machine-readable.
29. New research best: no.
30. Remaining unexplained about Top1: the exact current-observation policy that chooses livestock/crop/service/sale branches after expansion. Public medoids prove the economic family but not the hidden decision function.

## 10. Artifacts

The version audit, adaptive divergence map, direct comparison, shared core, Rank‑1 unique analysis, causal table, raw league, ablations, counterfactual decomposition, stop-rule validation artifacts, and finalist lock are all under `experiments/`. The corpus remains Top‑3-only for hypothesis generation.
