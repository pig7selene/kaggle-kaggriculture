# Checkpoint-resumable executor report

## Architecture

`agents/checkpoint_executor/commitment_executor_v1.py` is a state-based,
commitment-first continuation controller.  It reconstructs the observation at
takeover rather than replaying an expected route.  Optional land, animal, and
crop purchases are disabled in this proof; the controller owns only existing
plants, animals, inventories, feed/service obligations, and liquidation.

The represented state includes:

- visible crop coordinates, crop type/age/yield and daily watering state;
- animal structures, species, production, feed/care and fertilizer state;
- bank, quadrants, worker count/positions, shed, seeds and carried inventory;
- a terminal horizon and a feed reserve derived from the actual remaining days.

Crop cohorts are represented as the live plant objects and their observed
planted day.  This is deliberately conservative: no new cohort is admitted
after takeover, so an unserviceable replant commitment cannot be created.

## Safety fixes after the first failed probe

The initial generic greedy executor failed at checkpoint 24 (bank 22, three
wheat in the shed, four animals, no hands).  It repeatedly issued unaffordable
wheat buys, fed only part of the herd, and never converted available fertilizer
into cash.  It also did not hire enough hands to water the existing crop set.

The revised executor:

1. hires a workload-derived roster only when the Fibonacci bill is affordable;
2. splits shed wheat into per-unit carriers after hands spawn;
3. removes FEED tasks from units that carry no wheat;
4. treats daily fertilizer as available for every surviving animal and uses it
   as a low-cash recovery asset;
5. accounts for same-queue sale proceeds before buying wheat and suppresses
   impossible buy spam;
6. reserves only feed required through the remaining days, then liquidates it
   after the final day's feed;
7. stops late animal harvest/fertilizer collection at step 696, leaving time
   to drop and sell carried value.

Workers are assigned by criticality and distance.  FEED and WATER are hard
   deadlines, HARVEST/CARE/FERTILIZER are secondary, and carried goods have an
   explicit DROP task.  If a plan becomes infeasible, the recovery order is
   feed protection, deadline watering, harvest, drop, then liquidation.

## Resume gate

The final run is in
`experiments/checkpoint_executor_resume_results.json`:

| checkpoints | seeds | conditions | runtime | semantic | animal-loss games | terminal-stranding games | mean own-money gap |
|---|---:|---:|---:|---:|---:|---:|---:|
| 24, 72, 120, 168, 240, 360, 480, 600 | 51000, 51001 | 32 | 0 | 0 | 0 | 0 | -32,710.1 |

The executor is safe but deliberately conservative: mean own money was
20,556.4 versus 53,266.5 for the original continuation.  It finishes with no
observed terminal inventory value, but does not reproduce optional production
investment, so equality with CurrentBest is not expected.

Per-checkpoint means (four conditions each: two seeds × two seats):

| checkpoint | mean own money | mean money gap | animal losses | terminal value |
|---:|---:|---:|---:|---:|
| 24 | 20,637 | -32,629.5 | 0/4 | 0 |
| 72 | 16,930 | -36,336.5 | 0/4 | 0 |
| 120 | 18,387 | -34,879.5 | 0/4 | 0 |
| 168 | 8,442 | -44,824.5 | 0/4 | 0 |
| 240 | 1,918 | -51,348.5 | 0/4 | 0 |
| 360 | 23,493.5 | -29,773 | 0/4 | 0 |
| 480 | 35,711 | -17,555.5 | 0/4 | 0 |
| 600 | 38,932.5 | -14,334 | 0/4 | 0 |

## Perturbation gate

`experiments/checkpoint_executor_perturbation_results.json` contains 24 valid
action-level perturbation conditions on fresh seed 52002 (both seats, three
checkpoints).  A legal `PASS` replaced a farmer action, a water action was
skipped, or a matching market order was omitted before takeover.  The executor
had:

- 0 runtime failures;
- 0 semantic failures;
- 0 animal-loss games;
- 0 terminal-stranding games.

All 22 applicable perturbations changed the state; two
`omit_buy_product` rows had no matching baseline order and are marked
`changed=false` rather than being counted as fabricated perturbations.  The
largest degradation was the skipped-water condition, as expected, but it
remained safe.

## Commitment audit

`experiments/checkpoint_executor_commitment_audit.json` audits 12 takeover
conditions on seed 53000.  Results: runtime failures 0, semantic failures 0,
animal commitment-loss conditions 0, crop commitment-loss conditions 0,
maximum observed consecutive-unfed 1, maximum consecutive-unwatered 1, and
terminal-stranding conditions 0.

## Gate decisions

Resume, perturbation, and commitment safety gates pass.  Top-player
intervention and hindsight oracle stages were **NOT RUN**.  The executor's
large negative money gap is evidence that it is a safe commitment finisher,
not yet a faithful economic continuation; connecting a Top-derived target now
would confound execution recovery with strategy change.

The frozen files remain unchanged:

- `agents/top50_distilled/top50_observable_portfolio.py` SHA-256
  `f9ca672848ccffdfe56888d99bcdf5a9d7644062b9eec0cf0cdea13574931233`;
- `submission/main.py` SHA-256
  `789bb9bbd5122eb4891983e776a13777328e3e87736cbbc0b4bc86d13fc33f9b`.

## Highest-value next step

Keep this executor as a safety harness and build a separate, opt-in
continuation layer that can own one new crop cohort end-to-end (seed → plant →
water → harvest → sell) while retaining the livestock guard.  Validate that
layer against the same resume/perturbation tests before attempting any
Top-player intervention.  No new research agent was promoted in this stage.
