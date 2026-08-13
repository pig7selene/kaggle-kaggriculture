# Large-scale routing and replay-economy report

## Executive result

The replay schedule failed in the old engine primarily because the global,
stateless scheduler stopped converting labor into useful work at 50 tiles and
became movement-dominated at 75 tiles. A persistent-territory router reverses
that failure. With the same replay economy, the controlled R2/R3 ablation
increased average money from 44,164 to 72,352 and changed the result from
19/23/0 to 41/1/0.

The strongest held-out candidate is
`agents/router_replay_hands12.py`: three quadrants, a replay-derived cow/crop
schedule, and a twelve-hand ceiling. On 256 fresh games it went 256/0/0,
averaged 78,750 coins, and beat the frozen C8 best 32/0/0 by 23,402 coins.

## 1. Resumed state and artifacts

The interrupted `analyze_worker_routing.py` run had already completed. It was
not repeated. Its complete outputs were:

- `experiments/top_player_worker_routing.json`
- `experiments/top_player_worker_routing.md`

The old-router audit had also completed:

- `experiments/router_execution_audit.json`
- `experiments/router_execution_audit.md`

The last unfinished step was the newly created neighborhood script. It was
compiled and run once, producing `experiments/router_neighborhood.json`.

## 2. Where the old router loses efficiency

The table compares the old replay/full scheduler with the 35 selected public
top-player appearances. “Water miss” is the critical miss rate, not all
not-watered checks. Percentage-point deltas are old minus public.

| Capacity | Productive | Movement | Move/productive | Tile utilization | Critical water miss | Uncared | Fertilizer left |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 25 | 22.4% vs 35.1% (-12.7pp) | 62.1% vs 32.9% (+29.2pp) | 2.78 vs 0.94 (+196%) | 59.0% vs 71.3% (-12.3pp) | 1.7% vs 0.1% | 61.8% vs 0.0% | 21.9% vs 0.0% |
| 50 | 28.4% vs 41.3% (-12.9pp) | 67.7% vs 39.2% (+28.5pp) | 2.39 vs 0.95 (+152%) | 36.3% vs 84.2% (-47.9pp) | 16.4% vs 0.7% | 0.0% vs 0.0% | 0.0% vs 0.0% |
| 75 | 21.8% vs 38.6% (-16.8pp) | 74.0% vs 44.4% (+29.6pp) | 3.39 vs 1.15 (+195%) | 50.5% vs 92.8% (-42.3pp) | 6.5% vs 0.3% | 71.3% vs 9.8% | 22.7% vs 2.2% |

The scheduler therefore begins to fail materially at 50 tiles. At 75 tiles it
uses nearly three quarters of all worker actions for movement, needs 3.39 moves
per useful action, delays 728 harvest opportunities in the six-game audit,
and leaves 34.94 unlocked tiles empty despite available capital. Exact
same-tile conflicts were zero, so duplicate targeting was not the primary
failure. The primary mechanism was task churn: every unit repeatedly searched a
global task list, crossed quadrants for the currently highest-ranked task, and
made separate trips for feed, care, fertilizer, and animal harvest.

Land activation exposes the same failure. Public agents made new land
productive after a median four turns (range 2–13). The old replay land/labor
port took a median 12 turns (range 12–117), and the full replay port took 28.5
turns (range 8–64).

## 3. Top-player worker organization

Across 25 unique public episodes and 35 selected appearances, worker-day
territory purity had a median of 100%. The stable pattern was:

| Worker indices | Dominant responsibility | Stable region |
| --- | --- | --- |
| 0, 1, 4, 5 | Animal service | Northern animal zones near the shed |
| 2, 6, 10, 14 | Crop work | SW |
| 3, 7, 9, 13 | Crop work | Primarily NE |
| 8, 11, 12 | Crop work | Primarily NW |

Workers usually remained in their zone for the day. Animal workers repeatedly
batched local feed/care/collect/harvest work; crop workers serviced nearby
cohorts. Quadrant crossings were generally well below one per worker-day,
except for a few NE workers whose shed spawn required a boundary crossing.
This organization—not an exact path—is the scalable principle.

## 4. New scalable router

`agents/large_scale_router.py` implements:

- persistent index-based crop territories and stable animal specialists;
- local animal chunks instead of every specialist scanning every animal;
- survival/decay urgency before planting and lower-value maintenance;
- same-tile animal batching before another trip;
- task and resource reservations to prevent duplicate targets and wheat claims;
- local nearest-work selection inside a worker's territory;
- carried-animal placement recovery and crop-worker wheat handoff at the shed;
- endgame animal harvesting and inventory return.

The selected worker profile closely reproduces the population structure:
indices 0/1/4/5 are animal-heavy; 2/6/10 are SW crop workers; 3/7/9 are NE crop
workers; and 8/11/12 are NW crop workers. Median territory purity is 100%.

## 5. Router-only causal ablation

Seeds 12820–12822, seven high-economy opponents, and both seats produced 42
games per candidate. R0/R1 share the frozen C8 economy. R2/R3 share the same
replay economy.

| Candidate | W/L/T | Avg money | Avg advantage | Crop revenue | Animal revenue | Peak productive |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| R0 old router + C8 economy | 38/2/2 | 64,415 | +29,844 | 35,999 | 40,633 | 31.98 |
| R1 new router + C8 economy | 35/7/0 | 60,357 | +24,065 | 33,917 | 36,971 | 32.00 |
| R2 old router + replay economy | 19/23/0 | 44,164 | +2,799 | 28,623 | 39,975 | 48.50 |
| **R3 new router + replay economy** | **41/1/0** | **72,352** | **+35,801** | **45,187** | **48,235** | **68.43** |

R1 regresses at the frozen two-quadrant scale, so the new router is not a
universal drop-in improvement. Its specialization overhead is worthwhile only
when enough local work exists. The critical result is R2 versus R3 at 75 tiles:

| 75-tile metric | R2 old | R3 new | Change |
| --- | ---: | ---: | ---: |
| Productive-action ratio | 21.6% | 30.2% | +9.6pp |
| Movement ratio | 74.3% | 59.1% | -15.2pp |
| Moves/productive action | 3.44 | 1.96 | -43.1% |
| Productive-tile utilization | 49.5% | 75.8% | +26.3pp |
| Critical watering miss | 7.5% | 2.0% | -5.5pp |
| Animals uncared | 75.5% | 17.1% | -58.4pp |

Later same-tile batching and feed handoff refinements reduce the selected
router's 75-tile uncared rate further to 5.2% and fertilizer-left rate to 5.9%.

## 6. Refined router versus public execution

The selected final agent jumps directly from 25 to 75 unlocked tiles when cash
allows both queued deeds on day 11, so it has no meaningful 50-tile phase. The
50-tile row below uses R1 with the same router and frozen two-quadrant economy;
it is a router diagnostic, not a phase of the final agent.

| Capacity | Source | Productive | Movement | PASS | Move/productive | Tile utilization | Critical water miss |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 25 | selected router | 23.7% | 52.4% | 19.7% | 2.21 | 59.7% | 0.0% |
| 25 | public population | 35.1% | 32.9% | 28.6% | 0.94 | 71.3% | 0.1% |
| 50 | new router / C8 economy | 22.0% | 46.6% | 29.5% | 2.12 | 58.9% | 0.1% |
| 50 | public population | 41.3% | 39.2% | 16.1% | 0.95 | 84.2% | 0.7% |
| 75 | selected router | 32.9% | 53.7% | 11.4% | 1.63 | 75.1% | 2.2% |
| 75 | public population | 38.6% | 44.4% | 13.1% | 1.15 | 92.8% | 0.3% |

The router now scales economically, but it has not matched public execution.
At 75 tiles it still spends 9.3pp more actions moving, needs 42% more movement
per productive action, and uses 17.7pp less productive capacity.

## 7. Mixed livestock economics

The controlled screen used seeds 12950–12951, five opponents, and both seats:
20 games per candidate.

| Candidate | W/L/T | Avg money | Avg advantage | Animal net after feed/animal/service costs | Direct versus R3 |
| --- | ---: | ---: | ---: | ---: | --- |
| Routed cow-only, 12 base plots | 17/1/2 | 84,469 | +28,841 | 53,025 | 1/1/2 mirror |
| Routed cow-only, 10 base plots | 16/4/0 | 66,696 | +14,575 | 31,781 | 0/4, -5,454 |
| 1 cow + 4 sheep opening, 10 plots | 14/6/0 | 69,284 | +8,888 | 48,246 | 0/4, -28,239 |
| Sheep-only | 9/11/0 | 51,531 | -10,292 | lower | lost |
| Mixed throughout | 6/14/0 | 56,587 | negative robust effect | lower | lost |
| Mixed opening, six animal specialists | 3/17/0 | 53,641 | negative | lower | lost |

Against the same ten-plot crop base, the sheep opening adds 2,588 average
money (+3.9%) and substantially improves animal net cash flow. Sheep therefore
have real local economic value. They do not improve the complete routed agent:
the mixed candidate loses crop throughput, suffers transient feed/service
pressure and replacement spending, and loses every direct game to the
12-plot cow-only R3. Six specialists over-reserve labor and makes this worse.
The robust choice for this architecture remains cow-only.

## 8. Small replay-economy neighborhood

Seeds 13000–13001, seven opponents, both seats: 28 games per candidate.

| Candidate | W/L/T | Avg money | Avg advantage | Direct vs frozen C8 | Actual land use |
| --- | ---: | ---: | ---: | ---: | --- |
| **9 cows, 12 hands** | **27/1/0** | **88,368** | **+40,880** | **4/0, +32,428** | two deeds on d11 |
| 9 cows, 14 hands | 26/2/0 | 88,192 | +40,083 | 4/0, +32,337 | two deeds on d11 |
| 8 cows, 14 hands | 28/0/0 | 87,832 | +39,764 | 4/0, +29,630 | two deeds on d11 |
| One expansion only | 27/1/0 | 80,003 | +32,908 | 4/0, +21,820 | one deed on d11 |
| Land request days 5/9 | 24/4/0 | 78,943 | +32,610 | 4/0, +24,833 | d5 and d11 |
| Mixed opening | 22/6/0 | 72,842 | +15,955 | 4/0, +13,321 | d11 and later |

The economic policy requests land around days 6 and 10, but its realized cash
flow queues both successful purchases on day 11. Each becomes productive in
1–3 turns (median 1.5–2). Forcing the first deed on day 5 consumes compounding
capital and loses 9,249 coins versus the 9-cow control. Stopping at two total
quadrants loses 8,189 coins versus that same control. Thus three quadrants are
optimal in the tested routed architecture, but the replay family's exact d6/d10
cash timing is not yet reproduced.

The twelve-hand ceiling saves about 1,686 labor coins in the search sample
without reducing peak productive capacity materially. Fourteen hands are a
public-meta observation, not an optimum for this local router.

## 9. Fresh high-scale validation

Seeds 13100–13115 were held out from all preceding work. Eight opponents cover
the frozen best, old and mixed replay agents, early land, land/high labor,
early cows, high-labor proxy, and livestock/crop proxy. Both seats give 256
games per candidate and 1,024 total games. Every full game completed and every
candidate action passed semantic validation.

| Candidate | W/L/T | Avg money | Avg advantage | P10 seed advantage | Direct vs C8 | Quadrants | Peak hands | Peak productive | Crop revenue | Animal revenue |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **9 cows, 12 hands** | **256/0/0** | **78,750** | **+37,280** | **+31,474** | **32/0, +23,402** | **3.0** | **12** | **67.13** | **46,644** | **52,187** |
| 8 cows, 14 hands | 256/0/0 | 77,793 | +36,339 | +31,218 | 32/0, +22,525 | 3.0 | 14 | 67.57 | 47,322 | 51,404 |
| 9 cows, 14 hands | 256/0/0 | 77,139 | +35,800 | +30,459 | 32/0, +22,172 | 3.0 | 14 | 68.38 | 46,841 | 51,901 |
| Frozen C8 | 214/34/8 | 62,750 | +18,795 | +16,389 | 12/12/8 mirror | 2.0 | 8 | 31.93 | 35,737 | 39,281 |

The selected candidate's weakest matchup is `mixed_replay_open`, but it still
wins 32/0 with +18,093 average advantage and +10,852 matchup P10. It wins
32/0 against every opponent. There are zero invalid actions, zero observed cow
losses, and at most three final units left on animal tiles; no shed/inventory
overflow failure occurred.

Relative to the frozen C8 on the identical league, the winner gains 15,999.9
average coins, or 25.5%. It exceeds both stated promotion preferences: more
than 10% average-money gain and more than 5,000 direct advantage.

## 10. Remaining gap versus public replay economics

The 35 public appearances averaged 81,666 final coins and 111,085 total sale
revenue. The selected local candidate averages 78,750 final coins and 98,831
tracked crop/animal sale revenue. Those figures come from different opponent
populations and cannot be treated as a direct rating estimate, but they locate
the remaining gap:

- peak productive tiles are 67.1 locally versus roughly 70–75 publicly;
- 75-tile utilization is 75.1% versus 92.8%;
- movement is 53.7% versus 44.4%;
- critical watering misses are 2.2% versus 0.3%;
- 5.1% of animal-day checks are unfed and 5.2% uncared at 75-tile scale;
- public land arrives on d6/d10, while our cash-limited deeds both land on d11;
- the robust local policy still lacks the public wool cash bridge;
- crop revenue is the clearest remaining revenue deficit, consistent with lower
  occupancy and less efficient strawberry/wheat service.

The selected final money is 2,916 (3.6%) below the public replay mean, while
tracked sale revenue is about 12,254 (11.0%) lower. This is encouraging, not
proof of leaderboard equivalence, because market prices depend on the opponent.

## 11. Decision

`agents/router_replay_hands12.py` is the new strongest local agent. It is worth
a new Kaggle submission because the gain is large, survives 256 fresh games,
beats the frozen best directly, and has no catastrophic matchup in the tested
large-economy league.

It is not packaged in this milestone: the agent intentionally uses repository
helpers, and `submission/main.py` remains byte-for-byte unchanged. A separate
packaging step should make it standalone, repeat semantic/equivalence smoke
checks, and explicitly decide whether to eliminate the final three animal-tile
yield units before upload.

