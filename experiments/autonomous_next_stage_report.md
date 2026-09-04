# Autonomous next-stage research report (2026-09-01)

## Frozen state

The validated research best remains
`agents/top50_distilled/top50_observable_portfolio.py` (SHA-256
`f9ca672848ccffdfe56888d99bcdf5a9d7644062b9eec0cf0cdea13574931233`).
`submission/main.py` remains unchanged (SHA-256
`789bb9bbd5122eb4891983e776a13777328e3e87736cbbc0b4bc86d13fc33f9b`).
The safe executor remained unchanged (SHA-256
`cfe5395a0670240c35bce64b6fd853f93c0ce82e48ecb8079ad3d8c02b677882`).
No Kaggle submission was made.

## Why this direction was selected

Prior route-family and SELL residual studies found no durable own-money
headroom (the best route probe reversed on frontier seeds; the measured market
oracle was under 100 coins).  The safety executor's gap attribution instead
showed missing optional production, especially crops.  A one-wheat lifecycle
was fully realized but negative, and a one-melon lifecycle was only 50%
realized and negative.  The smallest remaining falsifier was therefore a
co-located premium cohort with explicit capital and worker slack, without
changing land, livestock, or the frozen route.

The theoretical gross ceiling of four fully realized unfertilized melons at
the base price is 24 × 250 − 4 × 80 = **5,680 coins before labor, movement,
and market effects**.  This is an upper bound, not an expected gain; it
justifies testing the capability but not building a large planner before
realization is demonstrated.

## Candidates and controls

All rows use the frozen CurrentBest opener, then take over at a real simulator
checkpoint.  The passive `commitment_executor_v1` is the paired control.  All
conditions use fresh deterministic seeds and both player seats.

| Candidate | Change isolated | Conditions | Mean own-money Δ | Median Δ | P10 Δ | Bootstrap 95% CI | Lifecycle realization | Runtime / semantic / animal-loss / stranding |
|---|---|---:|---:|---:|---:|---|---|---|
| `compact_melon_cohort_v1` | four melons, one borrowed PASS owner | 16 (56000–56001; checkpoints 24/72/120/168) | -464.4 | 0.0 | -2,811.0 | [-1,009.4, +17.9] | 3/4 admissions harvested (75%) | 0 / 0 / 0 incremental / 0 |
| `compact_melon_cohort_v2` | same economics, up to three PASS owners in parallel | 16 (56010–56011; checkpoint 24/72/120/168) | **+44.7** | 0.0 | -927.0 | [-244.4, +461.8] | 8/16 target tiles harvested (50% per admission) | 0 / 0 / 0 incremental / 0 |
| `compact_melon_cohort_v2` held-out | same as v2 on unseen checkpoint-24 seeds | 8 (56030–56033; both seats) | **-2,319.5** | -2,297.0 | -5,785.0 | [-4,180.8, -379.3] | 14/32 target tiles harvested (43.8% per admission) | 0 / 0 / 0 / 0 |
| `compact_melon_cohort_v3` | v2 plus one explicitly requested extra hand | 16 (56020–56021; checkpoints 24/72/120/168) | -548.6 | 0.0 | -4,322.0 | [-1,359.0, -4.2] | 6/16 target tiles harvested (37.5% per admission) | 0 / 0 / 0 / 0 |

The harness reports raw planting/harvest telemetry in each machine-readable
artifact; the percentages above are computed per four-tile admission rather
than by dividing aggregate counters across rows.

## Causal interpretation

The parallel-owner change removed some movement contention (v2 was nearly
flat on the development panel), but did not produce a reliable lifecycle:
most admissions harvested only one or two of four tiles.  The held-out panel
then lost 2,319 own coins, with 75% of paired conditions negative.  The extra
hand in v3 increased labor/movement and still harvested at most two tiles in
most rows, worsening the mean.  This is a **realization bottleneck plus
opportunity cost**, not evidence that melons have negative gross economics in
an appropriately owned full route.

The candidate and control had identical safety outcomes on the held-out panel:
zero runtime failures, zero semantic failures, zero animal losses, and zero
terminal stranding.  No frontier games were opened because the cheap signal
was below the +1,000-coin threshold and the fresh confirmation was negative.

## Decision

Reject the compact-cohort continuation capability in its current form.  Do not
promote v1, v2, or v3, do not expand to larger cohorts, and do not connect the
Top-player model yet.  The evidence does not support spending more compute on
this executor action space before a design can guarantee ownership of all
cohort service actions without stealing base commitments.

The frozen CurrentBest and submission are preserved.  The next worthwhile
research, if resumed, should begin with a new oracle or a complete coherent
economic package that owns worker/crop/livestock state end-to-end; it should
not be another isolated tile or simple market threshold.

## Artifacts

- `experiments/autonomous_stage_decision.md`
- `experiments/autonomous_compact_cohort_screen.json`
- `experiments/autonomous_compact_cohort_v2_screen.json`
- `experiments/autonomous_compact_cohort_v2_heldout.json`
- `experiments/autonomous_compact_cohort_v3_screen.json`
- `agents/checkpoint_executor/compact_melon_cohort_v1.py`
- `agents/checkpoint_executor/compact_melon_cohort_v2.py`
- `agents/checkpoint_executor/compact_melon_cohort_v3.py`
