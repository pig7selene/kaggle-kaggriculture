# Day 10–20 crop-lifecycle throughput

## Decision

`agents/lifecycle_lc_combined.py` is the new current-best source agent. It keeps
the public opening, market policy, livestock, land schedule, labor caps, and
opponent-blind economics unchanged. Only two post-day-10 field-scheduling
behaviors differ:

1. harvest an ongoing strawberry crop whenever held yield is available instead
   of waiting for the end of its production sequence;
2. when a worker has just emptied a target crop tile, replant it in place while
   there is still enough time to protect the new crop.

`submission/main.py` was not modified or submitted. Its SHA-256 remains
`3196b73fc2f46e25284b773136b530e2aacbaad2ba8a9dffdfce66472fe2a0fb`.

## Frozen scope and comparison method

- Frozen baseline: `agents/opening_public_front_cow8_day6.py`, SHA-256
  `3ede0041921010b0136abb538395faa5951e9af1fb9b76be41467246885da6a8`.
- New source: `agents/lifecycle_lc_combined.py`, SHA-256
  `db12d32912843e012c3dfd7e84c2c384ce998694bf02b98fc7e1fe9189c17e78`.
- The candidate and baseline were action-identical for all 263 agent calls in a
  day-0-through-day-10 equivalence game.
- The four real-loss reconstructions used the original replay action traces for
  JayveerSingh6 (episode 92008833), Lucas Ferreira (92009080), Pedro Rezende
  Gomes (92010768), and alexander kern (92011750), from both seats.
- Their recorded town-shop schedules were forced into every counterfactual.
  Fresh games used a separately seeded common shop schedule. This prevents farm
  occupancy from changing the future demand path through weed/shop RNG coupling.

## Why T2 appeared to help Lucas/Alexander and hurt Jayveer/Pedro

It did not physically have that matchup-specific effect. T2 improved crop
execution against all four opponents once the demand path was held fixed. The
mixed result in the earlier experiment came from an environment RNG coupling:
weed spawning consumes one random draw for every empty unlocked tile, then the
same daily generator chooses a new town shop. T2 changed empty-tile counts, so
the shop schedule first diverged on day 12 even with the same game seed.

| Opponent | First shop divergence | Uncontrolled T2 own-money delta | Uncontrolled opponent delta | Uncontrolled advantage delta |
| --- | --- | ---: | ---: | ---: |
| Jayveer | Ice Cream Shop → Yarn Store, day 12 | -10,129 | -1,235 | -8,894 |
| Lucas | Pizza Shop → Farmers Market, day 12 | -25,783 | -32,890 | +7,107 |
| Pedro | Pizza Shop → Yarn Store, day 12 | -2,559 | +4,248 | -6,807 |
| Alexander | Pet Cafe → Bakery in the original seat, day 12 | +12,178 | +5,516 | +6,662 |

The Lucas result is especially diagnostic: T2's own final money fell by 25.8k,
but the traced opponent fell by 32.9k, creating a misleading relative win. With
the recorded shops fixed, T2 improved average advantage against every matchup:

| Opponent | Baseline advantage | Fixed-shop T2 advantage | Delta | Crop-harvest delta | Crop-revenue delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| Jayveer | -11,736 | -8,189 | +3,547 | +8.0 | +641 |
| Lucas | -2,375 | -1,460 | +915 | +7.0 | +252 |
| Pedro | -8,551 | -7,794 | +757 | +5.0 | +456 |
| Alexander | -13,236 | -10,696 | +2,540 | +4.5 | +197 |

T2 therefore solved a real deployment delay, but only added 4–8 harvest actions
and 197–641 coins of day-10–20 crop revenue per matchup. That was too small to
close the real crop-output gap. Lucas/Alexander versus Jayveer/Pedro was a shop
schedule artifact, not evidence of a non-transitive field scheduler.

## Controlled scheduler ablations

Every row below is the eight-game fixed-shop real-loss screen. Economic policy
and the day-0–10 opening were identical.

| Candidate | Change | W/L/T | Avg advantage | Crop harvests | Crop revenue | Critical miss | Harvest delay | Replant delay |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L0 | Frozen current best | 0/8/0 | -8,975 | 29.5 | 8,458 | 2.51% | 21.0 | 57.0 |
| T2 | Replacement-plant deployment | 0/8/0 | -7,035 | 35.6 | 8,845 | 1.24% | 20.9 | 24.1 |
| L1 | Skip safe non-bonus watering | 0/8/0 | -9,852 | 32.6 | 8,672 | 1.60% | 23.3 | 31.7 |
| L1b | Cross-territory deadline rescue | 0/8/0 | -20,953 | 18.2 | 8,181 | 4.60% | 32.8 | 79.4 |
| **L2** | **Harvest ongoing yield when ready** | **3/5/0** | **-1,801** | **81.1** | **13,915** | 2.76% | **11.2** | 59.2 |
| L3 | Safe stationary replant chain | 0/8/0 | -6,921 | 33.8 | 8,753 | 1.54% | 20.8 | **28.0** |
| L4 | Plant admission control | 0/8/0 | -14,344 | 25.8 | 8,336 | **0.93%** | 22.6 | 75.1 |
| L5 | Dynamic workload territories | 0/8/0 | -28,646 | 16.2 | 7,117 | 4.43% | 27.8 | 92.9 |
| L6 | Oldest cohort before distance | 0/8/0 | -10,530 | 29.0 | 8,496 | 2.72% | 21.7 | 57.5 |
| **LC** | **L2 + L3** | **4/4/0** | **+323** | **83.6** | **13,907** | **1.70%** | **12.4** | **27.9** |
| LCD | LC + L1 | 4/4/0 | -431 | 78.2 | 12,672 | 1.32% | 15.3 | 23.2 |

The two watering-focused failures are informative. Admission control reached a
sub-1% critical-miss rate by planting too little and completed fewer cycles.
Cross-territory rescue made distant workers chase deadlines and created severe
movement thrash. Persistent territories should remain; low misses cannot be
purchased by starving harvest/replant work.

## What the successful scheduler changes

The baseline waited until a strawberry cohort's final/peak age even though an
ongoing plant already held sellable yield at earlier production intervals. That
left premium output on the tile for many turns. L2 turns each held strawberry
yield into an immediate harvest task. L3 then removes the stationary gap after a
one-time harvest: if the same target is empty and seed is available, the worker
replants without routing away and back.

Held-out day-10–20 lifecycle metrics show that this is completed-cycle
throughput, not occupancy or cheap-crop action inflation:

| Metric | Frozen best | LC | Change |
| --- | ---: | ---: | ---: |
| Crop harvest actions | 29.87 | 81.01 | +51.14 (+171%) |
| Strawberry harvest actions | 1.98 | 50.90 | +48.92 |
| Wheat harvest actions | 21.39 | 22.89 | +1.50 |
| Melon harvest actions | 5.13 | 5.11 | unchanged |
| Crop harvest units | 100.30 | 148.92 | +48.62 |
| Day-10–20 crop revenue | 8,564.8 | 14,409.2 | +5,844.4 (+68%) |
| Critical watering misses | 2.31% | 1.50% | -0.81 points (-35%) |
| Harvest delay | 20.74 turns | 12.02 turns | -8.72 turns |
| Replant delay | 59.51 turns | 27.93 turns | -31.58 turns |
| Movement per crop cycle | 39.64 | 13.94 | -65% |
| Lifecycle debt | 5,324 tile-hours | 3,632 tile-hours | -32% |
| Productive crop tile-hours | 12,485 | 13,746 | +10% |
| Completed cycles per worker-day | 0.241 | 0.654 | +172% |

On the exact reconstructed set, all successful harvest actions (crop plus
animal) rise from 69.0 to 122.6 during days 10–20. This reaches the requested
100+ direction and moves substantially toward the public-agent range near 147.
The increase is recurring strawberry output, not spammed wheat/carrot actions.

Raw end-of-day unwatered observations rise because a strawberry can be harvested
instead of watered on its production turn. The economically relevant hard
deadline metric—plants already carrying one miss—falls by 35%. The remaining
1.5% critical miss rate is still above the sub-1% target and is a genuine
remaining weakness.

## Reconstructed real-loss results

| Opponent | Baseline W/L/T | LC W/L/T | Baseline advantage | LC advantage | Harvests | Crop revenue | Critical miss |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Jayveer | 0/2/0 | 0/2/0 | -11,736 | -9,280 | 89.0 | 14,256 | 1.67% |
| Lucas | 0/2/0 | 2/0/0 | -2,375 | +11,281 | 83.0 | 12,759 | 1.35% |
| Pedro | 0/2/0 | 0/2/0 | -8,551 | -4,486 | 80.0 | 14,218 | 2.36% |
| Alexander | 0/2/0 | 2/0/0 | -13,236 | +3,778 | 82.5 | 14,395 | 1.42% |

The candidate fixes Lucas and Alexander and materially narrows Jayveer and
Pedro. Pedro is the one reconstruction where the critical miss rate rises, so
that trace remains the most important scheduler-specific weakness. Jayveer is
the worst final-money matchup at -9,280 average; neither is a newly created
failure, and both improve over the frozen baseline.

## Fresh held-out confirmation

Eight unseen seeds were run from both seats against the frozen best and 11 hard
adversarial/replay-derived opponents, followed by the eight fixed real-loss
counterfactuals: 200 full games per finalist.

| Candidate | W/L/T | Avg money | Avg advantage | Paired P10 | Advantage SD | Crop harvests | Crop revenue | Critical miss |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Frozen best | 184/16/0 | 88,209 | +39,555 | 0 | 28,764 | 29.87 | 8,565 | 2.31% |
| **LC** | **196/4/0** | **89,211** | **+42,294** | **+9,753** | **27,803** | **81.01** | **14,409** | **1.50%** |

- Directly versus the frozen best: **16/0/0**, average advantage **+5,801**,
  paired P10 **+3,133**.
- Fresh hard league: **176/0/0**, average advantage **+47,519**; every matchup
  remained positive.
- Reconstructed losses: **4/4/0**, average advantage **+323**, versus 0/8/0 and
  -8,975 for the baseline.
- Runtime failures: 0. Semantic action failures: 0. Observed invalid field
  actions on days 10–20: 0. Maximum end inventory: 3 sellable units (baseline 4).
- The original source agent remains behaviorally identical to the unchanged
  packaged submission over a separate 719-action smoke comparison, confirming
  that the opt-in router hooks did not alter the frozen strategy.

## Promotion and remaining weaknesses

LC is promoted because it materially increases profitable completed cycles,
wins every fresh direct game against the frozen best, improves the exact replay
set from 0–8 to 4–4, has positive held-out P10, reduces variance, and introduces
no runtime, semantic, or fresh-pool catastrophic matchup.

The evidence is strong enough to justify a separate Kaggle packaging/submission
milestone. It is not evidence that the midgame is solved:

1. total reconstructed harvests are 122.6, still below the public reference near
   147;
2. critical misses remain 1.5% overall and 2.36% in the Pedro trace;
3. Jayveer and Pedro remain systematic exact-trace losses;
4. early crop composition is frozen, so the previously observed day-10 melon
   deficit remains outside this experiment;
5. up to three sellable units can remain at the end and should be checked during
   any later standalone packaging step.

No Kaggle submission was prepared or sent in this phase.
