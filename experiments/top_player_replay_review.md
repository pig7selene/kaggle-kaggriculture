# High-rating public replay review

Date: 2026-08-11  
Frozen comparison agent: `agents/animal_c8_day12_land_day11.py`  
Submission status: `submission/main.py` was not changed and nothing was submitted.

## Executive conclusion

The sampled high-rating public population uses a remarkably consistent economic
schedule: mixed wheat/melon plus one cow and four sheep on day 0, a first extra
quadrant on day 6, eight cows by day 8, a second extra quadrant on day 10, a
14-hand workload peak, strawberry-heavy midgame, and wheat-heavy endgame. All
35 selected appearances ended with three quadrants; none bought the fourth.

This is strong evidence that this schedule is successful in the current public
population, but it is **not eight independent strategic discoveries**. The
action traces are close enough to indicate a shared policy family or common
template. The conclusions below therefore describe a successful public meta
family, not proven universal optima.

Directly copying its calendar into our cow-only engine failed locally. The
frozen C8 agent remained best at 182/8/2 over 192 held-out hard-league games.
The isolated third-quadrant version lost about 4,137 average coins, and both
more aggressive schedule ports regressed severely. The public schedule depends
on an early mixed-livestock cash engine and the ability to service nearly a full
three-quadrant farm; our present architecture does not reproduce either.

## 1. Corpus and method

The Kaggle leaderboard was captured on 2026-08-11. I selected eight teams from
the public top 10, selected at least four recent completed appearances for each,
and downloaded 25 unique replay JSON files. Direct games between selected teams
make some episodes appear for two players, yielding 35 selected-player
appearances.

| Player | Rating | Submission | Episodes studied | Appearances | Avg final money | Range |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| THUNDER THUNDER | 3216.7 | 55373222 | 91843967, 91853249, 91861609, 91870919 | 4 | 88,551 | 74,581–113,353 |
| Dmitry Larko | 3151.6 | 55412236 | 91843967, 91843968, 91853248, 91860677, 91869967 | 5 | 85,569 | 72,844–98,767 |
| Abracadabra | 3148.0 | 55391753 | 91856955, 91866168, 91866192, 91870920 | 4 | 68,643 | 52,866–83,503 |
| Ueddy | 3144.7 | 55407883 | 91843968, 91853247, 91853249, 91861610, 91870920 | 5 | 83,423 | 65,325–107,260 |
| Victor @ Tufa Labs | 3140.8 | 55417289 | 91860677, 91869963, 91870919, 91876492 | 4 | 102,852 | 94,884–106,890 |
| Erfan Eshratifar | 3103.0 | 55418684 | 91861609, 91865234, 91866168, 91867088, 91873681 | 5 | 80,281 | 55,167–105,323 |
| Valmorlee | 3100.9 | 55388560 | 91855065, 91864322, 91867069, 91869967 | 4 | 70,814 | 49,173–94,321 |
| Hak | 3097.1 | 55413692 | 91853240, 91856955, 91859757, 91869019 | 4 | 72,130 | 52,430–116,585 |

The complete unique episode list and selection metadata are in
`experiments/top_player_replays/manifest.json`. The 25 replay files are under
`experiments/top_player_replays/replays/`.

`analyze_top_player_replays.py` is the automatic analyzer. It reconstructs
unit and market actions using the installed environment's processing rules,
then extracts a 30-day timeline for every selected appearance. In particular,
it processes multi-unit sales at the changing per-unit market price rather than
using `quantity × initial price`. Predicted money matched every observed bank
transition: **zero reconstruction mismatches across all 25 replays**.

Machine-readable output is in `experiments/top_player_replay_analysis.json`.
The full 35-appearance day tables, including bank, farms, purchases, harvests,
sales/revenue, and capital spending, are in
`experiments/top_player_replay_timelines.md`.

## 2. Land purchase timing

| Player | First extra quadrant | Second extra quadrant | Final quadrants | Fourth bought |
| --- | ---: | ---: | ---: | ---: |
| THUNDER THUNDER | day 6 in 4/4 | day 10 in 4/4 | 3 in 4/4 | 0/4 |
| Dmitry Larko | day 6 in 5/5 | day 10 in 5/5 | 3 in 5/5 | 0/5 |
| Abracadabra | day 6 in 4/4 | day 10 in 4/4 | 3 in 4/4 | 0/4 |
| Ueddy | day 6 in 5/5 | day 10 in 5/5 | 3 in 5/5 | 0/5 |
| Victor @ Tufa Labs | day 6 in 4/4 | day 10 in 4/4 | 3 in 4/4 | 0/4 |
| Erfan Eshratifar | day 6 in 5/5 | day 10 in 5/5 | 3 in 5/5 | 0/5 |
| Valmorlee | day 6 in 4/4 | day 10 in 4/4 | 3 in 4/4 | 0/4 |
| Hak | day 6 in 4/4 | day 10 in 4/4 | 3 in 4/4 | 0/4 |

This is the cleanest shared signature: 8/8 players and 35/35 appearances used
exactly `[6, 10]`. Maximum productive occupancy was 70–75 per appearance and a
median 74–75 for most players. The fourth quadrant was universally skipped in
this corpus, probably because its 4,000-coin cost, seed cost, and service load
have too few remaining harvests to beat continued operation of three quadrants.

The timing was funded by cash flow, not idle starting cash:

| Day | Investment event | Median bank at day start | Median deed/animal investment | Same-day sales | Sales in current/prior two days | Main funding products |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 0 | 1 cow + 4 sheep | 3,000 | 2,400 | 0 | 0 | Starting capital |
| 5 | second cow | 543 | 400 | 994 | 1,970 | Fertilizer and first wheat |
| 6 | land + roughly 2 cows | 518 | 1,800 | 1,776 | 3,260 | First wool, fertilizer, wheat |
| 7 | roughly 2 cows | 26 | 800 | 2,947 | 5,731 | Wool, fertilizer, early milk |
| 8 | roughly 2 cows | 732 | 800 | 816 | 5,614 | Same cash cycle |
| 10 | second land | 2,165 | 2,000 | 9,298 | 12,076 | First melon cohort plus wool/milk/fertilizer |

The recurrent low bank balances through day 10 show aggressive reinvestment,
not conservative saving.

## 3. Cows, sheep, and structures

Every selected appearance bought one cow and four sheep and built five
pastures on day 0. No selected player used geese. Seven of eight players had a
median eight cows placed by day 8; most eventually reached nine, while Dmitry
and Erfan commonly reached ten. Sheep were at least four and sometimes scaled
later.

| Player | Cows d0 | d5 | d6 | d7 | d8 | Peak cows, median (range) | Peak sheep, median (range) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| THUNDER THUNDER | 1 | 2 | 2.5 | 6 | 7.5 | 8.5 (8–10) | 8 (4–9) |
| Dmitry Larko | 1 | 2 | 3 | 6 | 8 | 10 (9–10) | 4 (4–6) |
| Abracadabra | 1 | 2 | 3 | 6 | 8 | 9 (7–9) | 5 (4–5) |
| Ueddy | 1 | 2 | 3 | 6 | 8 | 9 (9–9) | 4 (4–4) |
| Victor @ Tufa Labs | 1 | 2 | 3 | 6 | 8 | 9 (9–9) | 5 (5–5) |
| Erfan Eshratifar | 1 | 2 | 3 | 6 | 8 | 10 (10–10) | 4 (4–4) |
| Valmorlee | 1 | 2 | 3 | 5.5 | 7 | 8 (6–9) | 4.5 (4–5) |
| Hak | 1 | 2 | 3 | 6 | 8 | 9 (9–9) | 4 (4–4) |

Fractional entries are medians across an even number of appearances. Apparent
animal-count drops and repurchases in some episodes indicate occasional escape
or placement failures. Those are not a strategic pattern worth copying.

The feed economy was mixed: the policies grew wheat but also bought large
amounts from the market for daily feed. They did not reserve all wheat-growing
capacity for animals. Fertilizer was collected and sold as a daily cash stream;
the replays do not support a general fertilizer-on-crops policy.

## 4. Labor scaling

All eight players reached 14 hands in every appearance. Labor reset daily and
tracked workload rather than staying at 14 continuously.

| Day/phase | Population median hands | Observed range | Workload event |
| --- | ---: | ---: | --- |
| 0 | 4 | 4–5 | Build/service five pastures and plant ten crops |
| 1–2 | 1, 2 | 0–2 | Animal service and watering |
| 3–5 | 3, 3, 3 | 2–4 | Wheat service/harvest and first strawberries |
| 6 | 4 | 3–4 | First expansion and animal scaling |
| 7–9 | 7, 6, 7 | 6–7 | Fill second quadrant and service 7–12 animals |
| 10 | 14 | 11–14 | Second land purchase, melon harvest, major planting |
| 11–15 | 10, 10, 8, 9, 9 | 8–13 | Complete the three-quadrant setup |
| 16–20 | 13, 9, 11, 13, 14 | 8–14 | Strawberry harvests and second melon cycle |
| 21–26 | 12, 10, 14, 11, 12, 12 | 10–14 | Strawberry-to-wheat rotation |
| 27–29 | 10, 10, 10 | 9–13 | Final harvest and liquidation |

Workers scaled with land and animals. The day-10 jump from seven to fourteen is
especially important: buying the third quadrant without doubling service
capacity is not the observed policy.

## 5. Crop phase pattern

The shared policy uses staged cohorts: major cohorts are internally fairly
synchronous, but new cohorts are added on days 0, 3–7, 10–12, and during later
replanting. It is neither one whole-farm synchronous monoculture nor continuous
fine-grained staggering.

| Day | Median visible crop counts (M/S/W) | Median productive tiles, including animals | Interpretation |
| ---: | ---: | ---: | --- |
| 0 | 5 / 0 / 5 | 15 | Capital-efficient wheat plus first melon payoff |
| 3 | 5 / 3 / 6 | 19 | Begin strawberry while retaining initial cohorts |
| 5 | 5 / 7 / 7 | 25 | Mixed cash bridge before land |
| 7 | 5 / 18 / 10 | 43 | Strawberry-heavy fill after first expansion |
| 10 | 12 / 31 / 13 | 67 | Second expansion after first melon sale |
| 12–15 | 14 / 36 / 13 | 74 | Stable midgame full-farm mix |
| 20 | 2 / 33 / 26 | 73 | Second melon harvest and transition begins |
| 21 | 0 / 29 / 30 | 72 | Wheat becomes co-dominant |
| 23 | 0 / 17 / 42 | 73 | Late wheat fill |
| 26 | 0 / 5 / 57 | 74 | Short-cycle endgame production |
| 28 | 0 / 0 / 27 | 40 | Stop non-paying planting and harvest down |
| 29 | 0 / 0 / 2 | 16 | Liquidation/service only |

The dominant sequence is:

- Days 0–2: wheat + melon opening.
- Days 3–5: wheat remains dominant while strawberry starts.
- Days 6–20: strawberry-heavy midgame with persistent wheat and a smaller
  melon cohort.
- Days 21–29: transition replacement slots to wheat and wind down.

No selected policy materially used carrot or tomato. Crop and land schedules
were almost invariant across opponents, so these replays provide little
evidence of active opponent-composition reaction despite the policies' strong
ratings.

## 6. Selling patterns

Products were usually sold on collection or at the next convenient shed visit.
Weighted harvest-to-sale lag stayed below one day:

| Product | Median lag in days | Range | Median season quantity sold | Median season revenue |
| --- | ---: | ---: | ---: | ---: |
| Melon | 0.21 | 0.11–0.54 | 114 | 15,960 |
| Strawberry | 0.83 | 0.68–0.93 | 274 | 24,668 |
| Milk | 0.44 | 0.33–0.78 | 223 | 13,190 |
| Wool | 0.60 | 0.18–0.75 | 132 | 13,904 |
| Wheat | — | — | 440 | 18,782 |
| Fertilizer | — | — | 236 | 12,529 |

The strawberry lag mostly reflects harvest logistics followed by day-start
sales, not multi-day speculation. Major sale timing was consistent: wheat near
day 4, wool near day 6, first milk around days 8–9, first melon around days
10–11, strawberry throughout the mid/late game, second melon around days
20–21, and a large wheat liquidation on day 29.

The agents frequently sold milk, wool, or melon into severe gluts—including at
the one-coin floor. Thus “sell quickly to finance compounding” is well supported
before day 10; “immediate selling is price-optimal all season” is not.

## 7. Common high-rating meta

| Pattern | Support | Typical timing/range | Likely economic reason |
| --- | ---: | --- | --- |
| Exactly three total quadrants | 8/8 agents, 35/35 appearances | Buy days 6 and 10 | Two expansions repay; fourth is too costly/late |
| Mixed livestock opening | 8/8, 35/35 | 1 cow + 4 sheep, 5 pastures, day 0 | Fertilizer plus early wool bridge the melon cash gap |
| Rapid cow ramp | 8/8 | 2 cows d5, ~3 d6, ~6 d7, ~8 d8 | Milk and fertilizer compound for most of season |
| Mixed wheat/melon opening | 8/8 | 5 wheat + 5 melon d0 | Wheat supplies early cash/feed; melon funds d10 |
| Strawberry-heavy midgame | 8/8 | Starts d3, dominant d6–20 | High-value repeated production after capacity exists |
| Wheat-heavy endgame | 8/8 | Transition d20/21 onward | Short cycle repays when premium crops no longer do |
| Workload-scaled labor | 8/8, max 14 in 35/35 | 4 d0, 7 d7, 14 d10 and peaks later | Services 70–75 productive tiles and animals |
| Fast selling/reinvestment | 8/8 | Premium lag 0.2–0.8 days | Prevents idle capital before expansions |
| No geese/carrot/tomato | 8/8 | Whole season | Inferior role in this policy/market family |

These are correlations in a likely related policy family. The corpus strongly
supports their joint success but cannot identify each component's standalone
causal value.

## 8. Player differences and uncertain findings

### Differences within the family

- Dmitry and Erfan tended to peak at ten cows; most others peaked at nine.
- THUNDER sometimes expanded sheep much more aggressively, reaching a median
  eight and a maximum nine; most players stayed at four or five.
- Victor's episodes produced the highest consistent average final money, but
  the same schedule also generated far lower money for other players because
  shared-market prices and opponents differed.
- Some agents lost and repurchased animals. This appears to be execution
  variance or recovery, not a distinct economic thesis.

### Uncertain observations

- Shared lineage makes “8/8 agents” less independent than the count suggests.
- The fourth-quadrant skip is universal here but not proven optimal against a
  different market population or a more efficient router.
- The exact 1-cow/4-sheep opening may be template-specific. Four sheep's early
  wool is clearly useful, but later wool often crashes to one coin.
- Exact day-based buying may hide a bank or state trigger whose outcomes happen
  to be deterministic in this family.
- Fast selling is necessary for the observed early reinvestment. Its superiority
  after the second expansion is uncertain.
- The invariant crop schedule gives no evidence that visible-opponent reaction
  is necessary for a 3,100+ rating, but it also does not prove reaction is
  useless against a more diverse future field.

## 9. Differences versus our current best

| Dimension | Public high-rating family | `animal_c8_day12_land_day11` | Likely consequence |
| --- | --- | --- | --- |
| Land | Extra quadrants d6 and d10; 3 total | One extra d11; 2 total | Much lower late capacity, but only if labor/routing can use land |
| Livestock opening | 1 cow + 4 sheep d0; cows ramp to 8 d8 | 8 cows purchased d12; no sheep | Misses fertilizer/wool cash bridge and several days of milk |
| Labor | Workload-varying, peak 14 | Two base/four animal workers; peak 8 after land | Cannot service public-meta scale |
| Crop opening | 5 wheat + 5 melon, strawberry from d3 | Phased melon opening | Longer wait for first reusable crop cash |
| Midgame mix | ~14 melon, 31–36 strawberry, 13 wheat | 12 base plots plus 12 adaptive land plots | Far less market-diversified output |
| Productive occupancy | 70–75 peak | 22.21 average in held-out league | Approximately one-third the operating scale |
| Selling | Usually within one day | Immediate crops, inventory-aware milk/fertilizer | Safer prices, but slower early reinvestment in some states |
| Bank usage | Repeatedly near zero through d10 | Protects cow/feed/land payback buffers | More robust locally; possibly under-compounds on Kaggle |

The capacity difference is real, but the local ablation shows it cannot be
valued as “53 missing tiles × crop profit.” Without enough early cash, animals,
workers, and routing throughput, extra land is a cost rather than production.

## 10. Top five likely weaknesses of our agent

1. **No pre-melon cash engine.** The strongest evidence is the day-0 sheep/cow
   opening in 35/35 appearances and its observed wool/fertilizer funding of the
   day-6 expansion. C8 waits for its day-10/11 melon cash and day-12 cows.
2. **Expansion is one cycle late and stops one quadrant early.** The public
   family has three quadrants by day 10; C8 has two from day 11. This is likely
   costly only after weakness 1 and the routing/labor constraints are fixed.
3. **The service architecture is capped too low.** Eight hands and 22 average
   productive tiles cannot reproduce the 14-hand, 70–75-tile economy. Simply
   hiring more is expensive and failed in the local port.
4. **The opening and midgame crop mix is too narrow.** Early wheat and day-3
   strawberry provide several cash cycles and diversify shared-market risk
   before/alongside melons.
5. **C8's capital protection may be too conservative for real opponents.** The
   public family sells rapidly and reinvests to near zero. The evidence supports
   more aggressive early reinvestment, but not blind late sales at floor prices.

Confidence is high for the joint schedule difference, medium for this ordering,
and low for isolated coin-cost estimates because the components interact.

## 11. Recommended next policy and hypotheses

Do not add another calendar flag to C8 first. Build a mixed-animal/full-farm
service architecture, then test this replay-derived policy as a joint but
ablatable schedule:

- **Day 0:** target five melons, five wheat, one cow, four sheep, five pastures,
  and four hands. Permit near-zero bank only after buying one day of feed and
  required seeds.
- **Days 1–5:** service all animals daily, sell fertilizer promptly, harvest the
  first wheat, introduce three strawberries around day 3 and reach roughly
  seven strawberries/seven wheat/five melons by day 5. Add cow 2 only if feed
  and service capacity are protected.
- **Day 6:** buy quadrant 2 when the deed plus 24 hours of feed, seeds, and labor
  are covered by realized cash; target three cows and four sheep. Test an exact
  day-6 rule against this safety-gated version.
- **Days 7–8:** ramp cows approximately 3→6→8 while filling the new quadrant
  strawberry-heavy with feed-support wheat. Target seven hands day 7 and six
  day 8.
- **Day 10:** after the first melon sale, buy quadrant 3, hire up to fourteen,
  and fill toward about 14 melon / 31–36 strawberry / 13 wheat. Gate on one-day
  feed plus planting/service cash, not a large passive reserve.
- **Days 11–20:** keep 8 cows and 4 sheep as the conservative core. Test a ninth
  cow around day 12–15 and a fifth sheep separately. Do not automatically copy
  THUNDER's larger sheep count because wool often hits the price floor.
- **Days 20–21:** harvest the second melon cohort and convert replacement slots
  to wheat. Do not dig productive strawberries merely to make the phase switch.
- **Days 27–29:** stop non-paying planting, return inventories, harvest all
  remaining product, and liquidate completely.
- **Quadrant 4:** skip by default. Allow it only if a conservative projection
  covers 4,000 coins, seeds, incremental labor, and feed before day 28; test as
  a separate hypothesis.
- **Selling hypothesis A:** immediate fertilizer/wool/milk/melon sales through
  day 10 to finance compounding, then inventory-aware sales.
- **Selling hypothesis B:** immediate sales all season, matching the public
  family. Compare A/B specifically; do not infer B from rating alone.

The next controlled implementation should isolate: (1) sheep cash bridge,
(2) mixed opening, (3) a router that can actually sustain 40 then 70 productive
tiles, and only then (4) the day-6/day-10 land schedule.

## 12. Local validation

Four agents were evaluated on fresh seeds 12600–12607 against all 12 opponents
in the frozen hard adversarial league, both seats: 192 games per candidate and
768 final games. Candidate actions were semantically validated every turn.

| Candidate | W/L/T | Score rate | Avg money | Avg advantage | Seed P10 advantage | Advantage SD | Confirmed land days | Avg productive tiles | Avg labor cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| **Current C8** | **182/8/2** | **95.3%** | **67,436** | **+27,445** | **+26,655** | 22,582 | 11 | 22.21 | 1,048 |
| C8 + third quadrant | 165/27/0 | 85.9% | 63,299 | +23,193 | +22,109 | 22,792 | 11, 15.09 | 23.13 | 1,048 |
| Replay land/labor only | 64/128/0 | 33.3% | 36,164 | -10,597 | -18,038 | 28,310 | 6, 16.43 (1.90 buys avg) | 22.61 | 4,258 |
| Replay full schedule, cow-only | 82/110/0 | 42.7% | 45,984 | +862 | -866 | 19,372 | 11.11, 12.11 | 28.12 | 5,855 |

Key controlled findings:

- The third quadrant added only 0.92 average productive tiles and reduced money
  by 4,137. It lost 2–14 to the C8 mirror with -4,462 average advantage.
- The land/labor port could buy its first land on day 6, but cow/seed/labor cash
  pressure delayed its second confirmed purchase to day 16.43 on average. It
  averaged only 6.21 peak cows, had one maximum cow escape, and stranded up to
  six valuable units. It is not submission-safe.
- The cow-only full schedule could not fund the public day-6 expansion; both
  purchases slipped to roughly days 11/12. It improved the local livestock
  proxy matchup to 13–3 and +5,029, but went 0–16 against C8 at -23,276 and
  regressed against five other strong generated policies.
- C8 had zero escapes and zero stranded value. The third-quadrant and full
  candidates also had zero; the land/labor candidate did not.

The complete per-game and per-opponent results are in
`experiments/top_player_replay_local_validation.json`.

**Promotion decision: none.** The replay evidence is strong enough to justify
building and testing a mixed sheep/cow compounding architecture, but the current
ports do not justify replacing C8 or preparing another Kaggle submission.

