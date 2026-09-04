# Open autonomous stage decision (2026-09-01)

## Current evidence

- CurrentBest is a safe, complete Top-50 portfolio; route selectors, market
  residuals, and Top-3 imitation have not produced a robust own-money gain.
- The safe checkpoint executor is reliable but omits optional production.
- Four-melon checkpoint cohorts have a theoretical gross ceiling, yet the
  executor realizes only a minority of target tiles and loses on held-out
  states.
- A two-seed hindsight oracle over the existing complete route bank showed a
  large apparent opportunity, so route transfer must be tested on fresh
  frontier conditions before any architecture is expanded.

## Competing hypotheses (ranked)

| Hypothesis | Prior | Upside | Cheapest discriminating test |
|---|---:|---:|---|
| H1. Static complete-route diversity contains transferable value | medium | high | whole-route bank oracle, then fresh frontier validation |
| H2. Checkpoint executor realization is the limiting factor | high | high | four-tile premium cohort with worker/capital reservation |
| H3. Top-3 target labels have causal value | medium | high | whole Top-3 packages from turn 0 against CurrentBest |
| H4. Simple market sequencing is the missing value | low | low | existing bounded SELL counterfactual/oracle |
| H5. A history/regime-conditioned online decision layer is required | high | high | compare hindsight route oracle with cross-regime transfer and observe sign stability |
| H6. Primitive-action RL/self-play is required | low | unknown | defer until a meaningful high-level action oracle exists |

## Executed tests

1. `compact_melon_cohort_v1/v2/v3`: isolated production ownership from real
   CurrentBest checkpoints, both seats, fresh seeds.
2. `run_autonomous_complete_route_oracle.py`: all 22 complete Top-50 routes,
   identical seeds and both seats.
3. `validate_complete_route_candidates.py`: three oracle-selected routes,
   four fresh seeds, both seats, CurrentBest plus tetsuya/Crop Dusta/OceanMix.
4. Whole Top-3 package transfer probe: four fresh seeds, both seats.

## Decision rule

Promote only a new complete package with positive paired own money on fresh
seeds, non-negative tails, and zero critical safety failures.  A high H2H
advantage without own-money growth is insufficient.

## Selected research direction

Use the evidence to design a regime-conditioned **complete economic program**
layer, not another isolated crop action or static route selector.  Its first
test must estimate a cross-regime oracle on disjoint seeds and keep each
candidate whole-episode/coherent.  Do not build a primitive RL system or a
large executor until that oracle survives the transfer gate.
