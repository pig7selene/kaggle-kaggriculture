# Autonomous next-step research report

Date: 2026-09-01

The frozen deployment/research best remained
`agents/top50_distilled/top50_observable_portfolio.py` (SHA-256
`f9ca672848ccffdfe56888d99bcdf5a9d7644062b9eec0cf0cdea13574931233`).
`submission/main.py` was not touched (SHA-256
`789bb9bbd5122eb4891983e776a13777328e3e87736cbbc0b4bc86d13fc33f9b`) and no
Kaggle submission was made.

## 1–4. Directions considered and falsified

| Direction | Test | Decision |
|---|---|---|
| Complete route-family medoids | 112-game cheap screen, then 128-game disjoint family-01 confirmation | Reject: deep own delta -10,692, advantage delta -14,642, P10 own -30,438 |
| New raw complete route | Existing locked 800-game validation of raw55899537 | Reject: own delta +182 (CI crosses zero), Top-3 own delta -4,730 |
| Current SELL reordering | 64 paired conditions on fresh seeds | No-op: 0 action changes and 0 own-money delta |
| Future SELL-slot assignment | 64 paired conditions, 611 assignments | Reject: own delta -954, P10 -2,225, 65.6% negative |
| Highest-money raw replay (`super_raw_55884271`) | 128 full games on seeds 50900–50907, both seats, frontier panel | Reject: own delta -6,649, advantage delta -4,382, P10 own -35,217 |
| General planner/executor takeover | Prior 28-game diagnostic | Reject: -8,298 advantage and 28/28 animal-loss games |
| Checkpoint-resume selection | Static route-bank compatibility audit | Defer: strict compatible ordered pairs shrink from 67.6% at step 24 to 1.6% at step 240 and <1% at steps 360–600 |

The route-family, market residual, and high-own-money raw-route experiments
were run in this stage.  The planner, blind splicing, and raw55899537 final
validation are prior locked evidence and were not repeated.

The replay corpus was current in the local manifests: Top-3 captured
2026-09-01 07:39 UTC (87 episodes; 30 current-version appearances each), the
adaptive corpus captured 08:37 UTC (216 episodes), and Top-50 captured
2026-08-31 15:16 UTC (250 episodes across 50 teams).  No newer version identity
was available locally, so no redundant Kaggle download was performed.

## 5–8. Architecture pursued and why

The selected research direction was a sequence of cheap falsifications rather
than a new deployable architecture.  First, complete route families were
executed whole to test whether a coherent economy was missing.  After that
failed on disjoint seeds, a market-only residual was built that could alter
only existing same-turn SELL slots or bounded future SELL slots.  This is the
smallest safe intervention because all crop, animal, land, labor, movement,
inventory, and terminal commitments remain owned by the frozen route.

New infrastructure:

- `run_autonomous_next_route_screen.py` (existing route-family screen)
- `experiments/autonomous_next_route_screen_report.md`
- `agents/autonomous_next/market_residual_reorder_v1.py`
- `agents/autonomous_next/market_residual_horizon_v1.py`
- `run_autonomous_market_residual.py`
- `audit_autonomous_checkpoint_compatibility.py`
- `experiments/autonomous_market_residual.json`
- `experiments/autonomous_checkpoint_compatibility.json`

The frontier study covered tetsuya, Crop Dusta, and OceanMix plus the broader
Top-50 corpus.  Shared evidence is a stable opening followed by history/state-
conditioned land, livestock, crop-cohort, labor, and sale decisions.  The
strongest player-specific signals are tetsuya's wool/fertilizer emphasis, Crop
Dusta's heavy wheat/feed cycling, and OceanMix's low-labor premium overlap;
fixed transplants failed, so these remain hypotheses rather than causal rules.

## 9–17. Quantitative results

The market residual panel used 192 full 720-step games: 8 fresh fixed seeds
(50800–50807), both seats, CurrentBest plus tetsuya, Crop Dusta, and OceanMix.

| Candidate | Games | W/L/T | Avg own money | Avg advantage | Median advantage | P10 advantage | P5 advantage | Variance advantage | Own delta vs CurrentBest |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| CurrentBest | 64 | 35/15/14 | 94,419 | 13,862 | 767 | -5,872 | -12,471 | 633,521,974 | 0 |
| reorder-v1 | 64 | 35/15/14 | 94,419 | 13,862 | 767 | -5,872 | -12,471 | 633,521,974 | 0 |
| horizon-v1 | 64 | 48/16/0 | 93,464 | 13,042 | 1,879 | -6,398 | -13,670 | 534,437,544 | **-954** |

Horizon-v1 paired deltas were: Crop Dusta -3,576 own / -4,113 advantage,
OceanMix -749 / -626, CurrentBest -46 / +914, and tetsuya +553 / +545.
There were zero runtime failures, zero semantic failures, and zero optimizer
errors across all 192 games.  Reorder-v1 changed no actions; horizon-v1 made
611 bounded assignments but had lower own money.  A fixed-seed bootstrap over
the 64 paired horizon conditions gave a 95% CI of **[-1,629, -367]** for own
money delta; reorder-v1's CI is exactly [0, 0] because it made no changes.

For context, the previously locked raw-route finalist had 400 paired
conditions / 800 games, own-money delta +182.2 with bootstrap 95% CI
[-1,612.4, +1,996.9], advantage delta +700.5, P10 own -24,208.5, P5 own
-29,868.0, and 0 runtime/semantic/escape failures.  It was not promoted.

Frontier reference for the retained CurrentBest (prior controlled panel):
48/8/0, average money 92,319, average advantage 22,463, P10 -4,826, P5
-14,790 against the fixed Top-3 representatives.  No new natural-RNG run was
performed in this stage; fixed-seed separation was preserved.  Prior raw-route
natural-RNG evidence was negative in own money (-2,603 delta), reinforcing
that H2H advantage can be market suppression rather than own growth.

The additional raw replay probe (`super_raw_55884271`, source replay money
144,328) was safe and 100% route-realized, but its paired own-money delta was
-6,649 on fresh frontier conditions.  Its per-opponent deltas were +5,206 vs
tetsuya, -25,770 vs Crop Dusta, -10,511 vs OceanMix, and +4,478 vs
CurrentBest.  A high public replay score therefore did not transfer as a
reusable economy.

## 18. Economic interpretation

The route medoid failure had 99.967% route realization and zero livestock
losses, so its loss is economic rather than an executor crash.  Its cheap
positive signal came from a narrow opponent/seed mix and reversed against
tetsuya and Crop Dusta on disjoint seeds.  Same-turn SELL permutation exposed
no headroom because the route's existing ordering was already locally optimal
under the exact own-market simulation.  Future slot assignment changed many
sales but pulled value out of the candidate's own economy under shared-market
interaction, especially against Crop Dusta.  The dominant unresolved value is
therefore not a free sell-order tweak; it is later state-compatible decisions
about crop cohorts, livestock scale, and market exposure.

## 19–21. Promotion

No new research best was promoted.  CurrentBest remains the observable
Top-50 portfolio at the SHA above.  The route medoids, raw route, reorder
residual, and horizon residual all failed robust own-money or frontier gates.

## 22. What this established

1. Complete-route family diversity is not automatically transferable: the only
   encouraging medoid signal was a false positive on a narrow panel.
2. The current route's same-turn sell sequence is not an obvious source of
   own-cash headroom.
3. A bounded future sell residual can alter hundreds of actions while still
   reducing own money; higher H2H win rate is not sufficient evidence.
4. Route-bank states become economically aliased quickly.  At day 10 (step
   240), only 8 of 506 ordered route pairs match all strict commitments
   (land, cohorts, geometry, animals, workers, seeds, inventories, and shed).
5. Safe adaptive value therefore requires an executor that owns coupled state,
   not another selector or arbitrary continuation splice.
6. Even the highest-money mined Top-50 replay can be strongly regime-specific:
   its whole-route probe lost 6.6k own money despite perfect realization.

## 23–24. Highest-value bottleneck and next stage

The highest-value remaining bottleneck is a checkpoint-resumable, target-driven
executor with explicit ownership of crop cohorts, worker zones, livestock
service, inventory, capital, and terminal liquidation.  The next stage should
first prove exact resume and same-state target execution on a small set of
coherent routes with zero animal loss; only then should the history-conditioned
Top-3 model propose guarded targets.  A narrow crop-cohort or livestock-target
executor is preferable to a general planner.  Do not package or submit until
that proof produces a robust positive own-money delta on frontier and unseen
seeds.
