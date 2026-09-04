# End-to-end pre-opening cohort owner — two-tile cohort screen

Date: 2026-09-02

## Scope and frozen state

This was a bounded continuation of the end-to-end owner work.  The frozen
route and current best were left unchanged:

`agents/top50_distilled/top50_observable_portfolio.py`

No submission file was changed and nothing was submitted to Kaggle.

The candidate, `agents/autonomous_next/end_to_end_owner_cohort_v1.py`,
reserved two worker slots and two WHEAT tiles at turn 0.  Between steps 240
and 360 it could take over only when the corresponding inherited unit was a
genuine `PASS`; it did not alter land, livestock, fertilizer, hiring, or the
existing market decisions.  It attempted to protect the reserved tiles,
water/harvest any realized cohort, and sell the resulting units.

The control was the same frozen route.  Every condition used a paired,
deterministic 720-step episode and both player seats.

## Results

Development seeds: **57600–57603** (8 conditions total).

| metric | result |
|---|---:|
| complete conditions | 8 / 8 |
| runtime failures | 0 |
| schema/semantic failures | 0 |
| animal-loss conditions | 0 |
| admissions | 8 |
| candidate plant actions | 0 |
| inherited/cohort harvest events observed | 16 (4 units per condition) |
| candidate sell requests | 32 |
| mean candidate own-money delta | **−1,442.5** |
| median own-money delta | **−456.5** |
| P10 own-money delta | **−4,552.0** |
| mean advantage delta | **−1,768.5** |

Per-condition money (candidate − control) was:

| seed | seat 0 | seat 1 |
|---:|---:|---:|
| 57600 | −538 | −538 |
| 57601 | −4,552 | −4,552 |
| 57602 | −305 | −305 |
| 57603 | −375 | −375 |

The two seats are identical here because the built-in opponent and seeded
state are symmetric for these paired runs.

## Safety and lifecycle observations

- All 719 requested actions per player were accepted by the simulator; the
  action-schema validator reported zero failures.
- All episodes reached 720 steps with no runtime exceptions.
- No candidate animal escaped.
- The candidate's terminal inventory value was 11 coins in each condition,
  versus 12 coins for the control.  Thus the cohort did not create additional
  stranded value; the small difference is a side effect of the inherited
  route's market state, not an endgame inventory leak from the cohort.
- The telemetry recorded one admission per condition but **zero actual
  `PLANT` overrides** and zero watering overrides.  The only observed
  lifecycle transitions were two harvest observations per condition, which
  were already performed by the inherited route and merely recognized by the
  owner ledger.
- The owner attempted 860 slot checks per condition and found no reliable
  free worker lane.  Consequently the reserved cohort never became an
  independently funded/managed production block.

## Decision

**Reject and do not promote.**  This experiment does not provide a crop
throughput mechanism: it added no planting capacity, produced no new crop
cycles, and regressed terminal money on every seed.  The negative tail is
large relative to the intended marginal wheat margin, so a held-out or hard
opponent expansion is not justified.

The result reinforces the earlier owner proofs: a safe overlay cannot borrow
post-opening capacity from the replay route.  A meaningful improvement would
require a complete pre-opening owner that reserves capital, tiles, worker
lanes, watering/harvest timing, shed capacity, and sales exposure together;
this bounded two-tile overlay is not that architecture.

## Reproducibility artifact

- `experiments/end_to_end_owner_cohort_screen.json`
- runner: `run_cohort_owner.py`

