# Autonomous next stage: complete-route family screen

## Hypothesis

The missing value might be in a coherent complete economy that was not
represented by the three routes used by the observable Top-50 portfolio.  A
whole-route family medoid should therefore be evaluated from turn 0; this
avoids the state-aliasing and livestock failures seen when arbitrary route
continuations were spliced into a live episode.

## Cheap test

`run_autonomous_next_route_screen.py` ran 112 full 720-step games on fixed
seeds 50600 and 50601, both seats, against CurrentBest, tetsuya, Crop Dusta,
and OceanMix.  Candidate and baseline conditions were paired by seed,
opponent, and seat.  The family-01 signal was then independently confirmed on
128 games (seeds 50700--50707, both seats, same opponent panel).

## Results

| candidate | cheap own-money delta | cheap advantage delta | cheap P10 own | deep own-money delta | deep advantage delta | deep P10 own | H2H vs CurrentBest (deep) | livestock losses |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| family01 medoid | +2,531 | -3,931 | -25,554 | **-10,692** | **-14,642** | **-30,438** | 44/20/0 | 0 |
| family02 medoid | -14,441 | -25,467 | — | not pursued | — | — | — | 16 (cheap) |
| family03 medoid | -11,585 | -25,251 | — | not pursued | — | — | — | 0 (cheap) |
| family04 medoid | -2,554 | -10,875 | — | not pursued | — | — | — | 4 (cheap) |
| family05 medoid | -13,330 | -30,610 | — | not pursued | — | — | — | 14 (cheap) |
| raw 55899537 | -1,611 | -14,571 | — | not pursued | — | 12/4/0 (cheap) | 0 |

The initial family-01 gain was a narrow opponent/seed artifact.  On the
disjoint deep panel it lost both own money and competitive advantage despite
99.967% route realization and zero livestock loss.  This is a genuine
economic failure, not an executor crash.

## Decision

No route family is promoted and no source strategy is modified.  The result
falsifies the idea that simply selecting a different complete-route family is
the next high-value direction.  The next cheap falsification is a constrained
market-only residual: preserve all route crop, animal, land, labor, and
movement commitments and vary only the order of already scheduled SELL
orders.  This directly measures whether the frozen portfolio has own-economy
headroom in market sequencing without introducing incompatible state
transitions.

Artifacts: `autonomous_next_route_screen.json` and
`autonomous_next_route_deep_screen.json`.
