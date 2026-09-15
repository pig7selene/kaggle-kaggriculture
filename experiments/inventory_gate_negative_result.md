# Inventory gate: a falsified premise

## What was built

A V233H-0911 variant that skips a premium-good SELL while the resource trades
below 60% of its base price, holding the goods for the parent's own terminal
liquidation. Built by `build_smaller_v233h_inventory_gate.py`; the submitted
0911 candidate was not modified and was verified byte-identical to its research
lock afterwards.

The motivation was three independent signals: Majkel's five leave-one-out
reliable branch-tree forks all gate on market inventory just under the 10,000
equilibrium; the G1 market module, free to choose among 58 features, put five
`inv_excess:*` features in its fifteen most-used splits and no shop feature at
all; and 59 units of standing wool surplus moves the wool price from 199 to 1.

## Result: it fails badly

Self-play against the ungated parent, 4 seeds in both seats:

| Metric | Value |
| --- | ---: |
| W/L/T | 0/8/0 |
| Mean margin | -45,964 |
| Worst | -73,172 |
| Livestock escapes, gated / parent | **126 / 0** |
| Runtime errors, semantic failures | 0, 0 |

A first version also re-emitted held quantities once the price recovered. That
was worse still and displaced real orders under the ten-order cap, but removing
the re-emission entirely did not help, so the damage is done by the skipping
itself.

## Why: the market does not recover

The premise was that a crashed premium price is an episode to wait out. It is
not. Measured across 60 official episodes, for every (resource, episode) pair
whose price fell below 60% of base:

- **61% never return above 60% for the rest of the game**
- the median first crossing is step **294**, with more than half the season left

Median price against base, all premium goods:

| Step | STRAWBERRY | MELON | MILK | WOOL |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 1.000 | 1.000 | 1.000 | 1.000 |
| 192 | 1.433 | 1.076 | 1.244 | 0.925 |
| 288 | 1.567 | 0.304 | 1.131 | 0.770 |
| 384 | 1.717 | 0.344 | 0.700 | 0.185 |
| 480 | 1.483 | 0.384 | 0.200 | 0.155 |
| 672 | 0.375 | 0.460 | 0.163 | 0.305 |

The decline is structural, not episodic: both seats produce and sell these goods
all season and the town's consumption cannot absorb them. So the gate blocks the
agent's main revenue channel from around step 294 to the end, cash runs short,
feed is not bought, and livestock starve. That is the 126 escapes.

## What this means

**Selling into a falling market is not a defect in our agent; given a
monotonically declining price it is close to correct.** Waiting only lowers the
price eventually received. The tape's price-blindness costs nothing here.

This does not contradict the branch-tree finding. Majkel's inventory forks are
at steps 21 to 31, when the market is still near equilibrium and small
deviations carry information about the shop draw and the opponent's opening.
That is a different regime from late-season selling.

The evidence that falsifies the premise was already in
`experiments/win_loss_divergence.md`, which shows the premium price index
falling 0.923, 0.809, 0.690, 0.537, 0.412 across blocks without recovering. It
should have been checked before the variant was built.

## Status

The gated agent is reproducible from `build_smaller_v233h_inventory_gate.py` and
is deliberately not committed. Nothing was submitted to Kaggle. The sealed G1
holdout was not touched.
