# Shop Router 0909 Hardened — final packaging report

## Decision

Packaging passed every success criterion. The verified manual-upload artifact is `submission/shop_router_0909_hardened.tar.gz`; no Kaggle submission was performed.

## Required answers

1. **Frozen research-best path:** `agents/shop_router_0909_hardened/main.py`.
2. **Frozen research-best SHA-256:** `da5c6df2c71128ce1372a5adaf6d4859f5758e7854b399d6ff634fbca666d8a2`.
3. **Research SHA unchanged:** yes; the before and after hashes are identical.
4. **Original submission SHA-256:** `789bb9bbd5122eb4891983e776a13777328e3e87736cbbc0b4bc86d13fc33f9b`.
5. **Final submission paths:** `submission/main.py` plus the manual-upload archive `submission/shop_router_0909_hardened.tar.gz`.
6. **Final hashes:** `main.py` `4a188ceaedaa5e37c2216c803517314a2cb2fd780a5bb65956ca016cf278c803`; archive `26e7d39eb1df83af7c595167298ad8f3d61afce76e216cd1e25d6416bb791046`.
7. **Static representation:** assets were kept separately. The archive contains root-level `main.py`, byte-identical `actions.json`, `LICENSE.txt`, and `NOTICE.md`.
8. **Asset hashes:** actions `17d503f2fd20d59f9c0f14024d1e74a8add8bb9b5561d4d908b45deecb5495ef`; license `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`; notice `51ef4107c99caae6b11f199a5d79015ada7fd9e1eb51201aa72bb3e4d5aea17c`.
9. **Absolute/local paths removed:** yes; packaged source contains no `/Users/`, username, or repository path token. It resolves `actions.json` relative to its own code filename.
10. **Import test:** passed in a clean process using `from submission.main import agent`.
11. **Clean-working-directory test:** passed for both archive import and a complete extracted-package game; action and final-state hashes matched the repository package.
12. **Multi-game reset:** passed four games in one process without module reload; every trace and final state matched a fresh import.
13. **Both seats:** passed throughout route equivalence, Plan-10 regression, reset, and smoke tests.
14. **Plans tested:** all 13 plans, including the universal plan-2 tail.
15. **Equivalence games:** 42 paired games: 26 forced-plan/both-seat games plus 16 natural games across four opponents.
16. **Plan-selection mismatches:** 0.
17. **Action mismatches:** 0 across 30,198 identical-observation calls.
18. **Final-state mismatches:** 0.
19. **Final-money mismatches:** 0.
20. **Plan-10 step 360:** preserved exactly as `PICKUP WHEAT 4` in both seats.
21. **Historical sheep failure:** remains fixed; target sheep was fed at observation 370 and escaped in 0/2 historical-condition games.
22. **Runtime exceptions:** 0 in equivalence, clean-directory, reset, and smoke gates.
23. **Agent exceptions:** 0.
24. **Final smoke league:** 32/0/0; mean own money 84,124.5, mean advantage +25,332.8, worst advantage +3,893; zero escapes.
25. **Ready artifacts:** yes. Upload `submission/shop_router_0909_hardened.tar.gz` manually without editing.
26. **Kaggle submission:** none; no API, CLI submit command, notebook submission, or upload was used.

## Packaging transformation

The Exact public source was copied without strategic refactoring. Only its deployment entry point was composed with the already-locked Plan-10 wrapper, and the Apache/attribution header was added. Reversing those two packaging-only edits reconstructs Exact `main.py` at SHA-256 `d6d74997dc5b483db63d8e39cafa1afeec0f366824e75107e109123f111e866b`. The action payload, license, and notice are byte-identical to their frozen sources.

The first separate-environment diagnostic produced equal actions and money but differing random weed states in nine games. It was correctly rejected as an equivalence method because the observations were not identical. The final gate invokes ResearchBest and Submission on the same 30,198 observations in one environment, records both actions, and reports zero differences.
