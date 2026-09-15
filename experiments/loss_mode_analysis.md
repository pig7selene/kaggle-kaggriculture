# Loss-mode analysis, submission 56183575

136 official episodes. 109 wins, 26 losses. A sale is 'distressed' below 25% of the step-0 base price.

| Metric | losses | worst decile | wins | best decile |
| --- | ---: | ---: | ---: | ---: |
| Episodes | 26 | 13 | 109 | 13 |
| Median margin | -3,346 | -4,750 | +5,623 | +29,724 |
| Median step fell behind | 502 | 500 | - | - |
| Median concurrency share | 0.77 | 0.77 | 0.78 | 0.13 |

## Same-lineage opponents

Similarity is the Jaccard overlap of the (step, resource) sets each seat submitted SELL orders on: an identity signal, not an economic one. Two agents running the same tape order at the same steps, liquidation no-ops included.

Distribution over 136 episodes: min 0.060, p25 0.284, median 0.685, p75 0.759, max 1.000. A median of 0.68 means the ladder is largely forks of one public agent.

| Threshold | Group | N | W/L/T | GSR | Median margin |
| ---: | --- | ---: | ---: | ---: | ---: |
| 0.5 | mirror | 92 | 73/18/1 | 0.799 | +3,838 |
| 0.5 | non_mirror | 44 | 36/8/0 | 0.818 | +6,842 |
| 0.6 | mirror | 82 | 66/15/1 | 0.811 | +3,838 |
| 0.6 | non_mirror | 54 | 43/11/0 | 0.796 | +6,746 |
| 0.7 | mirror | 62 | 48/13/1 | 0.782 | +3,726 |
| 0.7 | non_mirror | 74 | 61/13/0 | 0.824 | +6,109 |

Mirror games are consistently closer, by roughly 3,000 of median margin at every threshold, which is what playing a near-copy of yourself should look like. The win-rate difference is not robust: it runs 0.02 to 0.04 and changes sign between thresholds, so these data do not support a claim that we lose disproportionately to our own lineage.

### STRAWBERRY

| Metric | losses | worst decile | wins | best decile |
| --- | ---: | ---: | ---: | ---: |
| Episodes selling | 26 | 13 | 109 | 13 |
| Median units sold | 28 | 28 | 28 | 28 |
| Median price vs base | 0.233 | 0.399 | 0.347 | 0.347 |
| Median distressed share | 0.80 | 0.07 | 0.39 | 0.64 |
| Median gross | 1,024 | 1,341 | 1,166 | 1,166 |

### MILK

| Metric | losses | worst decile | wins | best decile |
| --- | ---: | ---: | ---: | ---: |
| Episodes selling | 26 | 13 | 109 | 13 |
| Median units sold | 46 | 47 | 47 | 47 |
| Median price vs base | 0.142 | 0.604 | 0.149 | 0.119 |
| Median distressed share | 0.80 | 0.04 | 0.85 | 0.93 |
| Median gross | 1,035 | 4,541 | 1,165 | 873 |

### WOOL

| Metric | losses | worst decile | wins | best decile |
| --- | ---: | ---: | ---: | ---: |
| Episodes selling | 26 | 13 | 109 | 13 |
| Median units sold | 32 | 32 | 32 | 27 |
| Median price vs base | 0.092 | 0.071 | 0.359 | 0.458 |
| Median distressed share | 0.89 | 0.94 | 0.61 | 0.30 |
| Median gross | 580 | 457 | 2,496 | 2,695 |

### WHEAT

| Metric | losses | worst decile | wins | best decile |
| --- | ---: | ---: | ---: | ---: |
| Episodes selling | 26 | 13 | 109 | 13 |
| Median units sold | 223 | 223 | 223 | 223 |
| Median price vs base | 1.604 | 1.595 | 1.594 | 1.686 |
| Median distressed share | 0.00 | 0.00 | 0.00 | 0.00 |
| Median gross | 8,894 | 8,876 | 8,895 | 9,505 |

### CARROT

| Metric | losses | worst decile | wins | best decile |
| --- | ---: | ---: | ---: | ---: |
| Episodes selling | 26 | 13 | 109 | 13 |
| Median units sold | 21 | 21 | 21 | 21 |
| Median price vs base | 1.612 | 1.571 | 1.657 | 1.493 |
| Median distressed share | 0.00 | 0.00 | 0.00 | 0.00 |
| Median gross | 1,185 | 1,155 | 1,176 | 1,087 |

### EGG

| Metric | losses | worst decile | wins | best decile |
| --- | ---: | ---: | ---: | ---: |
| Episodes selling | 23 | 12 | 82 | 11 |
| Median units sold | 16 | 16 | 16 | 16 |
| Median price vs base | 1.067 | 1.067 | 1.062 | 1.080 |
| Median distressed share | 0.00 | 0.00 | 0.00 | 0.00 |
| Median gross | 854 | 854 | 850 | 864 |
