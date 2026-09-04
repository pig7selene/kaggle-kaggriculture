# Territory lifecycle scheduler ablation

The economic program is the frozen Top-50 observable portfolio. Only unit actions differ.
Seeds per direct proxy: 4; recorded real-loss cases: 4; both seats.

## Aggregate results

| Candidate | Games | W/L/T | Win rate | Avg money | Avg advantage | Median | P10 | Adv variance | Harvests | Crop rev d10-20 | Water miss | Replant delay | Livestock losses |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| S0_currentbest | 56 | 48/0/8 | 85.7% | 99052.3 | +18936.2 | +7780.5 | +0.0 | 412896562 | 352.0 | 40395.1 | 29.47% | 6.21 | 0 |
| S1_persistent | 56 | 48/0/8 | 85.7% | 99052.3 | +18936.2 | +7780.5 | +0.0 | 412896562 | 352.0 | 40395.1 | 29.51% | 6.21 | 0 |
| S2_deadline | 56 | 48/8/0 | 85.7% | 98995.1 | +18862.4 | +7739.5 | -38.5 | 409688382 | 351.4 | 40395.1 | 29.67% | 6.44 | 0 |
| S3_chain | 56 | 48/8/0 | 85.7% | 98995.1 | +18862.4 | +7739.5 | -38.5 | 409688382 | 351.4 | 40395.1 | 29.67% | 6.44 | 0 |

## Matchups

### S0_currentbest

| Opponent | Games | W/L/T | Avg advantage | P10 |
| --- | ---: | ---: | ---: | ---: |
| Alexander_cow_melon | 2 | 2/0/0 | +60320.0 | +60320.0 |
| Jayveer_melon_burst | 2 | 2/0/0 | +51309.0 | +51309.0 |
| Lucas_four_quadrant | 2 | 2/0/0 | +56735.0 | +56735.0 |
| Pedro_wheat_turnover | 2 | 2/0/0 | +29027.0 | +29027.0 |
| lifecycle_lc | 8 | 8/0/0 | +47159.6 | +35550.0 |
| super_replay_v2 | 8 | 8/0/0 | +6482.8 | +2370.0 |
| top50_dmitry | 8 | 8/0/0 | +3572.2 | +2743.0 |
| top50_hanserong | 8 | 8/0/0 | +5696.0 | +2856.0 |
| top50_redblack | 8 | 0/0/8 | +0.0 | +0.0 |
| v27_k9_full | 8 | 8/0/0 | +20294.9 | +14024.9 |

### S1_persistent

| Opponent | Games | W/L/T | Avg advantage | P10 |
| --- | ---: | ---: | ---: | ---: |
| Alexander_cow_melon | 2 | 2/0/0 | +60320.0 | +60320.0 |
| Jayveer_melon_burst | 2 | 2/0/0 | +51309.0 | +51309.0 |
| Lucas_four_quadrant | 2 | 2/0/0 | +56735.0 | +56735.0 |
| Pedro_wheat_turnover | 2 | 2/0/0 | +29027.0 | +29027.0 |
| lifecycle_lc | 8 | 8/0/0 | +47159.6 | +35550.0 |
| super_replay_v2 | 8 | 8/0/0 | +6482.8 | +2370.0 |
| top50_dmitry | 8 | 8/0/0 | +3572.2 | +2743.0 |
| top50_hanserong | 8 | 8/0/0 | +5696.0 | +2856.0 |
| top50_redblack | 8 | 0/0/8 | +0.0 | +0.0 |
| v27_k9_full | 8 | 8/0/0 | +20294.9 | +14024.9 |

### S2_deadline

| Opponent | Games | W/L/T | Avg advantage | P10 |
| --- | ---: | ---: | ---: | ---: |
| Alexander_cow_melon | 2 | 2/0/0 | +60320.0 | +60320.0 |
| Jayveer_melon_burst | 2 | 2/0/0 | +51309.0 | +51309.0 |
| Lucas_four_quadrant | 2 | 2/0/0 | +56735.0 | +56735.0 |
| Pedro_wheat_turnover | 2 | 2/0/0 | +29027.0 | +29027.0 |
| lifecycle_lc | 8 | 8/0/0 | +46765.2 | +35754.6 |
| super_replay_v2 | 8 | 8/0/0 | +6482.8 | +2370.0 |
| top50_dmitry | 8 | 8/0/0 | +3532.5 | +2699.0 |
| top50_hanserong | 8 | 8/0/0 | +5654.8 | +2817.0 |
| top50_redblack | 8 | 0/8/0 | -40.8 | -45.0 |
| v27_k9_full | 8 | 8/0/0 | +20294.9 | +14024.9 |

### S3_chain

| Opponent | Games | W/L/T | Avg advantage | P10 |
| --- | ---: | ---: | ---: | ---: |
| Alexander_cow_melon | 2 | 2/0/0 | +60320.0 | +60320.0 |
| Jayveer_melon_burst | 2 | 2/0/0 | +51309.0 | +51309.0 |
| Lucas_four_quadrant | 2 | 2/0/0 | +56735.0 | +56735.0 |
| Pedro_wheat_turnover | 2 | 2/0/0 | +29027.0 | +29027.0 |
| lifecycle_lc | 8 | 8/0/0 | +46765.2 | +35754.6 |
| super_replay_v2 | 8 | 8/0/0 | +6482.8 | +2370.0 |
| top50_dmitry | 8 | 8/0/0 | +3532.5 | +2699.0 |
| top50_hanserong | 8 | 8/0/0 | +5654.8 | +2817.0 |
| top50_redblack | 8 | 0/8/0 | -40.8 | -45.0 |
| v27_k9_full | 8 | 8/0/0 | +20294.9 | +14024.9 |

