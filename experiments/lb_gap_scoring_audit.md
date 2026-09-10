# Kaggriculture scoring and runtime audit

## Official leaderboard semantics

Kaggle simulation competitions estimate each submission's Skill Rating as a Gaussian `N(mu, sigma²)`. Validated submissions start at `mu=600`, are matched against similarly rated agents, and update after episodes. A win raises the winner and lowers the loser; a draw pulls ratings together. The update magnitude depends on the expected result and uncertainty. Crucially, the amount by which an agent wins or loses does **not** affect Skill Rating. Source: [Kaggle competition documentation](https://www.kaggle.com/docs/competitions).

Therefore no exact numeric local leaderboard-score proxy is possible from this repository alone: the live opponent ratings, uncertainties, matchmaking sequence, and episode chronology are unavailable. The honest direct proxy is local W/L/T; raw coins and advantage are diagnostics only. A made-up mapping was deliberately NOT RUN.

## Why the old metric misled

Hardened went 20–20–0 against the refreshed current panel while keeping mean advantage positive, because 20 large wins coexist with 20 losses by only 5–10 coins. Margin-weighted local summaries call that strong; the official binary episode result counts every tiny loss fully.

## Dynamic-score evidence

Public empirical studies report that byte-identical submissions can display materially different ratings days apart: an age-matched comparison in the first study found 1839.0 versus 1237.8 for the same bytes submitted 9.7 days apart (-601.2). A second study's 2,880-paired-episode local pool ranked its v9 above v8 while the live leaderboard ranked v8 above v9; 12 of 15 pool opponents were saturated at either 0% or 100% win rate. A third study found median same-active-submission drift around -67 points/day at ratings >=2500 and -80/day at 2000–2500. These are observational—not official-formula or Shop0909-specific—sources: [Same File, 9 Days Apart](https://www.kaggle.com/code/dariushafshar/same-file-9-days-apart-1839-vs-1238), [18,144 episodes: local win rate ranks backwards](https://www.kaggle.com/code/dariushafshar/18-144-episodes-local-win-rate-ranks-backwards), and [Rating decay near the medal line](https://www.kaggle.com/code/dariushafshar/rating-decay-near-the-medal-line-80-pts-day).

## Runtime parity

Local historical validation used 1.32.6. Recent public notebooks explicitly install 1.32.7. The isolated 1.32.7 wheel has SHA-256 `2a1bb862ad2d6463080f80f6a766f46d94b53fd57168cfeddb9857fc3dbc4c8f`; the Kaggriculture engine source changed from SHA `fb9215c5e21a25243e2d13e75b3d70a79cf7d78fff150a90f1bb5eacf9ba2bcf` to `bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e`. The strategic diff is in the below-inventory price shapes for CARROT, TOMATO, and EGG (`hinge` with gain 8 replaces older defaults). Inspection found no change to action processing, market-order processing, hires, invalid-action behavior, reset, or randomization. Re-running the full diagnostic panel on 1.32.7 preserved the causal result; the Phase-A Hardened own-money delta versus 1.32.6 was only -34.25 and mean-advantage delta -12.0.

The public notebooks support 1.32.7 as the current public runtime expectation, but do not cryptographically prove the private competition server build. The version mismatch is real and should be fixed in future evaluation, yet it is weak evidence for the 2418.4 transfer gap.
