# Next capability decision

## Gap attribution

The paired action/observation audit (`experiments/checkpoint_executor_gap_attribution.json`)
shows that the passive executor's missing value is dominated by production,
not execution syntax.  Across 32 checkpoint/seed/seat conditions the mean
final-money gap was -41,454 coins.  Approximate sale-revenue gaps were:

| component | executor minus CurrentBest |
|---|---:|
| crop products | -37,680 |
| animal products | -20,540 |
| fertilizer | -10,011 |

The executor also spent less on seeds (-3,423), animals (-1,350), land
(-1,625), and hands (-2,378), which confirms that it is economically passive.
These action-derived amounts are directional because market prices move while
orders execute, but the ranking is stable: crop lifecycle throughput is the
largest recoverable component and has lower coupling than new livestock or
land.

## Candidate capabilities

1. **One wheat lifecycle** — low seed cost, short two-day maturity, no new
   structure or land, and existing executor already owns watering/harvest/
   liquidation.  Low risk; easy to falsify.
2. **Generic premium crop cohorts** — higher upside but greater cash, shed, and
   watering pressure; defer until wheat ownership is proven.
3. **Narrow animal continuation** — potentially recovers the animal-revenue
   gap, but requires structure placement, feed reserve, and more service
   contention.  Higher safety risk.
4. **Land continuation** — unlocks capacity but has capital and labor coupling;
   not useful until a crop owner exists.
5. **Replay-derived future commitment inference** — potentially highest
   upside, but difficult to distinguish causal inference from route replay and
   hard to perturb safely.

## Selection and falsification

Select a single wheat lifecycle owner first.  It reuses the tested executor as
the safety layer, admits at most one new tile at a time, buys only a seed that
can be paid for after preserving an observed feed reserve, and overrides a
worker only when no FEED/WATER/HARVEST safety task is being displaced.  Its
complete lifecycle is seed → plant → base-executor watering → harvest → shed
drop → sell.

The cheap falsification is a paired takeover screen on fresh checkpoints and
seeds, followed by the same perturbation and commitment audits.  Reject it if
realization is below 80%, it causes any animal loss/terminal stranding, or its
incremental own-money is below 1,000 coins on the screen.
