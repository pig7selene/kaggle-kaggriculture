# Three-hour early-compounding research report

## Decision

Promote `agents/animal_c8_day12_land_day11.py` as the new local best. It passed
the requested large-improvement bar on disjoint held-out seeds and remained
safe under semantic validation and red-team play. `submission/main.py` was not
modified and nothing was submitted to Kaggle.

## 1. Total simulations run

The session ran **6,070 full 720-turn games**. The main retained artifact
contains 6,060 search/validation games:

- 12 matched traced diagnosis games
- 640 broad joint-screen games
- 2,296 joint-refinement games
- 1,344 capital/labor-refinement games
- 280 direct red-team games
- 480 prefinal hard-pool games
- 1,008 held-out games

The other ten were eight traced economic-decomposition games and two saved-file
action-equivalence/safety audits.

All search and validation matchups used both seats. Seed ranges were disjoint:
diagnosis 11000–11001, broad 11100–11101, refinement 11120–11121,
capital/labor 11140–11142, red-team 11200–11203, prefinal 11220–11222, and
held-out 11300–11311.

## 2. Main configurations tested

- **32 broad joint policies:** fixed four cows, six cows on days 8/10/11,
  staged 4→6 and 4→8 transitions, land days 8/10/11/12/14 or dynamic ROI,
  5/6/7/8 hands, and 12/16-plot expansions.
- **82 local refinements:** adjacent land days, 12/16/20 plots, adjacent labor
  levels, 2/3/4 animal workers, bank gates, and second cow-transition timing.
- **32 capital/labor refinements:** deferred structures, fixed versus
  workload-based labor, animal worker count, and bank thresholds.
- **35 red-team mutations:** 4/6/8 cows on days 7–13, staged 4→6/8 policies,
  land days 8–13, 5–8 hands, 12/16/20 plots, and cow bank gates.
- **Eight prefinal contenders** and **three distinct held-out finalists**.

The frozen phased crop logic and adaptive new-land allocation were retained.
The existing engine already harvests melons on their first yield day, so a
supposed “earlier melon liquidation” at days 10–12 produced identical actions
and was abandoned.

## 3. Why the known exploiters beat the old best

Four matched games per exploiter were traced day by day with executed market
transactions.

| Exploiter | Durable economic-position lead | Durable income lead | Durable bank lead | Mechanism |
| --- | ---: | ---: | ---: | --- |
| `gen_cow6_d8` | day 23 | day 22 | day 29 | It attempts cows too early and even loses/rebuys them, but ultimately carries two extra cows plus day-11 land; the larger late milk/fertilizer stream overcomes its wasted early capital. |
| `gen_land_d11_labor7_sell12` | day 20 | day 26 | day 28 | It spends about 2,531 extra on day 11, creates 10–15 extra productive tiles immediately, and builds an inventory-value lead of roughly 8,131 by day 26 before liquidation. |
| `gen_land_d8_labor6` | day 20 | day 20 | day 28 | Its requested day-8 purchase is actually delayed by capital/ROI gates to day 11. The real edge is 16 expansion plots and six-hand capacity, producing an inventory lead of roughly 8,555 by day 26. |

The common weakness was not market prediction. P0 deployed the first major
melon cash flow too conservatively: only four cows and a smaller day-14
expansion. Earlier productive capacity accumulated value off-bank and appeared
as cash only during late liquidation.

## 4. Strongest new configuration

`agents/animal_c8_day12_land_day11.py`:

- existing phased melon → strawberry → wheat crop schedule
- one ROI-validated 12-plot quadrant, scheduled and actually bought on day 11
- all eight cows targeted and placed on day 12
- pastures start on day 11, avoiding wasted opening movement
- eight hired hands after expansion; four are dedicated animal-service workers
- daily feed/care/fertilizer collection and two-day market-wheat reserve
- existing adaptive new-land crop allocation and inventory-aware animal selling
- no second quadrant

## 5–9. Held-out result and promotion metrics

Each finalist played **336 games**: 14 opponents × 12 unseen seeds × both
seats. The pool included P0, the three known exploiters, historical hard
proxies, cow baselines, and three newly retained red-team strategies.

| Finalist | W/L/T | Avg money | Avg advantage | Raw-game P10 | Seed-averaged P10 | Productive tiles | Direct vs P0 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Eight cows day 12** | **319/11/6** | **64282.1** | **+26485.7** | **+2715.0** | **+24889.7** | **22.22** | **24/0/0, +15978.0** |
| Staged 4→8 day 16 | 296/40/0 | 63712.9 | +23827.5 | -1179.0 | +21827.1 | 21.86 | 24/0/0, +16381.8 |
| Frozen P0 | 176/148/12 | 49168.9 | +8894.8 | -14339.0 | +7631.5 | 18.04 | 6/6/12, +0.0 |

The raw-game P10 is the conservative statistic used for the promotion decision.
The saved search artifact additionally reports P10 after averaging both seats
and all opponents within each seed; that seed-level robustness statistic is
shown separately to avoid conflating the two distributions.

**Old versus new average money:** 49,168.9 → 64,282.1, a gain of
**15,113.1 coins (+30.74%)**.

The nominal worst matchup is self-play against the identical retained
`red_cow8_d12` policy: 9/9/6 and exactly zero average advantage. Excluding the
mirror, the weakest matchup is `red_stage_11_15_8`: 23/1/0, +3,540.9 average
advantage, with +932.1 matchup P10. There is no catastrophic opponent.

## Economic decomposition versus P0

Eight additional matched direct games on seeds 11410–11413 produced:

| Season total | New | P0 | Delta |
| --- | ---: | ---: | ---: |
| Crop revenue | 34806.5 | 28292.9 | +6513.6 |
| Milk revenue | 28573.6 | 15569.2 | +13004.4 |
| Fertilizer revenue | 10650.8 | 5254.1 | +5396.6 |
| Seed spending | 4397.5 | 3878.8 | +518.8 |
| Cow spending | 3200.0 | 1600.0 | +1600.0 |
| Labor spending | 1048.0 | 220.0 | +828.0 |
| Land spending | 1000.0 | 1000.0 | +0.0 |
| Feed spending | 5820.1 | 3139.8 | +2680.4 |
| Final money | 61565.2 | 42277.8 | **+19287.5** |

The new policy is initially behind after buying land and eight cows. Its
bank-plus-inventory lead becomes durable around day 19, cumulative-income and
bank leads become durable around day 21, and the lead expands through milk,
fertilizer, and the earlier crop quadrant.

## 10. Best cow timing/count

**Eight cows together on day 12.** This beat the initially selected 4→8 day-16
policy directly during red-team search by 6–2 and +5,115.6. Moving the second
tranche to day 15 also beat day 16, but the all-eight day-12 policy was more
robust in the expanded prefinal and held-out pools.

Raw day-8 or day-10 six/eight-cow attempts were unsafe: they purchased before
feed/service capital was ready, lost cows, and sometimes repurchased them.
Bank-gated six-cow variants avoided escapes but remained below eight cows.

## 11. Best land timing

**Day 11**, one 12-plot quadrant. Day-10 policies were usually capital-gated to
the same actual day 11. Day 12 lost a production day. Sixteen plots maximized
some development means, but 12 plots had the stronger direct and worst-matchup
margins. Twenty plots overloaded the routing/labor system and regressed.

## 12. Best labor policy

**Eight post-expansion hands, four dedicated to animal work.** Held-out season
labor cost averaged 1,048 coins and average hands over the whole season were
5.72. Four animal workers were essential: two- and three-worker variants lost
large amounts of income even when cows survived.

Workload-based hiring reduced labor cost to 759 but lost about 997 average
coins in the capital/labor screen. Seven hands also regressed. Deferring pasture
construction until day 10/11 reduced wasted opening movement and improved the
staged candidate.

The final agent still averages about 2,489 movement actions and 1,035 passes,
so worker-region routing remains an optimization opportunity. A more complex
path planner was not justified during this session because simple dedicated
animal workers already delivered the large gain.

## 13. Important failed ideas

- Ungated day-8/day-10 cow purchases caused avoidable escapes and repurchases.
- Fixed six cows and staged 4→6 were materially weaker than eight cows.
- Twenty expansion plots and seven hands both regressed.
- Two or three animal workers left too much animal-service opportunity on the
  table; four were much stronger.
- Workload-based labor saved coins but reduced final income.
- Cow bank thresholds up to 8,000 were inert once the correct day was chosen;
  an 11,000 threshold delayed investment and was exploitable.
- “Earlier melon liquidation” was not a real lever because P0 already harvests
  melon at its first yield day.
- The first staged day-16 finalist looked locally unbeatable but was broken by
  the all-eight day-12 red-team mutation.

## 14. Remaining exploitable weakness

The narrowest non-mirror matchup is the staged 4→8 day-15 opponent, although
the new policy still wins it 23–1 with positive P10. The strategy remains
capital-intensive and dependent on market-bought wheat, four dedicated animal
workers, and a large milk/fertilizer economy. A stronger opponent that combines
similar early cow scale with milk-market pressure or wheat-price pressure may
reduce the edge. Movement/pass counts also show unused labor efficiency.

## 15. Kaggle submission evidence

**Yes—the improvement is large enough to justify preparing another Kaggle
submission in a separate packaging step.** It exceeds both preferred promotion
thresholds, holds on unseen seeds, survives a harder red-team pool, has positive
P10, and recorded zero runtime failures, invalid actions, avoidable cow escapes,
or stranded valuable inventory.

This session did not modify `submission/main.py` and did not submit to Kaggle.

Complete retained artifacts are `experiments/3h_compounding_search.json` and
`experiments/3h_policy_league.json`; the latter maps the frozen and newly
discovered hard policies to reusable agent files.
