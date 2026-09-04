# Current Top-50 Strategy Mining and Distillation

## Decision

**Promote `agents/top50_distilled/top50_observable_portfolio.py` as the local research best.** This is not a Kaggle package or submission. `submission/main.py` is unchanged.

## 1. Actual baseline and preservation

| Item | Path | SHA-256 (raw = LF) |
|---|---|---|
| Frozen baseline | `agents/super_replay_v2/super_backbone_v2.py` | `c39d82b4f796271603e32ea8cb4b70261fbbe3d4e17940886caf5f5a6bd9adef` |
| Historical submission | `submission/main.py` | `a4f753d46a95e8d972098504f4930165e7e66f8ce292092e9ab090e4741310c3` |
| New research best | `agents/top50_distilled/top50_observable_portfolio.py` | `f9ca672848ccffdfe56888d99bcdf5a9d7644062b9eec0cf0cdea13574931233` |

No completed V5-V8 lineage existed. V3 and V4 were documented rejections, so V2 was the actual baseline.

## 2. Corpus freshness and coverage

Captured `2026-08-31T15:16:44.299729+00:00` from the current leaderboard: **50 teams**, **249 valid unique full episodes**, **408 elite appearances**, and **340 appearances after exact action deduplication**. A post-lock holdout added 22 unused episodes, two from every refined family.

| Deduplication level | Unique count |
|---|---:|
| Exact 719-action implementation | 340 |
| Field + non-SELL route implementation | 210 |
| Economic implementation | 22 |
| Economic family | 11 |

Fixed/bounded: **24**; phase-fixed: **10**; strongly state-dependent: **16**.

The newest server replays had 266 small local/server price-rounding divergences. Observed bank changes were treated as authoritative and the residual was explicitly recorded; it was never hidden.

## 3. Strategy families

| Family | Identity | Teams | Rank span | Land steps | Peak animals (C/S/G) | Hands | Avg replay money |
|---|---|---:|---|---|---|---:|---:|
| top50_family_01 | sheep_wheat_3q | 1 | 1-1 | 168/240 | 6/8/1 | 12 | 115,574 |
| top50_family_02 | sheep_wheat_3q | 1 | 2-2 | 150/265 | 6/7/0 | 12 | 100,072 |
| top50_family_03 | cow_wheat_3q | 38 | 3-50 | 150/265 | 9/5/0 | 12 | 83,841 |
| top50_family_04 | cow_wheat_3q | 1 | 5-5 | 150/238 | 3/3/0 | 12 | 96,983 |
| top50_family_05 | cow_wheat_3q | 3 | 6-36 | 150/265 | 6/4/0 | 12 | 88,454 |
| top50_family_06 | sheep_wheat_3q | 1 | 14-14 | 150/265 | 6/11/0 | 12 | 64,234 |
| top50_family_07 | cow_wheat_3q | 1 | 15-15 | 150/265 | 11/6/0 | 12 | 92,066 |
| top50_family_08 | cow_carrot_3q | 1 | 18-18 | 121/199 | 14/3/1 | 12 | 99,627 |
| top50_family_09 | cow_strawberry_3q | 1 | 26-26 | 120/253 | 12/2/0 | 12 | 91,989 |
| top50_family_10 | sheep_wheat_3q | 1 | 40-40 | 150/265 | 8/9/0 | 12 | 85,639 |
| top50_family_11 | sheep_wheat_3q | 1 | 47-47 | 150/265 | 4/10/0 | 12 | 107,075 |

A broad copied cow/wheat family contains 38 teams, but rank 1, rank 2, rank 5, rank 18, rank 26, and several livestock-scale variants remain economically distinct.

## 4. Consensus and rank contrast

Equal-weighting each family rather than each team gives:

- **three_or_more_quadrants**: 11/11 families (100%).
- **first_land_by_day7**: 11/11 families (100%).
- **second_land_by_day11_5**: 11/11 families (100%).
- **twelve_or_more_hands**: 11/11 families (100%).
- **melon_and_strawberry_waves**: 11/11 families (100%).
- **terminal_liquidation_after_step700**: 11/11 families (100%).
- **mixed_cow_sheep**: 10/11 families (91%).
- **eight_or_more_cows**: 5/11 families (45%).

Top 1-10 differs mainly through diversity and livestock balance, not universal earlier land: median land timing is still step 150/265. The Top-10 median peak is 6.5 cows versus 9 lower down, suggesting that more cows are not monotonically stronger.

## 5. Adaptive behavior

The strongest observable divergences involve current wool/milk/strawberry prices, current productive tiles, current hands, and bank. These are hypotheses, not proof. Representative state-dependent teams:

| Rank | Team | First divergence | Opening agreement | Midgame agreement |
|---:|---|---:|---:|---:|
| 1 | tetsuya | 73 | 93.4% | 16.9% |
| 2 | Yusuke Hayashi | 73 | 85.2% | 40.7% |
| 5 | Subramanya N | 24 | 67.3% | 16.7% |
| 7 | zhyphirus | 73 | 89.5% | 35.7% |
| 14 | washamba_bots | 144 | 95.0% | 50.0% |
| 15 | Driz Lo | 73 | 78.7% | 48.1% |

No deployable branch uses seed, replay ID, rank, future prices/shops/actions, or final result.

## 6. Raw parents and causal tests

| Candidate | Serious paired W/L/T | Paired own-money delta | P10 | Safety note |
|---|---:|---:|---:|---|
| dmitry_safe | 34/8/0 | 7,087 | -6,202 | research parent |
| hanserong_safe | 26/16/0 | 6,321 | -5,665 | research parent |
| redblack_safe | 24/18/0 | 5,259 | -7,868 | research parent |
| observable_portfolio | 34/8/0 | 7,669 | -1,807 | locked clean final |

The raw Dmitry route first showed +5,323. Its recurring day-28 cow escape was traced to a worker standing on the cow with wheat but collecting fertilizer at step 686. Broad rescue was catastrophic; the exact repair preserved economics. The development D/H/R portfolio oracle was +8,536, enough to justify selection.

## 7. New architecture

Four candidate agents were built: three complete, economically distinct elite parents with only exact safety repair (Dmitry 8-cow/4-sheep, Hanserong 7-cow/6-sheep, and redblack 9-cow/5-sheep), plus the observable portfolio selector. A V2 phase-transplant candidate was rejected before implementation because checkpoint crop/livestock state was not compatible with any winning parent; previous V3/V4 evidence already showed that such splices erase the route's coordinated capital plan.

All parents PASS at step 0. At step 1, before their first economic divergence, the candidate selects one coherent complete economy from the opponent's visible bank and hand count:

- dominant-family idle opening -> redblack 9-cow/5-sheep economy
- rank-1/rank-5-like opening -> Hanserong 7-cow/6-sheep economy
- otherwise -> Dmitry 8-cow/4-sheep economy

This is selection among complete coordinated plans, not route splicing.

## 8. Locked final unseen

| Metric | V2 | New candidate |
|---|---:|---:|
| Games | 132 | 132 |
| W/L/T | 52/48/32 | 107/25/0 |
| Average money | 89,167 | 95,146 |
| Average advantage | 9,576 | 17,617 |
| Advantage P25 | -962 | 2,520 |
| Advantage P10 | -14,493 | -2,027 |
| Advantage P5 | -23,795 | -8,798 |
| Worst advantage | -29,751 | -21,303 |
| Actual animal escapes | 0 | 0 |

Paired own-money delta: **+5,979**; median **+2,964**; P10 **-8,029**; P5 **-10,620**; worst **-39,825**. Net-advantage delta: **+8,040**.

Direct V2: **62/2** (fixed 30/2; natural 32/0 at 100,138 average money and +7,734 advantage). Unseen Top-50 families: **21/23** at +12,592 average advantage, versus V2's 12/32 at -1,020. Legacy/adaptive pool: **24/0** at +51,076; its paired own-money delta versus V2 was -3,094, so this win pool is competitive rather than an own-income gain.

## 9. Economic attribution

On the focused 16-condition attribution panel, own money changed -150, opponent money -7,790, and net advantage +7,640. The main positive revenue shifts were fertilizer, wheat, strawberry, carrot, and melon; milk/wool revenue fell. The candidate spent less on labor but cycled much more wheat/fertilizer product capital. This identifies the gain primarily as **market + capital value**, with a smaller production-mix contribution—not a simple output increase.

## 10. Ablation

- Broad risk feeding: rejected (route desynchronization).
- Exact deadline repair: preserves the +5k parent signal and yields zero actual final escapes.
- Static Dmitry -> full selector adds +582 paired money on the serious gate.
- Removing coherent parent identity through blind phase splicing was not attempted because checkpoint livestock/crop states are incompatible.

## 11. Remaining weaknesses

1. Paired own-money P10/P5 remain negative, despite substantially better competitive tails.
2. The candidate wins only 21/44 unseen elite-family games; family 08 contributes most of the elite mean.
3. Step-1 selection can react to opening identity but not future shop RNG; natural own-money tails remain market-sensitive.
4. Several state-dependent Top-50 agents vary later market actions in ways not safely transplantable into fixed route state.
5. The candidate is a local research architecture with project-local route assets, not a packaged standalone submission.

## 12. Promotion and next step

The local research promotion gate passes on +5k paired mean, 96.9% direct V2 wins, clean natural direct results, major competitive-tail improvement, and perfect safety. It does **not** pass a positive paired-own P10 criterion, so this should be treated as a stronger research best rather than a low-risk final solution.

Recommended next step: diagnose the eight losing elite families using the locked candidate's real branch choice and build a later, state-compatible market residual—not another broad route splice. Do not package or submit until that tail work is requested.
