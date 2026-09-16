# Route generation (tier 2): design, pre-registered

Written 2026-09-16 before any generated route was built or evaluated. The
target is the ~250 points between our plateau (56258686 at 2721) and the
leaderboard's fourth-to-fifteenth band (2969-3034). Everything cheaper has been
tried and measured this week: the base change was worth about +100, enabling
two of V43's disabled layers about +100, and re-assigning V43's existing routes
to shop pairs approximately zero (`route_remap_holdout.md`). What remains is
producing routes V43 does not have.

## Hard constraints, all measured

1. **A tape is a trajectory, not a policy.** Transplanting Majkel's recorded
   routes into V43's chassis lost by -54,290 mean margin on the pairs where it
   changed anything (`v43_majkel_hybrid_negative_result.md`). A generated route
   must be *produced by a run* of something that saw the real state.
2. **Steps 0-143 are fixed.** All 41 V43 routes share route 0's first 144 steps
   exactly; the router only switches at 144. A new route's prefix must be route
   0's, so generation is of the tail only, from the state route 0 leaves.
3. **Steps 648-718 belong to route 2.** V43's router hands every route to route
   2 at 648. The forced-route harness reproduces this. A generated route is
   therefore judged on 144-647 unless the handover is also changed, which is a
   separate experiment.
4. **Route count is memory-bounded.** 74 routes broke a four-worker pool and a
   two-worker pool. Budget: replace or add at most a handful of routes.
5. **In-sample selection lies.** The remap pilot's largest gain (+4,700) was
   -4,806 on unseen seeds. Every generated route is selected on one seed set and
   confirmed on a disjoint one before it counts; `seed_first_shops_manifest.json`
   has at least two seeds for every one of the 64 pairs.

## What V43's routes actually are (probe C)

Routes 105 (the 21-pair workhorse), 124 (best on average, +398 over 105 across
21 pairs, held-out positive on 4/4), 110 and 0 were compared as tapes:

| | 105 | 124 | 110 | 0 |
| --- | --- | --- | --- | --- |
| BUY_LAND steps | 150, 265 | 150, 265 | 150, 265 | 150, 265 |
| Animals bought | 8 cow, 6 sheep, 3 goose | same | 8 cow, 4 sheep, 5 goose | same as 105 |
| Seeds bought | W163 S33 C31 M12 | identical | identical | identical |
| First premium sell | S382 M249 Mk196 W149 | identical | identical | identical |
| Max hands | 11 | 11 | 12 | 11 |
| SELL orders (total) | 393 | 446 | 312 | 354 |

**V43's 41 routes are one farm plan with sell-schedule variants.** Same land
timing, same seed purchases to the unit, same first-sale steps, same animal
mix; they differ in how often and how much they sell. Route 124 is "105 that
sells more". The 12,000-17,000 spread between routes on a pair is entirely
sell scheduling. Farm-layout similarity confirms it (probe D): across all 27
non-Yarn routes on one seed, tiles agree 96.9% at steps 288, 432, 576 and 647;
105 and 124 agree 100% at every boundary.

Consequence: **the farm-strategy axis is untouched by V43's route bank.** Every
route expands its second quadrant at step 265. Majkel, measured over 40
episodes, expands at 221 (32/40 episodes at exactly 149/221). Same tiles, same
hands, and he ends with 15% more money per tile than our old lineage did.

## The lever is cash-gated (probe D)

Route 105's cash: step 150 $2,195 -> 200 $1,674 -> **221 $880** -> 240 $2,136
-> **265 $17,903**. Across all 27 routes at step 221: min $416, median $880,
max $1,082. The second quadrant costs $2,000.

**V43 cannot buy at 221.** It has less than half the price. The $17,903 at 265
is melon revenue: first melon sale at step 249, income settles at the day
boundary (264), land bought the next step. Majkel's earlier expansion is not a
timing knob; it is an earlier melon economy, or a different one. Moving one
action does not reproduce it.

The nearest feasible step is **241**: $2,136 on hand, and a shift of exactly 24
steps keeps day alignment (hires at hour 0, drops at hour 23), which a shift of
25 or 44 would not. It leaves about $136 for the new quadrant's seeds, so the
plan may starve there. That is precisely what the first experiment measures.

## Generator options, ranked by cost

| | Option | Cost | Status |
| --- | --- | --- | --- |
| A | Day-aligned re-timing of route 105's second expansion, 265 -> 241, re-simulated through V43's chassis | ~1 hour | **Experiment 1 below** |
| B | Route 124 as default for the 21 pairs (remap leftover) | one-line change | rides along with any submission; not worth one alone |
| C | Graft Terminal D's search-based terminal planner (`submission/terminal_planner.py`, steps 712-718, state-driven) in place of route 2's endgame | ~half day | V43's terminal_liquidation never fires because routes already sell out; value unproven, keep as option |
| D | Repo's live policy `replay_meta_common.make_replay_agent` (knobbed: land days, hands, animal/crop schedules) as tail generator, spliced after route 0's prefix | weeks | it scores 37k against V43's 163k standalone; would need to reach frontier play first |
| E | `super_replay_v4` knob modules | - | ruled out: their backbone is a tape (JALKARNA route), not a policy |

## Experiment 1: killed at pre-check, not run

The plan was a day-aligned shift of route 105's steps 265..647 to 241..623.
Reading the tape around the expansion shows why that cannot work:

- **Step 265 is the expansion day's first hour and spends everything at once:**
  `HIRE x5, BUY_LAND, BUY_ANIMAL GOOSE, BUY_PRODUCT FERTILIZER, BUY_SEED
  STRAWBERRY x2`, then continuous wheat-feed and seed purchases through 288 and
  nine more hires at 288. It is paid for by the $17,903 that lands at 264.
- **Steps 241..264 are the funding day itself:** `SELL MELON` 6/24/12/6/6/6/12
  across 249..264 plus milk sales. Shifting the tail back 24 steps *overwrites
  this day*. The melons are never sold, the $2,000 buy at 241 leaves $136, and
  the five hires, the goose and every seed purchase that follows fail for lack
  of cash. The new quadrant is bought and never planted.
- **Shifting only the BUY_LAND order** (leaving the funding day intact) buys the
  land 24 steps early but nothing plants it early: the tape's quadrant-3
  planting is a sequence of hand movements interleaved with everything else the
  hands do, and it cannot be isolated without a farm model. That variant tests
  only whether paying $2,000 a day earlier costs anything, which is a null.

The funding event and the expansion are one day apart *by construction*: melons
sold on day 10, cash settles at the day boundary, land bought on day 11. Moving
the expansion means moving the melon economy, and melons ripen when they were
planted -- in the fixed 0-143 prefix. There is no tape surgery that reproduces
Majkel's 221. Option A is dead by inspection, which is cheaper than by running.

## Revised conclusion

The probes settle what tier 2 is:

- V43's route bank varies only sell scheduling; its farm plan is fixed, and its
  one measurable gap to the frontier (second quadrant at 265 vs Majkel's 221) is
  gated by an early economy V43 does not have ($880 at 221 vs $2,000 needed).
- No tape-level operation closes that gap. Only a generator that re-plans steps
  144-265 -- earlier melon revenue or another funding source, then a planting
  plan for quadrant 3 -- can. That is option D. Its starting policy scores 37k
  against V43's 163k standalone, so the honest cost is weeks, and the narrowed
  target is "reach $2,000 by ~221 from V43's step-144 state with a viable
  quadrant-3 plan", not general play.

Cheap items that remain, each already has a harness:

- **B**: route 124 as default on the 21 non-Yarn pairs (+398 in-sample average,
  positive on 4/4 held-out pairs at +296..+622). One-line remap, a few points,
  rides along with any submission.
- **Yarn-side probe**: route 0 serves 49 of 64 Yarn pairs and was never
  measured. The non-Yarn result (author's choice ranks top-5) makes the prior
  low, but it is the last place a coarse assignment could hide anything, and it
  is the remap pilot rerun on the 12 Yarn routes -- about an hour. Kill
  criterion fixed now: if route 0 ranks top-5 on the probed pairs, close it.
- **C** stays an option with an unproven premise.

## Not doing

No new policy is written on this evidence alone; option D is a separate,
deliberate decision with a weeks-scale budget. No route is submitted on
selection-seed evidence. The sealed G1 holdout is not involved anywhere in this
tier. Nothing here touches 56258686.

## Not doing

No new policy is written before Experiment 1 reports. No route is submitted on
selection-seed evidence. The sealed G1 holdout is not involved anywhere in this
tier. Nothing here touches 56258686.
