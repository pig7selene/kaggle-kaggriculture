# Transplanting recorded tapes into another chassis does not work

## What was built

V43's chassis with Majkel1337's recorded play substituted on the 33 first-two-shop
pairs his 40 development episodes cover, falling through to V43's own router on
the other 31. Built by `build_v43_majkel_hybrid.py`. Settings were the winning
`room_guard + clamp_sells` configuration. The sealed G1 holdout was not used.

## Result

40 games against the `room_plus_clamp` baseline, 20 seeds in both seats.

| Group | N | W/L/T | GSR | Mean margin | Worst |
| --- | ---: | ---: | ---: | ---: | ---: |
| Pairs where routes changed | 24 | 6/18/0 | 0.250 | **-54,290** | -103,559 |
| Pairs left on V43's router | 16 | 0/0/16 | - | **exactly 0** | 0 |

The plumbing is correct: on every uncovered pair the two agents are behaviourally
identical, margin exactly zero, which is what the hybrid was designed to
guarantee. The routes themselves are what fail, and they fail enormously --
losing by more than half the winner's total on some seeds.

## Why

A recorded tape is a trajectory, not a policy. Majkel's action at step N assumes
the farm state his episode produced: these tiles planted, those animals placed,
the farmer standing here. Replayed under a different seed the referenced tiles
hold something else, so most of the tape degrades into no-ops and misapplied
operations. V43's layers are bounded repairs -- dig a blocking weed, pad hand
slots, clamp a sell to the shed -- not a re-planner, so they cannot rebuild a
trajectory that no longer fits its world.

This is the Phase 1 oracle result restated on a different chassis. That study
found that even with perfect hindsight selection, copying blocks between
Majkel's *own* episodes reaches 28.5% action match and under 3% after step 432.
Transplanting across agents was never going to do better. The risk was written
down in `build_v43_majkel_hybrid.py`'s own docstring and then reasoned away on
the theory that V43's repair layers would absorb the divergence. They do not.

## What this rules out

Borrowing routes from replays is not a path to the frontier, on any chassis.
V43's own routes are not recordings; its manifest describes them as the product
of its author's EXP277-279 search. The gap between 2600 and 3000 is a gap in
route *generation*, and generation is the part nobody publishes.

## Status

The hybrid is not committed as an agent and was never submitted; it rebuilds
from the builder script. Ablation-tuned `room_plus_clamp` (submission 56258686)
is unaffected.
