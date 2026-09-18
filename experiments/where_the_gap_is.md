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

## The five-step lead is close to the best response (2026-09-17, late)

Since three quarters of the pool is shipped V43, whose tape, router and layers
we hold and whose fills we can infer from the market to 24 units in 654, the
quantity to sell each step can be computed rather than guessed:
`build_v43_best_response.py` projects, per product, the inventory over a
horizon from the opponent's scheduled lots, the town's consumption and our own
plan, and picks the quantity maximising our revenue minus theirs.

Two modelling mistakes had to go first. Without conservation -- a unit sold now
is not there for the tape's later lot -- every extra unit looks like pure gain
and the optimum collapses to emptying the shed, the sell-on-arrival layer.
And the opponent's own sell_lead moves a lot from t+1 to t *and suppresses it
at t+1*; counting it twice doubles their supply in the model.

With both fixed, on three seeds against shipped:

| | mean margin |
|---|---:|
| lead5 | **+2,087** |
| best response, horizon 48, no opponent term | +2,050 |
| best response, horizon 48, with opponent term | +1,832 |
| best response, horizon 24 | +919 |

The computed response matches the flat five-step lead and does not beat it, and
adding the opponent term makes it worse -- the model of what the opponent will
sell is not accurate enough to steer on. The residual term is inert by
construction: moving a lot conserves the total, so unsold stock at the horizon
is the same for every candidate.

That is itself worth knowing. lead5 is not a lucky heuristic; against an
opponent running the same tape in the same town it is close to the optimal
response, which is why every richer scheme tried today -- planners, gates, slot
order, early liquidation, crop swaps, tail grafts -- lands below it.

## The farm, not the market, is where the top teams' +8k lives -- and the tape cannot reach it (2026-09-17, night)

**The V43 farm is deterministic.** Across six seeds the tape digs the same 37
weeds, loses the same 14 plants and keeps the same 19/53/58/55/21 planted tiles
by day; weeds barely appear because every tile is occupied. Money still swings
from 63,762 to 106,837 on the same farm: the town decides it. Shipped's money by
first-two-shop town runs 49k-177k (between-town sd 25.5k, within-town 12k);
PET_CAFE/BAKERY towns are the floor, SMOOTHIE/ICE_CREAM/YARN the ceiling.

**Top teams adapt the farm to the town; V43 and every strong V43 fork do not.**
All 640 replays of 9/16: where a V43-farm agent met a non-V43 agent the
non-V43 side won by +7.7k mean (+8.0k median) in every town class (91-100%
wins). Their animals and quadrants match V43's (COW 9.4 vs 8.5, quadrants 3.1
vs 3.3); their crops do not: WHEAT 12-17 vs 24, STRAWBERRY 23-27 vs 33,
TOMATO 9-12 and CARROT 3-11 vs 0. Driz Lo, Catalyst, Thomas Tschinkel and
mikelou1 all run V43's exact farm and lose to them by 1-25k.

**Why the crop mix matters: every V43 product is pushed past its price cliff.**
In V43 self-play the tape's own 12 opening melon tiles crash MELON from 270 to
76 by day 12; STRAWBERRY hits $1 by step 504 (33 tiles a side into a cliff at
+62 units); MILK $26-40; FERTILIZER $1 (+493). The only scarce products are
WOOL (-112 unmet, pinned at its $241 ceiling when a yarn store exists), TOMATO
(-228, $87, nobody grows it) and CARROT (-351, but capped at $42).

**shipped.py already invests in the fourth quadrant, conditionally.** Beyond
the chassis it carries `_v233` (day 12: >=2 YARN_STOREs and WOOL >= 220 -> buy
SE, six sheep, two hands) and `_v219` (day 18: >=3 PIZZA/FARMERS and money >=
12000 -> tomatoes on SE), each requiring the quadrant set to be exactly
{NW,NE,SW}. Fourth-quadrant ideas of our own therefore collide with them, and
buying SE early disables both.

**Three farm-side experiments, all negative, with the mechanism found each time:**

| idea | result vs shipped | why |
|---|---:|---|
| town-conditioned animal swap (sheep<->cow after 144) | -8,140 mean | both animal markets are already past the cliff; the marginal unit of either is worth $1, and the early wool it gives up was worth $150+ |
| melon sandbox on SE with our own hands (7-14 tiles) | -6.6k to -23k | melons are not an empty market (the tape's opening crashes them by day 12); land 4,000 + hands ~2-5k; and buying SE at 266 disables `_v233`, which on a two-yarn town is worth ~12k to whichever side keeps it |
| loosen `_v233` to one yarn store / `_v219` to two shops | -725 / -1,381 | one yarn store cannot absorb six more sheep: wool falls from $240 to $154 and the base wool revenue goes with it; the author's gates are right |

A subtlety that cost hours: any change to a farm's empty-tile count shifts the
shared weed RNG and with it the later shop draws, so paired-seed comparisons
see different towns. On seed 7 the land-only variant met a two-yarn town where
the *opponent's* sheep layer fired and ours could not -- the whole -20k.

**Conclusion.** The +8k lives in the main quadrants' crop mix and in reacting
to the town, which needs a farm program, not tape edits (crop swaps break the
tape's harvest timing) and not the fourth quadrant (V43 already takes the one
profitable case). The market side is at its ceiling (lead5 ~ best response).

## What the strong V43 forks actually change (2026-09-18, from their 9/16 replays)

`analyze_fork_submission.py` feeds a fork's recorded observations through
shipped to learn the route the tape would play, then diffs the fork's actions
against that tape. Driz Lo (12 games), Thomas Tschinkel (12), Catalyst (2),
mikelou1 (3): **the farm is V43's** -- plants by crop, builds, land steps and
hires per day match the tape to within one -- and the edits are in how the
units spend their steps and when sales are posted:

| per game | Driz Lo | Thomas | Catalyst | mikelou1 | tape |
|---|---:|---:|---:|---:|---:|
| FERTILIZE | 135 | 107 | 89 | 105 | 82 |
| FEED | 314 | 315 | 289 | 302 | 345 |
| CARE | 337 | 380 | 352 | 370 | 372 |
| PASS | 374 | 370 | 334 | 385 | 324 |
| SELL FERTILIZER orders | 58 | 91 | - | - | 89 |
| SELL WHEAT orders | 36 | 68 | - | - | 60 |

Common to all four: feed less, fertilize more, and (Driz Lo) post sales at
hours 0-1. Driz Lo's +53 fertilizations come with +52 extra moves and -52
redundant waters, -35 cares, -30 feeds: he frees tape steps and spends them on
a one-step detour to fertilize.

Why fertilizer: in the yield window each watering adds +1, or +2 when
fertilized, and one application lasts three days -- the whole wheat window --
so one fertilizer (sold by V43 at $39 on average, $100 early, $1 late) becomes
+3 wheat (~$105). V43 harvests wheat 148 times a game and 115 of those are
unfertilized (mean yield 3.7 of 6). The tape has 188 moments a game where a
unit stands on young unfertilized wheat with fertilizer in hand; in 69 of them
its action is a move that could be delayed a step. Ceiling about +5k net;
Driz Lo realises perhaps half.

Why less feeding: the care bonus needs fed-and-cared and is worth one extra
unit on a production day; for cows and geese that unit is $30-40 of glutted
milk or egg and costs a wheat ($35) plus a step, while an animal only escapes
after two consecutive unfed days. Sheep (wool $240) are the exception.

**Feeding less, replicated naively, loses animals (-12k).** Turning FEED into
PASS on a cow or goose fed yesterday (`consecutive_unfed == 0`) skipped 51-90
feeds a game and still lost three animals by step 600: the tape does not feed
every animal every day, so our skipped day plus the tape's own gap makes two
and the animal escapes. Including sheep: -29k. The forks' fewer feeds must be
scheduled against their own feeding calendar; the wheat saved is worth ~1k, so
this is not worth the machinery. Closed.

**Extra fertilizer hand: negative in every form (2026-09-18 early).** The
mechanism works -- 85 fertilizations a game, six-yield wheat harvests rise from
24 to 51 -- but the money does not follow: fertilizer bought +$5,151 (it is
$91 at step 144 and only falls under $30 after step 480), wheat revenue +$2,220,
the twelfth hire of the day costs fib(11) = $144, so -3,741 against lead5.
Gated to cheap fertilizer: -1,425 (7 hire-days for 26 fertilizations). Adding
late watering of unwatered window wheat: -2,842 (only 16 found a game; 47
exist but the hand is not near them). Fertilizing strawberries before first
yield: -2,785. The forks do not hire an extra hand; they re-route the hands
they have, which is the day-plan replanner again.

**Feed-less with a calendar guard: still loses animals.** Skipping FEED only
when the tape fed the tile on both previous days and we did not skip it
yesterday still leaves 10-15 of 17 animals by step 700 (-13k): the wheat a
skipped feed leaves in a unit's inventory changes the shed balance, and the
tape's own later PICKUP/FEED chain -- clamped to what the shed holds -- breaks.
Restricted to products under $60: -1,872. The tape does not feed on day 29, so
a final-day cleanup changes nothing.

Every farm-side edit tried tonight fails the same way: the tape is one coupled
schedule (wheat balance, shed, hire indices, weed RNG), and a local change
moves something else. The forks' edits only work as part of their own replanned
day.

## The rank-15 fork's edge is mostly its opponents' self-harm (2026-09-18)

Pulling all 99 episodes of Driz Lo's live submission settles the question its
9/16 sample could not. Against V43-lineage opponents it goes 52-6 with a mean
margin of +3,828 (median +3,690) where our lead manages +2,440 at 75%, and its
last thirty games are against opponents averaging 2,935 for an Elo-implied
performance of 3,030 against our 2,224.

Accounting for the money exactly -- final money equals start plus sales minus
spending, and every cost is known -- the margin is not earned in the market:

| per game, 29 games vs lineage | fork | opponent |
|---|---:|---:|
| final money | 105,032 | 100,292 |
| sales revenue | 132,696 | 136,737 |
| total spending | 30,665 | 39,444 |
| of which wheat purchases, mean | 4,537 | 12,855 |
| of which wheat purchases, median | 4,091 | 5,183 |

It sells less and earns less, and wins by spending less -- almost entirely on
wheat. But the mean is carried by four games where an opponent spent over
20,000 on wheat (one spent 92,181); the median gap is about 1,100, and our own
agent buys 4,389 worth, the same as the fork. There is nothing to copy: the
fork spends like a clean tape, and its opponents at the 2,900 mark are V43
forks that have damaged themselves.

That is consistent with every attempt to replicate its edits failing. Its farm
is the tape's; its extra fertilizing, when reproduced with a value gate, is
worth +107 a game, not +1,400.

## The public lineage had moved five generations ahead of us (2026-09-18)

We had been tuning a V43 notebook while the public line reached V48. Pulling
the current notebooks and extracting each one's agent (`extract_public_agents.py`,
digests matching the authors' published SHA-256) settles where the strength is:

| chassis, against ours | result |
|---|---|
| V48 (ahmedberatozer) vs our V43 | 31/1, +1,575 |
| V48 vs our best V43-based agent | 20/12 for V48, +543 |
| alperen5252525 "Ready Stock" vs V48 | 26/6, +362 |
| tetsutani market-smart vs V48 | 29/3, +34 |
| prvsiyan frontier vs V43 | -5,114 |

**None of the public generations touches the farm.** V43, V47, V48, both
tetsutani builds and alperen all play the identical unit actions -- FERTILIZE
112, FEED 308, CARE 374, WATER 995, PASS 284 a game, equal to one decimal
across three seeds. Five generations of public progress are entirely in how
market orders are chosen and ordered, which is why they stack cleanly with our
own market layers.

**Our two layers keep working on every chassis and add up.** On V48: dynamic
lead +266, value-gated fertilizer +209, both +478, and with the lead taking a
four-to-six step window +690 (holdout +729). On alperen: +795 against V48 and
+246 against the same layers on V48 (holdout +831 and +246). So each chassis
upgrade carries our layers forward intact.

**Driz Lo is not a public notebook.** Its signature -- FERTILIZE 151, PASS 389,
WATER 952, CARE 346, and roughly half the fertilizer and wheat sell orders --
matches none of them, so the rank-15 fork runs a private farm programme. Its
market layer reallocates order slots from wheat and fertilizer to wool and egg,
which is the same idea as our dynamic lead. Slot pressure is not our problem:
we hit the ten-order cap on 5% of steps.

### The packaging bug that cost two submissions

Kaggle loads an agent with `[v for v in env.values() if callable(v)][-1]`: the
last callable by insertion order. Re-assigning a name that already exists does
not move it, so a file ending in `kaggle_agent = agent` is only safe while
`kaggle_agent` is new. Stacking a second wrapper leaves its last helper --
`_fp_wants_fertilizer` -- as the last new callable, and the platform calls that
instead of the agent. Both submissions on 2026-09-18 errored this way while
running perfectly under our own loader, which takes `mod.agent` explicitly.
`package_v43_variant.py` now appends a uniquely named entry point and refuses
to build unless `get_last_callable` returns it.

## What the top of the board decides differently (2026-09-18, 650 replays, 22 teams)

`extract_top_structures.py` records each team-game's herd, crops, land, hires
and sell mix against the town it was dealt, so a rule shows up as a decision
that moves with the town. Ten teams averaging 92k-116k, by yarn stores in the
final town:

| | sheep, no yarn | sheep, 2+ yarn | strawberry tiles | carrot tiles |
|---|---:|---:|---:|---:|
| Unknown Mother-Goose | 0.0 | 7.2 | 0.7-2.0 | 15.2-15.8 |
| DSM | 0.0 | 5.6 | 0.6-1.3 | 2.2-2.3 |
| Majkel1337 | 0.0 | 5.5 | 1.2-1.9 | 5.7-8.6 |
| SpaTaro | 1.9 | 11.6 | 4.2-5.8 | 1.4-9.4 |
| Excluding | 0.0 | 5.8 | 1.1-1.5 | 12.9-18.5 |
| **our chassis** | **5.6** | **9.1** | **33** | **0** |

Two differences, both in the farm programme rather than the market.

**They keep no sheep where no yarn store buys wool.** Wool ends at $1-5 in those
towns. Our chassis buys six sheep regardless, and it buys them at steps 196-226
-- when only three of the eight shops have opened. The yarn store typically
appears at step 288 and a second at 504, so the decision is taken on 37% of the
information. Gating a sheep-to-cow swap on "no yarn among the shops revealed"
wins +401 and +2,616 when the guess is right and loses 6,890 when it is not,
which is a losing trade at that predictor strength; requiring four shops makes
it never fire. The top teams must be buying sheep later, which is a change to
the programme's timing, not a rule we can graft on.

**They grow carrot, not strawberry.** A carrot tile clears in three days and can
be replanted about six times for roughly 24 units a game; a strawberry tile is
ongoing and yields four in total. We run 33 strawberry tiles and no carrot.

Everything else matches: three quadrants, 276-297 hires.

Against the public builds themselves our submitted agent is unbeaten --
`alp_dw_46_fv_r30` takes 96 of 96 games against V47, V48, both tetsutani builds
and alperen, pooled mean +500, worst opponent plain alperen at +404 -- so the
losses above 2,000 online are to other people's modifications, not to any
published strategy.

**Three ways of grafting the herd finding onto the tape, all negative.** Swapping
the early sheep purchase for cows: +401 and +2,616 where the guess held, -6,890
where it did not, and the town distribution online (35% with two or more yarn
stores) makes the expectation -1,762. Declining the fourth quadrant when the
rival is already building sheep: -8,204 in the one game it fired, because more
sheep wins even at $77 wool. Abandoning sheep late, once the revealed town has
no wool buyer and wool sits at $5: -167, because an animal escapes after two dry
days, so only six feeds are ever saved -- about $200 -- against its remaining
yield and liquidation value.

The pattern is the same each time: the top teams' advantage is *when* they
decide, and a tape cannot be given that by wrapping it. The herd is committed at
steps 196-226 on three of eight shops; they commit after day 12. Closing this
needs the purchase and planting schedules moved from fixed steps to conditions,
which is a change to the programme rather than another layer.

**Moving the herd decision late fails because the premise was backwards.** The
plan was to take the broad bet early -- a cow costs 400 against a sheep's 500
and three shop types buy milk where one buys wool -- and let the chassis's own
day-12 expansion add sheep back once the town showed itself. Measured on ten
seeds against the same agent without it:

| | mean |
|---|---:|
| early cows, chassis gate (two yarn stores, wool 220) | -17,708 |
| early cows, gate loosened to one yarn store | -11,019 |
| gate loosened alone | -2,360 |

Milk is the flooded good, not the safe one: both sides already run six to eight
cows, so four more end the game at $1-34, while wool sits at $217-245 wherever
two yarn stores exist. Four sheep traded for four cows is about $9,360 of wool
for $500 of milk. And wool in a one-yarn town ends at $24-55, so adding sheep
there floods it too -- which is why loosening the gate also loses.

The author's gate is calibrated. The top teams' zero sheep in yarn-free towns is
real but those towns are 8 of our 26 online games, and every way of buying it
costs more than it returns.

**Carrot on the tape's strawberry tiles fails on the visit budget.** The idea
needed no extra steps: the tape already visits each strawberry tile 52 times a
game and stays put for two consecutive steps 847 times, so plant, water, harvest
and replant should fit inside visits that already happen. Measured over days
7-28 it does not. The tape supplies **0.99 stay-actions per tile per day** -- a
watering and nothing more -- and 28% of tile-days get no stay-action at all,
scheduled so that no tile is ever missed twice running. Strawberry survives on
exactly that; a carrot cycle needs five actions in four days, or 1.25 a day, and
dies after two dry days. In six-tile runs, 35 plantings produced 13 harvests and
15 weeds, and the layer lost 5,537 a game; at ten tiles, 9,368.

An earlier version also replaced the tape's *moves* across those tiles, stranding
units mid-route, which cost 29,569 a game -- of the 1,744 visits only 776 are
actions, the rest are passing through.

So both structural differences from the top teams are closed for the same
reason. The tape's step budget is calibrated to its own crops and herd; their
mix needs a different allocation, and the allocation is what the tape fixes.
Copying them means not using a tape.
