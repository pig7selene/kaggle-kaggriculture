# Leaderboard-driven economic breakthrough study

Date: 2026-08-12  
Real leaderboard baseline: `agents/opening_public_front_cow8_day6.py`  
Decision: **no promotion**  
Submission: unchanged; nothing submitted

## Executive conclusion

The missing leaderboard mechanism is **yield-complete crop capital timed to an
investment window**, not another movement-priority tweak.

Our 803.5 agent plants the correct five-melon opening, but its router offers
peak-day `HARVEST` before the last profitable `WATER`. In a representative real
loss, all five melons reached five units on day 10, yet the agent harvested
them in partial batches before watering and realized only **15 units**. A
representative top template waters the same five-tile cohort on day 10 and
harvests **30 units**. The same ordering truncates our first wheat wave: about
14 units in the representative loss versus 20 in the public template.

That is a capital error, not just a yield statistic. The public five-melon wave
realizes about **7.4k** on day 10, pays for the second deed, and immediately
plants the next 13-melon / strawberry / wheat cohort. Our median day-10 crop
revenue is **4,182 versus 8,563**, productive tiles are **58 versus 67**, and
bank is **2,885 versus 4,887**. By day 20 the crop-revenue gap is 8,881 versus
37,143. Extra animal revenue cannot close it.

The strongest new branch, `agents/leaderboard_r3_cow6_capital.py`, combines:

- peak-yield completion before destructive harvest;
- a day-10 conversion into the replay-derived second crop cohort;
- six cows, freeing animal-service and feed capital for crops;
- the previously isolated action-value scheduler.

On 72 held-out games it adds **7,683 own money on unseen real replay traces**,
**12,159** in fixed-shop direct games and **13,261** under natural RNG, raises
full crop revenue by **13,127**, and cuts the day-10–20 critical miss rate from
2.42% to 1.22%. It has zero invalid actions, livestock losses, or stranded
value. Nevertheless it still loses 14/16 held-out replay matchups, loses every
Filip/Amer/Yankang trace, and its paired-delta P10 is **-5,805**. It therefore
does not meet the requested promotion standard. The real 803 baseline remains
the leaderboard baseline and `experiments/current_best.json` is unchanged.

## 1. Exact public baseline mapping

| Public score | Submission ID | Submission SHA-256 | Source agent (SHA-256) | Main architecture |
| ---: | ---: | --- | --- | --- |
| 709.6 | 55429527 | `edacba210dd55e9094e505e14fb57003610be92c43028007c31dbbabc1d78505` | `agents/router_replay_hands12.py` (`bac81a2099f3c4b7f97670a4e25d8cb0cc1c22fd23a41310096dd792b2f8f99b`) | Three quadrants around day 11, persistent-zone router, nine cows, 12 hands |
| **803.5** | **55435253** | `3196b73fc2f46e25284b773136b530e2aacbaad2ba8a9dffdfce66472fe2a0fb` | **`agents/opening_public_front_cow8_day6.py`** (`3ede0041921010b0136abb538395faa5951e9af1fb9b76be41467246885da6a8`) | Public 1-cow/4-sheep opening, deeds day 6/10, eight cows by day 8, 14 hands, scalable router |
| 798.0 | 55438811 | `d0fbf1205a7e27f8294f1f9a06afd581cfb3e926f8ab88acc0b7f7a8b72620cf` | `agents/lifecycle_lc_combined.py` (`db12d32912843e012c3dfd7e84c2c384ce998694bf02b98fc7e1fe9189c17e78`) | 803 opening plus recurring strawberry harvest and stationary harvest→replant chaining |

The blank-description newest submission is 798.0, not 793. The current local
research pointer names the lifecycle agent, but the best observed Kaggle score
is the 803.5 source above.

## 2. Replay evidence and reconstruction coverage

- 35 public games for the 709.6 submission.
- 44 public games for the 803.5 submission.
- 49 public games for the 798.0 submission.
- 25 high-rating public replays containing 35 selected appearances from eight
  teams rated 3,097–3,217 when captured.
- **153 unique episodes** in the combined corpus.
- Every bank transition was reconstructed from unit prices and action effects:
  **zero financial mismatches**.

Selected high-rating teams were THUNDER THUNDER, Dmitry Larko, Abracadabra,
Ueddy, Victor @ Tufa Labs, Erfan Eshratifar, Valmorlee, and Hak. The full
episode/player manifest is in `experiments/top_player_replays/manifest.json`;
the new submission corpora are under `experiments/leaderboard_replays/`.

### Population trajectory checkpoints (medians)

Each tuple is `bank / cumulative revenue / crop revenue / animal revenue /
quadrants / hands / productive tiles / harvest actions`.

| Day | 803 baseline | 798 lifecycle | High-rating public |
| ---: | --- | --- | --- |
| 2 | 551 / 694 / 0 / 694 / 1 / 2 / 15 / 0 | 548 / 694 / 0 / 694 / 1 / 2 / 15 / 0 | 181 / 496 / 0 / 496 / 1 / 2 / 15 / 0 |
| 4 | 821 / 1,657 / 0 / 1,657 / 1 / 3 / 14 / 5 | 819 / 1,655 / 0 / 1,655 / 1 / 3 / 14 / 5 | 543 / 1,458 / 0 / 1,458 / 1 / 3 / 19 / 5 |
| 6 | 27 / 4,749 / 255 / 4,493 / 1 / 4 / 23 / 9 | 32 / 4,741 / 256 / 4,485 / 1 / 4 / 23 / 9 | 26 / 4,242 / 542 / 3,700 / **2** / 4 / 27 / 9 |
| 8 | 7 / 6,880 / 255 / 6,622 / 2 / 6 / 40 / 10 | 4 / 6,868 / 256 / 6,613 / 2 / 6 / 40 / 10 | 258 / 8,080 / 803 / 7,252 / 2 / 6 / **50** / 16 |
| 10 | 2,885 / 15,451 / 4,182 / 11,247 / 3 / 14 / 58 / 23 | 2,685 / 15,315 / 4,181 / 10,930 / 3 / 14 / 58 / 23 | **4,887 / 19,769 / 8,563 / 11,204 / 3 / 14 / 67 / 27** |
| 11 | 3,456 / 17,813 / 5,405 / 12,436 / 3 / 10 / 61 / 27 | 3,189 / 17,314 / 5,414 / 12,191 / 3 / 10 / 65 / 27 | **6,447 / 21,347 / 8,599 / 12,399 / 3 / 10 / 73 / 31** |
| 12 | 5,185 / 19,764 / 6,733 / 13,176 / 3 / 10 / 62 / 33 | 4,708 / 19,189 / 6,648 / 12,890 / 3 / 10 / 67 / 32 | **6,993 / 23,106 / 9,005 / 13,613 / 3 / 10 / 74 / 44** |
| 15 | 9,430 / 25,181 / 7,018 / 18,380 / 3 / 9 / 53 / 55 | 9,324 / 25,214 / 7,259 / 18,180 / 3 / 9 / 64 / 60 | **16,386 / 34,014 / 11,394 / 22,677 / 3 / 9 / 74 / 69** |
| 20 | 25,242 / 46,250 / 8,881 / 36,841 / 3 / 14 / 66 / 89 | 33,490 / 52,786 / 15,013 / 37,678 / 3 / 14 / 67 / 143 | **44,768 / 70,926 / 37,143 / 31,450 / 3 / 14 / 73 / 168** |
| 25 | 46,648 / 70,663 / 24,448 / 46,415 / 3 / 12 / 62 / 154 | 58,646 / 80,744 / 34,114 / 49,977 / 3 / 12 / 69 / 263 | **66,487 / 94,020 / 49,104 / 40,590 / 3 / 12 / 73 / 293** |
| 29 | 70,922 / 96,169 / 42,198 / 50,862 / 3 / 10 / 25 / 222 | 77,641 / 104,143 / 43,710 / **61,921** / 3 / 10 / 21 / 346 | **81,668 / 111,636 / 59,547** / 46,680 / 3 / 10 / 16 / 386 |

The top population is already five productive tiles ahead on day 4 and ten
ahead on day 8. The irreversible monetary divergence is usually the first crop
conversion: the median durable revenue lead in both our 803 and 798 losses is
day 11.

## 3. Loss taxonomy: decision → cash → investment → compounding

Across the 20 losses of submission 55435253, durable revenue leads begin most
often on days 11 and 17 (four losses each), with additional clusters on days
7–10. The mechanisms are:

1. **Peak-yield destruction / capital timing.** Early `HARVEST` sacrifices the
   final watering bonus, immediately halves some first crop waves, then leaves
   less cash for deed, seed, and animal orders.
2. **Cohort scale and continuity.** Strong agents turn a 30–60 unit melon wave
   into a fully planted second cohort. We finish day 10 with 58 productive
   tiles and only about 1–2 melons; the top median is 67 tiles and about 12.
3. **Livestock opportunity cost.** Nine cows maximize animal revenue but spend
   field actions, feed, and capital that high-throughput crops can compound
   faster. Six cows are locally stronger once crop yield is preserved.
4. **Market turnover/liquidity.** Pedro repeatedly cycles wheat. It creates a
   real spread in his replay but is interaction-dependent and did not transfer
   when copied.
5. **Second and late crop waves.** Several losses become durable only on days
   15–23, when opponents retain 70+ productive tiles or execute strawberry,
   melon, then wheat liquidation waves while ours repeatedly falls toward the
   low 50s.

## 4. Replay-derived economic archetypes

| Archetype | Source episode | Concrete mechanism | Cash → reinvestment |
| --- | ---: | --- | --- |
| Public fixed-template scaler | Teddy 92092507; Victor 91869963; Hak 91853240; Sagar 92180626 | 1 cow + 4 sheep, 5 wheat + 5 melon; deed d6/d10; 30-melon d10 sale; 14 hands; 13–14 melon midgame then wheat close | Wool/fertilizer d6–7 → deed + cows; milk/wool + full-yield melon d10 → deed + 40+ seeds |
| Jayveer melon burst | 92008833 | Starts 10 melons with lighter animals; 42-melon synchronized sale d11 | 10,188 melon + 415 fertilizer + 160 strawberry → 2,000 deed + 2,900 for six cows/one sheep in hours 0–3 |
| Lucas four-quadrant burst | 92009080 | Four-cow opening; two milk waves; 60 melons d11 | 13,933 melon + 2,675 milk → 4,000 fourth deed + eight sheep, then 80+ productive tiles |
| Alexander cow/melon | 92011750 | Four cows fund first deed; 42 melons + 12 milk d11, then 24 melons d12 | 12,491 d11 sale → 2,000 second deed; next 4,896 sustains planting |
| Pedro wheat turnover | 92010768 | Alternating 12–20 wheat buy/sell orders after d7; mixed carrots/wheat/strawberry | 3,066 wheat bought for 126,975; 3,206 sold for 133,609; ~6,634 spread funds liquidity, but includes 379 farmed wheat |

These are mechanisms, not interchangeable recipes. The top public family is
the most repeatable evidence: all 35 selected appearances buy land on exactly
days 6 and 10, all peak at 14 hands, and all use the same phase family. Their
peak cow count ranges 6–10 (median 9); therefore “six cows” is a controlled
capacity hypothesis, not the public consensus.

## 5. Jayveer's burst, exactly

- Day 0: 10 melons, five wheat, one strawberry; two cows/two sheep after the
  first purchases settle. This sacrifices early wool capacity for a much
  larger premium one-time cohort.
- Days 0–9: the melon cohort is serviced as one capital asset. A 12-milk sale
  for 2,112 at day 9 hour 22 pays for the first deed and another sheep.
- Day 10: 42 melon units are harvested and held overnight. Holding is not a
  price-optimization trick; it synchronizes cash with the next orders.
- Day 11 hour 0: 42 melons sell for 10,188 (average 242.57), plus fertilizer,
  strawberry, wheat, and wool. The second deed is purchased immediately.
- Day 11 hours 2–3: one sheep and six cows are purchased for 2,900.
- Days 12–20: about 13 melons, 34 strawberries, and 13 wheat remain in
  production. Full crop revenue reaches 69,839 versus our 39,965 in the exact
  comparison; Jayveer's animal revenue is lower, 35,424 versus 42,968.

The immediate day-11 revenue gap is 4,574; it grows to 6,338 by day 20. The
important causal chain is `large full-yield cohort → synchronized sale → deed
and six animals → high-value second cohort`, not “hold melons” by itself.

## 6. Pedro's wheat cycle, exactly

Pedro opens with two cows/two sheep and begins ahead in realized revenue. Day
7 wool (12 units, 2,178) funds the first deed plus another cow/sheep. Day 9
milk (12 units, 1,881) funds another cow. From day 7 hour 2 onward he buys about
12–20 wheat and sells it on the following turn, eventually cycling 3,066
bought units and 3,206 sold units. The 140-unit difference includes 379 wheat
harvested on-farm, so this is **inventory turnover plus farm supply**, not free
arbitrage.

The copied loop produced large gross “crop revenue” but only +426 money in the
isolated screen and regressed on the six-cow branch. Shared market pressure,
feed timing, and the opportunity cost of tying up cash remove the apparent
spread. Pedro's mechanism is real in his exact market path but classified as
**market-interaction dependent**, not transfer-positive.

## 7. Cash conversion windows and approximate compounding graph

```text
day 4 wheat
    └─ short-cycle cash/feed → finish NW planting
day 6–7 wool + fertilizer
    └─ deed #1 + cows → 25 additional slots + future milk
day 9 milk
    └─ bridge cash → feed/seeds or early deed
day 10–11 full-yield melon
    └─ deed #2 + 30–45 seeds (+ livestock in burst variants)
       └─ 67–74 productive tiles
          └─ strawberry + second melon cash, days 15–21
             └─ wheat conversion, days 20–29
```

The revenue streams matter because of timing:

- day-6 wool has a higher marginal value than similar late wool because it
  unlocks 25 tiles four days sooner;
- day-9 milk bridges the feed/deed gap;
- the day-10/11 melon wave is the critical multiplier because it finances the
  second deed and its seed/labor deployment simultaneously;
- late strawberry/wheat revenue matters mainly after all productive capital is
  installed.

## 8. Why the 798 lifecycle agent did not beat 803 on Kaggle

The lifecycle changes are execution-positive but capital-timing neutral.
Relative to the 803 public population, the 798 submission raises average final
money from 73,001 to 79,277 and median day-20 harvest actions from 89 to 143.
But through day 10 it is virtually identical: 58 productive tiles, 4.18k crop
revenue, and the same truncated first melon cohort. Against selected fresh
direct games it gains locally, yet its selection own-money delta reversed from
+1.6k with fixed shops to **-7.9k under natural RNG**. Its 49 public games were
24/25 with -1,518 average advantage, versus the 803 submission's 24/20 and
+5,988 in its own public sample.

### Transfer-positive

- public opening and day-6/day-10 deed schedule;
- scalable persistent-zone execution;
- yield-complete destructive harvests;
- capital-timed second crop cohort;
- recurring strawberry harvest / safe chain when it does not alter the cash
  phase;
- reduced animal service load as a supporting capacity mechanism.

### Transfer-negative or unproven

- prioritizing more harvests without repairing the first capital wave;
- copied static crop ratios without the cash history that funded them;
- Pedro's wheat loop outside Pedro's market path;
- scheduler changes whose sign flips with natural RNG;
- aggregate gains against weak synthetic opponents.

## 9. High-fidelity replay league

Sixteen replay-trace archetypes were created/validated, including Jayveer,
Pedro, Lucas, Alexander, Teddy, Sagar, Victor, Hak and eight unseen held-out
losses. The reusable wrappers are under `agents/leaderboard_archetypes/` and
the general trace loader is `agents/leaderboard_trace_common.py`.

Validation used both players' original action traces, the original seed, and
the recorded shop schedule. All 16 replays reproduced:

- 719 requested actions per player;
- every selected day 2/4/6/8/10/11/12/15/20/25/29 trajectory exactly;
- both final balances exactly;
- 720 steps and `DONE/DONE` status.

These opponents are high-fidelity counterfactuals, not adaptive programs: when
a candidate changes the market, later trace actions can no-op or buy different
quantities. Their strongest use is replay-grounded stress testing with results
shown per opponent, never as a hidden aggregate rating surrogate.

## 10. Architectural candidates

| ID | Agent | Economic mechanism |
| --- | --- | --- |
| R0 | `opening_public_front_cow8_day6.py` | Real 803.5 control |
| L798 | `lifecycle_lc_combined.py` | Later public lifecycle submission |
| R1 | `leaderboard_r1_yield_completion.py` | Water destructive crops through their final yield day before harvest |
| R2 | `leaderboard_r2_capital_cohorts.py` | R1 + day-10 replay crop cohort |
| R3 | `leaderboard_r3_cow6_capital.py` | R2 + six cows + action-value scheduler |
| R4 | `leaderboard_r4_capital_planner.py` | R2 + nine cows + action-value scheduler |
| R5 | `leaderboard_r5_cow6_capital_clean.py` | R2 + six cows, no scheduler change |
| R6 | `leaderboard_r6_timeline_planner.py` | Compact day-20 forecast for cash/inventory/output/feed/labor |

R6 estimates liquidity at a future checkpoint and can increase the finite
melon cohort when projected free cash is short. In the measured states it
selected the same 13-melon plan as R4 and was action/outcome-equivalent in the
screen. This is useful falsification: a planner abstraction alone creates no
value unless it changes a consequential decision.

### Small fixed-loss screen

| Candidate | W/L/T | Avg money | Avg advantage | Full crop revenue | D10–29 harvests |
| --- | ---: | ---: | ---: | ---: | ---: |
| R0 | 0/4/0 | 60,078 | -10,144 | 41,246 | 112.0 |
| R1 | 0/4/0 | 60,532 | -6,280 | 41,562 | 213.8 |
| R2 | 1/3/0 | 64,526 | -1,397 | 45,504 | 214.0 |
| **R3** | **4/0/0** | **72,524** | **+4,956** | **51,159** | **239.2** |

R1 proves yield completion is necessary but not sufficient. R2 proves the
cash must be converted into the next cohort. R3 shows that cow opportunity
cost becomes material only after crop capital is repaired.

## 11. Held-out validation

Held-out consisted of eight unseen real traces, eight new direct seeds under
fixed shops, the same eight under natural RNG, and three fresh seeds against
four mechanism-specific red teams; both seats. Total: 72 games per finalist.

| Candidate | W/L/T | Avg money | Avg advantage | Own delta: real traces | Own delta: fixed direct | Own delta: natural direct | Paired-delta P10 | Full crop revenue | D10–29 harvests | Critical miss |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| R0 | 26/42/4 | 82,483 | +5,998 | — | — | — | 0 | 42,651 | 123.5 | 2.42% |
| **R3** | **57/15/0** | **90,174** | **+16,735** | **+7,683** | **+12,159** | **+13,261** | **-5,805** | **55,777** | **238.6** | **1.22%** |
| R4 | 57/15/0 | 90,855 | +17,613 | +6,938 | +10,155 | +12,078 | -1,023 | 52,498 | 218.2 | 1.88% |
| R5 | 54/18/0 | 88,955 | +15,053 | +7,114 | +11,013 | +11,669 | -7,065 | 54,901 | 235.4 | 1.81% |

R3 is the strongest replay-grounded candidate because it produces the most
crop revenue, best watering safety, no livestock losses/stranding, and the
largest unseen-real-trace own-money gain. R4 has the best overall money and
less negative paired-delta tail, but it retains the nine-cow service burden and
does worse on the key Jayveer mechanism.

### Original diagnosis traces (selection; both seats)

| Matchup | R0 avg advantage | R3 avg advantage | R3 result |
| --- | ---: | ---: | ---: |
| Jayveer | -11,736 | **+1,978** | 2/0 |
| Pedro | -8,551 | **+7,934** | 2/0 |
| Lucas | -2,375 | **+7,242** | 2/0 |
| Alexander | -13,236 | **+14,167** | 2/0 |

### Unseen real traces (held-out; both seats)

| Matchup | R0 avg advantage | R3 avg advantage | R3 result |
| --- | ---: | ---: | ---: |
| David four-quadrant | -14,066 | **+7,910** | 2/0 |
| Okome strawberry/sheep | -24,797 | -4,977 | 0/2 |
| Ayuma crop/livestock | -11,976 | -9,223 | 0/2 |
| Prashant crop scaler | -22,230 | -11,864 | 0/2 |
| Garigariyong strawberry | -22,310 | -9,581 | 0/2 |
| Amer high-scale | -42,324 | -26,613 | 0/2 |
| Filip top template | -67,969 | -53,707 | 0/2 |
| Yankang wheat close | -35,392 | -34,946 | 0/2 |

### Red team

R3 is 6/0 against melon pressure, 6/0 against livestock pressure, 6/0 against
the wheat-turnover adversary, and 5/1 against the capital-wave adversary. The
R3 advantage P10 in those four groups is +85,243, +65,202, +1,650, and +571.
R4 goes 24/0 and is more robust here, which is why neither branch is promoted
on aggregate alone.

## 12. Answers to the requested questions

1. **Which source is the real 803 agent?**
   `agents/opening_public_front_cow8_day6.py`, source SHA shown above.
2. **Why did later local versions fail?** They improve post-opening execution
   but leave the truncated day-10 capital wave untouched; some gains also
   reverse under natural RNG and shared-market interaction.
3. **First top divergence?** Physical deployment appears by day 4; top land is
   visibly ahead on day 6; the first durable monetary/crop-capital divergence
   is usually day 10–11.
4. **Strongest mechanisms?** Full-yield capital cohorts, synchronized
   cash→investment windows, contiguous second cohorts, livestock/crop capacity
   balance, and late crop phase conversion. Pedro's turnover is a distinct but
   less transferable fifth mechanism.
5. **Jayveer?** 42 melons/10,188 at d11h0 → deed + six cows/one sheep in three
   hours → 13-melon/34-strawberry/13-wheat midgame.
6. **Pedro?** Alternating wheat inventory turnover plus farmed wheat; 126,975
   spent, 133,609 realized, ~6,634 gross spread, interaction-dependent.
7. **Timing-sensitive streams?** d6–7 wool/fertilizer, d9 milk, and especially
   d10–11 melon. Their value is the production they finance, not just sale ROI.
8. **Are six cows better?** For the repaired crop economy, yes in crop
   throughput and the four diagnosis traces; no as a universal public-meta
   claim. Top agents usually peak at 9–10 cows, and R4 is safer in some tails.
9. **Do top agents engineer windows?** The repeated day-6 wool, day-9 milk,
   day-10/11 melon, immediate deed/animal/seed orders across many replays is
   strong evidence of designed timing, though correlation alone is not proof.
10. **Can we reproduce them?** Yes: R2–R5 reproduce the day-10 cohort and
    immediate second phase. R3 reaches 61 productive tiles on day 10 and 71 on
    day 11 versus R0's 53 and 61 in held-out games.
11. **Hardest reconstructed opponent?** Among selection traces, Victor by
    average advantage; among held-out, Filip. Both are fixed-template crop
    throughput economies.
12. **Best candidate?** R3 for real-transfer mechanism evidence; R4 for raw
    held-out average and red-team robustness.
13. **Failed local improvements?** 798 lifecycle, copied crop phase alone,
    predictive/adjacent routing, wheat cycling, and earlier six-cow variants
    without capital repair.
14. **Largest new gain?** Yield-complete day-10 melon conversion plus its
    immediately funded second crop cohort; six cows is a supporting capacity
    release.
15. **Strongest final agent?** Research-only:
    `agents/leaderboard_r3_cow6_capital.py`.
16. **Clearly beats 803?** Mean evidence says yes (+7.7k real traces,
    +12–13k direct), but tail evidence says not robustly enough to promote.
17. **Jayveer/Pedro?** R3 flips both to 2/0 in the diagnosis set.
18. **Ready for Kaggle?** **No.** P10 is negative and the strongest unseen top
    templates remain catastrophic. The mechanism is credible; the policy is
    not yet robust enough.

## 13. Decision and remaining weakness

No agent is promoted. The real 803.5 source remains the leaderboard baseline,
and the repository's existing current-best pointer is intentionally unchanged.
`submission/main.py` was not modified; its SHA-256 remains
`d0fbf1205a7e27f8294f1f9a06afd581cfb3e926f8ab88acc0b7f7a8b72620cf`.

The next research question is no longer whether capital cohorts work. They do.
It is why fixed-template opponents such as Filip, Amer, and Yankang still turn
the same public opening into 110k–125k economies while R3 finishes around
65k–100k against their market paths. Evidence points to full-farm cohort
preservation and the day-20 wheat conversion, not another day-10 parameter.

## Artifacts

- `experiments/leaderboard_breakthrough_analysis.json`
- `experiments/leaderboard_breakthrough_selection.json`
- `experiments/leaderboard_breakthrough_heldout.json`
- `experiments/leaderboard_breakthrough_results.json`
- `experiments/leaderboard_archetype_validation.json`
- `experiments/leaderboard_planner_screen.json`
- `experiments/leaderboard_architecture_screen.json`
