# Open autonomous research stage — closure report

Date: 2026-09-01  
Scope: determine the next real source of performance without changing the
frozen strategy, packaging a submission, or calling Kaggle submission APIs.

## Frozen state and material review

The frozen local research best is
`agents/top50_distilled/top50_observable_portfolio.py` (SHA-256
`f9ca672848ccffdfe56888d99bcdf5a9d7644062b9eec0cf0cdea13574931233`).  The
existing packaged `submission/main.py` remained byte-identical during this
stage (SHA-256
`789bb9bbd5122eb4891983e776a13777328e3e87736cbbc0b4bc86d13fc33f9b`).  No
source strategy, submission, or Kaggle state was changed.

I reviewed `README.md`, `AGENTS.md`, `experiments/log.md`, the CurrentBest,
the V2 backbone (`agents/super_replay_v2/super_backbone_v2.py`), the
Top-50/Top-3 reports and datasets, the checkpoint-executor implementations,
and the V3/V4 replay lineages.  No separate V5/V6/V7/V8 artifacts were present;
the repository's historical V3/V4 directories are the latest named replay
lineages before the Top-50 work.

## Competing hypotheses

| ID | Explanation | Prior | Upside | Cheapest discriminating test | Status |
|---|---|---:|---:|---|---|
| H1 | A static complete route/family omitted from CurrentBest contains transferable value | medium | high | whole-route oracle, then disjoint frontier validation | **Rejected** |
| H2 | The executor cannot realize an alternative economic target safely | high | high | bounded target from real checkpoints with requested-vs-realized telemetry | **Partly supported, not sufficient alone** |
| H3 | Top-3 phase/decision labels have direct causal value | medium | high | whole Top-3 package from turn 0 against CurrentBest | **Rejected as a deployable shortcut** |
| H4 | Existing route value is mostly hidden in SELL ordering | low | low | same-turn and bounded future SELL residuals | **Rejected** |
| H5 | A regime-conditioned complete economic program is required | high | high | compare hindsight route oracle with fresh cross-regime transfer | **Survives; primary direction** |
| H6 | Lifecycle ownership (workers, geometry, capital, terminal capacity) is the limiting control variable | high | high | one-to-four-tile lifecycle with explicit ownership and held-out realization | **Supported as a mechanism** |
| H7 | Primitive-action RL/self-play is needed before a coherent high-level action oracle exists | low | unknown | first establish high-level executable headroom | **Deferred; not justified** |

The ranking is about research priority, not certainty.  H5 and H6 are the
survivors because they explain both the safety failures of broad replanning and
the incomplete value realization of narrow interventions.

## Diagnostic experiments and results

### 1. Replay prediction and causal transfer

The version-pure Top-3 corpus contains 219 teacher appearances (86 tetsuya,
66 Crop Dusta, 67 OceanMix; 215 unique valid replay files).  A 120-turn
history model reconstructed active phases at F1 **0.973**, major decisions at
F1 **0.839**, with transition recall **1.000** and mean timing error **4.1
steps**.  Current-state-only reconstruction was 0.865/0.735 and turn-only was
0.488/0.614.  Thus history matters for *imitation/prediction*.  Only 63.5% of
sampled CurrentBest states passed the combined OOD, distance, and confidence
guards, and crop/market/cohort decisions were the weak heads.

The whole-package transfer probe used fresh seeds 56400–56403, both seats,
and 24 games:

| Package | W/L/T vs CurrentBest | Mean advantage | P10 advantage |
|---|---:|---:|---:|
| tetsuya | 0/8/0 | -22,384 | -30,271 |
| Crop Dusta | 2/6/0 | -28,592 | -63,800 |
| OceanMix | 0/8/0 | -5,313 | -7,056 |

The labels predict replay behavior but are not a causal control signal when
the execution state is owned by a different economy.

### 2. Planner/executor integrity

`goal_executor_v1` was tested on the prior 28-game diagnostic panel.  It
averaged **-8,298 advantage coins**, had P10 **-132,772**, and lost animals in
**28/28** games.  A safety-gated control that disabled the planner around
animals was action-for-action the frozen route.  This separates an executor
integrity failure from a claim that adaptive targets have no value.

The narrower `commitment_executor_v1` passed resume, perturbation, and
commitment audits with zero runtime/semantic failures, zero animal losses and
zero terminal-stranding conditions.  Its attribution gap was mostly omitted
production (crop, animal, and fertilizer revenue), so “safe continuation” is
not the same as “profitable alternative economy.”

### 3. Complete-route diversity and transfer

The hindsight oracle evaluated **23 complete routes**, two fresh seeds
(56300–56301), and both seats (**92 games**).  The best route for seed 56300
was `super_raw_55885628`; for seed 56301 it was `super_raw_55859516`.
The four-condition oracle improvement was **+18,906.5 own coins** (P10/P5
**+16,160**).  This is a useful upper-bound signal, not a promotion result:
the winning route changed with the seed and the panel was intentionally tiny.

Three routes selected from that oracle were then tested whole on disjoint
seeds 56310–56313, against CurrentBest and tetsuya/Crop Dusta/OceanMix, both
seats (**128 games**):

| Route | Mean own-money Δ vs CurrentBest | Median Δ | P10 Δ | P5 Δ | H2H W/L/T | Safety |
|---|---:|---:|---:|---:|---:|---|
| 55885628 | -10,939 | -5,797 | -44,933 | -64,247 | 26/6/0 | 0 runtime, 0 semantic, 0 animal-loss |
| 55906837 | -4,008 | -314 | -35,334 | -42,044 | 26/6/0 | 0 runtime, 0 semantic, 0 animal-loss |
| 55909034 | -4,279 | -655 | -35,939 | -43,265 | 22/10/0 | 0 runtime, 0 semantic, 0 animal-loss |

The route-55885628 result is the clearest falsifier: a large hindsight gain
collapsed to a large fresh loss despite approximately 100% route realization.
The route itself was executable; its economics were regime-specific.

The previously locked raw route `top50_raw_55899537` remains rejected after
800-game final validation: paired own-money **+182.2** with a bootstrap 95%
CI of **[-1,612.4, +1,996.9]**, and a **-12,267.8** advantage regression
against the Top-3 frontier.  A separate high-money replay probe
(`super_raw_55884271`) was 100% route-realized and safe but lost **6,649** own
coins on fresh frontier conditions.  Public replay money is therefore not a
portable economic label.

### 4. Market residual

The market-only panel used 8 fresh fixed seeds (50800–50807), both seats,
CurrentBest, and the three Top-3 representatives (**192 games**).  Reordering
SELL orders already in the same turn changed **zero actions** and produced
exactly **0 own-money delta**.  A bounded future-slot residual made 611
assignments but reduced own money by **954** (bootstrap 95% CI
**[-1,629, -367]**), with 65.6% negative conditions.  It also reduced mean
advantage by about 820.  Market sequencing is not a free source of headroom;
future sale timing interacts with the whole production and opponent state.

### 5. Compact lifecycle capability

The checkpoint cohort probes kept the frozen route as the control and varied
only optional melon ownership:

| Candidate | Conditions | Mean own Δ | Median | P10 | Lifecycle realization |
|---|---:|---:|---:|---:|---:|
| compact cohort v1 | 16 | -464 | 0 | -2,811 | 75% admissions harvested |
| compact cohort v2 (parallel owners) | 16 development | +45 | 0 | -927 | 50% of target tiles harvested |
| v2 held-out | 8 | **-2,320** | -2,297 | -5,785 | 43.8% of target tiles harvested |
| v3 (+ one extra hand) | 16 | -549 | 0 | -4,322 | 37.5% of target tiles harvested |

Runtime and semantic failures were zero, as were incremental animal losses and
terminal stranding on the held-out v2 panel.  The extra hand did not repair
realization.  The theoretical four-melon gross ceiling (5,680 before labor,
movement, and market effects) is therefore not an executable expected value
under a partial-owner interface.

## Causal interpretation

The evidence separates four quantities that were previously conflated:

1. **Prediction quality:** high for phase/history reconstruction.
2. **Execution safety:** achievable for preserving existing commitments.
3. **Economic realization:** poor when an optional target does not own every
   watering/harvest/transport/capital obligation.
4. **Transferable economic value:** unstable across market/opponent regimes.

H2 is real but incomplete.  The safe executor proves that actions can be
validated and existing livestock can be preserved, while the cohort results
prove that partial ownership realizes only 38–50% of a nominal target.  H1 is
not supported: complete routes with nearly perfect route fidelity still reverse
on fresh regimes.  H3 is not supported as direct control: strong prediction
does not survive an incompatible continuation.  H4 is falsified by the no-op
reorder and negative horizon residual.

The actual primary bottleneck is **state-compatible ownership of a complete
economic program**.  That program must jointly own land and structures, crop
cohorts, worker zones and movement, livestock service/feed, inventory and
capital reserves, market exposure, and terminal liquidation.  CurrentBest's
step-1 selector can choose among complete programs but cannot replan after
future shops, prices, or realized production diverge.

## Economic attribution and externality

The earlier raw-route ledger showed that its roughly +2,073 own-money signal on
four matched seeds came from strawberry (+900), fertilizer (+657), wheat
(+266), wool (+156), milk (+30), slightly lower feed/product spend (-114), and
only a small strawberry throughput increase.  This is mostly market/capital
cycling, not a universal production advantage.

The complete-route fresh validation makes the externality explicit: some
routes improved H2H advantage against one opponent while losing own money
against the same frozen control.  The compact cohort's theoretical gross value
also failed to appear as final bank because movement and interference costs
were charged to the candidate's own economy.  Own money, opponent money, and
net advantage must remain separate metrics in the next stage.

## Candidate inventory and promotion status

| Candidate/capability | Result | Status |
|---|---|---|
| `goal_executor_v1` | -8,298 advantage; 28/28 animal-loss games | rejected |
| `goal_executor_safe_v1` | baseline-identical fallback | rejected as an improvement |
| `top50_family01_medoid` and other family medoids | family-01 deep -10,692 own; others negative | rejected |
| `top50_raw_55899537` | +182 own on locked 800-game validation; frontier regression | rejected |
| `market_residual_reorder_v1` | exact no-op | rejected/no headroom |
| `market_residual_horizon_v1` | -954 own, CI entirely negative | rejected |
| `compact_melon_cohort_v1/v2/v3` | negative held-out or incomplete realization | rejected |
| **CurrentBest** `top50_observable_portfolio` | unchanged, safe complete portfolio | **retained research best** |

For the retained CurrentBest, candidate deltas are necessarily zero by
definition.  No new candidate achieved the promotion gate of robust positive
own money, non-negative tails, direct H2H improvement, and zero critical safety
failures.

## Answers to the requested questions

1. **Initial bottleneck suggested:** safe execution of adaptive economic
   decisions; the old route executor was tightly coupled.
2. **Competing hypotheses:** static route diversity (H1), executor realization
   (H2), Top-3 causal labels (H3), SELL sequencing (H4), regime-conditioned
   complete programs (H5), lifecycle ownership (H6), and primitive RL/self-play
   (H7).
3. **Diagnostic experiments:** Top-3 history reconstruction; goal-executor
   safety screen; complete-route oracle; fresh route validation; Top-3 package
   transfer; market residual; checkpoint compatibility; and compact lifecycle
   cohorts.
4. **Falsified:** static route transfer, direct Top-3 package transfer, simple
   SELL reordering, bounded future SELL residual, broad planner takeover, and
   isolated optional crop commitments.
5. **Survived:** history as a predictor; execution integrity as a real
   mechanism; lifecycle ownership; and a regime-conditioned complete economic
   program as the highest-value architecture.
6. **Actual primary bottleneck:** one controller does not own all coupled
   commitments while adapting to market/opponent regimes.
7. **Executor realization improved?** Safety realization improved for existing
   commitments (zero failures), but optional target realization did not: held-out
   melon cohorts harvested only 43.8% of target tiles.
8. **How measured:** every target was tracked as requested, seed-acquired,
   planted, watered, matured, harvested, and sold; runtime, semantic,
   livestock-loss, and terminal-stranding counters were recorded separately.
9. **Top-3 causal value:** no generalized causal value established; packages
   lost 5–28k advantage on the cheap transfer panel.
10. **History for control:** history materially improves prediction (phase F1
    +0.086; decision F1 +0.097 over current state), but no safe delegation was
    enabled, so causal control value remains unproven.
11. **Planning:** the broad planner takeover did not help; it broke livestock
    invariants.  Planning is not disproven, but requires a new end-to-end
    executor.
12. **Market modeling:** simple sequencing did not help; the residual was
    either a no-op or negative.  Full regime-aware market planning remains open.
13. **Value learning:** not justified yet; there is no coherent alternative
    action-return dataset and the only valid route oracle was regime-unstable.
14. **RL:** not justified; primitive 719-turn RL would learn executor failure
    before high-level headroom is demonstrated.
15. **Self-play:** not justified; there is no controllable adaptive policy to
    train against a diverse population.
16. **New capabilities built:** deterministic paired harnesses, route-bank
    oracle/validation, market residuals, compatibility audit, safe checkpoint
    executor, target realization telemetry, and promotion/decision records.
17. **Candidate agents created:** goal executor variants, route-family medoids,
    raw complete-route probes, market residual agents, and compact-melon
    cohort variants under `agents/autonomous_next/` and
    `agents/checkpoint_executor/`.
18. **Strongest candidate:** the unchanged CurrentBest portfolio; no new
    candidate survived.
19. **Paired own-money delta vs CurrentBest:** CurrentBest 0 by control;
    route 55885628 -10,939, route 55906837 -4,008, route 55909034 -4,279,
    horizon residual -954, and held-out compact cohort v2 -2,320.  The
    rejected raw 55899537 was only +182.2 on its locked final panel.
20. **Advantage delta:** route 55885628 -10,372, route 55906837 -10,126,
    route 55909034 -9,988; horizon residual about -820.  The raw 55899537
    locked finalist was +700.5 overall but -12,267.8 against the Top-3
    frontier, so it was not robust.
21. **Direct H2H:** route candidates won 26/6/0, 26/6/0, and 22/10/0 in
    the mixed fresh league but still lost own money; H2H alone was misleading.
22. **Natural RNG:** no new natural-RNG panel was run in this stage; fixed
    seed separation was preserved.  Prior raw-route natural evidence was
    negative in own money.
23. **Strong/adaptive pool:** the complete-route fresh validation included
    tetsuya, Crop Dusta, and OceanMix; all three route candidates lost own
    money overall.  The Top-3 package probe was also negative.
24. **P10:** route candidates -44,933, -35,334, -35,939; compact v2 held-out
    -5,785; horizon residual -6,398 advantage (own-money CI wholly negative).
25. **P5:** route candidates -64,247, -42,044, -43,265; compact v2 was not
    large enough for a stable P5 but its lower tail was negative.
26. **Worst result:** the planner's -132,772 P10 with 28/28 animal losses;
    among safe whole routes, route 55885628 had -64,247 P5.
27. **Safety:** safe executor, route probes, residuals, and cohorts had zero
    runtime/semantic failures in their reported panels; the broad planner did
    not pass animal safety.
28. **Economic attribution:** small raw-route gains were mainly strawberry,
    fertilizer, wheat, wool and milk revenue plus feed savings; route transfer
    losses were economic, not route-crash failures.
29. **Requested vs realized accuracy:** complete routes were approximately
    100% realized; compact cohorts were only 37.5–50% harvested on the
    meaningful held-out/development panels.
30. **Oracle/headroom:** a two-seed route oracle showed +18,906.5, but fresh
    validation reversed to -4,008 to -10,939.  Transferable headroom is
    therefore not established and may be near zero without regime conditioning.
31. **New research best promoted:** no.  CurrentBest remains frozen.
32. **Source/SHA if promoted:** not applicable; retained source is
    `agents/top50_distilled/top50_observable_portfolio.py`, SHA
    `f9ca672848ccffdfe56888d99bcdf5a9d7644062b9eec0cf0cdea13574931233`.
33. **Evidence preventing promotion:** fresh sign reversal, negative own-money
    tails, Top-3 frontier regressions, and/or incomplete lifecycle realization;
    no candidate met all safety and economic gates.
34. **Next highest-value direction:** build a small checkpoint-resumable
    complete economic-program executor.  First prove, from diverse valid
    states, that it can own a compact target end-to-end with ≥80% realization,
    zero animal/crop losses, and terminal liquidation.  Then measure a
    same-state executable oracle across disjoint regimes, and only afterward
    let the history-conditioned Top-3 model propose guarded targets.  Keep
    CurrentBest as the safety fallback and do not use primitive RL/self-play
    before that oracle survives held-out seeds.

## Decision

The stage is closed without a new agent promotion.  The productive next step is
not another fixed route, SELL threshold, or isolated crop patch.  It is a
small, instrumented, end-to-end commitment executor whose target is evaluated
as a complete economic program rather than as a handful of borrowed actions.
All frozen source/submission files and historical artifacts remain preserved.
