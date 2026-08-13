# Post-opening real Kaggle gap

Date: 2026-08-11  
Newest submission: `55435253` (`public-opening + scalable router v6`)  
Frozen/current-best source: `agents/opening_public_front_cow8_day6.py`  
Submission status: `submission/main.py` was not modified and nothing was submitted.

## Executive conclusion

The new opening improved the early trajectory, but it did not fully reproduce
the top public economy. In three of four newest losses, the opponent's realized
revenue becomes durably higher on **day 11**, immediately after the second-land
planting and first major crop-sale wave. Pedro is the exception: his realized
revenue is ahead from day 0 and more than 2,500 ahead from day 7. Bank/equity
usually turn against us later because both players reinvest at different rates.

The decisive day-10–20 deficit is a **crop-throughput deficit**, not an animal
or nominal hand-count deficit. The top corpus earns 28,909 crop coins versus
4,592 for us in this window. We earn more animal revenue (26,317 versus
19,954), but that 6,363 edge cannot offset the 24,318 crop gap. Top agents keep
73.2 productive tiles (97.6% occupancy), harvest 147 times, and make 51
strawberry fertilizer applications. We keep 62.9 tiles (83.8%), harvest only
70 times, and never fertilize crops.

The most important maintenance distinction is not the raw watering-miss rate.
Top agents intentionally leave many plants unwatered for one safe day, but
almost never miss a second consecutive refresh: their critical miss rate is
0.29%, versus 2.79% for us. Our farm drops from 62 productive tiles on day 12
to 53.5 on day 15 and then spends day 16 replanting 17 lost/harvested slots.
Top agents hold about 74 productive tiles throughout days 12–19.

The only isolated local improvement that transferred across the replay-derived
league was **T2, post-day-10 replacement-planting priority**. On fresh seeds it
raised occupancy from 83.6% to 90.8%, reduced critical misses from 2.38% to
1.10%, cut time to 23 productive tiles in the newest quadrant from 43 to 37
turns, and raised average money against replay-derived agents by 4,423.
However, exact reconstructed loss traces remained mixed: T2 changed 0/8 wins
to 3/8, but only improved average advantage by 149, worsened P10, and regressed
badly against the Jayveer and Pedro traces. **It is not promoted.**

## 1. Newest public episodes

All ten currently available public episodes for submission `55435253` were
downloaded and reconstructed for both players. Dynamic-price cash flow matched
every observed bank transition: zero reconstruction mismatches.

| Episode | Our seat | Opponent | Rating at capture | Result | Our final | Opponent final |
| ---: | ---: | --- | ---: | --- | ---: | ---: |
| 92006057 | 0 | Romone Dunlop | 657.7 | Win | 68,512 | 52,032 |
| 92006971 | 1 | Thayaparan Kumarakuru | 672.7 | Win | 104,054 | 57,980 |
| 92007907 | 1 | Parham Ghazanfari | 749.0 | Win | 55,188 | 36,433 |
| 92008833 | 1 | JayveerSingh6 | 888.7 | Loss | 58,063 | 69,799 |
| 92009080 | 0 | Lucas Ferreira | 878.9 | Loss | 72,478 | 74,879 |
| 92009829 | 1 | Haitaks | 721.1 | Win | 114,542 | 85,263 |
| 92010768 | 0 | Pedro Rezende Gomes | 844.7 | Loss | 61,541 | 70,656 |
| 92011750 | 1 | alexander kern | 837.7 | Loss | 59,892 | 72,227 |
| 92012708 | 1 | Ange Adantchede | 616.8 | Win | 93,930 | 46,016 |
| 92013656 | 0 | Audric LOKO | 819.5 | Win | 70,466 | 65,566 |

The newest submission was 6/4 in this public set. All four losses were against
players above or close to our captured 833.3 rating; Lucas was the closest
game at -2,401.

### Durable-lead timing in losses

“Revenue lead” means exact cumulative realized sale revenue. “Bank” is cash at
day end. “Equity” adds observed inventory and book-value productive assets; it
is useful for timing but is not a liquidation-price forecast.

| Episode/opponent | Durable revenue lead | Durable revenue lead >2,500 | Durable bank lead | Durable equity lead | Final gap |
| --- | ---: | ---: | ---: | ---: | ---: |
| 92008833 / JayveerSingh6 | 11 | 11 | 21 | 20 | 11,736 |
| 92009080 / Lucas Ferreira | 11 | 11 | 18 | 10 | 2,401 |
| 92010768 / Pedro Rezende Gomes | 0 | 7 | 19 | 19 | 9,115 |
| 92011750 / alexander kern | 11 | 23 | 23 | 24 | 12,335 |

The median durable realized-revenue lead is day 11. The former day-6–8
diagnosis no longer describes three of the four losses.

## 2. Newest trajectory versus the top corpus

The comparison population is the existing 25-replay corpus: 35 appearances by
eight public teams rated 3097–3217 when captured. Values below are population
medians. Productive tiles are living crops plus occupied animal structures;
“used” is the count of distinct productive tiles on which a successful action
occurred that day.

### Money and scale checkpoints

| Day | Population | Cum. revenue | Bank | Q | Hands | Cows/sheep | Productive tiles | Used tiles |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | Ours | 694 | 552 | 1 | 2 | 1/4 | 15 | 14 |
| 2 | Top | 496 | 181 | 1 | 2 | 1/4 | 15 | 15 |
| 4 | Ours | 1,656 | 824 | 1 | 3 | 1/4 | 14 | 18 |
| 4 | Top | 1,458 | 543 | 1 | 3 | 1/4 | 19 | 15 |
| 6 | Ours | 4,750 | 24 | 1 | 4 | 2/4 | 23 | 23 |
| 6 | Top | 4,242 | 26 | 2 | 4 | 3/4 | 27 | 21 |
| 8 | Ours | 6,884 | 8 | 2 | 6 | 8/4 | 40 | 38 |
| 8 | Top | 8,080 | 258 | 2 | 6 | 8/4 | 50 | 29 |
| 10 | Ours | 15,640 | 3,136 | 3 | 14 | 8/4 | 58.5 | 56 |
| 10 | Top | 19,769 | 4,887 | 3 | 14 | 8/4 | 67 | 50 |
| 12 | Ours | 19,986 | 5,340 | 3 | 10 | 8/4 | 62 | 62 |
| 12 | Top | 23,106 | 6,993 | 3 | 10 | 8/4 | 74 | 50 |
| 15 | Ours | 26,102 | 10,086 | 3 | 9 | 8/4 | 53.5 | 49 |
| 15 | Top | 34,014 | 16,386 | 3 | 9 | 8/4 | 74 | 49 |
| 20 | Ours | 47,384 | 26,732 | 3 | 14 | 9/4 | 67 | 68.5 |
| 20 | Top | 70,926 | 44,768 | 3 | 14 | 8/4 | 73 | 55 |
| 25 | Ours | 72,774 | 48,526 | 3 | 12 | 9/4 | 62.5 | 66 |
| 25 | Top | 94,020 | 66,487 | 3 | 12 | 9/4 | 73 | 58 |
| 30 | Ours | 94,746 | 69,489 | 3 | 10 | 9/4 | 25 | 12.5 |
| 30 | Top | 111,636 | 81,668 | 3 | 10 | 9/4 | 16 | 35 |

### Crop and execution checkpoints

Crop mix is W=wheat, S=strawberry, M=melon, C=carrot.

| Day | Population | Crop mix | Cum. crop rev. | Cum. animal rev. | Movement | Productive actions | Raw watering miss |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 2 | Ours | W5/M5 | 0 | 694 | 52.0% | 32.0% | 6.7% |
| 2 | Top | W5/M5 | 0 | 496 | 23.6% | 32.2% | 33.3% |
| 4 | Ours | W2/S2/M5 | 0 | 1,656 | 55.7% | 32.1% | 9.6% |
| 4 | Top | W6/S3/M5 | 0 | 1,458 | 29.6% | 34.1% | 32.8% |
| 6 | Ours | W6/S6/M5 | 252 | 4,491 | 55.8% | 33.9% | 8.5% |
| 6 | Top | W7/S8/M5 | 542 | 3,700 | 33.4% | 35.5% | 38.8% |
| 8 | Ours | W8/S15/M5 | 252 | 6,649 | 56.5% | 34.8% | 6.6% |
| 8 | Top | W13/S20/M5 | 803 | 7,252 | 35.4% | 38.9% | 35.5% |
| 10 | Ours | W13.5/S32/M1 | 4,179 | 11,516 | 56.4% | 34.4% | 8.7% |
| 10 | Top | W13/S31/M12 | 8,563 | 11,204 | 37.1% | 37.1% | 34.1% |
| 12 | Ours | W10.5/C3.5/S32/M4 | 6,686 | 13,436 | 56.0% | 34.7% | 8.7% |
| 12 | Top | W13/S36/M14 | 9,005 | 13,613 | 37.6% | 37.4% | 36.1% |
| 15 | Ours | W5/S32/M4 | 6,988 | 19,613 | 54.9% | 35.0% | 10.3% |
| 15 | Top | W13/S36/M14 | 11,394 | 22,677 | 39.1% | 37.3% | 39.2% |
| 20 | Ours | W10.5/S39.5/M4 | 8,861 | 38,631 | 53.3% | 34.8% | 8.6% |
| 20 | Top | W26/S33/M2 | 37,143 | 31,450 | 41.2% | 38.2% | 36.7% |
| 25 | Ours | W23/S26.5 | 24,323 | 48,570 | 53.6% | 35.3% | 8.6% |
| 25 | Top | W44/S15 | 49,104 | 40,590 | 41.8% | 39.6% | 36.5% |
| 30 | Ours | W2.5/S9 | 45,034 | 53,216 | 51.3% | 34.0% | 9.8% |
| 30 | Top | W2 | 59,547 | 46,680 | 42.8% | 38.9% | 35.6% |

The high top raw-miss rate is intentional slack, not crop neglect. It becomes
economically safe because top agents almost never allow a second consecutive
miss. That distinction is visible only in the action-level audit.

## 3. Day 10–20 economic and routing decomposition

| Metric | Newest agent | Newest losses only | Real-loss opponents | Top corpus |
| --- | ---: | ---: | ---: | ---: |
| Revenue growth | 31,021 | 31,021 | 48,067 | 50,983 |
| Crop revenue | 4,592 | 4,566 | 23,738 | 28,909 |
| Animal revenue | 26,317 | 26,317 | 18,356 | 19,954 |
| Avg productive tiles | 62.9 | 63.0 | 67.7 | 73.2 |
| Capacity utilization | 83.8% | 84.1% | 83.7% | 97.6% |
| Avg distinct used tiles/day | 61.0 | 61.0 | 51.8 | 55.4 |
| Avg/peak hands | 10.9 / 14 | 10.9 / 14 | 11.3 / 11.5 | 10.9 / 14 |
| Movement | 52.0% | 51.6% | 57.6% | 43.4% |
| Productive actions | 34.5% | 34.4% | 35.3% | 38.0% |
| Moves/productive action | 1.51 | 1.50 | 1.79 | 1.13 |
| Raw watering miss | 9.12% | 8.26% | 31.58% | 37.40% |
| **Critical watering miss** | **2.79%** | **2.60%** | **1.40%** | **0.29%** |
| Successful harvests | 70 | approximately 70 | — | 147 |
| Crop fertilizer actions | 0 | 0 | 33.5 | 51 |
| Avg empty tiles | 12.1 | 12.0 | 11.6 | 1.8 |
| Seed spending | 2,020 | 1,985 | 3,125 | 820 |
| Labor spending | 3,040 | 3,040 | 3,040 | 3,040 |

The action-level audit corrects an earlier high-level replay summary: the top
corpus does use crop fertilizer in the midgame—51 median successful actions in
this window, all on strawberries. It also sells much of its fertilizer. The
policy is selective production-day application, not “fertilize every crop.”

### What happens after the second deed

Both populations observe the second extra quadrant around day 10 hour 1.

| Population | 1 tile | 6 tiles | 12 tiles | 18 tiles | 23 tiles |
| --- | ---: | ---: | ---: | ---: | ---: |
| Ours, turns after unlock | 1 | 6 | 10 | 16 | 43.5 |
| Top, turns after unlock | 12 | 15 | 19 | 22 | 35 |

Our router starts sooner and is faster through 18 tiles. It then stalls for
27.5 turns to reach 23, while the top planting wave needs only 13 turns from 18
to 23. Therefore “initial deployment is slow” is false; **completion and
subsequent maintenance are slow**. This is why T2 focuses on replacement and
the last empty slots rather than merely hiring more workers.

### A–I diagnosis

| Hypothesis | Verdict | Evidence |
| --- | --- | --- |
| A. Too few workers | Rejected as primary cause | Ours and top both average 10.9, peak at 14, and spend 3,040 on labor. The historical “12 ceiling” no longer describes this source. |
| B. Bad worker placement | Secondary | Ours moves 8.6 percentage points more than top. Worker 9 records 121 moves for 43.5 productive actions; top worker 9 records 111/81. |
| C. Bad territory sizes | Secondary, specific workers | Persistent territory purity is 100% in both populations, but work is imbalanced. Workers 3 and 8 use 163/163.5 moves for 82/68 productive actions; top is 126/85 and 125/83. A simple late-worker rebalance (T3) regressed. |
| D. Animal workers consume too much labor | Rejected | Animal-work share is 38.7% versus 37.7%; animal specialists average 3.64 versus 3.73. Our animal revenue is higher. |
| E. Planting too slowly after expansion | Partly confirmed | We reach 18 tiles sooner but the 23rd tile 8.5 turns later. T2 cuts this to 37 turns and is the strongest isolated ablation. |
| F. Watering/harvest latency | Confirmed | Critical misses are about 9.6× top (2.79%/0.29%); harvests are 70 versus 147. The farm collapses days 12–15 and replants on day 16. |
| G. Wrong crop mix | Confirmed structurally | At day 10 ours has 1 melon versus 12 top; by day 20 crop revenue trails 28,282 cumulatively. A day-11 allocation rule alone is too late to recreate the mature day-10 melon cohort. |
| H. Capital shortage | Rejected after day 10 | In essentially 100% of post-land hours with empty slots, the bank or seed inventory could fund another strawberry. |
| I. Shed/inventory overhead | Not primary | Logistics is 1.7% for us versus 2.8% top. Loaded shed-return moves are lower, 173.5 versus 225. The larger waste is field travel per completed crop task. |

The single largest routing waste is rigid long-distance field servicing by
workers 3, 8, and 9, plus an underused main animal specialist. Worker 0 records
119 PASS, 59 movement, and 71 productive actions; the top median is 52 PASS,
88 movement, and 112 productive actions, including 29 crop actions after its
animal queue. However, T3 demonstrates that a static territory remap is not a
sufficient fix.

## 4. Controlled ablations

Every candidate is action-identical to T0 through day 10. This was checked on
two additional fixed seeds, one from each seat. The common router/economic
files received opt-in controls; their defaults preserve T0. Replaying the four
actual loss action traces reproduces T0's original final money in the original
seat, providing an end-to-end semantic check.

Screening used two unseen seeds, both seats, six old synthetic opponents and
seven replay-derived opponents, plus the four exact loss traces in both seats:
60 games per candidate. Exact action-trace opponents are counterfactual rather
than adaptive: their hand list is resized if market interaction changes their
state, but their planned actions remain the recorded ones.

| Candidate | Change after day 10 | W/L/T | Avg money | Avg advantage | D10–20 revenue | Avg tiles | Critical miss | Old score | Replay-derived score | Real-loss W/L, avg adv. |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| T0 | Frozen current | 52/8/0 | 83,755 | +42,711 | 33,772 | 63.0 | 2.38% | 100% | 100% | 0/8, -8,366 |
| T1 | Keep 14 hands on days 11–20 | 51/9/0 | 79,712 | +40,915 | 33,411 | 70.9 | 2.02% | 100% | 92.9% | 1/7, -11,846 |
| **T2** | Plant before routine water, after harvest/critical water | **55/5/0** | **84,869** | **+44,665** | 33,511 | **68.2** | **1.06%** | 100% | **100%** | **3/5, -8,217** |
| T3 | Replay-balanced late-worker zones | 52/8/0 | 84,443 | +42,702 | 33,630 | 59.9 | 2.63% | 100% | 100% | 0/8, -9,256 |
| T4 | Replay crop ratios/phases | 52/8/0 | 83,754 | +42,914 | 33,571 | 63.1 | 2.61% | 100% | 100% | 0/8, -9,794 |
| F | Mature-strawberry fertilizer only | 51/9/0 | 80,707 | +38,641 | 31,552 | 63.4 | 2.00% | 100% | 96.4% | 0/8, -13,214 |
| W | Noon watering guard | 51/9/0 | 78,724 | +36,924 | 31,908 | 62.5 | 2.54% | 100% | 96.4% | 0/8, -15,117 |
| T5 | T2 + replay crop phases | 53/7/0 | 85,458 | +45,149 | 33,565 | 68.2 | 1.03% | 100% | 100% | 1/7, -11,128 |

T1 proves that occupancy alone is not profit. It reaches 94–95% local
occupancy but pays for excess labor and still misses critical maintenance. F
proves fertilizer is downstream of throughput: 27.5 applications per window
consume work and fertilizer-sale cash without first preserving enough mature
strawberries. T5 looks best on aggregate synthetic money but fails the real
trace gate, so it is rejected.

## 5. Fresh held-out confirmation

T0 and T2 were confirmed on seeds 812000–812007 against 13 programmable
opponents, both seats (208 fresh games per candidate), plus the eight fixed
real-loss trace counterfactuals. No runtime or action-schema failures occurred.

| Group | Candidate | Games | W/L/T | Score | Avg money | Avg advantage | P10 paired | D10–20 rev. | Avg tiles | Critical miss | 23rd-tile turns |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Old synthetic | T0 | 96 | 96/0/0 | 100% | 101,686 | +76,938 | +50,125 | 37,587 | 63.0 | 2.31% | 43 |
| Old synthetic | T2 | 96 | 96/0/0 | 100% | 103,884 | +79,175 | +53,354 | 37,330 | 68.2 | 0.93% | 37 |
| Replay-derived | T0 | 112 | 112/0/0 | 100% | 78,277 | +33,925 | +16,503 | 31,079 | 62.7 | 2.38% | 43 |
| Replay-derived | T2 | 112 | 112/0/0 | 100% | 82,700 | +38,876 | +19,804 | 31,428 | 68.1 | 1.10% | 37 |
| Reconstructed real losses | T0 | 8 | 0/8/0 | 0% | 64,680 | -8,366 | -11,313 | 29,910 | 63.1 | 2.51% | 43.5 |
| Reconstructed real losses | T2 | 8 | 3/5/0 | 37.5% | 59,600 | -8,217 | -18,809 | 30,225 | 68.1 | 1.24% | 38.5 |

Overall, T2 is 211/5 versus T0's 208/8, with 91,260 versus 88,178 average
money. The exact real-loss outcomes reveal why it is not promoted:

| Reconstructed opponent | T0 paired avg advantage | T2 paired avg advantage | Interpretation |
| --- | ---: | ---: | --- |
| JayveerSingh6 | -11,736 | -20,630 | Material regression |
| Lucas Ferreira | -2,375 | +4,702 | Loss pattern fixed |
| Pedro Rezende Gomes | -10,325 | -14,559 | Regression |
| alexander kern | -9,027 | -2,380 | Material improvement, one seat won |

T2 fixes two of the four observed patterns, not the population weakness. The
P10 degradation and lower exact-trace average money fail the robustness gate.

## 6. Direct answers

1. **When do the newest losses become durable?** Realized revenue becomes
   durably opponent-favored on day 11 in three of four losses. Pedro is ahead
   from day 0 and materially ahead by day 7. Durable cash/equity leads usually
   appear later, days 18–24.

2. **Is the new day 0–10 opening actually matching top agents?** Partly. It
   matches the 1-cow/4-sheep start, reaches eight cows, three quadrants, and 14
   hands, and is ahead in cumulative revenue through day 6. It does not match
   deployment: first land is observed later within day 6/7, productive tiles
   are 40 versus 50 on day 8 and 58.5 versus 67 on day 10, and the day-10 crop
   mix has one melon versus 12.

3. **What is the first major divergence?** Capacity begins diverging by day 6,
   but the first repeatable durable economic break is the day-11 crop wave.
   Top agents enter it with more mature crops and almost full land; we enter it
   with empty/recently replanted slots.

4. **How large is the day 10–20 throughput gap?** 19,962 revenue. The crop gap
   is 24,318 against us, partly offset by a 6,363 animal edge. Top keeps 10.3
   more productive tiles and performs 147 versus 70 harvests.

5. **Why do top agents reach 90%+ tile utilization?** They fill the entire
   farm in a bounded planting wave, preserve mature crops by allowing safe
   single watering skips but almost no consecutive misses, harvest promptly,
   replant replacement slots, and fertilize mature strawberry production
   cohorts. They do not achieve it merely by holding 14 hands every day.

6. **Is 12 hands actually too few?** The premise is stale for this source. It
   peaks at 14 and has the same median day-specific hand schedule and labor
   spend as the top corpus. T1's always-14 days 11–20 policy loses money.

7. **What routing still wastes the most actions?** Long field travel and load
   imbalance for crop workers 3/8/9, plus main-specialist idle time. Overall
   movement is 52.0% versus 43.4%, or 1.51 versus 1.13 moves per productive
   action. A static territory remap is not enough; task lifecycle and local
   replacement completion matter more.

8. **Is crop allocation now the main issue?** Crop economics are the main
   revenue issue, but the cause is allocation **plus maturity preservation and
   execution**. T4's day-11 ratio change is neutral because it cannot recreate
   the already-mature melon/strawberry cohorts visible on day 10 and does not
   fix losses/replant latency by itself.

9. **Which isolated change gives the largest replay-grounded improvement?** T2
   replacement-planting priority. It adds about 5.4 productive tiles, halves
   critical misses, finishes the newest quadrant six turns sooner, and adds
   4,423 average money in the fresh replay-derived league. No other isolated
   component passes all three group checks.

10. **Why should that improvement transfer better than previous local gains?**
    It changes a directly observed real-replay mechanism and improves exact
    counterfactual traces as well as replay-derived agents; it is not selected
    solely on weak synthetic wins. Nevertheless, its Jayveer/Pedro regressions
    and worse real-trace P10 show that the present evidence is **not strong
    enough to claim robust transfer or promote it**.

## 7. Decision and next research boundary

- Current best remains `agents/opening_public_front_cow8_day6.py`.
- `agents/post_opening_t2_deploy.py` is the strongest diagnostic candidate,
  not a promoted agent.
- The next justified architecture work is a lifecycle-aware local queue that
  jointly schedules harvest → replacement plant → safe watering while
  preserving mature day-10 cohorts. It should be tested against the Jayveer
  and Pedro patterns before crop fertilizer or crop ratios are reintroduced.
- No Kaggle packaging or submission is justified by this experiment.

## Artifacts

- `analyze_post_opening_real_gap.py`
- `experiments/post_opening_real_gap_diagnosis.json`
- `experiments/post_opening_real_gap_diagnosis.md`
- `run_post_opening_validation.py`
- `experiments/post_opening_screen_control.json`
- `experiments/post_opening_screen_variants.json`
- `experiments/post_opening_screen_water_guard.json`
- `experiments/post_opening_screen_combined.json`
- `experiments/post_opening_confirm.json`
- `agents/post_opening_t1_hands14.py`
- `agents/post_opening_t2_deploy.py`
- `agents/post_opening_t3_territory.py`
- `agents/post_opening_t4_crop_mix.py`
- `agents/post_opening_f_fertilizer.py`
- `agents/post_opening_w_water_guard.py`
- `agents/post_opening_t5_deploy_crop.py`

