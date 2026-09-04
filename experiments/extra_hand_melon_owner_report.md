# Extra-hand melon owner probe

## Scope

This was a bounded screen of `agents/autonomous_next/extra_hand_melon_owner_v1.py`
against the frozen `agents/top50_distilled/top50_observable_portfolio.py`.
The candidate reserved one NE tile, hired one additional hand after land unlock,
and assigned that hand a single MELON lifecycle. No source agent, current best,
or `submission/main.py` was changed.

Seeds `57800`–`57803` were run in both seats (8 complete 720-step games, 719
decisions per game).

## Result

| metric | result |
|---|---:|
| conditions | 8 |
| valid games | 8 |
| runtime failures | 0 |
| schema failures | 0 |
| animal-loss conditions | 0 |
| admissions | 8 |
| extra-hand confirmations | 192 (24 per game) |
| hire requests | 192 (24 per game) |
| plant actions | 8 (1 per game) |
| watering actions | 0 |
| harvest actions / units | 0 / 0 |
| sell requests | 0 |
| mean own-money delta vs control | **−3,005.75** |
| median own-money delta | **−3,117.50** |
| P10 own-money delta | **−4,138.00** |
| mean advantage delta | **−6,957.50** |
| terminal inventory value (candidate) | 12 coins |

Per-seed own-money deltas (candidate minus control) were −4,138 (57800),
−2,160 (57801), −1,650 (57802), and −4,075 (57803); seat-swapping produced
the same paired values. The candidate therefore lost money on every
condition and never realized the intended crop cycle.

## Diagnosis

The extra hand was confirmed, but the owner lane did not persist. It planted
one melon and then issued no WATER, HARVEST, or SELL actions. The inherited
route's deadline guard blocks the overlay whenever any existing crop/animal
service is urgent; because the overlay has no independent reserved service
window, the additional hand remains idle after planting while its daily hire
cost is paid. This is an ownership/scheduling failure, not evidence that one
additional melon is unprofitable.

## Decision

**Reject.** Do not run a held-out confirmation or promote this candidate. A
future extra-worker experiment must reserve a complete recurring lane (service
turns, worker identity, seed/market slots, harvest transport, and terminal sale
capacity) rather than overlaying the frozen route. Keep the current best and
`submission/main.py` unchanged.

Machine-readable output: `experiments/extra_hand_melon_owner_screen.json`.
