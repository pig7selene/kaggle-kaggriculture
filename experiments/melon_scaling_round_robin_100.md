# Pure-Melon Scale Round Robin

- Games per matchup: 100
- Seeds per matchup: 50
- Every seed is played in both player positions.
- Total games: 1000

## Win-rate matrix

Rows are the focal agent; columns are opponents.

| Scale | 08 | 12 | 16 | 20 | 25 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 08 | — | 0.0% | 0.0% | 0.0% | 0.0% |
| 12 | 100.0% | — | 100.0% | 100.0% | 100.0% |
| 16 | 100.0% | 0.0% | — | 100.0% | 100.0% |
| 20 | 100.0% | 0.0% | 0.0% | — | 100.0% |
| 25 | 100.0% | 0.0% | 0.0% | 0.0% | — |

## Robustness ranking

| Rank | Agent | W/L/T | Win rate | Avg money | Avg advantage | Matchups W/L/T |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | melon_scale_12 | 400/0/0 | 100.00% | 15239.25 | +1609.75 | 4/0/0 |
| 2 | melon_scale_16 | 300/100/0 | 75.00% | 14983.25 | +1971.25 | 3/1/0 |
| 3 | melon_scale_20 | 200/200/0 | 50.00% | 13978.50 | +762.50 | 2/2/0 |
| 4 | melon_scale_25 | 100/300/0 | 25.00% | 12418.50 | -1187.50 | 1/3/0 |
| 5 | melon_scale_08 | 0/400/0 | 0.00% | 13432.25 | -3156.00 | 0/4/0 |
