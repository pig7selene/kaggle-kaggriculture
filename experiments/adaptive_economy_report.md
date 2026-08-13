# Adaptive Economy Experiment Report

## Evaluation design

- Eight opponents: frozen melon-12 plus seven replay-backed proxies documented
  in `experiments/adversarial_pool.md`.
- Fixed seeds 8000–8015, with every matchup played in both positions.
- 32 games per matchup and 256 games per serious candidate.
- All final table entries use the frozen post-endgame-fix engine and identical
  pool code.
- P10 is the 10th percentile of each seed's average money advantage after
  averaging both seats and all pool opponents.
- Variance is sample variance of final candidate money across 256 games.

## Controlled candidates

| Version | Controlled change from engine control |
| --- | --- |
| `adaptive_control` | Fixed 12 melons, two hands, immediate selling; isolates the shared scheduler from the frozen baseline |
| `adaptive_a_crop` | Adaptive crop scoring only |
| `adaptive_b_selling` | Inventory-aware selling only |
| `adaptive_c_phased` | Explicit melon → strawberry → wheat phases only |
| `adaptive_d_land_labor` | ROI-gated land plus workload-based labor only |
| `adaptive_e_crop_selling` | A + B |
| `adaptive_f_full` | E + D, with no additional phase weighting |
| `adaptive_g_tuned` | Search-selected phase-aware adaptive crop scoring + selling, no land |
| `adaptive_h_hybrid` | Phase defaults with a modeled-profit override when an alternative is at least 1.30× better |

The adaptive crop score uses observed price/inventory, current town shops,
visible opponent crop ages and expected output, seed cost, time-to-yield,
remaining season, labor/land capacity, and projected self-market impact. Crops
that cannot create sellable yield by day 29 are excluded.

## Frozen full-pool results

| Candidate | Games | W/L/T | Win rate | Avg money | Avg advantage | P10 seed advantage | Money variance / SD | Weakest matchup |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `melon_scale_12` | 256 | 160/64/32 | 62.50% | 18551.26 | +3129.41 | +2727.81 | 14455565 / 3802.05 | livestock (0/32, -19008.22) |
| `adaptive_control` | 256 | 224/32/0 | 87.50% | 19322.93 | +3784.34 | +3426.62 | 13437478 / 3665.72 | livestock (0/32, -17960.06) |
| `adaptive_a_crop` | 256 | 224/32/0 | 87.50% | 25155.40 | +6564.82 | +6056.44 | 7789350 / 2790.94 | livestock (0/32, -14955.38) |
| `adaptive_b_selling` | 256 | 224/32/0 | 87.50% | 19328.23 | +3789.66 | +3431.88 | 13404653 / 3661.24 | livestock (0/32, -17959.50) |
| **`adaptive_c_phased`** | **256** | **224/32/0** | **87.50%** | **28004.63** | **+11599.96** | **+11233.44** | **5766718 / 2401.40** | **livestock (0/32, -8125.41)** |
| `adaptive_d_land_labor` | 256 | 132/124/0 | 51.56% | 13898.42 | -677.20 | -1072.81 | 25492358 / 5049.00 | livestock (0/32, -28080.53) |
| `adaptive_e_crop_selling` | 256 | 224/32/0 | 87.50% | 25155.40 | +6564.82 | +6056.44 | 7789350 / 2790.94 | livestock (0/32, -14955.38) |
| `adaptive_f_full` | 256 | 206/50/0 | 80.47% | 24147.21 | +3696.08 | +2643.56 | 19915355 / 4462.66 | livestock (0/32, -16924.50) |
| `adaptive_g_tuned` | 256 | 224/32/0 | 87.50% | 25232.73 | +6723.08 | +6346.25 | 8204159 / 2864.29 | livestock (0/32, -14949.81) |
| **`adaptive_h_hybrid`** | **256** | **224/32/0** | **87.50%** | **26109.72** | **+7344.73** | **+6845.09** | **7823573 / 2797.07** | **livestock (0/32, -13669.62)** |

`adaptive_c_phased` is the strongest pool strategy by average income,
advantage, tail, variance, and least-bad worst matchup. It won all 32 games
against each of seven opponents and lost all 32 against the livestock proxy.
Its livestock deficit averaged 8,125.41 coins, with a matchup P10 advantage of
-10,348.75.

`adaptive_h_hybrid` is the strongest agent that makes an economic crop choice
at planting time. It also went 7–1 by matchup, but its livestock deficit was
13,669.62 and it earned 1,894.91 less average money than fixed phased rotation.

## Component effects

Controlled average-money deltas:

| Component comparison | Avg-money change | Interpretation |
| --- | ---: | --- |
| Engine control vs frozen melon-12 | +771.67 | Central task assignment/routing is a modest independent gain |
| Adaptive crops (A) vs engine control | +5832.47 | Largest genuinely adaptive gain; also lowers money SD by 874.78 |
| Selling only (B) vs engine control | +5.30 | No meaningful local improvement under ordinary thresholds |
| Fixed phases (C) vs engine control | +8681.70 | Largest total gain; replay-backed production timing dominates |
| Crop + selling (E) vs crop only (A) | +0.00 | Selling decisions were identical in the final pool |
| Land/labor only (D) vs engine control | -5424.51 | Expansion creates self-gluts and high capital/path variance |
| Full F vs E | -1008.19 | Land/labor also harms the adaptive combined agent |
| Tuned phase scoring (G) vs E | +77.33 | Small tail improvement, not a step change |
| Hybrid phase override (H) vs G | +876.99 | Phase anchoring recovers meaningful income while retaining adaptation |

The systematic search covered 46 configurations across the main grid and its
focused extensions: melon allocation, sell/forecast thresholds, inventory
reserve, liquidation step, land scale/hurdle/timing, labor capacity, phase
bias, and hybrid override margin. Important negatives were reproducible:

- A 50% melon allocation cap lost two of five search matchups.
- Holding until 110–120% of base price reduced income and made P10 negative.
- Day-14 land was safer than day-11 land, but both lost to no-land adaptive play.
- No tested land/hiring configuration improved full-pool robustness.

## Endgame and action safety

The first semantic audit found five valuable units stranded by a dynamic agent
after a day-29 harvest. The final scheduler now:

- rejects new crops that cannot produce sellable yield in time;
- forces shed liquidation from step 648;
- limits day-29 harvesting to hour 10 or earlier;
- returns workers carrying valuable inventory to the shed for `DROP` and a
  subsequent final sale.

`python test_economic_agents.py` completed checked 720-turn games for every
candidate and proxy, validating action arity and tile/item applicability and
asserting zero valuable endgame inventory for candidates.

## Decision

No candidate is promoted. No Kaggle submission is justified yet.

The local improvement is large and consistent, but every serious candidate
loses 0–32 to the replay-inspired livestock/crop proxy. That proxy represents
the strongest observed real opponent and exposes the missing secondary revenue
engine. The strongest local strategy is also fixed-phase rather than fully
adaptive, while the strongest adaptive hybrid still leaves substantial income
on the table. Finally, the proxy set derives from only two public opponents, so
the 87.5% pool win rate is not a reliable leaderboard estimate.

Highest-priority remaining weaknesses:

1. No candidate livestock investment/operations branch.
2. Land ROI does not yet value crop diversification and routing congestion
   accurately enough; expansion increases variance and self-glut risk.
3. Selling forecasts cannot observe hidden opponent shed inventory and have no
   memory of recent visible harvest disappearance.
4. The phase plan may overfit two public episodes and eight local archetypes.
5. More real Kaggle episodes are needed before calibrating another submission.
