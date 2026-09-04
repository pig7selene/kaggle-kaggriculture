# Final independent validation — `top50_raw_55899537`

This report is the complete, locked post-evaluation decision for the raw-route
challenger.  No code, route, threshold, opponent pool, criterion, or seed was
changed after the finalist lock.  The run used 800 game executions (400
candidate/baseline paired conditions), 720 steps per game, both seats, and 136
unique fresh integer seeds.

## Required 40-point report

1. **Candidate path.** `agents/autonomous_next/top50_raw_55899537.py`.
2. **Candidate SHA.** `5d66e9283e4e500a4113a6d167abb04e0a088c2ad8799c1750da4b7a2172d069` (raw and LF-normalized; matches the lock).
3. **Baseline path/SHA.** `agents/top50_distilled/top50_observable_portfolio.py`; `f9ca672848ccffdfe56888d99bcdf5a9d7644062b9eec0cf0cdea13574931233` (raw and LF-normalized; matches the lock).
4. **Seed-independence audit.** `experiments/raw55899537_seed_audit.json` reports PASS: final ranges 50000–50063, 50100–50115, 50200–50207, 50300–50331, and 50400–50433 have no overlap with any seed-addressable candidate experiment (15000–18015). Public replay episodes were non-seed-addressable and were not reused.
5. **Fresh seed count.** 136 unique seeds; each fixed-seed condition was declared before evaluation.
6. **Total paired games.** 400 paired conditions / 800 actual games (plus candidate and baseline each run independently).
7. **Opponent families.** Direct CurrentBest (128), Top-3 frontier (96), historical strong controls (80), natural/fresh RNG (64), and four stress regimes (32). Opponent paths and exact counts are in `raw55899537_final_manifest.json`.
8. **Seat coverage.** 200 paired conditions with candidate in seat 0 and 200 with candidate in seat 1; every seed/opponent condition was swapped.
9. **Candidate mean own money.** **89,629.9** coins overall.
10. **Baseline mean own money.** **89,447.7** coins overall.
11. **Paired own-money delta.** **+182.2** coins (candidate minus baseline; median +449.0).
12. **Own-money 95% CI.** Deterministic bootstrap 95% CI **[-1,612.4, +1,996.9]**; it crosses zero.
13. **Candidate mean advantage.** **8,284.0** coins (own final money minus the opponent's final money).
14. **Baseline mean advantage.** **7,583.5** coins.
15. **Advantage delta.** **+700.5** coins; median +2,067.0, P25 +844.8, P10 -12,877.9, P5 -35,718.0, worst -81,259.0.
16. **Direct H2H vs CurrentBest.** Candidate H2H **128/0/0** over 128 conditions; paired own-money delta +685.9 and advantage delta +1,863.6. The separately recorded baseline-vs-CurrentBest control was 6/6/180; this does not change the paired candidate-versus-baseline comparison.
17. **Decisive win rate.** **86.5%** (346 wins, 54 losses, no ties); bootstrap 95% CI **83.0%–89.8%**. This is an advantage-based H2H rate, not an own-money-positive rate (own delta was positive in 54.5% of pairs).
18. **Natural RNG result.** 32 fresh seeds × both seats (64 pairs), CurrentBest opponent: candidate **64/0/0**, mean own-money delta **-2,602.9**, mean advantage delta **+1,932.1**, P10 own delta **-26,162.0**. The route wins the matchup through opponent suppression while often earning less cash.
19. **tetsuya result.** 32 pairs: candidate **2/30/0**, baseline **26/6/0**; candidate money 78,847.9 vs baseline 95,595.9; paired own delta **-16,748.0**, advantage delta **-28,602.9**, P10 **-35,139.6**. This is the weakest matchup.
20. **Crop Dusta result.** 32 pairs: candidate **30/2/0**, baseline **32/0/0**; candidate money 91,929.5 vs baseline 90,522.7; own delta **+1,406.8**, advantage delta **-9,922.3**, P10 **-19,383.3**.
21. **OceanMix result.** 32 pairs: candidate **18/14/0**, baseline **16/16/0**; candidate money 88,635.5 vs baseline 87,483.1; own delta **+1,152.4**, advantage delta **+1,721.8**, P10 **-19,486.8**.
22. **Adaptive/strong-pool aggregate.** The historical strong-control family (V2, K3, Nazmus, router_hands12, Victor; 80 pairs) is positive: candidate money 104,261.6 vs 100,333.9, own delta **+3,927.7**, advantage delta **+7,150.4**, candidate H2H 80/0/0. The Top-3 frontier aggregate is negative (own -4,729.6; advantage -12,267.8), so the broad pool is not uniformly positive.
23. **Median delta.** Own-money median **+449.0**; advantage median **+2,067.0**.
24. **P25.** Own-money **-10,837.5**; advantage **+844.8**.
25. **P10.** Own-money **-24,208.5**; advantage **-12,877.9**.
26. **P5.** Own-money **-29,868.0**; advantage **-35,718.0**. Negative own-money delta occurred in **45.5%** of pairs; below -1,000 in 42.0%, below -3,000 in 35.8%, and below -5,000 in 30.8%. By opponent, candidate/baseline H2H W/L/T were: CurrentBest 192/0/0 vs 6/6/180; V2 16/0/0 vs 16/0/0; tetsuya 2/30/0 vs 26/6/0; Crop Dusta 30/2/0 vs 32/0/0; OceanMix 18/14/0 vs 16/16/0; K3 16/0/0 vs 16/0/0; Nazmus 16/0/0 vs 16/0/0; router_hands12 16/0/0 vs 16/0/0; Victor 40/8/0 vs 38/10/0.
27. **Worst.** Worst paired own-money delta **-62,075** (OceanMix, seed 50109); worst advantage delta **-81,259** (tetsuya). The structured review is in `raw55899537_worst_case_analysis.md`.
28. **Negative-delta rate.** Own-money 45.5%; advantage 16.0%. The direct panel had no negative advantage deltas, while the Top-3 panel had 58.3% negative advantage deltas.
29. **Runtime failures.** **0** across all 800 game executions.
30. **Semantic failures.** **0** candidate and baseline action-schema failures.
31. **Livestock escapes.** **0 candidate escapes**. The baseline had two observed escapes in the Victor control; this does not count against the candidate.
32. **Stranded value.** Candidate mean terminal value **45.645** coins, range 12–192, with 0/400 above the 500-coin materiality threshold. There was no meaningful stranded value; residuals were mostly fertilizer.
33. **Route realization.** Candidate mean realization **99.9955%** (3,206,889 matches / 3,207,034 requests), zero fallback actions, 28 repair actions and 12 repair aborts across 400 candidate runs. Baseline realization was 99.9712% with 139 repairs and 114 aborts.
34. **Market externality.** Candidate own-money delta **+182.2**, opponent-money delta **-518.3**, net advantage delta **+700.5**. Therefore roughly three quarters of the H2H gain is opponent suppression/shared-market externality rather than reliable own-cash growth.
35. **Economic attribution.** Across 336 fixed-seed pairs used by the ledger, candidate-minus-baseline revenue deltas were: strawberry **+471,808** (+1,404/pair), wool **+553,712** (+1,648/pair), milk **-127,301** (-379/pair), wheat **-1,410,671** (-4,198/pair), fertilizer **-1,158,863** (-3,449/pair), melon **-103,692**, and carrot **-37,508**. Costs changed by +101,000 animal purchases, +191,577 labor, +2,000 land, while fertilizer product spend fell 1,179,348 and wheat product spend fell 1,127,208. This is a route/market mix effect, not a clean production-cost win.
36. **Worst-case failure pattern.** OceanMix losses preserve land, hands, animals, route realization, and terminal cleanup but miss milk/strawberry revenue (the largest row was -46,623 milk and -17,307 strawberry). Tetsuya losses compound from day 6: the candidate ends with 6 cows/4 sheep versus the baseline's 6 cows/6 sheep, with lower milk/strawberry and a 1,623-coin labor premium. There are no deadlocks, escapes, or terminal crop piles.
37. **Discovery comparison.** Discovery reported 64/0/0 on two 16-seed panels and approximately +1,976 advantage. Fresh direct H2H remained positive (+1,864), but the all-family advantage fell to +700 and own-money to +182, with negative P10/P5 and a severe tetsuya regression. Transfer quality: **POOR** for broad deployment (good on direct CurrentBest/natural controls, poor on frontier generalization).
38. **Statistical significance.** Advantage sign test: 336 positive / 64 negative, two-sided **p = 1.24e-45**. Own-money sign test: 218 positive / 182 negative, **p = 0.0800**. Thus the H2H advantage sign is convincing, but the own-money improvement is not.
39. **Final decision label.** **DO NOT PROMOTE.** The candidate fails the preferred robust-promotion gates: fresh own-money gain is effectively zero with a CI crossing zero, P10/P5 are materially negative, and it is decisively weaker against tetsuya and the Top-3 aggregate despite perfect direct CurrentBest H2H.
40. **READY FOR PACKAGING.** **NO.** Keep `top50_observable_portfolio.py` as the validated deployment baseline; do not package or submit `top50_raw_55899537`.

## Panel summary

| panel | paired conditions | candidate W/L/T | candidate money | baseline money | own Δ | advantage Δ | own P10 |
|---|---:|---:|---:|---:|---:|---:|---:|
| direct CurrentBest | 128 | 128/0/0 | 82,997.0 | 82,311.1 | +685.9 | +1,863.6 | -21,345.0 |
| Top-3 frontier | 96 | 50/46/0 | 86,471.0 | 91,200.6 | -4,729.6 | -12,267.8 | -27,524.0 |
| historical strong | 80 | 80/0/0 | 104,261.6 | 100,333.9 | +3,927.7 | +7,150.4 | -19,115.0 |
| natural/fresh RNG | 64 | 64/0/0 | 83,873.6 | 86,476.5 | -2,602.9 | +1,932.1 | -26,162.0 |
| stress suite | 32 | 24/8/0 | 100,571.5 | 91,463.0 | +9,108.5 | +16,364.8 | -15,339.0 |
| **all raw-weighted** | **400** | **346/54/0** | **89,629.9** | **89,447.7** | **+182.2** | **+700.5** | **-24,208.5** |

Stress regimes were diagnostic only: early shops +13,800 own / +14,873
advantage; premium pressure -1,160 / +7,115; strong opponent -2,215 /
 +6,857; weak cash +26,009 / +36,615 (both candidate and baseline lost the
Victor H2H).  No post-hoc market-regime clustering was used for selection; the
locked stress probes are the predeclared regime checks.

## Route consistency and economic milestones

The candidate's normal route repeatedly reaches first land at step 151 (day 6,
hour 7), second land at step 266 (day 11, hour 2), a 12-hand peak, and a
three-quadrant final farm with nine cows and five sheep.  The telemetry
milestone extractor records step 0 for some seat-1 initial observations; this
is an observation-indexing artifact, not a post-lock route change.  Across the
400 candidate runs the peak-hand count was always 12; peak animals were 14 in
360 runs, 10 in 32, and 4 in the weak-cash stress runs.  The small number of
repair/abort events did not create runtime, semantic, livestock, or terminal
failures.

## Claimed mechanism replication

| prior discovery claim | fresh result | classification |
|---|---|---|
| strawberry contribution | +471,808 revenue total | **REPLICATED** |
| wool contribution | +553,712 revenue total | **REPLICATED** |
| fertilizer revenue contribution | -1,158,863 revenue; lower spend | **REVERSED** |
| wheat contribution | -1,410,671 revenue; lower spend | **REVERSED** |
| milk contribution | -127,301 revenue | **NOT REPLICATED / REVERSED** |
| capital cycling | positive advantage but near-zero own-cash gain | **PARTIAL** |

The raw route is coherent and safe, but its gains are regime-dependent and often
come from changing the opponent's realized price/cash.  A future research stage
may study the tetsuya/OceanMix failure mechanisms, but this locked validation
does not authorize tuning or a hidden successor.

**Final decision: DO NOT PROMOTE.** No Kaggle submission was performed.
