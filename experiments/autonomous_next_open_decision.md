# Autonomous next-step decision

## What is known

The frozen Top-50 portfolio is still the validated research best.  A safe
checkpoint executor can finish observed crops, animals, feed, labor, and
liquidation with zero safety failures, but its continuation gap is dominated
by omitted production: about -37.7k crop revenue, -20.5k animal revenue, and
-10.0k fertilizer revenue over 32 paired conditions.  Route switching,
market-only residuals, and raw replay transfers either had no own-money
headroom or were regime-dependent.  A one-wheat lifecycle was fully realized
and safe, but averaged -274 own coins versus the passive executor control.

## Remaining uncertainty

The wheat result does not distinguish a bad crop family from an undersized
commitment.  Premium crops have much higher gross value, but their market
curves punish gluts and their seed/worker cost is larger.  A multi-tile cohort
could recover more value, but would couple more workers and inventories before
we know whether one high-value cycle has any local headroom.

## Alternatives and cheap falsifiers

| direction | cheap falsifier | risk |
|---|---|---|
| larger wheat cohort | four-tile lifecycle on the same checkpoint panel | likely too little gross value |
| one premium melon | one tile with a capital and market-price gate | glut and worker interference |
| baseline-proposal bridge | copy only observed BUY_SEED/PLANT proposals | route/state aliasing |
| new livestock/land target | one purchase with existing safety executor | uncoupled service failure |
| coupled target executor | build a full ownership state machine | highest effort, but addresses the measured gap |

## Selected first test

Test one **capital-gated melon lifecycle**.  It is the smallest experiment
that can falsify whether premium crop value is large enough to justify further
executor work.  The candidate will reserve feed cash, choose a nearby empty
tile, buy exactly one MELON seed only when the current market price is healthy,
and override only a persistent idle worker.  Existing safety tasks remain
authoritative.  If its paired own-money result is not clearly positive, the
next architecture should own a compact cohort plus worker/capital reservations
rather than adding isolated actions.

