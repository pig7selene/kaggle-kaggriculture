# Local → leaderboard transfer-gap forensic report

## Executive finding

The submission is Kaggle submission **56123896**, timestamped **2026-09-09 13:24:20.373 UTC** (21:24:20.373 UTC+8), status **COMPLETE**, with exact Public Score **2418.4**. The local archive still hashes to `26e7d39eb1df83af7c595167298ad8f3d61afce76e216cd1e25d6416bb791046`. The strongest explanation is **CASE E: the local harness and score proxy were wrong for the question being asked**, compounded by a changed opponent distribution. Packaging, Plan 10, Plan 0 economics, and router regret are not supported causes.

## Required answers (1–44)

1. **Exact score:** 2418.4.
2. **Submission ID:** 56123896.
3. **Submitted SHA:** the local submitted archive matches its frozen SHA exactly. Kaggle exposes filename/timestamp/score but not remote bytes, so server-side hash identity cannot be independently proven.
4. **Packaging cause:** implausible; prior 30,198-call equivalence plus unchanged hashes and normal COMPLETE status strongly reject it.
5. **Biased methodology:** yes—stale historical opponents, family selection bias, 50% forced shops, four broad seeds, and margin-centric summaries.
6. **Old distribution:** eight historical opponents, 4 seeds, both seats, 32 fixed-shop + 32 natural-shop games; no Shop0909 descendant.
7. **Refreshed distribution:** four frozen candidates × four current public strategies × five fresh natural seeds × both seats; historical controls kept separate.
8. **Recent reconstruction:** four genuinely recent complete notebooks, representing three distinct runtimes because Seven-Turn Rescue is byte-identical to Most Powerfull Route. Two were exercised; one runnable strategy and one native x86-64 strategy remain held out.
9. **FrozenBest current W/L/T:** 20/20/0 over 40 primary games.
10. **Own-money change:** +30632.2 (90679.0 → 121311.1); it improved.
11. **Advantage change:** -22700.7 (28189.7 → 5489.0).
12. **Current tail:** advantage P10 -7.0, P5 -7.1, worst -10.0.
13. **Exact vs Hardened:** paired own-money delta is exactly 0.0 in all 40 current conditions; actions/economics are off the patched Plan-10 path.
14. **Plan-10 patch:** exonerated.
15. **Plan 0 frequency:** 32/40 = 80%.
16. **Plan 0 current performance:** 16/16/0, mean own 122298.8, mean advantage +5667.9, P10 advantage -7.0, worst -7.0.
17. **Plan 0 degradation:** own money changed +16469.6; advantage changed -19043.4. It is not an own-economy collapse.
18. **Worst-transfer plan:** Plan 12, own delta -29217.6 in the limited all-plan panel.
19. **Best-transfer plan:** Plan 0, own delta +14927.8.
20. **Oracle headroom:** mean 0.0, max 0.0 over eight sampled current-meta conditions.
21. **Router regret:** no; it fell from historical mean +1,441.4 to observed 0 in this limited diagnostic.
22. **First divergence:** all 20 losses stayed tied through day 28 and first became negative on day 29; 0/20 crossed -1,000.
23. **Lost revenue:** fertilizer, mean 6.5 coins per loss.
24. **Excess cost:** none; every measured cost category is identical.
25. **Shared market:** it determines realized prices, but the decisive relative gap is only the opponent's extra terminal fertilizer sold at the $1 floor. It is not a broad whole-game realization collapse.
26. **Same-family harm:** yes in binary outcomes—0/20 against the two terminal descendants—versus 20/0 against two structurally distinct public opponents.
27. **Oversupply collision:** visible in low/floor prices and synchronized sales, but not causal for the broad transfer gap; near-mirrors are identical through day 28.
28. **Terminal headroom:** public overlays add mean 6.75 (e182) or 9.25 (r31), maximum 16 coins—far below +1,000.
29. **Terminal importance:** negligible cash fraction, but meaningful match-result tie-breaker because every 5–10 coin loss counts as a loss.
30. **Seven-Turn ideas:** retain as an outcome-sensitive evaluator control; do not start a dedicated value-recovery stage now.
31. **Scoring semantics:** central. [Kaggle's official documentation](https://www.kaggle.com/docs/competitions) says win margin does not affect Skill Rating and matchmaking is rating-dependent.
32. **Environment parity:** a real 1.32.6→1.32.7 price-curve change was found; isolated 1.32.7 reruns preserve the finding and show a small Phase-A effect.
33. **Public decay:** public observational studies show strong fixed-agent time drift generally, but no time series binds this exact submission. The old Shop Router v1 score 2839.5 versus 2418.4 is consistent with drift, not causal proof.
34. **Dominant failure family:** Shop0909-derived terminal-enhanced near-mirrors.
35. **Top-five pattern:** all are terminal fertilizer tie-breakers; losses 5–10 coins, first negative day 29, no cost/crop/livestock divergence, no stranded final inventory, extra opponent fertilizer sold at floor.
36. **Root cause:** harness/score-metric mismatch.
37. **Second cause:** stale opponent distribution and same-parent public meta convergence.
38. **Evidence weights:** 70% harness+score metric, 25% opponent/meta, 3% environment, 2% terminal cash; these are judgmental evidence weights, not an additive causal variance decomposition.
39. **Classification:** mixed; dominated by HARNESS GAP + SCORE-METRIC GAP, then opponent/meta; not router/parent-economy/packaging.
40. **Next stage:** **rebuild evaluation methodology before strategy work**—version-lock 1.32.7, make W/L/T primary, margin secondary, use contemporaneous/similar-strength opponents, preserve holdouts, and model rating uncertainty rather than inventing a score transform.
41. **Do not work next:** Plan-0 replacement, router redesign, Plan-10, a large terminal-value stage, GA/RL, arbitrary tuning, or a new submission.
42. **FrozenBest unchanged:** confirmed SHA `da5c6df2c71128ce1372a5adaf6d4859f5758e7854b399d6ff634fbca666d8a2`.
43. **Submission artifacts unchanged:** confirmed `submission/main.py` SHA `4a188ceaedaa5e37c2216c803517314a2cb2fd780a5bb65956ca016cf278c803` and archive SHA `26e7d39eb1df83af7c595167298ad8f3d61afce76e216cd1e25d6416bb791046`.
44. **No writes to Kaggle:** confirmed; no packaging, upload, or submission occurred. Only read-only listing/source acquisition was used.

## Decision

**CASE E — NEXT: rebuild evaluation methodology before strategy work.**

The key contradiction is now resolved: the refreshed agent still makes more money and wins distinct opponents by thousands, but an outcome-sensitive rating treats twenty 5–10 coin losses as twenty full losses. A 64–0 margin-weighted historical panel did not measure that vulnerability.

## Public sources

- [Official Kaggriculture code listing](https://www.kaggle.com/competitions/kaggriculture/code)
- [Official Kaggriculture overview](https://www.kaggle.com/competitions/kaggriculture/overview)
- [Most Powerfull Route](https://www.kaggle.com/code/flexonafft/kaggriculture-most-powerfull-route), [Market-Smart Farming](https://www.kaggle.com/code/tetsutani/market-smart-farming-kaggriculture), and [Seven-Turn Rescue](https://www.kaggle.com/code/dmitriigluzdov/kaggriculture-seven-turn-rescue-best-lb-2800)
- [Shape the Shop Work the Pasture](https://www.kaggle.com/code/tetsutani/shape-the-shop-work-the-pasture-kaggriculture), [Farming Score V3](https://www.kaggle.com/code/lynnsakurai/farming-score-v3-replay-revised), and [Adaptive Route Agent V2](https://www.kaggle.com/code/reyhanksatria/adaptive-route-agent-v2)
