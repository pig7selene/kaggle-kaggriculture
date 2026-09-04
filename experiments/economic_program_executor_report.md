# Economic-program executor: continuation capability report

Date: 2026-09-02

## Scope and frozen state

This stage tested a research-only checkpoint executor.  The frozen
CurrentBest (`agents/top50_distilled/top50_observable_portfolio.py`) and
`submission/main.py` were not changed.  The candidate is
`agents/economic_program/economic_program_executor_v1.py`; it may own at most
one compact four-tile MELON cohort, while the existing commitment executor
services observed crops, animals, feed, inventory, and liquidation.

## Safety diagnosis and fixes

The first checkpoint probe (seeds 57200/57201, checkpoint 240, both seats)
showed four sheep escapes at the day-25 refresh.  The animals had wheat
available, but workers carrying wheat were still selecting the generic
`PICKUP_WHEAT` task.  At hour 2, normal FEED scored below pickup, so an overdue
sheep at `(6,2)` was not reached before the day ended.  The first escape was at
step 600; no runtime or semantic exception occurred.

The candidate now (1) restricts wheat carriers to executable FEED tasks when
one exists, (2) raises overdue WATER above ordinary FEED, (3) delegates to the
proven commitment executor whenever no unfinished cohort is active, and (4)
keeps lifecycle telemetry synchronized after delegation.  These are safety
and attribution fixes, not economic tuning.

## Capability validation

The fresh validation panel used seeds `57210–57213`, both seats, and
checkpoints 72 and 120 (16 conditions total).  The control was the passive
commitment executor from the same checkpoint.

| metric | result |
|---|---:|
| conditions / valid | 16 / 16 |
| runtime failures | 0 |
| semantic failures | 0 |
| animal-loss conditions | 0 |
| pre-existing crop-loss conditions | 0 |
| terminal-stranding conditions | 0 |
| cohort admissions | 8 (all at checkpoint 72) |
| seeds acquired / planted | 32 / 32 |
| matured / harvested | 32 / 32 |
| realization among admissions | 100% |
| mean own-money delta vs passive executor | +6,947.5 |
| median own-money delta | +6,253.5 |
| P10 / P5 own-money delta | 0 / 0 |

The eight checkpoint-72 admissions averaged +13,895 own coins versus the
passive control.  Checkpoint-120 states had no free four-tile zone, so the
candidate correctly admitted nothing and matched the safety executor.

## Late-checkpoint boundary

A 12-condition screen on checkpoints 264/288/312 (seeds 57200/57201, both
seats) had zero runtime errors, semantic errors, animal losses, or terminal
stranding.  Four rows at checkpoint 288 reported an initial strawberry turning
into a weed at step 432.  Re-running the same state with
`commitment_executor_v1.py` produced identical actions and the same weed: this
is an inherited dense-state limitation of the base executor, not a candidate
regression.  Late checkpoints therefore remain outside the executor's proven
safe envelope for every pre-existing crop.

## Counterfactual against uninterrupted CurrentBest

The counterfactual panel used the same seeds, seats, opener, and opponent, but
compared an uninterrupted CurrentBest episode with a takeover by the candidate
at checkpoint 72 or 120 (16 conditions).  This is the relevant economic test;
the passive-control gain above is not a strategy-promotion result.

| checkpoint | admissions | mean candidate money | mean CurrentBest money | mean delta | median delta | min / max delta |
|---:|---:|---:|---:|---:|---:|---:|
| 72 | 8 | 29,793.3 | 81,577.8 | **−51,784.5** | −52,086.5 | −57,066 / −45,899 |
| 120 | 0 | 16,909.0 | 81,577.8 | **−64,668.8** | −64,211.5 | −67,790 / −62,462 |

Across all 16 rows the mean delta was **−58,226.6** and the mean advantage
delta was **−117,736.0**.  All runs were runtime- and semantically clean, but
the candidate lacks the coherent crop, livestock, land, and labor commitments
that make CurrentBest profitable.  A safe four-melon cohort is therefore a
real capability proof, not a competitive replacement.

## CurrentBest-preserving overlay

To isolate the cost of route disruption, `agents/economic_program/currentbest_overlay_v1.py`
and `run_currentbest_overlay.py` let the original CurrentBest agent continue
unchanged and replace only PASS unit actions, plus unused market slots, with a
four-melon cohort.  On the same 16 conditions (seeds 57210–57213, checkpoints
72/120, both seats), all runs were runtime- and semantically clean.  The
overlay admitted in all rows but completed only one of four target tiles on
average (25% realization), and its mean own-money delta versus uninterrupted
CurrentBest was **−430.25** (median −434; P10 −441).  This is a small negative
signal rather than the catastrophic −58k loss of full takeover: CurrentBest's
idle-unit slack is insufficient to finance a complete premium cohort, and
partial admissions still incur seed/route costs.

## Decision

The executor can now complete a bounded new premium-crop commitment from
compatible early states without animal loss or stranded inventory.  It does
not reproduce a complete high-value economy after takeover, and late dense
states still expose the inherited crop-routing boundary.  No candidate was
promoted; CurrentBest and `submission/main.py` remain frozen and no Kaggle API
was called.

The next high-value research direction is a coherent state-owner that
preserves the complete crop/livestock route while admitting new production
only when it has reserved territory and labor.  Isolated lifecycle patches or
late checkpoint splicing should not be promoted on the present evidence.

Artifacts:

- `experiments/economic_program_executor_probe_fix.json`
- `experiments/economic_program_executor_probe120_fix.json`
- `experiments/economic_program_executor_screen_fix.json`
- `experiments/economic_program_executor_late_delegate_fix.json`
- `experiments/economic_program_executor_validation_fix.json`
- `experiments/economic_program_counterfactual_fix.json`
- `run_economic_program_executor.py`
- `run_economic_program_counterfactual.py`
- `agents/economic_program/currentbest_overlay_v1.py`
- `run_currentbest_overlay.py`
- `experiments/currentbest_overlay_counterfactual.json`
