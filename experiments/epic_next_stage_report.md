# Epic next-stage architecture research

## Decision

No candidate is promoted. The frozen current best remains
`agents/lifecycle_lc_combined.py` (SHA-256
`db12d32912843e012c3dfd7e84c2c384ce998694bf02b98fc7e1fe9189c17e78`).

The strongest research branch is
`agents/epic_b8_capacity_value_guarded.py`: six cows, the local action-value
scheduler, and a semantic guard against duplicate terminal animal actions. It
is a real improvement on the two diagnosed losses, but it fails the stated
promotion bar on fresh direct, tail, hard-pool, and RNG-coupling evidence.

`submission/main.py` was not modified and nothing was submitted. Its SHA-256
remains `d0fbf1205a7e27f8294f1f9a06afd581cfb3e926f8ab88acc0b7f7a8b72620cf`.

## Evidence and controls

- Exact fixed-shop reconstructions: Jayveer episode **92008833** and Pedro
  episode **92010768**, 719 requested actions each, with the original opponent
  action traces.
- Broader real set: Lucas **92009080** and Alexander **92011750**.
- Top production corpus: 35 strong appearances from the existing 25-replay
  public corpus.
- Strategy comparisons used the same deterministic seed, the same recorded or
  independently generated shop schedule, and both seats.
- Diagnosis, development, selection, held-out, and RNG-audit seed partitions
  were separate.
- The final held-out league contained the four real reconstructions, seven top
  replay archetypes, the frozen current best, livestock/high-labor/land agents,
  and two new adversaries derived from the Jayveer/Pedro mechanisms.

## 1. Why Jayveer still beats the frozen agent

The first durable difference is not worker travel. It is a crop-capital event
at **day 11 hour 0**.

| Time | Frozen agent | Jayveer | Consequence |
| --- | --- | --- | --- |
| Day 6 end | 5 melons, 6 wheat, 6 strawberry; 2 cows + 4 sheep | 11 melons, 1 wheat, 7 strawberry; 2 cows + 2 sheep | Jayveer has roughly twice the premium one-time crop cohort while we carry more animal service load. |
| Day 9 h22 | — | Sells 12 milk and buys first land | Animal cash opens crop capacity before the large crop sale. |
| Day 10 h21 | Sells 10 melons | — | Our smaller initial melon cohort realizes first, but is not large enough to create a durable lead. |
| **Day 11 h0** | Sells fertilizer | **Sells 42 melons for 10,188, 5 fertilizer for 415, and 1 strawberry for 160; buys land** | Jayveer's cumulative revenue lead becomes durable: +3,248 overall and +7,096 from crops. |
| Day 11 h2–h3 | Buys feed | Buys 1 sheep and **6 cows**, plus feed | The crop wave immediately finances the next compounding asset layer. |
| Days 12–20 | About 4–6 melon tiles and 36–41 strawberry tiles | About 13 melons, 34 strawberries, and 13 wheat | Jayveer preserves a much higher-value crop portfolio throughout midgame. |

The second compounding difference is realized crop value. Full-game crop
revenue is **69,839 vs 39,965**. Jayveer earns 19,832 from melons and 40,077
from strawberries; we earn 7,886 and 26,847. Our animal revenue is higher
(42,968 vs 35,424), so livestock does not repair the crop gap.

The third difference is replacement continuity. In day 10–20 the frozen agent
has 23.0-turn average replant delay, versus 2.5 across the top corpus. Jayveer's
own exact-trace replant delay is 6.7 turns. Jayveer is not simply taking more
crop actions; it creates higher-value cohorts and gets replacement capital back
onto tiles much sooner.

## 2. Why Pedro still beats the frozen agent

Pedro's reported “crop revenue” is mostly a market inventory cycle. Treating it
as farm output was the earlier analytical error.

- The durable revenue lead begins around **day 6 hour 0**, and exceeds 2,500 by
  day 7.
- Day 7 h0: Pedro sells 12 wool for 2,178 plus fertilizer, then buys land at
  h1 and one sheep/one cow at h2.
- Beginning at h2, Pedro repeatedly buys roughly 12–20 wheat and sells it on
  the following turn. On day 10 this becomes an almost continuous 18–19 unit
  alternating cycle.
- Day 9 h0: 12 milk realizes 1,881; another cow is purchased at h1.
- Day 10 h0: Pedro sells 28 wheat plus wool/fertilizer, buys land at h1, and
  resumes the alternating wheat cycle.

Across the full replay Pedro buys **3,066 wheat for 126,975** and sells **3,206
wheat for 133,609**. The 6,634 spread is close to the final 4,509-coin
advantage. Pedro also harvests 379 wheat units, so the extra sold quantity is
not pure arbitrage, but the alternating market mechanism is economically
material.

The replay-faithful local copy falsified blind transfer. It raised measured crop
“revenue” from 41.5k to 210.5k through turnover but improved final money only
426 and worsened aggregate advantage to -7,278. On the six-cow value branch it
lost about 1.8k relative to the same agent without the loop. Competing with
Pedro for the same inventory curve and disrupting feed/cash timing removes the
observed benefit.

## 3. Reverse-engineering the top crop machine

### Crop allocation

| Day | Frozen melon / strawberry / wheat | Top mean melon / strawberry / wheat |
| ---: | ---: | ---: |
| 10 | 2.0 / 31.5 / 12.5 | **11.1 / 30.2 / 13.0** |
| 11 | 6.5 / 33.0 / 9.0 | **13.0 / 34.2 / 13.0** |
| 15 | 5.0 / 36.0 / 8.5 | **13.2 / 34.2 / 13.0** |
| 19 | 4.0 / 41.5 / 13.5 | **13.2 / 31.3 / 15.9** |
| 20 | 4.0 / 39.5 / 14.0 | **2.1 / 31.3 / 25.8** |
| 23 | 0 / 36.0 / 21.5 | **0 / 16.5 / 42.1** |
| 26 | 0 / 25.0 / 31.5 | **0 / 3.9 / 56.2** |

The shared top pattern is a 13-melon block through day 19, then a sharp wheat
replacement wave. The frozen agent is strawberry-heavier, carries too few
midgame melons, and completes the late wheat transition much more slowly.

### Cohorts and cadence

| Metric | Frozen exact losses | Top 35 appearances |
| --- | ---: | ---: |
| Crop harvest actions, day 10–20 | 84.5 | **104.5** |
| Full crop revenue | 41,314 | **61,224** |
| Critical watering misses, day 10–20 | 1.84% | **0.24%** |
| Average replant delay | 23.0 turns | **2.5 turns** |
| Movement per crop cycle | 13.36 | **9.31** |
| Median planting cohort | 3 tiles | **8 tiles** |
| Largest connected cohort fraction | 53.4% | **68.7%** |
| Quadrant crossings | 237 | **165** |

The remaining ~122→147 all-harvest gap is therefore mainly replacement
continuity plus crop value, not raw worker count. Top agents plant larger,
contiguous cohorts and replace cleared one-time crops nearly immediately. Their
average harvest delay is actually worse (14.6 vs 12.6 turns), so “harvest every
mature tile sooner” is not the missing universal rule.

## 4. Predictive positioning, territories, and logistics

Top agents do modestly pre-position: 13.47% of measured approaches versus
11.34% for the frozen exact losses. That 2.1-point gap is real but small.
Bounded predictive positioning changed exact-loss money by only **+24** and did
not move the lifecycle metrics. Reactive routing is not the main remaining
bottleneck.

Static territories are not yet too rigid. Urgent adjacent help added about 515
coins in the tiny exact screen, but only 14 coins when combined with the strong
six-cow/value branch there and 46 coins in the large held-out average. It also
slightly worsened Jayveer. Locality should remain the default.

Inventory logistics is not an explanatory gap:

- logistics tax: **10.40% ours vs 11.11% top**;
- loaded shed-directed moves: 533.5 ours vs 545.1 top;
- shed entries: 87.5 ours vs 72.3 top;
- seeds are global private inventory, so literal seed retrieval/carrying trips
  do not exist in this environment.

Our 43% excess quadrant crossings are meaningful, but the controlled adjacent
and predictive changes did not turn them into reliable money. No B4 logistics
candidate was built because the measurement did not justify extra complexity.

## 5. Isolated ablations

The first table is the fixed-shop Jayveer/Pedro screen (four games per row,
both seats). “Harvests” is crop harvest actions over days 10–29; market-loop
revenue is deliberately called out as turnover.

| Variant | W/L/T | Avg money | Own delta vs B0 | Harvests | Crop revenue | Critical miss |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| B0 frozen-copy control | 0/4/0 | 60,161 | — | 237.8 | 41,522 | 2.01% |
| B1 action-value scheduler | 0/4/0 | 61,095 | +934 | 228.2 | 41,847 | 1.58% |
| B2 predictive positioning | 0/4/0 | 60,184 | +24 | 237.8 | 41,545 | 2.01% |
| B3 adjacent help | 0/4/0 | 60,676 | +515 | 240.5 | 42,039 | 2.01% |
| B5 corrected replay crop phase | 0/4/0 | 59,289 | **-872** | 234.0 | 41,656 | 2.10% |
| B6 six cows | 0/4/0 | 67,993 | **+7,832** | 254.2 | 46,280 | 1.17% |
| B6 seven cows | 0/4/0 | 65,140 | +4,979 | 248.8 | 44,373 | **0.74%** |
| B6 eight cows | 0/4/0 | 61,331 | +1,170 | 236.8 | 42,226 | 1.92% |
| B7 six cows + value | **2/2/0** | **69,422** | **+9,261** | **259.5** | **47,648** | **0.61%** |
| B7 + adjacent help | 2/2/0 | 69,436 | +9,275 | 259.5 | 47,662 | 0.61% |
| Pedro two-turn market loop | 0/4/0 | 60,587 | +426 | 232.8 | 210,512 turnover | 1.39% |

The strongest isolated architectural scheduler change is B1. On six cows it
adds about 1.4k own money, five crop harvests, 1.4k crop revenue, reduces
critical misses from 1.17% to 0.61%, and reduces replant delay from 16.4 to
12.6 turns. The largest overall mechanism is nevertheless B6: **nine cows are
stealing too much worker and feed capacity from crops**.

## 6. Cow opportunity cost

The final held-out control/candidate decomposition makes the trade explicit.

| Metric | Nine-cow B0 | Six-cow/value candidate | Delta |
| --- | ---: | ---: | ---: |
| Crop revenue | 49,050 | 55,231 | **+6,181** |
| Animal revenue | 69,272 | 62,630 | -6,642 |
| Animal service actions | 1,117 | 965 | **-152** |
| Market wheat/feed spending | 5,527 | 4,610 | **-917** |
| Animal purchase spending | 5,694 | 4,400 | **-1,294** |
| Seed spending | 6,860 | 6,983 | +123 |
| Crop harvests, day 10–29 | 233.9 | **255.5** | **+21.6** |
| Critical miss, day 10–20 | 1.51% | **0.63%** | -0.88 pp |
| Replant delay, day 10–20 | 25.0 | **11.4** | -13.6 turns |

The candidate does not generate more total sales revenue; it substitutes crop
revenue for animal revenue. Its final-money gain comes from avoiding cow
capital and feed costs while using 152 service actions on crop work. This is a
real mechanism, but its value depends heavily on the shared milk/crop markets.

## 7. Controlled crop-phase result

The top phase schedule is descriptive, not independently transferable. The
first B5 implementation was found to be overridden outside NW by the historical
new-land allocator; it was corrected and rerun with `inherit` allocation from
day 11. The corrected B5 lost 872 coins. On six cows, replay phasing improved
only 3,484 over B0, versus 7,832 for six cows without it and 9,261 for
six-cow/value scheduling.

The failure mechanism is shared-market realization: earlier wheat replacement
enters already depressed wheat markets in the Jayveer/Pedro traces, while the
extra melon block cannot recreate the top agents' day-0 capital cohort after
day 10. Copying the tile ratios without the preceding capital and market state
is not equivalent to copying the top production machine.

## 8. Selection and held-out results

Selection used 28 games per candidate: four exact losses, fresh direct games,
and the replay-derived pool. The six-cow/value branch looked strong there:
26/2, +7,360 real-transfer delta, positive P10, and 6/0 directly.

The completely fresh hard held-out set reversed that confidence.

| Candidate | Games | W/L/T | Avg money | Avg advantage | Overall P10 | Own money delta vs B0 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| B0 frozen-copy | 102 | 84/14/4 | 93,177 | +33,715 | 0 | — |
| Six cows + value | 102 | 83/19/0 | 94,804 | +35,661 | **-924** | **+1,627 (+1.7%)** |
| + adjacent help | 102 | 85/17/0 | 94,850 | +35,699 | -636 | +1,673 (+1.8%) |

The guarded final branch repeats the six-cow/value result over all 102 games
with **zero runtime failures, zero semantic failures, zero invalid actions,
zero livestock losses, and zero stranded value**.

### Final guarded matchup evidence

| Group or matchup | W/L/T | Avg advantage | Own-money delta vs B0 |
| --- | ---: | ---: | ---: |
| Jayveer | 0/2/0 | **-2,599** | +10,504 |
| Pedro | **2/0/0** | **+1,680** | +8,018 |
| Lucas | 2/0/0 | +6,204 | **-5,576** |
| Alexander | 2/0/0 | +11,499 | +6,701 |
| Direct current best | **7/9/0** | +892 | +1,571 |
| Replay-derived pool | 42/0/0 | +39,318 | +2,945 |
| Hard pool | 28/8/0 | +53,838 | **-617** |
| New Jay-wave adversary | 2/4/0 | +2,389 | +3,595 |
| New Pedro-trader adversary | 2/4/0 | +2,357 | +3,908 |

The new adversaries break the candidate in win/loss terms even though it keeps
a positive average advantage: both have negative lower tails, and the hard
high-labor/land/livestock subset makes less own money than B0. The weakest
real matchup remains Jayveer.

## 9. RNG-coupling audit

Sixteen fresh seed/seat pairs were run twice against the current best: once
with an independently fixed common shop schedule and once with natural engine
RNG.

| Shop control | B0 avg money | Guarded candidate avg money | Paired own-money delta | Candidate direct W/L/T |
| --- | ---: | ---: | ---: | ---: |
| Fixed schedule | 72,040 | 75,056 | **+3,015** | 10/6/0 |
| Natural coupled RNG | 78,948 | 75,935 | **-3,013** | 6/10/0 |

The sign reversal proves that part of the apparent local improvement is
RNG-coupling, not a stable strategy effect. Candidate advantage remains
positive because the shared market also changes the opponent's money; that is
a market-interaction effect, not a reliable own-economy gain.

## 10. Answers to the research questions

1. **Why Jayveer?** A 42-melon/10,188-coin day-11 wave funds land and six cows;
   higher-value cohorts and much faster replacement then compound.
2. **Why Pedro?** A real wheat-inventory market cycle contributes about 6.6k,
   funded by wool/milk milestones. It is not farm crop revenue.
3. **What explains the harvest gap?** Replant continuity, larger contiguous
   cohorts, lower movement per cycle, fewer maintenance misses, and a
   higher-value melon/wheat phase—not nominal hand count.
4. **Predictive positioning?** Present weakly in top paths, but the controlled
   lookahead is effectively neutral.
5. **Static territories too rigid?** Not at current scale; adjacent help is
   negligible and slightly harms Jayveer.
6. **Inventory/logistics tax?** Ours is not higher than top. Seed retrieval is
   not a real operation in this environment.
7. **Are nine cows excessive?** Yes in the exact losses; six is the strongest
   controlled load. The benefit becomes only 1.7% in the full held-out pool.
8. **Crop phase wrong?** Descriptively yes, but copying the observed phase alone
   loses money because capital history and shared markets differ.
9. **Largest isolated architecture improvement?** Six-cow capacity recovery;
   the action-value scheduler is the largest scheduling improvement on top.
10. **What looked good but failed?** Replay crop phasing, predictive routing,
    adjacent help, and Pedro's market loop. The six-cow/value branch also fell
    from +7.4k selection to +1.6k held-out.
11. **What broke the finalist?** Direct current-best games, the new Jay/Pedro
    economic adversaries, and high-labor/land hard-pool seeds; RNG coupling
    reverses its own-money delta.
12. **Strongest final research agent?**
    `agents/epic_b8_capacity_value_guarded.py`.
13. **Improvement over frozen?** +1,627 own money (+1.7%) in the 102-game
    held-out set; +21.6 day-10–29 crop harvests, +6.2k crop revenue, but -6.6k
    animal revenue and no overall worker-turn revenue-efficiency gain.
14. **Jayveer/Pedro?** Pedro becomes 2/0; Jayveer narrows from -9,280 to -2,599
    but remains 0/2.
15. **Ready for Kaggle?** **No.** It misses the 10%/5,000 promotion bar, has
    negative P10, loses direct 7/9, regresses own money on the hard pool, and
    reverses under natural RNG coupling.

## Artifacts

- `experiments/epic_next_stage_diagnosis.json`
- `experiments/epic_isolated_screen.json`
- `experiments/epic_combination_screen.json`
- `experiments/epic_crop_phase_corrected_screen.json`
- `experiments/epic_selection.json`
- `experiments/epic_heldout.json`
- `experiments/epic_guarded_heldout.json`
- `experiments/epic_rng_audit.json`
- `experiments/epic_pedro_market_screen.json`
- `experiments/epic_next_stage_results.json`

The most useful next research direction is not another router parameter sweep.
It is a controlled capital-aware crop-cohort planner that can create the
day-10/11 melon wave from the opening without increasing animal service load,
then choose the wheat transition from expected realized market value rather
than copying a fixed public calendar.
