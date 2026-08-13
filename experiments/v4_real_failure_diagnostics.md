# V2 real Kaggle diagnostics

Submission `55473991`: 78 public episodes, 71 wins / 7 losses / 0 ties.

## Outcome buckets

| Bucket | Games | Avg money | Avg margin | Avg trajectory error | Avg productive peak |
|---|---:|---:|---:|---:|---:|
| loss | 7 | 81,590 | -3,820 | 3.95 | 74.0 |
| unusually_low_money | 6 | 51,743 | +13,748 | 10.57 | 74.0 |
| low_margin_win | 16 | 92,937 | +2,903 | 6.02 | 74.0 |
| normal_win | 43 | 96,167 | +15,729 | 5.03 | 73.9 |
| high_money | 6 | 146,917 | +31,569 | 13.07 | 74.0 |

## Repeated loss signatures

| Category | Loss games | Share |
|---|---:|---:|
| capital_shortfall | 5 | 71.4% |
| crop_cohort_desynchronization | 0 | 0.0% |
| delayed_hire | 0 | 0.0% |
| delayed_land | 0 | 0.0% |
| endgame_stranding | 0 | 0.0% |
| livestock_drift | 0 | 0.0% |
| productive_tile_deficit | 0 | 0.0% |
| worker_position_drift | 0 | 0.0% |

## Losses

| Episode | Opponent | Seat | Money | Opponent | Margin | First large divergence | Repairs | Final inventory value |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 92546177 | Subramanya N | 0 | 74,756 | 90,918 | -16,162 | 597 | 0 | 0 |
| 92570512 | Kris Adamatzky | 1 | 73,712 | 78,736 | -5,024 | 529 | 0 | 0 |
| 92588379 | CemBas | 0 | 63,709 | 65,569 | -1,860 | 505 | 0 | 0 |
| 92613464 | Rayk Kretzschmar | 1 | 97,919 | 99,111 | -1,192 | 670 | 1 | 0 |
| 92627345 | Pablo César Ruíz | 1 | 67,406 | 68,586 | -1,180 | 553 | 0 | 0 |
| 92576132 | NIklitaCheporev | 0 | 92,580 | 93,447 | -867 | 454 | 0 | 0 |
| 92567612 | Furious Monk | 0 | 101,047 | 101,501 | -454 | 662 | 1 | 0 |

The JSON artifact contains all day-by-day ledgers and checkpoint-level expected/actual state comparisons.

## V4 failure clustering

The refreshed corpus contains **78** valid deployed-V2 games. The hard set is 7 losses plus bottom-quartile games; the reference set is the strongest 19 V2 games by realized money.

| Cluster | Loss games |
|---|---:|
| market realization deficit | 5 |
| endgame inefficiency | 2 |

These labels are hypotheses. V4 promotion depends on paired action counterfactuals, not on this observational comparison.
