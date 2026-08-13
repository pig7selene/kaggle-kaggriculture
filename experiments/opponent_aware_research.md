# Opponent-aware architecture research

## Executive result

The opponent-awareness hypothesis was falsified for the current routed replay
architecture. Visible supply signals do predict what an opponent will sell, but
using those signals to alter our crops or hold inventory consistently reduced
money. The only positive ablation was relative-state hiring (O3), and its final
held-out gain was only 322 coins (+0.45%) with an exactly neutral direct result
against O0. That is far below the promotion standard.

`agents/router_replay_hands12.py` therefore remains the current best. Neither
`experiments/current_best.json` nor `submission/main.py` was modified, and
nothing was submitted to Kaggle.

The more important real-replay conclusion is structural: the four public losses
were already durable on days 6–8, before nuanced midgame crop or sale reactions
could plausibly recover them. The stronger opponents obtained earlier labor,
land, livestock, and cash turnover while the current agent was following its
own fixed ramp.

## Scope and evidence integrity

- Latest analyzed submission: `55429527`, public score `741.0` at capture.
- Newest public episodes: nine, all downloaded with our logs; 5 wins and 4
  losses.
- Prior high-rating corpus: 25 unique episodes, 35 selected appearances from
  eight players rated 3097.1–3216.7 at capture.
- Financial replay reconstruction: zero bank mismatches across all 34 replays.
- Opponent features: public farm state, public market state, and safely inferred
  market-history changes only. Opponent private inventory was not used.
- Local seeds were disjoint: development 12000–12002, selection 13000–13005,
  final confirmation 14000–14015, with both seats for every matchup.
- Full local league: O0 direct, six replay-derived archetypes, and all twelve
  retained hard adversaries (19 opponents total).
- Retained local evaluation: 2,648 full 720-turn games across development,
  selection, final confirmation, and the two bug ablations, plus a discarded
  76-game harness sanity run. Every retained game finished normally; semantic
  invalid-action count and reconstructed bank-mismatch count were both zero.
- Frozen-source SHA-256:
  `bac81a2099f3c4b7f97670a4e25d8cb0cc1c22fd23a41310096dd792b2f8f99b`.
- `submission/main.py` remained at SHA-256
  `edacba210dd55e9094e505e14fb57003610be92c43028007c31dbbabc1d78505`.

## 1. Real Kaggle failures

### Newest episodes

| Episode | Opponent | Seat | Result | Our money | Advantage | Durable gap day |
| ---: | --- | ---: | --- | ---: | ---: | ---: |
| 91942483 | Yuxiao Wang | 0 | Win | 102071 | +52296 | — |
| 91943392 | Joel Arias | 1 | Loss | 64458 | -6386 | 8 |
| 91944345 | SupremeWarrior108 | 1 | Win | 87914 | +50776 | — |
| 91945270 | DreamX5678 | 1 | Win | 76842 | +3677 | — |
| 91946207 | alexander kern | 0 | Win | 80732 | +8087 | — |
| 91947287 | Tran Huy Hoang1312 | 0 | Loss | 78991 | -13110 | 6 |
| 91948112 | AidenSong123 | 0 | Win | 59988 | +17977 | — |
| 91949046 | Bardia Bahadori | 0 | Loss | 53573 | -17835 | 7 |
| 91949996 | Abish Pius | 0 | Loss | 62392 | -25481 | 6 |

The median decisive-equity day was **6.5**. A decisive day is the first day on
which the eventual winner's public equity proxy was ahead by at least
`max(2500, 8% of the final gap)`, remained positive on at least 80% of the
remaining days, and was positive on the final three days. Bank-only durable
leads appeared on days 6, 7, 7, and 6 respectively.

### State at the decisive day

| Episode | Day | Opp bank edge | Opp quadrant edge | Opp hand edge | Opp productive-tile edge | Opp livestock edge | Opp cumulative-revenue edge |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 91943392 | 8 | +1069 | +2 | +5 | +3 | 0 | +7101 |
| 91947287 | 6 | -468 | 0 | +4 | +7 | +2 | +1333 |
| 91949046 | 7 | +400 | +1 | +3 | +25 | 0 | +1936 |
| 91949996 | 6 | +1504 | 0 | +4 | -2 | +1 | +13292 |
| **Mean** | **6.75** | **+626** | **+0.75** | **+4.0** | **+8.25** | **+0.75** | **+5916** |

All four losses were classified as opening/early compounding,
land/labor scaling, and livestock gaps. Two also had a material crop-economy
gap; one showed an additional execution gap. These labels overlap because the
mechanisms compound rather than occur independently.

### Episode-level mechanisms

- **Joel Arias:** bought the first extra quadrant immediately, reached three
  quadrants by day 8 and four by day 14, and combined five cows with seven sheep.
  Wool plus fertilizer supplied 51,539 coins of revenue. Our farm ultimately
  had more productive tiles, but the opponent had already banked the early cash
  lead and finished 6,386 ahead.
- **Tran Huy Hoang1312:** used eight hands from the opening, reached 13 cows plus
  three sheep, and produced 53,613 coins of milk/wool plus 13,068 fertilizer.
  The gap began before our first land-funded scale-up and finished at 13,110.
- **Bardia Bahadori:** began with two quadrants and roughly 40–50 productive
  tiles, then held eight cows and six sheep. Our late strawberry farm was larger,
  but livestock and earlier scale had already created a 17,835 final gap.
- **Abish Pius:** combined 12 cows, three sheep, 12 hands, and unusually large
  wheat market turnover. The replay reconstructed 198,641 coins of wheat-buy
  spending and 189,542 of wheat sales, so the sale number is turnover rather
  than self-grown wheat profit. Even after accounting for that cost, rapid
  cash recycling plus livestock created the largest loss, 25,481.

The two close wins reinforce the same point. DreamX5678 carried much larger
early land/livestock capacity, but our late liquidation narrowly recovered a
3,677 win. That is not a comfortable margin and does not show that the opening
is competitive.

### Diagnosis

The ~750 agent is primarily losing to **better fixed economic compounding**, not
to a lack of one-turn reactions. It commits scarce opening cash to its own cow
and crop ramp while stronger opponents use more labor and/or land immediately,
monetize livestock and staples sooner, and fund the next expansion before day
10. By the time our two deeds execute together around day 11, the real losses
already have a durable revenue lead.

## 2. Are high-rated public agents opponent-aware?

The answer from the available corpus is **mostly no**. It looks like a shared,
high-quality template family.

- All 35 selected appearances bought land on days 6 and 10.
- All ended with three quadrants and all peaked at 14 hands.
- Six of eight players had no hand-count variation across their replays.
- Victor @ Tufa Labs had exactly zero crop, planting, sale, or labor variation
  at the day level across four opponents.
- For Abracadabra, Ueddy, Erfan Eshratifar, Valmorlee, and Hak, mean pairwise
  daily planting differences were 0.05–0.12 tiles.
- THUNDER THUNDER and Dmitry Larko varied more in realized crop/sale counts,
  but expansion remained identical and the deviations were not systematically
  tied to the opponent.

After demeaning within player and day, correlation between opponent crop area
and the player's same-day planting deviation was:

| Crop | Within-player/day planting correlation |
| --- | ---: |
| Wheat | +0.001 |
| Carrot | +0.000 |
| Tomato | +0.000 |
| Strawberry | -0.088 |
| Melon | +0.016 |

The -0.088 strawberry value is weak correlation, not convincing reactive
behavior. Same-day selling correlations were also small: -0.086 wheat, +0.115
strawberry, and approximately zero for the other crops.

### Evidence classification

- **Strong evidence of reactive behavior:** none in the selected corpus.
- **Weak correlation:** slightly less strawberry planting when the opponent had
  more strawberry area; small sale-count differences in two players.
- **Fixed-template behavior:** land timing, three-quadrant ceiling, labor peak,
  opening crop mix, livestock ramp, strawberry midgame, wheat late game, and
  rapid liquidation.

Important caveat: the eight public names appear to share a closely related
policy lineage. The corpus is 35 appearances but not 35 independent strategy
designs. It is strong evidence about this top family, not proof that every
leaderboard agent is non-reactive.

## 3. Compact opponent model

The research layer was intentionally small and public-only. It tracked:

- opponent crop area and three-day maturity estimate by crop;
- opponent animal counts and three-day milk/egg/wool cadence;
- opponent quadrants, hands, productive tiles, and recent expansion;
- recent inferred product inflow from shared market inventory changes after
  subtracting our known sales;
- our relative bank, productive capacity, land, labor, and livestock state.

For each product, visible expected units plus a small area/recent-sales prior
were normalized into LOW, MEDIUM, or HIGH three-day supply pressure. Crop scores
used a smooth bounded multiplier (approximately 0.76–1.05); no crop was ever
forbidden. Only 25% of currently empty choices could deviate from the existing
phase prior in one planning pass.

Selling changes were similarly conservative. Before day 12, selling was
untouched so the first melon cash flow still funded reinvestment. Thereafter,
only premium products could be held, for at most one or two days depending on
pressure; overflow and day-28+ liquidation always overrode holding.

Relative reinvestment did not change the three-quadrant or cow ceilings. It
could append one affordable hire, up to the existing 12-hand ceiling, only when
the opponent led by at least 12 productive tiles, four hands, or one quadrant
plus seven productive tiles.

## 4. Which public signals are predictive?

Visible maturity is genuinely predictive of near-future sales even though the
reaction was not profitable. Correlations below are between a public signal at
day `d` and the same player's actual sales on days `d+1` through `d+3`, across
the 34-replay combined corpus.

| Product | Crop area | Maturing soon | Livestock due | Recent sales |
| --- | ---: | ---: | ---: | ---: |
| Wheat | +0.350 | +0.359 | — | +0.861 |
| Carrot | +0.702 | +0.702 | — | +0.079 |
| Tomato | +0.577 | +0.770 | — | +0.268 |
| Strawberry | +0.500 | **+0.863** | — | +0.782 |
| Melon | +0.308 | **+0.601** | — | -0.056 |
| Egg | — | — | **+0.989** | +0.939 |
| Milk | — | — | **+0.932** | +0.679 |
| Wool | — | — | **+0.878** | +0.446 |
| Fertilizer | — | — | — | +0.634 |

The best crop signal is growth-stage maturity, not raw area. Animal production
cadence is even more predictable. Recent sales are useful for persistent
producers but are partly autocorrelation rather than causal forecasting.

Thus opponent supply forecasting **works as prediction**. The experiments below
show that it does **not work as a profitable policy modifier** in the current
agent.

## 5. Controlled variants

| ID | Change from frozen O0 |
| --- | --- |
| O0 | None; `router_replay_hands12` frozen control |
| O1 | Opponent-aware crop scoring only |
| O2 | Opponent-aware premium selling only |
| O3 | Relative-state hiring only |
| O4 | Crop scoring plus selling |
| O5 | Crop scoring, selling, and relative-state hiring |

The router, persistent zones, animal specialists, animal schedule, land ceiling,
crop phase prior, and all unrelated economics remained identical.

## 6. Stronger replay-derived local league

Six replay-derived archetypes were added:

- fixed three-quadrant top-template reconstruction;
- aggressive strawberry scaler;
- fast land/high labor;
- mixed livestock-heavy scaler;
- early staple supply dump;
- rapid-selling early reinvestment.

The twelve retained hard adversaries were preserved, including early cows,
early land/high labor, C8 mirrors, livestock, high-labor, land-expander, phased
rotation, and older cow controls. O0 itself was the nineteenth direct opponent.

This is materially harder and more diverse than starter/random, but it still
does not fully reproduce the 3,100+ public agents. On final seeds O0 beat the
local fixed-template archetype 27–5 by only +981 average, whereas the actual
public agents often earned much more. The remaining simulator-to-leaderboard
gap must therefore remain an explicit limitation.

## 7. Development ablation results

Development used three seeds × 19 opponents × both seats = 114 games per
candidate.

| Candidate | W/L/T | Win rate | Avg money | Avg advantage | P10 | Money variance | Worst direct edge | Causal delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **O0** | **107/5/2** | **93.9%** | **80526** | **+33676** | **+771** | **576,983,305** | 0 | — |
| O1 crop | 100/14/0 | 87.7% | 79923 | +32493 | -189 | 539,636,403 | -1138 | -603 |
| O2 selling | 100/14/0 | 87.7% | 80271 | +33377 | -504 | 576,587,981 | -1004 | -255 |
| **O3 reinvestment** | **109/3/2** | **95.6%** | **81630** | **+34189** | **+970** | **553,233,512** | **0** | **+1105** |
| O4 crop+selling | 95/19/0 | 83.3% | 79621 | +32224 | -1387 | 547,454,392 | -1455 | -905 |
| O5 full | 94/20/0 | 82.5% | 80035 | +31948 | -1387 | 544,743,583 | -1455 | -490 |

### Component-level economy

Average successful crop sale revenue per development game:

| Candidate | Wheat | Carrot | Tomato | Strawberry | Melon |
| --- | ---: | ---: | ---: | ---: | ---: |
| O0 | 7120 | 1017 | 58 | 27458 | 12588 |
| O1 | 7633 | 1046 | 103 | 26805 | 12597 |
| O2 | 7086 | 1028 | 58 | 27337 | 12454 |
| O3 | 7116 | 964 | 58 | 28032 | 12581 |
| O4 | 7556 | 1059 | 125 | 26625 | 12464 |
| O5 | 7672 | 988 | 100 | 26788 | 12446 |

Selling and timing diagnostics:

| Candidate | Strawberry price | Melon price | Milk price | Avg holding turns | Exact pre-shock units | Crop switches | Hold events |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| O0 | 264.33 | 212.57 | 181.61 | 28.34 | 8461 | 0 | 0 |
| O1 | 265.42 | 212.49 | 181.68 | 28.51 | 8115 | 473 | 0 |
| O2 | 264.35 | 210.36 | 181.24 | 29.52 | 7363 | 0 | 4610 |
| O3 | 265.55 | 212.55 | 183.86 | 28.36 | 8325 | 0 | 0 |
| O4 | 265.00 | 210.26 | 181.46 | 29.75 | 7281 | 478 | 4529 |
| O5 | 265.71 | 210.36 | 183.47 | 29.90 | 7064 | 496 | 4695 |

“Exact pre-shock units” are successfully sold units followed by at least a 15%
market-price decline within 48 turns. O0's immediate policy sold more before
such declines than every awareness variant. The agent-side HIGH-pressure
instrumentation also recorded roughly 30,000 submitted units per aware
candidate, but that larger raw count did not translate into more confirmed
crash avoidance.

### Causal component evidence

- **Crop selection:** O1 made 473 actual pressure-caused plantings. On the 93
  paired games with a switch, money fell 740 and crop revenue fell 93 on
  average. It shifted revenue toward wheat (+512/game) but lost more strawberry
  revenue (-652/game). The model correctly anticipated supply but abandoned the
  phase prior too often for a lower-value crop.
- **Selling:** O2 created 4,610 hold events and increased estimated average
  inventory holding from 28.34 to 29.52 turns. It did not improve realized
  prices: strawberry was effectively flat (264.33 → 264.35), while melon fell
  212.57 → 210.36 and milk fell 181.61 → 181.24. Holding reduced crop revenue
  by 279 and total money by 255.
- **Relative reinvestment:** O3 added 152 hires. It improved development money
  by 1,105 and P10 by 199 without changing direct O0 behavior. The gain came
  from opponents that visibly scaled land/labor early.
- **Interactions:** O4 and O5 were worse than their components. Crop switches
  plus delayed sales reduced both capital velocity and premium-crop revenue.
  O5's switched development games lost 667 money and 299 crop revenue.

This is causal evidence against crop/selling awareness, not merely a lower
aggregate score.

## 8. Selection and held-out confirmation

Fresh selection seeds retained O0, O3, and full O5. O5 again lost 550 average
money; its 182 switch games lost 897 and 873 crop-revenue coins. O3 retained a
small +443 gain, so only O0 and O3 entered final confirmation.

Final confirmation used 16 unseen seeds × 19 opponents × both seats = 608 games
per candidate.

| Candidate | W/L/T | Win rate | Avg money | Avg advantage | P10 advantage | Money variance | Extra hires |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **O0 frozen** | **561/39/8** | **92.27%** | **72357.5** | **+30041.5** | **+323.0** | **547,164,413** | 0 |
| O3 relative hiring | 565/35/8 | 92.93% | 72679.5 | +30240.0 | +552.4 | 550,406,371 | 862 |

O3's paired gain was **+322.0 money (+0.45%)** and +181.2 crop revenue. It did
not meet either preferred threshold (10% money or +5,000 direct advantage).

The final O3 relative-state trace, averaged over the entire adversarial pool,
shows why the gate is sparse: O3 was slightly behind in bank on days 6 and 10
but already ahead in productive capacity; by day 21 it averaged a 9,733 bank
lead and 18.8 productive tiles of capacity lead.

| Day | Bank gap | Land gap | Hand gap | Productive gap | Livestock gap |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 6 | -320 | -0.21 | +1.59 | +1.03 | +2.42 |
| 10 | -659 | -0.21 | +1.25 | +2.45 | +4.92 |
| 15 | -2125 | +0.69 | +2.60 | +14.64 | +2.77 |
| 21 | +9733 | +0.64 | +4.37 | +18.80 | +2.69 |
| 28 | +24405 | +0.63 | +3.11 | +6.26 | +2.68 |

### Direct result versus `router_replay_hands12`

On the 32 final direct games, O3 and O0 produced exactly the same result:

- W/L/T: 12/12/8 from the labeled candidate perspective;
- average O3 money: 53,294.4;
- average O0 money: 53,294.4;
- average advantage: **0.0**;
- P10 advantage: -673.9.

This is expected: O3 only acts when substantially behind in visible scale, and
the symmetric O0 matchup never clears the gate. Neutrality is safer than a
regression, but it is not “clearly beats O0.”

### Replay-derived archetypes on final seeds

| Opponent | O0 W/L | O0 advantage | O3 W/L | O3 advantage | O3 delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| Fixed template | 27/5 | +981 | 27/5 | +981 | 0 |
| Strawberry scaler | 27/5 | +981 | 27/5 | +981 | 0 |
| Fast land/high labor | 28/4 | +5813 | 29/3 | +6809 | +996 |
| Livestock-heavy | 32/0 | +31987 | 32/0 | +32039 | +52 |
| Early supply dump | 27/5 | +3559 | 30/2 | +5063 | +1504 |
| Rapid reinvestment | 24/8 | +1651 | 24/8 | +1648 | -4 |

O3 is useful specifically against fast scale and early turnover. Its weakest
replay-derived P10 remained the rapid-reinvestment matchup at -3,595, unchanged
from O0. It did not introduce a new catastrophic opponent, but it also did not
solve the real day-6 compounding gap reliably enough to promote.

## 9. Red-team conclusion

The formal misleading-signal red-team gate was conditional on O4/O5 looking
strong. Neither survived development: O4/O5 had negative P10, lost all six
development direct games, and full O5 again lost ten of twelve selection direct
games. A larger red-team tournament would not be an honest use of confirmation
compute after the candidate had already failed.

The worst discovered exploit was simpler and stronger: a fixed high-quality
template can expose our reaction cost. O1 lost all six development direct games
to O0 by -1,138 average, O4/O5 lost all six by -1,455, and selection O5 lost
10/12 by -1,522. The opponent does not need to manipulate the model; it can
merely continue its profitable schedule while we switch crops or delay cash.

The existing inventory-holder and diversified-crop proxies remain available as
future misleading-signal tests if a later opponent-aware design first clears
the basic O0 and replay-archetype gates.

## 10. Small correctness-bug ablations

These were kept completely separate from O1–O5.

### Terminal milk cutoff

Extending the apparent animal-harvest cutoff by two hours changed no action in
16 paired games: money delta 0, total stranded milk 44 → 44, maximum three per
game. The hypothesized cutoff was not the cause, so
`router_replay_endgame_fix.py` is a rejected no-op experiment.

### Feed-before-expansion

Trace reconstruction found that scheduled herd expansion could occupy animal
specialists before every existing cow was fed. A local wrapper deferred
building/placement until the visible herd was fed.

| Variant | Games | Avg money | Direct advantage | Cow losses/replacements | Max/game | Stranded milk |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Source | 16 | 57222 | 0 | 18 | 2 | 44 |
| Feed-first fix | 16 | 66240 | -7951 | **0** | **0** | 45 |

The repair eliminated every replacement and raised its own paired gross money
by 9,018, but it lost directly by 7,951 because the changed shared-market flow
benefited the O0 opponent still more. This is another non-transitive result. It
is a valid correctness lead, not a safe promotion, and was not mixed into O3.

## 11. Direct answers

### 1. Why is the ~750 agent losing real Kaggle games?

It loses the opening capital race. On the decisive day, opponents average four
more hands, 8.25 more productive tiles, 0.75 more quadrants, 0.75 more livestock,
and 5,916 more cumulative revenue. The mechanism is earlier land/labor/livestock
turnover, sometimes amplified by high-volume staple trading—not primarily a
failure to react to a single visible crop.

### 2. At what day does the decisive gap usually appear?

Days 6–8, median 6.5 (mean 6.75) across the four losses.

### 3. Are top public agents measurably opponent-aware?

Not in this corpus. They are measurably template-like: identical land timing,
labor peak, phase transitions, and near-zero within-player planting response.

### 4. Which opponent signals are actually predictive?

Growth-stage maturity for strawberry/tomato/melon, animal production cadence
for milk/wool/eggs, and persistent recent sales. Raw crop area is weaker than
maturity. Fertilizer is best inferred from recent flow and animal count.

### 5. Does opponent crop-supply forecasting work?

As a forecast, yes: maturity-to-next-three-day-sales correlations reach 0.60–
0.86 for premium crops. As a decision policy, no: the resulting switches lose
money.

### 6. Does opponent-aware crop selection help?

No. O1 lost 603 average money in development; switched games lost 740 and crop
revenue fell 93. O4/O5 confirmed the negative effect.

### 7. Does opponent-aware selling help?

No. Holding did not improve realized prices, slowed cash, and cost 255 average
money alone. Combined with crop switching it was worse.

### 8. Does relative-state reinvestment help?

Slightly. O3 added gated hires and gained 322 held-out coins (+0.45%), mainly
against fast land/high-labor and early-dump archetypes. It was exactly neutral
against O0 and is too small to promote.

### 9. Which ablation is strongest?

O3 relative-state hiring. It is the only positive component, but it is not a
new best under the stated standard.

### 10. Direct result versus `router_replay_hands12`

O3: 12/12/8, +0.0 average advantage across 32 final games. O1/O2/O4/O5 all
lost directly during development/selection.

### 11. Performance against replay-derived high-rating archetypes

O3 ranged from +981 against the fixed/strawberry templates to +32,039 against
the local livestock-heavy archetype. Its useful deltas were +996 against fast
land/high labor and +1,504 against early supply dump. The local reconstructions
remain weaker than the actual 3,100+ replay economies.

### 12. Worst discovered exploit

A fixed profitable template is enough: reactive crop switches and holds make
us underperform while the opponent ignores us. The feed-first correctness fix
also revealed a shared-market exploit: increasing our production can improve
the opponent even more, producing a direct -7,951 despite higher own gross
money.

### 13. Is a new agent robust enough for another Kaggle submission?

**No.** O3 does not beat O0 directly or meet the magnitude threshold; O1/O2/O4/
O5 regress; and the safe-looking feed fix is non-transitively bad. The frozen
`router_replay_hands12.py` remains the strongest robust agent. The next research
priority should be a better fixed early-compounding schedule and capital engine
grounded in days 0–10 replay economics, not a larger opponent model.

## 12. Remaining weaknesses and next research direction

1. The opening is under-scaled relative to real winners before day 8.
2. Cow expansion can preempt feeding and cause one or two replacements; the
   obvious feed-first fix changes market interactions enough to lose directly.
3. About three milk units remain visible at termination; the apparent hour
   cutoff was not causal.
4. Replay-derived local archetypes still understate actual top-player cash flow,
   so positive league margins should not be interpreted as leaderboard parity.
5. The public top corpus has a shared-policy-family bias and only nine episodes
   from the newest submission.

A justified next milestone would reconstruct the strongest real days 0–10 cash
flows transaction-by-transaction, then ablate opening labor, sheep/cow mix,
staple turnover, and first-deed funding while keeping the proven territory
router frozen. Opponent awareness should remain dormant unless a later policy
first beats the fixed O0 template.

## Artifacts

- Replay diagnosis: `experiments/opponent_aware_diagnosis.json` and
  `experiments/opponent_aware_diagnosis.md`.
- Development: `experiments/opponent_awareness_dev_full.json` and `.md`.
- Selection: `experiments/opponent_awareness_selection_full.json` and `.md`.
- Final held-out: `experiments/opponent_awareness_final_full.json` and `.md`.
- Bug ablations: `experiments/opponent_endgame_bugfix_ablation.json` and
  `experiments/opponent_feed_first_bugfix_ablation.json`.
- Machine-readable synthesis: `experiments/opponent_aware_research.json`.
- Analyzer: `analyze_opponent_awareness.py`.
- Benchmark: `benchmark_opponent_awareness.py`.
