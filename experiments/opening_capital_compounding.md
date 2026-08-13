# Day 0-10 capital-compounding reconstruction

## Scope and frozen boundaries

This experiment isolated the opening. `submission/main.py`, opponent-awareness logic, and `agents/large_scale_router.py` were not modified. The public evidence was reconstructed before candidate work. Candidate-specific scheduling and compact pasture handling apply only through day 10; later play uses the existing replay crop phases, labor caps, selling policy, and unchanged territory router. The mixed herd necessarily remains part of the post-opening state.

The frozen comparison agent was `agents/router_replay_hands12.py` (SHA-256 `bac81a2099f3c4b7f97670a4e25d8cb0cc1c22fd23a41310096dd792b2f8f99b`). The strongest opening candidate is `agents/opening_public_front_cow8_day6.py` (SHA-256 `3ede0041921010b0136abb538395faa5951e9af1fb9b76be41467246885da6a8`). No registry or submission artifact was changed.

## Replay evidence

The exact analyzer audited all 35 selected appearances in the existing 25-replay top-player corpus with zero reconstructed-bank mismatches. Four representative episodes render eight strong-player openings turn by turn:

| Episode | Seed | Seat 0 | Seat 1 |
|---:|---:|---|---|
| 91866168 | 1050733733 | Abracadabra | Erfan Eshratifar |
| 91869967 | 122449146 | Valmorlee | Dmitry Larko |
| 91870919 | 1977148940 | THUNDER THUNDER | Victor @ Tufa Labs |
| 91870920 | 1182001269 | Ueddy | Abracadabra |

The complete per-turn records—including exact hour, bank before/after, successful plant/harvest/build/place actions, purchases, hires, sales, quantities, realized unit prices, and spending—are in `experiments/opening_capital_flow_top.json` and `experiments/opening_capital_flow_top.md`.

## Public opening: day-by-day cash flow

These medians use the eight rendered appearances; farm-state checkpoint medians over all 35 appearances are consistent with them.

| Day | Bank start → after day | Median sales | Median spending | Main cash event | Productive state after day (35-appearance median) |
|---:|---:|---:|---:|---|---|
| 0 | 3000 → 18 | 0 | 2998 | Buy 1 cow, 4 sheep, 5 wheat seeds, 5 melon seeds, opening feed, and 4-5 hands | 10 crops + 5 animals, 1 quadrant |
| 1 | 18 → 17 | 0 | 1 | Hire one hand; deliberately tolerate one safe missed-feed day | 10 crops + 5 animals |
| 2 | 17 → 184 | 496 | 329 | First five-animal fertilizer liquidation funds feed and labor | 10 crops + 5 animals |
| 3 | 184 → 185 | 486 | 472 | Add about 3 strawberry and 1 wheat lanes | 14 crops + 5 animals |
| 4 | 185 → 543 | 476 | 119 | Fertilizer accumulates cash; harvest/replant the persistent wheat lanes | 14 crops + 5 animals |
| 5 | 543 → 511 | 991 | 1029 | Fertilizer + wheat fund cow 2 and the NW fill | 19 crops + 6 animals |
| 6 | 511 → 34 | 1776 | 2274 | First wool parcel plus fertilizer buys deed 1 and continues the cow ramp | 20 crops + 7 animals, 2 quadrants |
| 7 | 34 → 727 | 2947 | 2236 | Remaining first wool payout funds cows and rapid first-expansion planting | 33 crops + 10 animals |
| 8 | 727 → 56 | 677 | 1341 | Reach roughly 8 cows while finishing the first expansion | 38 crops + 12 animals |
| 9 | 56 → 2087 | 2206 | 403 | First milk payout plus fertilizer creates deed-2 cash | 38 crops + 12 animals |
| 10 | 2087 → 5454 | 9494 | 6079 | Buy deed 2 at hour 0; later melon harvest funds 14 hands and new planting | 55 crops + 12 animals, 3 quadrants |

The opening is a deliberately staggered maturity ladder:

1. **Fertilizer is working capital.** Five opening animals create roughly 500 coins per daily liquidation, starting the first material return at day 2.
2. **Wheat is the short crop bridge.** Five cheap persistent lanes mature around day 4 and provide roughly 525 coins on the representative day-5 sale while also supporting feed.
3. **Sheep bridge the cow maturity gap.** Cows do not pay until around day 9. Four sheep produce the first wool at day 6; care compounding makes the first cycle approximately 20 wool units, normally sold as 5 units late on day 6 and 15 at day 7.
4. **Milk finances the second deed before melons.** The first six-unit milk payout arrives on day 9.
5. **Melons fund deployment, not the deed.** Deed 2 is normally bought at day 10/hour 0. The five-melon harvest and sale occur later that day and fund seeds plus rapid labor scaling.

## Where the money for each milestone comes from

Across all 35 appearances:

| Milestone | Observations | Typical exact time | Median bank before turn | Median cumulative revenue through event | Revenue decomposition |
|---|---:|---:|---:|---:|---|
| First land | 35/35 | day 6, hour 16 | 807 | 4242 | fertilizer 2649, wheat 542, wool 1051 |
| Eight cows | 32/35 | day 8, hour 12 | 65 | 8028 | fertilizer 3519, wheat 687, wool 3733 |
| Second land | 35/35 | day 10, hour 0 | 2165 | 12484 | fertilizer 4349, wheat 1159, wool 5439, milk 1050, melon 0 |

The first deed is purchased in the same turn as the first partial wool liquidation. The second deed is already cash-covered before any melon sale. The day-10 melon sale averages about 7412 coins in the representative sample and is immediately reinvested in labor and crop capacity.

## Matched comparison with the frozen router

Eight counterfactual games used each representative public seed and original seat. The other seat emitted its exact original public action trace. This controls seed, seat, and opponent intent, although changed market state can make some replayed opponent orders no-ops.

| Checkpoint | Public median | Frozen router median |
|---|---:|---:|
| Bank after day 4 | 542 | 1732 |
| Productive tiles after day 4 | 19 | 13 |
| Bank after day 6 | 34 | 890 |
| Quadrants after day 6 | 2 | 1 |
| Productive tiles after day 8 | 49.5 | 17 |
| Cows/sheep after day 8 | 8/4 | 5/0 |
| Bank after day 10 | 5454 | 554 |
| Quadrants after day 10 | 3 | 1 |
| Hands on day 10 | 14 | 4 |

The frozen router initially looks richer because it did not invest 2000 coins in sheep. That is idle accounting liquidity, not productive capital. The first repeatable return divergence is day 2/hour 0: public fertilizer revenue is about 496 versus 100 for the single-cow opening, a 396-coin gap. The frozen bank first falls below the matched public bank around day 6/hour 1 in six of eight runs and day 7/hour 1 in the other two. That is when the public wool/deed feedback loop becomes durable.

The causal deficit is not “land is too expensive.” The frozen opening lacks an asset that matures before cow milk. It therefore cannot simultaneously pay for feed, cows, the day-6 deed, new seeds, and labor. Its delayed melons cannot repair the lost days of productive capacity.

## Spatial and labor mechanism

The public replay layout is part of the economics:

- five day-0 pastures occupy compact shed-edge cells around `(4,4)`;
- the 5-wheat/5-melon block is contiguous farther from the shed;
- workers batch build → pickup → place → feed → care near the shed;
- persistent wheat lanes are replanted as wheat rather than replaced by expensive strawberries;
- only four new crop slots are funded on days 3-4, NW fills on day 5, and the first expansion ramps roughly 2 → 18 → 25 target slots on days 6-8.

The earlier local mixed proxy reversed this geometry, reserved central cells for crops, pushed sheep outward, took several days to place them, and caused escapes. A second failed prototype immediately bought all available strawberry slots; through day 4 it spent about 1020 coins more on seeds than the public opening, consuming the wool-to-land bridge. These failures demonstrate that animal choice alone is insufficient: compact service paths and staged seed commitments create the realized return.

## Controlled day-10 screen

The screen used fixed seeds 14200-14203, both seats, and three unchanged opponents (frozen current, the replay template, and an early-cow proxy), 24 games per configuration.

| Configuration | Bank d10 | Cows/sheep d8 | Land by d6 | Land 2 by d10 | No escapes | Main conclusion |
|---|---:|---:|---:|---:|---:|---|
| Frozen current | 518 | 5.0/0.0 | 0% | 0% | 0% | No early maturity bridge |
| Cow 1 ramp | 564 | 3.1/0.0 | 100% | 50% | 100% | Cannot fund both herd and second deed |
| Cow 5 opening | 187 | 2.0/0.0 | 0% | 33% | 96% | Cow-only capital remains locked until milk |
| Fertilizer delayed to d3 | 37 | 2.0/0.0 | 0% | 17% | 0% | Daily fertilizer liquidation is essential |
| Wool delayed to d7 | 3240 | 6.8/4.0 | 0% | 100% | 100% | First wool parcel is specifically the d6-deed trigger |
| Two-day feed reserve | 2313 | 6.3/4.0 | 0% | 100% | 100% | Extra reserve ties up deed capital |
| Survival-only feed | 685 | 4.6/2.6 | 100% | 79% | 17% | Safe day-1 skip cannot continue indefinitely |
| Early wheat at age 2 | 2317 | 6.2/4.0 | 100% | 100% | 100% | Sacrifices productive yield/tiles |
| 6 wheat / 4 melon | 2578 | 6.9/4.0 | 100% | 100% | 100% | More early cash, weaker day-10 burst |
| 4 wheat / 6 melon | 3427 | 6.7/4.0 | 100% | 100% | 100% | Strong, but below the five/five control |
| Public 5/5 template | 3490 | 6.8/4.0 | 92% | 100% | 100% | Reproduces both deeds robustly |
| Five day-0 hands | 3837 | 7.0/4.0 | 100% | 100% | 100% | Best broad-screen cash/setup control |

Funding the eight-cow target from the first wool window was then isolated. Five day-0 hands plus an eight-cow target beginning day 6 achieved the complete template—first deed, 8 cows + 4 sheep by day 8, second deed by day 10, and no escapes—in 83.3% of 24 search games. The failures were concentrated against the mirror replay-template opponent; every failure still had seven cows on day 8 and eight by day 10.

The fifth day-0 hand and day-6 eight-cow target are implementation compensations for the local router's placement latency. They are supported by controlled local results, not asserted as universal public meta.

## Full-season validation

Only the frozen control and two opening finalists advanced. Validation used seeds 15000-15005, eight frozen hard opponents, both seats, and 96 games per candidate. Fresh confirmation used disjoint seeds 15100-15107 for the validation winner, 128 games total.

| Candidate | Games | W/L/T | Score | Average money | Average advantage | P10 paired advantage | Worst matchup |
|---|---:|---:|---:|---:|---:|---:|---|
| **front cow-8 day-6** | **96** | **96/0/0** | **100%** | **107689** | **+71559** | **+25596** | frozen current |
| front five hands | 96 | 96/0/0 | 100% | 105572 | +69624 | +20562 | frozen current |
| frozen current | 96 | 88/4/4 | 93.8% | 85136 | +53229 | +0 | mirror |

Fresh held-out result for `opening_public_front_cow8_day6`: **128/0/0**, average money **102136**, average advantage **+67589**, P10 paired advantage **+29382**. Its weakest held-out matchup was the frozen current agent: **16/0/0**, average advantage **+19169**. No cow or sheep losses occurred in validation or held out. Maximum final valuable inventory was three units, so endgame handling is nearly complete but not yet an exact zero-stranding guarantee.

## Answer: why the public opening compounds and ours did not

Top openings convert nearly every starting coin into assets with different maturity dates. Fertilizer pays daily operating costs; wheat pays the first crop bridge; cared-for sheep create the day-6/day-7 capital burst; milk accumulates the day-10 deed balance; melons then fund mass deployment. Compact shed-edge animal routing makes the scheduled returns real, while staged crop slots prevent seed purchases from consuming the next milestone's principal.

The frozen opening instead concentrates on cows and long-cycle crops. It retains more nominal cash early but has only one fertilizer source, no day-6 wool event, later milk, no deed-funded capacity feedback, and insufficient labor growth. The first concrete efficiency divergence is five-animal versus one-animal fertilizer at day 2; the decisive divergence is sheep wool at day 6. By the time frozen melons/cows pay, the public policy already owns another quadrant, more animals, more labor, and more sale-producing tiles.

## Remaining uncertainty

- The eight named public players appear to share a closely related policy lineage, so 35 appearances are many market/seed observations but not 35 independent strategies.
- Counterfactual action-trace matches preserve intent rather than a fully reactive opponent; changed prices can invalidate some opponent orders.
- The local hard pool is still weaker than real high-rating Kaggle opponents. The large local gain is strong causal evidence for the opening mechanism, not a guaranteed leaderboard rating.
- The research candidate carries mixed livestock and a one-day feed policy beyond day 10 because those are consequences of the opening. No post-day-10 parameter search was performed.
- Up to three valuable units remained at episode end in held-out testing; this should be audited separately before any packaging decision.

The evidence is strong enough to treat `agents/opening_public_front_cow8_day6.py` as the strongest **research candidate** from this phase. It is not promoted or packaged here because this task did not authorize changing the registry or `submission/main.py`.
