# C2 Cow Staged-Land Search

All stages use deterministic seeds and both player positions. Search and held-out seeds are disjoint.

## timing_screen

Seeds: [9400, 9401]; games per variant: 40.

| Rank | Variant | W/L/T | Win rate | Avg money | Avg advantage | P10 | Variance | Tiles | Labor | Land | Worst |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | C_fixed_day14 | 40/0/0 | 100.0% | 48293.6 | +28140.7 | +26987.6 | 10923951.5 | 18.54 | 140.0 | 1.00 | animal_c2_cows (4/0/0, +5537.5) |
| 2 | B_fixed_day11 | 40/0/0 | 100.0% | 45650.1 | +25852.5 | +24962.0 | 13476187.4 | 17.04 | 155.0 | 1.00 | animal_c2_cows (4/0/0, +3139.0) |
| 3 | G_dynamic_roi | 40/0/0 | 100.0% | 45650.1 | +25852.5 | +24962.0 | 13476187.4 | 17.04 | 155.0 | 1.00 | animal_c2_cows (4/0/0, +3139.0) |
| 4 | F_cow_payback | 40/0/0 | 100.0% | 44359.8 | +24530.2 | +24069.1 | 6279595.3 | 13.45 | 110.0 | 1.00 | animal_c2_cows (4/0/0, +2167.0) |
| 5 | E_fixed_day18 | 39/1/0 | 97.5% | 44577.7 | +24665.8 | +23948.1 | 6882492.4 | 13.46 | 115.0 | 1.00 | animal_c2_cows (3/1/0, +884.5) |
| 6 | D_fixed_day16 | 39/1/0 | 97.5% | 44513.0 | +24557.3 | +23926.4 | 6628145.2 | 14.17 | 118.2 | 1.00 | animal_c2_cows (3/1/0, +462.5) |
| 7 | A_no_land | 37/1/2 | 92.5% | 43046.8 | +23110.4 | +22693.0 | 5375979.8 | 11.77 | 60.0 | 0.00 | animal_c2_cows (1/1/2, +0.0) |

## allocation_labor_search

Seeds: [9420, 9421]; games per variant: 24.

| Rank | Variant | W/L/T | Win rate | Avg money | Avg advantage | P10 | Variance | Tiles | Labor | Land | Worst |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | C_fixed_day14__adaptive__labor4 | 24/0/0 | 100.0% | 50360.2 | +28547.2 | +28523.4 | 33071934.8 | 17.92 | 220.0 | 1.00 | animal_c2_cows (4/0/0, +9282.0) |
| 2 | C_fixed_day14__phased_wheat_strawberry__labor4 | 24/0/0 | 100.0% | 49935.4 | +27747.2 | +27698.5 | 15150681.2 | 18.51 | 220.0 | 1.00 | animal_c2_cows (4/0/0, +8122.8) |
| 3 | C_fixed_day14__strawberry_heavy__labor4 | 24/0/0 | 100.0% | 49154.4 | +27108.5 | +27099.2 | 19667335.7 | 17.52 | 220.0 | 1.00 | animal_c2_cows (4/0/0, +7468.2) |
| 4 | C_fixed_day14__feed_support__labor4 | 24/0/0 | 100.0% | 48680.7 | +26536.0 | +26297.6 | 12097342.0 | 16.92 | 220.0 | 1.00 | animal_c2_cows (4/0/0, +7170.0) |
| 5 | C_fixed_day14__strawberry_heavy__labor8 | 24/0/0 | 100.0% | 47969.7 | +25691.2 | +25653.8 | 21152571.5 | 17.64 | 140.0 | 1.00 | animal_c2_cows (4/0/0, +7083.8) |
| 6 | C_fixed_day14__wheat_heavy__labor4 | 24/0/0 | 100.0% | 47872.5 | +25754.2 | +25692.9 | 13217464.2 | 17.38 | 220.0 | 1.00 | animal_c2_cows (4/0/0, +5584.5) |
| 7 | C_fixed_day14__phased_wheat_strawberry__labor8 | 24/0/0 | 100.0% | 47447.6 | +25060.5 | +24357.7 | 24214857.0 | 18.22 | 140.0 | 1.00 | animal_c2_cows (4/0/0, +6495.2) |
| 8 | C_fixed_day14__adaptive__labor8 | 24/0/0 | 100.0% | 46513.0 | +24436.7 | +24290.2 | 25981146.2 | 16.73 | 140.0 | 1.00 | animal_c2_cows (4/0/0, +4089.2) |
| 9 | C_fixed_day14__strawberry_heavy__labor12 | 24/0/0 | 100.0% | 45453.2 | +23483.4 | +22923.3 | 27819313.0 | 15.41 | 92.0 | 1.00 | animal_c2_cows (4/0/0, +4076.2) |
| 10 | C_fixed_day14__feed_support__labor8 | 23/1/0 | 95.8% | 45315.2 | +22921.1 | +21629.1 | 20900709.1 | 16.02 | 140.0 | 1.00 | animal_c2_cows (3/1/0, +4117.0) |
| 11 | C_fixed_day14__adaptive__labor12 | 24/0/0 | 100.0% | 44071.2 | +22009.3 | +21861.5 | 19247296.8 | 14.90 | 92.0 | 1.00 | animal_c2_cows (4/0/0, +3732.8) |
| 12 | C_fixed_day14__wheat_heavy__labor8 | 24/0/0 | 100.0% | 43901.2 | +21749.8 | +20776.8 | 17183831.6 | 16.63 | 140.0 | 1.00 | animal_c2_cows (4/0/0, +2825.8) |
| 13 | C_fixed_day14__wheat_heavy__labor12 | 23/1/0 | 95.8% | 43175.8 | +21281.6 | +20626.9 | 22771822.7 | 14.23 | 92.0 | 1.00 | animal_c2_cows (3/1/0, +1978.2) |
| 14 | C_fixed_day14__feed_support__labor12 | 23/1/0 | 95.8% | 42461.3 | +20572.5 | +20512.5 | 26477092.6 | 14.17 | 92.0 | 1.00 | animal_c2_cows (3/1/0, +1155.2) |
| 15 | C_fixed_day14__phased_wheat_strawberry__labor12 | 23/1/0 | 95.8% | 42631.1 | +20459.6 | +19463.2 | 27443782.6 | 15.70 | 92.0 | 1.00 | animal_c2_cows (3/1/0, +1102.5) |

## quadrant_roi_search

Seeds: [9440, 9441]; games per variant: 24.

| Rank | Variant | W/L/T | Win rate | Avg money | Avg advantage | P10 | Variance | Tiles | Labor | Land | Worst |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | C_fixed_day14__adaptive__labor4__q1__roi0.00 | 24/0/0 | 100.0% | 51530.6 | +29542.9 | +28399.0 | 12375722.7 | 18.28 | 220.0 | 1.00 | animal_c2_cows (4/0/0, +8464.0) |
| 2 | C_fixed_day14__adaptive__labor4__q1__roi0.15 | 24/0/0 | 100.0% | 51530.6 | +29542.9 | +28399.0 | 12375722.7 | 18.28 | 220.0 | 1.00 | animal_c2_cows (4/0/0, +8464.0) |
| 3 | C_fixed_day14__adaptive__labor4__q2__roi0.00 | 24/0/0 | 100.0% | 51530.6 | +29542.9 | +28399.0 | 12375722.7 | 18.28 | 220.0 | 1.00 | animal_c2_cows (4/0/0, +8464.0) |
| 4 | C_fixed_day14__adaptive__labor4__q2__roi0.15 | 24/0/0 | 100.0% | 51530.6 | +29542.9 | +28399.0 | 12375722.7 | 18.28 | 220.0 | 1.00 | animal_c2_cows (4/0/0, +8464.0) |
| 5 | C_fixed_day14__adaptive__labor4__q3__roi0.00 | 24/0/0 | 100.0% | 51530.6 | +29542.9 | +28399.0 | 12375722.7 | 18.28 | 220.0 | 1.00 | animal_c2_cows (4/0/0, +8464.0) |
| 6 | C_fixed_day14__adaptive__labor4__q3__roi0.15 | 24/0/0 | 100.0% | 51530.6 | +29542.9 | +28399.0 | 12375722.7 | 18.28 | 220.0 | 1.00 | animal_c2_cows (4/0/0, +8464.0) |
| 7 | C_fixed_day14__phased_wheat_strawberry__labor4__q1__roi0.00 | 24/0/0 | 100.0% | 50538.0 | +28431.4 | +27558.8 | 11419713.3 | 18.47 | 220.0 | 1.00 | animal_c2_cows (4/0/0, +8262.0) |
| 8 | C_fixed_day14__phased_wheat_strawberry__labor4__q1__roi0.15 | 24/0/0 | 100.0% | 50538.0 | +28431.4 | +27558.8 | 11419713.3 | 18.47 | 220.0 | 1.00 | animal_c2_cows (4/0/0, +8262.0) |
| 9 | C_fixed_day14__phased_wheat_strawberry__labor4__q2__roi0.00 | 24/0/0 | 100.0% | 50538.0 | +28431.4 | +27558.8 | 11419713.3 | 18.47 | 220.0 | 1.00 | animal_c2_cows (4/0/0, +8262.0) |
| 10 | C_fixed_day14__phased_wheat_strawberry__labor4__q2__roi0.15 | 24/0/0 | 100.0% | 50538.0 | +28431.4 | +27558.8 | 11419713.3 | 18.47 | 220.0 | 1.00 | animal_c2_cows (4/0/0, +8262.0) |
| 11 | C_fixed_day14__phased_wheat_strawberry__labor4__q3__roi0.00 | 24/0/0 | 100.0% | 50538.0 | +28431.4 | +27558.8 | 11419713.3 | 18.47 | 220.0 | 1.00 | animal_c2_cows (4/0/0, +8262.0) |
| 12 | C_fixed_day14__phased_wheat_strawberry__labor4__q3__roi0.15 | 24/0/0 | 100.0% | 50538.0 | +28431.4 | +27558.8 | 11419713.3 | 18.47 | 220.0 | 1.00 | animal_c2_cows (4/0/0, +8262.0) |

## heldout_confirmation

Seeds: [9600, 9601, 9602, 9603, 9604, 9605, 9606, 9607, 9608, 9609, 9610, 9611, 9612]; games per variant: 260.

| Rank | Variant | W/L/T | Win rate | Avg money | Avg advantage | P10 | Variance | Tiles | Labor | Land | Worst |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | best_expansion | 260/0/0 | 100.0% | 49723.1 | +30163.7 | +27864.2 | 32514648.4 | 17.92 | 220.0 | 1.00 | animal_c2_cows (26/0/0, +7954.7) |
| 2 | C2_no_land | 239/5/16 | 91.9% | 41792.5 | +21978.2 | +20117.5 | 19506364.0 | 11.78 | 60.0 | 0.00 | animal_c2_cows (5/5/16, +0.0) |

## Held-out matchup details

### best_expansion

| Opponent | W/L/T | Avg money | Avg advantage | P10 |
| --- | ---: | ---: | ---: | ---: |
| melon_scale_12 | 26/0/0 | 48359.7 | +32979.6 | +25846.0 |
| proxy_melon_heavy | 26/0/0 | 48122.6 | +32874.5 | +24553.8 |
| proxy_phased_rotation | 26/0/0 | 51790.0 | +38036.1 | +30365.4 |
| proxy_land_expander | 26/0/0 | 50327.3 | +47075.2 | +43622.6 |
| proxy_inventory_holder | 26/0/0 | 50473.8 | +37065.7 | +30743.9 |
| proxy_mixed_crop | 26/0/0 | 54142.5 | +32153.3 | +28636.2 |
| proxy_livestock_crop | 26/0/0 | 44590.7 | +13365.6 | +9413.2 |
| proxy_high_labor | 26/0/0 | 53816.8 | +38541.3 | +33775.0 |
| adaptive_c_phased | 26/0/0 | 47537.5 | +21591.2 | +16091.5 |
| animal_c2_cows | 26/0/0 | 48069.9 | +7954.7 | +4866.1 |

### C2_no_land

| Opponent | W/L/T | Avg money | Avg advantage | P10 |
| --- | ---: | ---: | ---: | ---: |
| melon_scale_12 | 26/0/0 | 39222.3 | +23744.7 | +17898.4 |
| proxy_melon_heavy | 26/0/0 | 40127.7 | +24880.0 | +19248.3 |
| proxy_phased_rotation | 26/0/0 | 44159.1 | +30432.7 | +27554.9 |
| proxy_land_expander | 26/0/0 | 43727.8 | +39721.9 | +34631.2 |
| proxy_inventory_holder | 26/0/0 | 43436.0 | +30027.3 | +26546.8 |
| proxy_mixed_crop | 26/0/0 | 44572.6 | +22349.3 | +20833.4 |
| proxy_livestock_crop | 26/0/0 | 37996.9 | +6238.7 | +4879.1 |
| proxy_high_labor | 26/0/0 | 45119.8 | +29038.8 | +26133.8 |
| adaptive_c_phased | 26/0/0 | 39283.7 | +13349.1 | +9502.8 |
| animal_c2_cows | 5/5/16 | 40279.4 | +0.0 | +0.0 |

