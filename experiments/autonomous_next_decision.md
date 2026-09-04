# Autonomous next-step research decision

## 1. Strongest current evidence

The frozen deployment/research best is the observable Top-50 portfolio
(`agents/top50_distilled/top50_observable_portfolio.py`).  It safely selects
one complete route at step 1, but the locked 400-condition finalist validation
showed only **+182 paired own-money coins** (95% CI -1,612 to +1,997).  Its
competitive advantage delta was +700, largely from reducing opponent cash, and
it regressed by **-12,268 advantage coins** against the Top-3 frontier (tetsuya
-28,603).  The raw challenger was route-stable and safe, so execution safety is
not the only ceiling; product mix and market/capital realization are.

Top-3 replay analysis shows genuine history-conditioned branching (history
phase F1 0.973, decision F1 0.839), but the attempted general executor lost
animals in 28/28 games and arbitrary route splicing failed catastrophically.
This means the project has evidence of strategic headroom but no validated
target executor yet.

## 2. Main bottlenecks

1. Complete routes are economically coupled; partial continuation switching
   breaks crop, livestock, worker, and inventory invariants.
2. CurrentBest commits at step 1 and cannot respond later to premium-market
   regimes or the opponent's changing economy.
3. Existing selection screens over-weight H2H/advantage; the raw-finalist
   result showed that own-money and frontier tails must be primary.
4. The route bank has 23 complete routes and five family medoids, but only the
   family-01 variants feed the current portfolio.  Their frontier own-economy
   value has not been measured systematically.

## 3. Directions rejected or deferred

| Direction | Status | Reason |
|---|---|---|
| Blind route/phase splicing | Dead for now | Prior swaps caused -14k to -34k deltas and animal losses. |
| General replanning executor | Deferred | The only attempt was -8,298 advantage, P10 -132,772, 28/28 animal-loss games. |
| Primitive-action RL/fitted-Q | Deferred | No safe target executor or coherent counterfactual action-return data. |
| Immediate Top-3 policy imitation | Deferred | Reconstruction is good, but crop/market/cohort targets and execution compatibility are weak. |
| Large parameter/timing search | Low priority | Would optimize the wrong route family before establishing economic headroom. |
| New opponent-awareness selector | Deferred | Step-1 selector already demonstrates the value; later decisions need a coherent route. |

## 4. Plausible next directions

| Direction | Expected upside | Cost/risk | Cheapest falsification |
|---|---:|---|---|
| Complete-route family oracle and robust route search | +2k–+10k if an unrepresented family transfers to the frontier | Low; no state switching | Run family medoids as whole episodes against CurrentBest, tetsuya, Crop Dusta, OceanMix on a small paired panel. |
| Checkpoint-resumable target executor | +5k–+15k if invariants can be owned end-to-end | High implementation and safety risk | Resume a known route from day-10/day-20 checkpoints and measure exact-state/action fidelity before any adaptive target. |
| Market-only residual within a route | +1k–+5k | Medium; must preserve inventory/worker commitments | Replay a fixed route while varying only already-scheduled sale batches; compare own-money deltas and terminal safety. |
| History-conditioned delayed complete-route selection | +1k–+5k | Medium; route choice must happen before commitments diverge | Compute hindsight best complete route at step 24/48/72 and test whether the winning route is state-compatible at that checkpoint. |
| Self-play/value learning over high-level commitments | Unknown, potentially large | High data and safety burden | First estimate hindsight oracle headroom from the complete-route bank; stop if it is small or frontier-negative. |

## 5. Chosen direction

Pursue **complete-route family oracle/robust screening first**.  It has the
   highest information per unit compute and directly tests the unresolved
   question: *is the missing value in a different coherent economy, or does
   the project require a new executor?*  It avoids all known failure modes of
   splicing and general takeover.  The screen will use paired own-money as the
   primary metric, include all three Top-3 representatives early, cover both
   seats, and retain separate seeds for later confirmation.

If no family medoid shows a positive frontier own-money signal, the next stage
will be a narrow checkpoint-resume executor proof—not another route selector.
If a medoid shows a material positive own-money delta with acceptable tails and
zero safety failures, it becomes a complete-route candidate for held-out
validation; no promotion occurs from the cheap screen alone.

## Addendum after execution (2026-09-01)

The family screen and disjoint family-01 confirmation were completed.  The
family-01 medoid's cheap +2,531 own-money signal reversed to -10,692 on the
deep panel (P10 -30,438), so no complete-route family passed.  Before paying
the cost of a checkpoint executor, a narrower market-only falsification was
run: same-turn SELL reordering was a no-op, while bounded future SELL-slot
assignment lost 954 own-money coins on fresh frontier conditions.  A static
compatibility audit also found strict route-state matches below 2% by step 240.

The updated decision is to defer both route selection and market residuals and
build only a small checkpoint-resume/target-execution proof next.  It must
demonstrate exact state ownership (cohorts, workers, animals, inventory, and
capital) before any history-conditioned target or planner is allowed to act.
