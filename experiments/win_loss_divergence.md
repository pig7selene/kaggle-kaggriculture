# Win/loss divergence, submission 56183575

109 wins and 26 losses. Ground truth only: farm money, tile and hand counts, market price and inventory. No sale revenue is reconstructed, because order quantity is not fill quantity and income settles at end of day.

## Median money margin by block

| Step | Wins | Losses | Gap | Separation |
| ---: | ---: | ---: | ---: | ---: |
| 0 | +0 | +0 | +0 | 0.50 |
| 72 | +0 | -24 | +24 | 0.79 |
| 144 | +0 | -53 | +53 | 0.73 |
| 216 | +7 | -51 | +58 | 0.78 |
| 288 | +22 | -50 | +72 | 0.76 |
| 360 | +154 | -154 | +308 | 0.74 |
| 432 | +583 | -131 | +714 | 0.75 |
| 504 | +978 | -508 | +1,486 | 0.80 |
| 576 | +1,656 | -538 | +2,194 | 0.87 |
| 648 | +2,750 | -3,072 | +5,822 | 0.97 |

Separation is the probability that a random loss sits below a random win on this measure at this block; 0.50 is no information and 1.00 is perfect.

## Median own money and production by block

| Step | Win money | Loss money | Win tiles | Loss tiles | Win hands | Loss hands |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 3,000 | 3,000 | 0 | 0 | 0 | 0 |
| 72 | 198 | 202 | 24 | 24 | 0 | 0 |
| 144 | 801 | 777 | 25 | 25 | 0 | 0 |
| 216 | 1,428 | 1,462 | 49 | 49 | 0 | 0 |
| 288 | 14,000 | 14,338 | 70 | 70 | 0 | 0 |
| 360 | 23,421 | 22,577 | 74 | 74 | 0 | 0 |
| 432 | 40,862 | 38,138 | 75 | 75 | 0 | 0 |
| 504 | 54,813 | 51,170 | 75 | 75 | 0 | 0 |
| 576 | 66,168 | 66,423 | 75 | 75 | 0 | 0 |
| 648 | 76,716 | 75,862 | 75 | 75 | 0 | 0 |

## Shared market state by block

Both seats face the same market, so this is context rather than an advantage; it says whether losses are played in crashed markets.

| Step | Win premium price/base | Loss premium price/base | Win excess inventory | Loss excess inventory |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 1.000 | 1.000 | +0 | +0 |
| 72 | 1.082 | 1.082 | -3 | -3 |
| 144 | 1.149 | 1.153 | -10 | -10 |
| 216 | 1.122 | 1.158 | -15 | -10 |
| 288 | 0.923 | 0.950 | +18 | +18 |
| 360 | 0.809 | 0.782 | +14 | +20 |
| 432 | 0.690 | 0.707 | +32 | +30 |
| 504 | 0.537 | 0.566 | +48 | +46 |
| 576 | 0.412 | 0.426 | +60 | +60 |
| 648 | 0.494 | 0.475 | +51 | +52 |

## Separation by field and block

| Field | 0 | 72 | 144 | 216 | 288 | 360 | 432 | 504 | 576 | 648 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| money | 0.50 | 0.38 | 0.92 | 0.49 | 0.45 | 0.52 | 0.56 | 0.53 | 0.53 | 0.54 |
| money_margin | 0.50 | 0.79 | 0.73 | 0.78 | 0.76 | 0.74 | 0.75 | 0.80 | 0.87 | 0.97 |
| tiles | 0.50 | 0.62 | 0.50 | 0.52 | 0.50 | 0.50 | 0.50 | 0.51 | 0.48 | 0.48 |
| opponent_tiles | 0.50 | 0.43 | 0.48 | 0.42 | 0.34 | 0.43 | 0.39 | 0.44 | 0.43 | 0.45 |
| hands | 0.50 | 0.50 | 0.50 | 0.50 | 0.50 | 0.50 | 0.50 | 0.50 | 0.50 | 0.50 |
| opponent_hands | 0.50 | 0.50 | 0.50 | 0.50 | 0.50 | 0.50 | 0.50 | 0.50 | 0.50 | 0.50 |
| premium_price_vs_base | 0.50 | 0.50 | 0.44 | 0.44 | 0.45 | 0.52 | 0.50 | 0.49 | 0.49 | 0.52 |
| premium_inventory_excess | 0.50 | 0.50 | 0.47 | 0.46 | 0.49 | 0.48 | 0.53 | 0.50 | 0.51 | 0.49 |
