# Coherent checkpoint owner — bounded replacement proof

Date: 2026-09-02

## Objective

This stage tested the smallest architecture that could address the observed
day 10–20 crop-throughput gap without changing the opening, livestock,
land, market timing, or endgame policy.  The candidate was allowed to admit at
most two MELON replacements on tiles observed to have become vacant recently.

The initial implementation (`coherent_state_owner_v1.py`) exposed two unsafe
failure modes: shadow warm-up polluted the live feed cursor, and optional tasks
could steal a mandatory watering lane.  That version was retained as a
negative diagnostic.  The final implementation (`coherent_state_owner_v2.py`)
separates shadow and live executors, uses the cold-start commitment executor as
the hard base, requires two free PASS units and a free market slot, and can
override only those PASS units.  Non-program crop, animal, feed, inventory,
and terminal actions remain owned by the base executor.

## Development screen

`run_coherent_state_owner.py` ran 16 paired conditions: deterministic seeds
57300–57301, checkpoints 240/264/288/312, both seats, and 720-turn episodes.
The control was `agents/checkpoint_executor/commitment_executor_v1.py` from the
same checkpoint; the candidate was shadow-warmed through the checkpoint and
then took over.

| Metric | v2 result |
|---|---:|
| Conditions | 16 |
| Runtime failures | 0 |
| Semantic failures | 0 |
| Candidate animal-loss conditions | 0 |
| Candidate terminal-stranding conditions | 0 |
| Mean own-money delta vs control | 0.0 |
| Median own-money delta | 0.0 |
| P10 / P5 own-money delta | 0.0 / 0.0 |
| Mean advantage delta | 0.0 |
| Admissions | 0 |
| Replacement plantings | 0 |
| Replacement harvests | 0 |

Four inherited control trajectories contained the same late crop-loss event;
there was no incremental candidate crop loss.  The strict admission gate
found no checkpoint with both two recent vacancies and two genuinely idle
PASS units after mandatory route work.  Consequently it spent no optional seed
capital and produced no extra cycles.

The final machine-readable result is
`experiments/coherent_state_owner_screen_v9.json`.  Earlier v1–v2 screens are
preserved as `coherent_state_owner_screen.json` through `_v8.json` for audit.

## Full action-equivalence proof

Two complete paired games compared the v2 candidate to the cold-start control
after takeover, covering every requested action from the checkpoint to turn
719:

| Seed | Seat | Checkpoint | Actions compared | Mismatches | Control money | Candidate money | Semantic failures |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 57300 | 0 | 264 | 455 | 0 | 16,794 | 16,794 | 0 |
| 57301 | 1 | 288 | 431 | 0 | 6,611 | 6,611 | 0 |

Both episodes completed all 720 steps.  The candidate and control opponent
money were also identical (120,480 and 95,697 respectively).  This confirms
that the shadow history and strict gates do not perturb a no-op continuation.

## Decision

This is a successful safety/ownership proof but not an economic improvement.
The result should **not** be promoted and should not trigger a held-out or
large benchmark.  The important causal finding is that CurrentBest's visible
post-checkpoint route leaves no reliably borrowable PASS capacity for even two
replacement melons.  A useful lifecycle improvement therefore cannot be an
overlay or a small borrowed cohort; it must own a complete worker/crop budget
before the checkpoint, or change the route's commitments earlier.

Keep `agents/top50_distilled/top50_observable_portfolio.py` and
`submission/main.py` unchanged.  The next research step, if pursued, should
be a full coherent route/state owner whose worker reservations are planned
before day 10, followed by a small exact-resume test.  Do not tune the v2
admission thresholds or run a broad parameter sweep: with zero admissions,
such tuning would only optimize a gate that has no actionable capacity.

