# ShopRouter0909Hardened Post-Submission Diagnostic

This is a read-only research report. The submitted source and archive were not changed, packaged, uploaded, or resubmitted.

## Required answers

1. **Exact scan timestamp:** 2026-09-10T01:26:00+08:00.
2. **24h cutoff:** 2026-09-09T01:26:00+08:00.
3. **Recent public strategy candidates found:** 3.
4. **Top 3 recent candidates:** flexonafft/kaggriculture-most-powerfull-route (score unbound, NEW_24H at 2026-09-09T21:35:03.2066667+08:00); tetsutani/market-smart-farming-kaggriculture (score unbound, MAJOR_UPDATE_24H at 2026-09-09T21:19:56.690+08:00); dmitriigluzdov/kaggriculture-seven-turn-rescue-best-lb-2800 (score unbound, NEW_24H discovery; exact publication timestamp unretained).
5. **Exact score/version binding:** all three fresh candidates are score-unbound: flexonafft source run 348544166 has no linked score; the tetsutani major update has no retained run/submission score link; dmitriigluzdov's title-only 2800+ claim is rejected. FrozenBest's ancestor remains exactly bound at v1/run 348430185/submission evidence score 2839.5.
6. **Recent 2900+ agent exists:** NO.
7. **Recent 3000+ agent exists:** NO.
8. **Most worth reproducing next:** Kaggriculture | Most Powerfull Route.
9. **Why:** It can recover and sell physically reachable goods in the last seven turns that FrozenBest's stored terminal tape leaves behind, while retaining the parent route on unsupported or non-dominating states.
10. **FrozenBest plans:** 13 complete continuations (plans 0-12), with universal plan 2 terminal takeover at step 648.
11. **Activation frequency:** see the table below; fixed is exact over all 64 ordered pairs, natural is 128 fresh games.
12. **Mean own money per plan:** see the table below.
13. **Mean advantage per plan:** see the table below.
14. **P10 own money per plan:** see the table below.
15. **Worst own-money result per plan:** see the table below.
16. **Strongest plan:** Plan 3 by balanced mean own money; Plan 7 is narrowly best by mean advantage.
17. **Weakest strategic plan:** Plan 12 (lowest mean advantage and 2 escape events). Plan 2 is marginally lowest by mean own money but has the strongest P10 tail.
18. **Most dangerous tail plan by P10 own money:** Plan 9.
19. **Router hindsight-best selection rate (ties count):** 26.7%.
20. **Mean oracle own-money gain:** 1441.4.
21. **Mean oracle advantage gain:** 896.6.
22. **Maximum oracle own-money gain:** 8746.0.
23. **Mean router regret:** 1441.4.
24. **P90 / P95 router regret:** 4928.0 / 7172.0.
25. **Largest-regret regime:** plan7_pizza_yarn|crop_dusta|seat0, shops ['PIZZA_SHOP', 'YARN_STORE'], selected Plan 7 vs Plan 12, regret 8746.0.
26. **Regret predictable from public state:** WEAK_OR_UNPROVEN evidence only; strongest absolute univariate correlation is 0.287. No selector was trained, so predictability is not established.
27. **Could the full plan choice safely be delayed:** NO for an unrestricted 13-way router; at least one continuation diverges at step 144. Pairwise staged delays remain possible (Plan 0/2 to step 313; several sheep-route pairs to step 216).
28. **Common-prefix structure:** all runtime policies share Plan 0 actions through step 143 and identical observed economic state through step 144; divergent step-144 actions first alter observations at step 145. Pairwise continuation prefixes vary from 0 to 169 actions; all switch to Plan 2 at step 648.
29. **Strategically diverse:** PARTLY; the blended clustering retains 4 effective groups, including one nine-plan sheep-led family.
30. **Some plans redundant:** YES, candidates exist; closest pair is 7/8 (action similarity 96.8%, outcome correlation 1.000).
31. **Dominant limitation:** ROUTER BOTTLENECK. Oracle-negative regimes after best-plan selection: none.
32. **Mean router headroom exceeds +1k:** YES.
33. **Mean router headroom exceeds +3k:** NO.
34. **Mean router headroom exceeds +5k:** NO.
35. **Recommended next research stage:** NO ACTION. NEXT: wait for real leaderboard result.
36. **Kaggle submission result:** PENDING.
37. **FrozenBest source unchanged:** CONFIRMED, SHA-256 `da5c6df2c71128ce1372a5adaf6d4859f5758e7854b399d6ff634fbca666d8a2`.
38. **Submission package unchanged:** CONFIRMED, main.py `4a188ceaedaa5e37c2216c803517314a2cb2fd780a5bb65956ca016cf278c803`, archive `26e7d39eb1df83af7c595167298ad8f3d61afce76e216cd1e25d6416bb791046`.
39. **Upload/submission during this stage:** NONE.

## Per-plan summary

| Plan | Fixed activation | Natural activation | Mean own | Mean advantage | P10 own | Worst own |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 76.56% | 79.69% | 105829.2 | 24711.3 | 64762.0 | 38873.0 |
| 1 | 1.56% | 3.12% | 110557.2 | 27406.3 | 58457.0 | 32853.0 |
| 2 | 0.00% | 0.00% | 105797.6 | 24667.0 | 64948.0 | 38718.0 |
| 3 | 1.56% | 1.56% | 111744.5 | 30410.0 | 57825.0 | 31691.0 |
| 4 | 1.56% | 0.00% | 110883.0 | 28820.6 | 58462.0 | 32744.0 |
| 5 | 3.12% | 0.00% | 110771.0 | 28722.5 | 58333.0 | 32618.0 |
| 6 | 3.12% | 4.69% | 111697.1 | 30493.2 | 57659.0 | 31859.0 |
| 7 | 1.56% | 0.00% | 111738.0 | 30544.2 | 57693.0 | 31900.0 |
| 8 | 1.56% | 0.00% | 111726.7 | 30528.2 | 57678.0 | 31887.0 |
| 9 | 4.69% | 4.69% | 109574.6 | 28182.0 | 55542.0 | 31528.0 |
| 10 | 1.56% | 4.69% | 111430.8 | 29470.1 | 58216.0 | 32323.0 |
| 11 | 1.56% | 0.00% | 111673.5 | 30347.1 | 57608.0 | 31966.0 |
| 12 | 1.56% | 1.56% | 106170.1 | 20206.6 | 56580.0 | 32055.0 |

## Interpretation

The exact current router averages 115203.3 own money on the matched 90-condition oracle panel. The best single global plan averages 111744.5; the best constant plan chosen separately per shop case averages 116196.9; and the infeasible per-condition hindsight oracle averages 116644.7. Thus shop-pair-only headroom above the best global constant is 4452.4, which explains 90.9% of the full conditioning gain on this panel. The frozen mapping captures 70.6%; remaining within-shop context headroom is at most 447.8. This latter number is an upper bound, not evidence that a legal selector can realize it.

The largest regret mechanism differences were: alternative planned cow quantity differs by -2; alternative planned sheep quantity differs by +3; crop planting-action deltas {'CARROT': -3, 'WHEAT': 2}; realized sale revenue delta +10606. The dominance table in `shop_router_0909_router_regret.json` distinguishes regimes where an existing plan usually replaces the selected parent from regimes where even the oracle portfolio remains weak.

Three mappings deserve first inspection if a later router stage is justified: Pizza→Yarn selected Plan 7 but Plan 12 won all six matched contexts by +7,186.7 mean own money; Smoothie→Yarn selected Plan 8 but Plan 1 won all six by +2,463.2; Yarn→Bakery selected Plan 9 but Plan 7 won all six by +2,399.7. These are diagnostic matched-condition findings, not authorized route changes.

Conditioning checks show that CurrentBest is the hardest opponent family for every forced plan by mean advantage, although every plan remains positive on average against all three tested families. Seat effects are negligible (the largest plan-level seat mean-own gap is under 45 coins). Low step-144 premium-price regimes have lower absolute own money for every plan, but that split is confounded with the fixed shop cases and is not a causal market rule.

Livestock safety is not uniform across forced regimes: Plan 12 had 2 escape events, Plans 1 and 5 had 1 each, and the frozen-hardened Plan 10 had 0. These are portfolio diagnostics under off-route forcing, not evidence that every escape is reachable under the frozen router's intended shop mapping.

## Scope and limitations

The forced-policy panel covers 15 representative shop regimes, three opponent families, both seats, and all 13 continuations (1,170 games). It is balanced for plan comparison but is not a full probability-weighted deployment forecast. The natural frequency panel adds 128 games; the exact fixed frequency panel enumerates all 64 ordered pairs in both seats. Hindsight oracle values are optimistic upper bounds. Public-feature associations are descriptive and no model or rule was trained. Local opponents and deterministic simulation cannot substitute for the pending Kaggle leaderboard result.

All 1426 diagnostic games had zero runtime errors and zero agent exceptions. The strict observer recorded 34,456 already-known benign public-tape diagnostics ({"AssertionError('invalid market operation')": 18234, "AssertionError('wrong quantity market order')": 16038, "AssertionError('wrong hand action count')": 184}); these were intentionally not changed or treated as new failure classes.

## Decision

**NEXT: wait for real leaderboard result**

Kaggle submission result: **PENDING**

## Public sources

- [Kaggriculture | Most Powerfull Route](https://www.kaggle.com/code/flexonafft/kaggriculture-most-powerfull-route)
- [Market-Smart Farming | Kaggriculture](https://www.kaggle.com/code/tetsutani/market-smart-farming-kaggriculture)
- [Kaggriculture: Seven-Turn Rescue | Best LB 2800+](https://www.kaggle.com/code/dmitriigluzdov/kaggriculture-seven-turn-rescue-best-lb-2800)

Scores and version/run bindings are reproduced exactly from the frontier ledger; missing bindings remain explicitly unverified.
