# Super Replay Backbone research

## Decision

**Promoted research best:** `super_replay_backbone_v1`, the complete RicardoLópez
rank-6 route from episode 92368798 plus exactly the frozen K3 worker-specific
weed transaction repair. The executable source is
`agents/super_replay/super_backbone_v1.py`.

This is a backbone replacement, not a heuristic expansion. It defeated K3 in
all 64 unseen direct games and passed the untouched elite split with positive
P10, 99.940% request fidelity, no runtime/schema failures, no fallback, no
livestock loss, and no meaningful endgame stranding. `submission/main.py` was
not changed and nothing was submitted or uploaded.

## 1. Corpus and reconstruction

The collector took the public Top 100 leaderboard snapshot, selected the
highest-public-score active submission per team, and requested the four newest
completed public appearances per submission.

| Item | Count |
| --- | ---: |
| Leaderboard teams / selected submissions | 100 / 100 |
| Requested appearances before episode deduplication | 400 |
| Unique episode IDs downloaded | 332 |
| Valid unique full replays | 331 |
| Elite appearances in those replays | 583 |
| Unique normalized elite appearances after action deduplication | 454 |
| Identical full-trajectory duplicates | 1 |
| Identical single-agent action duplicates | 129 |
| Rank coverage | 1–100 |
| Invalid or missing replay files | 0 |

Every replay contains 720 states and 719 requested actions per player. The
exact transition engine reconstructed all **331 × 719 = 237,989** state
transitions with **zero unexplained bank mismatches**. The audit separately
records sale revenue, seeds, feed, animals, deeds, hires, final money, and the
public inventory/land/hand/animal/crop states. No malformed episode was used.

Primary machine artifacts are the corpus manifest, financial audit, route
stability, route families, economic waves, phase graph, and action confidence
JSON files under `experiments/`.

## 2. Route stability and families

Among 99 deduplicated submissions with usable appearances:

| Classification | Submissions |
| --- | ---: |
| A — highly fixed | 84 |
| B — fixed with bounded repair | 3 |
| C — phase-fixed / locally adaptive | 10 |
| D — strongly state-dependent | 2 |

The structural distance graph supports three natural families, without forcing
a cluster count:

| Family | Size | Typical economic skeleton | Representative |
| --- | ---: | --- | --- |
| F1 / Victor-like | 93 | deeds at steps 160 and 240; 14 hands; 8 cows + 4 sheep; 12 melon, then 36 strawberry / 56 wheat | aisamhottman, episode 92391343 |
| F2 / early-land, lean labor | 5 | first deed around 148, second around 264; 12 hands; 10 cows + 4 sheep; 20 melon, then 34 strawberry / 37 wheat | MD. Nazmus, episode 92376386 |
| F3 / mixed wool | 1 | deeds around 144 and 220; 13 hands; 9 cows + 9 sheep; stronger wool/wheat weighting | researchstudio.site, episode 92367083 |

Ranks 1 and 2 are the two state-dependent submissions. They are economically
interesting but unsafe raw backbones. The important consensus is the day-6
first deed, day-10-ish second deed, mixed cow/sheep opening, and a coherent
melon → strawberry/wheat wave. Genuine disagreements are 12 versus 14 hands,
8 versus 10 cows, second-deed timing, wool exposure, and premium-product hold
duration.

Ricardo is an A-class route observed in 15 appearances. Its phase stability is
92.9% field / 100% market in the noisy opening, 98.4% field in first expansion,
96.7% in second expansion, 99.5% in midgame, 98.9% late, and 100% field during
liquidation. It buys deeds at days 6 and 10, reaches 14 hands, uses 8 cows and
4 sheep, and peaks at 74 productive tiles.

## 3. Economic waves

Ricardo's source route uses the following capital chain:

1. **Day 0:** one cow + four sheep ($2,400), with wheat sales keeping the
   opening liquid.
2. **Days 5–8:** fertilizer, wheat, and especially wool fund one cow on day 5,
   the $1,000 deed plus two cows on day 6, then two cows on both days 7 and 8.
3. **Day 10:** $9,606 same-day sales, including $7,412 melon, fund the $2,000
   second deed.
4. **Mid/late:** 12 melons transition into 36 strawberries and up to 56 wheat;
   premium holding is short for melon (0.12 day), moderate for milk (0.53),
   strawberry (1.03), and wool (1.80).
5. **Liquidation:** final SELL remains at step 718.

The source replay realized $117,725 revenue: fertilizer 12,296; melon 15,889;
milk 6,014; strawberry 58,830; wheat 19,477; wool 5,219.

An exact eight-game paired fixed-shop attribution against K3 found **+4,001
average final money**. Ricardo earns only +480 more gross revenue but spends
$3,521 less: −$900 animals, −$2,628 feed, −$140 seed, +$147 labor, identical
land spending. Its revenue shift is +$1,389 melon, +$1,037 strawberry, +$302
milk, offset by less wool/fertilizer/wheat. The mechanism is therefore a leaner
livestock/feed capital load plus more valuable crop timing—not extra repair or
unexplained RNG.

## 4. Raw-route Generation 0

Twenty-three complete elite routes and K3 received the same 24-game gate:
both seats, fixed and natural K3, frozen 803/R3/lifecycle agents, three family
medoids, and two reserved elite traces.

| Route | W/L/T | Avg money | Avg advantage | P10 | Fidelity |
| --- | ---: | ---: | ---: | ---: | ---: |
| K3 | 8/12/4 | 94,650 | +10,700 | −8,047 | 99.975% |
| F1 medoid | 14/8/2 | 102,066 | +12,295 | −5,008 | 99.971% |
| F2 medoid | 18/5/1 | 101,210 | **+15,215** | −1,855 | 99.981% |
| F3 medoid | 11/13/0 | 93,560 | +984 | −21,766 | 99.956% |
| Ricardo raw | 18/6/0 | **105,412** | +14,909 | −4,986 | 99.968% |
| Hamed raw | 18/4/2 | 105,566 | +14,568 | −5,530 | 99.969% |

F2 won the cheap mean/tail gate; Ricardo and Hamed established that multiple
stable F1 routes materially beat the older Victor trace. F3 was rejected for a
catastrophic tail.

## 5. Phase graph and rejected recombinations

Safe phase boundaries were opening 0–160, first expansion 160–240, second
expansion 240–336, midgame 336–504, late 504–648, and liquidation 648–719.
Synchronization signatures included money, hands, deeds, animals, crops,
seeds, and worker positions. The graph has 11 parent nodes, 550 evaluated
directed boundaries, and 312 compatible edges at distance ≤8. Eighty
single-tail phase splices were materialized; arbitrary per-action mutation was
never used.

The broad full splice run was intentionally stopped at a preserved 340/1,944
checkpoint after 14 complete candidates; the cheap screen was preserved at
140/648 after 17 complete candidates. The best splice, Nikita opening → Ricardo
tail at step 160, produced exactly Ricardo's results in all later selection
games. No tested substitution beat its raw parent. This is negative evidence:
the compatible F1 routes share the same effective phase structure, while the
economically distinct F2/F3 boundaries usually fail the state-compatibility
gate. Completing hundreds of redundant splices would not be compute-disciplined.

## 6. Architecture selection

Five locked architecture candidates received 36 games each: 20 rank 71–85
elite-trace games plus 16 fresh fixed/natural K3 games, both seats.

| Candidate | W/L/T | Avg money | Avg advantage | P10 | Safety |
| --- | ---: | ---: | ---: | ---: | --- |
| K3 | 5/19/12 | 90,404 | −2,335 | −8,880 | clean |
| F2 medoid | **28/8/0** | **87,829** | **+4,614** | −1,815 | 1 cow lost |
| Ricardo | 25/11/0 | 87,478 | +2,524 | −3,642 | clean |
| Hamed | 27/9/0 | 87,690 | +2,486 | −2,064 | clean |
| Nikita→Ricardo splice | 25/11/0 | 87,478 | +2,524 | −3,642 | clean; identical to Ricardo |

F2 and Ricardo advanced. Hamed was inferior; the splice was redundant.

## 7. Strictly unseen final

Before querying final episode IDs, the finalists were frozen in
`super_replay_unseen_finalists_lock.json`. Then one brand-new episode absent
from all 332 development IDs was downloaded for each rank 86–100 submission.
The final used those 15 opponents plus 16 untouched RNG seeds, fixed and
natural shops, both seats: 94 games per candidate, 282 total.

| Candidate | W/L/T | Avg money | Avg advantage | P10 | P5 | Fidelity | Livestock losses |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| K3 | 15/35/44 | 81,965 | −864 | −5,316 | −6,544 | 99.959% | 0 |
| F2 medoid | 76/18/0 | 84,431 | +4,699 | −544 | −1,243 | 99.953% | **9** |
| **Ricardo / Super Backbone** | **92/2/0** | **88,524** | **+5,668** | **+985** | **+824** | **99.940%** | **0** |

Ricardo versus K3 was **64/0**, +6,027 average advantage, P10 +3,124. Its
fixed-shop subgroup was 32/0 at +5,262; independent natural RNG was 32/0 at
**+6,793**. Against the 15 unseen elite traces it was 28/2, +4,903 average,
P10 +781. The only two losses were one seat each versus ranks 90 and 93; worst
advantage was −2,463, with no catastrophic matchup.

Across all 94 final games it requested 692,686 route action slots; 692,268
(99.940%) matched after actual-hand alignment, 65 bounded weed repairs occurred,
no fallback activated, and there were zero runtime, semantic, livestock, or
meaningful-stranding failures.

F2's mean was positive, but its negative tail and nine animal escapes fail the
explicit livestock/safety gate. It remains a useful alternative economic
family, not the promoted agent.

## 8. Action confidence and executable validation

The 719-entry Ricardo confidence map records source route/submission, support,
within-submission stability, cross-stable support, phase, confidence, and final
experimental validation. All 719 entries are now marked validated; mean
confidence is 0.837 (range 0.257–0.990). Low-confidence entries remain visible
rather than being laundered into false consensus.

`super_backbone_v1.py` was compared to the raw Ricardo finalist for two new
complete games, one per seat: **1,438/1,438 requested actions identical**,
finals 149,353–143,650 and 58,928–53,523, zero runtime/semantic failures, and
zero stranded value.

## 9. Promotion, preserved failures, and next direction

Promotion occurred because the result is architectural and robust: positive
fresh natural RNG, 64–0 direct K3, positive unseen P10/P5, strong elite-transfer
mean, high fidelity, clean seats, and no safety/fallback dependence.

Preserved rejected evidence:

- F3 mixed-wool route: catastrophic P10.
- F2 medoid: strong mean but negative tail and repeated cow losses.
- Hamed route: weaker than Ricardo in selection.
- Nikita→Ricardo splice: no behavioral benefit over raw Ricardo.
- 340/1,944 full-splice and 140/648 cheap-screen checkpoints: intentionally
  stopped without deleting results.
- Interrupted older multiwave search: still preserved at 600/1,536.

The next useful direction is not broad heuristic intelligence. First inspect
the two Ricardo unseen losses and the 0.06% divergence region, then test one
bounded animal-survival transaction only if it preserves the raw route's
positive P10. A second useful branch is a fully compatible F2 economic-wave
transfer, but only after defining a state synchronization that eliminates its
animal-scheduling failure. Do not add generic routing, dynamic SELL reordering,
or planner fallbacks without isolated evidence.
