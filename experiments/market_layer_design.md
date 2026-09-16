# Market-side tail layers on V43 room_plus_clamp (2026-09-16)

## Where the 225 points are

Full public leaderboard (9,186 teams, pulled 2026-09-16 12:00): Majkel1337 1st
3179.1; top-30 line 2916.3; アルモンド 38th 2902.4; redblackbst 169th 2798.8; we
(56258686, V43 + room_guard + clamp_sells) 401st 2677.3.

アルモンド runs V43's opening tape byte-for-byte (steps 0-143) and then a
state-dependent policy: its two episodes on the same shop pair agree on only
30-47% of field actions after 144 (first divergence 159/164/238), and match no
existing V43 route above 0.56. Yet every aggregate we can measure is the same as
V43 room_plus_clamp in self-play (`frontier_tail_almond.md` vs
`frontier_tail_v43_selfplay.md`):

| | アルモンド (20 online) | V43 self-play (24 seats) |
|---|---:|---:|
| money day 6 / 8 / 10 | 39.6k / 72.9k / 104.0k | 40.6k / 72.5k / 103.3k |
| hands HARVEST / PLANT / WATER, day 8 | 83.6 / 31.1 / 117.0 | 83.0 / 31.0 / 120.0 |
| shed mean, days 7-9 | 40-44 | 35-46 |
| shed after end-of-day, days 7-9 | 96-100 | 89-96 |

The one difference is the shape of the sell orders: 1.5-2x as many SELL orders
per day (day 8: 71 vs 47; day 9: 85 vs 64) and 2-3x the posted quantity for the
same output, including runs of `SELL <item> 1000` on consecutive steps and
several orders for one item in one step.

## Why that is worth anything

From the engine (`kaggle_environments/envs/kaggriculture/kaggriculture.py`):

- `market_price` is a function of current inventory only, and inventory changes
  only through trades (sales at $1 excepted). There is no reversion. Every unit
  either player sells permanently lowers the price of the next unit for both.
- `_process_market` matches the two players' order lists slot by slot: slot i of
  player 0 and slot i of player 1 run unit-by-unit in lockstep, both seeing the
  same pre-commit inventory; slot i finishes before slot i+1 starts.

So for any unit we will sell anyway, selling it a step earlier, or in an earlier
slot than the opponent's sale of the same item, is a pure transfer from them to
us. It cannot show in self-play against a clone (symmetric) and cannot show in a
money curve against unmatched opponents; it shows in direct matches and in the
rating. This is the same mechanism our own lineage exploited as front-running,
transplanted onto the better farm plan.

Constraints found the hard way: WHEAT and FERTILIZER are inputs (hands pick them
up from the shed to FEED and FERTILIZE), and V43's tapes carry same-step
`BUY_PRODUCT WHEAT` -> `SELL WHEAT` washes (82 in 4 games). The first cut of the
slot layer moved SELLs ahead of BUYs and lost 1-2.6k per game deterministically.
v2 never moves or drops a parent order; it only edits quantities, permutes
non-input SELLs among the slots they already occupy, and appends into free slots.

## Variants (build_v43_market_layers.py, EOF wrapper on room_plus_clamp)

- `sell_on_arrival_v2`: raise each non-input SELL to the full shed stock; append a
  SELL for every other non-input product in the shed (price > 1), premium first,
  into free slots.
- `slot_priority_v2`: quantities unchanged; non-input SELLs sorted by unit price
  descending within their own slots.
- `both_v2`: the two together.
- (`sell_on_arrival` v1 also ran: identical except that an over-full list could
  drop a parent SELL; kept for the record only.)

## Pre-registered evaluation (run_market_layer_ab.py)

Direct matches variant vs room_plus_clamp, same seed, both seats; margin =
variant money - base money.

- Pilot: pairs `sorted(by_pair)[0::4]` (16), seeds `[0:2]`, both seats: 64 games
  per variant.
- Selection: best pilot mean margin among variants with zero errors.
- Holdout for the selected variant only: pairs `[2::4]` (16 pairs never in the
  pilot), seeds `[2:4]` (never in the pilot), both seats: 64 games.
- Ship if holdout mean > 0, median > 0, wins > losses, zero errors. Scale: the
  +440 local margin of room_guard+clamp_sells became about +100 online, so the
  gap to the top 30 (+240) wants a local margin around +1000; anything positive
  still ships, because it is measured against the exact agent we have online.
- The submission is compared with 56258686 in the same rating window only.

## Results

- `sell_on_arrival` (v1): 64 games 31/33/0, mean -142, median -126, zero errors.
  Telemetry: the layer changed only ~35 of 719 steps per game (80 units raised,
  51 orders added). V43's sell_lead already sells nearly on arrival; the
  hypothesis that its tape leaves stock unsold is dead.

## Price gate (added after the realized-price table)

Realized price index (quoted price at the step x shed-capped fill, per
seat-game): アルモンド WOOL 0.45 x base with 41% of units at the floor, MILK
0.66, STRAWBERRY 1.00; V43 self-play WOOL 0.73 (20% floor), MILK 0.73,
STRAWBERRY 0.81 (27% floor); アルモンド's top-10 opponents WOOL 0.62, MILK 0.83,
STRAWBERRY 1.25. The engine's town consumption (`_town_consume`: every 4 steps
each unlocked shop instance takes 1 unit of each of its products, 2 for a
single-product shop; every 24 steps the town centre takes 1 of everything)
means a crashed premium price does recover, slowly. Dumping at $1 is therefore
a pure loss of the unit's later value, bounded only by shed room.

`gate_35_70` / `gate_50_80`: hold WOOL/MILK/STRAWBERRY/MELON while the quote is
below 0.35 (0.50) x base, release the whole stock at or above 0.70 (0.80) x
base; hold only if the products in the shed total <= 60, never in the last two
hours of a day, never on the final day. Same pilot/holdout protocol.

- `slot_priority_v2`: 64 games 11/53/0, mean -213, median -173, zero errors, with
  only 10.6 reorders per game. Consistently negative: premium quotes sit at the
  floor a fifth to a third of the time (floor sales add no inventory, so slot
  order is moot there) and moving a cheap SELL one slot later hands the
  opponent's identical order the first fills. Slot priority is closed; a v3 that
  pins zero-quantity placeholders was built but not run (placeholders occur in 8
  of 719 steps and only for inputs).
- `both_v2`: 64 games 23/41/0, mean -129, median -153. Closed.

- `gate_35_70`: stopped at 41 of 64 games, 4/37/0, mean -1,601, median -1,714, worst -3,929.
- `gate_50_80`: stopped at 40 of 64 games, 2/38/0, mean -2,340, median -2,409, worst -4,277.
  Holding premium stock is expensive on this chassis: the tape's later PICKUP/
  DROP traffic and end-of-day deposits need the shed room, a crashed wool price
  without a yarn store never recovers (3 units/day of town-centre demand against
  ~30/day of joint production), and the held units are dumped anyway when the
  hold limit binds. Closed at the interim read; both runs stopped to free CPU.

## Premium lead results (pilot: pairs [0::4], seeds [0:2], both seats, vs room_plus_clamp)

- `lead2`: 64 games 61/3/0, mean +287, median +212, worst -508, best +1,470; positive on all 16 pairs (+39 .. +935).
- `lead3`: 64 games 61/3/0, mean +388, median +404, worst -436, best +1,548.

Gain grows with lookahead, as the mechanism predicts against a one-step-lead
clone (a longer lead also gets ahead of the clone's consecutive lots). `lead4`
and `lead5` are added to the pilot family; selection stays "best pilot mean",
confirmed on the holdout (pairs [2::4], seeds [2:4]) of the selected variant.
Holdouts for lead2 and lead3 are running regardless, as extra evidence.
- `lead2` holdout (pairs [2::4], seeds [2:4], never seen by the pilot): 64 games
  61/3/0, mean +268, median +216, worst -1,075, best +2,451; positive on all 16
  pairs (+31 .. +578). Passes the pre-registered ship rule; the pilot estimate
  (+287 / +212) replicated within noise.
- `lead3` holdout (pairs [2::4], seeds [2:4]): 64 games 63/1/0, mean +389, median
  +308, worst -691, best +2,898; positive on all 16 pairs (+58 .. +962).
  Telemetry: 44.6 units led over 14.9 steps per game. Replicates the pilot
  (+388 / +404). Passes the ship rule.
- `lead4` pilot: 64 games 61/3/0, mean +447, median +451, worst -397, best +1,607
  (46.6 units led over 16.9 steps per game). Ahead of lead3 on the pilot; its
  holdout is running.
- `lead5` pilot: 64 games 64/0/0, mean +1,557, median +1,380, worst +201, best
  +4,218 (159.8 units led over 32.1 steps per game -- three times lead4's
  intervention). The jump from lead4 is discontinuous and not yet explained;
  the holdout decides. lead6 and lead8 added to the pilot family.

### Where the lead margin comes from (pilot seeds, same pairs for every variant)

| variant | our money | clone's money | margin | vs lead2 run: ours / clone's |
|---|---:|---:|---:|---:|
| lead2 | 78,557 | 78,270 | +287 | — |
| lead3 | 78,604 | 78,217 | +388 | +48 / −53 |
| lead4 | 78,661 | 78,214 | +447 | +104 / −56 |
| lead5 | 79,039 | 77,481 | +1,557 | +482 / −789 |

Static stock availability is flat in the lookahead (225 -> 189 leadable units
per game for k = 2..8), so lead5's tripled intervention is a dynamic effect.
Roughly 40% of its extra margin is our own revenue and 60% is the clone's
loss -- the earlier supply pushes the clone's own price-gated layers into
holding stock. The clone's share is real against every V43-lineage opponent
(the most-forked public agent in our band) and absent against others; our own
share stands either way.
- `lead4` holdout: 64 games 63/1/0, mean +445, median +321, worst -199, best
  +3,392 (40.7 units led over 15.5 steps). Replicates the pilot (+447 / +451).
- `lead5` holdout: 64 games 64/0/0, mean +1,713, median +1,418, worst +121, best
  +6,389; positive on all 16 pairs (+130 .. +4,113); 124.5 units led over 27.8
  steps. Replicates the pilot (+1,557 / +1,380). Money split on the holdout vs
  the lead2 run: ours +513, clone's -932.

## Decision (2026-09-16 13:55)

Selected: **lead5** -- best pilot mean among variants with a passing holdout
(lead2 +287/+268, lead3 +388/+389, lead4 +447/+445, lead5 +1,557/+1,713).
Package `submission/v43_room_clamp_lead5.tar.gz` (sha256 5821a9bd215731d0...,
source sha 572ef4a7f132be2f...); the extracted archive played 720 steps against
the base on seed 4242 for +1,680 with zero errors. lead6 and lead8 pilots are
still running as candidates for a follow-up submission; they do not gate this one.

Online comparison: same-window only, against 56258686 (2657.9 at 13:20 today,
dormant and drifting down from its 2730 peak). Local scale so far: +440 of
margin became about +100 of rating.
- `lead6` pilot: 64 games 63/1/0, mean +1,324, median +1,157, worst -52 (114.9 units led).
- `lead8` pilot: 64 games 63/1/0, mean +1,177, median +1,100, worst -224.
  Lookahead peaks at 5; lead6 and lead8 fall back. lead5 stays selected.

## Mechanism (instrumented game, seed 4242, lead5 vs base and base vs base)

Every fill logged from the engine. Both sides sell the same units (161 WOOL,
236 MILK, 251 STRAWBERRY, 72 MELON each); nothing is destroyed or left unsold.
The margin is price alone: ours +858, the clone's -815 on premium sales versus
the base-vs-base counterfactual. On a cliff-shaped curve the first seller of a
lot takes the high price and the second the low one, so the gain applies to any
opponent selling the same item after us; what is clone-specific is only that
we know when it sells. lead5 beats lead2 because the tape's premium lots come in
bursts of 1-4 consecutive steps: a lead longer than the burst puts our whole
stream ahead of the clone's one-step lead, a lead of 2 overlaps it.

Opponent inference: inventory delta + town consumption - our fills recovers the
clone's non-floor premium fills exactly (abs error 0 over 634 units). Our own
fills are not min(qty, shed at observation) -- hands DROP into the shed before
the market runs -- abs error 341 over 716; the chassis's `_projected_shed` is
the right estimator.

## Opponent inference validated online (validate_opponent_inference.py)

Passive probe on the base chassis vs LynnV44 (non-lineage), seed 4242, scored
against engine ground truth (every fill logged): premium items -- our fills abs
error 24 of 641 units, opponent fills abs error 24 of 654 units, opponent sale
steps hit 118 / missed 4 / false 0. All items: opponent error 465 of 1,517,
from unmodelled BUY_PRODUCT of WHEAT/FERTILIZER -- irrelevant to premium goods.
The agent can see what the opponent sells, one step late, with no false alarms.

## Public pool (pairs [0::8], seeds [0:2], both seats; paired by game)

| opponent | room_clamp vs opp | lead5 vs opp | paired lead5 - base |
|---|---|---|---|
| LynnV44 (V43 descendant) | 31/1, +2,379 | 31/1, +2,716 | +337 mean, +86 median, 22/32 > 0 |
| MoonMelons | 32/0, +8,575 | 31/0, +8,277 | -225, -283, 2/31 |
| MoonMarketSmart | 30/0, +8,162 | 27/0, +7,587 | -224, -217, 1/27 |
| TerminalD (our old lineage) | 24/0, +7,888 | 21/0, +7,994 | -224, -210, 0/21 |

Against an opponent that is not racing us for the same lots, the five-step
lead costs about 220 a game: the town's consumption would have lifted the price
in those steps. Wins are unaffected here (these opponents are far weaker), but a
near-equal non-lineage opponent could flip close games. Hence `adapt5`: infer
the opponent's premium sales online; switch the lead on only when they line up
with our own tape's lots (>= 60% of >= 6 observed sale steps), which is the
signature of a V43-lineage opponent; otherwise leave the parent's action alone.

## adapt5: lead only against opponents that race our lots

Classifier reference: the opponent's inferred sale items at step t against the
items in *our own chassis's* market orders at t (placeholders included). Hit
rate on one seed: clone 1.00 (per-step set equality 0.94), LynnV44 0.64,
MoonMelons 0.49; the raw tape is useless as a reference (0.53 for the clone)
because the effective schedule differs from it through sell_lead and clamp.
Classification uses WOOL/MILK/STRAWBERRY/MELON/EGG/CARROT/TOMATO (all exactly
inferable; WHEAT/FERTILIZER are confounded by BUY_PRODUCT), skips hours 0-1 of
each day (everyone dumps after the end-of-day deposit) and any item we led in
the last 6 steps (our lead distorts the reference). Enter clone mode at >= 20
events with hit rate >= 0.85, leave below 0.70. Premium sales only begin around
step 250, so the decision lands near step 340 and costs almost no lead: the
clone smoke games led 159/142 units against lead5's ~160.

Smoke (seeds 4242, 7): clone enters at 339, score 0.95, margins +1,628/+2,009;
MoonMelons never enters (0.48), led 0; TerminalD one short false entry (28
units); LynnV44 borderline (0.65), partial entry.
