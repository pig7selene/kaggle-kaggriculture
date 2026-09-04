# Top-3 Adaptive Policy Distillation

## Executive conclusion

The strategic reconstruction study succeeded, but the gameplay-transfer stage correctly stopped. On complete held-out episodes, the best structured-history model reached **0.973 phase macro-F1**, **0.839 major-decision macro-F1**, and **1.000 transition recall** with 4.1 steps mean timing error. History adds real signal: current-state-only was 0.865/0.735, while turn-only was 0.488/0.614.

This is not yet a deployable adaptive agent. Crop Dusta's held-out decision F1 is below the gate, crop/market/cohort target heads are weak, and the frozen CurrentBest is a selector over complete replay routes—not a target-driven executor. Buying different land, animals or crops would leave it without coherent construction, routing, service and harvesting continuations. Building a hybrid now would therefore repeat the route-splicing error in a less obvious form.

**Decision:** no new agent, no promotion, no submission change. The next architecture must be a safe target-driven executor before counterfactual policy improvement can resume.

## 1. Corpus and version purity

| Teacher | Current submission | Available | Used | Confidence |
|---|---:|---:|---:|---|
| tetsuya | 55905066 | 86 | 86 | exact submission ID / high |
| Crop Dusta | 55929317 | 66 | 66 | exact submission ID / high |
| OceanMix | 55926618 | 68 | 67 | exact submission ID / high |

The refresh captured 220 teacher appearances and retained **219 version-pure appearances** after excluding one identical full-replay duplicate. The 219 appearances refer to 215 unique valid replay files; all replay acquisition was read-only.

## 2. Strategic ontology and observed phases

The event-driven ontology separates seven mutually exclusive economic phases: opening foundation, first-land deployment, melon capitalization, second-land deployment, strawberry ramp, mixed premium production, and terminal liquidation. Livestock ramp, hiring, crop cohorts, land targets and market mode are parallel target/decision axes rather than forced mutually exclusive phases.

| Teacher | Dominant phase sequence | First land | Second land | Phase signatures |
|---|---|---:|---:|---:|
| tetsuya | OPENING_FOUNDATION → FIRST_LAND_DEPLOYMENT → SECOND_LAND_DEPLOYMENT → STRAWBERRY_RAMP → MIXED_PREMIUM_PRODUCTION → TERMINAL_LIQUIDATION | 168 | 240 | 2 |
| Crop Dusta | OPENING_FOUNDATION → FIRST_LAND_DEPLOYMENT → SECOND_LAND_DEPLOYMENT → MELON_CAPITALIZATION → STRAWBERRY_RAMP → MIXED_PREMIUM_PRODUCTION → TERMINAL_LIQUIDATION | 121 | 199 | 1 |
| OceanMix | OPENING_FOUNDATION → FIRST_LAND_DEPLOYMENT → MELON_CAPITALIZATION → STRAWBERRY_RAMP → MIXED_PREMIUM_PRODUCTION → TERMINAL_LIQUIDATION | 150 | 265 | 1 |

These boundaries come primarily from executed land purchases, premium-product realization and planting cessation; only terminal cessation is conservatively clipped to steps 600–696. They are not assigned solely from turn. The limited phase-signature diversity is itself an important result: adaptation is concentrated inside phases—livestock targets, crop cohorts and selling—not in wholesale route changes.

## 3. Genuine adaptive branches

A branch family is counted as genuinely variable only when at least two onset patterns each occur in at least 5% of that teacher's corpus. This avoids calling one-off action jitter a strategy branch.

| Teacher | Variable strategic families | Count | Reconstructable at F1 ≥ .75 |
|---|---|---:|---:|
| tetsuya | RAMP_COW_48, RAMP_SHEEP_48, START_MELON_COHORT_48, START_STRAWBERRY_COHORT_48, SELL_PREMIUM_24 | 5 | 4 (RAMP_COW_48, START_MELON_COHORT_48, START_STRAWBERRY_COHORT_48, SELL_PREMIUM_24) |
| Crop Dusta | RAMP_COW_48, RAMP_SHEEP_48, START_MELON_COHORT_48, START_STRAWBERRY_COHORT_48, SELL_PREMIUM_24 | 5 | 1 (SELL_PREMIUM_24) |
| OceanMix | RAMP_COW_48, RAMP_SHEEP_48, START_STRAWBERRY_COHORT_48, SELL_PREMIUM_24, ENTER_TERMINAL_24 | 5 | 4 (RAMP_COW_48, RAMP_SHEEP_48, START_STRAWBERRY_COHORT_48, SELL_PREMIUM_24) |

The main branch points are livestock ramps in roughly steps 0–234, melon/strawberry cohort starts in steps 0–312, premium-sale waves around steps 132–306, and OceanMix's variable terminal transition around steps 642–654. First-land, daily-hire continuity and several teacher-specific cohort timings are mostly fixed and should not be mislabeled as adaptive.

## 4. What public signals predict decisions

The strongest shared linear signals are correlational diagnostics, not causal rules:

- Land: owned quadrants/productive tiles, recent feed load, fertilizer inventory and melon-price history.
- Cow ramp: wheat price, current cows/pastures, time since cow/land purchase, recent hiring and shop count.
- Sheep ramp: multi-horizon milk/melon price history and recent labor scaling.
- Crop cohorts: existing cohort size, recent same-crop planting, owned land and wheat/melon price history.
- Premium selling: recent melon price range, recent feed/hire history and productive-tile load.
- Terminal: strawberry-count deltas, planting/harvest/sale history and late product prices.

Feature ablations show no single shortcut dominates: removing turn changes H72 phase F1 by only -0.004; removing opponent bank changes it by +0.000. The gain comes from the combined trajectory summary, although feature correlations remain too diffuse to be treated as an economic law.

## 5. Reconstruction results

| Model | Inputs | Phase F1 | Decision F1 | Transition recall | Timing error |
|---|---|---:|---:|---:|---:|
| M0_turn_only | turn_only | 0.488 | 0.614 | 0.509 | 16.9 |
| M1_current_linear | current_state | 0.865 | 0.735 | 0.939 | 6.4 |
| M2_current_stump_ridge | current_state_plus_quantile_stumps | 0.938 | 0.789 | 0.947 | 5.1 |
| M3_history24_linear | history24 | 0.925 | 0.803 | 0.969 | 5.5 |
| M4_history48_linear | history48 | 0.940 | 0.821 | 0.934 | 4.5 |
| M4_history72_linear | history72 | 0.951 | 0.832 | 0.982 | 5.4 |
| M4_history120_linear | history120 | 0.973 | 0.839 | 1.000 | 4.1 |
| M5_small_elm | history72_random_relu96 | 0.885 | 0.772 | 0.925 | 8.0 |

Held-out replay-level smoothed phase accuracy averages 0.969, has median 0.975, and worst 0.923. The worst replay accumulated 58 wrong-phase steps. A small nonlinear ELM regressed versus linear structured history, so GRU/temporal escalation is not justified.

### Per-teacher reconstruction

| Teacher | Active-phase F1 | Decision F1 | Transition recall |
|---|---:|---:|---:|
| tetsuya | 0.974 | 0.868 | 1.000 |
| Crop Dusta | 0.975 | 0.742 | 1.000 |
| OceanMix | 0.963 | 0.898 | 1.000 |

Shared major-decision heads:

| Decision | Precision | Recall | F1 |
|---|---:|---:|---:|
| BUY_LAND_24 | 0.968 | 0.928 | 0.948 |
| HIRE_24 | 1.000 | 0.995 | 0.998 |
| RAMP_COW_48 | 0.815 | 0.834 | 0.825 |
| RAMP_SHEEP_48 | 0.748 | 0.725 | 0.736 |
| START_MELON_COHORT_48 | 0.787 | 0.686 | 0.733 |
| START_STRAWBERRY_COHORT_48 | 0.812 | 0.817 | 0.814 |
| SELL_PREMIUM_24 | 0.974 | 0.976 | 0.975 |
| ENTER_TERMINAL_24 | 0.691 | 0.673 | 0.682 |

Target quality is uneven: land MAE 0.109, hands MAE 0.455, cows MAE 0.667, sheep MAE 0.755; but crop-family macro-F1 is 0.687, market-mode strict macro-F1 0.555, and cohort scale is within two plants only 37.0%.

## 6. History, aliasing, confidence and OOD

History raises phase F1 by +0.086, decision F1 by +0.097, and transition recall by +0.044 over current state. Nearest-neighbor decision F1 rises from 0.785 at current state to 0.833 at 48 turns. Among the closest 10% of current-state pairs, 13.6% still have different decisions; structured history resolves part, not all, of this aliasing.

On held-out teacher states, mean feature-range coverage is 99.9%. On 16 read-only CurrentBest diagnostic games, coverage is 99.7%, but only 63.5% of sampled states pass range + distance + confidence guards. All three teacher heads agree on phase only 63.1% of CurrentBest states and on all decision bits 75.8%. These are eligibility diagnostics, not actual delegation rates.

## 7. Failure analysis

- Crop Dusta is the reconstruction bottleneck: decision macro-F1 0.742; melon-cohort F1 0.328, sheep 0.669, cow 0.715, terminal 0.625.
- Shared terminal F1 is 0.682 and shared melon-cohort F1 0.733; both miss the intended robust-control threshold.
- Market HOLD never appears in this corpus, and staggered selling is too rare to reconstruct; a high overall market accuracy therefore overstates mode coverage.
- The model uses its own past feed/hire/plant/sale behavior to identify trajectory state. That memory is deployable, but a CurrentBest continuation does not automatically become a Top3-compatible continuation.
- Teacher disagreement is substantial for cow, sheep and strawberry decisions; this reflects multiple coherent economies and prevents blind averaging.

## 8. Executor compatibility and causal gate

CurrentBest selects Dmitry/Hanserong/redblack at step 1 and then follows a complete replay action backbone. It can repair weeds, a few transactions and imminent animal misses, but it cannot accept abstract targets. Compatibility is:

| Decision | Executor class |
|---|---|
| BUY_LAND_24 | NEEDS_NEW_EXECUTOR — extra land has no deploy/plant/water route and changes every downstream position anchor |
| ENTER_TERMINAL_24 | NEEDS_NEW_EXECUTOR — stopping planting and draining all field/shed inventory requires coordinated whole-route retiming |
| HIRE_24 | BOUNDED_SUPPRESSION_ONLY — extra hands have no assigned work; fewer hands drop expected route actions |
| RAMP_COW_48 | NEEDS_NEW_EXECUTOR — requires coordinated pasture build, pickup/place, wheat logistics and permanent service routes |
| RAMP_SHEEP_48 | NEEDS_NEW_EXECUTOR — requires coordinated pasture build, pickup/place, feed/care/fertilizer and harvest routes |
| SELL_PREMIUM_24 | PARAMETERIZABLE_WITHIN_EXISTING_SELL_SLOTS_ONLY — quantity/timing can be adjusted only when a coherent route already delivers inventory to shed |
| START_MELON_COHORT_48 | NEEDS_NEW_EXECUTOR — requires seed procurement, tile allocation, planting, watering and harvest continuation |
| START_STRAWBERRY_COHORT_48 | NEEDS_NEW_EXECUTOR — requires recurring-crop territory and permanent harvest/water scheduling |

Therefore same-state strategic counterfactuals, the executable portfolio oracle, fitted-Q and gameplay hybrids were **NOT RUN**. This is not a compute shortcut: there is no coherent alternative continuation to roll out. Adding one land/cow/seed order while retaining the old route would measure executor breakage, while switching to a Top3 replay route would violate the core no-splicing rule.

## 9. Required 40-point status

1. Corpus: 219 teacher appearances (86 tetsuya, 66 Crop Dusta, 67 OceanMix), 215 unique valid replay files.
2. Version confidence: high, exact current submission IDs captured at refresh time.
3. Ontology: seven event phases, seven target axes and eight major decision labels.
4. Teacher phases: table in §2; adaptation is mainly within-phase.
5. Genuine adaptive branch families: tetsuya 5, Crop Dusta 5, OceanMix 5.
6. Important branch points: livestock ramps, crop cohort launches, premium sale waves and OceanMix terminal timing.
7. Predictive public signals: own capacity/history, feed/hire events, commodity price/inventory history, opponent trajectory and shops; details in §4.
8. Current-state reconstruction: phase 0.865, decisions 0.735.
9. History reconstruction: phase 0.973, decisions 0.839.
10. History ablation: +0.086 phase F1 and +0.097 decision F1 over current state.
11. Turn-only baseline: phase 0.488, decisions 0.614.
12. tetsuya: active phase 0.974, decisions 0.868.
13. Crop Dusta: active phase 0.975, decisions 0.742.
14. OceanMix: active phase 0.963, decisions 0.898.
15. Major-decision shared macro-F1: 0.839; individual table in §5.
16. Transition timing: recall 1.000, mean absolute error 4.1 steps.
17. Remaining aliasing: 13.6% of closest current-state pairs disagree on a decision.
18. OOD coverage: teacher holdout 99.9%; CurrentBest guard eligibility 63.5%.
19. Counterfactual value: NOT RUN—no coherent executable target alternative.
20. High-level portfolio oracle: NOT RUN—only KEEP_CURRENTBEST is executable.
21. Fitted-Q: not justified; no action-return dataset or measured oracle headroom.
22. Hybrid architectures: H1/H2/H3 specified as designs, none built.
23. Strongest hybrid: none.
24. Delegation rate: not measured; no controller. Guard eligibility is 63.5%, not delegation.
25. CurrentBest fallback rate: not measured; would be 100% because no safe delegation was enabled.
26. Paired own-money delta: NOT RUN.
27. Advantage delta: NOT RUN.
28. H2H vs CurrentBest: NOT RUN.
29. H2H vs Rank1: NOT RUN.
30. H2H vs Rank2: NOT RUN.
31. H2H vs Rank3: NOT RUN.
32. Natural RNG: 16 diagnostic observation-only games; no candidate result claimed.
33. P10: NOT RUN.
34. P5: NOT RUN.
35. Safety: no new agent existed to validate; frozen source was not modified.
36. Most valuable learned adaptive decision: none causally established; land timing is best reconstructed but not transferable yet.
37. Largest wrong-branch failure: Crop Dusta melon cohort (F1 0.328), followed by its terminal/sheep/cow targets.
38. Promotion: no; CurrentBest remains frozen.
39. Current best: `agents/top50_distilled/top50_observable_portfolio.py`, SHA-256 `f9ca672848ccffdfe56888d99bcdf5a9d7644062b9eec0cf0cdea13574931233`.
40. Recommended next architecture: a safe target-driven economic executor with explicit land/structure/animal/crop commitments and replanning, validated first by exact checkpoint resume and same-state bounded target counterfactuals. Reuse the distilled model only as a guarded target proposer after that executor independently proves coherence.

## 10. Final lock

- Frozen research best: `agents/top50_distilled/top50_observable_portfolio.py` (`f9ca672848ccffdfe56888d99bcdf5a9d7644062b9eec0cf0cdea13574931233`).
- `submission/main.py` was not modified by this stage; observed SHA-256 `789bb9bbd5122eb4891983e776a13777328e3e87736cbbc0b4bc86d13fc33f9b`.
- No Kaggle submission or upload was performed.
