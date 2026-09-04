# Pre-opening owner — reserved future-quadrant wheat cohort

Date: 2026-09-02

## Scope

This bounded architecture probe reserved two NE tiles and a tail worker lane
at step 0, then attempted to buy two WHEAT seeds after the first land unlock,
run the complete plant/water/harvest lifecycle, and sell the output.  The
frozen economic authority was
`agents/top50_distilled/top50_observable_portfolio.py`.

The candidate did not change the source route, `submission/main.py`, or any
Kaggle submission.  It was evaluated in paired deterministic episodes with
the frozen route as the opponent, using both seats.

## Screen

Seeds **57700–57703**, both seats: 8 complete 720-step games.

| metric | result |
|---|---:|
| runtime failures | 0 |
| schema/semantic failures | 0 |
| animal-loss conditions | 0 |
| admissions | 8 / 8 |
| seed purchases | 8 (two seeds per condition) |
| plant actions | 16 (two per condition) |
| watering actions | 32 |
| harvest actions | 16 |
| harvested units | 32 |
| mean candidate own-money delta | **+6,581.75** |
| median own-money delta | **+4,495.5** |
| P10 own-money delta | **−2,619.0** |
| mean advantage delta | **−4,211.25** |
| candidate terminal inventory value | 16 coins/condition |
| control terminal inventory value | 12 coins/condition |

Per-seed results (candidate minus control):

| seed | own-money Δ | opponent-money Δ | advantage Δ |
|---:|---:|---:|---:|
| 57700 | −2,619 | +2,235 | −4,854 |
| 57701 | +963 | +3,644 | −2,681 |
| 57702 | +8,028 | +12,711 | −4,683 |
| 57703 | +19,955 | +24,582 | −4,627 |

The two seats produced the same values in each seed because the paired
configuration is symmetric.

## Causal interpretation

The lifecycle itself was realized without runtime, schema, or animal failures,
but it was not an economic improvement.  The candidate's own-money increase
was accompanied by a larger opponent increase on every seed, so the shared
market interaction made the candidate strictly less competitive.  The large
positive own deltas on seeds 57702–57703 are therefore not evidence of crop
profit; they are route/market-state displacement effects caused by taking the
tail worker away from the inherited schedule.

The candidate also left four additional coins of terminal inventory value in
every condition (16 versus 12), indicating that the extra cohort was not
fully liquidated through the inherited endgame slots.  This violates the
terminal-capacity objective even though no inventory was discarded by a
runtime error.

## Decision

**Reject.**  Do not run a held-out confirmation or promote this candidate.
The probe demonstrates that reserving future land and a worker from step 0 can
execute a real two-tile lifecycle, but it changes the route's worker/market
state enough to transfer more value to the opponent and to strand incremental
inventory.  A viable next architecture must own the whole opening route (not
replace a tail unit inside it) and must reserve market/shed capacity for the
new cohort before any purchase is made.

## Reproducibility

- candidate: `agents/autonomous_next/preopening_owner_wheat_v1.py`
- runner: `run_preopening_owner.py`
- machine-readable result: `experiments/preopening_owner_wheat_screen.json`

