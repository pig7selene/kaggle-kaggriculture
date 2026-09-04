# Autonomous Strategic Breakthrough Research

## Executive conclusion

The main bottleneck was not the ability to infer high-level behavior from
replays.  The Top-3 distillation work recovered phase and decision structure
with strong held-out accuracy, and history was materially useful.  The
blocking issue was converting a new strategic target into a *coherent,
safe, executable economy*.  The existing executor is a complete replay route
with tightly coupled worker geometry, transactions, crop cohorts, livestock
service, and terminal cleanup.  Switching only part of that route breaks the
coupling.

Two hypotheses were tested:

1. A state-driven goal executor would safely take over after the opening.
2. More complete, economically distinct route families would provide value
   without unsafe route splicing.

The first hypothesis failed decisively.  The second survived: a raw route
from the Top-50 route bank beat the frozen portfolio on two independent paired
panels and on the held-out control league, with zero observed animal losses.
The gain is real but modest (about +2,000 paired coins), so this is a
research-best promotion rather than a low-risk deployment decision.

## Frozen baseline and reproducibility

| Item | Path | SHA-256 |
|---|---|---|
| Frozen baseline | `agents/top50_distilled/top50_observable_portfolio.py` | `f9ca672848ccffdfe56888d99bcdf5a9d7644062b9eec0cf0cdea13574931233` |
| Promoted research best | `agents/autonomous_next/top50_raw_55899537.py` | `5d66e9283e4e500a4113a6d167abb04e0a088c2ad8799c1750da4b7a2172d069` |
| Submission (preserved) | `submission/main.py` | `789bb9bbd5122eb4891983e776a13777328e3e87736cbbc0b4bc86d13fc33f9b` |

The baseline source and submission were not edited during this stage.  No
Kaggle upload or submission API was called.  All games used the local
`kaggriculture` environment with 720 steps, deterministic seeds, and both
player seats.  The benchmark scripts and machine-readable outputs are:

- `run_autonomous_breakthrough_research.py`
- `validate_autonomous_route_candidates.py`
- `validate_raw_route_h2h.py`
- `analyze_route_candidate_economics.py`
- `analyze_raw_h2h_economics.py`
- `experiments/autonomous_breakthrough_diagnostics.json`
- `experiments/autonomous_route_validation.json`
- `experiments/autonomous_raw_route_h2h.json`
- `experiments/autonomous_raw_h2h_economics.json`
- `experiments/autonomous_route_economics.json`

The raw-route H2H artifact contains the second 16-seed confirmation panel;
the first panel was run with the same paired protocol on seeds 17000--17015
before the later confirmation artifact was written.

## What the existing evidence said before this stage

The Top-3 corpus contained 219 version-pure teacher appearances (86 tetsuya,
66 Crop Dusta, 67 OceanMix) and 215 unique valid replay files.  The best
structured-history reconstruction reached:

| Input | Phase macro-F1 | Major-decision macro-F1 | Transition recall | Mean transition error |
|---|---:|---:|---:|---:|
| Turn only | 0.488 | 0.614 | 0.509 | 16.9 steps |
| Current state | 0.865 | 0.735 | 0.939 | 6.4 steps |
| 120-turn state/history | **0.973** | **0.839** | **1.000** | **4.1 steps** |

History therefore carries deployable signal.  It does not, by itself, make a
different action sequence executable.  Crop-family F1 was 0.687, strict
market-mode F1 0.555, and cohort scale was within two plants only 37.0% of the
time.  Only 63.5% of sampled frozen-baseline states passed the combined range,
distance, and confidence guards.  These limits made blind target delegation
unsafe.

## Hypothesis 1: state-driven planner/executor takeover

`agents/autonomous_next/goal_executor_v1.py` used the proven opening and
switched to a state-driven crop executor at step 240 (day 10).  It attempted
to reason from the actual farm state and merged a backbone fallback for
livestock.  The safety-gated ablation,
`goal_executor_safe_v1.py`, disabled planner actions whenever animals were
present.

### Diagnostic result

The diagnostic screen used seeds 15000 and 15001, both seats, and the frozen
portfolio plus six diverse proxy opponents (28 games per candidate):

| Candidate | W/L/T | Average advantage | P10 advantage | Animal-loss games | Runtime errors |
|---|---:|---:|---:|---:|---:|
| Frozen portfolio | 25/1/2 | +126,953 (proxy-heavy) | 0 | 0 | 0 |
| Goal executor v1 | 20/8/0 | **-8,298** | **-132,772** | **28/28** | 0 |
| Safety-gated control | 25/1/2 | +126,953 | 0 | 0 | 0 |

The proxy-heavy average is not a claim about Kaggle strength; the decisive
signals are the direct frozen-baseline matchup and the catastrophic tail.  In
all 28 goal-executor games, the planner changed worker positions and/or market
order timing enough that the existing livestock service continuation no longer
matched the farm state.  Animals then missed feed/service deadlines and
escaped.  The repair code could not restore the lost route invariants.  With
the planner gated off around animals, behavior was identical to the baseline,
showing that this was an executor-integrity failure rather than evidence that
adaptive targets have no value.

### Interpretation

The experiment falsifies “switch a crop planner into a replay economy” as a
deployable architecture.  It does **not** falsify state-driven planning in a
new executor that owns land, crop cohorts, inventory, labor, and livestock
service together.  A planner takeover is only meaningful after that executor
can resume from a real checkpoint and maintain all safety deadlines.

## Hypothesis 2: complete route-family expansion

Two coherent routes were built from the existing Top-50 bank:

- `top50_family01_medoid.py`, a route-family medoid;
- `top50_raw_55899537.py`, a complete raw route selected without action
  splicing.

Each uses the same Stage-3 bounded safety executor as the proven parents.  The
raw route differs from the frozen portfolio/medoid in hundreds of actions,
including larger and less frequent market-sale batches; it is a complete
capital-and-worker plan, not a late-phase patch.

### Direct paired confirmation

Every seed was played twice, once in each seat, with the candidate and frozen
portfolio in the same environment.

| Panel | Seeds | Games | W/L/T | Candidate money | Frozen money | Mean advantage | Median advantage | P10 | P5 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 17000--17015 | 32 | 32/0/0 | 89,435 | 87,231 | +2,204 | — | +1,139 | +525 |
| B | 18000--18015 | 32 | 32/0/0 | 78,449 | 76,700 | +1,749 | +1,615 | +723 | +597 |
| Combined | 32 distinct seeds | 64 | **64/0/0** | — | — | **about +1,976** | positive | positive | positive |

Panel B is persisted in `experiments/autonomous_raw_route_h2h.json`; the
route-validation and diagnostics artifacts provide independent checks on the
same candidate.

### Held-out strong-control league

Seeds 16000--16003, both seats, eight replay-era/proxy controls (64 games)
gave the raw route **64/0/0**, mean advantage **+48,942**, P10 **+1,873**,
P5 **+1,162**, zero runtime errors, and zero observed animal losses.  This
league includes weak local proxies, so it is a robustness/safety control, not
a claim that the candidate is 48k stronger against real Kaggle players.  The
direct H2H numbers above are the promotion evidence.

The family medoid also beat the frozen portfolio 4/0 on the two-seed
diagnostic matchup (mean advantage +2,400), but the raw route had the stronger
held-out tail and was selected.

## Economic attribution

Four additional matched seeds (17200--17203, both seats) were replayed with
the transition ledger in `autonomous_raw_h2h_economics.json`:

| Quantity (candidate minus frozen) | Delta |
|---|---:|
| Final money | **+2,072.5** |
| Strawberry revenue | +900.0 |
| Fertilizer revenue | +657.0 |
| Wheat revenue | +265.8 |
| Wool revenue | +155.5 |
| Milk revenue | +30.0 |
| Strawberry harvest units | +4 |
| Milk harvest units | -2 |
| Feed/product spending | -114.3 |
| Seed spending | +50.0 |

The revenue gain is about +2,008 coins and the net cost change is -64 coins,
which reconciles to the +2,072.5 final-money delta.  The candidate's advantage
is therefore mostly a market/capital-cycling improvement, with a small
strawberry throughput contribution—not a wholesale production increase.
The broader route-economics run also showed that changing sale batch timing
can redistribute value between milk, wool, and strawberry depending on the
shared market; that is why both own money and H2H advantage were tracked.

## What was built

The stage added a small, reproducible research harness rather than a new
submission package:

- a state-driven goal executor prototype and a safety-gated control;
- a route-family medoid and a complete raw Top-50 route challenger;
- paired H2H, held-out league, and transition-ledger economic analyses;
- machine-readable diagnostics suitable for later checkpoint/resume tests;
- a promotion registry update in `experiments/current_best.json`.

The promoted research best is `agents/autonomous_next/top50_raw_55899537.py`.
The promotion gate deliberately records the caveat that the gain is below the
preferred +3,000 own-money target.  The previous portfolio remains available
as the frozen comparison baseline.

## What was rejected and why

| Direction | Decision | Evidence |
|---|---|---|
| Planner takeover with existing route fallback | Reject | -8,298 mean advantage, -132,772 P10, 28/28 animal-loss games |
| Safety gate that disables planner around animals | Reject as an improvement | Exact baseline behavior; no added value |
| Blind phase/route splicing | Do not pursue | It destroys the coordinated crop/livestock/worker state; no coherent continuation exists |
| Lowering Top-3 OOD/confidence thresholds | Reject | Would turn uncertain crop/market/cohort predictions into unsafe actions |
| Fitted-Q or primitive-action RL | Not justified yet | No coherent target executor or validated counterfactual action-return dataset |

## Remaining bottleneck and next stage

The surviving route-family gain says that executable economic diversity is
valuable, but the remaining ceiling is likely in **state-compatible adaptive
market and portfolio decisions**.  The portfolio selector reacts only to the
opponent's visible step-1 bank and hand count, then commits to one route.  It
cannot safely adapt later to market realization, future shops, or a diverging
crop/livestock state.  Its paired P10/P5 are still negative in the broader
Top-50 work, so one should not package this promotion automatically.

The next scientifically useful architecture is a checkpoint-resumable,
target-driven executor that owns all coupled commitments (land, structures,
animals, feed, crop cohorts, worker zones, sales, and terminal liquidation).
Use the distilled history model only as a guarded target proposer.  First prove
that the executor can realize a small number of known coherent targets from
varied states with zero animal losses; only then measure counterfactual target
value or train a residual value model.  Do not use policy-from-scratch RL or
blind route splicing before that proof.

## Final answer sheet

1. **Actual bottleneck:** safe realization of adaptive economic decisions; the
   old executor is a tightly coupled complete route.
2. **Architectures tested:** state-driven goal executor and complete route-family
   expansion.
3. **Rejected:** planner takeover, its safety-gated no-op variant as an
   improvement, blind splicing, and premature RL/value fitting.
4. **Survivor:** complete coherent raw-route selection.
5. **Infrastructure:** paired deterministic H2H, held-out league, economic
   ledger, route candidates, diagnostics, and promotion registry.
6. **New capability:** selecting among complete Top-50 economies at step 1,
   with bounded safety repair.
7. **Oracle/headroom:** no valid target oracle was run; the existing executor
   exposed no coherent alternative continuation.  The observed raw-route
   opportunity is about +2k paired coins.
8. **Candidate agents:** `goal_executor_v1`, `goal_executor_safe_v1`,
   `top50_family01_medoid`, and `top50_raw_55899537`.
9. **Strongest candidate:** `agents/autonomous_next/top50_raw_55899537.py`.
10. **Paired own-money delta:** +2,072.5 on the four-seed economic panel;
    approximately +2k on the independent 32-seed H2H panel aggregate.
11. **Advantage delta:** +1,748.8 on persisted panel B; +2,203.6 on panel A;
    approximately +1,976 combined.
12. **H2H:** 64/0/0 across the two 16-seed paired panels.
13. **Natural RNG:** not claimed as a separate natural-RNG study; all reported
    panels use fixed deterministic seeds.
14. **Strong/adaptive pool:** held-out control league 64/0/0, +48,942 mean
    advantage, P10 +1,873, zero animal losses.
15. **P10:** +723 on persisted direct panel B; +1,139 on panel A; +1,873 on
    the held-out control league.
16. **P5:** +597 on panel B; +525 on panel A; +1,162 on the held-out control
    league.
17. **Safety:** zero runtime errors in all successful panels and zero observed
    animal losses for the raw route; the goal executor had 28/28 animal-loss
    games and is not deployable.
18. **Economic attribution:** strawberry/fertilizer/wheat/wool/milk revenue
    and slightly lower feed spend, as tabulated above.
19. **Did Top-3 knowledge help?** Yes as evidence and history features, but
    not as a directly deployable target policy.
20. **Did history help control?** It materially improved reconstruction, but no
    safe delegated control was enabled; therefore causal control gain is not
    established.
21. **Was a planner/executor necessary?** A new one is necessary for future
    adaptive targets; the attempted takeover was defective.
22. **Was learning necessary?** Not for this measured gain; route-family
    selection won without a learned controller.
23. **Was RL justified?** No; action-return data and a safe target executor are
    still missing.
24. **Was self-play justified?** No; route-family and checkpoint-safe control
    should be solved first.
25. **Was a new research best promoted?** Yes, cautiously, as a local research
    best only.
26. **Promoted source/SHA:** `agents/autonomous_next/top50_raw_55899537.py`,
    `5d66e9283e4e500a4113a6d167abb04e0a088c2ad8799c1750da4b7a2172d069`.
27. **Largest remaining bottleneck:** late, state-compatible market/portfolio
    adaptation and the negative paired lower tail.
28. **Recommended next stage:** build and verify a checkpoint-resumable
    target-driven economic executor, then test guarded residual/value decisions
    on unseen seeds.

## Final lock

- `agents/top50_distilled/top50_observable_portfolio.py` remains unchanged and
  is the frozen baseline used for all comparisons.
- `experiments/current_best.json` records the raw-route promotion.
- `submission/main.py` was not modified by this stage and no Kaggle action was
  performed.
