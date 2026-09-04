# Prefix-compatible adaptive route benchmark

Seeds: `61000–61001` (2); both seats; 720 turns.
The candidate can switch only at turn 72 after an exact shared route prefix.

| Candidate | Games | W/L/T | Win rate | Avg money | Avg advantage | Median advantage | P10 | P5 | Worst | SD advantage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| current_best | 32 | 26/2/4 | 81.25% | 122953.1 | +73991.4 | +77787.0 | +0.0 | -1378.8 | -3064.0 | 62951.8 |
| prefix_adaptive_v1 | 32 | 26/6/0 | 81.25% | 126360.1 | +73481.1 | +77860.5 | -4917.4 | -7605.8 | -10391.0 | 63924.4 |

## Matchups

### current_best

| Opponent | Games | W/L/T | Avg money | Avg advantage | P10 | Switches |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| current_best | 4 | 0/0/4 | 87070.0 | +0.0 | +0.0 | 0 |
| tetsuya | 4 | 4/0/0 | 99392.5 | +11838.0 | +9726.0 | 0 |
| crop_dusta | 4 | 4/0/0 | 118751.5 | +46259.0 | +30032.0 | 0 |
| oceanmix | 4 | 2/2/0 | 97710.0 | +5096.0 | -3064.0 | 0 |
| livestock_crop | 4 | 4/0/0 | 131395.0 | +112579.5 | +93088.0 | 0 |
| land_expander | 4 | 4/0/0 | 128402.0 | +124798.2 | +110785.5 | 0 |
| high_labor | 4 | 4/0/0 | 171826.8 | +155453.2 | +153100.6 | 0 |
| phased_rotation | 4 | 4/0/0 | 149077.2 | +135907.0 | +121589.0 | 0 |

### prefix_adaptive_v1

| Opponent | Games | W/L/T | Avg money | Avg advantage | P10 | Switches |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| current_best | 4 | 0/4/0 | 106375.0 | -7859.0 | -10391.0 | 4 |
| tetsuya | 4 | 4/0/0 | 103045.0 | +19992.5 | +15303.0 | 0 |
| crop_dusta | 4 | 4/0/0 | 118804.5 | +46320.0 | +30090.0 | 0 |
| oceanmix | 4 | 2/2/0 | 101604.5 | +304.0 | -1231.0 | 4 |
| livestock_crop | 4 | 4/0/0 | 131478.0 | +112663.5 | +93171.0 | 0 |
| land_expander | 4 | 4/0/0 | 128495.0 | +124891.2 | +110878.3 | 0 |
| high_labor | 4 | 4/0/0 | 171910.5 | +155538.5 | +153182.4 | 0 |
| phased_rotation | 4 | 4/0/0 | 149168.0 | +135997.8 | +121682.0 | 0 |
