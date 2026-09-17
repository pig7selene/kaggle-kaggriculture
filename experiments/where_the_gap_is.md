# Where the gap to the top actually is (2026-09-17)

## The pool we are in

Of 144 online episodes of submission 56274059 (adapt5), 120 opponents share
V43's opening tape and 114 of 120 fingerprint as **shipped V43** -- the public
notebook's own switch defaults. We beat them 72/48 with a mean margin of +807.
Our premium price index against them is 0.65 of base; theirs is 0.64. The band
from roughly 2400 to 2700 is a crowd of V43 forks playing the same farm and
splitting games on small edges.

## The top is not V43

In the 120 highest-scoring episodes of 2026-09-16 the teams are Majkel1337
(117 appearances), M & M & P & Q (69) and DSM (39). None is V43 lineage:
opening agreement with V43 route 0 is 0.01. Their money: Majkel 110k mean,
M&M&P&Q 115k, DSM 104k. Ours online: 103k.

## Their farm is not bigger

Majkel1337 (episode 109802923) against shipped V43 self-play, at the same
checkpoints:

| step | V43 PLANT/PASTURE/COOP | V43 money | Majkel PLANT/PASTURE/COOP | Majkel money |
|---:|---|---:|---|---:|
| 288 | 53/14/4 | 14,758 | 60/9/4 | 11,682 |
| 432 | 58/14/3 | 41,229 | 60/9/4 | 37,855 |
| 648 | 58/14/3 | 85,317 | 59/8/4 | 90,023 |
| 719 | 0/14/4, 11 hands | 102,830 | 3/7/4, 10 hands | 116,326 |

Same number of planted tiles, same hands, and V43 has *more* pastures. V43 is
ahead on money until step ~500 and loses 13k over the second half.

## The difference is the price they sell at

Final day (steps 648-718), means over 20 episodes each:

| | money 648 -> end | shed at 648 | units sold | premium units | **premium price index** |
|---|---|---:|---:|---:|---:|
| Majkel1337 | 87,076 -> 111,459 | 95 | 365 | 99 | **1.02** |
| M & M & P & Q | 84,877 -> 115,298 | 96 | 262 | 61 | **1.01** |
| us (adapt5) | 83,017 -> 103,239 | 90 | 263 | 63 | **0.61** |

We sell the same quantity of premium goods as M&M&P&Q and get 60% of the
price. The last-day item mix says why: they sell TOMATO (31-57 units) and
CARROT, we sell almost no tomato (2) and more FERTILIZER. V43's plan runs 14
pastures and floods wool and milk; both V43 agents in a game do it, so the
premium market sits far above equilibrium for the whole second half. The top
teams run 8 pastures, sell into an unflooded premium market at base price, and
put the land into crops the town actually consumes.

Engine 1.32.7 sharpens this: CARROT, TOMATO and EGG now use a `hinge` curve
below I0, so their price spikes once the market is genuinely short of them.

## What follows

1. Within the V43 cluster the margin is a timing arms race. Measured, 64 direct
   matches each: lead5 beats shipped 64/0 (+1,946) but loses to an opponent
   leading 8 steps 24/40 (-162); lead8 beats shipped 63/1 (+1,589) and beats
   the 8-step opponent 59/5 (+646). Longer leads are more robust, worth maybe
   +100 of rating.
2. The 13k that separates us from the top is a production-mix difference, and a
   tape transplant cannot import it: replaying Majkel's own actions against a
   different opponent yields 4,194 instead of 116,326, because his cash sits at
   0-700 through the first 150 steps and a few coins of market difference kill
   the hires (first divergence: 4 hands at step 25, then weeds take the farm).
   The engine itself is reproducible -- replaying both recorded tapes on the
   episode's seed returns the original money to 1.6% and the identical farm.
3. What is reachable is **differentiating our route from the opponent's**.
   Every route experiment so far used our own chassis as the opponent, so both
   sides produced the same goods. Against shipped V43 on its own router, a
   route with a different mix sells into a market the opponent is not flooding.
   run_route_vs_shipped.py measures exactly that, per route, with the realized
   premium index alongside the margin.
