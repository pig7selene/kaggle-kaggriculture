# Adopting Ahmed V43 as the base

## Why

The 256-game tournament in `public_agent_tournament.md` settled it: V43 goes
32/0/0 against our 0911 candidate and 32/0/0 against Terminal D, mean margins
+5,838 and +7,269, and its worst game out of sixty-four is still a 1,922 win.
The criterion fixed before that run was that a public agent winning at least 70%
against both of ours means the base should change rather than be patched.

Terminal D, which the registry lists as our highest verified leaderboard result
at 2496.8, loses to all four public agents tested, including the weakest at
27/3/2. Fourth through fifteenth on the leaderboard now sit between 2969 and
3034.

## What is being submitted

The author's own archive, unmodified, so that the reading attributes to the base
alone and any later gain attributes to what we add on top.

| Field | Value |
| --- | --- |
| Source | `ahmedberatozer/kaggriculture-v43-recovering-lost-harvests` (Apache-2.0) |
| Pulled | 2026-09-15 |
| Archive | `submission/ahmed_v43_public.tar.gz` |
| Archive SHA-256 | `f76baf851aecc13edefcc640dbf61cd409fd321a719dccb2f1b00559041e4f1e` |
| main.py SHA-256 | `919fc1d61050cd96f799979e49177ae3ac7bce98ec9835724238bea73f4a08ed` |
| Bytes | 135,866 (single `main.py`) |

Both hashes were verified against the author's published `v43_manifest.json`,
which reports `source_integrity: PASS`, `archive_integrity: PASS`, and
`live_rating_guarantee: null` -- the author does not claim an online result.

## What it is

A documented route-replay chassis with nine independently switchable layers:

    hand_align            pad/truncate hands to the real hand count
    weed_repair           DIG a weed blocking PLANT/BUILD, then replay
    sell_lead             sell next step's lots one step early
    front_run             sell before the opponent's scheduled SELL
    budget_guard          fund each 72-step block's purchases
    room_guard            keep shed <= 99 at hour 23
    clamp_sells           trim SELL orders to the projected shed
    dead_stock            sell stock the route will never sell
    terminal_liquidation  step >= 718: sell the whole projected shed

Tunables include `shed_capacity: 100`, `max_orders: 10` and `min_sell_price: 2`.
Its engine notes are verified against kaggle_environments 1.32.7, which also
resolves the 1.32.6/1.32.7 skew this repository has been carrying.

Five of those layers have no counterpart in our agent: `budget_guard`,
`room_guard`, `clamp_sells`, `dead_stock`, and the `min_sell_price` floor. Two
of them speak directly to things we measured ourselves: `clamp_sells` addresses
the speculative 1000-unit liquidation orders that fill nothing, and
`min_sell_price: 2` is the correctly scaled version of the price gate we built
and falsified at 0.6 of base, which failed because it blocked the main revenue
channel for four hundred steps rather than only the floor.

## Expectation

If the 2969-3034 band is a strong public agent plus small tweaks, V43 should
land near it, which would be 400 to 500 points above anything we have. That is a
prediction recorded before the result, not after.

## Status

Not yet submitted: the submission command requires a permission this session
does not have. Nothing about the 0911 candidate (submission 56250442) changes.
