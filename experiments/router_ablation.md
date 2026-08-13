# Router-only ablation

R0/R1 share the frozen C8 economy; R2/R3 share the frozen cow-only replay economy.

| Candidate | Games | W/L/T | Score | Avg money | Avg advantage | P10 | Crop revenue | Animal revenue | Quadrants | Peak hands | Peak productive |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| R0_old_router_current_economy | 42 | 38/2/2 | 92.9% | 64415.2 | +29844.0 | +27497.3 | 35999.4 | 40633.4 | 2.00 | 8.00 | 31.98 |
| R1_new_router_current_economy | 42 | 35/7/0 | 83.3% | 60357.0 | +24065.4 | +21351.7 | 33916.9 | 36971.4 | 2.00 | 8.00 | 32.00 |
| R2_old_router_replay_economy | 42 | 19/23/0 | 45.2% | 44164.3 | +2799.5 | +2774.5 | 28623.1 | 39975.2 | 3.00 | 14.00 | 48.50 |
| R3_new_router_replay_economy | 42 | 41/1/0 | 97.6% | 72352.3 | +35800.6 | +34984.4 | 45187.0 | 48235.0 | 3.00 | 14.00 | 68.43 |

## Routing by capacity

### R0_old_router_current_economy

| Capacity | Productive | Movement | PASS | Move/productive | Tile utilization | Critical water miss | Unfed | Uncared | Fert left |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 25 | 21.0% | 28.8% | 50.2% | 1.37 | 44.7% | 0.0% | 0.0% | 0.0% | 0.0% |
| 50 | 23.5% | 57.3% | 16.9% | 2.44 | 57.4% | 3.8% | 5.9% | 20.5% | 0.0% |

### R1_new_router_current_economy

| Capacity | Productive | Movement | PASS | Move/productive | Tile utilization | Critical water miss | Unfed | Uncared | Fert left |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 25 | 20.6% | 29.2% | 50.2% | 1.42 | 46.5% | 0.8% | 0.0% | 0.0% | 0.0% |
| 50 | 22.0% | 46.6% | 29.5% | 2.12 | 58.9% | 0.1% | 5.1% | 16.9% | 46.3% |

### R2_old_router_replay_economy

| Capacity | Productive | Movement | PASS | Move/productive | Tile utilization | Critical water miss | Unfed | Uncared | Fert left |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 25 | 22.6% | 62.0% | 11.4% | 2.75 | 59.3% | 1.6% | 3.2% | 58.8% | 18.6% |
| 50 | 26.4% | 62.0% | 9.6% | 2.35 | 35.0% | 13.4% | 0.0% | 2.0% | 0.9% |
| 75 | 21.6% | 74.3% | 2.2% | 3.44 | 49.5% | 7.5% | 0.7% | 75.5% | 23.7% |

### R3_new_router_replay_economy

| Capacity | Productive | Movement | PASS | Move/productive | Tile utilization | Critical water miss | Unfed | Uncared | Fert left |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 25 | 21.8% | 55.6% | 18.7% | 2.55 | 59.9% | 0.0% | 23.5% | 36.7% | 31.5% |
| 50 | 0.0% | 38.1% | 1.0% | 0.00 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| 75 | 30.2% | 59.1% | 9.2% | 1.96 | 75.8% | 2.0% | 2.0% | 17.1% | 61.3% |

