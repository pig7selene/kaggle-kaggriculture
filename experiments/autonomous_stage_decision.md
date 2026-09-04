# Autonomous next-stage research decision (2026-09-01)

## Current evidence

- The frozen research best is `agents/top50_distilled/top50_observable_portfolio.py`.
- Complete-route family and market-residual probes either reversed on frontier
  seeds or contained less than about 100 coins of local oracle headroom.
- The safe checkpoint executor has zero safety failures but omits optional
  production; its gap attribution is dominated by crop revenue.
- A one-WHEAT commitment was fully realized but averaged -274 paired own coins.
- A one-MELON commitment had higher gross value but only 50% realization and
  averaged -517 paired own coins.

## Competing hypotheses

1. **Compact premium cohort:** a small, co-located MELON cohort can create
   meaningful own-money value if capital and one worker are reserved for its
   full lifecycle; the one-tile probe was too small and too exposed to route
   interference.
2. **Larger wheat cohort:** several short cycles might provide safer cash, but
   gross value is likely below the measured crop-revenue gap.
3. **Executor-only refinement:** better continuation safety without new
   production is unlikely to recover the dominant crop-revenue deficit.

## Cheapest falsifier selected

Implement a four-tile MELON cohort with explicit admission, feed-capital
reserve, persistent owner, daily watering, peak harvest, and terminal drop/sell
ownership.  It may override only PASS actions from the proven executor and
must never displace FEED/WATER or other observed commitments.  Compare it to
the passive executor on fresh checkpoint/seat pairs, recording intended versus
realized lifecycle counts and safety outcomes.

## Stop/scale rule

- Reject if paired own-money is non-positive, realization is below 80%, or any
  runtime/semantic/animal-loss/terminal-stranding gate fails.
- Only if the compact cohort is clearly positive will it be tested against the
  frontier panel and extended to a coupled target-driven executor.
- Frozen agents and `submission/main.py` remain untouched throughout.
