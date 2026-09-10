# Farming Score V5: Timing Optimized — deep forensic report

## Executive decision

**No candidate was built or promoted. CurrentBest remains frozen.** The exact public V5 v2 mechanism produced zero behavioral/economic difference across 48 paired conditions. Full V5 averaged **+1,136 own coins** versus CurrentBest but **−3,494 advantage**, had a negative median own delta, a 95% bootstrap interval crossing zero, severe downside, and livestock escapes in 40/48 games. The scientific stop rule fired.

## 1–5. Source, reconstruction, name, and architecture

1. The notebook is Arlene (`lynnsakurai`), *Farming Score V5: Timing Optimized*, current public version 2, run 346466052, dated 2026-09-01.
2. Public v2 archive SHA: `35143710b4b493e2e94a68efa21aa03fc3833318fef52645b8e58d5ffeb4bf9e`; local `main.py`: `e8498c67914ecc607ae69fde25a728361eb5acea94c00ecc85deffbdafe50413`; reconstructed single-file main: `e8498c67914ecc607ae69fde25a728361eb5acea94c00ecc85deffbdafe50413`.
3. Reconstruction passed exact archive/member verification, compile/import, and 216 corrected local games with zero runtime/schema failures. No public replay was exposed, so independent public-action equivalence is not claimed beyond exact public-source reconstruction.
4. “Timing Optimized” means: decide the livestock direction at the step-150 second-shop information window, then reuse it for step-169/176 registered bundles, subject to the substitution cap. It does not retime purchases or the rest of the economy.
5. V5 is bounded state-adaptive guarded replay, not a fixed replay and not a free planner.

## 6–9. Economy, phases, V3 relationship, first divergence

6. The complete economy combines replayed melon/wheat/strawberry cohorts, pasture livestock, fertilizer, up to 12 hands, two land expansions, conserved sale nodes, repair wrappers, and step-718 liquidation.
7. Its phases are opening geometry, first production, shop-information window, land/strawberry buildout, mature multi-product monetization, and terminal liquidation.
8. There is no clean V3→V5 timing revision map: the retrieved V5 is a Kenjo/Niklita-derived lineage. Land timing is unchanged; livestock/crops/market/repair/terminal logic is structurally different. The genuine natural revision is public V5 v1→v2.
9. V3 and V5 diverge at step 0 in every pair: V3 buys 13 wheat; V5 places no market order. The full downstream chain is confounded, so this is not assigned as the cause of the final delta.

## 10–18. Controlled league

10. V5−V3 own money: mean **+3,918**, median +4,498, bootstrap 95% CI **[−1,231, +9,285]**.
11. V5−V3 advantage: mean **−7,586**, CI **[−12,430, −3,137]**.
12. V5−CurrentBest own money: mean **+1,136**, median −592, CI **[−4,964, +7,350]**.
13. V5−CurrentBest advantage: mean **−3,494**, CI **[−8,793, +1,120]**.
14. Broad paired V5−V3 advantage W/L/T is 12/36/0; direct games versus V3 are **0/8/0**.
15. Broad paired V5−CurrentBest advantage W/L/T is 26/22/0; direct games versus CurrentBest are **4/4/0**.
16. V5 absolute own-money P10/P5/worst are **61,146 / 56,727 / 51,527**. Paired V5−CurrentBest P10/P5/worst are **−16,798 / −38,192 / −45,241**.
17. V5 improves V3's absolute tail levels on this panel, but the paired tail remains bad and direct V3 H2H is 0–8. It did not reliably repair V3's failure regimes.
18. Crop Dusta is not repaired: V5−CurrentBest own delta is +14,184, but advantage is −13,561 and direct broad-condition H2H is 2–6; the opponent benefits even more from the shared market.

## 19–28. Timing and causal mechanisms

19. Land: no change—requests remain 150 and 265.
20. Labor: no isolated optimization; V5's distinct route spends about 6,387 versus V3's 5,914 in the dossier.
21. Livestock: the meaningful source change is evidence timing/commitment at cow88/cow150/cow169/cow176, not earlier purchases. V5 also has fewer animals and an unrelated programme.
22. Crops: no v1→v2 change. V3/V5 strawberry and wheat differences are structural; the core early melon cohort is similar.
23. Market: no v1→v2 change. Full-policy shared-market effects explain why own-money and advantage conclusions disagree.
24. Terminal: V5 sells visible inventory at 718; useful in principle, but unchanged v1→v2 and not isolated versus V3.
25. No positive V5 mechanism qualified as strongest. The most important exact public change is the shop-window commitment only because it is the sole v2 revision.
26. Its measured causal value is **exactly 0 coins**: v1 and v2 were action-identical in all 48 conditions.
27. Rejected: full V5 economy, adaptive pasture substitution as a transplant, the unisolated cow88 maturity gate, and terminal frontier as a claimed new V5 gain.
28. Nothing transferred to CurrentBest; its source remains unchanged.

## 29–40. Candidate funnel and safety

29. Candidate agents built: none.
30. Strongest candidate: none; CurrentBest remains the reference.
31–39. Candidate paired deltas, H2H, natural RNG, broad results, P10/P5/worst: **NOT RUN**, because no candidate entered the funnel.
40. Full V5 has 0 runtime and schema failures but fails safety: 40 escapes in 40/48 games, always at step 215 on pasture `[5,3]` (32 COW, 8 SHEEP). At step 210 it requests FEED without carried wheat, a silent no-op; the animal escapes at end of day.

## 41–46. Attribution and decision

41. Economic attribution: in the six-condition dossier V5 trails V3 mainly in milk, wool, and strawberry revenue, uses fewer animals, and spends somewhat more on labor. The full commodity tables are in the attribution artifact.
42. Timing attribution: only the v2 step-150 commitment is causal and exactly tested; it changes zero natural actions and is worth zero. All V3/V5 timing comparisons are descriptive because lineage and quantities change together.
43. New research best promoted: **No**.
44. Promoted path/SHA: not applicable. Frozen CurrentBest remains `agents/top50_distilled/top50_observable_portfolio.py`, SHA `f9ca672848ccffdfe56888d99bcdf5a9d7644062b9eec0cf0cdea13574931233`.
45. Unexplained: the original author's private/public leaderboard motivation for v2 and regimes outside the tested panel where the commitment triggers economically. The notebook's current v2 score was not public in retrieved metadata.
46. Best next direction: independently repair and test the step-210 exact-feed delivery defect **only if** future evidence makes the complete V5 economy strategically attractive; otherwise study a different public lineage with a source-identifiable, behaviorally active revision. Do not transplant the zero-value window commitment.

## Frozen-state assurance

- CurrentBest raw/LF SHA: `f9ca672848ccffdfe56888d99bcdf5a9d7644062b9eec0cf0cdea13574931233`.
- `experiments/current_best.json` SHA: `789842d027703a66f083f3ff0ffc541172d7fd1c76819732075e04fbddb1c521`.
- `submission/main.py` raw/LF SHA: `789bb9bbd5122eb4891983e776a13777328e3e87736cbbc0b4bc86d13fc33f9b`.
- No candidate, package, upload, submission, or Kaggle write API was used.
