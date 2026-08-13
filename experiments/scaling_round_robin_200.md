# Carrot Scale Round Robin

- Games per matchup: 200
- Seeds per matchup: 100
- Both player positions are used for every seed.
- Total games: 3000

## Win-rate matrix

Rows are the focal agent; columns are opponents.

| Agent | 04 | 08 | 12 | 16 | 20 | 25 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 04 | — | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| 08 | 100.0% | — | 0.0% | 0.0% | 0.0% | 0.0% |
| 12 | 100.0% | 100.0% | — | 0.0% | 0.0% | 0.0% |
| 16 | 100.0% | 100.0% | 100.0% | — | 0.0% | 16.5% |
| 20 | 100.0% | 100.0% | 100.0% | 100.0% | — | 70.0% |
| 25 | 100.0% | 100.0% | 100.0% | 83.5% | 30.0% | — |

## Average money-advantage matrix

| Agent | 04 | 08 | 12 | 16 | 20 | 25 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 04 | — | -2201.25 | -3739.05 | -4425.55 | -5266.01 | -4610.42 |
| 08 | +2201.25 | — | -1446.41 | -2552.24 | -2884.16 | -2844.09 |
| 12 | +3739.05 | +1446.41 | — | -896.71 | -1439.67 | -1330.72 |
| 16 | +4425.55 | +2552.24 | +896.71 | — | -522.12 | -609.83 |
| 20 | +5266.01 | +2884.16 | +1439.67 | +522.12 | — | +62.34 |
| 25 | +4610.42 | +2844.09 | +1330.72 | +609.83 | -62.34 | — |

## Robustness ranking

| Rank | Agent | W/L/T | Win rate | Avg money | Avg advantage | Matchups W/L/T | Worst matchup | Best matchup |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 1 | carrot_scale_20 | 940/60/0 | 94.00% | 7308.27 | +2034.86 | 5/0/0 | carrot_scale_25 (70.0%, +62.34) | carrot_scale_04 (100.0%, +5266.01) |
| 2 | carrot_scale_25 | 827/173/0 | 82.70% | 6785.61 | +1866.54 | 4/1/0 | carrot_scale_20 (30.0%, -62.34) | carrot_scale_04 (100.0%, +4610.42) |
| 3 | carrot_scale_16 | 633/367/0 | 63.30% | 7225.95 | +1348.51 | 3/2/0 | carrot_scale_20 (0.0%, -522.12) | carrot_scale_04 (100.0%, +4425.55) |
| 4 | carrot_scale_12 | 400/600/0 | 40.00% | 6758.15 | +303.67 | 2/3/0 | carrot_scale_20 (0.0%, -1439.67) | carrot_scale_04 (100.0%, +3739.05) |
| 5 | carrot_scale_08 | 200/800/0 | 20.00% | 5994.63 | -1505.13 | 1/4/0 | carrot_scale_20 (0.0%, -2884.16) | carrot_scale_04 (100.0%, +2201.25) |
| 6 | carrot_scale_04 | 0/1000/0 | 0.00% | 4764.40 | -4048.46 | 0/5/0 | carrot_scale_20 (0.0%, -5266.01) | carrot_scale_08 (0.0%, -2201.25) |

## Pair details

| Agent | Opponent | W/L/T | Win rate | Avg money | Avg opponent | Avg advantage |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| carrot_scale_04 | carrot_scale_08 | 0/200/0 | 0.00% | 5350.34 | 7551.59 | -2201.25 |
| carrot_scale_04 | carrot_scale_12 | 0/200/0 | 0.00% | 5046.10 | 8785.15 | -3739.05 |
| carrot_scale_04 | carrot_scale_16 | 0/200/0 | 0.00% | 4686.77 | 9112.32 | -4425.55 |
| carrot_scale_04 | carrot_scale_20 | 0/200/0 | 0.00% | 4554.53 | 9820.55 | -5266.01 |
| carrot_scale_04 | carrot_scale_25 | 0/200/0 | 0.00% | 4184.24 | 8794.66 | -4610.42 |
| carrot_scale_08 | carrot_scale_12 | 0/200/0 | 0.00% | 6189.00 | 7635.41 | -1446.41 |
| carrot_scale_08 | carrot_scale_16 | 0/200/0 | 0.00% | 5955.30 | 8507.54 | -2552.24 |
| carrot_scale_08 | carrot_scale_20 | 0/200/0 | 0.00% | 5342.15 | 8226.32 | -2884.16 |
| carrot_scale_08 | carrot_scale_25 | 0/200/0 | 0.00% | 4935.12 | 7779.20 | -2844.09 |
| carrot_scale_12 | carrot_scale_16 | 0/200/0 | 0.00% | 6362.84 | 7259.55 | -896.71 |
| carrot_scale_12 | carrot_scale_20 | 0/200/0 | 0.00% | 5823.64 | 7263.31 | -1439.67 |
| carrot_scale_12 | carrot_scale_25 | 0/200/0 | 0.00% | 5183.73 | 6514.45 | -1330.72 |
| carrot_scale_16 | carrot_scale_20 | 0/200/0 | 0.00% | 5833.60 | 6355.72 | -522.12 |
| carrot_scale_16 | carrot_scale_25 | 33/167/0 | 16.50% | 5416.77 | 6026.60 | -609.83 |
| carrot_scale_20 | carrot_scale_25 | 140/60/0 | 70.00% | 4875.45 | 4813.11 | +62.34 |

## Non-transitive cycles

No directed three-agent cycles were detected.
