# Territory lifecycle scheduler ablation

The economic program is the frozen Top-50 observable portfolio. Only unit actions differ.
Seeds per direct proxy: 1; recorded real-loss cases: 4; both seats.

## Aggregate results

| Candidate | Games | W/L/T | Win rate | Avg money | Avg advantage | Median | P10 | Adv variance | Harvests | Crop rev d10-20 | Water miss | Replant delay | Livestock losses |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| S0_currentbest | 30 | 24/4/2 | 80.0% | 96438.5 | +57188.1 | +51309.0 | -774.0 | 2320914435 | 351.5 | 42238.5 | 29.28% | 5.65 | 0 |
| S1_persistent | 30 | 24/4/2 | 80.0% | 96438.5 | +57188.1 | +51309.0 | -774.0 | 2320914435 | 351.5 | 42238.5 | 29.29% | 5.65 | 0 |
| S2_deadline | 30 | 24/6/0 | 80.0% | 96422.6 | +57156.1 | +51309.0 | -817.0 | 2322225743 | 351.2 | 42238.5 | 29.41% | 5.76 | 0 |
| S3_chain | 30 | 24/6/0 | 80.0% | 96422.6 | +57156.1 | +51309.0 | -817.0 | 2322225743 | 351.2 | 42238.5 | 29.41% | 5.76 | 0 |

## Matchups

### S0_currentbest

| Opponent | Games | W/L/T | Avg advantage | P10 |
| --- | ---: | ---: | ---: | ---: |
| Alexander_cow_melon | 2 | 2/0/0 | +60320.0 | +60320.0 |
| Jayveer_melon_burst | 2 | 2/0/0 | +51309.0 | +51309.0 |
| Lucas_four_quadrant | 2 | 2/0/0 | +56735.0 | +56735.0 |
| Pedro_wheat_turnover | 2 | 2/0/0 | +29027.0 | +29027.0 |
| lifecycle_lc | 2 | 2/0/0 | +50505.0 | +50505.0 |
| proxy_high_labor | 2 | 2/0/0 | +125799.0 | +125799.0 |
| proxy_land_expander | 2 | 2/0/0 | +139555.0 | +139555.0 |
| proxy_livestock_crop | 2 | 2/0/0 | +113901.0 | +113901.0 |
| proxy_phased_rotation | 2 | 2/0/0 | +128077.0 | +128077.0 |
| router_replay_hands12 | 2 | 2/0/0 | +75999.0 | +75999.0 |
| super_replay_v2 | 2 | 2/0/0 | +9696.0 | +9696.0 |
| top50_dmitry | 2 | 0/2/0 | -774.0 | -774.0 |
| top50_hanserong | 2 | 0/2/0 | -3055.0 | -3055.0 |
| top50_redblack | 2 | 0/0/2 | +0.0 | +0.0 |
| v27_k9_full | 2 | 2/0/0 | +20727.0 | +20727.0 |

### S1_persistent

| Opponent | Games | W/L/T | Avg advantage | P10 |
| --- | ---: | ---: | ---: | ---: |
| Alexander_cow_melon | 2 | 2/0/0 | +60320.0 | +60320.0 |
| Jayveer_melon_burst | 2 | 2/0/0 | +51309.0 | +51309.0 |
| Lucas_four_quadrant | 2 | 2/0/0 | +56735.0 | +56735.0 |
| Pedro_wheat_turnover | 2 | 2/0/0 | +29027.0 | +29027.0 |
| lifecycle_lc | 2 | 2/0/0 | +50505.0 | +50505.0 |
| proxy_high_labor | 2 | 2/0/0 | +125799.0 | +125799.0 |
| proxy_land_expander | 2 | 2/0/0 | +139555.0 | +139555.0 |
| proxy_livestock_crop | 2 | 2/0/0 | +113901.0 | +113901.0 |
| proxy_phased_rotation | 2 | 2/0/0 | +128077.0 | +128077.0 |
| router_replay_hands12 | 2 | 2/0/0 | +75999.0 | +75999.0 |
| super_replay_v2 | 2 | 2/0/0 | +9696.0 | +9696.0 |
| top50_dmitry | 2 | 0/2/0 | -774.0 | -774.0 |
| top50_hanserong | 2 | 0/2/0 | -3055.0 | -3055.0 |
| top50_redblack | 2 | 0/0/2 | +0.0 | +0.0 |
| v27_k9_full | 2 | 2/0/0 | +20727.0 | +20727.0 |

### S2_deadline

| Opponent | Games | W/L/T | Avg advantage | P10 |
| --- | ---: | ---: | ---: | ---: |
| Alexander_cow_melon | 2 | 2/0/0 | +60320.0 | +60320.0 |
| Jayveer_melon_burst | 2 | 2/0/0 | +51309.0 | +51309.0 |
| Lucas_four_quadrant | 2 | 2/0/0 | +56735.0 | +56735.0 |
| Pedro_wheat_turnover | 2 | 2/0/0 | +29027.0 | +29027.0 |
| lifecycle_lc | 2 | 2/0/0 | +50152.0 | +50152.0 |
| proxy_high_labor | 2 | 2/0/0 | +125799.0 | +125799.0 |
| proxy_land_expander | 2 | 2/0/0 | +139555.0 | +139555.0 |
| proxy_livestock_crop | 2 | 2/0/0 | +113901.0 | +113901.0 |
| proxy_phased_rotation | 2 | 2/0/0 | +128077.0 | +128077.0 |
| router_replay_hands12 | 2 | 2/0/0 | +75999.0 | +75999.0 |
| super_replay_v2 | 2 | 2/0/0 | +9696.0 | +9696.0 |
| top50_dmitry | 2 | 0/2/0 | -817.0 | -817.0 |
| top50_hanserong | 2 | 0/2/0 | -3095.0 | -3095.0 |
| top50_redblack | 2 | 0/2/0 | -44.0 | -44.0 |
| v27_k9_full | 2 | 2/0/0 | +20727.0 | +20727.0 |

### S3_chain

| Opponent | Games | W/L/T | Avg advantage | P10 |
| --- | ---: | ---: | ---: | ---: |
| Alexander_cow_melon | 2 | 2/0/0 | +60320.0 | +60320.0 |
| Jayveer_melon_burst | 2 | 2/0/0 | +51309.0 | +51309.0 |
| Lucas_four_quadrant | 2 | 2/0/0 | +56735.0 | +56735.0 |
| Pedro_wheat_turnover | 2 | 2/0/0 | +29027.0 | +29027.0 |
| lifecycle_lc | 2 | 2/0/0 | +50152.0 | +50152.0 |
| proxy_high_labor | 2 | 2/0/0 | +125799.0 | +125799.0 |
| proxy_land_expander | 2 | 2/0/0 | +139555.0 | +139555.0 |
| proxy_livestock_crop | 2 | 2/0/0 | +113901.0 | +113901.0 |
| proxy_phased_rotation | 2 | 2/0/0 | +128077.0 | +128077.0 |
| router_replay_hands12 | 2 | 2/0/0 | +75999.0 | +75999.0 |
| super_replay_v2 | 2 | 2/0/0 | +9696.0 | +9696.0 |
| top50_dmitry | 2 | 0/2/0 | -817.0 | -817.0 |
| top50_hanserong | 2 | 0/2/0 | -3095.0 | -3095.0 |
| top50_redblack | 2 | 0/2/0 | -44.0 | -44.0 |
| v27_k9_full | 2 | 2/0/0 | +20727.0 | +20727.0 |

