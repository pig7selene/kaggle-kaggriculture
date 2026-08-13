# Harvest-to-replant pipeline research

## Decision

The frozen best remains `agents/lifecycle_lc_combined.py`. This research did
not modify `submission/main.py`, did not submit to Kaggle, and did not change
`experiments/current_best.json`.

The strongest research candidate is `agents/replant_cow6_guarded.py`. It
improves crop throughput substantially by reclaiming worker time from three
cows, but it does not pass the promotion rule: its fresh direct P10 is negative
and its natural-RNG head-to-head advantage is slightly negative. The most
effective literal pipeline mechanism, exact same-worker chaining, reaches the
public latency regime but lowers profitable completed cycles.

## 1. Exact diagnosis: where the long delay comes from

The earlier 23-turn headline came from the lifecycle-debt metric, which starts
replacement debt when a plant is harvested, lost, or expires. The new event
replay measures the narrower requested quantity: successful destructive
harvest action to successful replant action, following replants through day 29.
On the frozen Jayveer and Pedro traces it finds 113 one-time harvests, 111
replants, and a **10.96-turn mean / 1-turn median / 26-turn P90**. Thus the
23-turn figure is still valid for the broader dead-tile lifecycle, while 10.96
is the directly observed completed-harvest pipeline latency.

| Excess-delay cause | Share | Interpretation |
| --- | ---: | --- |
| Watering emergency | **51.63%** | Critical refresh work displaces planting after the harvest |
| Scheduler priority | **17.00%** | The empty harvested tile loses to other ordinary tasks |
| Harvest backlog | **11.39%** | Other mature crops remain ahead of replacement |
| Shed travel | **7.32%** | Harvest product return, especially the day-10 melon cash wrapper |
| Territory assignment | **6.33%** | The relevant worker/slot falls outside the active partition |
| Animal service | **3.62%** | A crop worker becomes or assists an animal specialist |
| Worker leaves territory | **2.08%** | Unnecessary quadrant departure not already classed as shed travel |
| No seed available | **0.63%** | The economically chosen replacement seed is missing |

The tail is concentrated, not universal. **81.98%** of completed replants are
already immediate and 85.59% complete within 20 turns. Melon is the failure:
17 events average 43.0 turns (median 21), compared with wheat's 5.9 and
carrot's 1.0. Days 10 and 11 contain the worst events. Examples include NW
melons at `(1,4)` delayed 143 turns and `(0,4)` delayed 158 turns. The first
concrete divergence is that the opening cash-return override sends the
harvester toward the shed; on the next day worker identities/territories are
recreated and watering plus animal work keep the cleared NW tile out of the
queue.

Seeds are **global `private.seeds`**, never worker-carried. Consequently:

- “seed held by the wrong worker” is impossible;
- distance to a seed source is always zero when a seed exists;
- seed-related shed trips and seed-retrieval movement are exactly zero;
- the correct eventual replacement seed was already available after market
  processing in 99.10% of our completed events.

The harvester left its quadrant in 12.61% of completed events. A different
worker was estimated able to arrive sooner in 18.02%, but reliable hand
identity only persists within a day. Of the 91 within-day or main-farmer events
where identity is reliable, the same-worker rate is 100%; the bad tail mostly
crosses a day boundary and loses that continuity.

## 2. Why public agents reach about 2.5 turns

The same analyzer covered 35 selected high-rating appearances: 2,931
destructive harvests and 2,802 observed replants, plus 4,621 ongoing strawberry
harvests that do not empty their tile.

| Metric | Frozen exact traces | Top 35 appearances |
| --- | ---: | ---: |
| Mean harvest-to-replant | 10.96 | **2.79** |
| Median | 1 | **1** |
| P90 | 26 | **1** |
| Immediate next-turn | 81.98% | **95.11%** |
| Within 2 / 5 / 10 / 20 turns | 81.98 / 81.98 / 81.98 / 85.59% | **95.18 / 95.32 / 95.75 / 97.18%** |
| Correct seed globally available | 99.10% | **99.96%** |
| Same worker, reliable subset | 100.0% | **99.52%** |
| Harvester leaves quadrant | 12.61% | **2.46%** |
| Another worker could be sooner | 18.02% | **4.85%** |

The mechanism is therefore primarily **C: harvest/replant task chaining**.
Public agents leave the harvester on the newly empty tile and request PLANT on
the next callback. This is not literal seed preloading (A), because seeds cannot
be carried. Predictive positioning (B) is secondary: the prior corpus audit
measured only 13.47% top pre-positioned approaches versus 11.34% ours, and the
isolated predictive ablation was action-for-action neutral. Cohorts (D) and
territories (E) shape the favorable conditions—top median planting cohort is
eight contiguous tiles and quadrant exits are rare—but the per-tile one-turn
handoff is the direct explanation.

Public agents use local cohorts, but not a harvest-all-then-replant sweep as a
universal rule. Their 95% one-turn rate means the dominant primitive is
`HARVEST A -> PLANT A`, repeated through a coherent territory. A forced
three-tile cohort ordering in our scheduler reduced locality and watering
safety rather than reproducing this behavior.

## 3. Isolated pipeline ablations

The opening, land schedule, opponent model, crop economics, and selling policy
were frozen. P0 is an action-equivalent research copy of the current best
(719/719 actions in its equivalence check). The initial screen used Jayveer and
Pedro exact traces in both seats.

| Variant | Mechanism | Money | Replant mean / P90 | <=2 | Harvests | Crop revenue | Critical miss | Verdict |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| P0 | Frozen control | 60,161 | 11.40 / 26.9 | 81.6% | 237.8 | 41,522 | 2.01% | Control |
| P1 | Forecasted global seed reserve | 60,150 | 10.41 / 21.2 | 85.2% | **239.5** | **41,830** | 2.07% | Small screen gain; no transfer |
| P2 | 1–3 turn predictive positioning | 60,161 | 11.40 / 26.9 | 81.6% | 237.8 | 41,522 | 2.01% | Exact no-op |
| P3c | Exact same-worker next-turn chain | 59,626 | **4.03 / 1.0** | **96.1%** | 232.0 | 40,860 | 2.61% | Latency solved, economics worse |
| P3d | Remembered harvested tile, 5 turns | 59,500 | 9.42 / 23.3 | 81.5% | 234.0 | 40,827 | 2.10% | Reject |
| P3e | Workload-gated exact chain | 59,860 | 8.20 / 17.9 | 86.4% | 234.5 | 41,280 | 2.43% | Reject |
| P3g | Extend frozen stationary chain to h23 | 59,518 | 7.99 / 20.3 | 84.6% | 231.8 | 40,789 | 2.71% | Reject |
| P3i | Crop-only exact chain through h21 | 59,910 | 7.95 / 17.3 | 86.5% | 233.8 | 41,379 | 2.38% | Reject |
| P4 | Three-tile cohort priority | 57,131 | 11.26 / 25.6 | 81.7% | 214.2 | 38,277 | 3.08% | Strong reject |
| P5 | Unproven mechanisms combined | 60,252 | 30.90 / 102.4 | 30.0% | 221.8 | 40,569 | 1.40% | Strong reject; not advanced |

The exact chain proves causality but also proves why latency cannot be optimized
alone. The frozen scheduler already performs safe stationary replacement
through hour 21. Forcing more replants creates future watering demand and steals
actions from ready ongoing strawberry harvests. In the four-real-loss transfer
test P3c cut latency 16.58 -> 5.02, yet cut harvests 236.1 -> 232.5, crop
revenue 36,838 -> 36,389, and worsened critical misses 1.70% -> 2.44%.
Its aggregate advantage changed from +323 to -238. It helped neither Jayveer
nor Pedro economically.

P1 is also not worker seed preloading; it is a small global seed purchase
reserve based on imminent destructive harvest count. Across all four real-loss
traces it changed mean money by -299, improving Jayveer but regressing Pedro,
Lucas, and Alexander. It was not combined with rejected mechanisms.

## 4. Livestock opportunity cost

Because crop time is the real scarce resource, the requested 6/7/8/9-cow
ablation used the frozen scheduler with no pipeline change. Results below are
the eight exact real-loss games (four opponents, both seats).

| Cows | Money | Crop rev | Animal rev | Animal turns | Crop turns | Harvests | Replant | Critical miss |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **6** | **69,095** | **39,930** | 52,075 | **591** | **1,304** | **252.1** | **9.66** | 1.29% |
| 7 | 68,492 | 38,324 | 53,288 | 657 | 1,278 | 245.8 | 18.57 | **0.63%** |
| 8 | 66,644 | 37,418 | 53,404 | 695 | 1,253 | 238.2 | 13.78 | 1.48% |
| 9 (P0) | 65,901 | 36,838 | **54,301** | 724 | 1,228 | 236.1 | 16.58 | 1.70% |

For the sixth-to-ninth cow block, the extra animal revenue is about +2,226,
but crop revenue falls about 3,092 and final money falls 3,194. It consumes
about 133 more animal-service turns and removes about 76 crop turns. Those lost
crop turns compound into 16 fewer completed harvests. Six cows is therefore the
best count in this controlled architecture. Seven has the lowest miss rate but
does not maximize money or crop completions.

The guarded six-cow file suppresses duplicate animal terminal requests that
are silent no-ops; this does not change money or field behavior. Final
confirmation recorded zero runtime failures, semantic failures, invalid/no-op
actions, livestock losses, and stranded final value.

## 5. Real-loss transfer

| Opponent | P0 money / advantage | Six-cow money / advantage | Own-money change |
| --- | ---: | ---: | ---: |
| Jayveer | 57,817 / -9,280 | 66,345 / -6,615 | **+8,528** |
| Pedro | 62,505 / -4,486 | 69,640 / -341 | **+7,135** |
| Lucas | 76,981 / +11,281 | 69,065 / +3,397 | **-7,916** |
| Alexander | 66,300 / +3,778 | 71,329 / +8,199 | **+5,029** |

Six cows materially improves the two priority losses and nearly closes Pedro,
but still loses both seats to Jayveer and Pedro. Lucas remains a win but is a
large own-income regression. This is the main transfer caveat.

## 6. Fresh confirmation, RNG, and red team

Fresh held-out confirmation used seeds starting at 995000, both seats, the
current best, all four exact losses, and the 13-opponent hard/replay league.

| Candidate | Games | W/L/T | Avg money | Avg advantage | P10 paired advantage | Harvests | Crop revenue | Miss | Runtime / semantic / invalid | Losses / stranded |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| P0 | 50 | 38/12/0 | 75,453 | +21,962 | 0 | 233.7 | 48,783 | 1.58% | 0 / 0 / 0 | 13 / 104 |
| **Six-cow guarded** | **50** | **38/12/0** | **80,482** | **+24,313** | **-2,939** | **253.0** | **53,569** | **1.33%** | **0 / 0 / 0** | **0 / 0** |

The candidate gains 5,029 average money overall. Paired own-money gains are
+3,194 on exact losses, +3,934 directly, and +6,268 in the hard pool. Directly
it is 8/8 with +2,658 average game advantage and +3,934 own money, but its
direct paired P10 is -2,981. Its worst real matchup remains Jayveer (-6,615).

The broader fresh red team (68 games per candidate) stresses the top-meta
mirrors, replay-derived pressure agents, high labor, land expansion, livestock,
and direct current-best play. Six cows improves the record 49/13/6 ->
58/10/0, harvests 231.6 -> 252.3, crop revenue 51,556 -> 56,212, critical
misses 1.40% -> 1.23%, movement/cycle 14.58 -> 13.95, and completed
cycles/worker-day 0.631 -> 0.660. Its weakest programmable matchups are the
Jay and Pedro replay-inspired traders, both approximately neutral across four
seat-games rather than catastrophic. Productive tile-hours rise 13,826 ->
14,747. The red-team direct seed set is variable: +3,873 paired own money on
average, but two seeds lose roughly 5–6k.

The eight-seed RNG audit gives the reason not to promote:

| Schedule | Paired own-money delta | Head-to-head advantage | W/L/T |
| --- | ---: | ---: | ---: |
| Fixed shops | **+2,198** | +467 | 6/10/0 |
| Natural coupled RNG | **+3,720** | **-277** | 6/10/0 |

The own-economy gain survives both RNG regimes, so it is not a fake income
artifact. The competitive sign does not: shared-market interaction makes the
natural head-to-head slightly negative and P10 is -6,568 there. The candidate
also fails the explicit positive-P10 promotion requirement.

Red-team scenarios map to existing hard agents: aggressive strawberry creates
harvest/watering waves; Jay/Pedro archetypes stress market and maturity timing;
high-labor and land-expander stress deployment; animal-heavy agents stress
service/product markets; fixed and natural shop schedules stress low seed
inventory and demand coupling; exact traces include mixed maturity and the
day-10 land transition; every game includes late-game horizon and liquidation.
No forced-chain candidate survived even the cheaper screen, so none was exposed
to a wasteful large validation.

## 7. Answers to the research questions

1. **Why ~23 turns?** The broad lifecycle-debt mean includes lost/expired crop
   slots. Direct successful harvest-to-replant delay is 10.96. Its tail is
   concentrated in day-10/11 NW melons after cash-return travel, worker
   reassignment, and subsequent watering debt.
2. **Cause percentages?** Seed 0.63%; worker leaving 2.08%; animal 3.62%;
   watering 51.63%; backlog 11.39%; scheduler 17.00%; shed 7.32%; territory
   6.33%. Seed-held-by-wrong-worker is impossible.
3. **Why top ~2.5?** They preserve same-tile, same-worker next-turn continuity
   for about 95% of destructive harvests and rarely leave the quadrant.
4. **Preloaded seeds?** No worker preloading exists in this game. Global seed
   availability is already 99.10% ours and 99.96% top.
5. **Pre-positioning?** Modest in the corpus and an exact no-op in the isolated
   ablation; not the primary mechanism.
6. **Cohorts?** Top crops are spatially coherent cohorts, but their event trace
   is dominated by same-tile immediate replant, not harvest-three/replant-three.
7. **Strongest isolated latency mechanism?** Exact same-worker chaining:
   11.40 -> 4.03 turns and P90 26.9 -> 1.0.
8. **Lowest safe latency?** No new chain met the safety bar. The best safe
   architecture result is six cows at about 9.5–10.1 turns, achieved by freeing
   capacity rather than forcing PLANT.
9. **Harvest improvement?** Six cows adds about 19–21 harvests in fresh pools;
   exact forced chaining loses about four.
10. **Crop-revenue improvement?** Six cows adds 4,786 in held-out confirmation
    and 4,656 in red team. Forced chaining loses 449 on exact traces.
11. **Optimal cow count?** Six in this controlled architecture.
12. **Jayveer?** Yes, +8,528 own money and disadvantage -9,280 -> -6,615, but
    it still loses.
13. **Pedro?** Yes, +7,135 own money and disadvantage -4,486 -> -341, but it
    still narrowly loses.
14. **RNG audit?** Own-income improvement persists; competitive advantage
    reverses slightly under natural RNG and tail risk remains negative.
15. **Strongest final candidate?** `agents/replant_cow6_guarded.py`, research
    only. The frozen current best remains `agents/lifecycle_lc_combined.py`.
16. **Enough for submission?** **No.** Throughput evidence is compelling, but
    negative P10, 8/8 direct rather than a reliable win, a natural-RNG negative
    head-to-head, and continued Jayveer/Pedro losses fail the stated bar.

## Artifacts and reproducibility

- Exact event corpus: `experiments/replant_pipeline_diagnosis.json`
- Initial/targeted/cohort screens: `experiments/replant_pipeline_screen.json`,
  `replant_pipeline_safe_chain_screen.json`,
  `replant_pipeline_targeted_screen.json`,
  `replant_pipeline_bounded_screen.json`, and
  `replant_pipeline_cohort_screen_v2.json`
- Four-loss transfer: `experiments/replant_pipeline_real_traces.json`
- Cow isolation: `experiments/replant_pipeline_cow_pipeline_isolation.json`
- Fresh confirmation: `experiments/replant_pipeline_confirmation.json` and
  `experiments/replant_pipeline_guarded_confirmation.json`
- Red team/RNG: `experiments/replant_pipeline_redteam.json` and
  `experiments/replant_pipeline_rng.json`
- Consolidated machine-readable result: `experiments/replant_pipeline_research.json`

