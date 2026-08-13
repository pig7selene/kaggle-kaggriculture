# R3 tail robustification

Date: 2026-08-12  
Frozen research baseline: `agents/leaderboard_r3_cow6_capital.py`  
Public anchors: `agents/lifecycle_lc_combined.py` and the actual 803.5 agent,
`agents/opening_public_front_cow8_day6.py`  
Decision: **no promotion**  
Submission: unchanged; nothing submitted

## Executive conclusion

R3's negative tail has **two different meanings**, and combining them obscures
the diagnosis.

1. Its -5,805 paired own-money P10 versus the 803.5 agent is created primarily
   by 12 otherwise easy red-team games. The six-cow branch wins those games by
   63k–97k, but earns 3.1k–7.1k less than the eight-cow 803 agent. Six cows give
   up roughly 14k–17k of animal annuity while the extra crop capacity realizes
   only 5k–8k there.
2. Its 15 actual held-out losses are dominated by a different problem. Eight
   seat-invariant losses to Amer, Filip, Prashant, and Yankang average -31,783.
   Those opponents create materially larger crop cohorts, preserve throughput,
   and convert large day-10 and day-20 waves. R3's deed timing, hand ramp, and
   corrected final watering are already right; its crop scale is not enough.

The tested guards cannot reconcile the two. Conditional extra cows partly
recover the annuity tail but do not improve the top-template record (still
2/14), and the two-cow version introduces four livestock losses and up to 108
coins of stranded endgame value. Early harvest under visible melon pressure
loses money. Extending late strawberries loses 2,302 average money and breaks
Jayveer.

On 200 fresh, real-heavy games per finalist, frozen R3 remains the strongest
choice: 151/49/0, 72,565 average money, +13,284 paired game advantage, paired
P10 -64 and P5 -9,241. This is an excellent mean but an unrepaired deep tail.
No candidate passes promotion, so `experiments/current_best.json` is unchanged.

## 1. Frozen inputs and study coverage

| File | SHA-256 before and after study |
| --- | --- |
| `agents/leaderboard_r3_cow6_capital.py` | `57a4d38a72fffe75061271423b5580dec79c8c0e0423db4bef8899b3993b8fad` |
| `agents/lifecycle_lc_combined.py` | `db12d32912843e012c3dfd7e84c2c384ce998694bf02b98fc7e1fe9189c17e78` |
| `agents/opening_public_front_cow8_day6.py` | `3ede0041921010b0136abb538395faa5951e9af1fb9b76be41467246885da6a8` |
| `submission/main.py` | `d0fbf1205a7e27f8294f1f9a06afd581cfb3e926f8ab88acc0b7f7a8b72620cf` |
| `experiments/current_best.json` | `0b2e47f9034914888fe90079997fef8495081437ffdf74f78fb55486ed6e86b1` |

The diagnosis reran 27 unique tail games with the exact opponent program,
seed, recorded shop schedule, and seat:

- all 15 losses from the 72-game held-out set;
- all 12 games whose paired own-money delta versus the 803 agent was below
  -3,000;
- both R3 and `lifecycle_lc_combined`, for 54 reconstructed games total;
- zero financial reconstruction mismatches.

The compact diagnosis is in `r3_tail_robustification.json`; full turn/day
timelines, actions, prices, inventories, crop states, and counterfactual event
features remain in `r3_tail_diagnosis.json`.

The R3 wrapper was not edited. The shared research engine gained opt-in fields
used only by separate G-agents. A fresh R3 rerun reproduced the original exact
replay outcomes, deed days, six-cow count, zero-failure safety metrics, and
held-out money, verifying the dormant defaults did not change frozen R3
behavior.

## 2. Every held-out loss, individually

`Largest day` is the opponent's largest single-day revenue gain over R3. The
classification compares all three trajectories: lifecycle, R3, and opponent.

| Opponent | Seat | R3 / opponent | Final advantage | Durable revenue lead | Largest day | Three-way result |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Amer high scale | 0 | 85,726 / 111,876 | -26,150 | D2 | D11 (+9,515) | Shared weakness |
| Amer high scale | 1 | 85,047 / 112,123 | -27,076 | D2 | D11 (+9,515) | R3-specific regression (-1,202 own money) |
| Ayuma crop/livestock | 0 | 80,782 / 89,980 | -9,198 | D17 | D10 (+9,756) | R3-specific regression (-2,561) |
| Ayuma crop/livestock | 1 | 80,678 / 89,926 | -9,248 | D17 | D10 (+9,756) | R3-specific regression (-2,874) |
| Filip top template | 0 | 65,023 / 118,730 | -53,707 | D9 | D20 (+15,321) | R3 improves lifecycle by 1,774, not enough |
| Filip top template | 1 | 65,023 / 118,730 | -53,707 | D9 | D20 (+15,321) | R3 improves lifecycle by 1,774, not enough |
| Garigariyong strawberry | 0 | 103,116 / 111,989 | -8,873 | D24 | D11 (+7,596) | R3 improves lifecycle by 9,497, not enough |
| Garigariyong strawberry | 1 | 101,901 / 112,190 | -10,289 | D22 | D11 (+6,383) | R3 improves lifecycle by 8,000, not enough |
| Okome strawberry/sheep | 0 | 62,855 / 67,832 | -4,977 | D25 | D11 (+6,126) | R3 improves lifecycle by 13,803, not enough |
| Okome strawberry/sheep | 1 | 62,855 / 67,832 | -4,977 | D25 | D11 (+6,126) | R3 improves lifecycle by 13,803, not enough |
| Prashant crop scaler | 0 | 100,334 / 112,198 | -11,864 | D9 | D11 (+6,311) | R3 improves lifecycle by 5,680, not enough |
| Prashant crop scaler | 1 | 100,334 / 112,198 | -11,864 | D9 | D11 (+6,311) | R3 improves lifecycle by 5,680, not enough |
| Yankang wheat close | 0 | 77,655 / 112,715 | -35,060 | D13 | D20 (+9,498) | R3 improves lifecycle by 1,672, not enough |
| Yankang wheat close | 1 | 77,852 / 112,684 | -34,832 | D13 | D20 (+9,299) | R3 improves lifecycle by 1,969, not enough |
| Crop-capital pressure | 0 | 92,241 / 93,300 | -1,059 | D27 | D29 (+2,161) | R3 improves lifecycle by 1,621, not enough |

### Concrete divergence chains

**Amer.** The first concrete divergence is crop capacity, not a missed deed.
By day 4 Amer has 24 productive tiles and 1,563 crop revenue; R3 has 14 and
zero. R3 buys land on days 6 and 10, earlier than Amer's effective second
deployment, but Amer converts a much larger crop wave on day 11. At the end,
Amer has sold 802 wheat, 108 melons and 261 strawberries versus R3's 129, 83
and 161. The crop revenue deficit is 48,418; animal revenue is also 11,842
lower. Waiting for one more opening watering is not the cause.

**Ayuma.** Ayuma's day-10 crop wave adds 9,756 more revenue that day, but R3's
earlier animal cash keeps the total lead recoverable through day 16. From day
17 it becomes durable. Final crop revenue is 58,443 versus 44,129, and Ayuma
also has nine cows versus six. This is the clearest true mixed crop/annuity
failure and explains why it is one of only three R3-specific loss regressions.

**Filip.** R3's yield correction helps by 1,774, but Filip is already at 50
productive tiles on day 8 versus 38, then 68 versus 60 on day 10. The largest
compounding divergence is a 15,321 day-20 revenue wave. Filip finishes with
438 wheat, 102 melons and 286 strawberries sold versus 127, 82 and 156; crop
revenue is 68,791 versus 26,073. This is not recoverable with a sale-timing
guard.

**Garigariyong.** R3 leads for much of the game after absorbing the day-11
wave. The loss becomes durable only on days 22–24, when the opponent's larger
strawberry/wool economy converts. Garigariyong sells 219 strawberries for
56,479; R3 sells 161 for 40,658. R3 actually earns 3,942 more animal revenue,
so unconditional extra cows target the wrong stream.

**Okome.** The opponent converts a 60-unit opening melon family on days 10–11,
but R3 nearly recovers by day 24. The durable day-25 loss is a smaller combined
strawberry/sheep close: 61,562 crop and 33,662 animal revenue versus 55,948 and
30,080. It is market-dependent and much smaller than the top crop cluster.

**Prashant.** A 60-melon day-10 cohort and follow-up day-11 sale create a
10.9k cumulative revenue lead. R3 holds similar productive capacity later,
but the opponent completes more premium cycles (207 strawberries) and keeps a
14,715 final crop-revenue lead. R3's animal revenue is only 956 lower; this is
not a cow-count failure.

**Yankang.** The opening melon wave establishes the lead; a day-20 48-melon
wave plus a much larger wheat close compounds it. Yankang sells 451 wheat
versus R3's 112 and 203 strawberries versus 164. Final crop revenue is 73,989
versus 45,500; the additional 13,194 animal revenue makes recovery impossible.

**Crop-capital pressure.** This is a lone, small, late loss. R3 has 5,833 more
crop revenue but 10,071 less animal revenue; the lead becomes durable only on
day 27. It does not share the early top-template collapse.

Among the 15 losses, R3 is a specific regression in only three, a shared
weakness in one, and a substantial-but-insufficient improvement in 11. Across
all 27 tail games, the 12 annuity-delta games turn the overall comparison into
15 R3 regressions, one shared weakness, and 11 partial improvements.

## 3. The games that create paired P10

These are the complete under--3,000 own-money delta set from the original
72-game confirmation. They are **not competitive losses**.

| Opponent | Seed | Seat | R3 money | 803 money | Own-money delta | Game advantage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Melon pressure | 962100 | 0 | 112,718 | 119,101 | -6,383 | +91,534 |
| Melon pressure | 962100 | 1 | 112,987 | 116,128 | -3,141 | +91,803 |
| Melon pressure | 962101 | 0 | 117,801 | 123,987 | -6,186 | +96,584 |
| Melon pressure | 962101 | 1 | 117,731 | 122,846 | -5,115 | +96,514 |
| Melon pressure | 962102 | 0 | 104,818 | 111,589 | -6,771 | +83,637 |
| Melon pressure | 962102 | 1 | 104,818 | 111,398 | -6,580 | +83,637 |
| Livestock pressure | 962100 | 0 | 110,075 | 116,639 | -6,564 | +72,419 |
| Livestock pressure | 962100 | 1 | 109,316 | 112,475 | -3,159 | +71,263 |
| Livestock pressure | 962101 | 0 | 114,415 | 120,674 | -6,259 | +75,982 |
| Livestock pressure | 962101 | 1 | 114,419 | 121,531 | -7,112 | +75,919 |
| Livestock pressure | 962102 | 0 | 102,339 | 108,157 | -5,818 | +63,963 |
| Livestock pressure | 962102 | 1 | 102,381 | 108,064 | -5,683 | +63,122 |

Original 72-game paired own-money distribution versus the 803 agent:

| Mean | Median | P25 | P10 | P5 | Worst |
| ---: | ---: | ---: | ---: | ---: | ---: |
| +7,691 | +8,168 | +1,752 | **-5,805** | -6,464 | -7,112 |

The dominant decision behind this statistical tail is the fixed six-cow cap.
In these low-pressure economies the reclaimed crop actions are not scarce, so
the eight-cow baseline's long milk/fertilizer annuity dominates. This is a
regret relative to an income baseline, not evidence R3 is vulnerable to those
opponents.

## 4. Failure clusters

| Cluster | Games / losses | Average loss or advantage | Worst | First affected | Determinism |
| --- | ---: | ---: | ---: | ---: | --- |
| Unseen top crop throughput | 8 / 8 | -31,783 | -53,707 | Median durable D9 | Seat-invariant exact traces |
| Mixed market/livestock | 6 / 6 | -7,927 | -10,289 | Median durable D23 | Commodity/RNG sensitive |
| Six-cow paired annuity | 12 / 0 | +80,531 game advantage | +63,122 minimum win | No opponent lead | Seed sensitive, present in both seats |
| Isolated capital wave | 1 / 1 | -1,059 | -1,059 | D27 | Isolated |

Therefore the tail is **multiple mechanisms**, not one threshold:

- one homogeneous mechanism creates the paired P10 statistic;
- one different, much more serious mechanism creates catastrophic real losses;
- two smaller late-market mechanisms fill out the remaining losses.

## 5. Decision-regret audit

The analyzer records each material harvest decision with bank, quote, market
inventory, opponent mature/held supply, crop age/yield/watering state, next
deed cost, and visible shops. It also reconstructs the subsequent cash,
investment, crop and animal streams.

| Decision | Replay/simulation result | Regret conclusion |
| --- | --- | --- |
| Wait for final watering | Across the 27 R3 tail games, only one melon was destructively harvested with a remaining final-water opportunity; it was a day-12 tile, not an opening deed cohort. No such harvest would have unlocked the first or second deed. | The corrected R3 wait is economically right in the observed critical windows. |
| Harvest now | G2 permits early harvest when visible opponent melon supply is at least 30 and price at least 235. It loses 62 mean money versus R3, has -1,661 paired P10 delta, and worst delta -4,306. | Market collision does not compensate for sacrificed yield/cycle ordering. |
| Sell now | R3 returns opening harvests promptly and sells shed inventory on the next observation. No pre-deed delayed shed cohort was found. | G3 is intentionally action-equivalent; there is no observed sale delay to repair. |
| Buy land | R3 normally buys on days 6 and 10. The high-rating population uses the same dates. | No tail loss is explained by a missed required deed window. |
| Buy cow | Six cows reclaim crop work but lose annuity in easy games. G4/G8 test conditional restoration. | Real tradeoff, but neither gate fixes the severe top-crop cluster. |
| Hire hand | R3 reaches 14 hands on day 10, matching the replay median. | Not the first divergence. More hires would not create the missing initial cohorts. |
| Plant melon | R3's five opening melons now reach full yield, but strong losers deploy larger opening/second waves. | Cohort scale and reinvestment, not premature destruction, remain weak. |
| Plant strawberry | G5 keeps strawberries after day 20 at prices at least 150. It loses 2,302 mean money and makes Jayveer 0/2. | A quote floor alone ignores maturation/workload and is rejected. |
| Plant wheat | Yankang/Amer exploit much larger late wheat volume. A late fixed mix is not shared by Filip/Prashant. | Evidence supports adaptive capacity architecture, not a narrow fixed wheat guard. |

### Capital-timing equation

For a destructive crop, the compact decision is:

`wait value = marginal yield × expected sale price`

versus

`early-cash value = cash made liquid now × ROI of the concrete investment
unlocked during the saved turns`.

Early harvest is admissible only when it actually crosses a documented bank
threshold before a critical window. Merely seeing rival inventory is not
enough. In the observed R3 opening, early harvest did not cross either deed
threshold, while waiting added one unit per tile. Also, field harvest does not
create spendable cash until the carrier returns and the item sells. That
logistics delay further weakens the early-cash case.

**Answer:** waiting can be wrong in principle, but it was not economically
wrong in any observed first/second-deed R3 failure. The tested early-harvest
counterfactual regressed both mean and tail.

## 6. Critical capital windows from the 153-replay corpus

The corpus contains 153 unique public episodes; the reliable high-rating
subset has 35 selected appearances. All 35 buy the first and second deeds on
days 6 and 10. Costs below are engine costs; delay losses are conservative
opportunity-cost approximations, not causal replay measurements.

| Window | Target | Required cash | Typical source | Est. cost of +6 / +12 / +24 turns |
| --- | --- | ---: | --- | ---: |
| First land | D6 | 1,000 | D6 wool + fertilizer + early wheat | 150 / 300 / 600 |
| Livestock ramp | D7–9 | ~1,600 for four cows | Post-deed wool/fertilizer + first milk | 180 / 360 / 720 |
| Second land | D10 | 2,000 | D9 milk + D10 wool + full-yield melon | 400 / 800 / 1,600 |
| Major post-deed cohort | D10–12 | ~3,000 seeds/feed buffer | Synchronized D10/11 melon conversion | 500 / 1,000 / 2,000 |

The day-10 window is most important: it must fund the deed **and** immediate
deployment. A deed without seeds and scheduled workers leaves purchased tiles
economically idle. In this tail study R3 usually makes that window; the strong
opponents exploit the next step by putting more premium/close crops through
the same three quadrants.

## 7. Narrow guards and adversaries

Each implementation states its intended observed failure in its module
docstring.

| Guard | Intended failure | Screen result versus frozen R3 | Decision |
| --- | --- | --- | --- |
| G0 R3 | Frozen control | — | Retain |
| G1 capital-window harvest | Early crop cash crosses a deed threshold | No qualifying observed event; action-equivalent control | Do not invent exception |
| G2 market harvest | Rival melon wave reaches market first | -62 mean; -1,661 P10; -4,306 worst | Reject |
| G3 capital sale | Harvested crop sits through a deed window | No delayed cohort; action-equivalent control | No defect found |
| G4 milk annuity | Six-cow annuity deficit | Follow-up +1,004 mean in one panel, but P10 delta -675 | Finalist, then reject |
| G5 late crop floor | Late top-template crop throughput | -2,302 mean; -4,166 P10; Jayveer 0/2 | Reject |
| G6 G4+G5 | Combined annuity and late crops | -2,128 mean; -4,578 P10 | Reject |
| G7 post-D20 two cows | Restore annuity after crop conversion | -178 mean; -3,194 P10 | Reject |
| G8 conditional seventh cow | Smallest annuity hedge | +254 mean, -814 P10 in screen | Finalist, then reject |

Three new pressure agents were added:

- `r3_early_cash_burst.py`: early cash/deployment pressure for the high-scale
  cluster;
- `r3_delayed_melon_scaler.py`: delayed full-yield capital-wave pressure;
- `r3_crop_heavy_scaler.py`: crop-capacity mirror pressure.

Existing exact replay archetypes remain the authoritative adversaries for the
top-crop and mixed-market clusters; existing livestock/melon/crop-capital
pressure agents remain the annuity and isolated-wave representatives. The new
proxies applied pressure but did **not** recreate the real catastrophic mean:
frozen R3 went 11/5 against early cash, 10/6 against delayed melon, and 8/8 in
the crop-heavy mirror. This is useful falsification—simple schedule proxies
still understate the public agents' execution/market interaction.

## 8. Fresh final confirmation

Final seeds 964000–964007 were unused by selection. All programmable games ran
both seats. Each candidate received 200 games: 24 exact real traces, 64 direct
fixed/natural anchor games, 48 new-adversary games, and 64 low-weight historical
red-team games (600 games total).

`Paired advantage` pairs the two seats by opponent and seed. `Delta vs R3`
compares own money on identical candidate/opponent/seed/seat jobs.

| Candidate | W/L/T | Own money | Paired adv mean / med | P25 | P10 | P5 | Worst | Own-money delta vs R3 mean / P10 / P5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **R3 six cows** | **151/49/0** | **72,565** | **+13,284 / +4,777** | 0 | **-64** | -9,241 | -53,707 | control |
| G4 conditional eight | 150/50/0 | 73,039 | +13,696 / +5,442 | +595 | -3,176 | -9,134 | -54,278 | +474 / -1,479 / -2,954 |
| G8 conditional seven | 143/57/0 | 72,729 | +13,492 / +4,966 | +112 | -1,037 | -10,054 | -52,983 | +164 / -1,163 / -1,455 |

G4's +474 mean is the best annuity recovery, but it turns a near-zero R3 P10
into -3,176, loses six harvests, reduces crop revenue by 703, suffers four
livestock losses, and strands up to 108 value. G8 is safety-clean and sacrifices
less, but its P10 remains negative and it goes 6/10 in fixed direct R3 games.
Neither lifts the -50k top-template events.

### Controlled, natural, and anchors

| Candidate | Vs R3 fixed | Vs R3 natural | Vs 803 fixed | Vs 803 natural |
| --- | ---: | ---: | ---: | ---: |
| R3 | 8/8, 0 | 8/8, 0 | 16/0, +16,562 | 16/0, +17,841 |
| G4 | 7/9, +421 | 9/7, +782 | 16/0, +16,252 | 16/0, +18,026 |
| G8 | 6/10, -109 | 8/8, +202 | 16/0, +16,270 | 16/0, +17,708 |

The number after W/L is average head-to-head advantage. All candidates still
beat the 803 anchor decisively under both modes. G8 changes sign against R3;
G4 remains slightly positive in mean, but its paired own-money P10 is negative
in both modes and it fails safety. Thus the robustification conclusion does
not survive both RNG regimes strongly enough for promotion.

### Required real matchups

| Candidate | Jayveer | Pedro | Lucas | Alexander | Unseen top pool |
| --- | ---: | ---: | ---: | ---: | ---: |
| **R3** | 2/0, +1,978 | 2/0, +7,934 | 2/0, +7,242 | 2/0, +14,167 | **2/14, -17,875** |
| G4 | 2/0, +1,761 | 2/0, +7,718 | 2/0, +8,125 | 2/0, +11,454 | 2/14, -17,943 |
| G8 | 2/0, +1,982 | 2/0, +7,291 | 2/0, +8,117 | 2/0, +13,527 | 2/14, -17,845 |

All finalists preserve the four required wins, but neither guard materially
changes the unseen record. Filip remains the catastrophic matchup: R3 -53,707,
G4 -54,278, G8 -52,983. Amer and Yankang also remain about -26.6k and -34.9k.

### Economic checkpoints

These are averages over the full 200-game real-heavy league.

| Candidate | D6 / D10 / D11 cash | D15 / D20 cash | Land days | D20 cows | Crop rev | Melon rev | Strawberry rev | D10–29 harvests |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| R3 | 69 / 2,403 / 3,976 | 11,238 / 27,542 | 6,10 in 189/200; 7,10 in 11 | 6 in 200 | 46,691 | 15,564 | 25,828 | 237.0 |
| G4 | 69 / 2,403 / 3,976 | 10,894 / 26,562 | Same | 6 in 122; 8 in 78 | 45,988 | 15,592 | 25,502 | 231.0 |
| G8 | 69 / 2,403 / 3,976 | 11,150 / 27,381 | Same | 6 in 176; 7 in 24 | 46,463 | 15,585 | 25,774 | 235.8 |

All three have identical pre-guard capital paths. Median first melon sale is
step 260 (D10H20); average melon revenue through day 12 is 6,563. The cow
guards spend capital only after the proven deed/opening phase, but even then
they reduce crop throughput enough to erase much of the annuity gain.

### Safety

| Candidate | Runtime/invalid | Livestock losses | Max stranded value |
| --- | ---: | ---: | ---: |
| R3 | 0 / 0 | 0 | 0 |
| G4 | 0 / 0 | **4** | **108** |
| G8 | 0 / 0 | 0 | 0 |

## 9. Direct answers

1. **What exact games create negative P10?** The 12 melon/livestock-pressure
   games listed in section 3. All are huge wins; they are own-income
   regressions caused by six cows.
2. **One mechanism or multiple?** Multiple. Six-cow annuity creates statistical
   P10; top-template crop throughput creates actual catastrophic losses; mixed
   late markets create smaller losses.
3. **Largest tail decision?** Relative to 803, the six-cow cap. In absolute
   losses, the larger problem is insufficient crop cohort scale and repeated
   throughput after day 10, not one harvest threshold.
4. **Is final-watering delay ever wrong?** In principle yes if immediate sale
   crosses a real investment threshold whose compounding value exceeds added
   yield. In these failures, no: no required deed was unlocked, and G2 loses.
5. **Critical windows?** D6 first deed, D7–9 animal ramp, D10 second deed, and
   D10–12 immediate seed/deployment wave. The last two are the strongest
   multiplier.
6. **Which top strategies exploit R3?** Amer's very high crop/wheat capacity,
   Filip's high-throughput public template, Prashant's larger premium cycles,
   and Yankang's melon-plus-wheat close.
7. **Why?** They deploy more productive tiles before/at the first crop wave and
   complete much larger second/late cohorts. Three quadrants and 14 hands alone
   do not guarantee equivalent crop throughput.
8. **Which narrow guard fixes the largest cluster?** None. G4 partly fixes the
   annuity statistic, but it does not fix the larger top-crop failure cluster.
9. **Mean sacrifice?** G4 gains 474 mean versus R3 rather than sacrificing it,
   but sacrifices 703 crop revenue and six harvests; G8 gains only 164 and loses
   228 crop revenue.
10. **P10/P5 improvement?** Neither improves the relevant final paired game
    tail: R3 -64/-9,241; G4 -3,176/-9,134; G8 -1,037/-10,054. Paired own-money
    deltas versus R3 are also negative at P10/P5.
11. **Regression wins preserved?** Yes, all finalists retain 2/0 against
    Jayveer, Pedro, Lucas, and Alexander.
12. **Fixed shops?** R3 remains strongest/neutral head-to-head; G4 is only
    +421 mean against R3 with a negative paired tail, G8 is -109.
13. **Natural RNG?** G4 is +782 and G8 +202 head-to-head in mean, but negative
    tails and the G8 fixed sign reversal remain. All still crush 803.
14. **New adversary still breaking the strongest?** The delayed-melon proxy is
    the strongest non-mirror proxy (6/16 wins against R3), but none recreates
    the real negative mean. Filip remains the actual breaker at 2/2 and -53,707.
15. **Strongest final candidate?** Frozen
    `agents/leaderboard_r3_cow6_capital.py`.
16. **Ready for Kaggle?** **No.** Its mean transfer is excellent, but P5 and
    worst-game loss remain severe, top-template results are still 2/14, and no
    guard repairs them without new tail/safety regressions.

## 10. Promotion decision and next research implication

No agent is promoted. `experiments/current_best.json` continues to point to
`agents/lifecycle_lc_combined.py`; `submission/main.py` was not touched.

The negative result is informative: the catastrophic tail cannot be repaired
by one sale, price, or cow threshold. The next justified research unit is a
controlled **crop-capacity/cohort deployment mechanism** that preserves R3's
yield-complete opening, deed timing, router, and regression wins. It should be
tested against exact Amer/Filip/Prashant/Yankang traces—not tuned against the
weaker proxies—and remain separate from any submission work.

## Artifacts

- `experiments/r3_tail_diagnosis.json` — complete 54-game, day/decision-level
  three-way diagnosis.
- `experiments/r3_guard_screen.json` — G0/G2/G4/G5/G6 initial screen.
- `experiments/r3_guard_followup.json` — G4/G7 follow-up.
- `experiments/r3_guard_cow7.json` — G4/G8 follow-up.
- `experiments/r3_tail_final.json` — complete 600-game fresh final league.
- `experiments/r3_tail_robustification.json` — compact machine-readable
  conclusions, individual audit, checkpoints, hashes, and promotion result.

