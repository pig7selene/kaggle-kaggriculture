# Opponent-awareness replay diagnosis

This is the factual, pre-implementation diagnosis. Opponent features use only
public farm state and public action history; replay-private inventory is excluded.

## Newest submission episodes

Submission: 55429527 (public score 741.0)

| Episode | Opponent | Seat | Result | Final money | Advantage | Decisive equity day | Durable bank day | Classification |
| ---: | --- | ---: | --- | ---: | ---: | ---: | ---: | --- |
| 91942483 | Yuxiao Wang | 0 | win | 102071 | +52296 | - | - | - |
| 91943392 | Joel Arias | 1 | loss | 64458 | -6386 | 8 | 6 | opening / early compounding, land/labor scaling, livestock, routing/execution |
| 91944345 | SupremeWarrior108 | 1 | win | 87914 | +50776 | - | - | - |
| 91945270 | DreamX5678 | 1 | win | 76842 | +3677 | - | - | - |
| 91946207 | alexander kern | 0 | win | 80732 | +8087 | - | - | - |
| 91947287 | Tran Huy Hoang1312 | 0 | loss | 78991 | -13110 | 6 | 7 | opening / early compounding, land/labor scaling, crop choice, livestock |
| 91948112 | AidenSong123 | 0 | win | 59988 | +17977 | - | - | - |
| 91949046 | Bardia Bahadori | 0 | loss | 53573 | -17835 | 7 | 7 | opening / early compounding, land/labor scaling, livestock |
| 91949996 | Abish Pius | 0 | loss | 62392 | -25481 | 6 | 6 | opening / early compounding, land/labor scaling, crop choice, livestock |

Median decisive equity-gap day across classifiable losses: **6.5**.

## High-rated-agent template check

| Player | Rating | Games | Identical land schedule | Mean crop L1/day | Mean planting L1/day | Mean sale L1/day | Max hand range |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| THUNDER THUNDER | 3216.7 | 4 | True | 3.51 | 1.96 | 20.66 | 4 |
| Dmitry Larko | 3151.6 | 5 | True | 4.24 | 0.83 | 11.65 | 4 |
| Abracadabra | 3148.0 | 4 | True | 0.60 | 0.05 | 3.09 | 0 |
| Ueddy | 3144.7 | 5 | True | 0.68 | 0.06 | 0.89 | 0 |
| Victor @ Tufa Labs | 3140.8 | 4 | True | 0.00 | 0.00 | 0.00 | 0 |
| Erfan Eshratifar | 3103.0 | 5 | True | 2.03 | 0.12 | 1.17 | 0 |
| Valmorlee | 3100.9 | 4 | True | 1.22 | 0.06 | 6.41 | 0 |
| Hak | 3097.1 | 4 | True | 1.09 | 0.09 | 0.62 | 0 |

## Public-signal predictive checks

Correlation is with the same player's actual sales during the next three days.

| Product | Crop area r | Maturing-soon r | Livestock-due r | Recent-sales r |
| --- | ---: | ---: | ---: | ---: |
| WHEAT | +0.350 | +0.359 | +0.000 | +0.861 |
| CARROT | +0.702 | +0.702 | +0.000 | +0.079 |
| TOMATO | +0.577 | +0.770 | +0.000 | +0.268 |
| STRAWBERRY | +0.500 | +0.863 | +0.000 | +0.782 |
| MELON | +0.308 | +0.601 | +0.000 | -0.056 |
| EGG | +0.000 | +0.000 | +0.989 | +0.939 |
| MILK | +0.000 | +0.000 | +0.932 | +0.679 |
| WOOL | +0.000 | +0.000 | +0.878 | +0.446 |
| FERTILIZER | +0.000 | +0.000 | +0.000 | +0.634 |

Complete 30-day timelines for both players and exact economic ledgers are in
`experiments/opponent_aware_diagnosis.json`.
