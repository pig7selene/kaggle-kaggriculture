# Predictive watering and six-cow capacity research

## Decision

**No promotion.** The frozen best remains `agents/lifecycle_lc_combined.py`.
The strongest research-only branch is
`agents/watering_w3d_guarded.py` (W3dG): six cows, strict deadline/bonus-window
watering, and state-neutral suppression of duplicate animal no-ops.

W3dG is economically promising, but it does not validate the proposed causal
mechanism. It carries *more* measured watering debt and inherited emergency
work, misses the `<0.7%` watering target, does not reach 260 harvests, has a
negative P10 on the larger controlled and natural-RNG audits, loses both exact
Jayveer seats, and regresses own money on one fresh hard-pool panel. Its final
60-game money gain is only 2.1%, below the preferred promotion scale.

The frozen agent and submission were not modified. No Kaggle submission was
made.

## Experimental controls

- W0 is an isolated nine-cow copy of the frozen architecture. A full local
  equivalence game matched `agents/lifecycle_lc_combined.py` on all 719 action
  requests and final money (106,924 each).
- Opening, three-quadrant economy, crop phases, persistent-zone router,
  recurring strawberry harvesting, selling, and endgame logic were held fixed.
- W1 changes only the target herd from nine cows to six.
- Development used the four exact reconstructed losses with their recorded
  shop schedules. Selection, final confirmation, RNG audits, and red-team runs
  used disjoint seed ranges.
- Both seats were used throughout. Fixed-shop and natural-RNG results are
  reported separately.
- `agents/watering_w3d_guarded.py` suppresses only duplicate or already-satisfied
  animal actions that are semantic no-ops. It does not change field economics.

### Candidate definitions

| ID | Isolated change |
| --- | --- |
| W0 | Frozen nine-cow control |
| W1 | Six cows only |
| W2 | Nine cows + short-horizon predictive admission/value ordering |
| W3 | Six cows + the same predictive admission/value ordering |
| W4 | W3 + bounded local watering-cluster preference |
| W3b/W4b | Territory-local borrowing, with/without sweep preference |
| W3c | Harvest-protected local borrowing |
| W2d/W3d | Nine/six cows + strict deadline and one-time bonus-window watering |
| W3e | Six cows + proactive late-day safe-watering guard |
| W3dG | W3d + state-neutral animal no-op guard |

W5 was not created. The earlier guarded harvest/replant-chain experiment had
already shown that forcing the chain steals watering and harvest actions. None
of the new evidence justified reintroducing it.

## Watering-debt model

For every visible plant the analyzer records lifecycle stage, maturity,
watering state, a conservative product/seed value at risk, territory, and the
worker's travel into the action. It classifies each tile as:

- **Critical:** unwatered with `consecutive_unwatered >= 1`; it must be
  serviced before end of day.
- **Near-critical:** unwatered with `consecutive_unwatered == 0`; skipping the
  day makes it critical tomorrow.
- **Safe:** already watered today.

At each turn:

`watering debt actions = critical + near-critical * (hour + 1) / 24`

The value-weighted form uses the same urgency multiplier. This is a workload
pressure measure, not a count of crop deaths. An important instrumentation
correction separates mandatory planting-day watering from inherited debt:

- **Planting-day emergency:** planting initializes the crop in a state that
  must be refreshed that day.
- **Inherited emergency:** the crop entered the day already critical because
  the previous safe day was skipped.

The predictive prototype estimates each territory's next-day workload and
available crop-worker capacity, reserves capacity for visible harvests, and
admits only the highest-value excess near-critical tiles. No global planner is
used.

## What creates emergencies in W0

The exact Jayveer/Pedro day-10–25 traces show that emergencies are predominantly
recurring-crop cohort pressure, not random worker shortage:

- 123 inherited emergency waters per appearance, of which 94.5 are strawberry,
  21 wheat, 6.5 melon, and 1 carrot.
- NW accounts for 48.2% of critical crop-turns, SW 35.1%, and NE 16.7%.
- Near-critical waves peak on days 17 and 22; critical pressure follows on days
  18 and 23. Harvest backlog rises in the same late-season waves.
- Current watering travel is not unusually long: 1.51 actions on average with
  P90 4. The problem is which daily refreshes are admitted, not a single long
  cross-farm emergency route.

The model can predict tomorrow's critical set from an unwatered safe crop, but
watering it earlier in the *same day* creates no multi-day reserve. Therefore
the useful prediction horizon is mostly the remainder of the current day plus
the next end-of-day boundary. This makes capacity admission and deadline
execution more important than indiscriminate early watering.

## Phase 1: what six cows actually free

The clean W0/W1 comparison uses the same eight exact-loss games.

| Metric | W0: 9 cows | W1: 6 cows | Change |
| --- | ---: | ---: | ---: |
| Animal-service worker turns | 723.6 | 591.4 | **-132.3** |
| Crop worker turns | 1,228.3 | 1,303.8 | **+75.5** |
| Movement turns | 2,683.6 | 2,806.3 | +122.6 |
| Crop harvests | 236.1 | 252.1 | **+16.0** |
| Crop revenue | 36,837.9 | 39,929.5 | **+3,091.6** |
| Animal revenue | 54,301.1 | 52,074.8 | -2,226.4 |
| Avg replant latency | 16.58 | 9.66 | **-6.92** |
| Critical miss rate | 1.75% | 1.59% | -0.16 pp |
| Emergency waters | 223.0 | 230.6 | +7.6 |
| Final money | 65,900.6 | 69,094.9 | **+3,194.3** |

In this matched exact panel, W0 earns 13,907 crop revenue on days 10–20 and
25,528 on days 20–29. W3dG earns 14,903 and 29,996 respectively: +996 in the
middle window and +4,468 in the late window. (The game has days 0–29, so
"day 20–30" is represented as inclusive days 20–29.)

Six cows reclaim 132 animal-service turns. Approximately 76 become recorded
crop actions and much of the rest supports access to a larger crop workload:
movement rises by 123 turns. The result is 16 more harvests and substantially
shorter natural replant delay. The capacity does **not** automatically remove
watering emergencies; the additional live crop area slightly increases their
count. Crop work is nevertheless more valuable at the margin: W1 gains 3,092
crop revenue while giving up 2,226 animal revenue.

## Top-player watering behavior: attempted falsification

The public replay comparison covers 35 strong-player appearances and days
10–25. Local columns use the four exact reconstructed opponents, both seats;
the public column is observational rather than matched-seed causal evidence.

| Day 10–25 metric | W0 | W1 | W3 | W4 | Strong public agents |
| --- | ---: | ---: | ---: | ---: | ---: |
| Critical miss rate | 1.75% | 1.59% | 1.35% | 1.47% | **0.34%** |
| Proactive-water fraction | 69.7% | 70.6% | 16.4% | 15.5% | 31.8% |
| Water actions / crop harvest | 4.21 | 4.18 | **2.97** | 3.03 | 3.37 |
| Avg travel into water | **1.51** | 1.60 | 2.12 | 2.17 | 1.53 |
| Avg watering cohort | 3.16 | 3.04 | 2.29 | 2.27 | 2.08 |
| P90 watering cohort | 7.0 | 6.9 | 5.0 | 5.0 | 5.0 |
| Territory crossings | 150 | 164 | 163 | 168 | **104** |
| Water immediately before harvest waves | 76.6% | 74.3% | 95.4% | 95.7% | **96.2%** |
| Crop harvests in analyzer window | 175.1 | 188.1 | **190.4** | 185.3 | **202.3** |

This falsifies the initial assumption that strong agents prevent debt through
more proactive watering or larger watering sweeps. They deliberately tolerate
more in-progress critical work, but execute it reliably by the deadline. They
also use fewer water actions per completed crop harvest, cross territories less,
and align watering closely with harvest waves. Their advantage is deadline
execution, crop/cohort admission, and spatial stability—not blanket preventive
watering.

## Controlled ablations on the four real losses

All rows below are eight games: Jayveer, Pedro, Lucas, and Alexander, both
seats, with recorded shop schedules.

| Candidate | W/L/T | Money | Adv. | Debt | Critical miss | Emergency water | Harvests | Backlog | Replant | Crop rev. |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| W0 | 4/4/0 | 65,901 | +323 | 16.6 | 1.75% | 223 | 236.1 | 5.7 | 16.6 | 36,838 |
| W1 | 4/4/0 | 69,095 | +1,160 | 17.8 | 1.59% | 231 | 252.1 | 6.1 | 9.7 | 39,930 |
| W2 | 4/4/0 | 66,902 | +1,271 | 24.9 | 1.53% | 451 | 229.1 | 8.0 | 9.9 | 37,657 |
| W3 | **6/2/0** | **70,205** | **+2,721** | 26.0 | 1.35% | 473 | **253.8** | 8.3 | 10.9 | 41,282 |
| W4 | 5/3/0 | 69,575 | +1,556 | 26.1 | 1.47% | 474 | 246.8 | 8.6 | 9.5 | 40,633 |
| W3d | 5/3/0 | 69,825 | +1,909 | 26.6 | **1.19%** | 482 | 247.1 | 8.9 | 10.7 | **41,487** |
| W3e | 4/4/0 | 67,300 | -1,071 | **16.6** | 1.49% | **200** | 231.2 | 6.8 | **4.9** | 38,563 |

### W1 versus W3: the central comparison

W3 raises money by 1,110 and crop revenue by 1,353 over W1, with 1.6 more
harvests and a 0.24-point lower miss rate. But it does so by reducing total
watering from roughly 786 to 566 actions and waiting for deadlines: inherited
emergency work and measured debt rise sharply, proactive watering falls from
70.6% to 16.4%, and backlog rises from 6.1 to 8.3. This is better action-value
efficiency, not successful prevention of emergencies.

W3e is the clean counterexample. It performs the most preventive watering,
reduces emergency actions to 200, keeps measured debt at W0 levels, and lets
replant latency fall to 4.9 without forced chaining. It also loses 20.9
harvests and 1,367 crop revenue relative to W1, finishing 1,795 coins poorer.
Proactive watering did steal harvest capacity.

### Local batching and territory borrowing

- W4's local cluster preference loses 630 money and 6.9 harvests versus W3,
  while critical misses worsen by 0.12 points.
- Local borrowing (W3b) falls to 217.8 harvests and 66,145 money.
- Adding a sweep to it (W4b) lowers misses but remains worse at 217.5 harvests
  and 65,496 money.
- Harvest-protected borrowing (W3c) recovers to 239.2 harvests but still trails
  W1 by 1,075 money.
- Sweep-only W4c is an exact economic no-op relative to W1.

Territory borrowing and cluster scores therefore create detours or displace
harvests. The frozen persistent zones are already locally efficient enough that
the proposed sweep layer adds no value.

## Cow count after deadline scheduling

| Cows | Money | Harvests | Critical miss | Crop revenue | Animal revenue | Animal turns | Replant latency |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **6** | **69,825** | **247.1** | **1.19%** | **41,487** | 52,034 | **592** | **10.7** |
| 7 | 68,216 | 234.6 | 1.36% | 39,903 | 53,320 | 659 | 19.9 |
| 8 | 66,463 | 223.8 | 1.66% | 37,732 | 53,383 | 695 | 13.7 |
| 9 | 65,741 | 223.2 | 1.56% | 36,754 | **54,018** | 718 | 14.7 |

Six remains the clear economic optimum under this scheduler. Each added cow
raises service work faster than animal revenue and removes profitable crop
cycles.

## Exact reconstructed loss matchups

| Opponent | W0 W/L | W0 money / adv. | W3dG W/L | W3dG money / adv. | Own-money change |
| --- | ---: | ---: | ---: | ---: | ---: |
| Jayveer | 0/2 | 57,817 / -9,280 | 0/2 | 68,102 / -4,442 | **+10,285** |
| Pedro | 0/2 | 62,505 / -4,486 | **1/1** | 69,978 / **+36** | **+7,473** |
| Lucas | 2/0 | 76,981 / +11,281 | 2/0 | 69,773 / +4,129 | **-7,208** |
| Alexander | 2/0 | 66,300 / +3,778 | 2/0 | 71,448 / +7,912 | **+5,149** |

W3 (selective predictive/value ordering) is 2/0 against Pedro at +419 and
0/2 against Jayveer at -3,262. W3dG sacrifices some Pedro/Jayveer competitive
edge for lower misses. Pedro becomes narrowly positive on aggregate, but not in
both seats; Jayveer improves dramatically but remains a clear loss. Lucas is a
large transfer regression.

## Fresh validation

### Selection and first unseen panel

Selection used 32 games per candidate. W3 and W3d advanced as the only two
finalists. In the first 60-game unseen panel W3 reached 56/4, 80,167 money,
+3,382 paired own money in the hard pool, and +609 P10; W3d reached 55/5,
80,707 money, +4,012 hard-pool own money, and +1,660 P10. W3d's direct paired
own-money delta was +7,722. This initially looked promotable.

The separate guarded confirmation below used a new seed range. Since the guard
only removes already-satisfied animal no-ops, its economic result is a transfer
confirmation of the same W3d policy. It failed to reproduce the positive tail
or hard-pool own-money result. The disagreement between independent panels is
why the earlier positive P10 is not treated as conclusive.

### Guarded final panel

This is 60 fresh games: 8 exact-loss traces, 16 direct games versus W0, and 36
games against nine hard/replay-derived opponents. Both seats were used.

| Metric | W0 | W3dG | Change |
| --- | ---: | ---: | ---: |
| W/L/T | 40/20/0 | **48/12/0** | +8 wins |
| Average money | 87,573 | **89,420** | **+1,847 (+2.1%)** |
| Average advantage | +27,065 | +26,469 | -595 |
| Paired P10 advantage | -4,758 | **-1,709** | +3,049, still negative |
| Critical miss rate | 1.60% | **1.06%** | -0.55 pp |
| Crop harvests | 231.5 | **248.3** | **+16.8** |
| Strawberry harvests | 147.5 | **167.9** | +20.4 |
| Crop revenue | 52,058 | **58,721** | **+6,663 (+12.8%)** |
| Day 10–20 crop revenue | 15,268 | **16,151** | +882 |
| Day 21–29 crop revenue | 36,539 | **42,319** | +5,780 |
| Replant latency | 15.0 | **13.3** | -1.7 |
| Crop revenue / crop turn | 42.41 | **55.56** | +31.0% |
| Invalid actions | 59 | **0** | candidate clean |
| Livestock losses | 22 | **0** | candidate clean |
| Max stranded value | 110 | **0** | candidate clean |

The paired own-money deltas are +3,925 on exact losses, +6,320 directly versus
W0, but **-602** in this fresh hard pool. Directly, W3dG is 13/3 with +4,640
competitive advantage; direct paired P10 is still -1,581.

W3dG's debt remains higher (26.75 versus 16.61), inherited emergency waters
remain higher (377 versus 122), and backlog remains higher (8.78 versus 5.70).
It succeeds by using fewer waters per crop harvest and completing more valuable
cycles, not by eliminating debt.

### RNG audit

The larger audit uses 16 unseen seeds, both seats, against the frozen agent:
32 controlled-shop and 32 natural-RNG games per candidate.

| RNG regime | W3dG W/L/T | Competitive adv. | Paired own-money delta | P10 |
| --- | ---: | ---: | ---: | ---: |
| Controlled shops | 24/8/0 | +3,238 | **+3,999** | **-4,810** |
| Natural RNG | 18/14/0 | +2,031 | **+2,406** | **-4,602** |

The average sign does not flip in the larger audit, so the gain is not merely a
fixed-shop artifact. The negative tail is persistent in both regimes and is the
main promotion blocker. A smaller preliminary natural panel did show an
own-money sign flip; increasing to 16 seeds resolved the mean but confirmed the
tail risk.

### Deliberate red team

W0 and W3dG were each tested in 32 fresh games (eight stress opponents, two
seeds, both seats): strawberry waves, mixed maturities, two animal-service
spikes, far-worker/fast-land deployment, low-cash reinvestment, phased crop
waves, and dense sheep/cow production.

| Candidate | W/L/T | Money | Advantage | P10 | Miss rate | Harvests | Crop rev. |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| W0 | 32/0/0 | 92,521 | +43,284 | +16,819 | 1.70% | 236.0 | 54,034 |
| W3dG | **32/0/0** | **95,412** | **+44,785** | **+20,640** | **0.91%** | **249.6** | **60,501** |

W3dG gains 2,891 paired own money and has zero invalid actions, livestock
losses, or stranded value. It survives these constructed pressures. This does
not override the harder direct/exact negative P10 or the Jayveer/Lucas transfer
failures.

## Answers to the research questions

1. **Capacity freed:** six cows save 132.3 animal-service turns in the exact
   screen.
2. **Where it goes:** +75.5 recorded crop actions, +122.6 movement/access
   actions, +16 harvests, and a larger maintained crop economy.
3. **Emergency cause:** recurring strawberry cohorts dominate inherited debt;
   daily cohort waves and territory load imbalance create the day-17/18 and
   day-22/23 pressure spikes.
4. **Predictability:** tomorrow's critical set is visible one day ahead, but an
   early action within a day creates no multi-day watering reserve.
5. **Does predictive watering reduce emergencies?** No. Selective W3 increases
   emergency execution while lowering deaths. The genuinely proactive W3e
   reduces emergencies but loses harvests and money.
6. **Does local batching help?** No. W4 and local-borrow variants regress.
7. **Does proactive watering steal harvests?** Yes: W3e loses 20.9 harvests
   versus W1 despite much shorter replant latency.
8. **Harvest backlog:** W1 is 6.1; W3/W3d rise to 8.3/8.9. Better deadline
   execution does not lower the observed backlog.
9. **Natural replant latency:** six cows alone improves 16.6 to 9.7. W3d is
   10.7 in the exact screen and 13.3 broadly. W3e reaches 4.9 but is economically
   worse. No forced chain was used.
10. **Optimal cow count:** six among 6/7/8/9 under the selected scheduler.
11. **Crop revenue gain:** W3dG gains 6,663 (+12.8%) in the guarded final panel;
    only 882 is days 10–20, while 5,780 arrives days 21–29.
12. **Jayveer:** no. The deficit narrows from -9,280 to -4,442, but both seats
    remain losses.
13. **Pedro:** marginally on aggregate (+36, 1/1), while W3 wins both seats at
    +419. This is not robust enough to call solved.
14. **Controlled RNG:** +3,999 paired own money, +3,238 competitive advantage,
    but P10 -4,810.
15. **Natural RNG:** +2,406 paired own money, +2,031 competitive advantage, but
    P10 -4,602. No mean sign reversal in the larger audit.
16. **Strongest candidate:** W3dG, the guarded six-cow strict-deadline policy.
17. **Submission-worthy?** No. The gain is real but the central debt-prevention
    hypothesis is disproved, P10 is negative, misses remain above target,
    harvests remain below target, and Jayveer/Lucas transfer is unresolved.

## Final interpretation

The useful mechanism is not “water cheaply now to avoid expensive emergency
watering later.” The game only remembers the daily refresh, and excessive safe
watering consumes the exact actions needed for harvests. The stronger policy is
closer to **just-in-time deadline execution**: reduce the herd to six, skip
low-value redundant watering, protect one-time yield windows, and service true
deadlines reliably. That increases revenue per crop-worker turn and aligns
watering with harvest waves.

The remaining gap to strong public agents is spatial/deadline reliability:
W3dG still travels farther, crosses territories more, and misses about three
times as often. A future study should target stable workload admission and
deadline ownership without increasing preventive water actions. That is a
different hypothesis and should not be folded into this frozen experiment.

## Artifacts

- Machine summary: `experiments/predictive_watering_research.json`
- Exact requested revenue windows: `experiments/predictive_watering_exact_windows.json`
- Top/current diagnosis: `experiments/predictive_watering_diagnosis.json`
- Initial W0–W4 screen: `experiments/predictive_watering_screen.json`
- Local and protected batching: `experiments/predictive_watering_local_screen.json`,
  `experiments/predictive_watering_protected_screen.json`
- Policy and cow screens: `experiments/predictive_watering_policy_screen.json`,
  `experiments/predictive_watering_cow_ablation.json`
- Selection and unseen validation: `experiments/predictive_watering_selection.json`,
  `experiments/predictive_watering_final.json`,
  `experiments/predictive_watering_guarded_final.json`
- RNG: `experiments/predictive_watering_rng.json`,
  `experiments/predictive_watering_rng_final.json`
- Stress audit: `experiments/predictive_watering_redteam.json`
