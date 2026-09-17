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

## The production line is closed (2026-09-17, evening)

### What the top agent actually does

Town demand is the same in both sets of games (strawberry 3.85 units per 4
steps in ours, 4.17 in theirs). The difference is the strawberry programme:

| 3-day block | our units @ price | Majkel's units @ price |
|---|---|---|
| days 12-14 | — | 1 @ 204 |
| days 15-17 | 1 @ 201 | 48 @ 217 |
| days 18-20 | 17 @ 171 | 64 @ 198 |
| days 21-23 | 38 @ 101 | 47 @ 177 |
| days 24-26 | 50 @ 91 | 33 @ 173 |
| days 27-29 | 23 @ 100 | 44 @ 181 |

He starts three days earlier, sustains twice the flow, and never drops below
1.4 of base. We arrive late and sell the bulk after the price has fallen. Over
the whole game his sell revenue is 139k against our 87k on the same number of
units (1,475 vs 1,434) -- entirely a mix-and-timing difference, not scale.

### Why we cannot retrofit it

`build_v43_crop_swap.py` sows a different crop where the tape sows wheat,
buying the seeds a few steps ahead out of cash above a floor. Against shipped
V43, all four configurations lose badly:

| variant | margin (2 seeds) | what happened |
|---|---|---|
| 40 tiles -> strawberry, days 10-15 | -21,293 / -21,497 | strawberry 129 -> 217 units but index 0.95 -> **0.26**; wheat 672 -> 91 |
| 15 tiles -> strawberry | -13,309 / -12,777 | same shape, smaller |
| 40 tiles -> tomato | -13,012 / -13,739 | tomato index 2.98 -> 1.28, wheat -> 134 |
| 40 tiles -> carrot | -4,242 / -11,343 | carrot index 1.78 -> 1.18, wheat -> 266 |

Two mechanisms kill it. An ongoing crop never clears its tile, so each swapped
tile stops cycling and the tape's five or six later wheat plantings there do
nothing -- wheat collapses from 672 units to 91-266, and wheat is also the feed
for fourteen animals. And the swapped tiles all yield within the same three
days, so the extra supply arrives as a burst the market cannot absorb: adding
90 strawberries at once takes the price from 114 to 31, because strawberry's
above-equilibrium curve is linear at 1.92 per unit.

Matching Majkel means re-planning which tile is sown with what on which day,
i.e. rebuilding the trajectory. That is the agent, not a layer.

### The no-demand goods are already handled

Fertilizer (no shop consumes it) and melon (only the town centre, one per 24
steps) realize 0.40 and 0.52 of base for us. Selling the whole shed stock of
them on arrival, with a reserve, changes nothing: the chassis already empties
them as they arrive (`nd_fert20` and `nd_melon` are margin-identical to the
base on three seeds; a smaller reserve is worse). Their price is structurally
low because both players dump into a market with no demand.

### What is left

lead8 (submitted as 56296489) against the room_clamp control (56293133) is the
live question, and route differentiation against shipped is still running.
Everything else is closed.
