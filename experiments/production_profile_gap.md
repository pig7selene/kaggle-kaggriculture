# Production profile gap

Majkel 40 episodes vs ours 136 episodes. Sealed G1 holdout not opened.

| Metric | Majkel | Ours | Ratio |
| --- | ---: | ---: | ---: |
| Median final money | 109,076.0 | 95,184.0 | 1.146 |
| Median peak productive tiles | 74.0 | 75.0 | 0.987 |
| Median peak hands | 11.0 | 11.0 | 1.000 |
| Median money per productive tile | 1,479.0 | 1,249.5 | 1.184 |

## Outcomes

Rating moves on wins, not on how much a win is won by, so the spread of the margin distribution matters more here than its mean.

| Metric | Majkel | Ours |
| --- | ---: | ---: |
| W/L/T | 37/3/0 | 109/26/1 |
| GSR | 0.9250 | 0.8051 |
| Mean margin | +7,674 | +6,835 |
| Median margin | +7,890 | +4,474 |
| p10 margin | +654 | -3,319 |
| Worst margin | -3,235 | -8,176 |
| Wins under +5k | 24% | 44% |

## Trajectory (median)

| Step | Majkel money | Ours money | Majkel tiles | Ours tiles | Majkel hands | Ours hands |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 3,000 | 3,000 | 0 | 0 | 0 | 0 |
| 72 | 18 | 198 | 25 | 24 | 0 | 0 |
| 144 | 764 | 801 | 25 | 25 | 0 | 0 |
| 216 | 2,099 | 1,428 | 50 | 49 | 0 | 0 |
| 288 | 8,568 | 14,021 | 72 | 70 | 0 | 0 |
| 360 | 22,908 | 23,231 | 73 | 74 | 0 | 0 |
| 432 | 44,751 | 40,518 | 71 | 75 | 0 | 0 |
| 504 | 65,414 | 53,813 | 72 | 75 | 0 | 0 |
| 576 | 76,082 | 66,126 | 70 | 75 | 0 | 0 |
| 648 | 86,638 | 76,230 | 69 | 75 | 0 | 0 |

## Median peak portfolio

- Majkel crops: {'CARROT': 17.5, 'MELON': 12.0, 'STRAWBERRY': 31.0, 'TOMATO': 6.5, 'WHEAT': 39.0}
- Ours crops: {'CARROT': 29.0, 'MELON': 12.0, 'STRAWBERRY': 33.0, 'TOMATO': 0.0, 'WHEAT': 38.0}
- Majkel animals: {'COW': 8.5, 'GOOSE': 2.0, 'SHEEP': 5.0}
- Ours animals: {'COW': 8.0, 'GOOSE': 3.0, 'SHEEP': 6.0}

- Majkel land steps: {'149+221': 32, '149+219': 4, '149+217': 3, '149+228': 1}
- Ours land steps: {'150+265': 105, '150+265+433': 23, '150+265+289': 8}

## Confound

Market inventory is global, so opponent selling moves prices. The two panels faced different opponent pools, so money comparisons are confounded; peak tiles and peak hands are own-farm quantities and are not.

