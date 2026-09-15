# V43 layer ablation

Each variant is the shipped V43 with settings patched, against the shipped agent itself, 20 seeds in both seats. A positive margin is that change's value.

| Variant | N | W/L/T | GSR | Mean margin | Median | Worst | Semantic fails | Escapes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| room_plus_clamp | 40 | 37/3/0 | 0.925 | +440 | +263 | -696 | 152 | 0 |
| all_on_no_budget | 40 | 37/3/0 | 0.925 | +433 | +255 | -720 | 152 | 0 |
| all_on | 40 | 33/7/0 | 0.825 | +366 | +190 | -786 | 82 | 0 |
| +room_guard | 40 | 31/9/0 | 0.775 | +258 | +226 | -1,034 | 72 | 0 |
| +clamp_sells | 40 | 26/14/0 | 0.650 | +160 | +10 | -1,026 | 152 | 0 |
| +terminal_liquidation | 40 | 2/2/36 | 0.500 | +0 | +0 | -1,043 | 72 | 0 |
| +front_run | 40 | 2/2/36 | 0.500 | +0 | +0 | -1,043 | 72 | 0 |
| +dead_stock | 40 | 14/20/6 | 0.425 | -1 | -0 | -1,041 | 72 | 0 |
| +budget_guard | 40 | 2/36/2 | 0.075 | -67 | -66 | -1,109 | 2 | 0 |
