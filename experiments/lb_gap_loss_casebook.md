# Local → leaderboard loss casebook

All 20 current-panel losses are the same pattern: a Shop0909-derived terminal overlay remains economically identical through day 28, then collects and sells 5–10 additional fertilizer units at the $1 floor during turns 714–718.

| Opponent | Seat | Shops | Plan | Own | Opp | Adv | First negative day | Lost revenue | Terminal loss | Collision |
|---|---:|---|---:|---:|---:|---:|---:|---|---:|---|
| market_smart_terminal | 0 | YARN_STORE → PIZZA_SHOP | 6 | 119782 | 119792 | -10 | 29 | fertilizer (-6.5 mean) | 10 | near-mirror |
| market_smart_terminal | 1 | YARN_STORE → PIZZA_SHOP | 6 | 119782 | 119792 | -10 | 29 | fertilizer (-6.5 mean) | 10 | near-mirror |
| market_smart_terminal | 0 | SMOOTHIE_SHOP → PIZZA_SHOP | 0 | 121498 | 121505 | -7 | 29 | fertilizer (-6.5 mean) | 7 | near-mirror |
| market_smart_terminal | 1 | SMOOTHIE_SHOP → PIZZA_SHOP | 0 | 121498 | 121505 | -7 | 29 | fertilizer (-6.5 mean) | 7 | near-mirror |
| market_smart_terminal | 0 | SMOOTHIE_SHOP → ICE_CREAM_SHOP | 0 | 114928 | 114935 | -7 | 29 | fertilizer (-6.5 mean) | 7 | near-mirror |
| market_smart_terminal | 1 | SMOOTHIE_SHOP → ICE_CREAM_SHOP | 0 | 114928 | 114935 | -7 | 29 | fertilizer (-6.5 mean) | 7 | near-mirror |
| market_smart_terminal | 0 | SMOOTHIE_SHOP → BRUNCH_SPOT | 0 | 137443 | 137450 | -7 | 29 | fertilizer (-6.5 mean) | 7 | near-mirror |
| market_smart_terminal | 1 | SMOOTHIE_SHOP → BRUNCH_SPOT | 0 | 137443 | 137450 | -7 | 29 | fertilizer (-6.5 mean) | 7 | near-mirror |
| market_smart_terminal | 0 | PIZZA_SHOP → PET_CAFE | 0 | 115906 | 115913 | -7 | 29 | fertilizer (-6.5 mean) | 7 | near-mirror |
| market_smart_terminal | 1 | PIZZA_SHOP → PET_CAFE | 0 | 115906 | 115913 | -7 | 29 | fertilizer (-6.5 mean) | 7 | near-mirror |
| most_powerfull_terminal | 0 | YARN_STORE → PIZZA_SHOP | 6 | 119782 | 119789 | -7 | 29 | fertilizer (-6.5 mean) | 7 | near-mirror |
| most_powerfull_terminal | 1 | YARN_STORE → PIZZA_SHOP | 6 | 119782 | 119789 | -7 | 29 | fertilizer (-6.5 mean) | 7 | near-mirror |
| most_powerfull_terminal | 0 | SMOOTHIE_SHOP → PIZZA_SHOP | 0 | 121498 | 121503 | -5 | 29 | fertilizer (-6.5 mean) | 5 | near-mirror |
| most_powerfull_terminal | 1 | SMOOTHIE_SHOP → PIZZA_SHOP | 0 | 121498 | 121503 | -5 | 29 | fertilizer (-6.5 mean) | 5 | near-mirror |
| most_powerfull_terminal | 0 | SMOOTHIE_SHOP → ICE_CREAM_SHOP | 0 | 114928 | 114933 | -5 | 29 | fertilizer (-6.5 mean) | 5 | near-mirror |
| most_powerfull_terminal | 1 | SMOOTHIE_SHOP → ICE_CREAM_SHOP | 0 | 114928 | 114933 | -5 | 29 | fertilizer (-6.5 mean) | 5 | near-mirror |
| most_powerfull_terminal | 0 | SMOOTHIE_SHOP → BRUNCH_SPOT | 0 | 137443 | 137448 | -5 | 29 | fertilizer (-6.5 mean) | 5 | near-mirror |
| most_powerfull_terminal | 1 | SMOOTHIE_SHOP → BRUNCH_SPOT | 0 | 137443 | 137448 | -5 | 29 | fertilizer (-6.5 mean) | 5 | near-mirror |
| most_powerfull_terminal | 0 | PIZZA_SHOP → PET_CAFE | 0 | 115906 | 115911 | -5 | 29 | fertilizer (-6.5 mean) | 5 | near-mirror |
| most_powerfull_terminal | 1 | PIZZA_SHOP → PET_CAFE | 0 | 115906 | 115911 | -5 | 29 | fertilizer (-6.5 mean) | 5 | near-mirror |

Top five by absolute loss are therefore not distinct structural failures; they are five replications of the terminal-fertilizer tie-break pattern.
