# Frozen-router matched opening audit

Each run uses the original public seed and seat. The other player emits the exact action trace from the public replay. Invalid counterfactual opponent orders remain silent no-ops under normal game rules.

- Frozen source: `agents/router_replay_hands12.py`
- Matched runs: 8
- Financial reconstruction mismatches: 0

## Median checkpoint comparison

| Day | Public bank after day | Current bank after day | Public tiles | Current tiles | Public quadrants | Current quadrants | Public cows/sheep | Current cows/sheep | Public/current max hands |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 4 | $542 | $1,732 | 19.0 | 13.0 | 1.0 | 1.0 | 1.0/4.0 | 1.0/0.0 | 3.0/3.0 |
| 6 | $34 | $890 | 27.0 | 16.0 | 2.0 | 1.0 | 3.0/4.0 | 4.0/0.0 | 4.0/4.0 |
| 8 | $56 | $132 | 49.5 | 17.0 | 2.0 | 1.0 | 8.0/4.0 | 5.0/0.0 | 6.0/4.0 |
| 10 | $5,454 | $554 | 66.5 | 14.0 | 3.0 | 1.0 | 8.0/4.0 | 8.0/0.0 | 14.0/4.0 |

## First concrete divergences

- **Abracadabra episode 91866168 seat 0**: return deficit day 2 hour 0 ($393); bank deficit day 7 hour 1 ($1,248).
- **Erfan Eshratifar episode 91866168 seat 1**: return deficit day 1 hour 0 ($408); bank deficit day 6 hour 1 ($142).
- **Valmorlee episode 91869967 seat 0**: return deficit day 2 hour 0 ($396); bank deficit day 7 hour 1 ($1,263).
- **Dmitry Larko episode 91869967 seat 1**: return deficit day 1 hour 0 ($408); bank deficit day 6 hour 1 ($131).
- **THUNDER THUNDER episode 91870919 seat 0**: return deficit day 2 hour 0 ($396); bank deficit day 6 hour 1 ($109).
- **Victor @ Tufa Labs episode 91870919 seat 1**: return deficit day 1 hour 0 ($172); bank deficit day 6 hour 1 ($118).
- **Ueddy episode 91870920 seat 0**: return deficit day 2 hour 0 ($396); bank deficit day 6 hour 1 ($102).
- **Abracadabra episode 91870920 seat 1**: return deficit day 2 hour 0 ($396); bank deficit day 6 hour 1 ($104).
