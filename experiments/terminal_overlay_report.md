# Terminal overlay sprint report

1. **Public variants inspected:** Most Powerfull Route, Market-Smart Farming, Seven-Turn Rescue.
2. **Exact changes:** all use a physical 712–718 worker planner, retain 712–717 markets, and liquidate actual stock at 718. Most/Seven are byte-identical. Market-Smart expands late-actor two-stop proposals and preserves one late near-shed proposal. Every state-specific primitive change is recorded in `terminal_overlay_source_diff.json`.
3. **Candidates tested:** 6 (three source candidates plus D/E/F minimal bounded variants).
4. **Frozen known near-mirror:** 0/20/0 (W/L/T).
5. **Best known near-mirror:** 12/0/8.
6. **Known loss→win:** 12.
7. **Known loss→tie:** 8.
8. **Known win→loss:** 0.
9. **Known overall mean own-money delta:** +9.700.
10. **Known overall mean advantage delta:** +11.600.
11. **Gain source:** exclusively additional terminal fertilizer collection, return, drop, and sale; certified deltas are 7–11 units in the near-mirror panel.
12. **Fresh near-mirror:** 8/0/8 versus Frozen's 0/16/0.
13. **Fresh rate:** 50% raw wins, 75% tie-adjusted match score, 100% non-loss.
14. **Non-mirror regression:** none; both Frozen and selected are 16/0/0. Selected mean own delta +11.375.
15. **Runtime errors:** 0.
16. **Agent errors:** 0.
17. **Livestock escapes:** 0.
18. **Selected path:** `agents/shop_router_0909_terminal/main.py`.
19. **Selected SHA:** bundle `16f111f8a345da71ae56069bf170ce5c670847993f4ef05054ed1f6eb000bec3`; entrypoint `495bfa4825c9e58638e804aeeb62a9537826f6d4d869222815e1bbeefd84d3dc`; policy `404da11becd74f31a1590a844b4594f4b53a54bebc10b9489e7f0cc7e8448fdb`.
20. **current_best.json:** updated after lock and validation.
21. **Archive:** `submission/shop_router_0909_terminal.tar.gz`.
22. **Archive SHA:** `cc458128e8e51b5bc1047d7b391ecad358020aa4511a8b45e6b9f26360ada1a0`.
23. **Packaging equivalence:** 10 paired conditions / 20 runs; action mismatches 0, final-state mismatches 0, final-money mismatches 0.
24. **Kaggle submission:** none. Archive is ready for manual upload only.

Decision: **ADOPT → PACKAGE → STOP.** The old frozen source and old submitted archive remain unchanged.
