# Majkel G1 market module

Decision tree over 58 state features, 2720 distinct market actions, leave-one-episode-out over 40 development episodes (28,760 steps). Sealed G1 holdout not opened.

| Model | Market-action accuracy |
| --- | ---: |
| Majority class (empty action) | 0.3887 |
| Block router, state_heavy | 0.5445 |
| Per-step nearest neighbour, state_heavy | 0.5629 |
| **This module** | **0.5511** |

## Most used split features

| Feature | Splits |
| --- | ---: |
| money | 6942 |
| unwatered_tiles | 6231 |
| shed:WHEAT | 4223 |
| productive_tiles | 3960 |
| inv_excess:WHEAT | 2628 |
| shed:MILK | 2583 |
| shed:STRAWBERRY | 2404 |
| inv_excess:FERTILIZER | 2397 |
| inv_excess:MILK | 2319 |
| inv_excess:STRAWBERRY | 2013 |
| shed:WOOL | 1960 |
| inv_excess:CARROT | 1881 |
| hour | 1866 |
| step | 1834 |
| crop:WHEAT | 1827 |
