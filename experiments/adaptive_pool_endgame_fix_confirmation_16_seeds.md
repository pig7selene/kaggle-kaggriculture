# Adaptive Economy Pool Benchmark

- Seeds per opponent: 16
- Every seed is played in both positions.
- Opponents: 8
- Games per candidate: 256
- Worst-seed percentile is the 10th percentile of seat- and opponent-averaged money advantage by seed.

| Rank | Candidate | W/L/T | Win rate | Avg money | Avg advantage | P10 seed advantage | Money SD | Matchups W/L/T | Worst matchup |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | adaptive_h_hybrid | 224/32/0 | 87.50% | 26109.72 | +7344.73 | +6845.09 | 2797.07 | 7/1/0 | proxy_livestock_crop (0.0%, -13669.62) |
| 2 | adaptive_g_tuned | 224/32/0 | 87.50% | 25232.73 | +6723.08 | +6346.25 | 2864.29 | 7/1/0 | proxy_livestock_crop (0.0%, -14949.81) |
| 3 | adaptive_f_full | 214/42/0 | 83.59% | 25056.97 | +5184.11 | +3585.03 | 4287.96 | 7/1/0 | proxy_livestock_crop (0.0%, -15653.66) |

## Matchup details

### adaptive_h_hybrid

| Opponent | W/L/T | Win rate | Avg money | Avg advantage | P10 seed advantage |
| --- | ---: | ---: | ---: | ---: | ---: |
| melon_scale_12 | 32/0/0 | 100.0% | 24189.88 | +5972.56 | +4866.50 |
| proxy_melon_heavy | 32/0/0 | 100.0% | 23300.84 | +5892.97 | +4425.50 |
| proxy_phased_rotation | 32/0/0 | 100.0% | 25657.78 | +8242.38 | +7182.75 |
| proxy_land_expander | 32/0/0 | 100.0% | 28540.00 | +22738.94 | +21619.50 |
| proxy_inventory_holder | 32/0/0 | 100.0% | 24522.81 | +7865.28 | +7134.00 |
| proxy_mixed_crop | 32/0/0 | 100.0% | 30567.00 | +8673.69 | +7864.00 |
| proxy_livestock_crop | 0/32/0 | 0.0% | 23432.88 | -13669.62 | -15586.50 |
| proxy_high_labor | 32/0/0 | 100.0% | 28666.59 | +13041.69 | +12216.00 |

### adaptive_g_tuned

| Opponent | W/L/T | Win rate | Avg money | Avg advantage | P10 seed advantage |
| --- | ---: | ---: | ---: | ---: | ---: |
| melon_scale_12 | 32/0/0 | 100.0% | 23207.06 | +4805.62 | +4083.00 |
| proxy_melon_heavy | 32/0/0 | 100.0% | 23051.97 | +5596.88 | +4656.50 |
| proxy_phased_rotation | 32/0/0 | 100.0% | 23632.91 | +6263.69 | +5740.00 |
| proxy_land_expander | 32/0/0 | 100.0% | 27862.56 | +23595.38 | +21180.50 |
| proxy_inventory_holder | 32/0/0 | 100.0% | 23918.88 | +7269.78 | +6498.00 |
| proxy_mixed_crop | 32/0/0 | 100.0% | 29664.06 | +7978.66 | +7231.50 |
| proxy_livestock_crop | 0/32/0 | 0.0% | 22068.25 | -14949.81 | -16792.75 |
| proxy_high_labor | 32/0/0 | 100.0% | 28456.12 | +13224.44 | +12307.50 |

### adaptive_f_full

| Opponent | W/L/T | Win rate | Avg money | Avg advantage | P10 seed advantage |
| --- | ---: | ---: | ---: | ---: | ---: |
| melon_scale_12 | 28/4/0 | 87.5% | 22517.88 | +3522.75 | +233.50 |
| proxy_melon_heavy | 30/2/0 | 93.8% | 23168.09 | +4691.31 | +2520.50 |
| proxy_phased_rotation | 32/0/0 | 100.0% | 25231.16 | +7565.16 | +4521.25 |
| proxy_land_expander | 32/0/0 | 100.0% | 27566.16 | +21897.44 | +18518.50 |
| proxy_inventory_holder | 32/0/0 | 100.0% | 26251.22 | +8466.91 | +4643.75 |
| proxy_mixed_crop | 32/0/0 | 100.0% | 30765.72 | +8466.88 | +5715.75 |
| proxy_livestock_crop | 0/32/0 | 0.0% | 21753.34 | -15653.66 | -19003.00 |
| proxy_high_labor | 28/4/0 | 87.5% | 23202.19 | +2516.06 | -4058.75 |
