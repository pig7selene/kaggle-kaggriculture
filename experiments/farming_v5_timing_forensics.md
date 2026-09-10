# Farming V5 timing forensics

## Finding

The exact public v2 change is much narrower than the title suggests. Version 1 already deferred an immature non-Yarn signal at the `cow88` registered bundle until the second shop could be seen at `cow150`. Version 2 adds one commitment: the direction chosen at `cow150` is reused at `cow169` and `cow176`, subject to the maximum three COW-to-SHEEP substitutions.

Nothing else moved in the public v1→v2 archive: only `agents/e773a_demand_aligned_pasture_network.py` changed. Land, hire, animal purchase nodes, quantities, routes, feeding, crops, sales, and terminal liquidation are byte-identical.

## Exact controlled result

Across 48 same-seed/opponent/seat pairs, v1 and v2 had a 719-action common prefix in every game. Own-money delta, opponent-money delta, advantage delta, and every tail statistic were exactly zero. A synthetic state confirms the code can matter: when `cow150` prefers COW and later wool pressure flips, v1 changes `cow169` to SHEEP while v2 keeps COW. That is a semantic capability test, not economic evidence.

## Broader timing dimensions

| Dimension | V3 | V5 | Finding |
|---|---|---|---|
| Land | orders at 150, 265 | orders at 150, 265 | no change |
| Labor | different replay schedule; mean dossier spend 5,914 | different replay schedule; mean 6,387 | structural, not isolated timing |
| Livestock | fixed programme, about 17 peak animals | conserved adaptive bundles, about 14 peak animals | direction/mix and programme differ; not timing-only |
| Melon | day-0 cohort, harvest around 245–264 | same core day-0 window | no current v2 change |
| Strawberry/Wheat | V3-specific cohorts | Kenjo/Niklita-derived cohorts | structural route difference |
| Sell/hold | V3-specific production and sale route | conserved sale-allocation wrappers | quantity and production confounded |
| Terminal | different route | full sell frontier at 718 | coherent but not isolated as a v2 revision |

## Same-turn semantics and execution failure

The harness uses the environment's real ordered market actions, affordability, expenses, and sales. The initial cross-version module-loader collision was corrected and its output excluded. In corrected runs, the major safety defect is real: in 40/48 V5 games, at step 210 the actor on pasture `[5,3]` requests `FEED` without carried wheat; the silent no-op leads to escape at the end of step 215. This is an executor/resource failure, not a timing gain.

## Why the name?

Empirically, “Timing Optimized” refers to **when visible shop evidence is considered mature and how long the resulting livestock direction remains committed**. It is not a general retiming of the farm economy. The public v2 refinement contributed 0 measured coins on this panel.
