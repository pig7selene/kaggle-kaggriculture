# Final opening adversarial validation

Frozen source: `agents/opening_public_front_cow8_day6.py`. Seeds 731001-731008 were fresh and used in both seats.

## Overall

- W/L/T: **248/8/0**
- Average money: **92716**
- Average advantage: **+50461**
- P10 paired advantage: **+44945**
- First land by day 6: **98.0%**
- Second land by day 10: **100.0%**
- Wool revenue days 6-7: **3933 avg**
- Milk revenue day 9: **1062 avg**; days 9-10 window: **1062 avg**

## Matchups

| Opponent | W/L/T | Avg money | Avg advantage | P10 | Land d6 | Land d10 | Wool d6-7 | Milk d9 / d9-10 | Animal-loss games | Stranded max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| sheep_wool_heavy | 16/0/0 | 96502 | +57744 | +33920 | 88% | 100% | 3708 | 1141 / 1141 | 0 | 3 |
| sheep_to_cow | 16/0/0 | 85282 | +30670 | +20701 | 88% | 100% | 3542 | 1209 / 1209 | 0 | 3 |
| cow_milk_heavy | 16/0/0 | 75808 | +28505 | +22313 | 100% | 100% | 4007 | 853 / 853 | 0 | 4 |
| fertilizer_liquidator | 16/0/0 | 97997 | +60140 | +45208 | 100% | 100% | 4021 | 736 / 736 | 0 | 3 |
| land_day5_day9 | 16/0/0 | 87331 | +24575 | +16198 | 100% | 100% | 4040 | 670 / 670 | 0 | 3 |
| fast_land_high_labor | 16/0/0 | 82361 | +26875 | +20177 | 100% | 100% | 4002 | 678 / 678 | 0 | 4 |
| high_labor | 16/0/0 | 96867 | +75067 | +58608 | 100% | 100% | 4158 | 1159 / 1159 | 0 | 2 |
| top_meta_mirror | 8/8/0 | 67176 | +0 | +0 | 94% | 100% | 3787 | 1127 / 1127 | 0 | 2 |
| frozen_router | 16/0/0 | 86406 | +20436 | +9529 | 100% | 100% | 4059 | 876 / 876 | 0 | 4 |
| livestock_crop | 16/0/0 | 97699 | +61272 | +46624 | 100% | 100% | 3861 | 1209 / 1209 | 0 | 3 |
| land_expander | 16/0/0 | 110764 | +100327 | +90950 | 100% | 100% | 4007 | 1201 / 1201 | 0 | 3 |
| phased_rotation | 16/0/0 | 109116 | +86573 | +70136 | 100% | 100% | 3861 | 1254 / 1254 | 0 | 2 |
| melon_heavy | 16/0/0 | 98697 | +75550 | +61195 | 100% | 100% | 3861 | 1209 / 1209 | 0 | 3 |
| gen_land_d8 | 16/0/0 | 100375 | +53010 | +45991 | 100% | 100% | 3951 | 1235 / 1235 | 0 | 2 |
| gen_cow6_d8 | 16/0/0 | 95302 | +54360 | +47244 | 100% | 100% | 4116 | 1197 / 1197 | 0 | 3 |
| conditional_land_planner | 16/0/0 | 95776 | +52275 | +35704 | 100% | 100% | 3951 | 1235 / 1235 | 0 | 2 |

Worst matchup: **top_meta_mirror**.

The JSON artifact contains every game, exact successful land-purchase days, realized animal-product revenue, losses, and final stranded inventory by item.

## Rejection-gate decision

- No opponent systematically broke the capital chain. Sheep-heavy pressure delayed deed 1 to day 7 in 4/32 games, but deed 2 still arrived by day 10 in all 32 and the candidate won every game.
- Cow/milk and fertilizer pressure preserved both land milestones in 100% of games.
- Overall paired P10 was +44,945, and the direct frozen-router matchup was 16/0/0 with +20,436 average advantage and +9,530 P10.
- There were zero livestock losses and zero runtime, semantic, or invalid-action failures.
- The mirror produced 8/8 seat-symmetric outcomes and zero paired advantage; these are not losses to a different policy.
- Final inventory was small but nonzero: 127/256 games had at least one unit, averaging 0.91 and reaching four units maximum.

All stated rejection conditions passed. The candidate was promoted in `experiments/current_best.json` without changing its source.

## Standalone packaging

`submission/main.py` was generated mechanically from the frozen dependency graph. It imports only Python standard-library modules (`base64`, `runpy`, `zlib`) and exposes `agent(obs)` without repository files.

- Source SHA-256: `3ede0041921010b0136abb538395faa5951e9af1fb9b76be41467246885da6a8`
- Submission SHA-256: `3196b73fc2f46e25284b773136b530e2aacbaad2ba8a9dffdfce66472fe2a0fb`
- Seed 731101, seat 0: 719/719 actions equal; final money 89,881 vs 86,330.
- Seed 731102, seat 1: 719/719 actions equal; final money 65,738 vs 53,799.
- Both were complete 720-step games with zero runtime, semantic, or invalid-action errors and zero livestock losses.

Nothing was submitted to Kaggle.
