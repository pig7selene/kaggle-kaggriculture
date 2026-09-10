# Farming Score V3 economic dossier

## Strategy in plain language

V3 is a high-labor, mixed livestock/crop replay policy. It requests two land expansions at turns 150 and 265 (observed unlocked-state changes at 151 and 266), peaks at 12 hired hands, constructs 17 pastures plus one coop, and buys nine cows and nine sheep. In the detailed runs it reaches 17 placed animals—nine cows and eight sheep—with no escapes. The unused coop and one unplaced/unrealized sheep indicate that requested tape totals should not be mistaken for executed assets.

The crop portfolio is wheat-led, with strawberries and melons as premium revenue, a small carrot allocation, and no tomatoes. Route 0 requests 198 wheat seeds, 33 strawberry, 12 melon, and 5 carrot; route 1 requests one fewer wheat seed. Both routes repeatedly collect animal fertilizer, buy additional fertilizer/wheat, fertilize premium crops, and sell fertilizer surplus. They harvest/service nearly continuously and end with a small wheat field plus the livestock base.

## Requested policy totals

| Metric | Route 0 | Route 1 |
|---|---:|---:|
| HIRE orders | 287 | 285 |
| BUY_PRODUCT fertilizer units | 63 | 58 |
| SELL fertilizer units | 357 | 355 |
| SELL strawberry units | 354 | 354 |
| WATER requests | 1115 | 1123 |
| HARVEST requests | 466 | 466 |

## Executed representative economics

Across four detailed appearances per forced route (CurrentBest and V2, both seats), route 0 averaged **109434.8** final coins and route 1 **110531.2**. Route 1's +1096.5 bank edge reconciles exactly:

- revenue delta: **+528.5** (milk +760; wool +207.5; fertilizer −231; wheat −208.5; strawberry +0.5);
- spend reduction: **+568.0** (fertilizer +270 saved, labor +288 saved, wheat seed +10 saved).

The base engine is economically substantial: route 1 averages 40,422.5 strawberry revenue, 26,515 milk, 24,392.5 wool, 15,618 melon, 16,001.5 fertilizer, and 14,262.25 wheat. It spends 7,600 on animals, 3,000 on land, 5,722 on labor, 4,370 on seeds, and 7,393 on bought wheat/fertilizer in this representative panel.

## Timing and phase behavior

Cash is intentionally near zero early while livestock, land, and labor are accumulated. Across the four detailed route-1 appearances, mean bank end rises from 28 on day 0 to 136 on day 3, 512 on day 6, 1,477 on day 9, 18,567 on day 12, 51,990 on day 18, 89,214 on day 24, and 110,531 on day 29; absolute endpoints vary strongly by opponent market behavior. Major asset milestones do not vary: first placed animal around turn 5, land around turns 151/266, peak 12 hands, peak 17 animals.

The only route difference is the day-15-to-day-17 block (turns 360–431). Route 1 spends less on fertilizer and hiring, rearranges field servicing/drop/pickup timing, realizes more milk/wool revenue, and gives up a little wheat/fertilizer revenue. After turn 431 the requested tapes rejoin, but their farm/inventory states remain causally different.

## Selling and market interaction

V3 liquidates throughout the season rather than holding everything to a single terminal dump. Static requested sale totals are larger than executed totals because invalid or inventory-constrained orders silently no-op. In the detailed route-1 sample it executes about 353.5 wheat, 352 fertilizer, 261 strawberry, 261 milk, 194.5 wool, 72 melon, and 9 carrot sales per game. The broad league's +5,341 advantage delta but near-zero own-money delta shows that market interference/opponent suppression is material; it is not equivalent to private wealth creation.

## Evidence limits

Crop cohort planting, watering, fertilization, and harvest windows are fully recorded per detailed game in `experiments/farming_v3_runs/dossier.partial.json`. Specific harvested units cannot be causally matched to later sales because the game pools products in inventories and shed storage. This dossier therefore reports truthful aggregate holding/sale behavior and does not invent lot-level lineage.
