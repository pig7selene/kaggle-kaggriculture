# Shop Router 0909 Plan-10 hardening report

## Decision

**Select and promote `ShopRouter0909Hardened`.** The one-primitive Plan-10 repair removes the confirmed sheep escape while preserving exact behavior outside Plan 10. The fresh 64-game broad league was 64/0/0 with mean advantage +28,189.7; direct H2H was 24/0/0 against both CurrentBest and V2. No runtime error, agent exception, new warning class, or livestock escape occurred after lock.

## Required answers

1. **Escape turn:** end-of-day refresh after action step 383 (day 15/hour 23); the sheep is first absent in observation step 384.
2. **First causal divergence:** step 332, `SELL WHEAT 9`, starts the shortage by leaving 16 wheat for 17 animals at day-14 opening. The first service failure is step 345; the decisive day-15 allocation failure becomes unavoidable at step 363.
3. **Why:** the final feeder receives one of two requested wheat, consumes it on `[6,4]`, reaches `[7,4]` empty, and two successive `FEED` actions silently fail. Two unfed end-of-day refreshes remove the sheep.
4. **Root-cause class:** wheat resource allocation/order and feed timing. Movement and hand availability are not causal; the feeder arrives on time.
5. **Existing action that created it:** initiating step-332 wheat sale; decisive step-360 farmer pickup of five hoards one unused unit and starves the step-363 feeder pickup.
6. **Candidates tested:** 4.
7. **Edits:** A step332 sell 9→8; B step335 add buy 1 wheat in idle market capacity; C step339 first hand pickup 5→4; D step360 farmer pickup 5→4.
8. **Selected candidate:** Fix D, `reallocate_day15`.
9. **Primitive changes:** one numeric action argument, only when route Plan 10 is active.
10. **Dead/no-op reuse:** selected Fix D does not replace a dead action; it reclaims an otherwise unused carried wheat unit. Fix B tested the dead market-capacity alternative.
11. **Route alignment:** unchanged; no insertion and no tape-index shift. There are 8 emitted-action differences in the known replay: the patch at 360 plus seven later sale-quantity realizations from the surviving sheep.
12. **Escape before/after:** 1→0 in each seat of the known condition.
13. **Plan-10 targeted count:** 120 selected-patch matrix games (72 development + 48 post-lock); 100 actually routed to Plan 10 and 20 were natural-RNG negative controls. The separate known gate adds 2 games.
14. **Post-patch Plan-10 escapes:** 0/100 actual Plan-10 matrix games (and 0 in all 120 matrix games).
15. **Known-condition own-money delta:** +4,127 (90,596→94,723).
16. **Known-condition advantage delta:** +4,142 (29,361→33,503); opponent money changed by -15.
17. **Fresh broad validation W/L/T:** 64/0/0 across 64 games. Across all 184 locked-candidate post-lock games: 160/0/24; all ties are the direct Exact H2H where the route was outside Plan 10.
18. **Broad mean own money:** 90,679.0; median 92,134.5.
19. **Broad mean advantage:** +28,189.7.
20. **H2H vs CurrentBest:** 24/0/0, mean advantage +13,046.2 over 24 games.
21. **H2H vs V2:** 24/0/0, mean advantage +25,047.2 over 24 games.
22. **Natural-shop broad league:** 32/0/0, mean own 87,564.2, mean advantage +23,046.3, worst +5,164 (32 games).
23. **Fixed-shop broad league:** 32/0/0, mean own 93,793.8, mean advantage +33,333.1, worst +6,770 (32 games).
24. **Seat 0:** 32/0/0, mean own 90,649.5, mean advantage +28,146.5 (32 broad-league games).
25. **Seat 1:** 32/0/0, mean own 90,708.4, mean advantage +28,232.9 (32 broad-league games).
26. **Broad advantage P25:** +13,618.8 (own-money P25 68,475.0).
27. **Broad advantage P10:** +7,814.3 (own-money P10 55,615.5).
28. **Broad advantage P5:** +6,770.0 (own-money P5 54,764.0).
29. **Broad worst:** advantage +5,164; own money 49,258.
30. **Runtime exceptions:** 0.
31. **Agent exceptions:** 0.
32. **Actual livestock escapes:** 0 across 184 post-lock candidate games. Terminal counters: 1,448 animal-instances had exactly one missed final-day refresh across all panels, but none had two misses; broad-league counts exactly match Exact and the season ends before escape. 
33. **New warning class:** none. Only the two previously classified benign strict-checker classes appeared; broad counts are exactly Hardened 2,778 vs Exact 2,778.
34. **Exact-vs-Hardened paired delta:** off-route broad league 64/64 pairs are exactly 0 own/0 opponent/0 advantage. Across 40 fresh actual Plan-10 pairs: mean own +1,033.6, opponent -184.2, advantage +1,217.9.
35. **Expected-value cost of the original defect:** `1/64 × 16/40 × 2,466.1 = 15.41` own-money coins per random game using raw conditional cost; baseline-adjusted estimate is 14.92. Practical paired hardening gain is +16.15 own coins and +19.03 advantage per random game.
36. **Practical EV:** Hardened is superior: zero off-route cost, +78.7 mean own money even in the 24 Plan-10 pairs where Exact did not escape, and positive overall Plan-10 paired gain.
37. **Selected version:** `ShopRouter0909HardenedPlan10ReallocateDay15`.
38. **Research-best promotion:** yes, after the locked validation passed.
39. **Final source:** `agents/shop_router_0909_hardened/main.py`.
40. **Final SHA-256:** `da5c6df2c71128ce1372a5adaf6d4859f5758e7854b399d6ff634fbca666d8a2`.
41. **`experiments/current_best.json`:** changed to point at the hardened research agent.
42. **Frozen CurrentBest source:** untouched; SHA-256 remains `f9ca672848ccffdfe56888d99bcdf5a9d7644062b9eec0cf0cdea13574931233`.
43. **`submission/main.py`:** untouched; SHA-256 remains `789bb9bbd5122eb4891983e776a13777328e3e87736cbbc0b4bc86d13fc33f9b`.
44. **Kaggle:** no package, upload, or submission was performed.

## Safety interpretation

The 16 broad-league terminal stranded units are one carried wool per affected game (aggregate marked value 4,040), exactly matching Exact. They are not caused by the patch. Existing strict warnings remain intentional public-tape behavior and are not counted as environment failures. Provenance is retained in `agents/shop_router_0909_hardened/NOTICE.md` and `LICENSE.txt`; the exact public parent and action payload remain immutable.

Frozen Exact asset hashes are: `main.py` `d6d74997dc5b483db63d8e39cafa1afeec0f366824e75107e109123f111e866b`; `actions.json` `17d503f2fd20d59f9c0f14024d1e74a8add8bb9b5561d4d908b45deecb5495ef`; `LICENSE.txt` `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`; `submission-manifest.json` `e58657e059e0dac2e1fe9c9175141a3d876bc7d33b7b31ddca80669ec10e8df6`.
