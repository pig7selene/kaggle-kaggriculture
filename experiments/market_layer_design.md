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
