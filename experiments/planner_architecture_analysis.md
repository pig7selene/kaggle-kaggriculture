# Opponent-aware full-farm planner milestone

## Decision

No candidate is promoted. The frozen
`agents/animal_c2_land_day14_adaptive.py` control remains the robust best.
The strongest new architecture is P3 (full-farm marginal crop planning plus
visible-opponent and self-market-impact forecasts), but it regresses on fresh
held-out seeds.

The experiment generated 36 adversarial strategies, retained the 12 hardest,
and evaluated against a permanent league of 26 opponents (14 historical plus
12 generated). All matchups used both seats. Seed partitions were disjoint:

- adversarial discovery: 10000–10003
- component development: 10020–10051
- architecture search: 10060–10061
- final held-out confirmation: 10100–10104

## P0–P7 architecture search

This stage used 104 games per candidate (26 opponents × two seeds × both
seats). P4 retained synchronized planting because S0 won the cohort ablation;
P6 retained four fixed cows because dynamic allocation lost; P7 retained one
quadrant because no conditional second purchase passed its gate. Consequently,
P3/P4 and P5/P6/P7 are behaviorally identical in this stage.

| Candidate | W/L/T | Avg money | Avg advantage | Median | P10 | P5 | Money variance | Worst opponent |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| P0 current best | 80/22/2 | 47015.6 | +13995.9 | +7386.0 | +13724.3 | +13690.4 | 32504997.2 | gen_land_d8_labor6_sell0 |
| P1 full-farm planner | 64/40/0 | 41919.5 | +8627.5 | +3782.5 | +8499.6 | +8483.6 | 19219406.6 | gen_land_d11_labor7_sell12 |
| P2 + opponent forecast | 76/28/0 | 45472.0 | +12469.5 | +4611.5 | +11594.1 | +11484.7 | 33763144.0 | gen_cow6_d8 |
| P3 + self impact | 85/19/0 | 46288.4 | +12527.0 | +7059.0 | +11979.6 | +11911.2 | 35031169.3 | gen_land_d8_labor6_sell0 |
| P4 + cohort search winner | 85/19/0 | 46288.4 | +12527.0 | +7059.0 | +11979.6 | +11911.2 | 35031169.3 | gen_land_d8_labor6_sell0 |
| P5 + forecast selling | 83/21/0 | 46300.6 | +12448.3 | +7056.0 | +11871.4 | +11799.3 | 35757784.5 | gen_land_d8_labor6_sell0 |
| P6 + animal search winner | 83/21/0 | 46300.6 | +12448.3 | +7056.0 | +11871.4 | +11799.3 | 35757784.5 | gen_land_d8_labor6_sell0 |
| P7 + land search winner | 83/21/0 | 46300.6 | +12448.3 | +7056.0 | +11871.4 | +11799.3 | 35757784.5 | gen_land_d8_labor6_sell0 |

## Distinct held-out finalists

Each finalist received 260 games (26 opponents × five fresh seeds × both
seats). The selector canonicalized default configuration values so duplicate
P4 did not displace the distinct P5 finalist.

| Candidate | W/L/T | Win rate | Avg money | Avg advantage | Median | P10 | P5 | Money variance | Direct vs P0 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| **P0 current best** | **215/43/2** | **82.7%** | **47776.7** | **+14340.9** | **+9696.5** | **+14104.1** | **+14047.1** | **28667801.5** | 4/4/2, +0.0 |
| P3 self-impact planner | 202/58/0 | 77.7% | 46539.0 | +12120.8 | +7416.0 | +11601.7 | +11566.8 | 37013029.1 | 2/8/0, -1100.5 |
| P5 forecast selling | 197/63/0 | 75.8% | 46557.7 | +12068.4 | +7464.5 | +11505.6 | +11455.2 | 37394500.6 | 1/9/0, -1108.4 |

P3 loses 1237.7 average coins (-2.59%) versus P0. P5 loses 1219.0
(-2.55%). Neither comes close to the +15% average-money or +5000 direct
head-to-head promotion bar.

### Held-out economic decomposition

| Metric | P0 | P3 | P5 |
| --- | ---: | ---: | ---: |
| Productive tiles | 17.62 | 17.61 | 17.61 |
| Labor cost | 220.0 | 219.6 | 219.6 |
| Wheat revenue | 2733.8 | 3003.8 | 5426.3 |
| Carrot revenue | 111.5 | 120.2 | 120.4 |
| Tomato revenue | 0.0 | 81.7 | 77.7 |
| Strawberry revenue | 11436.9 | 10640.6 | 10657.8 |
| Melon revenue | 16597.7 | 15794.1 | 15774.0 |
| Animal-product revenue | 17985.1 | 17930.5 | 17955.9 |
| Fertilizer revenue | 5690.1 | 5638.6 | 5639.4 |
| Land ROI | 0.893 | 0.747 | 0.747 |
| Modeled self market impact | 2502.9 | 2286.9 | 2290.1 |
| Inventory holding turns | 46.3 | 48.9 | 67.6 |

The planner reduced modeled self impact by about 216 coins, but it was too
conservative: lower strawberry and melon revenue more than erased the benefit.
Forecast selling held inventory about 19 turns longer than P3 and added only
18.7 average coins, while worsening W/L and direct results.

Worst five held-out opponents:

- P0: gen_land_d11_labor7_sell12, gen_land_d8_labor6_sell0, gen_cow6_d8,
  the identical P0 control, gen_land_d14_labor5_sell24.
- P3: gen_land_d11_labor7_sell12, gen_land_d8_labor6_sell0, gen_cow6_d8,
  P0, gen_cow4_d11.
- P5: gen_land_d11_labor7_sell12, gen_land_d8_labor6_sell0, P0,
  gen_cow6_d8, gen_land_d14_labor5_sell24.

P0's strongest matchup was proxy_land_expander (10/0, +52981.9). Its worst
record was gen_land_d11_labor7_sell12 (0/10, -2807.4); its largest monetary
loss was gen_cow6_d8 (2/8, -3486.0).

## Component ablations

- **Opponent forecast was the largest planner improvement:** P1 to P2 gained
  3552.5 average money in architecture search. Self-impact modeling added a
  further 816.4. The full planner itself remained below P0.
- **Cohorts:** S0 synchronized scored 47531.0 average money and +7017.4
  advantage. S1/S2/S3/S4 scored 41489.0/41167.0/38188.8/40786.9. Staggering
  created too much idle-tile time and delayed high-value harvests for this
  routing/labor engine.
- **Selling:** planner-selected horizon led development by 88.0 coins over
  immediate selling, but the held-out incremental gain was only 18.7 coins and
  came with worse downside.
- **Animals:** fixed four cows remained the robust winner (+7538.7 average
  advantage, +7511.2 P10). A 2-cow/2-sheep mix earned more average money but
  had lower advantage and P10; the dynamic selector, sheep, geese, 0/2/6-cow
  variants all lost.
- **Second land:** all four conditional variants converged to the one-quadrant
  control. Their bank/ROI gates correctly declined every second purchase.

## Adversarial discovery and remaining exploit

The automatically generated search found three strategies that reliably beat
P0 during discovery:

| Generated opponent | Discovery W/L/T vs P0 | Avg advantage over P0 | Held-out P0 result |
| --- | ---: | ---: | ---: |
| gen_cow6_d8 | 8/0/0 | +4530.9 | P0 2/8, -3486.0 |
| gen_land_d11_labor7_sell12 | 8/0/0 | +3672.4 | P0 0/10, -2807.4 |
| gen_land_d8_labor6_sell0 | 8/0/0 | +2738.4 | P0 1/9, -2441.3 |

The obvious remaining exploit is capital/scale timing. P0 always commits to
four day-11 cows, one day-14 quadrant, and a relatively synchronized crop
economy. Six early cows, or earlier land combined with six/seven-worker scale
and coordinated selling, compounds faster than P0. The new crop planner did
not close this gap; it lost even more heavily to those three adversaries.

## Promotion and submission decision

- strongest robust candidate: unchanged P0
- strongest new candidate: P3, but below P0
- promotion: no
- `experiments/current_best.json`: unchanged
- `submission/main.py`: unchanged
- Kaggle submission: not justified and not prepared

All final candidates recorded zero runtime failures, zero invalid actions, and
zero stranded endgame value.
