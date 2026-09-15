# Majkel G1 market module, compositional

One decision tree per (verb, resource) slot, 20 slots, leave-one-episode-out over 40 development episodes (28,760 steps). Sealed G1 holdout not opened.

| Model | Market-action accuracy | Same data |
| --- | ---: | --- |
| Majority class (empty action) | 0.3887 | 40 episodes |
| Block router, state_heavy | 0.5445 | 40 episodes |
| Flat tree over 2,720 atomic classes | 0.5511 | 40 episodes |
| **This module** | **0.5298** | 40 episodes |
| Per-step nearest neighbour, state_heavy | 0.5629 | 15 episodes, not comparable |

## Per-slot accuracy

| Slot | Accuracy |
| --- | ---: |
| BUY_ANIMAL COW | 0.9929 |
| BUY_ANIMAL GOOSE | 0.9984 |
| BUY_ANIMAL SHEEP | 0.9955 |
| BUY_LAND - | 0.9977 |
| BUY_PRODUCT WHEAT | 0.9779 |
| BUY_SEED CARROT | 0.9879 |
| BUY_SEED MELON | 0.9976 |
| BUY_SEED STRAWBERRY | 0.9733 |
| BUY_SEED TOMATO | 0.9895 |
| BUY_SEED WHEAT | 0.8636 |
| HIRE - | 0.9976 |
| SELL CARROT | 0.9814 |
| SELL EGG | 0.9856 |
| SELL FERTILIZER | 0.9804 |
| SELL MELON | 0.9904 |
| SELL MILK | 0.8925 |
| SELL STRAWBERRY | 0.9233 |
| SELL TOMATO | 0.9859 |
| SELL WHEAT | 0.9188 |
| SELL WOOL | 0.9299 |

## Most used split features

| Feature | Splits |
| --- | ---: |
| unwatered_tiles | 9644 |
| money | 5827 |
| shed:WHEAT | 5393 |
| hour | 3593 |
| productive_tiles | 3520 |
| shed:STRAWBERRY | 2571 |
| inv_excess:MILK | 2439 |
| shed:MILK | 2395 |
| inv_excess:FERTILIZER | 2345 |
| ripe_tiles | 2295 |
| seed:WHEAT | 2192 |
| crop:WHEAT | 2188 |
| hands | 2186 |
| step | 2163 |
| inv_excess:WHEAT | 2011 |
