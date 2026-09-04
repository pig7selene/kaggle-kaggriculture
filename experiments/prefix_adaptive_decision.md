# Prefix-adaptive route probe: decision record

Date: 2026-09-02

## Scope and frozen inputs

This was a narrow, research-only probe.  The retained baseline was
`agents/top50_distilled/top50_observable_portfolio.py` (CurrentBest), and the
candidate was `agents/autonomous_next/prefix_adaptive_portfolio_v1.py`.
Neither the baseline, any historical agent, nor `submission/main.py` was
modified.  No Kaggle submission or upload was made.

The candidate warmed a small set of complete replay routes, selected the same
observable step-1 anchor as CurrentBest, and allowed at most one continuation
choice at step 72.  A continuation was eligible only when its recorded action
prefix was byte-for-byte identical through turns 0--71.  This was intended to
avoid the state aliasing and animal/labor desynchronization seen in arbitrary
route splicing.  At the switch point it scored only already-scheduled future
SELL batches using live prices, market inventory, and visible opponent
pressure.  A bounded score margin prevented tiny quote changes from forcing a
switch.

## Benchmark evidence

The development panel used deterministic seeds 61000--61001, both seats, 720
turns, and eight opponents (CurrentBest, tetsuya, Crop Dusta, OceanMix,
livestock/crop, land-expander, high-labor, and phased-rotation).  This is 32
games per candidate and 64 complete games total.  All games completed with
zero runtime failures; the candidate made 719 calls in every game and no
semantic failure was recorded.

| Candidate | Games | W/L/T | Win rate | Mean own money | Mean advantage | Median advantage | P10 advantage | P5 advantage | Worst advantage |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| CurrentBest | 32 | 26/2/4 | 81.25% | 122,953.1 | +73,991.4 | +77,787.0 | 0.0 | -1,378.8 | -3,064 |
| prefix_adaptive_v1 | 32 | 26/6/0 | 81.25% | 126,360.1 | +73,481.1 | +77,860.5 | -4,917.4 | -7,605.8 | -10,391 |

The candidate's own-money mean was 3,406.9 coins higher, but this did not
translate into a stronger result: its mean advantage fell by 510.3 coins,
ties disappeared, and the lower tail became substantially worse.  The
advantage and tail metrics are the relevant safety gate because the market is
shared and an agent can increase its own cash while giving the opponent a
larger relative gain.

### Where the selector changed behavior

The selector switched at turn 72 in all four CurrentBest matchups and all four
OceanMix matchups.  It never switched against tetsuya, Crop Dusta, or the four
simpler proxy opponents.  Against CurrentBest the selected route remained the
same route id (`super_raw_55859516`) but differed from the frozen portfolio's
continuation, producing advantages of -5,327 and -10,391 on the two seeds (the
seat swap duplicates each seed).  The paired mean advantage delta was -7,859.
Against OceanMix, the paired mean advantage delta was -4,792; one seed moved
from a +13,256 baseline advantage to +1,839, and the other remained negative.

For context, paired own-money deltas (candidate minus CurrentBest) were:

| Opponent | Mean own-money delta | Mean advantage delta | Switches |
|---|---:|---:|---:|
| CurrentBest | +19,305 | -7,859 | 4 |
| tetsuya | +3,652.5 | +8,154.5 | 0 |
| Crop Dusta | +53 | +61 | 0 |
| OceanMix | +3,894.5 | -4,792 | 4 |
| livestock/crop | +83 | +84 | 0 |
| land-expander | +93 | +93 | 0 |
| high-labor | +83.75 | +85.25 | 0 |
| phased-rotation | +90.75 | +90.75 | 0 |

The large positive own-money delta in the self matchup is not evidence of a
useful improvement: the candidate and baseline are the two competing players,
so a route change can redistribute shared-market value and reduce relative
advantage.  The same pattern, with a smaller but still negative advantage
effect, appears against OceanMix.

## Causal interpretation

The exact-prefix guard solved the primary safety problem: no incompatible
crop, animal, worker, inventory, or land commitment was introduced before the
choice point.  It did not solve the economic problem.  By turn 72, all
candidate routes had already accumulated coupled hidden state (cohorts,
worker locations, shed contents, feed reservations, and future sale timing).
The selector's ordinal estimate treated future SELL quantities as if current
quotes were sufficient.  In the live shared market, the chosen continuation
changed the timing and composition of premium-product supply.  That can raise
the candidate's final bank while suppressing the opponent less effectively—or
even letting the opponent realize a larger relative advantage.  The result is
regime-sensitive, not a robust adaptive edge.

This is consistent with the earlier complete-route and market-residual
studies: safe execution alone is not enough, and a partial market view cannot
price the coupled production and inventory commitments.  The probe therefore
does not justify a broader route selector or more aggressive switching.

## Decision

**Reject `prefix_adaptive_v1` for promotion.**  Preserve it as a documented
negative probe.  CurrentBest remains
`agents/top50_distilled/top50_observable_portfolio.py` with SHA-256
`f9ca672848ccffdfe56888d99bcdf5a9d7644062b9eec0cf0cdea13574931233`.
`submission/main.py` remains unchanged with SHA-256
`789bb9bbd5122eb4891983e776a13777328e3e87736cbbc0b4bc86d13fc33f9b`.

The result is a useful falsification, not a reason to tune the switch margin
or run a large parameter sweep.  A further selector should be attempted only
after a coherent state owner can carry crop cohorts, livestock service,
workers, capital, inventory, and terminal liquidation across the decision
point.  The cheapest safe next step is a narrowly scoped checkpoint-resume
proof with explicit ownership and action-for-action state checks; if that
cannot preserve the full economy, return to complete end-to-end economic
packages rather than adding another overlay.

Artifacts:

- `experiments/prefix_adaptive_dev.json`
- `experiments/prefix_adaptive_dev.md`
- `run_prefix_adaptive_benchmark.py`
- `agents/autonomous_next/prefix_adaptive_portfolio_v1.py`

