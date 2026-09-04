# Autonomous next-step experiment: premium lifecycle probe

## Decision context

Repository evidence was reviewed before implementation: the frozen
Top-50 portfolio remains the validated research best; Top-3 history models have
high predictive accuracy but no safe executable target; route-family and raw
route transfers are regime-dependent; same-turn SELL reordering is a no-op;
and the safe checkpoint executor trails CurrentBest mainly through omitted
crop/animal production.  A one-wheat lifecycle was previously safe but
economically negative (−274 own coins on its 16-condition screen).

The next discriminating question was whether a single premium crop has enough
gross value to justify another isolated lifecycle intervention.  This avoids
assuming that the wheat result generalizes to all crops while keeping the
implementation small and falsifiable.

## Candidate

`agents/checkpoint_executor/premium_lifecycle_v1.py` layers one
capital-gated MELON commitment on top of
`agents/checkpoint_executor/commitment_executor_v1.py`:

`BUY_SEED MELON → PLANT → WATER → HARVEST → DROP/SELL`.

The candidate requires a healthy observed melon price, reserves near-term
animal feed cash, selects a nearby empty tile, and overrides only one idle
worker.  It does not buy land, animals, fertilizer, or additional crops.

## Cheap screen

The paired screen (`run_checkpoint_executor_lifecycle.py --candidate ...`)
used seeds 55003 and 55004, checkpoints 24/72/120/168, both seats (16
conditions).  CurrentBest generated the pre-checkpoint state and was the
opponent; the passive commitment executor was the control.

| metric | result |
|---|---:|
| conditions | 16 |
| runtime failures | 0 |
| semantic failures | 0 |
| animal-loss games | 0 |
| terminal inventory-stranding games | 0 |
| admissions / seeds acquired | 8 / 8 |
| plantings / harvests | 8 / 4 |
| lifecycle realization | 50% |
| mean control money | 17,172.5 |
| mean candidate money | 16,655.8 |
| mean own-money delta | **−516.8** |
| median own-money delta | −40.0 |
| P10 own-money delta | −1,987.0 |
| mean advantage delta | −935.6 |

The four successful rows were early checkpoint-24 takeovers: each produced
six melon units, which were sold, but the added cash did not cover the route
interference and timing cost.  Later takeovers either could not complete the
ten-day melon lifecycle or left an active crop at the end of the run.

## Safety retest

Fresh seed 55005, checkpoints 24/72, both seats, and four valid perturbations
(`farmer_pass`, `skip_water`, `omit_sell`, `omit_buy_product`) produced 16
conditions.  Runtime failures, semantic failures, animal losses,
pre-existing crop losses, and terminal inventory stranding were all zero;
maximum consecutive unfed/unwatered was one.  The checkpoint-72 perturbation
rows still demonstrate the economic failure mode: the optional melon remained
in the growing phase rather than reaching a complete harvest lifecycle.

## Alternatives considered

| direction | evidence/decision |
|---|---|
| one wheat lifecycle | safely realized, −274 own coins; falsified as useful recovery |
| one premium melon | 50% realization, −517 own coins; falsified as isolated recovery |
| more SELL ordering | zero action changes or zero own-money headroom in prior panel |
| raw/medoid route transfer | robust safety but regime-dependent or negative on Top-3 frontier |
| broad planner takeover | catastrophic livestock-loss tail; rejected |
| multi-tile/cohort executor | not yet implemented; remains the only direction with enough theoretical value to address the −37.7k crop-revenue gap |

## Conclusion

The premium probe rejects the hypothesis that one high-value crop is a safe,
high-return continuation unit.  The issue is not merely seed price: a single
melon can produce six units, yet a ten-day maturity and premium-market glut
make realization regime-sensitive, while reserving or moving a worker perturbs
existing milk/wool/crop cash flow.  The next bottleneck is therefore a coupled
commitment representation that plans a **compact cohort** and explicitly
reserves worker time, capital, and terminal capacity.  Adding isolated crop
actions is not justified.  No candidate was promoted, the frozen best and
`submission/main.py` were unchanged, and no Kaggle submission occurred.

