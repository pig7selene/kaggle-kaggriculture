# Mirror detectability

75 mirror and 61 non-mirror episodes of submission 56183575, probed every 24 steps. Lower feature values mean the opponent's board is tracking ours.

## Earliest step reaching a given classification accuracy

| Feature | 80% | 90% | 95% |
| --- | ---: | ---: | ---: |
| board_l1 | never | never | never |
| money_gap | 288 | never | never |
| hands_gap | never | never | never |
| quadrant_gap | never | never | never |

## Accuracy by step (best single feature per step)

| Step | board_l1 | money_gap | hands_gap | quadrant_gap |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 0.55 | 0.55 | 0.55 | 0.55 |
| 72 | 0.64 | 0.77 | 0.55 | 0.55 |
| 144 | 0.64 | 0.74 | 0.55 | 0.58 |
| 216 | 0.72 | 0.77 | 0.55 | 0.58 |
| 288 | 0.75 | 0.80 | 0.55 | 0.55 |
| 360 | 0.77 | 0.78 | 0.55 | 0.58 |
| 432 | 0.76 | 0.79 | 0.55 | 0.58 |
| 504 | 0.76 | 0.74 | 0.55 | 0.62 |
| 576 | 0.75 | 0.73 | 0.55 | 0.62 |
| 648 | 0.78 | 0.64 | 0.55 | 0.62 |

## What is still open when detection fires

| Commitment | Median step | Earliest | Latest |
| --- | ---: | ---: | ---: |
| first_sheep_purchase | 2 | 2 | 2 |
| first_wool_sale | 150 | 150 | 151 |
| last_wool_sale | 719 | 719 | 719 |
