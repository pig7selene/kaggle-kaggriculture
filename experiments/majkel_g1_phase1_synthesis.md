# Majkel G1 Phase 1 synthesis — what the 09-12 artifacts already proved

Read 2026-09-15. Sources, all produced 2026-09-12 and never read until now:

- `experiments/majkel_56156662_block_router_loo.json` (40 development episodes)
- `experiments/majkel_g1_loo.json` (15 development episodes)
- `experiments/majkel_56156662_branch_tree.json` / `.md` (40 development episodes)

Every rate below was recomputed from those JSON payloads, not transcribed.
**The sealed G1 holdout was not opened**: no file under
`/private/tmp/kaggriculture_majkel_56156662/g1_holdout` was parsed, and the six
sealed episode ids appear in no artifact read or written here. Seal state is
registered in `experiments/majkel_g1_split_lock.json`
(`holdout_actions_read: 0`) and its six hashes were verified intact on
2026-09-15 by `build_majkel_corpus_manifest.py`.

## 1. The tape/block-copying paradigm has a measured ceiling of 28.5%

`block_router_loo.json` records an `oracle_by_block` panel: the best achievable
if, with perfect hindsight, you chose the single best source episode to copy for
each 72-step block. This is an upper bound on *any* routing algorithm, not the
score of one.

| Block | Steps | farmer | hands | market | **exact** |
|---:|---|---:|---:|---:|---:|
| 0 | 0–71 | 99.2% | 98.0% | 98.9% | **94.1%** |
| 1 | 72–143 | 92.0% | 89.7% | 95.7% | **77.7%** |
| 2 | 144–215 | 79.1% | 84.7% | 81.1% | **47.5%** |
| 3 | 216–287 | 86.2% | 85.7% | 72.8% | **35.7%** |
| 4 | 288–359 | 79.0% | 76.4% | 54.9% | **15.1%** |
| 5 | 360–431 | 78.1% | 68.3% | 41.6% | **6.6%** |
| 6 | 432–503 | 60.8% | 59.4% | 37.9% | **2.4%** |
| 7 | 504–575 | 53.7% | 51.5% | 32.0% | **1.6%** |
| 8 | 576–647 | 47.7% | 48.3% | 28.6% | **2.5%** |
| 9 | 648–719 | 51.6% | 45.7% | 33.4% | **1.6%** |
| **all** | 0–719 | | | | **28.5%** (8,200 / 28,760) |

Reconstructing Majkel from Majkel's own 40 episodes reaches 94% in the opening
and under 3% after step 432 — with an oracle.

Realised routing against that ceiling:

| Profile (40 eps, 28,760 steps) | farmer | hands | market | exact |
|---|---:|---:|---:|---:|
| **state_heavy** | 64.6% | 59.6% | 54.5% | **19.6%** |
| balanced | 65.0% | 59.5% | 54.1% | 19.1% |
| balanced_sticky | 65.0% | 59.5% | 54.1% | 18.6% |
| shops_heavy | 63.5% | 58.0% | 53.0% | 17.5% |
| shops_sticky | 63.6% | 58.0% | 53.0% | 17.5% |

Best realised 19.6% against a 28.5% ceiling. **Better routing is worth at most
9 more points; the remaining 71 points are not reachable by routing at all.**

This is the structural verdict on our own architecture, which is a 719-step tape
replayer with a `SHOP_PLANS` lookup and bounded repairs.

## 2. The shop signal is the weakest feature, confirmed twice independently

| Study | Episodes | Setup | Best | Worst |
|---|---:|---|---|---|
| `majkel_g1_loo` | 15 | per-step modular nearest neighbour | **state_heavy 28.1%** | sequence_heavy 23.5% |
| `block_router_loo` | 40 | 72-step block routing | **state_heavy 19.6%** | shops_heavy 17.5% |

Two different setups, different episode counts, same ordering: raising the farm
**tile-state** weight improves every metric; raising the **shop-sequence**
weight degrades every metric. In `g1_loo` the winning profile weights
`tile: 700` and `shop_seq: 80`; the losing one weights `shop_seq: 1500`.

Our entire routing key is the first two shops, and the
`smaller_market_shock_v233h_non_yarn_0911` candidate extended it with 42 more
shop-pair routes. That is optimisation along the axis these two studies
independently rank last.

## 3. What Majkel actually branches on

`branch_tree` found 20 forks across 40 development episodes. Leave-one-out
generalisation is only trustworthy for the first five, where group sizes are
still large:

| Step | Group split | Channel | Observable | Rule | LOO |
|---:|---|---|---|---|---:|
| 21 | 40 → 28/12 | plan | `market_inventory:WHEAT` | threshold **9993.0** | 40/40 |
| 22 | 28 → 19/9 | plan | `own_money@t-1` | threshold 9.5 | 28/28 |
| 25 | 19 → 16/2/1 | plan | `own_hands` | eq | 18/19 |
| 25 | 9 → 4/3/2 | plan+market | `own_hands` | eq | 9/9 |
| 31 | 16 → 13/3 | market | `market_inventory:WHEAT` | threshold **9981.5** | 16/16 |

After step 32 the LOO column decays (12/13 → 10/12 → 8/11 → 5/8 → 2/4): groups
shrink to 4–12 episodes, where a 3/1 split scoring a perfect pair separation is
not evidence. **Treat forks 1–5 as rules and forks 6–20 as overfitting.**

Three observations that matter more than the rules themselves:

1. **The first fork is at step 21, not 144.** Our `SHOP_PLANS` lookup happens at
   step 144; Majkel has already branched on day one.
2. **The thresholds cluster against the market equilibrium.** 9993.0, 9981.5,
   9977.5, 9967.5, 9962.0 — all within 40 units of `I0 = 10000`. He reads how
   far the shared market inventory has been pushed from equilibrium. Our agent
   has no such input; it follows its tape regardless of market state.
3. **He branches on the opponent.** `rival_money@t-1` at step 36 and
   `rival_money` at step 113.

## 4. The G0 hand-slot mismatch was volume, not a representation bug

The G0 holdout report's 17,077 / 39,000 hand-slot mismatches looked alarming
next to 1,564 farmer mismatches. The ratio is mechanical: there are roughly ten
hand slots per step against one farmer action, and the count grows as the farm
does (12,910 slots across block 0, 30,000 across blocks 4–8). As a rate, G0's
56.2% hand-slot correctness sits in the same band as block routing's 48–60% in
the late game. No evidence of a pure encoding artifact; hands are genuinely hard.

## 5. Subsystem errors are near-independent

In `g1_loo`, the product of the three per-subsystem rates tracks the exact-match
rate closely (state_heavy: 0.742 × 0.697 × 0.563 = 0.291 vs 0.281 measured;
local_demand: 0.265 vs 0.257). Exact sits slightly below the product, so the
errors are near-independent with mild positive correlation.

Consequence: **exact-action match is mostly measuring the conjunction.** Any
single subsystem that improves multiplies through the whole. The market channel
is both the weakest (28–38% oracle in the late game) and the one that moves
money, so it has the largest product leverage.

## 6. Consequences for Phase 2

1. **Stop routing tapes after the opening.** The oracle proves there is nothing
   left to recover there; this is not a tuning problem.
2. **Keep the opening as a tape.** Blocks 0–1 are 94% and 78% oracle-copyable.
   This is the part of our architecture that is actually well-founded.
3. **Condition the mid and late game on state, not shops.** The evidenced
   variables are market inventory relative to 10,000, own money, rival money,
   own hands, and per-resource demand.
4. **Target the market channel first**, for the leverage in §5.

This supersedes the sequencing suggested before Phase 1, which proposed
reconstructing shop-conditioned livestock allocation first. That target was
chosen on the assumption that the shop signal carried the branch information;
§2 shows it carries the least.

## 7. Limitations, stated rather than implied

- **Everything above measures imitation fidelity, not score.** Not matching
  Majkel's actions is not the same as playing worse; a different policy of equal
  strength would score 0% here. These numbers bound copying, not winning.
- **The market is shared.** `market_inventory` is global, so an opponent's
  selling moves our prices directly. This is why Majkel reads it — and it means
  any money comparison across different opponent pools is confounded.
- **The late-game oracle collapse may partly reflect divergence, not policy
  complexity.** By step 432 two episodes' boards differ enough that no copied
  action is legal, which depresses match rates independently of how simple the
  underlying rule might be.
- Forks 6–20 in `branch_tree` are not usable; see §3.

## 8. Not done here

No candidate was modified. No Kaggle submission was made. The sealed G1 holdout
was not opened, and no new holdout was declared or consumed.
