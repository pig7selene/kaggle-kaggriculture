# Checkpoint-resumable executor design

## Why the previous general executor failed

`goal_executor_v1` replaced a coupled replay continuation with a crop planner
while trying to merge only animal actions from the backbone.  Worker positions,
crop cohorts, feed inventory, market order budget, and livestock deadlines
therefore drifted apart.  The result was -8,298 mean advantage, a -132,772 P10,
and animal losses in all 28 diagnostic games.  The failure was executor
integrity, not a lack of Top-player signal.

## Scope of this proof

The new executor starts from the observed state at any step.  It does not
assume control from turn 0 and does not create optional land, animal, or crop
commitments.  It owns only the work needed to finish commitments already
visible in the state: feed/service, watering, harvest, placement of already
owned animals, inventory drops, feed purchases, and terminal liquidation.

## Represented state and commitments

At initialization it snapshots:

- planted crop: location, crop, age, maturity, yield, watering deadline;
- animal structure: location, animal, feed/care status, production and
  fertilizer availability;
- carried and shed inventory, seeds, cash, land, workers and positions;
- terminal horizon and mandatory feed reserve.

The snapshot is refreshed from observations each turn.  It is a commitment
ledger rather than a historical route: existing plants/animals remain owned;
optional purchases are disabled until a later experiment proves the executor.

## Scheduling and safety

Every unit is assigned a nearest task from a priority queue.  Critical tasks are
animal FEED and crop WATER near their two-day deadline.  Deadline-sensitive
tasks are HARVEST and animal CARE/COLLECT_FERTILIZER.  Optional tasks are
replanting and nonessential movement.  Assignment is recomputed from real
positions, so a worker relocation is recoverable.  Feed is reserved before
selling or any optional action; wheat is bought only when the reserve is short.

## Crop and livestock ownership

Existing crops are watered and harvested from their actual age/yield fields.
No crop is replanted unless a seed is already owned and there is enough season
time; this proof therefore cannot create an unserviceable cohort.  Animals are
never sold.  Unfed animals receive priority, with a two-day wheat reserve and
late-hour overrides.  Care/fertilizer collection runs only after feed tasks are
covered.

## Inventory, capital, and terminal mode

Workers drop carried goods at shed-adjacent tiles.  Market SELL orders liquidate
non-commitment shed inventory while preserving wheat and owned animal items.
Near the terminal horizon the executor stops optional work, harvests all
available production, and sells every valuable shed item that is not required
for remaining feed.  Same-turn market orders are bounded to ten and feed buys
are accounted for before optional sales.

## Recovery and correctness gates

If a task becomes infeasible, the recovery order is: protect animals, water
deadline crops, finish ready harvests, drop inventory, preserve cash, and
liquidate.  The resume gate compares against the original CurrentBest
continuation at checkpoints; equality is not required, but safety and a
coherent terminal state are.  The perturbation gate then uses only valid
action-level perturbations (worker relocation, omitted transaction, delayed
watering, or altered inventory) and measures graceful degradation.

Only after both gates pass would a single Top-player high-level target be
allowed.  No Top-3 intervention is part of this proof.
