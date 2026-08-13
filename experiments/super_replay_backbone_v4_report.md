# Super Replay Backbone V4 — bounded dynamic strategy search

## Decision

**No V4 agent was promoted. Frozen V2 remains the research best.** No dynamic module passed development, so no module combination was eligible for selection or protected elite final holdout. `submission/main.py` was not modified and nothing was submitted or uploaded.

## Evidence and failure clusters

The deployed V2 corpus now contains **78** valid public episodes: 71 wins / 7 losses / 0 ties, with **0** financial mismatches. The two newly available games added one loss with the same price-realization signature.

| Failure cluster | Games |
|---|---:|
| market realization deficit | 5 |
| endgame inefficiency | 2 |

Bad and good V2 games have nearly identical harvest and sale quantities. The average bad-game milk and strawberry revenues are far lower, so the remaining observational deficit is market realization—not field production.

## Editable windows

| Window | Steps | Reason |
|---|---:|---|
| W1 | 192–192 | last two discretionary cow purchases |
| W2 | 240–264 | second-land liquidation and reinvestment wave |
| W3 | 336–527 | premium realization and second crop wave |
| W4 | 576–718 | terminal ROI, liquidation, and late labor |

## Single-module ablations

| Candidate | Module | Paired W/L/T | Mean Δ money | P10 Δ | P5 Δ | Override rate | Safety |
|---|---|---:|---:|---:|---:|---:|---|
| C_cows6 | C | 6/10/0 | -2,134 | -7,070 | -8,961 | 0.14% | 0/0/0/0 |
| C_cows7 | C | 8/8/0 | -584 | -2,874 | -4,047 | 0.14% | 0/0/0/0 |
| E_liq27 | E | 2/14/0 | -603 | -1,011 | -1,190 | 0.83% | 0/0/0/0 |
| E_no_hire29 | E | 0/16/0 | -3,621 | -5,020 | -5,807 | 0.28% | 0/0/0/0 |
| E_no_seed25 | E | 0/16/0 | -1,270 | -1,586 | -1,632 | 1.39% | 0/0/0/0 |
| M_day | M | 0/16/0 | -1,686 | -2,835 | -2,970 | 1.95% | 0/0/0/0 |
| M_fair | M | 0/16/0 | -1,395 | -2,294 | -2,866 | 3.00% | 0/0/0/0 |
| M_half | M | 2/14/0 | -1,053 | -1,676 | -1,892 | 7.81% | 0/0/0/0 |
| M_hold_floor | M | 0/16/0 | -4,572 | -9,906 | -11,822 | 5.88% | 0/0/39/2 |
| M_hold_low | M | 0/16/0 | -8,111 | -13,914 | -14,879 | 6.08% | 0/0/61/2 |
| M_hold_safe | M | 0/16/0 | -5,651 | -8,782 | -9,672 | 5.51% | 0/0/38/2 |
| M_pressure | M | 0/16/0 | -1,205 | -1,934 | -2,226 | 2.69% | 0/0/0/0 |
| N0_raw | N | 4/12/0 | -2,196 | -8,671 | -12,719 | 0.00% | 0/0/4/0 |
| N1_weed | N | 4/12/0 | -2,184 | -8,671 | -12,719 | 0.00% | 0/0/0/0 |
| N2_rescue | N | 4/12/0 | -2,221 | -8,702 | -12,742 | 0.14% | 0/0/0/0 |
| W_wheat34 | W | 0/16/0 | -1,355 | -1,696 | -1,752 | 0.14% | 0/0/0/0 |
| W_wheat40 | W | 0/16/0 | -679 | -868 | -899 | 0.14% | 0/0/0/0 |

Safety columns are runtime / semantic / livestock-loss / meaningful-stranding counts.

## Counterfactual state replay

The checkpoint harness restores environment seed metadata and warms replay-backbone state from prior observations. It reproduced uninterrupted V2 at steps 160, 240, 480, and 600 for every tested episode before any branch was trusted.

### Market

| Alternative | Games | W/L/T | Mean final-bank Δ |
|---|---:|---:|---:|
| sell_strawberry_four_steps_early | 4 | 2/2/0 | +95.5 |
| sell_strawberry_eight_steps_early | 4 | 2/2/0 | +81.0 |
| sell_strawberry_twelve_steps_early | 4 | 2/2/0 | +72.5 |
| sell_strawberry_one_step_early | 4 | 1/3/0 | +44.8 |
| half_strawberry_399 | 4 | 4/0/0 | +3.5 |
| three_quarter_strawberry_399 | 4 | 4/0/0 | +2.5 |
| quarter_strawberry_399 | 4 | 3/1/0 | +1.2 |
| half_milk_406 | 4 | 0/0/4 | +0.0 |
| delay_strawberry_399 | 4 | 3/1/0 | -0.5 |
| full_strawberry_399 | 4 | 0/4/0 | -8.2 |
| delay_milk_406 | 4 | 0/4/0 | -448.5 |

The best local perturbation—selling one strawberry batch four steps earlier—was only +95.5 coins and split 2/2. Nearby timing and quantity values were similarly tiny and inconsistent.

### Endgame

| Alternative | Mean final-bank Δ |
|---|---:|
| skip_day25_seed | -190.5 |
| liquidate_premium_day27 | -291.0 |
| skip_day29_hires | -2,985.8 |

### Capital

| Alternative | Mean final-bank Δ |
|---|---:|
| buy_one_final_cow | -463.2 |
| buy_zero_final_cows | -2,287.5 |

## Nazmus safety experiment

Raw Nazmus lost four animals in the screen. K3 repair and the narrow shed-cow rescue both eliminated observed losses, but N1/N2 lost roughly 2.2k paired money to V2. The rescue therefore does not expose a stronger safe architecture.

## Selection, final confirmation, and attribution

The numerically strongest rejected dynamic candidate was `C_cows7` at -584 paired money—still negative. Because no individual module passed, no combination search was run. Frozen V2 alone was SHA-locked and completed 40 fresh both-seat fixed/natural games with 0 runtime failures, 0 semantic failures, 0 livestock losses, and 0 meaningful stranding events.

Economic attribution is therefore negative: earlier selling loses recovery value; holding inventory consumes shed/feed liquidity and causes safety failures; removing cows loses milk/fertilizer annuity; suppressing terminal seed/hire spend sacrifices harvest/service income; shrinking the wheat wave reduces output. There is no positive V4 delta to attribute.

## Promotion gate

| Gate | Result |
|---|---|
| Positive paired mean | FAIL for every module |
| ≥60% decisive wins and +1.5k–2k | FAIL |
| P10/P5 non-regression | FAIL for every module family |
| Safety | PASS for many isolated variants; FAIL for hold-market and raw Nazmus |
| Selection/final unseen | Not opened for rejected candidates |
| Promotion | **No** |

## Remaining dynamic headroom and next architecture

The measured hand-designed dynamic oracle is noise-level around the opened sale window (under +100 coins locally), while broad online thresholds lose thousands. The bottleneck is not insufficient search over a simple threshold: market action value is strongly state-dependent and correlated with unobserved opponent inventory/future sales. A learned residual action-value model is now justified only as an offline next research architecture, trained on validated checkpoint counterfactuals and still constrained to rare overrides. It should not replace V2 and should not be RL from scratch.

V2 remains: `agents/super_replay_v2/super_backbone_v2.py` at `c39d82b4f796271603e32ea8cb4b70261fbbe3d4e17940886caf5f5a6bd9adef`.

## Requested completion summary

1. Real V2 episodes analyzed: **78**.
2. Dominant clusters: five market-realization deficits; two endgame economic losses.
3. Editable windows: step 192; 240–264; 336–527; 576–718.
4. Market counterfactual: broad rules regress; best local perturbation +95.5 and 2/2.
5. Endgame counterfactual: every tested change negative (−190.5 to −2,985.8).
6. Capital allocation: seven cows −463.2 locally / −583.6 screen; six cows worse.
7. Crop wave: reduced day-20 wheat purchases lose 679–1,355 paired money.
8. Nazmus rescue: safety restored, but approximately −2.2k paired versus V2.
9. Strongest individual module: `C_cows7`, still -584.
10. Strongest combination: none; no individual module qualified for combination.
11. Override frequency: `C_cows7` 0.14%; tested range 0.14%–7.81% excluding raw routes.
12. V2 baseline fresh confirmation: 40 games, average money 77,655.
13. V4 finalist result: no V4 finalist; V2 only.
14. Direct paired delta: every V4 module negative; best −583.6.
15. Natural RNG delta: not opened for rejected modules beyond the development paired panel.
16. Recent elite replay result: no candidate passed the real-loss/development-elite gate.
17. Final unseen result: not opened for rejected V4 candidates; V2 fresh confirmation only.
18. V2 fresh-confirmation P10 advantage: -161.9.
19. V2 fresh-confirmation P5 advantage: -445.9.
20. Safety: V2 0 runtime / 0 semantic / 0 livestock / 0 meaningful stranding.
21. Economic attribution: all tested changes destroy sale recovery, annuity, crop output, or terminal service value.
22. V4 promoted: **No**.
23. Research-best source: V2 path and SHA above; no `super_backbone_v4.py` created.
24. Remaining hand-designed dynamic headroom: under about 100 coins in the measured local sale window.
25. Next step: offline learned residual action-value control with rare overrides, not RL from scratch.
