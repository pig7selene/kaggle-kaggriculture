# Kaggriculture Experiment Log

## baseline_carrot_v1

- **Agent:** `agents/baseline_carrot.py`
- **Strategy:** One farmer maintains four carrot plots near the NW shed tile. It
  buys only enough seeds for those plots, prioritizes watering, harvests at age
  three, clears plot weeds, safely replants, and sells carrots from the shed.
- **Benchmark:** Quick suite, 100 games over fixed seeds, with both player
  positions per seed: 80 games against `starter` and 20 against the deterministic
  seeded equivalent of the bundled `random` agent.
- **Result artifact:** `experiments/baseline_carrot_v1_quick.json`
- **New best:** Yes — this is the initial recorded benchmark.

| Opponent | Games | Wins | Losses | Ties | Win rate | Avg money | Median money | Avg opponent | Avg advantage | Min money | Max money |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| starter | 80 | 80 | 0 | 0 | 100.00% | 5907.75 | 5984.00 | 3409.70 | +2498.05 | 5187.00 | 6607.00 |
| random | 20 | 20 | 0 | 0 | 100.00% | 6218.40 | 6329.00 | 53.00 | +6165.40 | 5418.00 | 6613.00 |
| **overall** | **100** | **100** | **0** | **0** | **100.00%** | **5969.88** | **6266.00** | **2738.36** | **+3231.52** | **5187.00** | **6613.00** |

## Carrot farm-scale tournament

- **Shared strategy:** Carrots only, no land purchases, animals, fertilizer, or
  market prediction. Each worker owns one contiguous block of at most four
  plots and follows the baseline water / peak-harvest / replant loop.
- **Labor policy:** `ceil(plot_count / 4) - 1` hands hired at the start of every
  day, giving 0, 1, 2, 3, 4, and 6 hands for the tested scales.
- **Benchmark:** Each experiment uses seeds 3000–3049 and swaps candidate seats,
  for 100 deterministic head-to-head games per configuration.
- **Promotion rule:** Positive paired-seed average advantage with the lower end
  of its approximate 95% confidence interval above zero.

| Agent version | Plots | Hands/day | Compared with | W/L/T | Win rate | Candidate avg | Best avg | Avg advantage | Median advantage | Paired 95% CI | New best? |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `carrot_scale_04_v1` | 4 | 0 | `baseline_carrot_v1` | 0/0/100 | 0.00% | 5746.62 | 5746.62 | +0.00 | +0.00 | [+0.00, +0.00] | No |
| `carrot_scale_08_v1` | 8 | 1 | `baseline_carrot_v1` | 100/0/0 | 100.00% | 7325.40 | 5237.27 | +2088.13 | +1838.00 | [+1914.69, +2261.57] | **Yes** |
| `carrot_scale_12_v1` | 12 | 2 | `carrot_scale_08_v1` | 100/0/0 | 100.00% | 7905.77 | 6371.19 | +1534.58 | +1393.50 | [+1391.50, +1677.66] | **Yes** |
| `carrot_scale_16_v1` | 16 | 3 | `carrot_scale_12_v1` | 100/0/0 | 100.00% | 7003.24 | 6166.93 | +836.31 | +743.50 | [+755.81, +916.81] | **Yes** |
| `carrot_scale_20_v1` | 20 | 4 | `carrot_scale_16_v1` | 100/0/0 | 100.00% | 6343.21 | 5825.01 | +518.20 | +423.50 | [+439.59, +596.81] | **Yes** |
| `carrot_scale_25_v1` | 25 | 6 | `carrot_scale_20_v1` | 31/69/0 | 31.00% | 4873.28 | 4923.44 | -50.16 | -102.00 | [-118.42, +18.10] | No |

Result artifacts are stored as `experiments/carrot_scale_*_quick.json`; the
tournament roll-up is `experiments/scaling_summary_quick.json`. The current best
after this phase is **`carrot_scale_20_v1`**.

## Carrot scale full round robin

- **Agents:** Frozen 4-, 8-, 12-, 16-, 20-, and 25-plot scale agents from the
  preceding tournament; no strategy files were changed.
- **Benchmark:** All 15 distinct pairs, 200 games per matchup using seeds
  4000–4099 in both player positions; 3,000 games total.
- **Ranking method:** Full-pool robustness: Copeland matchup score, then
  worst-matchup score rate, overall score rate, and average money advantage.
- **Result artifacts:** `experiments/scaling_round_robin_200.json` and
  `experiments/scaling_round_robin_200.md`.
- **New best:** `carrot_scale_20_v1` is retained and independently confirmed as
  the robust best. It is the only agent that wins every matchup.

### Win-rate matrix

Rows are focal agents and columns are opponents.

| Scale | 4 | 8 | 12 | 16 | 20 | 25 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | — | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| 8 | 100.0% | — | 0.0% | 0.0% | 0.0% | 0.0% |
| 12 | 100.0% | 100.0% | — | 0.0% | 0.0% | 0.0% |
| 16 | 100.0% | 100.0% | 100.0% | — | 0.0% | 16.5% |
| **20** | **100.0%** | **100.0%** | **100.0%** | **100.0%** | — | **70.0%** |
| 25 | 100.0% | 100.0% | 100.0% | 83.5% | 30.0% | — |

### Robustness ranking

| Rank | Agent | Total W/L/T | Overall win rate | Avg money | Avg advantage | Matchups W/L/T | Worst matchup | Best matchup |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 1 | `carrot_scale_20` | 940/60/0 | 94.00% | 7308.27 | +2034.86 | 5/0/0 | scale 25: 70.0%, +62.34 | scale 4: 100%, +5266.01 |
| 2 | `carrot_scale_25` | 827/173/0 | 82.70% | 6785.61 | +1866.54 | 4/1/0 | scale 20: 30.0%, -62.34 | scale 4: 100%, +4610.42 |
| 3 | `carrot_scale_16` | 633/367/0 | 63.30% | 7225.95 | +1348.51 | 3/2/0 | scale 20: 0.0%, -522.12 | scale 4: 100%, +4425.55 |
| 4 | `carrot_scale_12` | 400/600/0 | 40.00% | 6758.15 | +303.67 | 2/3/0 | scale 20: 0.0%, -1439.67 | scale 4: 100%, +3739.05 |
| 5 | `carrot_scale_08` | 200/800/0 | 20.00% | 5994.63 | -1505.13 | 1/4/0 | scale 20: 0.0%, -2884.16 | scale 4: 100%, +2201.25 |
| 6 | `carrot_scale_04` | 0/1000/0 | 0.00% | 4764.40 | -4048.46 | 0/5/0 | scale 20: 0.0%, -5266.01 | scale 8: 0.0%, -2201.25 |

No directed three-agent non-transitive cycles were detected. The scale-20 vs
scale-25 matchup is the closest: 140–60 with +62.34 average advantage for scale
20; its paired-seed mean advantage has an approximate 95% confidence interval
of [+15.83, +108.84].

## Pure-melon crop and scale experiment

- **Agent family:** Melons only on the original NW route, with no land,
  animals, fertilizer, crop rotation, or market prediction. Workers still own
  fixed blocks of at most four plots, prioritize daily watering, and sell shed
  inventory immediately.
- **Lifecycle:** Seeds cost 80 coins. Melons are watered every day and harvested
  at age 10, after watering ages 6–10 has filled the unfertilized six-unit yield
  cap; empty plots are then replanted except on the final turn of a day.
- **Labor:** `ceil(plot_count / 4) - 1` hands per day, matching the carrot scale
  experiments. The initial 20-plot crop test therefore hires four hands daily.
- **Fixed seeds:** Initial crop gate uses 6000–6099; matched starter benchmarks
  use 6100–6199; the melon round robin uses 6200–6249; final confirmation uses
  6300–6399. Every seed is played in both player positions.
- **Current-best files:** `agents/carrot_scale_20.py`, its shared strategy, the
  best-agent registry, and the submission were not modified.

### Crop-choice gate and matched absolute income

| Agent | Opponent | Games | W/L/T | Win rate | Avg money | Opponent avg | Avg advantage | Median advantage | Paired advantage 95% CI |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `melon_scale_20_v1` | `carrot_scale_20_v1` | 200 | 200/0/0 | 100.00% | 29302.00 | 10498.91 | +18803.10 | +19301.00 | [+18378.36, +19227.83] |
| `melon_scale_20_v1` | starter | 200 | 200/0/0 | 100.00% | 29302.00 | 3487.23 | +25814.77 | +25812.00 | n/a |
| `carrot_scale_20_v1` | starter | 200 | 200/0/0 | 100.00% | 10531.93 | 3206.70 | +7325.24 | +6765.00 | n/a |

The melon-20 crop-choice gate is a reliable improvement, so the requested
8/12/16/20/25 plot sweep was run. Raw artifacts:

- `experiments/melon_scale_20_vs_carrot_scale_20_200.json`
- `experiments/melon_scale_20_vs_starter_200.json`
- `experiments/carrot_scale_20_vs_starter_matched_200.json`

### Pure-melon scale round robin

All ten scale pairs received 100 games (50 seeds × both seats), for 1,000 games
total.

| Rank | Agent | Total W/L/T | Win rate | Avg money | Avg advantage | Matchups W/L/T |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | `melon_scale_12_v1` | 400/0/0 | 100.00% | 15239.25 | +1609.75 | 4/0/0 |
| 2 | `melon_scale_16_v1` | 300/100/0 | 75.00% | 14983.25 | +1971.25 | 3/1/0 |
| 3 | `melon_scale_20_v1` | 200/200/0 | 50.00% | 13978.50 | +762.50 | 2/2/0 |
| 4 | `melon_scale_25_v1` | 100/300/0 | 25.00% | 12418.50 | -1187.50 | 1/3/0 |
| 5 | `melon_scale_08_v1` | 0/400/0 | 0.00% | 13432.25 | -3156.00 | 0/4/0 |

`melon_scale_12_v1` won every individual scale matchup. Its narrowest result
was still 100–0 against scale 16, with +17.00 average money advantage. No
directed three-agent cycles were detected. Complete artifacts:

- `experiments/melon_scaling_round_robin_100.json`
- `experiments/melon_scaling_round_robin_100.md`

### Winning scale confirmation

| Agent | Opponent | Games | W/L/T | Win rate | Avg money | Opponent avg | Avg advantage | Median advantage | Paired advantage 95% CI |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `melon_scale_12_v1` | `carrot_scale_20_v1` | 200 | 200/0/0 | 100.00% | 29869.00 | 10958.61 | +18910.38 | +19843.00 | [+18386.93, +19433.84] |
| `melon_scale_12_v1` | starter | 200 | 200/0/0 | 100.00% | 29869.00 | 3489.41 | +26379.59 | +26377.00 | n/a |

- **Strongest pure-melon configuration:** `melon_scale_12_v1` (12 plots, two
  hands per day).
- **New best:** Reliable experimental winner, but not automatically promoted;
  `experiments/current_best.json` remains unchanged and no Kaggle submission
  was made.
- **Confirmation artifacts:**
  `experiments/melon_scale_12_vs_carrot_scale_20_200.json` and
  `experiments/melon_scale_12_vs_starter_matched_200.json`.

## Melon scale 12 promotion and submission preparation

- **Promoted version:** `melon_scale_12_v1`.
- **Current-best registry:** `experiments/current_best.json` now points to
  `agents/melon_scale_12.py` and retains the melon round robin as its selection
  evidence.
- **Submission artifact:** `submission/main.py` was replaced with a standalone
  copy of the 12-plot melon strategy. It imports only Python's standard
  `math` module and has no dependency on repository agent files.
- **Exact configuration audit:** 12 melon plots on the established NW route,
  three four-plot worker assignments (main farmer plus two hired hands), melon
  seed cost 80, harvest age 10 after daily watering, immediate shed selling,
  no land purchases, animals, or fertilizer.
- **Full-season verification:** Three checked 720-turn games used seeds
  7101–7103 against starter, random, and `carrot_scale_20_v1`. Every game ended
  with both players in `DONE` status. The standalone agent matched
  `agents/melon_scale_12.py` action-for-action, emitted semantically valid
  actions, hired exactly two hands on every day, and planted exactly the 12
  target plots.
- **Kaggle submission:** Not submitted automatically.

## Adaptive economy and replay-backed pool

- **Evidence read:** Full `README.md`, all existing experiment reports, the
  complete episode-analysis JSON/Markdown, manifest, and action schedules from
  all three downloaded replays were inspected before strategy changes.
- **Evaluation pool:** Frozen melon-12 plus seven proxies for melon-heavy,
  phased rotation, aggressive land, inventory holding, mixed crops,
  crop/livestock, and high-labor scaling. See
  `experiments/adversarial_pool.md`.
- **Architecture:** `agents/economic_common.py` provides market-impact crop
  scoring, opponent-visible harvest forecasting, town-demand modeling,
  lifecycle-aware planting, inventory-aware selling, ROI-gated land, dynamic
  labor, optional livestock operations, and forced endgame liquidation.
- **Controlled branches:** `adaptive_a_crop`, `adaptive_b_selling`,
  `adaptive_c_phased`, `adaptive_d_land_labor`, `adaptive_e_crop_selling`, and
  `adaptive_f_full`, plus an engine control and search-derived G/H variants.
- **Final benchmark:** Seeds 8000–8015, both seats, eight opponents, 256 games
  per serious candidate. Final frozen-engine artifacts are:
  `adaptive_pool_frozen_engine_confirmation_16_seeds.json`,
  `adaptive_pool_endgame_fix_confirmation_16_seeds.json`,
  `adaptive_d_land_labor_confirmation_16_seeds.json`, and
  `adaptive_f_controlled_confirmation_16_seeds.json`.

| Candidate | Games | W/L/T | Win rate | Avg money | Avg advantage | P10 seed advantage | Money SD | Worst matchup |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `melon_scale_12` | 256 | 160/64/32 | 62.50% | 18551.26 | +3129.41 | +2727.81 | 3802.05 | livestock 0–32, -19008.22 |
| `adaptive_control` | 256 | 224/32/0 | 87.50% | 19322.93 | +3784.34 | +3426.62 | 3665.72 | livestock 0–32, -17960.06 |
| `adaptive_a_crop` | 256 | 224/32/0 | 87.50% | 25155.40 | +6564.82 | +6056.44 | 2790.94 | livestock 0–32, -14955.38 |
| `adaptive_b_selling` | 256 | 224/32/0 | 87.50% | 19328.23 | +3789.66 | +3431.88 | 3661.24 | livestock 0–32, -17959.50 |
| **`adaptive_c_phased`** | **256** | **224/32/0** | **87.50%** | **28004.63** | **+11599.96** | **+11233.44** | **2401.40** | **livestock 0–32, -8125.41** |
| `adaptive_d_land_labor` | 256 | 132/124/0 | 51.56% | 13898.42 | -677.20 | -1072.81 | 5049.00 | livestock 0–32, -28080.53 |
| `adaptive_e_crop_selling` | 256 | 224/32/0 | 87.50% | 25155.40 | +6564.82 | +6056.44 | 2790.94 | livestock 0–32, -14955.38 |
| `adaptive_f_full` | 256 | 206/50/0 | 80.47% | 24147.21 | +3696.08 | +2643.56 | 4462.66 | livestock 0–32, -16924.50 |
| `adaptive_g_tuned` | 256 | 224/32/0 | 87.50% | 25232.73 | +6723.08 | +6346.25 | 2864.29 | livestock 0–32, -14949.81 |
| **`adaptive_h_hybrid`** | **256** | **224/32/0** | **87.50%** | **26109.72** | **+7344.73** | **+6845.09** | **2797.07** | **livestock 0–32, -13669.62** |

### Parameter search

- **Main grid:** 24 variants × five opponents × four seeds × both seats = 960
  games. Phase-aware adaptive scoring ranked first.
- **Selling/land extension:** 200 games. Withholding to 110–120% of base price
  hurt; day-14 land beat day-11 land but remained below no-land play.
- **Phase-bias grid:** 480 games. Strawberry bias 2.00 with melon penalty 0.70
  ranked first.
- **Hybrid override grid:** 200 games. A 1.30× alternative-profit override won.
- **Artifacts:** `experiments/adaptive_parameter_search*.json`.

### Findings and decision

- Fixed phased rotation is the strongest robust local candidate. It gains
  +8681.70 average money over the shared-engine fixed-melon control.
- `adaptive_h_hybrid` is the strongest genuinely adaptive candidate; it gains
  +876.99 average money over the phase-weighted adaptive G variant.
- Adaptive crop selection is the largest adaptive component (+5832.47 average
  money over control). Selling alone adds only +5.30. Land/labor is harmful in
  both isolation and combination and materially raises variance.
- A semantic audit found and fixed final-day inventory stranding. The final
  `test_economic_agents.py` run passed every candidate/proxy with no valuable
  candidate inventory left unsold.
- **New best:** No promotion. Every serious candidate loses all 32 games to the
  replay-inspired livestock/crop proxy; the evidence is not strong enough for
  another Kaggle submission.
- **Full report:** `experiments/adaptive_economy_report.md`.

## Livestock economic-compounding milestone

- **Diagnosis first:** `analyze_livestock_economics.py` recorded executed
  transactions for 32 matched `adaptive_c_phased` versus livestock-proxy games
  on seeds 8000–8015. The proxy gained a durable cumulative-income lead on day
  11, economic-position lead on day 18, and bank lead on day 20 in all 32 games.
  Milk plus fertilizer added 22,403 gross coins; after higher capital and
  operating costs, the mean final advantage was +8,125.41.
- **Real replay check:** Hubbahub episode 91705498 was reproduced exactly. Its
  seven placed cows generated 14,361 milk revenue and 10,189 fertilizer
  revenue. After 4,800 of cow purchases and 8,442 of bought wheat, direct
  animal-linked net cash was +11,308. The replay also bought five excess cows,
  so the policy was evidence rather than a template.
- **Controlled files:** `animal_only_geese/cows/sheep.py` isolate animal
  economies. C0–C5 are `animal_c0_phased.py`, `animal_c1_geese.py`,
  `animal_c2_cows.py`, `animal_c3_sheep.py`, `animal_c4_tuned_cows.py`, and
  `animal_c5_adaptive.py`.
- **Search:** 67 type/count/timing configurations, 36
  feed/care/fertilizer/harvest policies, 38 feed/capital/selling variants, and
  25 adaptive-selection variants were evaluated on separate seeds. Four cows
  were strongest; daily feed, daily care, fertilizer collection, two animal
  workers, and a two-day market-wheat reserve were essential. Self-grown and
  mixed feed were inferior to market feed. Geese were weakest, while sheep
  were viable but less robust than cows.
- **Implementation audits:** at-risk animals are fed before additional
  placements, ongoing feed purchases are independent from the new-animal
  payback gate, final animal output is harvested, and the terminal wheat reserve
  is liquidated. `test_economic_agents.py` passed all existing adaptive agents,
  C0–C5, animal-only controls, and proxies with no invalid actions or stranded
  candidate value.
- **Final evaluation:** seeds 8900–8915, both seats, the frozen eight-opponent
  pool plus `adaptive_c_phased`; 288 games per candidate.

| Rank | Candidate | W/L/T | Win rate | Avg money | Avg advantage | P10 advantage | Money SD | Livestock result |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | **`animal_c2_cows`** | **288/0/0** | **100.00%** | **42255.72** | **+24545.59** | **+23328.92** | **4002.35** | **32–0, +6690.59** |
| 2 | `animal_c3_sheep` | 285/3/0 | 98.96% | 39070.25 | +21227.79 | +20428.22 | 2446.62 | 29–3, +3348.31 |
| 3 | `animal_c4_tuned_cows` | 281/7/0 | 97.57% | 47505.35 | +21266.85 | +17407.11 | 7253.43 | 28–4, +5123.28 |
| 4 | `animal_c5_adaptive` | 264/24/0 | 91.67% | 37381.56 | +17906.66 | +16947.69 | 2518.65 | 8–24, -1548.66 |
| 5 | `animal_c1_geese` | 252/36/0 | 87.50% | 29104.65 | +11217.78 | +10501.36 | 2253.83 | 1–31, -7379.22 |
| 6 | `animal_c0_phased` | 228/36/24 | 79.17% | 27907.84 | +10476.38 | +9973.06 | 2246.46 | 0–32, -7398.34 |

- **Component result:** versus unchanged phased crops, `animal_c2_cows` gives
  up 5,205.56 crop-revenue coins but adds 18,261.81 milk and 5,997 fertilizer.
  After cows, feed, and incremental seeds, its net gain is +14,096.59. Direct
  animal cash flow pays back on day 20.
- **New best:** **Yes.** `experiments/current_best.json` now points to
  `agents/animal_c2_cows.py`. It wins every matchup, reverses the livestock gap,
  and retains a +5,238 worst-seed P10 advantage in that matchup.
- **Artifacts:** `experiments/livestock_gap_diagnosis.*`,
  `experiments/animal_parameter_search.json`,
  `experiments/adaptive_animal_selection_search.json`,
  `experiments/animal_pool_final_code_unseen_16_seeds.*`, and
  `experiments/animal_c2_final_economic_decomposition.*`.
- **Submission:** Not prepared or submitted. The evidence supports preparing a
  Kaggle submission in a separate milestone to obtain real-episode validation.
- **Full report:** `experiments/livestock_economy_report.md`.

## C2 cow staged-land expansion

- **Frozen control:** `agents/animal_c2_cows.py`; the no-land shadow in the
  isolated land engine matched it action-for-action for all 719 decisions in a
  full game. Neither the frozen candidate nor `submission/main.py` changed.
- **Architecture:** `agents/animal_land_common.py` preserves the C2 opening,
  four day-11 cows, two-day market-wheat reserve, animal service, selling, and
  endgame behavior. Land is evaluated only after protecting cow/feed capital.
  Each purchase requires a conservative remaining-season estimate with land,
  seed, and incremental labor costs and a projected payback no later than day
  28. New quadrants use explicit targets rather than filling unused NW tiles.
- **Search/confirmation split:** timing seeds 9400–9401, allocation/labor seeds
  9420–9421, scale/ROI seeds 9440–9441, and unseen confirmation seeds
  9600–9612. Every matchup used both seats.

### Controlled timing screen

All land versions initially used one 12-plot quadrant, phased
strawberry-to-wheat allocation, and staged labor.

| Variant | Scheduled policy | Games | W/L/T | Avg money | Avg advantage | P10 | Actual land/day |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| A | no land | 40 | 37/1/2 | 43046.75 | +23110.42 | +22693.05 | 0 |
| B | day 11 | 40 | 40/0/0 | 45650.10 | +25852.45 | +24962.01 | 1 / 11 |
| C | day 14 | 40 | 40/0/0 | 48293.62 | +28140.70 | +26987.58 | 1 / 14 |
| D | day 16 | 40 | 39/1/0 | 44513.03 | +24557.35 | +23926.43 | 1 / ROI-delayed |
| E | day 18 | 40 | 39/1/0 | 44577.70 | +24665.83 | +23948.12 | 1 / ROI-delayed |
| F | cow payback (~day 20) | 40 | 40/0/0 | 44359.80 | +24530.20 | +24069.08 | 1 / 20 |
| G | bank + dynamic ROI | 40 | 40/0/0 | 45650.10 | +25852.45 | +24962.01 | 1 / 11 |

Day 14 was the strongest timing. Day 11 spent growth capital too early, while
days 16–20 left too little productive runway.

### Allocation and labor ablation

The best result for every requested allocation policy used a capacity of four
new-land plots per added hand: three extra hands after expansion, for five
hands (six total units) from day 14 onward. C2's first two units remain reserved
for animal service.

| New-land policy | Games | W/L/T | Avg money | Avg advantage | P10 |
| --- | ---: | ---: | ---: | ---: | ---: |
| adaptive | 24 | 24/0/0 | 50360.25 | +28547.17 | +28523.43 |
| phased strawberry/wheat | 24 | 24/0/0 | 49935.42 | +27747.25 | +27698.45 |
| strawberry-heavy | 24 | 24/0/0 | 49154.42 | +27108.54 | +27099.24 |
| feed-support wheat | 24 | 24/0/0 | 48680.67 | +26536.04 | +26297.61 |
| wheat-heavy | 24 | 24/0/0 | 47872.50 | +25754.17 | +25692.90 |

Allowing two or all three remaining quadrants did not cause additional buys:
the second-quadrant estimate could not repay by day 28. All one/two/three-
quadrant cap variants therefore converged to exactly one purchased quadrant.

### Held-out full-pool confirmation

Thirteen unseen seeds × ten opponents × both seats produced 260 games per
agent. Variance is population money variance.

| Agent | Games | W/L/T | Win rate | Avg money | Avg advantage | P10 | Variance | Avg productive tiles | Avg labor cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **day-14 adaptive land** | **260** | **260/0/0** | **100.00%** | **49723.09** | **+30163.72** | **+27864.18** | **32514648.37** | **17.92** | **220.00** |
| C2 no land | 260 | 239/5/16 | 91.92% | 41792.53 | +21978.24 | +20117.51 | 19506364.00 | 11.78 | 60.00 |

| Key opponent | Expansion W/L/T | Expansion advantage | C2 advantage | Improvement |
| --- | ---: | ---: | ---: | ---: |
| `animal_c2_cows` | 26/0/0 | +7954.73 | +0.00 | +7954.73 |
| `proxy_livestock_crop` | 26/0/0 | +13365.62 | +6238.69 | +7126.92 |
| `proxy_land_expander` | 26/0/0 | +47075.23 | +39721.88 | +7353.35 |
| `proxy_high_labor` | 26/0/0 | +38541.31 | +29038.77 | +9502.54 |

- **Capital/payback:** first quadrant cost 1000; projected seed cost averaged
  1057.31 and incremental season labor 150.00. Mean projected payback was day
  26.46 (range 19–28), mean projected ROI 83.52%, and every one of 260 buys
  passed the payback gate.
- **Workload:** five hired hands after day 14 cost 220 coins over the season
  versus 60 for C2. The expansion averaged 449.88 water actions, 64.11 harvests,
  183 animal-service actions, and 1820.40 movement actions per game. C2's core
  animal counts were unchanged; maximum escaped cows and stranded valuable
  units were both zero.
- **Observed allocation:** a ten-game diagnostic across the full opponent list
  made 258 wheat, 76 strawberry, and 16 carrot plantings on the new quadrant,
  with no fixed melon fill. Choices remain responsive to market and opponent
  state.
- **New best:** **Yes — `agents/animal_c2_land_day14_adaptive.py`.** It improves
  every high-economy matchup, beats C2 directly, wins every held-out game, and
  has no new catastrophic matchup. Complete artifacts are
  `experiments/cow_land_search.json` and `experiments/cow_land_search.md`.
- **Submission:** Not prepared or submitted; `submission/main.py` is unchanged.

## Opponent-aware full-farm planner and adversarial league

- **Frozen control:** `agents/animal_c2_land_day14_adaptive.py` (SHA-256
  `a9300dd402c9e40a76209356adc7ce4d697a9ba972d5169cb9233f2f4894cfaf`).
  `submission/main.py` remained unchanged.
- **Architecture:** `agents/planner_common.py` adds marginal full-farm crop
  economics, visible-opponent supply forecasting, sequential self-market
  impact, cohort controls, forecast selling, animal capital allocation, and a
  conditional second-land gate. Controlled P0–P7 entry points are under
  `agents/planner_p*.py`.
- **Harder league:** 36 generated adversaries were screened directly against
  P0; the 12 hardest were retained alongside 14 historical agents for a
  permanent 26-opponent league. The top discoveries were early six-cow
  production and early-land/high-labor economies.
- **Separated seeds:** adversarial 10000–10003, component development
  10020–10051, architecture search 10060–10061, held-out 10100–10104; every
  matchup used both seats.
- **Ablations:** synchronized planting beat 2/3/4/planner cohorts. Forecast
  selling added only 18.7 held-out coins over P3 and worsened W/L. Fixed four
  cows remained more robust than dynamic, sheep, goose, mixed, 0/2/6-cow
  choices. Every conditional second-land gate declined the purchase.
- **Largest architectural gain:** visible-opponent forecasting improved P1 to
  P2 by 3552.5 average coins; self-impact added another 816.4. This did not
  recover the full planner's deficit versus the scripted P0 control.

| Held-out candidate | Games | W/L/T | Avg money | Avg advantage | Median | P10 | P5 | Direct vs P0 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| **P0 current best** | **260** | **215/43/2** | **47776.7** | **+14340.9** | **+9696.5** | **+14104.1** | **+14047.1** | 4/4/2, +0.0 |
| P3 self-impact planner | 260 | 202/58/0 | 46539.0 | +12120.8 | +7416.0 | +11601.7 | +11566.8 | 2/8/0, -1100.5 |
| P5 forecast selling | 260 | 197/63/0 | 46557.7 | +12068.4 | +7464.5 | +11505.6 | +11455.2 | 1/9/0, -1108.4 |

- **Remaining exploit:** P0 lost held-out to `gen_cow6_d8` (2/8, -3486.0),
  `gen_land_d11_labor7_sell12` (0/10, -2807.4), and
  `gen_land_d8_labor6_sell0` (1/9, -2441.3). Its fixed capital/scale timing is
  still exploitable by earlier cow or land/labor compounding.
- **New best:** No promotion. P3 is the strongest new architecture but loses
  1237.7 average coins (-2.59%) and -1100.5 directly to P0. No challenger met
  the +15% money or +5000 direct promotion bar.
- **Correctness:** final candidates had zero runtime failures, invalid actions,
  or stranded endgame value.
- **Artifacts:** `experiments/planner_league_results.json`,
  `experiments/planner_league_results.md`, `experiments/policy_league.json`,
  and `experiments/planner_architecture_analysis.md`.
- **Submission:** not justified, not prepared, and not submitted.

## Day 0-10 capital-compounding reconstruction

- **Frozen scope:** `agents/router_replay_hands12.py`, `agents/large_scale_router.py`,
  and `submission/main.py` were not modified. The frozen source SHA-256 remains
  `bac81a2099f3c4b7f97670a4e25d8cb0cc1c22fd23a41310096dd792b2f8f99b`;
  submission remains `edacba210dd55e9094e505e14fb57003610be92c43028007c31dbbabc1d78505`.
- **Exact replay audit:** all 35 selected top-player appearances reconciled with
  zero bank mismatches. Eight appearances from episodes 91866168, 91869967,
  91870919, and 91870920 were rendered turn by turn through day 10.
- **Mechanism:** five opening animals create about 496 fertilizer coins on day 2;
  persistent wheat pays the day-4/5 bridge; cared-for sheep sell 5 wool units on
  day 6 and 15 on day 7; milk produces the retained day-10 deed balance; the
  day-10 melon sale funds planting and 14 hands after the deed. Compact shed-edge
  pastures and staged crop slots are necessary to realize this schedule.
- **Milestones:** all 35 public appearances bought land on day 6/hour 16 and
  day 10/hour 0. Median cumulative revenue at deed 1 was 4242 (fertilizer 2649,
  wheat 542, wool 1051). Median bank before deed 2 was 2165; cumulative revenue
  contained no melon yet.
- **First frozen divergence:** public day-2 fertilizer revenue was roughly 496
  versus 100; the durable bank crossover occurred around day 6/hour 1, when the
  sheep/wool policy entered its first deed while the cow-only policy remained on
  one quadrant.
- **Controlled opening screen:** 360 fixed-seed day-10 games across 15 controls.
  Delayed fertilizer, delayed wool, two-day feed reserves, and cow-only openings
  all failed the target schedule. Five day-0 hands and funding the eight-cow
  target from day-6 wool were strongest.
- **Strongest candidate:** `agents/opening_public_front_cow8_day6.py`, SHA-256
  `3ede0041921010b0136abb538395faa5951e9af1fb9b76be41467246885da6a8`.
- **Full validation:** 96/0/0, average money 107689, average advantage +71559,
  P10 +25596 across eight hard opponents and both seats. Fresh held-out:
  128/0/0, average money 102136, advantage +67589, P10 +29382. Weakest matchup
  was frozen current at 16/0/0 and +19169. No cow or sheep losses; maximum final
  valuable inventory was three units.
- **New best:** not promoted. This phase establishes the strongest research
  candidate and causal opening mechanism; it does not change the registry or
  prepare a submission.
- **Artifacts:** `analyze_opening_capital_flow.py`,
  `analyze_current_opening.py`, `run_opening_search.py`,
  `run_opening_followup.py`, `run_opening_full_validation.py`,
  `experiments/opening_capital_flow_top.*`,
  `experiments/opening_current_matched.*`,
  `experiments/opening_day10_screen.*`,
  `experiments/opening_day8_cow_followup.json`,
  `experiments/opening_full_validation.*`, and
  `experiments/opening_capital_compounding.md`.
- **Submission:** unchanged; nothing was submitted.

## Final adversarial opening validation and promotion

- **Frozen candidate:** `agents/opening_public_front_cow8_day6.py` remained
  byte-for-byte unchanged at SHA-256
  `3ede0041921010b0136abb538395faa5951e9af1fb9b76be41467246885da6a8`.
- **League:** 256 complete games on fresh seeds 731001-731008, both seats,
  across 16 wool, milk, fertilizer, early-land, high-labor, mirror, frozen-router,
  and retained hard adversaries.
- **Result:** 248/8/0, average money 92,716, average advantage +50,461,
  paired P10 +44,945. All eight negative seat-level results were in the exact
  mirror; paired mirror advantage was zero.
- **Capital chain:** first deed by day 6 in 98.0% overall and second deed by
  day 10 in 100%. Sheep pressure delayed deed 1 to day 7 in 4/32 games but
  never broke deed 2 or caused a loss. Cow/milk and fertilizer pressure had
  100% success at both milestones.
- **Animal cash:** average realized wool revenue on days 6-7 was 3,933 and
  milk revenue on day 9 was 1,062. There were zero livestock losses.
- **Direct gate:** 16/0/0 versus `router_replay_hands12`, +20,436 average
  advantage and +9,530 paired P10.
- **Residual inventory:** 0.91 units average and four maximum; no animal-tile
  yield remained in the two packaging equivalence games.
- **Promotion:** updated `experiments/current_best.json` to
  `agents/opening_public_front_cow8_day6.py`.
- **Packaging:** standalone `submission/main.py`, SHA-256
  `3196b73fc2f46e25284b773136b530e2aacbaad2ba8a9dffdfce66472fe2a0fb`;
  imports only `base64`, `runpy`, and `zlib`.
- **Equivalence:** seeds 731101/seat 0 and 731102/seat 1 each matched 719/719
  decisions across complete 720-step games. Final money was 89,881 and 65,738;
  zero runtime, semantic, invalid-action, or livestock-loss findings.
- **Artifacts:** `run_opening_adversarial_final.py`,
  `experiments/opening_adversarial_final.*`, `package_opening_submission.py`,
  `validate_opening_submission.py`, and
  `experiments/opening_submission_packaging_validation.json`.
- **Submission:** packaged only; nothing was submitted to Kaggle.

## Three-hour early-compounding research

- **Frozen baseline:** `agents/animal_c2_land_day14_adaptive.py` remained
  byte-for-byte unchanged. `submission/main.py` also remained unchanged.
- **Compute:** 6,070 full-season simulations: 6,060 retained search/validation
  games plus eight economic-decomposition and two saved-file audit games, across traced diagnosis,
  broad joint search, local refinement, capital/labor refinement, direct
  red-team mutation, prefinal selection, and held-out confirmation.
- **Known weakness:** the two land challengers bought on actual day 11, created
  16 productive expansion plots, and carried large inventory-value leads before
  late liquidation. The six-cow challenger overcame a wasteful early
  escape/rebuy cycle through two additional late cows. All exposed P0's slow
  reinvestment of its first melon cash flow.
- **Red-team correction:** the first 4→8 day-16 finalist was beaten 6–2 and
  +5,115.6 by an all-eight day-12 mutation, which then became the final winner.
- **New strategy:** eight cows on day 12, pastures from day 11, one 12-plot
  adaptive quadrant on day 11, eight post-expansion hands, and four dedicated
  animal workers. The phased crop, feed, care, fertilizer, selling, and endgame
  logic remain unchanged.

| Held-out agent | Games | W/L/T | Avg money | Avg advantage | P10 | Productive tiles | Direct vs P0 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **animal_c8_day12_land_day11** | **336** | **319/11/6** | **64282.1** | **+26485.7** | **+24889.7** | **22.22** | **24/0/0, +15978.0** |
| staged 4→8 day 16 | 336 | 296/40/0 | 63712.9 | +23827.5 | +21827.1 | 21.86 | 24/0/0, +16381.8 |
| frozen day-14 P0 | 336 | 176/148/12 | 49168.9 | +8894.8 | +7631.5 | 18.04 | 6/6/12, +0.0 |

- **Improvement:** +15,113.1 average money, or +30.74%, on identical unseen
  opponents/seeds. The weakest non-mirror matchup was still 23–1, +3,540.9,
  with positive matchup P10.
- **Safety:** zero runtime failures, invalid actions, avoidable cow escapes, or
  stranded valuable endgame inventory. The saved agent matched the evaluated
  configuration action-for-action on two additional full games.
- **New best:** promoted to `agents/animal_c8_day12_land_day11.py` in
  `experiments/current_best.json`.
- **Artifacts:** `experiments/3h_compounding_search.json`,
  `experiments/3h_policy_league.json`, and `experiments/3h_research_report.md`.
- **Submission:** evidence supports a separate packaging/submission milestone,
  but `submission/main.py` was not modified and nothing was submitted.

## High-rating public replay meta review

- **Corpus:** 25 unique public episodes, 35 selected appearances from eight
  top-10 teams rated 3097.1–3216.7 at capture. Exact players, submissions, and
  episode IDs are in `experiments/top_player_replays/manifest.json`.
- **Analyzer:** `analyze_top_player_replays.py` reconstructs exact dynamic-price
  market cash flow and 30-day farm/investment timelines. All 25 replay bank
  histories reconciled with zero money mismatches. Outputs are
  `experiments/top_player_replay_analysis.json` and
  `experiments/top_player_replay_timelines.md`.
- **Observed public meta:** all 35 appearances bought land on days 6 and 10,
  ended on three quadrants, and peaked at 14 hands. The common opening was five
  wheat, five melon, one cow, four sheep, and five pastures on day 0; cows scaled
  to roughly eight by day 8. Midgame was strawberry-heavy and day-21+ production
  became wheat-heavy. Products were generally sold within one day.
- **Caveat:** action traces indicate a closely related/shared policy family, so
  the eight-player count is population evidence but not eight independent
  causal confirmations.
- **Controlled held-out validation:** fresh seeds 12600–12607, 12 frozen hard
  opponents, both seats, 192 games per candidate (768 total).

| Candidate | W/L/T | Score | Avg money | Avg advantage | P10 |
| --- | ---: | ---: | ---: | ---: | ---: |
| **animal_c8_day12_land_day11** | **182/8/2** | **95.3%** | **67436** | **+27445** | **+26655** |
| replay_meta_third_quadrant | 165/27/0 | 85.9% | 63299 | +23193 | +22109 |
| replay_meta_full_schedule | 82/110/0 | 42.7% | 45984 | +862 | -866 |
| replay_meta_land_labor | 64/128/0 | 33.3% | 36164 | -10597 | -18038 |

- **Interpretation:** the public day-6/day-10 schedule could not be transplanted
  into the cow-only C8 engine. The isolated third quadrant cost 4137 average
  coins; aggressive ports lacked the sheep/wool cash bridge and routing
  throughput needed to fill and service 70–75 productive tiles.
- **New best:** No. C8 remains frozen current best. The next justified
  architectural experiment is a controlled mixed sheep/cow opening and
  full-farm service router, not another land-calendar sweep.
- **Report:** `experiments/top_player_replay_review.md`.
- **Submission:** `submission/main.py` remained unchanged; nothing was
  submitted.

## Day 10–20 crop-lifecycle scheduler

- **Frozen economics/opening:** `agents/opening_public_front_cow8_day6.py` was
  preserved. All variants were action-identical to it through day 10 and kept
  land, livestock, labor caps, selling, and opponent awareness unchanged.
- **T2 causal correction:** T2 physically improved all four reconstructed loss
  matchups. Its former Lucas/Alexander gains and Jayveer/Pedro regressions were
  caused by empty-tile-dependent weed RNG changing day-12 town-shop unlocks.
  Fixed recorded shop schedules removed that confound; T2 then improved average
  advantage in all four traces but still went 0/8.
- **Isolated result:** harvesting ongoing strawberry yield as soon as available
  was the dominant change (29.5 to 81.1 crop harvests; 8,458 to 13,915 crop
  revenue). Safe stationary replant chaining was the only complementary
  improvement. Deadline skipping, cross-territory rescue, plant admission,
  dynamic workload zones, and cohort-before-distance ordering were rejected.
- **Combined fixed-trace screen:** `agents/lifecycle_lc_combined.py` went 4/4/0
  versus 0/8/0 for the baseline, with 83.6 versus 29.5 crop harvests, 13,907
  versus 8,458 crop revenue, 1.70% versus 2.51% critical misses, and 27.9 versus
  57.0 turns of replant delay. Total successful harvests reached 122.6 versus
  69.0.
- **Fresh confirmation:** 200 full games per finalist. LC went 196/4/0, averaged
  89,211 money and +42,294 advantage, and had +9,753 paired P10. It beat the
  frozen best 16/0 with +5,801 average advantage and went 176/0 in the fresh
  hard league. Runtime/semantic/invalid-field failures were all zero.
- **New best:** Yes. `agents/lifecycle_lc_combined.py` (version
  `lifecycle_ready_chain_v1`, SHA-256
  `db12d32912843e012c3dfd7e84c2c384ce998694bf02b98fc7e1fe9189c17e78`).
- **Remaining gap:** Jayveer (-9,280) and Pedro (-4,486) remain exact-trace
  losses, critical misses remain 1.50%, and total harvests remain below the
  public reference near 147.
- **Artifacts:** `experiments/crop_lifecycle_throughput.md`,
  `experiments/crop_lifecycle_screen.json`,
  `experiments/crop_lifecycle_confirm.json`,
  `experiments/crop_lifecycle_harvest_check.json`,
  `experiments/t2_fixed_shop_screen.json`, and
  `experiments/t2_matchup_causality.json`.
- **Submission:** evidence supports a later packaging/submission milestone, but
  `submission/main.py` was not modified and nothing was submitted.

## Large-scale territory router and replay economy

- **Frozen control:** `agents/animal_c8_day12_land_day11.py` remained
  byte-for-byte unchanged. The interrupted routing analyzer had already
  completed, so its replay analysis was not repeated. `submission/main.py`
  remained unchanged.
- **Execution diagnosis:** at 75 tiles the old replay router used 74.0% of
  actions for movement, only 21.8% productively, needed 3.39 moves per useful
  action, and utilized 50.5% of capacity. Public top-player traces were 44.4%,
  38.6%, 1.15, and 92.8%, respectively. The old scheduler's global task churn,
  repeated quadrant crossings, and unbatched animal service—not exact duplicate
  conflicts—caused the collapse.
- **Architecture:** `agents/large_scale_router.py` adds persistent quadrant
  territories, animal specialists, local crop chunks, urgency queues, task/feed
  reservations, batched animal service, shed/feed handoff, and endgame return.
- **Router-only causal test:** R2 old-router/replay economy scored 19/23/0 with
  44,164 average money. R3 with the same economy and new router scored 41/1/0
  with 72,352. At 75 tiles productive actions rose 21.6%→30.2%, movement fell
  74.3%→59.1%, and utilization rose 49.5%→75.8%. R1 regressed on the frozen
  two-quadrant economy, confirming that the router is specifically beneficial
  at large scale rather than a universal drop-in.
- **Mixed livestock:** a 1-cow/4-sheep opening added 2,588 average coins (+3.9%)
  versus the same ten-plot cow-only crop base, but lost crop throughput and all
  direct games to the stronger 12-plot cow-only routed policy. Sheep have
  positive isolated economics but are not robust in the current service layout.
- **Neighborhood:** two routed expansions beat one by about 8,189 average coins;
  buying the first deed on day 5 lost about 9,249. Cash flow caused the queued
  day-6/day-10 deeds to execute together on day 11. A twelve-hand ceiling beat
  fourteen hands in the search and confirmation samples.
- **Held-out confirmation:** seeds 13100–13115, eight high-economy opponents,
  both seats, 256 games per candidate and 1,024 total games.

| Candidate | W/L/T | Avg money | Avg advantage | P10 | Direct vs frozen C8 |
| --- | ---: | ---: | ---: | ---: | ---: |
| **router_replay_hands12** | **256/0/0** | **78750.0** | **+37279.9** | **+31473.8** | **32/0, +23401.6** |
| router_replay_cow8 | 256/0/0 | 77792.7 | +36339.3 | +31218.3 | 32/0, +22524.8 |
| router_r3_replay_economy | 256/0/0 | 77138.9 | +35799.7 | +30458.5 | 32/0, +22172.2 |
| frozen C8 | 214/34/8 | 62750.1 | +18794.6 | +16389.2 | 12/12/8 mirror |

- **New best:** **Yes — `agents/router_replay_hands12.py`.** It improves
  average money by 15,999.9 (+25.5%), wins 32/0 directly by +23,401.6, and its
  weakest matchup is still 32/0 and +18,092.9. There were zero runtime failures,
  semantic action errors, invalid-action observations, or cow losses.
- **Remaining gap:** 75-tile utilization is 75.1% versus 92.8% publicly, and
  movement remains 9.3 percentage points higher. The candidate averaged 78,750
  against the local league versus 81,666 across the public corpus; that
  cross-population comparison is indicative only.
- **Artifacts:** `experiments/router_execution_audit.*`,
  `experiments/top_player_worker_routing.*`, `experiments/router_ablation.*`,
  `experiments/mixed_livestock_router_screen.json`,
  `experiments/router_neighborhood.json`,
  `experiments/router_final_validation.json`, and
  `experiments/large_scale_router_report.md`.
- **Submission:** evidence justifies a separate packaging milestone, but
  `submission/main.py` was not modified and nothing was submitted.

## Opponent-aware architecture falsification

- **Frozen baseline:** `agents/router_replay_hands12.py` remained byte-for-byte
  unchanged (SHA-256 `bac81a2099f3c4b7f97670a4e25d8cb0cc1c22fd23a41310096dd792b2f8f99b`).
  `submission/main.py` also remained unchanged.
- **Real evidence:** nine newest public episodes from submission `55429527`
  (score 741.0) produced 5 wins and 4 losses. Exact two-sided economic
  reconstruction had zero bank mismatches. The four durable loss gaps appeared
  on days 8, 6, 7, and 6 (median 6.5), with opponents averaging four more hands,
  8.25 more productive tiles, and 5,915.5 more cumulative revenue at that point.
- **Top-player behavior:** the 25-replay/35-appearance high-rating corpus was
  overwhelmingly fixed-template. Every selected player used day-6/day-10 land;
  within-player/day planting correlation with opponent crop area was between
  -0.088 and +0.016 for the active premium crops.
- **Forecast quality:** visible maturity predicted next-three-day strawberry
  sales at `r=0.863`, melon at `r=0.601`, and livestock cadence predicted
  egg/milk/wool at `r=0.989/0.932/0.878`. Prediction did not imply a profitable
  reaction.
- **Controlled O0–O5 development:** 114 games per variant across 19 opponents,
  both seats. O1 crop choice lost 602.6 paired coins; O2 selling lost 254.6;
  O4 lost 905.0; O5 lost 490.3. Pressure-caused O1 switches lost 740.1 on
  switched games, and selling holds did not improve realized premium prices.
  Only O3 relative-state hiring was positive (+1104.8 development).
- **Fresh selection:** O3 retained only +443.3; full O5 lost 550.2, and its
  switched games lost 896.6.
- **Final confirmation:** 16 unseen seeds × 19 opponents × both seats = 608
  games per finalist.

| Candidate | W/L/T | Win rate | Avg money | Avg advantage | P10 | Direct vs O0 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| **O0 frozen** | **561/39/8** | **92.27%** | **72357.5** | **+30041.5** | **+323.0** | mirror |
| O3 relative hiring | 565/35/8 | 92.93% | 72679.5 | +30240.0 | +552.4 | 12/12/8, +0.0 |

- **Bug isolation:** a two-hour endgame harvest extension was an exact no-op.
  Feed-before-expansion eliminated 18 cow losses/replacements in 16 games and
  raised own paired money by 9,018, but lost directly to O0 by 7,951 due to the
  changed shared-market flow; neither fix was mixed into O1–O5 or promoted.
- **New best:** No. O3's final +322.0 (+0.45%) money gain and +0.0 direct edge
  miss the promotion standard. O0 remains current best.
- **Conclusion:** real losses are driven by superior fixed early compounding,
  not a demonstrated need for opponent-aware crop/sale reactions. Next work
  should reconstruct and ablate days 0–10 capital/labor/livestock cash flow.
- **Artifacts:** `experiments/opponent_aware_research.md`,
  `experiments/opponent_aware_research.json`, and the referenced diagnosis,
  development, selection, final, and isolated-bug result files.
- **Submission:** not justified, not prepared, and not submitted.

## Newest real-gap and post-opening throughput audit

- **Newest evidence:** all ten public episodes for submission `55435253` were
  downloaded and reconstructed for both players with zero bank mismatches. The
  four losses were to JayveerSingh6, Lucas Ferreira, Pedro Rezende Gomes, and
  alexander kern.
- **New loss timing:** durable opponent sale revenue begins on day 11 in three
  losses; Pedro is the early exception (ahead from day 0, +2,500 by day 7).
  The former day-6–8 diagnosis is no longer the population pattern.
- **Day 10–20 cause:** top replay agents earn 50,983 versus 31,021 revenue.
  Their crop edge is 28,909 versus 4,592, while our animal revenue is actually
  higher (26,317 versus 19,954). They average 73.2 productive tiles and 0.29%
  critical watering misses versus 62.9 and 2.79% for us.
- **Labor falsification:** both populations average 10.9 hands, peak at 14, and
  spend 3,040. Holding 14 hands through days 11–20 increases occupancy but
  lowers money; nominal worker count is not the primary bottleneck.
- **Controlled screen:** T0/T1/T2/T3/T4, fertilizer-only, water-guard, and T5
  were reported separately against six old synthetic, seven replay-derived,
  and four exact reconstructed real-loss opponents. Only T2 replacement-
  planting priority improved the replay-derived and exact-trace groups.
- **Fresh confirmation:** eight unseen seeds, 13 programmable opponents, both
  seats (208 games per candidate), plus eight exact loss-trace counterfactuals.

| Group | Candidate | W/L/T | Avg money | Avg advantage | Avg tiles d10–20 | Critical miss |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Old synthetic | T0 | 96/0/0 | 101,686 | +76,938 | 63.0 | 2.31% |
| Old synthetic | T2 | 96/0/0 | 103,884 | +79,175 | 68.2 | 0.93% |
| Replay-derived | T0 | 112/0/0 | 78,277 | +33,925 | 62.7 | 2.38% |
| Replay-derived | T2 | 112/0/0 | 82,700 | +38,876 | 68.1 | 1.10% |
| Reconstructed real losses | T0 | 0/8/0 | 64,680 | -8,366 | 63.1 | 2.51% |
| Reconstructed real losses | T2 | 3/5/0 | 59,600 | -8,217 | 68.1 | 1.24% |

- **New best:** No. T2 fixes Lucas and improves alexander, but worsens Jayveer
  and Pedro and degrades reconstructed-loss P10. The frozen current best remains
  `agents/opening_public_front_cow8_day6.py`.
- **Artifacts:** `experiments/post_opening_real_gap.md`, the diagnosis JSON/MD,
  separated screen files, and `experiments/post_opening_confirm.json`.
- **Submission:** `submission/main.py` remained unchanged; nothing was
  submitted.

## Epic next-stage architecture research

- **Frozen baseline:** `agents/lifecycle_lc_combined.py`, SHA-256
  `db12d32912843e012c3dfd7e84c2c384ce998694bf02b98fc7e1fe9189c17e78`.
- **Exact diagnosis:** Jayveer's durable lead starts day 11 hour 0 when a
  42-melon sale realizes 10,188 and funds land plus six cows. Pedro's apparent
  crop lead is mostly a 3,066-unit wheat inventory cycle: 126,975 spent and
  133,609 realized, a 6,634 spread.
- **Top production gap:** top agents average 2.5-turn replant delay versus 23.0,
  0.24% critical misses versus 1.84%, and 9.31 movement actions per crop cycle
  versus 13.36. Their planting cohorts are contiguous batches of about eight,
  not three. Inventory logistics tax is not higher for us.
- **Isolated result:** reducing the herd from nine to six cows is the largest
  mechanism (+7,832 own money in the Jayveer/Pedro screen). Adding the local
  action-value scheduler produces +9,261, cuts critical misses to 0.61%, and
  wins both Pedro seats. Predictive positioning, adjacent help, copied crop
  phasing, and replay-faithful wheat market cycling do not transfer reliably.
- **Held-out:** the guarded six-cow/value candidate ran 102 games at 83/19/0,
  94,804 average money, +35,661 advantage, and -924 P10. It improved own money
  only 1,627 (+1.7%), went 7/9 directly, remained 0/2 against Jayveer, and lost
  617 own money on average in the hard pool. Zero runtime/semantic/invalid
  actions, livestock losses, or stranded value.
- **RNG audit:** fixed shops produced +3,015 paired own money; natural coupled
  RNG produced -3,013. The sign reversal rejects promotion.
- **New best:** No. `experiments/current_best.json` remains unchanged. The
  strongest research-only branch is
  `agents/epic_b8_capacity_value_guarded.py`.
- **Artifacts:** `experiments/epic_next_stage_report.md`,
  `experiments/epic_next_stage_results.json`, and the diagnosis, isolated,
  selection, held-out, guarded, RNG-audit, and Pedro-market JSON files.
- **Submission:** unchanged; nothing submitted.

## Leaderboard-driven capital-window research

- **Real baseline:** public 803.5 submission 55435253 maps to
  `agents/opening_public_front_cow8_day6.py` (SHA-256
  `3ede0041921010b0136abb538395faa5951e9af1fb9b76be41467246885da6a8`).
- **Evidence:** 153 public episodes were reconstructed with zero financial
  mismatches. Sixteen replay archetypes reproduce their source checkpoint
  trajectories and final money exactly under original traces/seed/shops.
- **Mechanism:** the 803 router harvests destructive crops before their final
  peak-day watering. Five opening melons can realize 15 units instead of the
  public template's 30, weakening the day-10 deed/seed capital window.
- **Candidates:** R1 yield completion; R2 yield completion + second capital
  cohort; R3 R2 + six cows/value scheduler; R4 nine-cow capital/value; R5 clean
  six-cow capital; R6 compact checkpoint planner.
- **Held-out:** R3 ran 57/15/0 over 72 games, averaged 90,174 and +16,735,
  added 7,683 own money on unseen real traces, 12,159 fixed-shop and 13,261
  natural direct own money, raised crop revenue 13,127, and had zero invalid
  actions, livestock losses, or stranded value. Its paired-delta P10 remained
  -5,805 and it remained 0/2 versus six of eight unseen traces.
- **New best:** No. R3 is the strongest research-only branch, but negative tail
  and catastrophic top-template matchups fail promotion. `current_best.json`
  and `submission/main.py` remain unchanged; nothing was submitted.
- **Artifacts:** `experiments/leaderboard_breakthrough_report.md` and the
  leaderboard breakthrough analysis, selection, held-out, planner, and replay
  validation JSON files.

## Harvest-to-replant pipeline and crop-time opportunity cost

- **Frozen baseline:** `agents/lifecycle_lc_combined.py`, SHA-256
  `db12d32912843e012c3dfd7e84c2c384ce998694bf02b98fc7e1fe9189c17e78`.
  `submission/main.py` and `experiments/current_best.json` remained unchanged.
- **Exact diagnosis:** the prior 23-turn lifecycle-debt headline includes crop
  losses/expiry. Successful destructive harvest-to-replant events average 10.96
  turns (median 1, P90 26). Excess delay is 51.63% watering emergency, 17.00%
  scheduler priority, 11.39% harvest backlog, 7.32% shed travel, 6.33%
  territory assignment, 3.62% animal service, 2.08% worker departure, and only
  0.63% seed availability. Seeds are global; worker seed preload is impossible.
- **Top mechanism:** 35 high-rating appearances replant 95.18% within two
  turns with P90 1 and 99.52% same-worker continuity on the reliable subset.
  Exact next-turn task chaining, not pre-positioning or seed logistics, is the
  direct mechanism.
- **P0-P5:** exact chaining reaches 4.03 turns and P90 1, but lowers harvests,
  crop revenue, and watering safety. Predictive positioning is a no-op; a
  corrected three-tile cohort priority loses 3,030 money and 23.5 harvests;
  remembered-empty and combined branches also regress. A five-seed global
  reserve yields only a tiny screen gain and does not transfer across all four
  real losses.
- **Cow opportunity cost:** the controlled 6/7/8/9-cow exact-loss ablation
  selects six cows. Versus nine, six cows reclaim about 133 animal-service
  turns, add about 76 crop turns and 16 harvests, add 3,092 crop revenue while
  giving up 2,226 animal revenue, and add 3,194 final money.
- **Fresh confirmation:** the guarded six-cow research agent runs 50 games at
  38/12/0, 80,482 average money, +24,313 advantage, 253.0 harvests, 53,569 crop
  revenue, 1.33% critical misses, and -2,939 P10. It has zero runtime,
  semantic, or invalid actions, livestock losses, and stranded value.
- **Real losses:** own money changes by +8,528 Jayveer, +7,135 Pedro, -7,916
  Lucas, and +5,029 Alexander. Jayveer and Pedro remain losses.
- **RNG audit:** paired own income improves +2,198 with fixed shops and +3,720
  under natural RNG, but natural head-to-head advantage is -277 and natural
  P10 is -6,568.
- **New best:** No. The strongest research-only candidate is
  `agents/replant_cow6_guarded.py`; negative P10 and RNG-sensitive competitive
  transfer fail promotion.
- **Artifacts:** `experiments/replant_pipeline_research.md`,
  `experiments/replant_pipeline_research.json`, and the referenced diagnosis,
  screen, cow, confirmation, red-team, and RNG JSON files.
- **Submission:** unchanged; nothing submitted.

## Predictive watering and six-cow capacity

- **Frozen baseline:** `agents/lifecycle_lc_combined.py` remained current best
  (SHA-256 `db12d32912843e012c3dfd7e84c2c384ce998694bf02b98fc7e1fe9189c17e78`).
  W0 matched it action-for-action on all 719 requests in a full game.
- **Six-cow mechanism:** W1 saves 132.3 animal-service turns, adds 75.5 crop
  turns and 16 harvests, raises crop revenue 3,092, lowers natural replant
  latency from 16.6 to 9.7, and adds 3,194 money in the exact-loss screen.
- **Top-replay falsification:** 35 strong public appearances are less proactive
  (31.8% versus 69.7%) and use smaller watering cohorts, but have 0.34% misses,
  fewer waters per harvest, fewer territory crossings, and 96.2% of harvest
  waves immediately preceded by watering. Their mechanism is reliable
  deadline execution and spatial/cohort admission, not blanket early watering.
- **Ablations:** proactive late-day watering reduced emergency work and replant
  delay but lost 20.9 harvests versus W1. Local sweeps and territory borrowing
  also regressed. The strongest policy is W3dG: six cows with strict
  deadline/bonus-window watering and no-op animal action suppression.
- **Guarded fresh panel:** 60 games per agent. W3dG ran 48/12/0, averaged
  89,420 money, 248.3 harvests, 58,721 crop revenue, and 1.06% misses. It added
  1,847 money (+2.1%) and 6,663 crop revenue over W0, with zero runtime,
  semantic, invalid-action, livestock-loss, or stranded-value failures. P10
  remained negative (-1,709), and hard-pool own money regressed 602.
- **Requested revenue windows:** in the exact-loss panel W3dG adds 996 crop
  revenue on days 10–20 and 4,468 on days 20–29 (the season has no day 30).
- **Real losses:** W3dG remains 0/2 versus Jayveer (-4,442), reaches 1/1 versus
  Pedro (+36), remains 2/0 against Lucas (+4,129) but loses 7,208 own money
  there, and improves Alexander to +7,912.
- **RNG:** controlled-shop paired own money is +3,999 with P10 -4,810; natural
  RNG is +2,406 with P10 -4,602. The larger audit does not show a mean sign
  flip, but tail risk persists.
- **Red team:** W3dG went 32/0 against eight fresh stress archetypes, gained
  2,891 paired own money, and cut misses from 1.70% to 0.91%, with no failures.
- **New best:** No. The candidate increases measured watering debt/inherited
  emergencies, misses the `<0.7%` and 260-harvest targets, has negative P10,
  and does not solve Jayveer/Lucas transfer. `experiments/current_best.json`
  remains unchanged.
- **Artifacts:** `experiments/predictive_watering_research.md`,
  `experiments/predictive_watering_research.json`, and the diagnosis, screen,
  selection, final, RNG, and red-team JSON files referenced by the report.
- **Submission:** unchanged; nothing submitted.

## R3 tail robustification

- **Frozen baseline:** `agents/leaderboard_r3_cow6_capital.py`, SHA-256
  `57a4d38a72fffe75061271423b5580dec79c8c0e0423db4bef8899b3993b8fad`.
  The lifecycle, 803.5, submission, and current-best artifacts were preserved.
- **Diagnosis:** all 15 held-out losses and all 12 under--3,000 paired-delta
  games were reconstructed for both R3 and lifecycle. Paired P10 is dominated
  by a six-cow annuity regression in easy games; catastrophic actual losses are
  a separate, seat-invariant top-template crop-throughput cluster averaging
  -31,783 across eight games.
- **Decision regret:** no R3 opening melon wait delayed either required deed.
  A visible-supply early-harvest guard lost 62 mean money and worsened paired
  P10 delta to -1,661. R3 already sells opening shed inventory without a
  pre-deed delay.
- **Guards:** market harvest, conditional one/two-cow recovery, late
  strawberry retention, and guarded combinations were tested as isolated
  branches. Conditional cows partly restored easy-game annuity but did not
  improve the 2/14 unseen-top record. The two-cow guard also caused four
  livestock losses and stranded up to 108 value.
- **Fresh final:** 200 unseen, real-heavy games per finalist, both seats,
  fixed and natural RNG. R3 ran 151/49/0 at 72,565 money and +13,284 paired
  advantage, with P10 -64, P5 -9,241, and zero safety failures. G4 ran
  150/50/0 with P10 -3,176; G8 ran 143/57/0 with P10 -1,037. All retained
  Jayveer/Pedro/Lucas/Alexander 2/0, but all remained 2/14 versus unseen top
  traces.
- **New best:** No. No narrow guard repairs the real top-crop tail; frozen R3
  remains the strongest research candidate, while `experiments/current_best.json`
  remains unchanged.
- **Artifacts:** `experiments/r3_tail_robustification.md`, compact JSON,
  full diagnosis/final JSON, three guard screens, and three new cluster-pressure
  adversaries.
- **Submission:** unchanged; nothing submitted.

## V27 replay backbone and bounded correction

- **Frozen inputs:** `submission/main.py`, R3, the 803 opening, and lifecycle
  retained their pre-study SHA-256 hashes. The interrupted multi-wave search
  was parked at 600/1536 games in its existing `.partial` artifact.
- **Public evidence:** 25 unique episodes / 35 appearances from eight
  submissions rated 3097–3217 were grouped by submission and whole-route
  fingerprint. Four structural families emerged. Victor's selected family is
  99.65% stable in field actions and 99.20% in market actions; its medoid route
  reproduced 719/719 requested actions and 94,884 final money exactly.
- **Strict ladder:** K0–K9 were tested on the same 48-game serious panel, both
  seats, fixed/natural shops, reconstructed losses, eight held-out real routes,
  and frozen 803/lifecycle/R3 anchors. Every stage went 48/0; K0 averaged
  +48,253 advantage. Broad capital repair and future SELL-slot assignment were
  rejected because they regress fresh/pressure results or create stranding.
- **Winning component:** K3 adds only worker-specific weed
  DIG→retry→bounded displaced-action replay. Fresh confirmation was 32/0,
  122,464 average money, +53,559 advantage, P10 +39,977, 99.987% route-action
  fidelity, zero runtime/schema/livestock/stranding failures, and no fallback.
- **New best:** Yes — `agents/v27_replay_weed_guard.py`, version
  `v27_victor_route_weed_guard_v1`. The improvement is architectural and
  decisively reverses Filip/Amer/Yankang/Prashant as well as
  Jayveer/Pedro/Lucas/Alexander.
- **Artifacts:** `experiments/v27_replay_backbone_report.md`, full and compact
  result JSON, fresh confirmation JSON, route manifest/stability, market
  semantics, and market-risk analysis.
- **Submission:** unchanged; nothing packaged or submitted.

## V27 K3 submission packaging

- **Frozen source:** `agents/v27_replay_weed_guard.py` remained byte-identical
  at SHA-256 `dc0100ec0d029a6362f92618429b09d7baba5b8a5257f20a61385fe82afeda51`.
- **Package:** standalone `submission/main.py`, embedded zlib/base64 Victor
  route, SHA-256 `4ceb5a94a5c3c945853e09dd46a60267bec0948840be01363d49d8ac1b0cf521`.
- **Equivalence:** 44/44 paired conditions passed (88 differential games):
  exact known Victor episode at 94,884; 16 fresh both-seat pairs; 22 requested
  strong-opponent both-seat pairs; five controlled weed cases. All requested
  farmer, ordered hand, and ordered market actions matched; source and package
  route fidelity both measured 99.954739% on the adversarial aggregate.
- **Safety:** zero runtime/schema failures, livestock escapes, meaningful
  stranding, fallback activation, unsupported dependencies, or unexplained
  divergence. A clean directory containing only `main.py` completed 720 turns.
- **Result:** packaging gate passed; ready for manual Kaggle submission.
  Nothing was submitted or uploaded.
- **Artifacts:** `experiments/v27_submission_packaging_report.md`,
  `experiments/v27_submission_packaging.json`, `package_v27_submission.py`,
  and `validate_v27_submission.py`.

## Top-100 Super Replay Backbone

- **Frozen baseline:** `agents/v27_replay_weed_guard.py` stayed byte-identical
  at `dc0100ec0d029a6362f92618429b09d7baba5b8a5257f20a61385fe82afeda51`;
  `submission/main.py` stayed byte-identical at
  `4ceb5a94a5c3c945853e09dd46a60267bec0948840be01363d49d8ac1b0cf521`.
- **Corpus:** Top 100 submissions, 332 downloaded episode IDs, 331 unique
  valid full replays, 583 elite appearances / 454 normalized appearances,
  ranks 1–100. Exact audit covered 237,989 transitions with zero unexplained
  bank mismatches.
- **Structure:** 84 highly fixed, three bounded-fixed, ten phase-fixed, and two
  state-dependent submissions. Three natural route families emerged: 93-agent
  Victor-like, five-agent early-land/lean-labor, and one mixed-wool route.
- **Generation 0:** 23 raw routes + K3, 576 completed games. F2 had the best
  cheap mean/tail; Ricardo and Hamed were the strongest stable high-income raw
  routes. F3's catastrophic tail rejected it.
- **Splices:** 550 compatibility checks, 312 compatible edges, 80 generated
  candidates. Preserved full checkpoint 340/1,944 and screen 140/648. No
  completed splice beat its raw parent; Nikita→Ricardo was outcome-identical
  to Ricardo.
- **Selection:** 180 games across K3/F2/Ricardo/Hamed/splice. F2 led at
  28/8, +4,614, but lost one cow; Ricardo was 25/11, +2,524 and safe.
- **Strict unseen final:** finalists were locked before 15 new rank-86-100
  episodes were queried. Ricardo ran 92/2, averaged 88,524 money and +5,668
  advantage, with P10 +985 and P5 +824. It beat K3 64/0 at +6,027; natural
  RNG was 32/0 at +6,793. Fidelity 99.940%; zero runtime, semantic, fallback,
  livestock, or meaningful-stranding failures. F2 was rejected despite +4,699
  because P10 was −544 and nine animals escaped.
- **Economic mechanism:** eight exact paired games show Ricardo at +4,001
  final money from +480 revenue and −3,521 recorded spend, principally −900
  animal and −2,628 feed cost while shifting revenue toward melon/strawberry.
- **New research best:** Yes — `agents/super_replay/super_backbone_v1.py`,
  SHA-256 `96bd9cefd7c31075e47719ec1f9d1ee9391b467f68b956c65e0dd96478adb516`.
- **Artifacts:** `experiments/super_replay_backbone_report.md`, corpus,
  stability, family, economic-wave, financial-audit, phase-graph,
  action-confidence, Generation-0, selection, unseen-final, and promotion
  validation JSON files.
- **Submission:** unchanged; nothing submitted or uploaded.

## Super Replay Backbone submission packaging

- **Frozen source:** `agents/super_replay/super_backbone_v1.py` matched and
  retained SHA-256 `96bd9cefd7c31075e47719ec1f9d1ee9391b467f68b956c65e0dd96478adb516`.
- **Package:** standalone `submission/main.py` embeds only Ricardo's 719 route
  actions and expected-state anchors plus the exact Stage-3 worker rematcher and
  bounded K3 weed repair. Final SHA-256:
  `0b7c4fb3587f446a414cad30464522dab68ac64d88bc8f4e776e090e9b4cf1d8`;
  size 91,596 bytes.
- **Equivalence:** 40/40 paired conditions passed: 719/719 on the Ricardo source
  replay, 16/16 fresh both-seat pairs, 18/18 strong-opponent pairs, and 5/5
  controlled weed cases. Route fidelity was identical at 99.949877%.
- **Safety:** zero runtime/schema failures, livestock losses, meaningful
  stranding, packaging regressions, or unexpected fallback. A clean directory
  containing only `main.py` completed all 720 steps.
- **Result:** packaging gate passed; ready for manual Kaggle upload. Nothing was
  submitted or uploaded automatically.
- **Artifacts:** `experiments/super_backbone_submission_packaging_report.md`,
  `experiments/super_backbone_submission_packaging.json`,
  `package_super_backbone_submission.py`, and
  `validate_super_backbone_submission.py`.

## Super Replay Backbone V2

- **Preservation:** V1 remained at
  `96bd9cefd7c31075e47719ec1f9d1ee9391b467f68b956c65e0dd96478adb516`;
  deployed `submission/main.py` remained at
  `0b7c4fb3587f446a414cad30464522dab68ac64d88bc8f4e776e090e9b4cf1d8`.
- **Real diagnosis:** all 77 currently available V1 public episodes were
  analyzed (58/19). Losses preserved land, labor, livestock, crop geometry,
  harvest volume, and worker utilization; the repeated deficit was realized
  milk/strawberry/product value, not an operational milestone failure.
- **Corpus:** current Top 20, 20 selected versions, 240 requested appearances,
  182 unique IDs, 181 valid unique replays, 171 deduplicated development
  appearances, and 29 episode IDs held untouched until finalist lock. Three
  mutated known families emerged; 17/20 submissions were highly fixed.
- **Search:** 19 raw routes plus V1, eight coherent phase candidates, and six
  elite-supported market windows. JALKARNA complete route was strongest;
  Nazmus had higher cheap mean but lost livestock. The best phase splice was
  JALKARNA from step 240, but it was inferior to the coherent full route.
  Window-only gains were marginal. No new repair or branch was justified.
- **Mechanism:** JALKARNA versus V1 gained +4,077 final money in 16 exact paired
  economic games via +4,157 revenue for +80 spend: milk +1,486, strawberry
  +1,026, wool +1,023, wheat +492, with unchanged animal/land/labor spend.
- **Selection:** JALKARNA complete 46/2/0, +3,345, P10 +550, P5 +139, zero
  failures; V1 6/14/28, −214. Finalist hashes were then locked.
- **Final unseen:** V2 76/14/0 over 90 games, 94,172 average money, +2,549
  advantage, median +3,838, P10 −375, P5 −9,208, fidelity 99.9578%, zero
  runtime/semantic/fallback/livestock/meaningful-stranding failures. Direct V1
  was 32/0 at +4,617; fixed +4,667 and natural +4,567.
- **New research best:** `agents/super_replay_v2/super_backbone_v2.py`, SHA-256
  `c39d82b4f796271603e32ea8cb4b70261fbbe3d4e17940886caf5f5a6bd9adef`.
- **Artifacts:** required V2 diagnostic, corpus, stability, family, phase,
  candidate-search, failure-cluster, final-validation JSON files and
  `experiments/super_replay_backbone_v2_report.md`.
- **Submission:** unchanged; nothing packaged, uploaded, or submitted.

## Super Replay Backbone V2 submission packaging

- **Source:** `agents/super_replay_v2/super_backbone_v2.py` (`c39d82b4f796271603e32ea8cb4b70261fbbe3d4e17940886caf5f5a6bd9adef`).
- **Package:** `submission/main.py` (`a4f753d46a95e8d972098504f4930165e7e66f8ce292092e9ab090e4741310c3`, 91,462 bytes).
- **Equivalence:** 32/32 paired conditions passed: 719/719 source-replay actions, 16/16 fresh both-seat pairs, 10/10 strong-opponent pairs, and 5/5 controlled weed pairs.
- **Safety:** zero runtime/schema failures, livestock escapes, packaging-induced stranding, or fallback; fidelity delta 0.0 percentage points.
- **Status:** ready for manual Kaggle submission; no submission or upload performed.

## Super Replay Backbone V3

- **Corpus:** current Top-10, 10 submission versions, 126 valid unique replays; split 71 development / 24 selection / 31 final before action mining; zero development financial mismatches.
- **Routes:** 10 complete routes, 3 structural families. Nazmus was strongest but unsafe (two actual cow escapes in two conditions). Best safe tail was Furious Monk from step 160.
- **Branch:** step 160, opponent bank <= 644 selects the compatible tail. Development oracle +85; branch selection/final paired own-money deltas -16.0/-30.1.
- **Final:** branch paired W/L/T 12/16/16; zero safety failures, but promotion gate failed. V2 remains best.
- **Deployment:** `submission/main.py` unchanged; no Kaggle submission or upload performed.

## Super Replay Backbone V4 — bounded dynamic strategy search

- **Preservation:** V2, V1, K3, `submission/main.py`, and `current_best.json` retained their frozen SHA-256 hashes. Nothing was submitted or uploaded.
- **Real evidence:** refreshed deployed V2 submission `55473991` to 78 valid public episodes (71/7), with zero financial mismatches. Five losses are market-realization deficits and two are endgame economic losses; physical production and end inventory remain intact.
- **Counterfactual harness:** environment seed metadata plus warmed backbone state reproduced uninterrupted V2 exactly at checkpoints 160/240/480/600 across all tested loss episodes.
- **Market:** four early-sale thresholds and three hold/recovery policies all regressed. Best broad policy lost 1,053 paired money; hold policies lost 4,572–8,111 and caused livestock/stranding failures. The best local timing perturbation was only +95.5 and split 2/2.
- **Endgame/capital/crop:** all rejected. Seven cows lost 584 paired money; six cows lost 2,134; reduced wheat waves lost 679–1,355; forced day-27 liquidation lost 603; skipped day-29 hires lost 3,621.
- **Nazmus:** raw route lost four animals. K3 and narrow rescue were safe in-screen but both lost about 2.2k paired money to V2, so research stopped.
- **Selection/final:** no module passed development, so no combinations or protected elite final holdout were opened. Frozen V2 completed 40 fresh fixed/natural games with zero runtime, semantic, livestock, or stranding failures.
- **New best:** No. V2 remains `agents/super_replay_v2/super_backbone_v2.py` (`c39d82b4f796271603e32ea8cb4b70261fbbe3d4e17940886caf5f5a6bd9adef`).
- **Next architecture:** if research continues, use an offline learned residual action-value model on validated checkpoints; keep rare overrides and V2 as the base. Do not use policy-from-scratch RL.

## Current Top-50 deep strategy mining and distillation

- **Frozen baseline:** V2 remained unchanged at
  `c39d82b4f796271603e32ea8cb4b70261fbbe3d4e17940886caf5f5a6bd9adef`;
  `submission/main.py` remained unchanged at
  `a4f753d46a95e8d972098504f4930165e7e66f8ce292092e9ab090e4741310c3`.
- **Corpus:** refreshed the current Top 50 at
  `2026-08-31T15:16:44.299729+00:00`: 50 teams, 249 valid unique full
  episodes, 408 selected appearances, 340 exact-action-deduplicated
  appearances, 210 route implementations, 22 economic implementations, and
  11 refined economic families. A post-lock holdout added 22 unused episodes,
  two per family.
- **Consensus:** all 11 independent families use at least three quadrants,
  first land by day 7, second land by day 11.5, 12 hands, melon/strawberry
  waves, and terminal liquidation. Ten use mixed cows and sheep. Top 1-10
  relies on more livestock diversity, not monotonically more cows.
- **Raw parents:** exact safety-repaired Dmitry, Hanserong, and redblack
  complete economies produced serious paired own-money gains of +7,087,
  +6,321, and +5,259. Broad feeding repair was rejected because it
  desynchronized the replay routes; only audited deadline repairs survived.
- **Architecture:** `top50_observable_portfolio_v1` selects one complete,
  coherent economy at step 1 using only the opponent's currently visible bank
  and hand count. It never uses seed, replay ID, rank, future state, or result.
- **Locked final:** 132 games per agent. Candidate 107/25/0, average money
  95,146, average advantage +17,617, advantage P10 -2,027 and P5 -8,798.
  V2 was 52/48/32, money 89,167, advantage +9,576, P10 -14,493 and P5
  -23,795. Paired own-money delta was +5,979 and net-advantage delta +8,040.
  Direct V2 was 62/2 (natural 32/0). Unseen Top-50 families were 21/23 versus
  V2's 12/32. Exact safety: zero runtime, semantic, fallback, livestock-escape,
  or meaningful-stranding failures.
- **Attribution:** on the focused panel, net advantage improved +7,640, driven
  mainly by fertilizer/wheat capital cycling and opponent market suppression;
  this is primarily market/capital value rather than a pure production gain.
- **Promotion:** yes, as the new local **research best**:
  `agents/top50_distilled/top50_observable_portfolio.py`, SHA-256
  `f9ca672848ccffdfe56888d99bcdf5a9d7644062b9eec0cf0cdea13574931233`.
  It is not labeled low-risk final because paired-own P10 remains -8,029.
- **Report:** `experiments/top50_strategy_mining_report.md` plus the complete
  required `experiments/top50_*` machine-readable artifact set.
- **Submission:** unchanged; nothing packaged, uploaded, or submitted.

## Top-50 Observable Portfolio final deployment packaging

- **Locked source:**
  `agents/top50_distilled/top50_observable_portfolio.py`, raw/LF SHA-256
  `f9ca672848ccffdfe56888d99bcdf5a9d7644062b9eec0cf0cdea13574931233`.
- **Previous deployment recorded:** V2 `submission/main.py`, raw/LF SHA-256
  `a4f753d46a95e8d972098504f4930165e7e66f8ce292092e9ab090e4741310c3`.
- **Standalone package:** `submission/main.py`, raw/LF SHA-256
  `789bb9bbd5122eb4891983e776a13777328e3e87736cbbc0b4bc86d13fc33f9b`,
  272,360 bytes. It embeds all three exact routes, the proven Stage-3 worker
  executor, exact livestock safety wrappers, and the locked step-1 selector.
- **Dependencies:** standard library plus the installed Kaggriculture runtime;
  no project-local import, runtime file read, network access, or local path.
  A clean directory containing only `main.py` completed all 720 steps.
- **Integrity:** three 719-step parent route/action and expected-state payloads
  matched exactly. Selector agreement was 110/110 states. Same-module
  sequential seat-0/seat-1 reset matched fresh imports exactly.
- **Equivalence:** 16/16 full games passed across eight fresh seeds, both seats,
  and V2, K3, Nazmus, rank-1 adaptive, ResearchStudio adaptive, V1, portfolio
  mirror, and a Top-50 family-03 medoid. All 11,504/11,504 requested actions,
  final money, advantage, land, hands, animals, inventory, and terminal state
  were identical.
- **Safety:** zero runtime failures, semantic failures, actual livestock
  escapes, meaningful terminal stranding, or unexpected fallback.
- **Runtime:** 0.818 ms mean call, 1.415 ms P95; package import median 26.233 ms.
- **V2 sanity:** 8/0/0, average money 112,003, average advantage +9,356.
- **Status:** ready for manual Kaggle upload. No submission, upload, remote
  modification, or Git push was performed.

## 2026-09-01 — Current Top-3 forensic research

- Baseline: `agents/top50_distilled/top50_observable_portfolio.py` (`f9ca672848ccffdfe56888d99bcdf5a9d7644062b9eec0cf0cdea13574931233`); Super Replay V2 retained as control.
- Live snapshot: tetsuya / Crop Dusta / OceanMix at 2026-09-01T07:39:57.571562+00:00; 30 exact-current-version appearances each.
- Finding: all three stabilize the opening then branch materially; a public medoid is not the hidden adaptive policy.
- Raw league: Rank1 medoid led the broad initial panel but split 4–4 with CurrentBest, showed tail risk, and lost livestock.
- Microtuning: exact Rank3 branch swap, exact K3 branch swap, and combination all failed development (paired mean deltas −19,609 / −14,180 / −33,789; all had escapes).
- Decision: no validation consumption, no finalist, no promotion. CurrentBest remains unchanged. `submission/main.py` untouched at `789bb9bbd5122eb4891983e776a13777328e3e87736cbbc0b4bc86d13fc33f9b`. Nothing submitted.
- Report: `experiments/top3_forensic_research_report.md`.

## 2026-09-01 — Top-3 adaptive policy distillation

- Frozen baseline remained `agents/top50_distilled/top50_observable_portfolio.py` (`f9ca672848ccffdfe56888d99bcdf5a9d7644062b9eec0cf0cdea13574931233`).
- Refreshed version-pure corpus: 219 usable teacher appearances—86 tetsuya, 66 Crop Dusta, 67 OceanMix—covering 215 unique valid public replay files.
- Built an event-driven seven-phase ontology, eight major strategic-decision targets, complete-episode/action-hash grouped splits, 24/48/72/120-turn deployable history features, and a passing leakage audit.
- Best untouched-holdout reconstruction: phase macro-F1 0.973, major-decision macro-F1 0.839, transition recall 1.000, mean transition timing error 4.1 steps. Current-state-only was 0.865/0.735 and turn-only 0.488/0.614, confirming material history value.
- Limits: Crop Dusta decision F1 0.742; crop-family F1 0.687; strict market-mode F1 0.555; cohort scale within two plants only 37.0%. Only 63.5% of frozen-CurrentBest diagnostic states passed OOD + confidence guards.
- Executor audit: CurrentBest is a step-1 selector over complete replay backbones. Land, livestock, crop-cohort and terminal targets require a new target-driven low-level executor; fixed route switching remains forbidden. Counterfactuals, oracle, fitted-Q and gameplay hybrids were explicitly not run rather than measuring incoherent route breakage.
- Promotion: no. CurrentBest remains the research best. `submission/main.py` remained at `789bb9bbd5122eb4891983e776a13777328e3e87736cbbc0b4bc86d13fc33f9b`; nothing packaged, uploaded or submitted.
- Report: `experiments/top3_adaptive_distillation_report.md`.

## Autonomous strategic breakthrough research

- **Hypothesis:** a state-driven goal executor could safely convert the
  Top-3/Top-50 strategic signal into adaptive control after the opening.
- **Result:** `goal_executor_v1` failed the diagnostic screen (20/8/0,
  average advantage -8,298, P10 -132,772) and lost animals in 28/28 games.
  The safety-gated control fell back to the frozen route around livestock and
  was behaviorally identical to the baseline.  The failure is executor
  integrity, not evidence that history has no predictive value.
- **Second hypothesis:** complete economically distinct route families would
  add robust value without incompatible route splicing.  The raw
  `top50_raw_55899537` route won both independent 16-seed paired panels (64/0/0
  total, approximately +1,976 mean advantage; positive P5/P10) and the
  64-game held-out control league (64/0/0, +48,942 mean advantage, P10 +1,873).
  All successful raw-route panels had zero runtime errors and zero observed
  animal losses.
- **Economic attribution:** on four additional matched seeds, final money was
  +2,072.5, driven by strawberry (+900), fertilizer (+657), wheat (+266), wool
  (+156), and milk (+30) revenue, with feed/product spend -114 and seed spend
  +50.  This is primarily market/capital cycling with a small throughput gain.
- **Decision:** promote `agents/autonomous_next/top50_raw_55899537.py` as the
  cautious local research best (SHA-256
  `5d66e9283e4e500a4113a6d167abb04e0a088c2ad8799c1750da4b7a2172d069`).  The
  gain is below the preferred +3k own-money target and paired lower-tail risk
  remains, so do not package or submit automatically.
- **Artifacts:** `experiments/autonomous_breakthrough_research.md`,
  `autonomous_breakthrough_diagnostics.json`, `autonomous_route_validation.json`,
  `autonomous_raw_route_h2h.json`, `autonomous_raw_h2h_economics.json`, and
  `autonomous_route_economics.json`, plus the four candidate/validation
  scripts listed in the report.

## 2026-09-01 — Final independent validation of `top50_raw_55899537`

- **Locked inputs:** Candidate SHA-256
  `5d66e9283e4e500a4113a6d167abb04e0a088c2ad8799c1750da4b7a2172d069` and
  frozen baseline SHA-256
  `f9ca672848ccffdfe56888d99bcdf5a9d7644062b9eec0cf0cdea13574931233` both
  matched `experiments/raw55899537_finalist_lock.json`.
- **Validation:** 400 paired conditions / 800 full 720-step games, 136 fresh
  disjoint seeds, both seats, direct CurrentBest, Top-3, historical strong,
  natural-RNG, and four predeclared stress regimes. Runtime and semantic
  failures were zero; candidate escapes were zero; route realization was
  99.9955%; mean terminal stranded value was 45.645 coins.
- **Result:** Candidate H2H was 346/54/0 and mean advantage delta was +700.5,
  but paired own-money delta was only +182.2 (bootstrap 95% CI -1,612.4 to
  +1,996.9). The Top-3 frontier regressed by -12,267.8 advantage coins; the
  tetsuya matchup regressed by -28,602.9 and had the worst tails.
- **Decision:** **DO NOT PROMOTE.** `experiments/current_best.json` was
  restored to `agents/top50_distilled/top50_observable_portfolio.py`. The
  challenger remains preserved as a rejected research finalist; no source
  strategy or `submission/main.py` was changed and nothing was submitted.
- **Reports:** `experiments/raw55899537_worst_case_analysis.md` and
  `experiments/raw55899537_final_validation_report.md`, alongside the complete
  locked JSON artifact set.

## 2026-09-01 — Autonomous next-step complete-route family falsification

- **HYPOTHESIS:** a coherent complete route family omitted from the observable
  Top-50 portfolio could provide a materially stronger own economy without
  unsafe continuation switching.
- **CHEAP TEST:** 112 paired full games on seeds 50600--50601, both seats,
  against CurrentBest and the three Top-3 frontier representatives.  Family-01
  was independently confirmed on 128 paired games on disjoint seeds
  50700--50707.
- **RESULT:** the cheap family-01 signal (+2,531 own money) did not transfer:
  deep own-money delta **-10,692**, advantage delta **-14,642**, own P10
  **-30,438**, with 44/20/0 direct H2H and zero livestock losses.  Other
  medoids were immediately negative (family-02 -14,441; family-03 -11,585;
  family-04 -2,554; family-05 -13,330 own-money on the cheap panel).  The raw
  55899537 route was also negative on this screen (-1,611 own money).
- **ECONOMIC INTERPRETATION:** route realization was 99.967% in the deep
  family-01 test, so the loss is not primarily an executor bug.  Complete-route
  family selection does not currently reveal robust own-economy headroom and
  appears sensitive to frontier market regimes.
- **DECISION:** no promotion and no changes to CurrentBest or
  `submission/main.py`.  The next experiment is a narrow market-only residual
  that keeps every production, animal, land, labor, and movement commitment
  fixed while testing only already-scheduled SELL ordering.  This is the
  cheapest safe test of remaining market-sequencing headroom.
- **ARTIFACTS:** `experiments/autonomous_next_route_screen_report.md`,
  `autonomous_next_route_screen.json`, and
  `autonomous_next_route_deep_screen.json`.

## 2026-09-01 — Autonomous next-step market residual and checkpoint audit

- **HYPOTHESIS:** after complete-route family selection failed, the frozen
  route might still contain safe own-economy headroom in market sequencing.
  A market-only residual should improve sales while preserving all production
  and service commitments.
- **CHEAP TEST:** 192 full games on fresh deterministic seeds 50800--50807,
  both seats, paired against CurrentBest, tetsuya, Crop Dusta, and OceanMix.
  `market_residual_reorder_v1` permuted only multiple SELL orders already in
  the same turn.  `market_residual_horizon_v1` additionally used the existing
  bounded public-hazard future SELL-slot assignment and restored displaced
  batches at their original slots.
- **RESULT:** reorder-only made **zero changes** and was action-for-action
  identical to CurrentBest (64/64 paired conditions, delta 0).  The horizon
  residual made 611 bounded assignments but reduced own money by **954.3** on
  64 paired conditions (median -176, P10 -2,225, P5 -8,671, 65.6% negative),
  with advantage delta -819.9.  A fixed-seed bootstrap 95% CI for its own
  delta was **[-1,629, -367]**.  Its own-money deltas were -3,575.6 vs Crop
  Dusta, -749.3 vs OceanMix, -45.9 vs CurrentBest, and +553.4 vs tetsuya.
  Runtime and semantic failures were zero in all 192 games and optimizer
  errors were zero.
- **CHECKPOINT AUDIT:** pairwise strict compatibility of complete route-bank
  expected states falls from 67.6% at step 24 to 22.1% at step 48, 5.9% at
  step 168, 1.6% at step 240, and below 1% by steps 360--600.  Matching land
  or geometry alone is therefore not a safe continuation criterion; crop
  cohorts, inventories, seeds, worker state, and animal commitments alias.
- **DECISION:** no candidate is promoted.  Market ordering has no measurable
  headroom in the existing route (the route is already locally ordered), and
  future slot assignment is negative under frontier interaction.  The static
  checkpoint audit makes a full delayed route selector low-value until a
  target-driven executor can own all coupled state.  CurrentBest and
  `submission/main.py` remain untouched; no Kaggle submission occurred.
- **ARTIFACTS:** `run_autonomous_market_residual.py`,
  `agents/autonomous_next/market_residual_reorder_v1.py`,
  `agents/autonomous_next/market_residual_horizon_v1.py`,
  `experiments/autonomous_market_residual.json`, and
  `audit_autonomous_checkpoint_compatibility.py` with
  `experiments/autonomous_checkpoint_compatibility.json`.

## 2026-09-01 — High-own-money raw Top-50 route probe

- **HYPOTHESIS:** the highest-own-money mined replay (`super_raw_55884271`,
  Borrun, source replay money 144,328) may contain a stronger complete
  economic package than the current portfolio, even though its family medoid
  was not robust.
- **CHEAP TEST:** 128 full games on fresh seeds 50900--50907, both seats,
  paired against CurrentBest, tetsuya, Crop Dusta, and OceanMix.  The route was
  executed whole through the existing Stage-3 safety executor; no actions were
  spliced.
- **RESULT:** raw_55884271 was safe (0 runtime failures, 0 semantic failures,
  0 livestock losses, 100% route realization) but lost **6,649.3 own-money
  coins** paired with CurrentBest (64 conditions; median -6,082, P10 -35,217,
  P5 -43,317, 71.9% negative).  Own-money deltas by opponent were +5,205.6
  vs tetsuya, -25,770.1 vs Crop Dusta, -10,510.6 vs OceanMix, and +4,478.1
  vs CurrentBest.  Mean advantage delta was -4,381.5.
- **DECISION:** reject the route despite its exceptional source replay money.
  Its value is trajectory/regime-specific and does not transfer to the
  frontier.  This reinforces that public final money is not causal evidence
  for a reusable complete route.
- **ARTIFACTS:** `agents/autonomous_next/top50_raw_55884271.py`,
  `experiments/autonomous_raw_55884271_probe.json`.

## 2026-09-01 — Checkpoint-resumable commitment executor safety stage

- **HYPOTHESIS:** a narrow state-based executor can take over a real
  CurrentBest checkpoint, preserve visible crop/livestock commitments, and
  finish without the animal-loss cascade seen in `goal_executor_v1`.
- **IMPLEMENTATION:** `agents/checkpoint_executor/commitment_executor_v1.py`
  reconstructs live objects, hires only workload-required hands, distributes
  observed wheat, protects FEED/WATER deadlines, uses fertilizer as a low-cash
  recovery asset, and enters a reserve-aware terminal liquidation mode.  It
  does not create optional land/animal/crop commitments.
- **RESUME TEST:** 32 conditions (seeds 51000/51001, both seats, checkpoints
  24/72/120/168/240/360/480/600).  Runtime failures **0**, semantic failures
  **0**, animal-loss games **0**, terminal-stranding games **0**.  Mean own
  money was 20,556 versus 53,267 for the original continuation (mean gap
  -32,710), showing safe but conservative continuation.
- **PERTURBATION TEST:** 24 fresh valid action-level perturbations on seed
  52002 (both seats, checkpoints 24/72/120).  Runtime/semantic failures,
  animal losses, and terminal stranding were all **0**.  22/24 rows applied a
  matching perturbation; two omitted-buy rows correctly remained unchanged
  because no such baseline order existed.
- **COMMITMENT AUDIT:** 12 conditions on seed 53000.  Runtime/semantic
  failures **0**, animal commitment-loss conditions **0**, crop
  commitment-loss conditions **0**, maximum consecutive-unfed **1**,
  consecutive-unwatered **1**, terminal-stranding conditions **0**.
- **INTERPRETATION:** the original failure was execution integrity: feed
  logistics, capital recovery, and worker workload—not action schema.  The
  revised controller is safety-capable, but it intentionally stops optional
  production and therefore trails CurrentBest materially.  This is a safety
  harness, not a promoted strategy.
- **DECISION:** Resume, Perturbation, and Commitment gates pass.  Top-player
  interventions and oracle/headroom are **NOT RUN** because the executor does
  not yet own new crop/land/livestock commitments; running them would conflate
  recovery with strategy improvement.  CurrentBest and `submission/main.py`
  remain unchanged; no Kaggle submission occurred.
- **ARTIFACTS:** `experiments/checkpoint_executor_design.md`,
  `experiments/checkpoint_executor_resume_results.json`,
  `experiments/checkpoint_executor_perturbation_results.json`,
  `experiments/checkpoint_executor_commitment_audit.json`,
  `experiments/checkpoint_executor_safety.json`,
  `experiments/checkpoint_executor_recovery_analysis.json`,
  `experiments/checkpoint_executor_report.md`,
  `run_checkpoint_executor_perturbation.py`, and
  `audit_checkpoint_executor_commitments.py`.

## 2026-09-01 — Optional crop-lifecycle capability falsification

- **HYPOTHESIS:** the passive continuation gap is dominated by missing crop
  production, so the smallest useful state-based commitment is one complete
  wheat lifecycle (seed → plant → service → harvest → drop/sell) layered on
  top of the proven safety executor.
- **IMPLEMENTATION:** `agents/checkpoint_executor/crop_lifecycle_v1.py`
  admits at most one observed empty tile, keeps all existing commitments
  authoritative, and overrides only an idle (`PASS`) unit.  It buys no land,
  animals, fertilizer, or other crops.  `run_checkpoint_executor_lifecycle.py`
  performs paired checkpoint takeovers without editing simulator state.
- **CHEAP SCREEN:** 16 conditions on seeds 55000/55001, checkpoints 24/72/120/168,
  both seats, versus the passive executor control.  Runtime failures **0**,
  semantic failures **0**, animal losses **0**, terminal stranding **0**.
  Four admissions all acquired a seed, planted, and harvested (100% lifecycle
  realization).  Mean own-money delta was **−274.1** (median 0, P10 −2,758.5),
  so the capability was safe but not economically useful.
- **SAFETY RETEST:** 16 valid perturbation/commitment conditions on fresh seed
  55002, checkpoints 24/72, both seats.  Runtime/semantic failures,
  pre-existing crop losses, animal losses, and terminal stranding were all
  **0**; max consecutive unfed/unwatered was **1**.
- **INTERPRETATION:** one wheat tile has too little gross value to offset
  persistent-worker movement and occasional interference with high-value
  livestock/crop service.  The first capability is therefore falsified as a
  recovery step, despite perfect safety.
- **DECISION:** no promotion and no changes to the frozen best or
  `submission/main.py`.  The next bottleneck is a compact multi-tile or
  premium lifecycle with explicit worker/capital reservation; Top-player
  interventions remain deferred.  No Kaggle submission occurred.
- **ARTIFACTS:** `experiments/checkpoint_executor_lifecycle_report.md`,
  `experiments/checkpoint_executor_lifecycle_screen.json`,
  `experiments/checkpoint_executor_lifecycle_safety.json`,
  `run_checkpoint_executor_lifecycle.py`,
  `run_checkpoint_executor_lifecycle_safety.py`.

## 2026-09-01 — Premium lifecycle probe and executor bottleneck confirmation

- **HYPOTHESIS:** a single premium MELON lifecycle may recover enough gross
  value to justify further continuation-executor work after the one-WHEAT
  lifecycle failed.
- **IMPLEMENTATION:** `agents/checkpoint_executor/premium_lifecycle_v1.py`
  adds one price- and capital-gated MELON commitment on top of the unchanged
  safety executor.  It selects a nearby empty tile and overrides only one
  persistent idle worker; all existing feed/water/harvest/drop/liquidation
  commitments remain delegated.
- **CHEAP SCREEN:** 16 paired conditions on fresh seeds 55003/55004,
  checkpoints 24/72/120/168, both seats, with the passive executor as control.
  Runtime/semantic failures **0**, animal losses **0**, and terminal inventory
  stranding **0**.  Admissions/seeds acquired were 8/8, but plantings/harvests
  were 8/4 (50% realization).  Mean candidate own money was 16,655.8 versus
  17,172.5 control (delta **−516.8**; median −40; P10 −1,987), and mean
  advantage delta was −935.6.
- **SAFETY RETEST:** 16 valid perturbation conditions on fresh seed 55005,
  checkpoints 24/72, both seats.  Runtime/semantic failures, animal losses,
  pre-existing crop losses, and terminal inventory stranding were all **0**;
  max consecutive unfed/unwatered was **1**.  Checkpoint-72 rows confirmed
  an economically incomplete melon lifecycle rather than a crash.
- **INTERPRETATION:** one premium crop has higher gross value than wheat but
  still cannot reliably repay its ten-day maturity, market-glut exposure, and
  worker-route interference.  Isolated lifecycle patches are not enough to
  recover the measured crop-revenue gap.
- **DECISION:** no promotion and no changes to the frozen best or
  `submission/main.py`.  The highest-value remaining direction is a coupled
  compact-cohort executor with explicit capital/worker/terminal reservation;
  do not add isolated crop actions or route splices.  No Kaggle submission
  occurred.

- **ARTIFACTS:** `experiments/autonomous_next_open_decision.md`,
  `experiments/autonomous_next_open_report.md`,
  `experiments/checkpoint_executor_premium_screen.json`,
  `experiments/checkpoint_executor_premium_safety.json`,
  `run_checkpoint_executor_lifecycle.py`, and
  `run_checkpoint_executor_lifecycle_safety.py`.

## 2026-09-01 — Autonomous compact-cohort headroom falsification

- **EVIDENCE REVIEW:** Complete-route families and market residuals had no
  durable own-money headroom (market oracle under 100 coins).  The safe
  checkpoint executor's remaining gap was dominated by omitted crop/animal
  production.  One wheat and one melon commitments were already safe but
  economically negative.
- **DECISION RECORD:** `experiments/autonomous_stage_decision.md` selected the
  cheapest meaningful falsifier: a capital-gated, co-located four-melon cohort
  with explicit worker slack, while preserving the frozen executor as the
  control and forbidding land/animal/route changes.
- **IMPLEMENTATION:**
  `agents/checkpoint_executor/compact_melon_cohort_v1.py` borrowed one PASS
  unit; v2 allowed up to three PASS units in parallel; v3 added one explicitly
  requested extra hand.  All candidates preserved the base executor's
  feed/water/harvest/drop/liquidation authority and emitted the documented
  action schema.
- **RESULTS:** v1 (16 paired conditions, seeds 56000–56001, checkpoints
  24/72/120/168) averaged **−464.4** own coins with 75% per-admission harvest
  realization.  v2 averaged **+44.7** on its 16-condition development panel
  (bootstrap 95% CI **[−244.4, +461.8]**) but harvested only 50% of target
  tiles.  On eight fresh held-out checkpoint-24 conditions (seeds
  56030–56033, both seats), v2 averaged **−2,319.5** (median −2,297,
  P10 −5,785, bootstrap CI **[−4,180.8, −379.3]**; 75% negative).
  v3's extra hand averaged **−548.6** (CI **[−1,359.0, −4.2]**) with 37.5%
  per-admission harvest realization.
- **SAFETY:** Across all candidate/control rows there were zero runtime
  failures and zero semantic failures.  Held-out v2 had zero candidate animal
  losses and zero terminal-stranding conditions.  No frontier panel was opened:
  the cheap signal was below the +1,000-coin gate and fresh confirmation was
  negative.
- **ECONOMIC INTERPRETATION:** Parallel ownership reduced contention but did
  not make a complete cohort executable; most admissions harvested only one or
  two of four melons.  The extra worker added cost without improving
  realization.  The theoretical 5,680-coin gross ceiling therefore was not
  reachable under the partial-ownership interface.  This rejects isolated
  cohort expansion as the next architecture, not melon economics in a fully
  coherent route.
- **DECISION:** No candidate promoted.  Frozen CurrentBest
  (`agents/top50_distilled/top50_observable_portfolio.py`) and
  `submission/main.py` remained unchanged; no Kaggle submission occurred.
  Complete report: `experiments/autonomous_next_stage_report.md`; machine
  readable screens: `experiments/autonomous_compact_cohort*_*.json`.

## 2026-09-01 — Open autonomous research stage closure

- **Frozen state:** CurrentBest remained
  `agents/top50_distilled/top50_observable_portfolio.py` (SHA-256
  `f9ca672848ccffdfe56888d99bcdf5a9d7644062b9eec0cf0cdea13574931233`).
  The existing `submission/main.py` remained byte-identical at SHA-256
  `789bb9bbd5122eb4891983e776a13777328e3e87736cbbc0b4bc86d13fc33f9b`.
  No Kaggle upload or submission API was called.
- **Question:** determine whether the remaining value was in route diversity,
  executor realization, Top-3 imitation, SELL sequencing, or a new adaptive
  economic program.  The stage reviewed the README/AGENTS instructions, all
  accumulated reports and logs, the Top-3/Top-50 corpora, V2/V3/V4 lineages,
  and checkpoint-executor artifacts.  No separate V5/V6/V7/V8 artifacts were
  present.
- **Route oracle:** 23 complete routes on seeds 56300–56301, both seats (92
  games).  Hindsight best improved own money by +18,906.5, but the winning
  route changed by seed.  Fresh whole-route validation on seeds 56310–56313
  reversed the three selected routes to -10,939, -4,008, and -4,279 own
  coins (P10 -44,933, -35,334, -35,939 respectively), despite ~100% route
  realization and zero safety failures.
- **Top-3 transfer:** 24 fresh games (56400–56403, both seats) gave tetsuya
  0/8, Crop Dusta 2/6, and OceanMix 0/8 versus CurrentBest, with mean
  advantages -22,384, -28,592, and -5,313.  Replay history remains predictive
  (phase F1 0.973; decision F1 0.839) but no causal delegation was enabled.
- **Market residual:** 192 full games on seeds 50800–50807.  Same-turn SELL
  reordering changed zero actions and zero money.  A bounded future-slot
  residual made 611 assignments but lost 954 own coins (bootstrap CI
  [-1,629, -367]).
- **Lifecycle executor:** compact melon cohorts were safe but realized only
  37.5–50% of target harvests; held-out v2 was -2,320 own coins (P10 -5,785).
  The broad goal executor remained unsafe (28/28 animal-loss games, P10
  -132,772); the commitment executor preserved observed commitments with zero
  safety failures but omitted profitable production.
- **Decision:** H1 static route transfer, H3 direct Top-3 package transfer,
  H4 SELL sequencing, broad planner takeover, and isolated lifecycle patches
  were rejected.  H2 executor realization and H6 lifecycle ownership remain
  real mechanisms; H5 regime-conditioned complete economic-program control is
  the highest-value surviving direction.  Primitive RL, fitted-Q, and
  self-play are not justified before a coherent high-level oracle exists.
- **Promotion:** none.  CurrentBest remains the retained research best; all
  candidates failed robust own-money/tail or realization gates.
- **Report:** `experiments/autonomous_open_stage_report.md` contains the
  hypotheses, diagnostics, attribution, tails, candidate table, and the
  requested 34-point final answer.  Existing route/cohort/residual JSON
  artifacts remain unchanged.

## 2026-09-02 — Economic-program executor safety repair and counterfactual

- **CANDIDATE:** `agents/economic_program/economic_program_executor_v1.py`
  (research-only; frozen CurrentBest and `submission/main.py` unchanged).
- **DIAGNOSIS:** At checkpoint day-rollovers, wheat carriers could choose
  `PICKUP_WHEAT` over an executable overdue `FEED`, causing a sheep escape at
  step 600 despite available feed.  A local feed-carrier priority fixed the
  failure.  A separate late-checkpoint crop weed was reproduced with the
  base executor and is an inherited dense-state boundary, not a candidate
  regression.
- **VALIDATION:** 16 fresh takeover conditions (seeds 57210–57213,
  checkpoints 72/120, both seats) had 0 runtime failures, 0 semantic
  failures, 0 animal losses, 0 pre-existing crop losses, and 0 terminal
  stranding.  Eight checkpoint-72 cohorts completed 32/32 plantings and
  harvests (100% realization among admissions), averaging +13,895 own coins
  versus the passive commitment executor.
- **COUNTERFACTUAL:** Against uninterrupted CurrentBest on the same seeds,
  the takeover averaged **−58,226.6** own coins (checkpoint 72: −51,784.5;
  checkpoint 120: −64,668.8; P10 −66,058.5).  The safe cohort capability is
  therefore not competitive and was not promoted.
- **DECISION:** Keep CurrentBest and `submission/main.py` frozen.  A coherent
  state owner that preserves the full crop/livestock economy is required
  before further isolated lifecycle expansion.  No Kaggle submission.
- **ARTIFACTS:** `agents/economic_program/economic_program_executor_v1.py`,
  `run_economic_program_executor.py`,
  `run_economic_program_counterfactual.py`,
  `experiments/economic_program_executor_report.md`, and the corresponding
  probe/screen/counterfactual JSON files.

## 2026-09-02 — CurrentBest-preserving overlay falsification

- **HYPOTHESIS:** A bounded melon cohort may have positive value if it uses
  only PASS units and unused market slots while CurrentBest continues its
  complete route.
- **IMPLEMENTATION:** `agents/economic_program/currentbest_overlay_v1.py`
  exposes `make_agent(base_agent)`; `run_currentbest_overlay.py` binds it to
  the same opener instance, preserving route state across the checkpoint.
- **RESULT:** 16 conditions (seeds 57210–57213, checkpoints 72/120, both
  seats) had 0 runtime failures and 0 semantic failures.  The overlay's mean
  own-money delta versus uninterrupted CurrentBest was **−430.25** (median
  −434, P10 −441).  It admitted 16 cohorts but realized only 25% of target
  tiles on average, because CurrentBest left too little executable slack.
- **DECISION:** Reject isolated PASS-only cohort overlays; they are much safer
  than full takeover but still economically negative.  A useful next
  architecture must own a coherent territory/labor budget together with the
  existing crop and livestock commitments.  No promotion, submission change,
  or Kaggle upload.
- **ARTIFACTS:** `agents/economic_program/currentbest_overlay_v1.py`,
  `run_currentbest_overlay.py`,
  `experiments/currentbest_overlay_counterfactual.json`, and the expanded
  executor report.

## 2026-09-02 — Territory lifecycle scheduler ablation (S0–S3)

- **FROZEN CONTROL:** `agents/top50_distilled/top50_observable_portfolio.py`.
  `submission/main.py` and all existing strategy files were preserved.
- **ROUTING EVIDENCE:** the completed public replay audit measured 0.94, 0.95,
  and 1.15 movement/productive actions at 25/50/75 unlocked-tile scale,
  respectively.  The 75-tile population had 100% territory purity, so the
  experiment tested whether local lifecycle ownership—not static remapping—was
  the missing mechanism.
- **CANDIDATES:** S0 exact control; S1 persistent territories; S2 S1 plus
  one-refresh watering deadline rescue; S3 S2 plus same-worker harvest→replant
  chaining and cohort priority.  Market/economic orders, opening, animals,
  land, feed, and terminal logic were inherited unchanged.
- **SAFETY SCREEN:** four recorded real-loss opponents, both seats (32 games)
  completed with zero runtime, semantic, and livestock failures.  S0/S1/S2/S3
  all went 8/0/0; S1 was action-equivalent in outcome, while S2/S3 changed
  only a small set of near-deadline movements.
- **HELD-OUT HARD PANEL:** fresh seeds 981100–981103, both seats, six strong
  local route families plus the recorded cases (224 games per full panel).
  S0: **48/0/8**, +18,936 average advantage, P10 0, 352.0 harvests; S1 was
  identical.  S2/S3: **48/8/0**, +18,862 average advantage, P10 −38.5,
  351.4 harvests, and no crop-revenue gain.  All variants had zero runtime,
  semantic, and livestock failures.
- **DIAGNOSTICS:** S2/S3 issued 272 urgent overrides but slightly increased
  watering misses and lost eight ties against `top50_redblack`; S3 realized
  zero actual chain plantings.  The route's hidden animal/crop commitments
  leave no reliable slack for a scheduler-only overlay.
- **DECISION:** no promotion.  S0/CurrentBest remains strongest and safest;
  S1 is retained only as a no-op control, and S2/S3 are rejected.  The next
  useful direction is a coherent state owner for a bounded crop cohort with
  explicit worker, capital, feed, and terminal reservations—not another
  movement patch.  Full report: `experiments/territory_lifecycle_report.md`;
  machine-readable results: `experiments/territory_lifecycle_heldout.json`.

## 2026-09-02 — Prefix-compatible adaptive route probe

- **CANDIDATE:** `agents/autonomous_next/prefix_adaptive_portfolio_v1.py`,
  SHA-256 `e26eb35c2857f3045c5fa42301511c50570bf14d05dfca72cc3183183d0aea9f`.
  CurrentBest remained
  `agents/top50_distilled/top50_observable_portfolio.py` (SHA-256
  `f9ca672848ccffdfe56888d99bcdf5a9d7644062b9eec0cf0cdea13574931233`).
- **DESIGN:** preserve the observable step-1 anchor and allow one switch at
  turn 72 only among complete routes whose actions are exactly identical
  through turn 71.  Rank compatible continuations using current prices,
  market inventory, and visible opponent product pressure.  No strategy,
  source agent, or `submission/main.py` was modified.
- **BENCHMARK:** 64 complete 720-turn games on deterministic seeds 61000 and
  61001, both seats, against CurrentBest, tetsuya, Crop Dusta, OceanMix,
  livestock/crop, land-expander, high-labor, and phased-rotation.  Runtime and
  benchmark call-count failures were zero.
- **RESULT:** CurrentBest 26/2/4, average money 122,953.1, average advantage
  +73,991.4, P10 0.0.  The candidate 26/6/0, average money 126,360.1,
  average advantage +73,481.1, P10 -4,917.4, P5 -7,605.8, worst -10,391.
  Own-money mean was +3,406.9 versus CurrentBest, but the relative advantage
  and lower tail regressed.
- **DIAGNOSTIC:** the selector switched in all four CurrentBest matchups and
  all four OceanMix matchups, and never switched against the other six
  opponents.  The paired mean advantage delta was -7,859 versus CurrentBest
  and -4,792 versus OceanMix.  This shows that exact-prefix compatibility
  prevents desynchronization but does not make a partial SELL/market score
  economically reliable under shared-market interaction.
- **DECISION:** **reject; do not promote.**  Keep the candidate as a negative
  probe.  The next useful architecture is a checkpoint-resume/state-owner
  proof that explicitly carries crop cohorts, livestock, workers, capital,
  inventory, and terminal commitments.  Do not tune the selector or launch a
  broad sweep until that ownership is demonstrated.  Full decision record:
  `experiments/prefix_adaptive_decision.md`; machine-readable results:
  `experiments/prefix_adaptive_dev.json`.

## 2026-09-02 — Coherent checkpoint owner and replacement-capacity proof

- **GOAL:** test a minimal state-owner architecture for the day 10–20 crop
  throughput gap without changing the opening, livestock, land, market, or
  endgame logic.  The candidate could admit at most two MELON replacements on
  recently vacated tiles.
- **CANDIDATES:** `agents/autonomous_next/coherent_state_owner_v1.py` was the
  initial full-owner attempt.  It was retained as a diagnostic after exposing
  shadow-state contamination and optional-task watering interference.
  `agents/autonomous_next/coherent_state_owner_v2.py` is the strict repair:
  separate shadow/live executors, cold-start base commitments, seed-slot
  reservation, two recent vacancies, two free PASS units, and overrides only
  for PASS units.  Existing base actions are never reordered or discarded.
- **SCREEN:** 16 paired 720-turn conditions on seeds 57300–57301, checkpoints
  240/264/288/312, both seats.  Control was the passive commitment executor
  from the same checkpoint.  v2 had zero runtime failures, zero semantic
  failures, zero animal losses, zero incremental crop losses, and zero
  terminal stranding.  Mean/median/P10/P5 own-money and advantage deltas were
  all **0.0**; the strict gate admitted 0 programs, planted 0 replacements,
  and harvested 0 replacements.
- **EQUIVALENCE:** two full action-level comparisons (seed 57300 seat 0 at
  checkpoint 264: 455 actions; seed 57301 seat 1 at checkpoint 288: 431
  actions) had 0 mismatches, 0 semantic failures, and identical final money
  (16,794 and 6,611 respectively).  Both episodes completed all 720 steps.
- **CAUSAL FINDING:** after mandatory watering, harvest, feed, care,
  fertilizer, inventory, and terminal work are reserved, CurrentBest exposes
  no reliable two-unit PASS capacity at these checkpoints.  Borrowed-cohort
  overlays therefore cannot raise crop throughput safely; a complete route
  owner must reserve the worker/crop budget before day 10.
- **DECISION:** no promotion and no held-out expansion.  Keep CurrentBest and
  `submission/main.py` frozen.  The coherent-owner proof is safe but
  economically neutral; do not tune its zero-admission thresholds or launch a
  broad sweep.  Full report: `experiments/coherent_state_owner_report.md`;
  final machine-readable result: `experiments/coherent_state_owner_screen_v9.json`.

## 2026-09-02 — End-to-end pre-opening reservation owner

- **GOAL:** test whether declaring worker/crop capacity before day 10 can
  realize a controlled lifecycle that a checkpoint overlay could not safely
  borrow. The frozen CurrentBest remained
  `agents/top50_distilled/top50_observable_portfolio.py`; `submission/main.py`
  was unchanged.
- **CONTROL OWNER:** `agents/autonomous_next/end_to_end_owner_v1.py` records a
  day-0 farmer/WHEAT reservation and complete per-unit commitment ledger while
  returning the frozen action unchanged. Four full 720-turn comparisons
  (seeds 57400–57401, both seats) covered all 719 actions with **0 mismatches**,
  identical final money, and 0 schema failures.
- **CANDIDATE:** `agents/autonomous_next/end_to_end_owner_crop_v1.py` consumes
  one reserved farmer slot after step 240 for a single capital-gated WHEAT
  cycle. It changes no land, animal, fertilizer, or unrelated economic policy
  and admits only when the base route leaves a real PASS lane.
- **SCREEN:** development seeds 57400–57403, both seats (8 paired games):
  8/8 admissions, plantings, harvests, and sell requests; 0 runtime/schema
  failures; 0 animal losses; mean own-money delta **+25.75**, median +24.5,
  P10 +23.0. Held-out seeds 57500–57501 (4 games) retained full realization
  and mean delta **+29.5** (median/P10 +29.5/+29.0).
- **HARD PANEL:** seeds 57510–57511, both seats, six opponents (24 games):
  mean own-money delta +2.67, median 0, P10 −2.0, mean advantage delta +4.58;
  0 runtime/schema/animal-loss failures. Per-opponent deltas were 0 vs
  tetsuya/Crop Dusta, +20 vs OceanMix, −2.5 vs livestock/crop, −1 vs
  land-expander, and −0.5 vs high-labor. Terminal inventory value matched
  control on every condition (12 coins inherited from the route).
- **DECISION:** **do not promote**. Pre-opening ownership is safe and turns
  a zero-admission overlay into a fully realized one-tile cycle, but the value
  is only 25–30 coins and not a breakthrough. The unresolved gap is a larger
  coherent pre-day-10 cohort with reserved capital, tiles, watering lanes,
  harvest timing, and market exposure. Full report:
  `experiments/end_to_end_owner_report.md`; machine-readable screens:
  `experiments/end_to_end_owner_screen_v1.json`,
  `experiments/end_to_end_owner_heldout.json`, and
  `experiments/end_to_end_owner_league.json`.

## 2026-09-02 — End-to-end two-tile cohort owner screen

- **GOAL:** test whether reserving two worker slots and two WHEAT tiles from
  turn 0 could safely add a second pre-opening lifecycle without changing the
  frozen replay portfolio's economic decisions.
- **CANDIDATE:** `agents/autonomous_next/end_to_end_owner_cohort_v1.py`;
  it admitted only on inherited `PASS` lanes between steps 240–360, protected
  its targets, and sold any realized cohort output.  Land, animals, fertilizer,
  hiring, and the inherited market policy were unchanged.
- **SCREEN:** seeds 57600–57603, both seats, 8 complete paired 720-step games.
  Runtime failures **0**, schema failures **0**, animal-loss conditions **0**.
  Admissions **8**, but actual candidate plant actions **0**; the owner only
  observed two inherited harvests per condition and issued bounded sell
  requests.
- **RESULT:** mean own-money delta **−1,442.5**, median **−456.5**, P10
  **−4,552.0**, mean advantage delta **−1,768.5**.  Candidate money was lower
  on every tested seed.  Terminal inventory value was 11 coins for the
  candidate versus 12 for control, so no additional stranded cohort value was
  introduced.
- **DECISION:** **reject; do not promote or run a larger confirmation.**  The
  route exposes no reliable free worker lane for this overlay, so no new crop
  cycle was realized.  A future improvement would need a complete pre-opening
  owner of capital, tiles, worker lanes, lifecycle timing, shed capacity, and
  sale exposure; keep CurrentBest and `submission/main.py` unchanged.  Full
  report: `experiments/end_to_end_owner_cohort_report.md`; machine-readable
  result: `experiments/end_to_end_owner_cohort_screen.json`.

## 2026-09-02 — Pre-opening future-quadrant wheat owner probe

- **GOAL:** test a genuinely pre-reserved cohort by declaring two future NE
  tiles and a tail worker lane at step 0, then funding and executing two WHEAT
  lifecycles after first-land unlock.
- **CANDIDATE:** `agents/autonomous_next/preopening_owner_wheat_v1.py` layered
  the frozen observable portfolio and changed no source route or submission.
  It bought two seeds when capital/market slots allowed, protected the
  reserved tiles, and handled watering, harvest, and sales with the reserved
  lane.
- **SCREEN:** seeds 57700–57703, both seats (8 complete 720-step games).
  Runtime/schema failures **0**, animal-loss conditions **0**.  Admissions
  8/8, plantings 16, watering actions 32, harvest actions 16 (32 units).
- **RESULT:** mean own-money delta **+6,581.75**, median +4,495.5, P10
  **−2,619.0**, but mean advantage delta **−4,211.25**.  On every seed the
  opponent's money increased more than the candidate's (opponent deltas
  +2,235 to +24,582), so the candidate became less competitive despite
  positive own-money deltas on three seeds.  Terminal inventory value was 16
  versus 12 for control, leaving four additional coins of unsold value.
- **DECISION:** **reject; no held-out confirmation or promotion.**  The
  lifecycle can be realized, but replacing the route's tail worker changes
  shared-market/worker state and transfers more value to the opponent while
  failing to reserve terminal sale capacity.  A meaningful successor must own
  the entire opening route and reserve crop, worker, shed, and market capacity
  together.  Full report: `experiments/preopening_owner_wheat_report.md`;
  machine-readable result: `experiments/preopening_owner_wheat_screen.json`.

## 2026-09-02 — Pre-opening owner capacity audit

- **SCOPE:** offline inspection of all 23 routes in
  `experiments/top50_route_bank.json` for steps 0–263.  No simulator games,
  strategy changes, or submission changes were made.
- **MEASURED:** first-land timing, daily maximum hand counts, market-order
  headroom for an additional seed-plus-hire pair, hire headroom, and turns
  containing a PASS unit.  All 23 routes unlock first land around step 150
  (the few medoids with earlier/later milestones remain route-specific), and
  every route has some market headroom, but none guarantees a free slot on
  every daily reinvestment turn.  Daily maximum hands are already 3–7 by day
  2, 6–8 by day 6, and 11–12 by day 10.
- **INTERPRETATION:** the NW quadrant is full by day 2, so any additional
  pre-opening crop must reserve a future-quadrant tile.  A second worker also
  needs a recurring daily market slot; when the route emits ten orders, an
  overlay must displace a purchase or hire.  PASS lanes are intermittent and
  are not proof of spare capacity because crop/animal deadlines can claim
  them later.
- **DECISION:** use this audit to constrain, not broaden, the next design.  A
  viable cohort requires a complete route owner that reserves future land,
  worker capacity, seed capital, watering/harvest lanes, and terminal sale
  slots together.  Do not continue adding tail-worker overlays to the frozen
  portfolio.  Full audit: `experiments/preopening_owner_capacity_audit.md`;
  machine-readable data: `experiments/preopening_owner_capacity_audit.json`.

## 2026-09-02 — Additional-worker melon owner probe

- **GOAL:** test whether a genuinely additional worker lane (rather than
  borrowing an inherited tail hand) can add one reserved NE MELON lifecycle to
  the frozen observable portfolio.
- **CANDIDATE:** `agents/autonomous_next/extra_hand_melon_owner_v1.py`; it
  reserved one future tile, admitted after first-land unlock, hired one hand
  when a market slot and cash buffer were available, and attempted the full
  plant → water → harvest → shed → sell lifecycle. The baseline route,
  `agents/top50_distilled/top50_observable_portfolio.py`, and
  `submission/main.py` were not modified.
- **SCREEN:** seeds 57800–57803, both seats (8 complete 720-step games).
  Runtime/schema failures **0**, animal-loss conditions **0**. Admissions 8,
  extra-hand confirmations 192 (24 per game), plantings 8, but watering 0,
  harvests 0, and sell requests 0.
- **RESULT:** mean own-money delta **−3,005.75**, median **−3,117.5**, P10
  **−4,138**, and mean advantage delta **−6,957.5**. Candidate money was
  lower on every seed; terminal inventory value remained 12 coins.
- **DECISION:** **reject; no held-out confirmation or promotion.** The
  inherited deadline guard blocked the overlay after planting, so the extra
  hand incurred recurring hire costs without realizing a crop cycle. This is
  a scheduling/ownership failure, not a crop-economics result. A successor
  must reserve the complete recurring lane and sale capacity together. Full
  report: `experiments/extra_hand_melon_owner_report.md`; machine-readable
  screen: `experiments/extra_hand_melon_owner_screen.json`.

## 2026-09-02 — Top-10 public strategy research and adjustment

- **EVIDENCE:** reused the complete downloaded V3 Top-10 corpus (10 selected
  submission versions, 126 valid unique replays, 82 deduplicated development
  appearances, 3 structural families, zero financial-reconstruction
  mismatches). The new synthesis is generated by `analyze_top10_meta.py` and
  saved as `experiments/top10_meta_summary.json` and
  `experiments/top10_meta_summary.md`.
- **CONSENSUS:** all ten routes use a three-quadrant melon/strawberry economy,
  first land at steps 144–160, second land at 217–264, mixed cows and sheep,
  high labor, and final liquidation. Ranks 1 and 2 are genuinely adaptive;
  ranks 3–10 largely form a stable 160/240 JALKARNA-like family. This confirms
  the capital skeleton but does not justify a universal earlier-land, cow, or
  labor change.
- **ADJUSTMENT:** the raw JALKARNA parent was rejected after a direct
  low-bank/four-hand diagnostic showed repeated livestock losses. A safer probe
  `agents/autonomous_next/top10_lowbank_hanserong_v1.py` routed that signature
  to the proven Hanserong parent at step 1, leaving all other states on the
  frozen selector.
- **SCREEN:** seeds 57900–57901, both seats, fixed and natural shops, all ten
  Top-10 route opponents plus seven hard local opponents (272 complete games).
  Runtime/schema failures were 0. CurrentBest was 130/6/0 with 112,963 mean
  money and +42,681 mean advantage. The adjustment was 102/34/0 with 114,176
  mean money and +39,538 mean advantage; paired own-money delta +1,212.5 but
  paired advantage delta −3,143.1, P10 −5,567, and 64 livestock losses.
- **DECISION:** **reject; do not promote.** The higher own bank is a
  shared-market artifact and comes with a weaker competitive tail and unsafe
  animal realization. Keep `agents/top50_distilled/top50_observable_portfolio.py`
  and `submission/main.py` unchanged. Full report:
  `experiments/top10_strategy_research.md`; machine-readable screen:
  `experiments/top10_lowbank_hanserong_screen.json`.
