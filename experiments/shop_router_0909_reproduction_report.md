# Shop Router 0909 — recent high-score reproduction report

## Recent scan first

**Search timestamp:** 2026-09-09T15:22:42+08:00  
**72-hour cutoff:** 2026-09-06T15:22:42+08:00  
**Coverage:** approximately 180 public competition-Code entries across nine listing pages.  
**Recent strategies found:** 27 agent/strategy-like NEW_72H entries (42 total new notebooks; 13 strategy-like entries exposed a live listing score).

Top recent candidates, using the live listing score first and showing an exact version-linked score where available:

1. **Shop Router 0909** — 3h18m old — live 2847.4; exact v1 link 2839.5.
2. **Kaggriculture: 93.8% Win Rate Public State Router** — 45h06m old — live 2645.0; exact link not re-established in this scan.
3. **Kaggriculture_reactive_router** — 12h38m old — live 2641.7; exact v1 link 2733.6.
4. **Shop Router 0908** — 23h20m old — live/exact historical link 2611.5.

No credible complete NEW_72H public agent with a verifiable 2900+ score-version pair was found. The old notebook titled “Kaggriculture | 2900+” was not eligible: it was first published in August, its current live score was 1145.1, and its recent v15 had no matching high-score submission.

**Selected target:** Yusuke Hayashi (`yhay81`), *Shop Router 0909*, public v1/run 348430185.  
**Why:** it was the highest-scoring complete reproducible NEW_72H agent, exposed every runtime file, had Apache-2.0 licensing, and v1 had an exact submission-source link at 2839.5. Its quick CurrentBest benchmark exceeded the +3k stop-search threshold, so the task moved immediately to deep validation.

## Exact source and version result

The notebook has three accessible versions, all published on 2026-09-09. The inference `main.py` is identical in v1/v2/v3. V1 and v2 embed the identical 5,099,830-byte `actions.json`; v3 merely repackages that identical JSON together with the same license. V1 is the conservative reproduction target because submission 56113158 explicitly points to source run 348430185 and records **2839.5**. The current notebook listing showed **2847.4** at scan time, but that live value is not proof that v3 itself produced 2847.4.

- Public/local `main.py` SHA-256: `d6d74997dc5b483db63d8e39cafa1afeec0f366824e75107e109123f111e866b`
- Public/local `actions.json` SHA-256: `17d503f2fd20d59f9c0f14024d1e74a8add8bb9b5561d4d908b45deecb5495ef`
- License: Apache License 2.0, notice retained.
- Local agent: `agents/shop_router_0909/main.py`
- Exact reconstruction: **passed**. Code and payload are byte-identical; no strategy rewrite occurred.
- Public replay equality: not asserted, because no score-linked public episode trace was exposed.

The selected notebook makes no “93.8% win rate” claim, so the old headline's semantics are not applicable. Public scores above are competition ratings; local win rates below are separately measured game outcomes.

## Controller

The agent loads 13 complete 719-turn tapes. It starts on plan 0, routes once at step 144 from the ordered first two public shops, uses an exact 15-pair map centered on Yarn Store, and falls back to plan 0 for every other pair. At step 648 it switches every route to plan 2 for a common ending. Thus actual behavior has a 144-turn common prefix and a shared step-648 tail even though the stored tapes themselves first differ at step 70.

Online logic uses only allowed current observations: own farm, own private inventory, public prices, current shops, step, and player. It inserts DIG for weed-blocked work, shifts only that worker within the day, advances eligible sales one turn using a lightweight shed projection, and liquidates on step 718. It does not read seed, replay ID, opponent identity/private state, future shops/prices/actions, outcome, or hidden simulator state. The only provenance caveat is that the notebook does not enumerate the exact upstream search/data lineage for all 13 static tapes.

## Local controlled results

Environment: `kaggle-environments==1.32.6`, 720 steps. Fresh module per game except the explicit same-process reset test. Both seats were always tested.

### Broad league

The 192-game league evaluated Shop Router 0909, frozen CurrentBest, and V2 against eight opponents, with fixed and natural shop schedules. Each candidate played 64 games.

| Candidate | W/L/T | Mean own | Median own | Mean advantage | P10 advantage | P5 advantage | Worst advantage |
|---|---:|---:|---:|---:|---:|---:|---:|
| Shop Router 0909 | 64/0/0 | 94,175.1 | 107,507 | 22,801.6 | 8,902 | 4,959.9 | 1,889 |
| CurrentBest | 41/17/6 | 86,722.9 | 90,651.5 | 9,930.9 | -6,201 | -12,479.2 | -14,405 |
| V2 | 30/34/0 | 82,953.5 | 87,530.5 | 1,011.2 | -12,977.3 | -14,154 | -18,699 |

Against the paired CurrentBest policy runs, the exact reproduction gained **+7,452.2 own money** and **+12,870.7 advantage** on average. This comparison is paired by opponent, seed, seat, and shop mode; it is not the same as direct H2H.

### Direct H2H

| Opponent | Games | W/L/T | Mean own | Mean advantage | P10 advantage | P5 advantage | Worst |
|---|---:|---:|---:|---:|---:|---:|---:|
| CurrentBest | 16 | 16/0/0 | 114,833.1 | **+8,053.0** | +565.5 | +525 | +525 |
| V2 | 16 | 16/0/0 | 118,343.0 | **+19,711.2** | +12,288.5 | +11,447 | +11,447 |

Fixed-shop CurrentBest H2H averaged +9,396.2 advantage; natural-shop H2H averaged +6,709.8. The full direct panel therefore supports a clean local improvement, while still being much smaller than the live leaderboard population.

### Internal route ablation

For one natural realization (`SMOOTHIE_SHOP`, `PIZZA_SHOP`), the actual fallback choice was plan 0. Forcing all 13 plans against CurrentBest and K3 showed plan 0 best by mean own money (89,747.5) and plan 2 only 19.5 lower; plan 2 was 10 advantage points better. Plan 12 was worst at -22,021.5 mean advantage. This supports the default choice for that one pair but is not enough coverage to redesign the public router.

## Safety and compatibility

All 276 deep-validation games completed with **0 runtime errors and 0 agent exceptions**. Four additional games reused one imported module sequentially; every game completed 720 steps with 719 calls, so episode/seat state reset passed.

The exact public output is not strict-lint clean. Across the 148 games in which it was the evaluated candidate, the checker recorded 5,805 warnings: 3,622 empty market placeholders, 2,137 zero-quantity orders left after sale advancement, and 46 current-observation hand-count mismatches around hires. The engine silently handled these and every game finished. They were deliberately not rewritten during exact reproduction.

There was one substantive strategy safety issue: plan 10 (`YARN_STORE`, `PET_CAFE`) allowed a sheep at `[7,4]` to escape on step 383 for H2H seed 1309401, reproduced in both seats. Broad league had zero escapes; H2H had two escape events in 32 games. Terminal stranding was zero in H2H and appeared in 2/64 league games, averaging only 7.8 value across the league. No hardened variant was built because feeding changes would cease to be the untouched public reproduction.

## Decision

**The exact public Shop Router 0909 v1 is the strongest locally reproduced candidate in this stage.** It beats CurrentBest 16/16 directly with +8,053 mean advantage and wins all 64 broad-opponent games. A new research candidate was therefore created at `agents/shop_router_0909/`, but it was **not promoted**: the task froze CurrentBest/deployment state, and the strict-lint plus route-10 sheep escape should receive an independently named hardening and fresh promotion panel first.

`experiments/current_best.json` was not changed. `submission/main.py` was not changed. No archive was built, no upload occurred, and no Kaggle submission/write API was used.
