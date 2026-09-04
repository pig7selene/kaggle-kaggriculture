# Territory lifecycle scheduler ablation

The economic program is the frozen Top-50 observable portfolio. Only unit actions differ.
Seeds per direct proxy: 2; recorded real-loss cases: 4; both seats.

## Aggregate results

| Candidate | Games | W/L/T | Win rate | Avg money | Avg advantage | Median | P10 | Adv variance | Harvests | Crop rev d10-20 | Water miss | Replant delay | Livestock losses |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| S0_currentbest | 28 | 28/0/0 | 100.0% | 126388.6 | +101657.9 | +119850.0 | +51309.0 | 1540178724 | 351.0 | 43462.5 | 29.11% | 5.15 | 0 |
| S1_persistent | 28 | 28/0/0 | 100.0% | 126388.6 | +101657.9 | +119850.0 | +51309.0 | 1540178724 | 351.0 | 43462.5 | 29.11% | 5.15 | 0 |
| S2_deadline | 28 | 28/0/0 | 100.0% | 126388.6 | +101657.9 | +119850.0 | +51309.0 | 1540178724 | 351.0 | 43462.5 | 29.18% | 5.15 | 0 |
| S3_chain | 28 | 28/0/0 | 100.0% | 126388.6 | +101657.9 | +119850.0 | +51309.0 | 1540178724 | 351.0 | 43462.5 | 29.18% | 5.15 | 0 |

## Matchups

### S0_currentbest

| Opponent | Games | W/L/T | Avg advantage | P10 |
| --- | ---: | ---: | ---: | ---: |
| Alexander_cow_melon | 2 | 2/0/0 | +60320.0 | +60320.0 |
| Jayveer_melon_burst | 2 | 2/0/0 | +51309.0 | +51309.0 |
| Lucas_four_quadrant | 2 | 2/0/0 | +56735.0 | +56735.0 |
| Pedro_wheat_turnover | 2 | 2/0/0 | +29027.0 | +29027.0 |
| proxy_high_labor | 4 | 4/0/0 | +132237.5 | +125799.0 |
| proxy_land_expander | 4 | 4/0/0 | +146026.2 | +139555.0 |
| proxy_livestock_crop | 4 | 4/0/0 | +120535.5 | +113901.0 |
| proxy_phased_rotation | 4 | 4/0/0 | +134554.5 | +128077.0 |
| router_replay_hands12 | 4 | 4/0/0 | +79556.0 | +75999.0 |

### S1_persistent

| Opponent | Games | W/L/T | Avg advantage | P10 |
| --- | ---: | ---: | ---: | ---: |
| Alexander_cow_melon | 2 | 2/0/0 | +60320.0 | +60320.0 |
| Jayveer_melon_burst | 2 | 2/0/0 | +51309.0 | +51309.0 |
| Lucas_four_quadrant | 2 | 2/0/0 | +56735.0 | +56735.0 |
| Pedro_wheat_turnover | 2 | 2/0/0 | +29027.0 | +29027.0 |
| proxy_high_labor | 4 | 4/0/0 | +132237.5 | +125799.0 |
| proxy_land_expander | 4 | 4/0/0 | +146026.2 | +139555.0 |
| proxy_livestock_crop | 4 | 4/0/0 | +120535.5 | +113901.0 |
| proxy_phased_rotation | 4 | 4/0/0 | +134554.5 | +128077.0 |
| router_replay_hands12 | 4 | 4/0/0 | +79556.0 | +75999.0 |

### S2_deadline

| Opponent | Games | W/L/T | Avg advantage | P10 |
| --- | ---: | ---: | ---: | ---: |
| Alexander_cow_melon | 2 | 2/0/0 | +60320.0 | +60320.0 |
| Jayveer_melon_burst | 2 | 2/0/0 | +51309.0 | +51309.0 |
| Lucas_four_quadrant | 2 | 2/0/0 | +56735.0 | +56735.0 |
| Pedro_wheat_turnover | 2 | 2/0/0 | +29027.0 | +29027.0 |
| proxy_high_labor | 4 | 4/0/0 | +132237.5 | +125799.0 |
| proxy_land_expander | 4 | 4/0/0 | +146026.2 | +139555.0 |
| proxy_livestock_crop | 4 | 4/0/0 | +120535.5 | +113901.0 |
| proxy_phased_rotation | 4 | 4/0/0 | +134554.5 | +128077.0 |
| router_replay_hands12 | 4 | 4/0/0 | +79556.0 | +75999.0 |

### S3_chain

| Opponent | Games | W/L/T | Avg advantage | P10 |
| --- | ---: | ---: | ---: | ---: |
| Alexander_cow_melon | 2 | 2/0/0 | +60320.0 | +60320.0 |
| Jayveer_melon_burst | 2 | 2/0/0 | +51309.0 | +51309.0 |
| Lucas_four_quadrant | 2 | 2/0/0 | +56735.0 | +56735.0 |
| Pedro_wheat_turnover | 2 | 2/0/0 | +29027.0 | +29027.0 |
| proxy_high_labor | 4 | 4/0/0 | +132237.5 | +125799.0 |
| proxy_land_expander | 4 | 4/0/0 | +146026.2 | +139555.0 |
| proxy_livestock_crop | 4 | 4/0/0 | +120535.5 | +113901.0 |
| proxy_phased_rotation | 4 | 4/0/0 | +134554.5 | +128077.0 |
| router_replay_hands12 | 4 | 4/0/0 | +79556.0 | +75999.0 |

