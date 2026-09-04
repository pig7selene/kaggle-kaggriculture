# Territory lifecycle scheduler research

Date: 2026-09-02

## Scope and frozen control

The research control was `agents/top50_distilled/top50_observable_portfolio.py`
(the retained CurrentBest).  `submission/main.py` was not touched.  The new
candidates call the CurrentBest from turn 0 and preserve its market orders,
opening, land, livestock, labor-capital, opponent-observation, and terminal
policies.  Only unit actions are eligible for a narrow crop overlay.

The completed routing audit (`experiments/top_player_worker_routing.json`)
provided the target evidence: public agents keep 100% territory purity, with
movement/productive ratios of 0.94, 0.95, and 1.15 at 25/50/75 unlocked tiles.
The 75-tile population is the stressed scale: 44.4% movement, 13.1% PASS,
and 1.15 moves per productive action.  Critical watering misses remain below
0.4% in that corpus, so a rescue must be very selective; indiscriminate
cross-territory work is likely to be negative.

## Ablation definitions

| Variant | Change |
| --- | --- |
| S0 | exact CurrentBest unit actions (control) |
| S1 | persistent worker-to-quadrant assignment; local crop tasks only |
| S2 | S1 plus one-refresh watering deadline rescue |
| S3 | S2 plus same-worker harvest-to-replant chaining and cohort priority |

Animal actions, carried animals, wheat/feed movement, shed logistics, and any
already-issued crop action are protected.  S3 admits a replant only when the
same worker harvested the tile on the immediately preceding turn and the seed
is already owned; it cannot create a new capital commitment.

## Real-loss smoke (recorded episodes)

Four reconstructed loss opponents (Jayveer, Pedro, Lucas, Alexander), both
seats, eight games per variant, all completed with zero runtime, semantic, and
livestock failures.

| Variant | W/L/T | Avg advantage | P10 | Avg harvests | Crop revenue d10–20 | Water miss |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| S0 | 8/0/0 | +49,348 | +29,027 | 351.0 | 41,826 | 29.11% |
| S1 | 8/0/0 | +49,348 | +29,027 | 351.0 | 41,826 | 29.11% |
| S2 | 8/0/0 | +49,348 | +29,027 | 351.0 | 41,826 | 29.39% |
| S3 | 8/0/0 | +49,348 | +29,027 | 351.0 | 41,826 | 29.39% |

The recorded traces are now much weaker than CurrentBest, so this panel is a
safety/causality check rather than a promotion league.

## Held-out hard-route confirmation

The confirmation used four fresh seeds (`981100–981103`), both seats, and the
strong local families `top50_dmitry`, `top50_hanserong`, `top50_redblack`,
`super_replay_v2`, `v27_k9_full`, and `lifecycle_lc` (192 proxy games), plus
the eight recorded-loss games per variant.  All 224 games reached 720 turns.

| Variant | Games | W/L/T | Win rate | Avg advantage | Median | P10 | P5 | Adv variance | Harvests | Crop rev d10–20 | Water miss | Replant delay | Animal losses |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| S0 | 56 | 48/0/8 | 85.7% | +18,936.2 | +7,780.5 | 0.0 | 0.0 | 412,896,562 | 352.0 | 40,395 | 29.47% | 6.21 | 0 |
| S1 | 56 | 48/0/8 | 85.7% | +18,936.2 | +7,780.5 | 0.0 | 0.0 | 412,896,562 | 352.0 | 40,395 | 29.51% | 6.21 | 0 |
| S2 | 56 | 48/8/0 | 85.7% | +18,862.4 | +7,739.5 | −38.5 | −41.0 | 409,688,382 | 351.4 | 40,395 | 29.67% | 6.44 | 0 |
| S3 | 56 | 48/8/0 | 85.7% | +18,862.4 | +7,739.5 | −38.5 | −41.0 | 409,688,382 | 351.4 | 40,395 | 29.67% | 6.44 | 0 |

### Matchup detail

S0 and S1 were identical against every opponent.  S2/S3 were also identical
to S0 except against `top50_redblack`, where they changed eight tied games to
losses (mean −40.75 coins).  No variant improved a harvest count or crop
revenue.  S1 generated only a handful of harmless equivalent route changes;
S2/S3 generated 272 urgent overrides across the held-out panel.  S3 generated
zero actual chain plantings: no state simultaneously offered a same-worker
harvest, owned replacement seed, and unclaimed route slack.

## Interpretation

1. The initial broad territory idea is not portable over a replay-route
   economy.  The route already protects nearly all productive actions, and
   replacing movement steps cannot reproduce the route's hidden future
   commitments.
2. Persistent territories are safe but have no headroom when applied as a
   passive overlay: the route's units are already committed before an
   observable crop deadline appears.
3. Deadline rescue is economically non-positive.  It increased watering miss
   rate slightly (29.47% → 29.67%), reduced harvests by 0.6 per game, and
   introduced a small negative tail without increasing crop revenue.
4. Replant chaining did not activate.  This is evidence that a useful chain
   must own the complete crop cohort (seed admission, territory, watering,
   harvest, shed transport, and market slot), not merely patch a PASS action.
5. The real bottleneck remains coherent lifecycle ownership and state-based
   replanning.  A scheduler-only overlay cannot safely borrow enough worker
   time from the frozen replay backbone to close the public crop-throughput
   gap.

## Decision

No candidate is promoted.  S0/CurrentBest remains the strongest and safest
policy; `submission/main.py` and all existing strategy files remain unchanged.
S1 is a useful no-op safety control.  S2 and S3 are rejected because they do
not improve throughput and create a reproducible negative tail against one
strong route.

The next justified architecture is a coherent state owner that plans a
bounded crop cohort together with worker reservations and the existing animal
commitments from the beginning of the episode.  Any future candidate should
be measured on requested-versus-realized cycles and must demonstrate positive
own-money delta on held-out strong families before adding market or opponent
complexity.

Artifacts:

- `agents/territory_lifecycle_common.py`
- `agents/territory_s0_currentbest.py`
- `agents/territory_s1_persistent.py`
- `agents/territory_s2_deadline.py`
- `agents/territory_s3_chain.py`
- `run_territory_lifecycle_ablation.py`
- `experiments/territory_lifecycle_smoke_v3.json`
- `experiments/territory_lifecycle_ablation_quick.json`
- `experiments/territory_lifecycle_hard_screen.json`
- `experiments/territory_lifecycle_heldout.json`
