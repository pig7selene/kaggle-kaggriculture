# Livestock economic-compounding milestone

## Outcome

`agents/animal_c2_cows.py` is the new robust local best. It keeps the phased
crop schedule, builds four pasture structures during the opening, and buys four
cows after the first melon harvest on day 11. In the final held-out evaluation
it won all 288 games, including 32–0 against `proxy_livestock_crop` with a
+6,690.59 average advantage.

No submission was created or sent.

## Why the old phased agent lost

The transaction-level diagnosis used seeds 8000–8015 in both seats, for 32
matched games. The original proxy advantage was +8,125.41.

| Component per game | `adaptive_c_phased` | Livestock proxy | Proxy minus baseline |
| --- | ---: | ---: | ---: |
| Crop revenue | 25,218.00 | 18,670.25 | -6,547.75 |
| Animal-product revenue | 0.00 | 16,145.00 | +16,145.00 |
| Fertilizer revenue | 0.00 | 6,258.00 | +6,258.00 |
| Seed spending | 2,976.88 | 4,760.94 | +1,784.06 cost |
| Animal spending | 0.00 | 1,600.00 | +1,600.00 cost |
| Labor spending | 60.00 | 360.00 | +300.00 cost |
| Land spending | 0.00 | 1,000.00 | +1,000.00 cost |
| Bought-feed spending | 0.00 | 3,045.78 | +3,045.78 cost |

The proxy did not win because its crop operation was more profitable: it earned
about 6,548 fewer crop-revenue coins. It won because milk plus fertilizer added
22,403 gross coins. After the extra 7,730 of seeds, cows, land, labor, and feed,
that recurring income left the observed 8,125 advantage.

The timing is exact and stable across the matched set:

- Day 11: the proxy obtains a durable cumulative-income lead after its larger
  first melon sale, then spends the proceeds on land, four cows, feed, and more
  crop slots. Its bank remains behind because of that capital outlay.
- Day 13: daily fertilizer sales begin contributing roughly 300–400 coins per
  day.
- Day 18: bank plus marked-to-market inventory becomes durably higher for the
  proxy.
- Day 20: the first cared-milk payout contributes about 4,650 milk coins plus
  377 fertilizer coins. The proxy bank crosses the baseline and remains ahead.

The complete 30-row decomposition is in
`experiments/livestock_gap_diagnosis.md` and its JSON companion.

## Hubbahub evidence

Replay 91705498 was reproduced exactly at 50,801 final coins using its recorded
actions and seed.

- Seven pastures were built on day 0 and two more on day 11.
- One cow was bought on day 0; eleven more were bought on day 11. Seven cows
  were placed, while five excess cows remained in the final shed.
- Five of seven placed cows were fed on day 11; all seven were fed and cared
  for daily from day 12 onward.
- Milk was harvested from all seven cows on days 19, 21, 23, 25, 27, and 29.
- Milk sales began on day 20, ended on day 28, and returned 14,361 coins for
  120 units. Fertilizer returned 10,189 coins for 115 units.
- Bought feed cost 8,442 coins. Cow purchases cost 4,800 coins.
- Milk plus fertilizer minus cow and feed purchases contributed an estimated
  +11,308 direct net coins, 23.7% of the money earned above the 3,000 start.

This supports cows as a compounding side economy, but also exposes waste in the
replay: excess animal purchases and structures are not required for the return.

## Controlled animal search

The staged tuning search used seeds 8600–8603, both seats, and five focused
opponents. It evaluated 67 type/count/timing configurations, 36
feed/care/fertilizer/harvest policies, 38 feed/capital/selling variants, and 25
adaptive-selection variants.

### Animal-only controls

| Control | Avg money | Avg advantage | Livestock-proxy advantage |
| --- | ---: | ---: | ---: |
| Four geese only | 17,476.88 | -18,184.42 | -29,459.75 |
| Four cows only | 34,231.12 | -365.45 | -11,295.38 |
| Four sheep only | 25,756.22 | -9,906.30 | -14,517.50 |

Animals alone did not create a robust strategy. Cows were the strongest
standalone economy, but the crop opening is needed to fund and complement them.

### Policy findings

- Four cows were the strongest species/count combination.
- Daily feeding, daily care, and daily fertilizer collection were all material.
  Removing fertilizer dropped focused-pool income by about 13,243 coins and
  restored a negative livestock matchup. Survival/production-only feeding and
  reduced care each lost roughly 11,000 coins versus the best care loop.
- Harvest thresholds of one and three were effectively tied when two workers
  serviced four cows; terminal liquidation correctness mattered more.
- A two-day market-wheat reserve was best. One day was operationally fragile.
  Self-grown and mixed feed lost roughly 14,000 or more coins because feed plots
  displaced higher-value crops and added watering/harvesting work.
- Early cows maximized mean income in tuning, but were much more variable on
  held-out seeds. Waiting for the first melon harvest preserved opening capital
  and was the robust winner.
- Holding animal products to 1.10x base for at most two days was best in the
  tuning block, but the robust day-11 candidate's default aware policy was more
  consistent across the final pool.
- The adaptive selector often chose geese because its long-horizon economic
  estimate still underprices animal-service workload and premium batch timing.
  It did not beat the fixed cow policy.

## Final held-out benchmark

Final code used seeds 8900–8915, both positions, nine opponents (the frozen
eight-agent pool plus `adaptive_c_phased`), for 288 games per candidate.

| Rank | Candidate | W/L/T | Win rate | Avg money | Avg advantage | P10 advantage | Variance | Worst matchup |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | **C2 phased + day-11 cows** | **288/0/0** | **100.00%** | **42,255.72** | **+24,545.59** | **+23,328.92** | **16,018,773** | livestock 32–0, +6,690.59 |
| 2 | C3 phased + sheep | 285/3/0 | 98.96% | 39,070.25 | +21,227.79 | +20,428.22 | 5,985,951 | livestock 29–3, +3,348.31 |
| 3 | C4 tuned early cows | 281/7/0 | 97.57% | 47,505.35 | +21,266.85 | +17,407.11 | 52,612,225 | livestock 28–4, +5,123.28 |
| 4 | C5 adaptive animals | 264/24/0 | 91.67% | 37,381.56 | +17,906.66 | +16,947.69 | 6,343,592 | livestock 8–24, -1,548.66 |
| 5 | C1 phased + geese | 252/36/0 | 87.50% | 29,104.65 | +11,217.78 | +10,501.36 | 5,079,737 | livestock 1–31, -7,379.22 |
| 6 | C0 unchanged phased | 228/36/24 | 79.17% | 27,907.84 | +10,476.38 | +9,973.06 | 5,046,584 | livestock 0–32, -7,398.34 |

C2 also beat `adaptive_c_phased` 32–0 with +14,096.59 average advantage.
Its worst-matchup P10 advantage against the livestock proxy was still +5,238.

## C2 component economics

Against the livestock proxy, C2 earned +1,473.63 more crop revenue, +2,653.56
more milk revenue, and 224.34 less fertilizer revenue. It saved 1,521.25 on
seeds, 300 on labor, and 1,000 on land while spending only 33.50 more on feed.
Those components reconcile to its +6,690.59 final advantage.

Against unchanged `adaptive_c_phased`, cows reduced crop revenue by 5,205.56
because two workers service animals, but added 18,261.81 milk revenue and
5,997 fertilizer revenue. After 1,600 for cows, 3,122.59 for feed, and 234.06
extra seed spending, the net improvement was +14,096.59. Direct cow cash flow
paid back on day 20.

Complete artifacts:

- `experiments/livestock_gap_diagnosis.json` / `.md`
- `experiments/animal_parameter_search.json`
- `experiments/adaptive_animal_selection_search.json`
- `experiments/animal_pool_final_code_unseen_16_seeds.json` / `.md`
- `experiments/animal_c2_final_economic_decomposition.json` / `.md`

## Decision and remaining risks

C2 satisfies all three replacement gates: it materially reverses the livestock
matchup, does not regress elsewhere, and repeats the gain on unseen seeds. It is
therefore recorded as the new local best in `experiments/current_best.json`.

The evidence is strong enough to justify preparing a Kaggle submission in a
separate milestone. Remaining risks are that the pool contains only one
livestock proxy, real opponents may produce enough milk to create a harsher
glut, the adaptive animal selector remains miscalibrated, and the real replay
sample still contains only one cow-heavy opponent. No submission was prepared
or sent during this milestone.
