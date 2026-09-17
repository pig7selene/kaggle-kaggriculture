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

## The trajectory import is closed too (2026-09-17, late)

`prototype_corrective_replay.py` replays a recorded trajectory by chasing its
*state* rather than repeating its actions: it walks a unit back to the tile the
recording had it on, buys the hands, seeds, animals and land the recording owned
at that step whenever it can afford them, digs a weed sitting where the
recording wanted to plant, and posts sell orders sized to the stock we actually
hold. On Majkel's own episode and seed it climbs

| layer | money | share of the original 116,326 |
|---|---:|---:|
| raw tape | 4,194 | 3.6% |
| + purchase catch-up | 98,986 | 85.1% |
| + position correction | 114,856 | 98.7% |
| + weed digging | 120,848 | 103.9% |

so the engineering problem is solved: a recorded trajectory can be executed
faithfully. The plan still does not transfer. Three of his winning trajectories
against shipped V43 on four fresh seeds:

| trajectory | original margin | mean margin vs shipped |
|---|---:|---:|
| 109668603 | +17,945 | **-16,943** |
| 109607344 | +16,570 | **-31,618** |
| 109466152 | +12,071 | **-12,306** |
| (room_plus_clamp, same seeds) | | +114 |

Two reasons. His 141 episodes agree with each other on only 29% of opening
actions -- he is a reactive agent, not a tape, so there is no shop-independent
opening to branch from. And the shop draw is not a function of the seed alone:
weed spawning and shop unlocking share one RNG per day, so how many empty tiles
each farm has changes which shops the town unlocks. A transplanted trajectory
therefore always meets a different town than it was recorded against, and its
crop programme is aimed at the wrong demand. Against shipped it not only earns
less than V43 does, it leaves the goods shipped sells untouched and lifts the
opponent's money from ~95k to 100-156k.

## What is still open: V43's own route bank

Forcing each of the 41 routes for steps 144-647 against shipped V43 (4 pairs,
both seats):

| route | W/L | mean margin | premium units | premium index |
|---|---|---:|---:|---:|
| 103 | 8/0 | **+1,639** | 288 | 0.43 |
| 112 | 8/0 | +1,369 | 300 | 0.42 |
| 101 / 116 / 119 | 6/2 | +934 | 314 | 0.42 |
| 104 | 6/2 | +243 | 294 | 0.42 |
| 124 | 2/6 | -143 | 329 | 0.40 |
| 105 (the default for most pairs) | 2/6 | -718 | 328 | 0.41 |
| 0 | 0/8 | -3,107 | 352 | 0.40 |

The ranking follows premium volume: the routes that win sell 288-314 premium
units, the routes that lose sell 326-386. Against an opponent flooding the same
market, producing less premium is worth more than producing more -- the effect
the crop swap could not reach by editing the tape is already present in the
route bank. Best-of-41 on eight games is a selection risk, so a holdout on
eight unseen pairs and two unseen seeds is running.

## The ceiling is not 2700: three V43 forks sit in the top 34 (2026-09-17)

Fresh leaderboard, 9,301 teams:

| team | rank | score | opening agreement with V43 route 0 | field agreement with shipped after 144 |
|---|---:|---:|---:|---:|
| Driz Lo | **15** | 2976.9 | 0.99 (2 steps differ) | 0.35 |
| Thomas Tschinkel | **23** | 2940.8 | **1.00 (0 steps differ)** | 0.72 |
| Catalyst | **34** | 2918.6 | 1.00 | 0.79 |
| mikelou1 | 56 | 2891.1 | 1.00 | 0.98 |

They all keep V43's opening tape byte for byte and replace the play after step
144, and the less of shipped's tail they keep the higher they rank. Their money
is not remarkable (80-104k against our 103k); they win games, which is what the
rating counts.

Two of their episodes on the same first-two-shop pair agree on 0.57-0.93 of
tail field actions -- the signature of a tape under reactive repair layers,
which is what V43 is too.

### Replaying their trajectory directly does not work

The corrective replayer on Driz Lo's trajectories loses 28k-42k to shipped on
fresh seeds and never once reproduces the recorded shop pair in 14 tries: weed
spawning and shop unlocking share a per-day RNG, so the town differs, and the
standalone replayer executes the opening worse than the chassis does (49-95k
where V43 makes 88-116k).

### Grafting their tail into V43's route bank does

V43's router returns route 0 until step 144 and only then picks by the first
two shops, so an injected route's own steps 0-143 are never read. Splicing
route 0's opening onto a fork's steps 144-718 therefore gives a route the
chassis replays with all its reactive layers, and the state at 144 matches by
construction because their opening *is* route 0. This is exactly what the
Majkel graft could not have.

`build_v43_fork_tails.py` collects the best-margin tail per pair from the
2026-09-16 daily set: 33 of 64 pairs, mostly Driz Lo and Thomas Tschinkel.
Against shipped V43, paired game by game with room_plus_clamp on the same
seeds:

| pair | tail? | fork_tails | room_clamp | delta |
|---|---|---:|---:|---:|
| BAKERY + PET_CAFE | yes | +5,030 | +223 | **+4,807** |
| FARMERS_MARKET + BAKERY | yes | +2,208 | -113 | **+2,321** |
| BAKERY + BAKERY | yes | +2,491 | +595 | **+1,896** |
| BRUNCH_SPOT + BAKERY | no | +578 | +578 | 0 |
| BRUNCH_SPOT + PET_CAFE | no | +362 | +362 | 0 |

Uncovered pairs are identical to the base to the dollar, so the wiring is
clean; covered pairs gain 1,900-4,800. That is the magnitude the rating needs.

### Route differentiation is closed by its holdout

Forcing route 103 globally measured +1,639 on four pairs and **-6,140 (2/28)**
on eight unseen pairs and two unseen seeds; the router's own defaults 124 and
105 came out best (-291, -627). The pilot was a best-of-41 on eight games and
did not survive. A route is good for the pairs it was built for, not globally.

### Fork tails: select by measurement, not by the fork's own result

Over the full 64-game A/B the first bank is neutral (mean delta -75 against
room_plus_clamp; 26 of 59 games identical because the pair is uncovered). The
per-pair split is what matters:

| pair | tail source | fork's own margin | delta vs room_clamp |
|---|---|---:|---:|
| BAKERY + PET_CAFE | Driz Lo ep109826301 | -16,153 | **+4,208** |
| FARMERS_MARKET + BAKERY | Thomas Tschinkel ep109835653 | -12,314 | **+2,168** |
| BAKERY + BAKERY | mikelou1 ep109762388 | -4,141 | +1,084 |
| PIZZA_SHOP + PET_CAFE | Driz Lo ep109729483 | -4,968 | -1,458 |
| PET_CAFE + BAKERY | Driz Lo ep109656981 | -10,079 | -1,496 |
| ICE_CREAM_SHOP + PET_CAFE | Driz Lo ep109817461 | -4,181 | -3,434 |
| PIZZA_SHOP + BAKERY | Driz Lo ep109807931 | -11,048 | -3,836 |

The fork's own margin does not predict the transplanted tail's value: the best
tail we have came from a game its author lost by 16k. So the selection rule is
our own measurement against shipped, per pair, with a holdout on unseen seeds --
the same discipline that just killed route 103. The bank is rebuilt from the
2026-09-15 and 2026-09-16 daily sets (45 of 64 pairs; Catalyst 18, Driz Lo 14,
Thomas Tschinkel 11, mikelou1 2) and every pair is being measured.

### Fork tails, measured honestly: about +300 a game

Keyed by the town each game actually drew (the seed manifest's pair labels are
wrong once the opponent is shipped rather than our own chassis), the first bank
is positive on 20 of 50 exercised pairs and the second-candidate bank on 23 of
45 -- so a fork's tail is not intrinsically better than V43's, it is better in
its author's own game. Selecting the 18 best and averaging gives +1,860 on
those pairs, or +523 per game over all 64. The holdout of eight of them on
unseen seeds keeps six positive but regresses hard: +365 against a pilot of
+1,360 for the same pairs, which puts the honest estimate near +300 a game.

Real, and additive, but not the 3,000 the rating needs.

### The untested dimension: V43's own layer switches against the pool

The layer ablation that chose room_guard + clamp_sells played our variants
against *each other*. The route experiment showed how badly that can mislead --
route 103 measured +1,639 against shipped on four pairs and -6,140 on eight
unseen ones. So the switches are being swept again with shipped V43 as the
opponent: dead_stock, terminal_liquidation, budget_guard, both endgame layers
together, all of them, and the two ablations that remove sell_lead and
weed_repair, each with and without lead8.
