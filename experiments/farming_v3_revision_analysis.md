# Farming Score V3 revision analysis

## Evidence boundary

The current public artifact is Kaggle notebook version **4**, last run **2026-09-05T14:29:18.4057716Z**. Its two cells contain a prose design note and the complete deterministic builder for the standalone agent. The extracted `main.py` matches the notebook's own SHA-256 assertion exactly: `d36ae976ad4a6316e6c1a27a5d04e9cc8e30300f21bdd31e749127c67a9311c4`.

Historical notebook source was not retrievable through the public/current endpoint. Version-addressed CLI/API attempts returned 403 or 404, so this report does **not** invent a V1→V4 code diff. Search-index snapshots mention 1819.4 for an older “Version 1 of 1,” 2273.6 as a V2 best, and either 2023.7 or 2703.9 around the current notebook. Those values are asynchronous public metadata, not controlled measurements, and are excluded from causal claims.

## What the current revision explicitly changes

The notebook describes itself as a deployment revision: it preserves a supplied two-route policy while translating a native C++ deployment into one pure-Python, single-file agent. The current agent adds two bounded state-dependent mechanisms around the replay tapes:

1. At turn 360 it selects route 1 for a BAKERY/fertilizer condition or a PET_CAFE/rival-plant condition; otherwise route 0.
2. At each 72-turn boundary it computes the selected block's planned spend, protects future feed/fertilizer/unplaced animals, and sells priced surplus only when cash is insufficient.

The strategic tape itself contains exactly two 719-turn routes. They are identical through turn 359, differ on every turn from 360–431 (72 turns), and are identical again from 432–718. This is a coherent block choice, not per-turn imitation or arbitrary splicing.

## Locally measured revision value

- Forced route 1 versus forced route 0, with identical openings through turn 359: **+926.9 own coins/game** over 32 continuations; 32/32 positive; bootstrap 95% CI **+755.2 to +1,109.5**.
- The route-1 advantage delta is smaller but positive overall: **+442.4**, bootstrap 95% CI **+260.2 to +603.8**. It is neutral/noisy against V2 specifically.
- The budget guard changed zero actions in 88 normal-cash V3-family appearances sampled in the raw/counterfactual panels. At $2,000 starting cash it fired in 8/8 raw-V3 appearances, always adding `SELL WHEAT 4` at turn 72. Its paired own-money effect averaged **+798**, but the eight-game CI crossed zero.

## Interpretation

The strongest supported innovation is the coherent route-1 midseason block, especially its lower fertilizer and labor spend. The published router's thresholds are reproducible, but this local panel found route 1 superior in every tested same-state continuation, including states where the published selector chose route 0. Thus the existence of the branch is supported; the necessity of its threshold boundary is not. The guard is sound defensive engineering for low-cash conditions, not the explanation for normal-setting strength.
