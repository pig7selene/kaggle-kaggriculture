# Checkpoint executor: first optional lifecycle

## Question

The safe checkpoint executor had already passed resume, perturbation, and
commitment safety gates, but it was economically passive.  Gap attribution
showed that missing crop revenue was the largest component.  The first
controlled capability was therefore one complete wheat lifecycle, with all
existing livestock and crop service remaining delegated to the safety layer.

Candidate: `agents/checkpoint_executor/crop_lifecycle_v1.py`  
Control: `agents/checkpoint_executor/commitment_executor_v1.py`

The candidate may buy one WHEAT seed, plant one observed empty unlocked tile,
service it only with a unit whose safety action is `PASS`, harvest it at
maturity, and then return the realized item through the base executor's DROP
and SELL path.  It never buys land, animals, fertilizer, or another crop.

## Cheap takeover screen

The screen (`run_checkpoint_executor_lifecycle.py`) used the frozen
`top50_observable_portfolio` as the opener through the checkpoint and as the
opponent.  The control and candidate were run from identical deterministic
states.  Seeds were 55000 and 55001, checkpoints were 24, 72, 120, and 168,
and both player seats were tested (16 paired conditions).

| metric | result |
|---|---:|
| conditions | 16 |
| runtime failures | 0 |
| semantic failures | 0 |
| candidate animal-loss games | 0 |
| candidate terminal-stranding games | 0 |
| lifecycle admissions | 4 |
| seed requests / acquired | 4 / 4 |
| plants / harvests | 4 / 4 |
| mean control money | 15,613.6 |
| mean candidate money | 15,339.5 |
| mean candidate minus control | **−274.1** |
| median money delta | 0.0 |
| P10 money delta | −2,758.5 |
| mean advantage delta | +4,743.0 |
| lifecycle realization (harvest/admission) | 100% |

The artifact with every row is
`experiments/checkpoint_executor_lifecycle_screen.json`.

The candidate was admitted only in four low-checkpoint conditions where the
observed bank could cover the seed and two-unit animal feed reserve.  A wheat
plant produced a lower-bound two units in those traces (the base executor's
route sometimes delayed watering), so the additional gross value was only on
the order of tens of coins.  The optional worker route changed persistent
geometry and therefore sometimes delayed existing animal/crop service; this
created the large negative tail despite zero safety failures.

## Safety gates

`run_checkpoint_executor_lifecycle_safety.py` applied valid action-level
perturbations (`farmer_pass`, `skip_water`, `omit_sell`, and
`omit_buy_product`) immediately before takeover on fresh seed 55002,
checkpoints 24 and 72, both seats (16 conditions).  Results:

- runtime failures: 0;
- semantic failures: 0;
- animal-loss conditions: 0;
- pre-existing crop-loss conditions: 0;
- maximum consecutive unfed: 1;
- maximum consecutive unwatered: 1;
- terminal-stranding conditions: 0.

The full rows are in `experiments/checkpoint_executor_lifecycle_safety.json`.

## Decision

This is a **safe but economically falsified** first capability.  A single
wheat tile cannot recover a meaningful fraction of the approximately 32k
continuation gap: its maximum sale value is small, while moving a persistent
worker can perturb high-value livestock and premium-crop routes.  The result
does not justify promotion or any change to the frozen best agent or
`submission/main.py`.

The next bottleneck is capability scale and commitment locality: a useful
continuation must own a compact cohort (or a higher-value crop lifecycle) and
reserve a worker without changing the safety executor's farmer/animal route.
That should be tested as a separate, parameterized cohort/premium experiment
only after choosing an explicit capital and worker budget.  No Top-player
intervention was attempted, and no Kaggle submission was made.

