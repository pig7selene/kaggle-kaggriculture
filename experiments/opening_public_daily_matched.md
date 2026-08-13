# Frozen-router matched opening audit

Each run uses the original public seed and seat. The other player emits the exact action trace from the public replay. Invalid counterfactual opponent orders remain silent no-ops under normal game rules.

- Frozen source: `agents/opening_public_daily_feed.py`
- Matched runs: 8
- Financial reconstruction mismatches: 0

## Median checkpoint comparison

| Day | Public bank after day | Current bank after day | Public tiles | Current tiles | Public quadrants | Current quadrants | Public cows/sheep | Current cows/sheep | Public/current max hands |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 4 | $542 | $81 | 19.0 | 12.0 | 1.0 | 1.0 | 1.0/4.0 | 1.0/4.0 | 3.0/3.0 |
| 6 | $34 | $294 | 27.0 | 18.0 | 2.0 | 2.0 | 3.0/4.0 | 2.0/4.0 | 4.0/4.0 |
| 8 | $56 | $40 | 49.5 | 28.0 | 2.0 | 2.0 | 8.0/4.0 | 5.0/4.0 | 6.0/6.0 |
| 10 | $5,454 | $75 | 66.5 | 38.5 | 3.0 | 2.0 | 8.0/4.0 | 4.5/3.0 | 14.0/14.0 |

## First concrete divergences

- **Abracadabra episode 91866168 seat 0**: return deficit day 5 hour 0 ($257); bank deficit day 1 hour 0 ($14).
- **Erfan Eshratifar episode 91866168 seat 1**: return deficit day 1 hour 0 ($408); bank deficit day 1 hour 0 ($10).
- **Valmorlee episode 91869967 seat 0**: return deficit day 5 hour 0 ($241); bank deficit day 1 hour 0 ($14).
- **Dmitry Larko episode 91869967 seat 1**: return deficit day 1 hour 0 ($408); bank deficit day 1 hour 0 ($10).
- **THUNDER THUNDER episode 91870919 seat 0**: return deficit day 3 hour 0 ($94); bank deficit day 2 hour 1 ($26).
- **Victor @ Tufa Labs episode 91870919 seat 1**: return deficit day 1 hour 0 ($172); bank deficit day 1 hour 0 ($5).
- **Ueddy episode 91870920 seat 0**: return deficit day 3 hour 0 ($95); bank deficit day 2 hour 1 ($44).
- **Abracadabra episode 91870920 seat 1**: return deficit day 3 hour 0 ($95); bank deficit day 2 hour 1 ($49).
