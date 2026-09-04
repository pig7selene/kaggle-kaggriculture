# Territory lifecycle scheduler ablation

The economic program is the frozen Top-50 observable portfolio. Only unit actions differ.
Seeds per direct proxy: 0; recorded real-loss cases: 4; both seats.

## Aggregate results

| Candidate | Games | W/L/T | Win rate | Avg money | Avg advantage | Median | P10 | Adv variance | Harvests | Crop rev d10-20 | Water miss | Replant delay | Livestock losses |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| S0_currentbest | 8 | 8/0/0 | 100.0% | 91273.0 | +49347.8 | +54022.0 | +29027.0 | 147935279 | 351.0 | 41826.2 | 29.11% | 5.15 | 0 |
| S1_persistent | 8 | 0/8/0 | 0.0% | 31002.9 | -61881.6 | -60381.5 | -68697.8 | 20612790 | 221.6 | 23168.4 | 32.13% | 64.87 | 60 |
| S2_deadline | 8 | 0/8/0 | 0.0% | 21893.5 | -75063.8 | -75558.5 | -80841.0 | 23332188 | 166.0 | 16209.0 | 34.53% | 65.73 | 46 |
| S3_chain | 8 | 0/8/0 | 0.0% | 23857.1 | -71473.9 | -71490.5 | -77201.7 | 16952878 | 161.5 | 16535.5 | 33.19% | 66.61 | 55 |

## Matchups

### S0_currentbest

| Opponent | Games | W/L/T | Avg advantage | P10 |
| --- | ---: | ---: | ---: | ---: |
| Alexander_cow_melon | 2 | 2/0/0 | +60320.0 | +60320.0 |
| Jayveer_melon_burst | 2 | 2/0/0 | +51309.0 | +51309.0 |
| Lucas_four_quadrant | 2 | 2/0/0 | +56735.0 | +56735.0 |
| Pedro_wheat_turnover | 2 | 2/0/0 | +29027.0 | +29027.0 |

### S1_persistent

| Opponent | Games | W/L/T | Avg advantage | P10 |
| --- | ---: | ---: | ---: | ---: |
| Alexander_cow_melon | 2 | 0/2/0 | -57004.5 | -57585.7 |
| Jayveer_melon_burst | 2 | 0/2/0 | -68843.0 | -69133.4 |
| Lucas_four_quadrant | 2 | 0/2/0 | -59092.5 | -59247.3 |
| Pedro_wheat_turnover | 2 | 0/2/0 | -62586.5 | -63474.1 |

### S2_deadline

| Opponent | Games | W/L/T | Avg advantage | P10 |
| --- | ---: | ---: | ---: | ---: |
| Alexander_cow_melon | 2 | 0/2/0 | -68454.0 | -69934.0 |
| Jayveer_melon_burst | 2 | 0/2/0 | -80841.0 | -80841.0 |
| Lucas_four_quadrant | 2 | 0/2/0 | -77968.0 | -78085.6 |
| Pedro_wheat_turnover | 2 | 0/2/0 | -72992.0 | -73235.2 |

### S3_chain

| Opponent | Games | W/L/T | Avg advantage | P10 |
| --- | ---: | ---: | ---: | ---: |
| Alexander_cow_melon | 2 | 0/2/0 | -65703.5 | -65837.5 |
| Jayveer_melon_burst | 2 | 0/2/0 | -77277.5 | -77429.1 |
| Lucas_four_quadrant | 2 | 0/2/0 | -71244.0 | -71735.2 |
| Pedro_wheat_turnover | 2 | 0/2/0 | -71670.5 | -72108.5 |

