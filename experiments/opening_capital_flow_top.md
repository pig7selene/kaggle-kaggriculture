# Top-player opening capital-flow audit

This audit reconstructs successful actions by replaying every public action against the prior replay state. Bank values are the observed values immediately before and after the whole turn; multiple simultaneous market orders can share one row.

- Public appearances audited: 35
- Representative appearances rendered turn-by-turn: 8
- Financial reconstruction mismatches: 0

## Aggregate funding milestones

| Milestone | n | Typical time | Median bank after | Median cumulative sales |
|---|---:|---:|---:|---:|
| eight_cows | 32 | day 8.0, hour 12.0 | $65 | $8,028 |
| land_1 | 35 | day 6, hour 16 | $1,127 | $4,242 |
| land_2 | 35 | day 10, hour 0 | $1,805 | $12,484 |

### Median cumulative revenue available at each milestone

| Milestone | FERTILIZER | MELON | MILK | WHEAT | WOOL |
|---|---:|---:|---:|---:|---:|
| eight_cows | $3,519 | $0 | $0 | $687 | $3,733 |
| land_1 | $2,649 | $0 | $0 | $542 | $1,051 |
| land_2 | $4,349 | $0 | $1,050 | $1,159 | $5,439 |

## Abracadabra — episode 91866168 seat 0

Opponent: Erfan Eshratifar; seed: 1050733733.

| Day/hour | Bank before → after | Successful economic events |
|---|---:|---|
| 0/00 | $3,000 → $24 | buy animal {'COW': 1, 'SHEEP': 4}; buy seed {'MELON': 5, 'WHEAT': 5}; buy feed {'WHEAT': 4}; hire 4 ($7.0) |
| 0/03 | $24 → $24 | build {'PASTURE': 1} |
| 0/04 | $24 → $24 | place animal {'SHEEP': 1}; build {'PASTURE': 1} |
| 0/05 | $24 → $24 | plant {'MELON': 1}; place animal {'COW': 1} |
| 0/07 | $24 → $24 | plant {'WHEAT': 1} |
| 0/08 | $24 → $24 | plant {'WHEAT': 1}; build {'PASTURE': 1} |
| 0/09 | $24 → $24 | place animal {'SHEEP': 1} |
| 0/10 | $24 → $24 | plant {'WHEAT': 1} |
| 0/12 | $24 → $24 | plant {'MELON': 1} |
| 0/13 | $24 → $24 | plant {'WHEAT': 1}; build {'PASTURE': 1} |
| 0/14 | $24 → $24 | place animal {'SHEEP': 1} |
| 0/15 | $24 → $24 | plant {'MELON': 1} |
| 0/16 | $24 → $24 | plant {'WHEAT': 1} |
| 0/19 | $24 → $24 | plant {'MELON': 1}; build {'PASTURE': 1} |
| 0/20 | $24 → $24 | place animal {'SHEEP': 1} |
| 0/22 | $24 → $24 | plant {'MELON': 1} |
| 1/00 | $24 → $23 | hire 1 ($1.0) |
| 1/02 | $23 → $23 | collect fertilizer 1 |
| 1/04 | $23 → $23 | collect fertilizer 1 |
| 1/07 | $23 → $23 | collect fertilizer 2 |
| 1/09 | $23 → $23 | collect fertilizer 1 |
| 2/00 | $23 → $340 | buy feed {'WHEAT': 6}; sell 5 FERTILIZER for $493 @ [99, 99, 99, 98, 98]; hire 2 ($2.0) |
| 2/03 | $340 → $310 | buy feed {'WHEAT': 1} |
| 2/04 | $310 → $310 | collect fertilizer 1 |
| 2/05 | $310 → $280 | buy feed {'WHEAT': 1} |
| 2/06 | $280 → $280 | collect fertilizer 1 |
| 2/09 | $280 → $250 | buy feed {'WHEAT': 1} |
| 2/10 | $250 → $250 | collect fertilizer 1 |
| 2/14 | $250 → $219 | buy feed {'WHEAT': 1} |
| 2/18 | $219 → $188 | buy feed {'WHEAT': 1} |
| 2/19 | $188 → $188 | collect fertilizer 1 |
| 3/00 | $188 → $261 | buy seed {'STRAWBERRY': 3, 'WHEAT': 1}; sell 4 FERTILIZER for $387 @ [97, 97, 97, 96]; hire 3 ($4.0) |
| 3/03 | $261 → $230 | buy feed {'WHEAT': 1} |
| 3/04 | $230 → $230 | collect fertilizer 1 |
| 3/05 | $230 → $199 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 1} |
| 3/06 | $199 → $199 | collect fertilizer 1 |
| 3/08 | $199 → $199 | plant {'STRAWBERRY': 1} |
| 3/09 | $199 → $167 | buy feed {'WHEAT': 1} |
| 3/10 | $167 → $167 | collect fertilizer 1 |
| 3/11 | $167 → $167 | plant {'STRAWBERRY': 1}; collect fertilizer 1 |
| 3/14 | $167 → $135 | plant {'WHEAT': 1}; buy feed {'WHEAT': 1} |
| 3/16 | $135 → $103 | buy feed {'WHEAT': 1} |
| 4/00 | $103 → $480 | sell 4 FERTILIZER for $381 @ [96, 95, 95, 95]; hire 3 ($4.0) |
| 4/01 | $480 → $430 | buy seed {'WHEAT': 5} |
| 4/03 | $430 → $398 | buy feed {'WHEAT': 1} |
| 4/04 | $398 → $398 | collect fertilizer 1 |
| 4/05 | $398 → $365 | buy feed {'WHEAT': 1} |
| 4/06 | $365 → $365 | collect fertilizer 1 |
| 4/08 | $365 → $365 | harvest {'WHEAT': 4} |
| 4/09 | $365 → $365 | plant {'WHEAT': 1} |
| 4/10 | $365 → $365 | collect fertilizer 1 |
| 4/13 | $365 → $365 | harvest {'WHEAT': 4} |
| 4/14 | $365 → $365 | plant {'WHEAT': 1} |
| 4/15 | $365 → $365 | harvest {'WHEAT': 4} |
| 4/16 | $365 → $365 | plant {'WHEAT': 1}; harvest {'WHEAT': 4} |
| 4/18 | $365 → $365 | harvest {'WHEAT': 4} |
| 4/19 | $365 → $365 | plant {'WHEAT': 2}; collect fertilizer 1 |
| 5/00 | $365 → $460 | buy animal {'COW': 1}; buy seed {'STRAWBERRY': 4, 'WHEAT': 1}; sell 4 FERTILIZER for $373 @ [94, 93, 93, 93]; sell 17 WHEAT for $536 @ [33, 33, 32, 32, 32, 32, 32, 32, 32, 31, 31, 31, 31, 31, 31, 30, 30]; hire 3 ($4.0) |
| 5/01 | $460 → $429 | buy feed {'WHEAT': 1} |
| 5/04 | $429 → $398 | buy feed {'WHEAT': 1} |
| 5/05 | $398 → $367 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 5/06 | $367 → $367 | plant {'STRAWBERRY': 1}; collect fertilizer 1 |
| 5/08 | $367 → $367 | build {'PASTURE': 1} |
| 5/09 | $367 → $336 | place animal {'COW': 1}; buy feed {'WHEAT': 1} |
| 5/10 | $336 → $336 | plant {'WHEAT': 1}; collect fertilizer 1 |
| 5/11 | $336 → $305 | buy feed {'WHEAT': 1} |
| 5/14 | $305 → $273 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 5/18 | $273 → $241 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 1} |
| 5/21 | $241 → $241 | plant {'STRAWBERRY': 1} |
| 6/00 | $241 → $602 | sell 4 FERTILIZER for $365 @ [92, 91, 91, 91]; hire 3 ($4.0) |
| 6/02 | $602 → $602 | harvest {'WOOL': 5} |
| 6/04 | $602 → $570 | harvest {'WOOL': 5}; buy feed {'WHEAT': 1} |
| 6/05 | $570 → $570 | collect fertilizer 1 |
| 6/06 | $570 → $537 | buy feed {'WHEAT': 1} |
| 6/07 | $537 → $537 | collect fertilizer 1 |
| 6/08 | $537 → $504 | buy feed {'WHEAT': 1} |
| 6/09 | $504 → $504 | harvest {'WOOL': 5}; collect fertilizer 1 |
| 6/11 | $504 → $471 | buy feed {'WHEAT': 1} |
| 6/12 | $471 → $438 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 6/13 | $438 → $438 | collect fertilizer 1 |
| 6/16 | $438 → $760 | sell 3 FERTILIZER for $271 @ [91, 90, 90]; sell 5 WOOL for $1051 @ [218, 215, 212, 206, 200]; buy land 1 ($1000.0) |
| 6/17 | $760 → $47 | buy animal {'COW': 1}; buy seed {'STRAWBERRY': 3, 'WHEAT': 1}; hire 1 ($3.0) |
| 6/20 | $47 → $47 | plant {'STRAWBERRY': 1}; build {'PASTURE': 2} |
| 6/21 | $47 → $47 | place animal {'COW': 1} |
| 6/23 | $47 → $47 | plant {'STRAWBERRY': 1} |
| 7/00 | $47 → $1,289 | buy animal {'COW': 2}; sell 2 FERTILIZER for $179 @ [90, 89]; sell 10 WOOL for $1896 @ [199, 199, 197, 195, 193, 190, 187, 183, 179, 174]; hire 7 ($33.0) |
| 7/01 | $1,289 → $155 | buy seed {'STRAWBERRY': 9, 'WHEAT': 3}; buy feed {'WHEAT': 6} |
| 7/03 | $155 → $121 | buy feed {'WHEAT': 1} |
| 7/04 | $121 → $87 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 7/05 | $87 → $52 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 7/06 | $52 → $52 | collect fertilizer 1 |
| 7/07 | $52 → $17 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 1}; build {'PASTURE': 1} |
| 7/08 | $17 → $17 | plant {'STRAWBERRY': 1}; place animal {'COW': 1}; collect fertilizer 1 |
| 7/10 | $17 → $17 | plant {'STRAWBERRY': 1}; collect fertilizer 1 |
| 7/11 | $17 → $17 | plant {'STRAWBERRY': 1} |
| 7/12 | $17 → $17 | build {'PASTURE': 1} |
| 7/13 | $17 → $17 | plant {'STRAWBERRY': 1}; place animal {'COW': 1} |
| 7/14 | $17 → $17 | plant {'STRAWBERRY': 1} |
| 7/15 | $17 → $17 | plant {'WHEAT': 1} |
| 7/16 | $17 → $17 | harvest {'WHEAT': 4} |
| 7/17 | $17 → $17 | plant {'WHEAT': 1}; collect fertilizer 1 |
| 7/18 | $17 → $17 | plant {'STRAWBERRY': 1} |
| 7/20 | $17 → $17 | plant {'WHEAT': 2} |
| 7/22 | $17 → $17 | plant {'STRAWBERRY': 1} |
| 8/00 | $17 → $158 | buy animal {'COW': 1}; buy seed {'WHEAT': 3}; sell 6 FERTILIZER for $521 @ [88, 87, 87, 87, 86, 86]; sell 2 WHEAT for $70 @ [35, 35]; hire 6 ($20.0) |
| 8/01 | $158 → $8 | buy seed {'STRAWBERRY': 1, 'WHEAT': 5} |
| 8/03 | $8 → $8 | harvest {'MILK': 6} |
| 8/04 | $8 → $8 | collect fertilizer 2 |
| 8/05 | $8 → $8 | build {'PASTURE': 1} |
| 8/06 | $8 → $8 | place animal {'COW': 1}; collect fertilizer 1 |
| 8/07 | $8 → $8 | harvest {'WHEAT': 4} |
| 8/08 | $8 → $8 | plant {'WHEAT': 1}; collect fertilizer 2 |
| 8/11 | $8 → $8 | build {'PASTURE': 1} |
| 8/12 | $8 → $8 | harvest {'WHEAT': 4}; collect fertilizer 1 |
| 8/13 | $8 → $8 | plant {'WHEAT': 1} |
| 8/14 | $8 → $8 | plant {'STRAWBERRY': 1} |
| 8/15 | $8 → $8 | collect fertilizer 1 |
| 8/16 | $8 → $8 | plant {'WHEAT': 1}; harvest {'WHEAT': 4} |
| 8/17 | $8 → $8 | plant {'STRAWBERRY': 1, 'WHEAT': 1}; harvest {'WHEAT': 4} |
| 8/18 | $8 → $8 | plant {'WHEAT': 1}; collect fertilizer 1 |
| 8/19 | $8 → $8 | plant {'WHEAT': 1} |
| 8/20 | $8 → $8 | plant {'WHEAT': 1} |
| 8/21 | $8 → $8 | harvest {'WHEAT': 4} |
| 8/22 | $8 → $8 | plant {'WHEAT': 1} |
| 9/00 | $8 → $2,153 | sell 8 FERTILIZER for $668 @ [85, 84, 84, 83, 83, 83, 83, 83]; sell 6 MILK for $1050 @ [186, 183, 179, 175, 169, 158]; sell 13 WHEAT for $460 @ [36, 36, 36, 36, 36, 35, 35, 35, 35, 35, 35, 35, 35]; hire 7 ($33.0) |
| 9/01 | $2,153 → $2,143 | buy seed {'WHEAT': 1} |
| 9/02 | $2,143 → $2,143 | harvest {'WOOL': 4} |
| 9/03 | $2,143 → $2,108 | buy feed {'WHEAT': 1} |
| 9/04 | $2,108 → $2,003 | buy feed {'WHEAT': 3}; collect fertilizer 1 |
| 9/05 | $2,003 → $2,003 | collect fertilizer 3 |
| 9/07 | $2,003 → $1,967 | harvest {'WOOL': 4}; buy feed {'WHEAT': 1} |
| 9/08 | $1,967 → $1,895 | buy feed {'WHEAT': 2} |
| 9/09 | $1,895 → $1,859 | buy feed {'WHEAT': 1}; collect fertilizer 2 |
| 9/10 | $1,859 → $1,859 | collect fertilizer 1 |
| 9/12 | $1,859 → $1,859 | harvest {'WOOL': 4} |
| 9/13 | $1,859 → $1,823 | buy feed {'WHEAT': 1} |
| 9/14 | $1,823 → $1,787 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 9/15 | $1,787 → $1,787 | collect fertilizer 1 |
| 9/17 | $1,787 → $1,787 | harvest {'WHEAT': 4} |
| 9/18 | $1,787 → $1,787 | plant {'WHEAT': 1} |
| 10/00 | $1,787 → $1,293 | sell 2 WHEAT for $74 @ [37, 37]; sell 12 WOOL for $1465 @ [164, 158, 151, 144, 137, 129, 121, 112, 102, 93, 82, 72]; hire 7 ($33.0); buy land 1 ($2000.0) |
| 10/01 | $1,293 → $20 | buy seed {'MELON': 4}; hire 7 ($953.0) |
| 10/05 | $20 → $20 | collect fertilizer 2 |
| 10/06 | $20 → $20 | harvest {'MELON': 6}; collect fertilizer 2 |
| 10/07 | $20 → $20 | plant {'MELON': 1} |
| 10/08 | $20 → $20 | harvest {'MELON': 6} |
| 10/09 | $20 → $20 | plant {'MELON': 1}; harvest {'MELON': 6} |
| 10/10 | $20 → $20 | plant {'MELON': 1}; collect fertilizer 3 |
| 10/11 | $20 → $20 | harvest {'MELON': 6} |
| 10/12 | $20 → $257 | harvest {'MELON': 6}; buy seed {'MELON': 9, 'STRAWBERRY': 6}; buy feed {'WHEAT': 1}; sell 6 MELON for $1594 @ [272, 270, 268, 266, 262, 256] |
| 10/13 | $257 → $19 | plant {'MELON': 2, 'STRAWBERRY': 3}; buy seed {'STRAWBERRY': 2}; buy feed {'WHEAT': 1} |
| 10/15 | $19 → $489 | plant {'MELON': 1}; buy seed {'STRAWBERRY': 8}; buy feed {'WHEAT': 6}; collect fertilizer 1; sell 6 MELON for $1498 @ [250, 250, 250, 250, 249, 249] |
| 10/16 | $489 → $489 | plant {'MELON': 1, 'STRAWBERRY': 3} |
| 10/17 | $489 → $1,969 | harvest {'MILK': 3}; sell 6 MELON for $1480 @ [248, 248, 247, 246, 246, 245] |
| 10/18 | $1,969 → $1,969 | plant {'MELON': 1}; collect fertilizer 1 |
| 10/19 | $1,969 → $1,893 | plant {'MELON': 1, 'STRAWBERRY': 2}; buy feed {'WHEAT': 2} |
| 10/20 | $1,893 → $3,339 | plant {'STRAWBERRY': 1}; sell 6 MELON for $1446 @ [244, 243, 242, 240, 239, 238] |
| 10/21 | $3,339 → $3,339 | plant {'MELON': 1} |
| 10/22 | $3,339 → $4,723 | plant {'STRAWBERRY': 2}; buy seed {'WHEAT': 1}; sell 6 MELON for $1394 @ [236, 235, 233, 232, 230, 228] |
| 10/23 | $4,723 → $4,723 | plant {'WHEAT': 1} |

Milestone funding:

- **land_1** at day 6, hour 16: bank $438 → $760; cumulative sales $3,857 {'FERTILIZER': 2270, 'WHEAT': 536, 'WOOL': 1051}; cumulative spending $6,097.
- **land_2** at day 10, hour 0: bank $1,787 → $1,293; cumulative sales $10,240 {'FERTILIZER': 3638, 'MILK': 1050, 'WHEAT': 1140, 'WOOL': 4412}; cumulative spending $11,947.

## Erfan Eshratifar — episode 91866168 seat 1

Opponent: Abracadabra; seed: 1050733733.

| Day/hour | Bank before → after | Successful economic events |
|---|---:|---|
| 0/00 | $3,000 → $12 | buy animal {'SHEEP': 4}; buy seed {'MELON': 5, 'WHEAT': 5}; buy feed {'WHEAT': 19}; hire 4 ($7.0) |
| 0/01 | $12 → $20 | buy animal {'COW': 1}; sell 14 WHEAT for $408 @ [30, 30, 30, 30, 29, 29, 29, 29, 29, 29, 29, 29, 28, 28] |
| 0/03 | $20 → $20 | build {'PASTURE': 1} |
| 0/04 | $20 → $20 | place animal {'SHEEP': 1}; build {'PASTURE': 1} |
| 0/05 | $20 → $20 | plant {'MELON': 1}; place animal {'COW': 1} |
| 0/07 | $20 → $20 | plant {'WHEAT': 1} |
| 0/08 | $20 → $20 | plant {'WHEAT': 1}; build {'PASTURE': 1} |
| 0/09 | $20 → $20 | place animal {'SHEEP': 1} |
| 0/10 | $20 → $20 | plant {'WHEAT': 1} |
| 0/12 | $20 → $20 | plant {'MELON': 1} |
| 0/13 | $20 → $20 | plant {'WHEAT': 1}; build {'PASTURE': 1} |
| 0/14 | $20 → $20 | place animal {'SHEEP': 1} |
| 0/15 | $20 → $20 | plant {'MELON': 1} |
| 0/16 | $20 → $20 | plant {'WHEAT': 1} |
| 0/19 | $20 → $20 | plant {'MELON': 1}; build {'PASTURE': 1} |
| 0/20 | $20 → $20 | place animal {'SHEEP': 1} |
| 0/22 | $20 → $20 | plant {'MELON': 1} |
| 1/00 | $20 → $19 | hire 1 ($1.0) |
| 1/02 | $19 → $19 | collect fertilizer 1 |
| 1/04 | $19 → $19 | collect fertilizer 1 |
| 1/07 | $19 → $19 | collect fertilizer 2 |
| 1/09 | $19 → $19 | collect fertilizer 1 |
| 1/23 | $19 → $319 | sell 3 FERTILIZER for $300 @ [100, 100, 100] |
| 2/00 | $319 → $341 | buy feed {'WHEAT': 6}; sell 2 FERTILIZER for $198 @ [99, 99]; hire 2 ($2.0) |
| 2/03 | $341 → $311 | buy feed {'WHEAT': 1} |
| 2/04 | $311 → $311 | collect fertilizer 1 |
| 2/05 | $311 → $281 | buy feed {'WHEAT': 1} |
| 2/06 | $281 → $281 | collect fertilizer 1 |
| 2/09 | $281 → $251 | buy feed {'WHEAT': 1} |
| 2/10 | $251 → $251 | collect fertilizer 1 |
| 2/14 | $251 → $220 | buy feed {'WHEAT': 1} |
| 2/15 | $220 → $220 | collect fertilizer 1 |
| 2/18 | $220 → $189 | buy feed {'WHEAT': 1} |
| 2/19 | $189 → $189 | collect fertilizer 1 |
| 2/23 | $189 → $483 | sell 3 FERTILIZER for $294 @ [98, 98, 98] |
| 3/00 | $483 → $363 | buy seed {'STRAWBERRY': 3, 'WHEAT': 1}; sell 2 FERTILIZER for $194 @ [97, 97]; hire 3 ($4.0) |
| 3/03 | $363 → $332 | buy feed {'WHEAT': 1} |
| 3/04 | $332 → $332 | collect fertilizer 1 |
| 3/05 | $332 → $301 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 1} |
| 3/06 | $301 → $301 | collect fertilizer 1 |
| 3/08 | $301 → $301 | plant {'STRAWBERRY': 1} |
| 3/09 | $301 → $269 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 3/10 | $269 → $269 | collect fertilizer 1 |
| 3/11 | $269 → $269 | plant {'STRAWBERRY': 1}; collect fertilizer 1 |
| 3/14 | $269 → $237 | plant {'WHEAT': 1}; buy feed {'WHEAT': 1} |
| 3/16 | $237 → $205 | buy feed {'WHEAT': 1} |
| 3/23 | $205 → $397 | sell 2 FERTILIZER for $192 @ [96, 96] |
| 4/00 | $397 → $679 | sell 3 FERTILIZER for $286 @ [96, 95, 95]; hire 3 ($4.0) |
| 4/01 | $679 → $629 | buy seed {'WHEAT': 5} |
| 4/03 | $629 → $597 | buy feed {'WHEAT': 1} |
| 4/04 | $597 → $597 | collect fertilizer 1 |
| 4/05 | $597 → $564 | buy feed {'WHEAT': 1} |
| 4/06 | $564 → $564 | collect fertilizer 1 |
| 4/08 | $564 → $564 | harvest {'WHEAT': 4} |
| 4/09 | $564 → $564 | plant {'WHEAT': 1} |
| 4/10 | $564 → $564 | collect fertilizer 1 |
| 4/13 | $564 → $564 | harvest {'WHEAT': 4} |
| 4/14 | $564 → $564 | plant {'WHEAT': 1} |
| 4/15 | $564 → $564 | harvest {'WHEAT': 4}; collect fertilizer 1 |
| 4/16 | $564 → $564 | plant {'WHEAT': 1}; harvest {'WHEAT': 4} |
| 4/18 | $564 → $564 | harvest {'WHEAT': 4} |
| 4/19 | $564 → $564 | plant {'WHEAT': 2}; collect fertilizer 1 |
| 4/20 | $564 → $663 | sell 3 WHEAT for $99 @ [33, 33, 33] |
| 4/23 | $663 → $1,039 | sell 4 FERTILIZER for $376 @ [94, 94, 94, 94] |
| 5/00 | $1,039 → $764 | buy animal {'COW': 1}; buy seed {'STRAWBERRY': 4, 'WHEAT': 1}; sell 1 FERTILIZER for $94 @ [94]; sell 14 WHEAT for $445 @ [33, 33, 32, 32, 32, 32, 32, 32, 32, 31, 31, 31, 31, 31]; hire 3 ($4.0) |
| 5/01 | $764 → $733 | buy feed {'WHEAT': 1} |
| 5/04 | $733 → $702 | buy feed {'WHEAT': 1} |
| 5/05 | $702 → $671 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 5/06 | $671 → $671 | plant {'STRAWBERRY': 1}; collect fertilizer 1 |
| 5/08 | $671 → $671 | build {'PASTURE': 1} |
| 5/09 | $671 → $640 | place animal {'COW': 1}; buy feed {'WHEAT': 1} |
| 5/10 | $640 → $640 | plant {'WHEAT': 1}; collect fertilizer 1 |
| 5/11 | $640 → $609 | buy feed {'WHEAT': 1} |
| 5/14 | $609 → $577 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 5/15 | $577 → $577 | collect fertilizer 1 |
| 5/17 | $577 → $577 | plant {'STRAWBERRY': 1} |
| 5/18 | $577 → $545 | buy feed {'WHEAT': 1} |
| 5/22 | $545 → $545 | plant {'STRAWBERRY': 1} |
| 5/23 | $545 → $1,006 | sell 5 FERTILIZER for $461 @ [93, 92, 92, 92, 92] |
| 6/00 | $1,006 → $1,002 | hire 3 ($4.0) |
| 6/02 | $1,002 → $1,002 | harvest {'WOOL': 5} |
| 6/04 | $1,002 → $970 | harvest {'WOOL': 5}; buy feed {'WHEAT': 1} |
| 6/05 | $970 → $970 | collect fertilizer 1 |
| 6/06 | $970 → $937 | buy feed {'WHEAT': 1} |
| 6/07 | $937 → $937 | collect fertilizer 1 |
| 6/08 | $937 → $904 | buy feed {'WHEAT': 1} |
| 6/09 | $904 → $904 | harvest {'WOOL': 5}; collect fertilizer 1 |
| 6/11 | $904 → $871 | buy feed {'WHEAT': 1} |
| 6/12 | $871 → $838 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 6/13 | $838 → $838 | collect fertilizer 1 |
| 6/14 | $838 → $871 | sell 1 WHEAT for $33 @ [33] |
| 6/15 | $871 → $871 | harvest {'WOOL': 5} |
| 6/16 | $871 → $1,193 | sell 3 FERTILIZER for $271 @ [91, 90, 90]; sell 5 WOOL for $1051 @ [218, 215, 212, 206, 200]; buy land 1 ($1000.0) |
| 6/17 | $1,193 → $114 | buy animal {'COW': 2}; buy seed {'STRAWBERRY': 2, 'WHEAT': 1}; buy feed {'WHEAT': 2}; hire 1 ($3.0) |
| 6/18 | $114 → $114 | collect fertilizer 1 |
| 6/19 | $114 → $81 | buy feed {'WHEAT': 1} |
| 6/20 | $81 → $81 | plant {'STRAWBERRY': 1}; build {'PASTURE': 2} |
| 6/21 | $81 → $81 | place animal {'COW': 1} |
| 6/23 | $81 → $81 | plant {'STRAWBERRY': 1} |
| 7/00 | $81 → $2,231 | buy animal {'COW': 2}; sell 3 FERTILIZER for $268 @ [90, 89, 89]; sell 15 WOOL for $2715 @ [199, 199, 197, 195, 193, 190, 187, 183, 179, 174, 169, 167, 164, 161, 158]; hire 7 ($33.0) |
| 7/01 | $2,231 → $1,065 | buy seed {'STRAWBERRY': 10, 'WHEAT': 3}; buy feed {'WHEAT': 4} |
| 7/03 | $1,065 → $1,031 | buy feed {'WHEAT': 1} |
| 7/04 | $1,031 → $962 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 2}; collect fertilizer 1 |
| 7/05 | $962 → $962 | collect fertilizer 2 |
| 7/06 | $962 → $962 | plant {'STRAWBERRY': 1} |
| 7/07 | $962 → $927 | buy feed {'WHEAT': 1}; build {'PASTURE': 1} |
| 7/08 | $927 → $892 | plant {'STRAWBERRY': 1}; place animal {'COW': 1}; buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 7/09 | $892 → $892 | plant {'STRAWBERRY': 1}; collect fertilizer 1 |
| 7/10 | $892 → $857 | buy feed {'WHEAT': 1} |
| 7/11 | $857 → $857 | plant {'STRAWBERRY': 1} |
| 7/12 | $857 → $857 | plant {'STRAWBERRY': 1}; build {'PASTURE': 1} |
| 7/13 | $857 → $822 | place animal {'COW': 1}; buy feed {'WHEAT': 1} |
| 7/14 | $822 → $822 | plant {'STRAWBERRY': 1}; collect fertilizer 1 |
| 7/15 | $822 → $787 | plant {'STRAWBERRY': 1, 'WHEAT': 1}; buy feed {'WHEAT': 1} |
| 7/16 | $787 → $787 | harvest {'WHEAT': 4} |
| 7/17 | $787 → $787 | plant {'WHEAT': 1}; collect fertilizer 1 |
| 7/18 | $787 → $787 | plant {'STRAWBERRY': 1} |
| 7/19 | $787 → $787 | place animal {'COW': 1} |
| 7/20 | $787 → $787 | plant {'WHEAT': 2} |
| 7/21 | $787 → $857 | sell 2 WHEAT for $70 @ [35, 35] |
| 7/22 | $857 → $857 | plant {'STRAWBERRY': 1} |
| 7/23 | $857 → $1,298 | sell 5 FERTILIZER for $441 @ [89, 88, 88, 88, 88] |
| 8/00 | $1,298 → $623 | buy animal {'COW': 2}; buy seed {'WHEAT': 3}; sell 2 FERTILIZER for $175 @ [88, 87]; hire 6 ($20.0) |
| 8/01 | $623 → $303 | buy seed {'STRAWBERRY': 2, 'WHEAT': 5}; buy feed {'WHEAT': 2} |
| 8/03 | $303 → $231 | harvest {'MILK': 6}; buy feed {'WHEAT': 2} |
| 8/04 | $231 → $231 | collect fertilizer 2 |
| 8/05 | $231 → $195 | buy feed {'WHEAT': 1}; build {'PASTURE': 1} |
| 8/06 | $195 → $195 | place animal {'COW': 1}; collect fertilizer 1 |
| 8/07 | $195 → $123 | harvest {'WHEAT': 4}; buy feed {'WHEAT': 2} |
| 8/08 | $123 → $123 | plant {'WHEAT': 1}; collect fertilizer 2 |
| 8/10 | $123 → $123 | collect fertilizer 1 |
| 8/11 | $123 → $123 | build {'PASTURE': 1} |
| 8/12 | $123 → $123 | harvest {'WHEAT': 4}; place animal {'COW': 1}; collect fertilizer 1 |
| 8/13 | $123 → $123 | plant {'WHEAT': 1} |
| 8/14 | $123 → $123 | plant {'STRAWBERRY': 1} |
| 8/15 | $123 → $123 | collect fertilizer 1 |
| 8/16 | $123 → $123 | plant {'WHEAT': 1}; harvest {'WHEAT': 4} |
| 8/17 | $123 → $123 | plant {'STRAWBERRY': 1, 'WHEAT': 1}; harvest {'WHEAT': 4} |
| 8/18 | $123 → $123 | plant {'WHEAT': 1}; collect fertilizer 2 |
| 8/19 | $123 → $123 | plant {'WHEAT': 1} |
| 8/20 | $123 → $123 | plant {'WHEAT': 1} |
| 8/21 | $123 → $339 | harvest {'WHEAT': 4}; sell 6 WHEAT for $216 @ [36, 36, 36, 36, 36, 36] |
| 8/22 | $339 → $339 | plant {'WHEAT': 1} |
| 8/23 | $339 → $937 | sell 7 FERTILIZER for $598 @ [86, 86, 86, 85, 85, 85, 85] |
| 9/00 | $937 → $2,457 | sell 3 FERTILIZER for $253 @ [85, 84, 84]; sell 6 MILK for $1050 @ [186, 183, 179, 175, 169, 158]; sell 7 WHEAT for $250 @ [36, 36, 36, 36, 36, 35, 35]; hire 7 ($33.0) |
| 9/01 | $2,457 → $2,447 | buy seed {'WHEAT': 1} |
| 9/02 | $2,447 → $2,447 | harvest {'WOOL': 4} |
| 9/03 | $2,447 → $2,412 | buy feed {'WHEAT': 1} |
| 9/04 | $2,412 → $2,307 | buy feed {'WHEAT': 3}; collect fertilizer 1 |
| 9/05 | $2,307 → $2,307 | collect fertilizer 3 |
| 9/07 | $2,307 → $2,271 | harvest {'WOOL': 4}; buy feed {'WHEAT': 1} |
| 9/08 | $2,271 → $2,199 | buy feed {'WHEAT': 2}; collect fertilizer 1 |
| 9/09 | $2,199 → $2,163 | buy feed {'WHEAT': 1}; collect fertilizer 2 |
| 9/10 | $2,163 → $2,199 | collect fertilizer 1; sell 1 WHEAT for $36 @ [36] |
| 9/12 | $2,199 → $2,163 | harvest {'WOOL': 4}; buy feed {'WHEAT': 1} |
| 9/14 | $2,163 → $2,091 | buy feed {'WHEAT': 2}; collect fertilizer 1 |
| 9/15 | $2,091 → $2,091 | collect fertilizer 1 |
| 9/17 | $2,091 → $2,091 | harvest {'WHEAT': 4} |
| 9/18 | $2,091 → $2,091 | plant {'WHEAT': 1}; harvest {'WOOL': 4} |
| 9/19 | $2,091 → $2,091 | collect fertilizer 1 |
| 9/21 | $2,091 → $2,165 | collect fertilizer 1; sell 2 WHEAT for $74 @ [37, 37] |
| 10/00 | $2,165 → $1,805 | sell 16 WOOL for $1673 @ [164, 158, 151, 144, 137, 129, 121, 112, 102, 93, 82, 72, 61, 55, 49, 43]; hire 7 ($33.0); buy land 1 ($2000.0) |
| 10/01 | $1,805 → $32 | buy seed {'MELON': 9, 'STRAWBERRY': 1}; hire 7 ($953.0) |
| 10/03 | $32 → $32 | plant {'STRAWBERRY': 1} |
| 10/05 | $32 → $32 | collect fertilizer 2 |
| 10/06 | $32 → $32 | harvest {'MELON': 6}; collect fertilizer 2 |
| 10/07 | $32 → $32 | plant {'MELON': 1} |
| 10/08 | $32 → $32 | harvest {'MELON': 6} |
| 10/09 | $32 → $32 | plant {'MELON': 1}; harvest {'MELON': 6}; collect fertilizer 1 |
| 10/10 | $32 → $32 | plant {'MELON': 1}; collect fertilizer 3 |
| 10/11 | $32 → $32 | harvest {'MELON': 6} |
| 10/12 | $32 → $258 | plant {'MELON': 2}; harvest {'MELON': 6}; buy seed {'MELON': 4, 'STRAWBERRY': 9}; buy feed {'WHEAT': 4}; sell 6 MELON for $1594 @ [272, 270, 268, 266, 262, 256] |
| 10/13 | $258 → $110 | plant {'MELON': 2, 'STRAWBERRY': 2}; buy feed {'WHEAT': 4} |
| 10/14 | $110 → $34 | buy feed {'WHEAT': 2} |
| 10/15 | $34 → $1,532 | plant {'MELON': 1, 'STRAWBERRY': 1}; collect fertilizer 2; sell 6 MELON for $1498 @ [250, 250, 250, 250, 249, 249] |
| 10/16 | $1,532 → $1,532 | plant {'MELON': 1, 'STRAWBERRY': 2} |
| 10/17 | $1,532 → $3,012 | harvest {'MILK': 3}; sell 6 MELON for $1480 @ [248, 248, 247, 246, 246, 245] |
| 10/18 | $3,012 → $3,012 | plant {'MELON': 1, 'STRAWBERRY': 1}; collect fertilizer 2 |
| 10/19 | $3,012 → $2,936 | plant {'MELON': 1, 'STRAWBERRY': 2}; buy feed {'WHEAT': 2} |
| 10/20 | $2,936 → $4,382 | sell 6 MELON for $1446 @ [244, 243, 242, 240, 239, 238] |
| 10/21 | $4,382 → $4,382 | plant {'MELON': 1} |
| 10/22 | $4,382 → $5,766 | plant {'STRAWBERRY': 1}; buy seed {'WHEAT': 1}; sell 6 MELON for $1394 @ [236, 235, 233, 232, 230, 228] |
| 10/23 | $5,766 → $6,080 | sell 2 MILK for $314 @ [158, 156] |

Milestone funding:

- **land_1** at day 6, hour 16: bank $871 → $1,193; cumulative sales $4,702 {'FERTILIZER': 2666, 'WHEAT': 985, 'WOOL': 1051}; cumulative spending $6,509.
- **eight_cows** at day 8, hour 12: bank $123 → $123; cumulative sales $8,371 {'FERTILIZER': 3550, 'WHEAT': 1055, 'WOOL': 3766}; cumulative spending $11,248.
- **land_2** at day 10, hour 0: bank $2,165 → $1,805; cumulative sales $12,521 {'FERTILIZER': 4401, 'MILK': 1050, 'WHEAT': 1631, 'WOOL': 5439}; cumulative spending $13,716.

## Valmorlee — episode 91869967 seat 0

Opponent: Dmitry Larko; seed: 122449146.

| Day/hour | Bank before → after | Successful economic events |
|---|---:|---|
| 0/00 | $3,000 → $24 | buy animal {'COW': 1, 'SHEEP': 4}; buy seed {'MELON': 5, 'WHEAT': 5}; buy feed {'WHEAT': 4}; hire 4 ($7.0) |
| 0/03 | $24 → $24 | build {'PASTURE': 1} |
| 0/04 | $24 → $24 | place animal {'SHEEP': 1}; build {'PASTURE': 1} |
| 0/05 | $24 → $24 | plant {'MELON': 1}; place animal {'COW': 1} |
| 0/07 | $24 → $24 | plant {'WHEAT': 1} |
| 0/08 | $24 → $24 | plant {'WHEAT': 1}; build {'PASTURE': 1} |
| 0/09 | $24 → $24 | place animal {'SHEEP': 1} |
| 0/10 | $24 → $24 | plant {'WHEAT': 1} |
| 0/12 | $24 → $24 | plant {'MELON': 1} |
| 0/13 | $24 → $24 | plant {'WHEAT': 1}; build {'PASTURE': 1} |
| 0/14 | $24 → $24 | place animal {'SHEEP': 1} |
| 0/15 | $24 → $24 | plant {'MELON': 1} |
| 0/16 | $24 → $24 | plant {'WHEAT': 1} |
| 0/19 | $24 → $24 | plant {'MELON': 1}; build {'PASTURE': 1} |
| 0/20 | $24 → $24 | place animal {'SHEEP': 1} |
| 0/22 | $24 → $24 | plant {'MELON': 1} |
| 1/00 | $24 → $23 | hire 1 ($1.0) |
| 1/02 | $23 → $23 | collect fertilizer 1 |
| 1/04 | $23 → $23 | collect fertilizer 1 |
| 1/07 | $23 → $23 | collect fertilizer 2 |
| 1/09 | $23 → $23 | collect fertilizer 1 |
| 2/00 | $23 → $343 | buy feed {'WHEAT': 6}; sell 5 FERTILIZER for $496 @ [100, 100, 99, 99, 98]; hire 2 ($2.0) |
| 2/03 | $343 → $313 | buy feed {'WHEAT': 1} |
| 2/04 | $313 → $313 | collect fertilizer 1 |
| 2/05 | $313 → $283 | buy feed {'WHEAT': 1} |
| 2/06 | $283 → $283 | collect fertilizer 1 |
| 2/09 | $283 → $253 | buy feed {'WHEAT': 1} |
| 2/10 | $253 → $253 | collect fertilizer 1 |
| 2/14 | $253 → $222 | buy feed {'WHEAT': 1} |
| 2/18 | $222 → $191 | buy feed {'WHEAT': 1} |
| 2/19 | $191 → $191 | collect fertilizer 1 |
| 3/00 | $191 → $267 | buy seed {'STRAWBERRY': 3, 'WHEAT': 1}; sell 4 FERTILIZER for $390 @ [98, 98, 97, 97]; hire 3 ($4.0) |
| 3/03 | $267 → $236 | buy feed {'WHEAT': 1} |
| 3/04 | $236 → $236 | collect fertilizer 1 |
| 3/05 | $236 → $205 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 1} |
| 3/06 | $205 → $205 | collect fertilizer 1 |
| 3/08 | $205 → $205 | plant {'STRAWBERRY': 1} |
| 3/09 | $205 → $174 | buy feed {'WHEAT': 1} |
| 3/10 | $174 → $174 | collect fertilizer 1 |
| 3/11 | $174 → $174 | plant {'STRAWBERRY': 1}; collect fertilizer 1 |
| 3/14 | $174 → $143 | plant {'WHEAT': 1}; buy feed {'WHEAT': 1} |
| 3/16 | $143 → $111 | buy feed {'WHEAT': 1} |
| 4/00 | $111 → $489 | sell 4 FERTILIZER for $382 @ [96, 96, 95, 95]; hire 3 ($4.0) |
| 4/01 | $489 → $439 | buy seed {'WHEAT': 5} |
| 4/03 | $439 → $407 | buy feed {'WHEAT': 1} |
| 4/04 | $407 → $407 | collect fertilizer 1 |
| 4/05 | $407 → $375 | buy feed {'WHEAT': 1} |
| 4/06 | $375 → $375 | collect fertilizer 1 |
| 4/08 | $375 → $375 | harvest {'WHEAT': 4} |
| 4/09 | $375 → $375 | plant {'WHEAT': 1} |
| 4/10 | $375 → $375 | collect fertilizer 1 |
| 4/13 | $375 → $375 | harvest {'WHEAT': 4} |
| 4/14 | $375 → $375 | plant {'WHEAT': 1} |
| 4/15 | $375 → $375 | harvest {'WHEAT': 4} |
| 4/16 | $375 → $375 | plant {'WHEAT': 1}; harvest {'WHEAT': 4} |
| 4/18 | $375 → $375 | harvest {'WHEAT': 4} |
| 4/19 | $375 → $375 | plant {'WHEAT': 2}; collect fertilizer 1 |
| 5/00 | $375 → $455 | buy animal {'COW': 1}; buy seed {'STRAWBERRY': 4, 'WHEAT': 1}; sell 4 FERTILIZER for $375 @ [94, 94, 94, 93]; sell 17 WHEAT for $519 @ [32, 32, 32, 31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29, 29, 29]; hire 3 ($4.0) |
| 5/01 | $455 → $426 | buy feed {'WHEAT': 1} |
| 5/04 | $426 → $397 | buy feed {'WHEAT': 1} |
| 5/05 | $397 → $367 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 5/06 | $367 → $367 | plant {'STRAWBERRY': 1}; collect fertilizer 1 |
| 5/08 | $367 → $367 | build {'PASTURE': 1} |
| 5/09 | $367 → $337 | place animal {'COW': 1}; buy feed {'WHEAT': 1} |
| 5/10 | $337 → $337 | plant {'WHEAT': 1}; collect fertilizer 1 |
| 5/11 | $337 → $307 | buy feed {'WHEAT': 1} |
| 5/14 | $307 → $277 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 5/18 | $277 → $247 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 1} |
| 5/21 | $247 → $247 | plant {'STRAWBERRY': 1} |
| 6/00 | $247 → $611 | sell 4 FERTILIZER for $368 @ [93, 92, 92, 91]; hire 3 ($4.0) |
| 6/02 | $611 → $611 | harvest {'WOOL': 5} |
| 6/04 | $611 → $580 | harvest {'WOOL': 5}; buy feed {'WHEAT': 1} |
| 6/05 | $580 → $580 | collect fertilizer 1 |
| 6/06 | $580 → $549 | buy feed {'WHEAT': 1} |
| 6/07 | $549 → $549 | collect fertilizer 1 |
| 6/08 | $549 → $518 | buy feed {'WHEAT': 1} |
| 6/09 | $518 → $518 | harvest {'WOOL': 5}; collect fertilizer 1 |
| 6/11 | $518 → $487 | buy feed {'WHEAT': 1} |
| 6/12 | $487 → $455 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 6/13 | $455 → $455 | collect fertilizer 1 |
| 6/16 | $455 → $777 | sell 3 FERTILIZER for $271 @ [91, 90, 90]; sell 5 WOOL for $1051 @ [218, 215, 212, 206, 200]; buy land 1 ($1000.0) |
| 6/17 | $777 → $64 | buy animal {'COW': 1}; buy seed {'STRAWBERRY': 3, 'WHEAT': 1}; hire 1 ($3.0) |
| 6/20 | $64 → $64 | plant {'STRAWBERRY': 1}; build {'PASTURE': 2} |
| 6/21 | $64 → $64 | place animal {'COW': 1} |
| 6/23 | $64 → $64 | plant {'STRAWBERRY': 1} |
| 7/00 | $64 → $1,306 | buy animal {'COW': 2}; sell 2 FERTILIZER for $179 @ [90, 89]; sell 10 WOOL for $1896 @ [199, 199, 197, 195, 193, 190, 187, 183, 179, 174]; hire 7 ($33.0) |
| 7/01 | $1,306 → $180 | buy seed {'STRAWBERRY': 9, 'WHEAT': 3}; buy feed {'WHEAT': 6} |
| 7/03 | $180 → $147 | buy feed {'WHEAT': 1} |
| 7/04 | $147 → $114 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 7/05 | $114 → $81 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 7/06 | $81 → $81 | plant {'STRAWBERRY': 1}; collect fertilizer 1 |
| 7/07 | $81 → $48 | buy feed {'WHEAT': 1}; build {'PASTURE': 1} |
| 7/08 | $48 → $48 | plant {'STRAWBERRY': 1}; place animal {'COW': 1}; collect fertilizer 1 |
| 7/09 | $48 → $14 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 1} |
| 7/10 | $14 → $14 | collect fertilizer 1 |
| 7/11 | $14 → $14 | plant {'STRAWBERRY': 1} |
| 7/12 | $14 → $14 | plant {'STRAWBERRY': 1}; build {'PASTURE': 1} |
| 7/13 | $14 → $14 | place animal {'COW': 1} |
| 7/14 | $14 → $14 | plant {'STRAWBERRY': 1} |
| 7/15 | $14 → $14 | plant {'STRAWBERRY': 1, 'WHEAT': 1} |
| 7/16 | $14 → $14 | harvest {'WHEAT': 4} |
| 7/17 | $14 → $14 | plant {'WHEAT': 1}; collect fertilizer 1 |
| 7/18 | $14 → $14 | plant {'STRAWBERRY': 1} |
| 7/20 | $14 → $14 | plant {'WHEAT': 2} |
| 7/22 | $14 → $14 | plant {'STRAWBERRY': 1} |
| 8/00 | $14 → $158 | buy animal {'COW': 1}; buy seed {'WHEAT': 3}; sell 6 FERTILIZER for $526 @ [89, 88, 88, 87, 87, 87]; sell 2 WHEAT for $68 @ [34, 34]; hire 6 ($20.0) |
| 8/01 | $158 → $8 | buy seed {'STRAWBERRY': 1, 'WHEAT': 5} |
| 8/03 | $8 → $8 | harvest {'MILK': 6} |
| 8/04 | $8 → $8 | collect fertilizer 2 |
| 8/05 | $8 → $8 | build {'PASTURE': 1} |
| 8/06 | $8 → $8 | place animal {'COW': 1}; collect fertilizer 1 |
| 8/07 | $8 → $8 | harvest {'WHEAT': 4} |
| 8/08 | $8 → $8 | plant {'WHEAT': 1}; collect fertilizer 2 |
| 8/11 | $8 → $8 | build {'PASTURE': 1} |
| 8/12 | $8 → $8 | harvest {'WHEAT': 4}; collect fertilizer 1 |
| 8/13 | $8 → $8 | plant {'WHEAT': 1} |
| 8/14 | $8 → $8 | plant {'STRAWBERRY': 1} |
| 8/15 | $8 → $8 | collect fertilizer 1 |
| 8/16 | $8 → $8 | plant {'WHEAT': 1}; harvest {'WHEAT': 4} |
| 8/17 | $8 → $8 | plant {'WHEAT': 1}; harvest {'WHEAT': 4} |
| 8/18 | $8 → $8 | plant {'WHEAT': 1}; collect fertilizer 1 |
| 8/19 | $8 → $8 | plant {'WHEAT': 1} |
| 8/20 | $8 → $8 | plant {'WHEAT': 1} |
| 8/21 | $8 → $8 | harvest {'WHEAT': 4} |
| 8/22 | $8 → $8 | plant {'WHEAT': 1} |
| 9/00 | $8 → $2,137 | sell 8 FERTILIZER for $677 @ [86, 86, 85, 85, 84, 84, 84, 83]; sell 6 MILK for $1050 @ [186, 183, 179, 175, 169, 158]; sell 13 WHEAT for $435 @ [34, 34, 34, 34, 34, 34, 33, 33, 33, 33, 33, 33, 33]; hire 7 ($33.0) |
| 9/01 | $2,137 → $2,127 | buy seed {'WHEAT': 1} |
| 9/02 | $2,127 → $2,127 | harvest {'WOOL': 4} |
| 9/03 | $2,127 → $2,094 | buy feed {'WHEAT': 1} |
| 9/04 | $2,094 → $1,994 | buy feed {'WHEAT': 3}; collect fertilizer 1 |
| 9/05 | $1,994 → $1,994 | collect fertilizer 3 |
| 9/07 | $1,994 → $1,960 | harvest {'WOOL': 4}; buy feed {'WHEAT': 1} |
| 9/08 | $1,960 → $1,892 | buy feed {'WHEAT': 2} |
| 9/09 | $1,892 → $1,858 | buy feed {'WHEAT': 1}; collect fertilizer 2 |
| 9/10 | $1,858 → $1,858 | collect fertilizer 1 |
| 9/12 | $1,858 → $1,858 | harvest {'WOOL': 4} |
| 9/13 | $1,858 → $1,824 | buy feed {'WHEAT': 1} |
| 9/14 | $1,824 → $1,789 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 9/15 | $1,789 → $1,789 | collect fertilizer 1 |
| 9/17 | $1,789 → $1,789 | harvest {'WHEAT': 4} |
| 9/18 | $1,789 → $1,789 | plant {'WHEAT': 1} |
| 10/00 | $1,789 → $1,291 | sell 2 WHEAT for $70 @ [35, 35]; sell 12 WOOL for $1465 @ [164, 158, 151, 144, 137, 129, 121, 112, 102, 93, 82, 72]; hire 7 ($33.0); buy land 1 ($2000.0) |
| 10/01 | $1,291 → $18 | buy seed {'MELON': 4}; hire 7 ($953.0) |
| 10/05 | $18 → $18 | collect fertilizer 2 |
| 10/06 | $18 → $18 | harvest {'MELON': 6}; collect fertilizer 2 |
| 10/07 | $18 → $18 | plant {'MELON': 1} |
| 10/08 | $18 → $18 | harvest {'MELON': 6} |
| 10/09 | $18 → $18 | plant {'MELON': 1}; harvest {'MELON': 6} |
| 10/10 | $18 → $18 | plant {'MELON': 1}; collect fertilizer 3 |
| 10/11 | $18 → $18 | harvest {'MELON': 6} |
| 10/12 | $18 → $257 | harvest {'MELON': 6}; buy seed {'MELON': 9, 'STRAWBERRY': 6}; buy feed {'WHEAT': 1}; sell 6 MELON for $1594 @ [272, 270, 268, 266, 262, 256] |
| 10/13 | $257 → $21 | plant {'MELON': 2, 'STRAWBERRY': 3}; buy seed {'STRAWBERRY': 2}; buy feed {'WHEAT': 1} |
| 10/15 | $21 → $503 | plant {'MELON': 1}; buy seed {'STRAWBERRY': 8}; buy feed {'WHEAT': 6}; collect fertilizer 1; sell 6 MELON for $1498 @ [250, 250, 250, 250, 249, 249] |
| 10/16 | $503 → $503 | plant {'MELON': 1, 'STRAWBERRY': 3} |
| 10/17 | $503 → $1,983 | harvest {'MILK': 3}; sell 6 MELON for $1480 @ [248, 248, 247, 246, 246, 245] |
| 10/18 | $1,983 → $1,983 | plant {'MELON': 1}; collect fertilizer 1 |
| 10/19 | $1,983 → $1,911 | plant {'MELON': 1, 'STRAWBERRY': 2}; buy feed {'WHEAT': 2} |
| 10/20 | $1,911 → $3,357 | plant {'STRAWBERRY': 1}; sell 6 MELON for $1446 @ [244, 243, 242, 240, 239, 238] |
| 10/21 | $3,357 → $3,357 | plant {'MELON': 1} |
| 10/22 | $3,357 → $4,741 | plant {'STRAWBERRY': 2}; buy seed {'WHEAT': 1}; sell 6 MELON for $1394 @ [236, 235, 233, 232, 230, 228] |
| 10/23 | $4,741 → $4,741 | plant {'WHEAT': 1} |

Milestone funding:

- **land_1** at day 6, hour 16: bank $455 → $777; cumulative sales $3,852 {'FERTILIZER': 2282, 'WHEAT': 519, 'WOOL': 1051}; cumulative spending $6,075.
- **land_2** at day 10, hour 0: bank $1,789 → $1,291; cumulative sales $10,218 {'FERTILIZER': 3664, 'MILK': 1050, 'WHEAT': 1092, 'WOOL': 4412}; cumulative spending $11,927.

## Dmitry Larko — episode 91869967 seat 1

Opponent: Valmorlee; seed: 122449146.

| Day/hour | Bank before → after | Successful economic events |
|---|---:|---|
| 0/00 | $3,000 → $12 | buy animal {'SHEEP': 4}; buy seed {'MELON': 5, 'WHEAT': 5}; buy feed {'WHEAT': 19}; hire 4 ($7.0) |
| 0/01 | $12 → $20 | buy animal {'COW': 1}; sell 14 WHEAT for $408 @ [30, 30, 30, 30, 29, 29, 29, 29, 29, 29, 29, 29, 28, 28] |
| 0/03 | $20 → $20 | build {'PASTURE': 1} |
| 0/04 | $20 → $20 | place animal {'SHEEP': 1}; build {'PASTURE': 1} |
| 0/05 | $20 → $20 | plant {'MELON': 1}; place animal {'COW': 1} |
| 0/07 | $20 → $20 | plant {'WHEAT': 1} |
| 0/08 | $20 → $20 | plant {'WHEAT': 1}; build {'PASTURE': 1} |
| 0/09 | $20 → $20 | place animal {'SHEEP': 1} |
| 0/10 | $20 → $20 | plant {'WHEAT': 1} |
| 0/12 | $20 → $20 | plant {'MELON': 1} |
| 0/13 | $20 → $20 | plant {'WHEAT': 1}; build {'PASTURE': 1} |
| 0/14 | $20 → $20 | place animal {'SHEEP': 1} |
| 0/15 | $20 → $20 | plant {'MELON': 1} |
| 0/16 | $20 → $20 | plant {'WHEAT': 1} |
| 0/19 | $20 → $20 | plant {'MELON': 1}; build {'PASTURE': 1} |
| 0/20 | $20 → $20 | place animal {'SHEEP': 1} |
| 0/22 | $20 → $20 | plant {'MELON': 1} |
| 1/00 | $20 → $19 | hire 1 ($1.0) |
| 1/02 | $19 → $19 | collect fertilizer 1 |
| 1/04 | $19 → $19 | collect fertilizer 1 |
| 1/07 | $19 → $19 | collect fertilizer 2 |
| 1/09 | $19 → $19 | collect fertilizer 1 |
| 2/00 | $19 → $339 | buy feed {'WHEAT': 6}; sell 5 FERTILIZER for $496 @ [100, 100, 99, 99, 98]; hire 2 ($2.0) |
| 2/03 | $339 → $309 | buy feed {'WHEAT': 1} |
| 2/04 | $309 → $309 | collect fertilizer 1 |
| 2/05 | $309 → $279 | buy feed {'WHEAT': 1} |
| 2/06 | $279 → $279 | collect fertilizer 1 |
| 2/09 | $279 → $249 | buy feed {'WHEAT': 1} |
| 2/10 | $249 → $249 | collect fertilizer 1 |
| 2/14 | $249 → $218 | buy feed {'WHEAT': 1} |
| 2/15 | $218 → $218 | collect fertilizer 1 |
| 2/18 | $218 → $187 | buy feed {'WHEAT': 1} |
| 2/19 | $187 → $187 | collect fertilizer 1 |
| 3/00 | $187 → $359 | buy seed {'STRAWBERRY': 3, 'WHEAT': 1}; sell 5 FERTILIZER for $486 @ [98, 98, 97, 97, 96]; hire 3 ($4.0) |
| 3/03 | $359 → $328 | buy feed {'WHEAT': 1} |
| 3/04 | $328 → $328 | collect fertilizer 1 |
| 3/05 | $328 → $297 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 1} |
| 3/06 | $297 → $297 | collect fertilizer 1 |
| 3/08 | $297 → $297 | plant {'STRAWBERRY': 1} |
| 3/09 | $297 → $266 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 3/10 | $266 → $266 | collect fertilizer 1 |
| 3/11 | $266 → $266 | plant {'STRAWBERRY': 1}; collect fertilizer 1 |
| 3/14 | $266 → $235 | plant {'WHEAT': 1}; buy feed {'WHEAT': 1} |
| 3/16 | $235 → $203 | buy feed {'WHEAT': 1} |
| 4/00 | $203 → $676 | sell 5 FERTILIZER for $477 @ [96, 96, 95, 95, 95]; hire 3 ($4.0) |
| 4/01 | $676 → $626 | buy seed {'WHEAT': 5} |
| 4/03 | $626 → $594 | buy feed {'WHEAT': 1} |
| 4/04 | $594 → $594 | collect fertilizer 1 |
| 4/05 | $594 → $562 | buy feed {'WHEAT': 1} |
| 4/06 | $562 → $562 | collect fertilizer 1 |
| 4/08 | $562 → $562 | harvest {'WHEAT': 4} |
| 4/09 | $562 → $562 | plant {'WHEAT': 1} |
| 4/10 | $562 → $562 | collect fertilizer 1 |
| 4/13 | $562 → $562 | harvest {'WHEAT': 4} |
| 4/14 | $562 → $562 | plant {'WHEAT': 1} |
| 4/15 | $562 → $562 | harvest {'WHEAT': 4}; collect fertilizer 1 |
| 4/16 | $562 → $562 | plant {'WHEAT': 1}; harvest {'WHEAT': 4} |
| 4/18 | $562 → $562 | harvest {'WHEAT': 4} |
| 4/19 | $562 → $562 | plant {'WHEAT': 2}; collect fertilizer 1 |
| 4/21 | $562 → $658 | sell 3 WHEAT for $96 @ [32, 32, 32] |
| 5/00 | $658 → $744 | buy animal {'COW': 1}; buy seed {'STRAWBERRY': 4, 'WHEAT': 1}; sell 5 FERTILIZER for $468 @ [94, 94, 94, 93, 93]; sell 14 WHEAT for $432 @ [32, 32, 32, 31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30]; hire 3 ($4.0) |
| 5/01 | $744 → $715 | buy feed {'WHEAT': 1} |
| 5/04 | $715 → $686 | buy feed {'WHEAT': 1} |
| 5/05 | $686 → $656 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 5/06 | $656 → $656 | plant {'STRAWBERRY': 1}; collect fertilizer 1 |
| 5/08 | $656 → $656 | build {'PASTURE': 1} |
| 5/09 | $656 → $626 | place animal {'COW': 1}; buy feed {'WHEAT': 1} |
| 5/10 | $626 → $626 | plant {'WHEAT': 1}; collect fertilizer 1 |
| 5/11 | $626 → $596 | buy feed {'WHEAT': 1} |
| 5/14 | $596 → $566 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 5/15 | $566 → $566 | collect fertilizer 1 |
| 5/18 | $566 → $536 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 1} |
| 5/23 | $536 → $536 | plant {'STRAWBERRY': 1} |
| 6/00 | $536 → $991 | sell 5 FERTILIZER for $459 @ [93, 92, 92, 91, 91]; hire 3 ($4.0) |
| 6/02 | $991 → $991 | harvest {'WOOL': 5} |
| 6/04 | $991 → $960 | harvest {'WOOL': 5}; buy feed {'WHEAT': 1} |
| 6/05 | $960 → $960 | collect fertilizer 1 |
| 6/06 | $960 → $929 | buy feed {'WHEAT': 1} |
| 6/07 | $929 → $929 | collect fertilizer 1 |
| 6/08 | $929 → $898 | buy feed {'WHEAT': 1} |
| 6/09 | $898 → $898 | harvest {'WOOL': 5}; collect fertilizer 1 |
| 6/11 | $898 → $867 | buy feed {'WHEAT': 1} |
| 6/12 | $867 → $835 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 6/13 | $835 → $835 | collect fertilizer 1 |
| 6/15 | $835 → $867 | harvest {'WOOL': 5}; sell 1 WHEAT for $32 @ [32] |
| 6/16 | $867 → $1,189 | sell 3 FERTILIZER for $271 @ [91, 90, 90]; sell 5 WOOL for $1051 @ [218, 215, 212, 206, 200]; buy land 1 ($1000.0) |
| 6/17 | $1,189 → $112 | buy animal {'COW': 2}; buy seed {'STRAWBERRY': 2, 'WHEAT': 1}; buy feed {'WHEAT': 2}; hire 1 ($3.0) |
| 6/18 | $112 → $112 | collect fertilizer 1 |
| 6/19 | $112 → $80 | buy feed {'WHEAT': 1} |
| 6/20 | $80 → $80 | plant {'STRAWBERRY': 1}; build {'PASTURE': 2} |
| 6/21 | $80 → $80 | place animal {'COW': 1} |
| 6/23 | $80 → $80 | plant {'STRAWBERRY': 1} |
| 7/00 | $80 → $2,230 | buy animal {'COW': 2}; sell 3 FERTILIZER for $268 @ [90, 89, 89]; sell 15 WOOL for $2715 @ [199, 199, 197, 195, 193, 190, 187, 183, 179, 174, 169, 167, 164, 161, 158]; hire 7 ($33.0) |
| 7/01 | $2,230 → $1,070 | buy seed {'STRAWBERRY': 10, 'WHEAT': 3}; buy feed {'WHEAT': 4} |
| 7/03 | $1,070 → $1,037 | buy feed {'WHEAT': 1} |
| 7/04 | $1,037 → $971 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 2}; collect fertilizer 1 |
| 7/05 | $971 → $971 | collect fertilizer 2 |
| 7/06 | $971 → $971 | plant {'STRAWBERRY': 1} |
| 7/07 | $971 → $938 | buy feed {'WHEAT': 1}; build {'PASTURE': 1} |
| 7/08 | $938 → $905 | plant {'STRAWBERRY': 1}; place animal {'COW': 1}; buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 7/09 | $905 → $905 | plant {'STRAWBERRY': 1}; collect fertilizer 1 |
| 7/10 | $905 → $871 | buy feed {'WHEAT': 1} |
| 7/11 | $871 → $871 | plant {'STRAWBERRY': 1} |
| 7/12 | $871 → $871 | plant {'STRAWBERRY': 1}; build {'PASTURE': 1} |
| 7/13 | $871 → $837 | place animal {'COW': 1}; buy feed {'WHEAT': 1} |
| 7/14 | $837 → $837 | plant {'STRAWBERRY': 1}; collect fertilizer 1 |
| 7/15 | $837 → $803 | plant {'STRAWBERRY': 1, 'WHEAT': 1}; buy feed {'WHEAT': 1} |
| 7/16 | $803 → $803 | harvest {'WHEAT': 4} |
| 7/17 | $803 → $803 | plant {'WHEAT': 1}; collect fertilizer 1 |
| 7/18 | $803 → $803 | plant {'STRAWBERRY': 1} |
| 7/19 | $803 → $803 | place animal {'COW': 1} |
| 7/20 | $803 → $803 | plant {'WHEAT': 2} |
| 7/21 | $803 → $871 | sell 2 WHEAT for $68 @ [34, 34] |
| 7/22 | $871 → $871 | plant {'STRAWBERRY': 1} |
| 8/00 | $871 → $633 | buy animal {'COW': 2}; buy seed {'WHEAT': 3}; sell 7 FERTILIZER for $612 @ [89, 88, 88, 87, 87, 87, 86]; hire 6 ($20.0) |
| 8/01 | $633 → $315 | buy seed {'STRAWBERRY': 2, 'WHEAT': 5}; buy feed {'WHEAT': 2} |
| 8/03 | $315 → $247 | harvest {'MILK': 6}; buy feed {'WHEAT': 2} |
| 8/04 | $247 → $247 | collect fertilizer 2 |
| 8/05 | $247 → $213 | buy feed {'WHEAT': 1}; build {'PASTURE': 1} |
| 8/06 | $213 → $213 | place animal {'COW': 1}; collect fertilizer 1 |
| 8/07 | $213 → $145 | harvest {'WHEAT': 4}; buy feed {'WHEAT': 2} |
| 8/08 | $145 → $145 | plant {'WHEAT': 1}; collect fertilizer 2 |
| 8/10 | $145 → $145 | collect fertilizer 1 |
| 8/11 | $145 → $145 | build {'PASTURE': 1} |
| 8/12 | $145 → $145 | harvest {'WHEAT': 4}; place animal {'COW': 1}; collect fertilizer 1 |
| 8/13 | $145 → $145 | plant {'WHEAT': 1} |
| 8/14 | $145 → $145 | plant {'STRAWBERRY': 1} |
| 8/15 | $145 → $145 | collect fertilizer 1 |
| 8/16 | $145 → $145 | plant {'WHEAT': 1}; harvest {'WHEAT': 4} |
| 8/17 | $145 → $145 | plant {'STRAWBERRY': 1, 'WHEAT': 1}; harvest {'WHEAT': 4} |
| 8/18 | $145 → $145 | plant {'WHEAT': 1}; collect fertilizer 2 |
| 8/19 | $145 → $145 | plant {'WHEAT': 1} |
| 8/20 | $145 → $145 | plant {'WHEAT': 1} |
| 8/21 | $145 → $349 | harvest {'WHEAT': 4}; sell 6 WHEAT for $204 @ [34, 34, 34, 34, 34, 34] |
| 8/22 | $349 → $349 | plant {'WHEAT': 1} |
| 9/00 | $349 → $2,446 | sell 10 FERTILIZER for $843 @ [86, 86, 85, 85, 84, 84, 84, 83, 83, 83]; sell 6 MILK for $1050 @ [186, 183, 179, 175, 169, 158]; sell 7 WHEAT for $237 @ [34, 34, 34, 34, 34, 34, 33]; hire 7 ($33.0) |
| 9/01 | $2,446 → $2,436 | buy seed {'WHEAT': 1} |
| 9/02 | $2,436 → $2,436 | harvest {'WOOL': 4} |
| 9/03 | $2,436 → $2,403 | buy feed {'WHEAT': 1} |
| 9/04 | $2,403 → $2,303 | buy feed {'WHEAT': 3}; collect fertilizer 1 |
| 9/05 | $2,303 → $2,303 | collect fertilizer 3 |
| 9/07 | $2,303 → $2,269 | harvest {'WOOL': 4}; buy feed {'WHEAT': 1} |
| 9/08 | $2,269 → $2,201 | buy feed {'WHEAT': 2}; collect fertilizer 1 |
| 9/09 | $2,201 → $2,167 | buy feed {'WHEAT': 1}; collect fertilizer 2 |
| 9/10 | $2,167 → $2,201 | collect fertilizer 1; sell 1 WHEAT for $34 @ [34] |
| 9/12 | $2,201 → $2,167 | harvest {'WOOL': 4}; buy feed {'WHEAT': 1} |
| 9/14 | $2,167 → $2,097 | buy feed {'WHEAT': 2}; collect fertilizer 1 |
| 9/15 | $2,097 → $2,097 | collect fertilizer 1 |
| 9/17 | $2,097 → $2,097 | harvest {'WHEAT': 4} |
| 9/18 | $2,097 → $2,097 | plant {'WHEAT': 1}; harvest {'WOOL': 4} |
| 9/19 | $2,097 → $2,097 | collect fertilizer 1 |
| 9/21 | $2,097 → $2,167 | collect fertilizer 1; sell 2 WHEAT for $70 @ [35, 35] |
| 10/00 | $2,167 → $1,807 | sell 16 WOOL for $1673 @ [164, 158, 151, 144, 137, 129, 121, 112, 102, 93, 82, 72, 61, 55, 49, 43]; hire 7 ($33.0); buy land 1 ($2000.0) |
| 10/01 | $1,807 → $34 | buy seed {'MELON': 9, 'STRAWBERRY': 1}; hire 7 ($953.0) |
| 10/03 | $34 → $34 | plant {'STRAWBERRY': 1} |
| 10/05 | $34 → $34 | collect fertilizer 2 |
| 10/06 | $34 → $34 | harvest {'MELON': 6}; collect fertilizer 2 |
| 10/07 | $34 → $34 | plant {'MELON': 1} |
| 10/08 | $34 → $34 | harvest {'MELON': 6} |
| 10/09 | $34 → $34 | plant {'MELON': 1}; harvest {'MELON': 6}; collect fertilizer 1 |
| 10/10 | $34 → $34 | plant {'MELON': 1}; collect fertilizer 3 |
| 10/11 | $34 → $34 | harvest {'MELON': 6} |
| 10/12 | $34 → $268 | plant {'MELON': 2}; harvest {'MELON': 6}; buy seed {'MELON': 4, 'STRAWBERRY': 9}; buy feed {'WHEAT': 4}; sell 6 MELON for $1594 @ [272, 270, 268, 266, 262, 256] |
| 10/13 | $268 → $127 | plant {'MELON': 2, 'STRAWBERRY': 2}; buy feed {'WHEAT': 4} |
| 10/14 | $127 → $55 | buy feed {'WHEAT': 2} |
| 10/15 | $55 → $1,553 | plant {'MELON': 1, 'STRAWBERRY': 1}; collect fertilizer 2; sell 6 MELON for $1498 @ [250, 250, 250, 250, 249, 249] |
| 10/16 | $1,553 → $1,553 | plant {'MELON': 1, 'STRAWBERRY': 2} |
| 10/17 | $1,553 → $3,033 | harvest {'MILK': 3}; sell 6 MELON for $1480 @ [248, 248, 247, 246, 246, 245] |
| 10/18 | $3,033 → $3,033 | plant {'MELON': 1, 'STRAWBERRY': 1}; collect fertilizer 2 |
| 10/19 | $3,033 → $2,961 | plant {'MELON': 1, 'STRAWBERRY': 2}; buy feed {'WHEAT': 2} |
| 10/20 | $2,961 → $4,407 | sell 6 MELON for $1446 @ [244, 243, 242, 240, 239, 238] |
| 10/21 | $4,407 → $4,407 | plant {'MELON': 1} |
| 10/22 | $4,407 → $5,791 | plant {'STRAWBERRY': 1}; buy seed {'WHEAT': 1}; sell 6 MELON for $1394 @ [236, 235, 233, 232, 230, 228] |

Milestone funding:

- **land_1** at day 6, hour 16: bank $867 → $1,189; cumulative sales $4,676 {'FERTILIZER': 2657, 'WHEAT': 968, 'WOOL': 1051}; cumulative spending $6,487.
- **eight_cows** at day 8, hour 12: bank $145 → $145; cumulative sales $8,339 {'FERTILIZER': 3537, 'WHEAT': 1036, 'WOOL': 3766}; cumulative spending $11,194.
- **land_2** at day 10, hour 0: bank $2,167 → $1,807; cumulative sales $12,450 {'FERTILIZER': 4380, 'MILK': 1050, 'WHEAT': 1581, 'WOOL': 5439}; cumulative spending $13,643.

## THUNDER THUNDER — episode 91870919 seat 0

Opponent: Victor @ Tufa Labs; seed: 1977148940.

| Day/hour | Bank before → after | Successful economic events |
|---|---:|---|
| 0/00 | $3,000 → $28 | buy animal {'COW': 1, 'SHEEP': 4}; buy seed {'MELON': 5, 'WHEAT': 5}; buy feed {'WHEAT': 4}; hire 4 ($7.0) |
| 0/02 | $28 → $0 | buy feed {'WHEAT': 1} |
| 0/04 | $0 → $0 | build {'PASTURE': 2} |
| 0/05 | $0 → $0 | plant {'MELON': 1}; place animal {'COW': 1, 'SHEEP': 1} |
| 0/07 | $0 → $0 | plant {'WHEAT': 1} |
| 0/08 | $0 → $0 | plant {'WHEAT': 1} |
| 0/09 | $0 → $0 | build {'PASTURE': 1} |
| 0/10 | $0 → $0 | plant {'WHEAT': 1}; place animal {'SHEEP': 1} |
| 0/12 | $0 → $0 | plant {'MELON': 1} |
| 0/13 | $0 → $0 | plant {'WHEAT': 1} |
| 0/14 | $0 → $0 | build {'PASTURE': 1} |
| 0/15 | $0 → $0 | plant {'MELON': 1}; place animal {'SHEEP': 1} |
| 0/16 | $0 → $0 | plant {'WHEAT': 1} |
| 0/19 | $0 → $0 | plant {'MELON': 1} |
| 0/20 | $0 → $0 | build {'PASTURE': 1} |
| 0/21 | $0 → $0 | place animal {'SHEEP': 1} |
| 0/22 | $0 → $0 | plant {'MELON': 1} |
| 1/04 | $0 → $0 | collect fertilizer 1 |
| 1/07 | $0 → $0 | collect fertilizer 1 |
| 1/10 | $0 → $0 | collect fertilizer 1 |
| 1/14 | $0 → $0 | collect fertilizer 1 |
| 1/17 | $0 → $0 | collect fertilizer 1 |
| 2/00 | $0 → $318 | buy feed {'WHEAT': 6}; sell 5 FERTILIZER for $496 @ [100, 100, 99, 99, 98]; hire 2 ($2.0) |
| 2/03 | $318 → $288 | buy feed {'WHEAT': 1} |
| 2/04 | $288 → $288 | collect fertilizer 1 |
| 2/05 | $288 → $258 | buy feed {'WHEAT': 1} |
| 2/06 | $258 → $258 | collect fertilizer 1 |
| 2/09 | $258 → $228 | buy feed {'WHEAT': 1} |
| 2/10 | $228 → $228 | collect fertilizer 1 |
| 2/14 | $228 → $197 | buy feed {'WHEAT': 1} |
| 2/15 | $197 → $197 | collect fertilizer 1 |
| 2/18 | $197 → $166 | buy feed {'WHEAT': 1} |
| 2/19 | $166 → $166 | collect fertilizer 1 |
| 3/00 | $166 → $338 | buy seed {'STRAWBERRY': 3, 'WHEAT': 1}; sell 5 FERTILIZER for $486 @ [98, 98, 97, 97, 96]; hire 3 ($4.0) |
| 3/03 | $338 → $307 | buy feed {'WHEAT': 1} |
| 3/04 | $307 → $307 | collect fertilizer 1 |
| 3/05 | $307 → $276 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 1} |
| 3/06 | $276 → $276 | collect fertilizer 1 |
| 3/08 | $276 → $276 | plant {'STRAWBERRY': 1} |
| 3/09 | $276 → $244 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 3/10 | $244 → $244 | collect fertilizer 1 |
| 3/11 | $244 → $244 | collect fertilizer 1 |
| 3/12 | $244 → $244 | plant {'STRAWBERRY': 1} |
| 3/14 | $244 → $212 | plant {'WHEAT': 1}; buy feed {'WHEAT': 1} |
| 3/16 | $212 → $180 | buy feed {'WHEAT': 1} |
| 4/00 | $180 → $652 | sell 5 FERTILIZER for $476 @ [96, 96, 95, 95, 94]; hire 3 ($4.0) |
| 4/01 | $652 → $602 | buy seed {'WHEAT': 5} |
| 4/03 | $602 → $570 | buy feed {'WHEAT': 1} |
| 4/04 | $570 → $570 | collect fertilizer 1 |
| 4/05 | $570 → $537 | buy feed {'WHEAT': 1} |
| 4/06 | $537 → $537 | collect fertilizer 1 |
| 4/08 | $537 → $537 | harvest {'WHEAT': 4} |
| 4/09 | $537 → $537 | plant {'WHEAT': 1} |
| 4/10 | $537 → $537 | collect fertilizer 1 |
| 4/13 | $537 → $537 | harvest {'WHEAT': 4} |
| 4/14 | $537 → $537 | plant {'WHEAT': 1} |
| 4/15 | $537 → $537 | harvest {'WHEAT': 4}; collect fertilizer 1 |
| 4/16 | $537 → $537 | plant {'WHEAT': 1}; harvest {'WHEAT': 4} |
| 4/18 | $537 → $537 | harvest {'WHEAT': 4} |
| 4/19 | $537 → $537 | plant {'WHEAT': 2}; collect fertilizer 1 |
| 5/00 | $537 → $731 | buy animal {'COW': 1}; buy seed {'STRAWBERRY': 4, 'WHEAT': 1}; sell 5 FERTILIZER for $466 @ [94, 94, 93, 93, 92]; sell 17 WHEAT for $542 @ [33, 33, 33, 33, 32, 32, 32, 32, 32, 32, 32, 31, 31, 31, 31, 31, 31]; hire 3 ($4.0) |
| 5/01 | $731 → $700 | buy feed {'WHEAT': 1} |
| 5/04 | $700 → $669 | buy feed {'WHEAT': 1} |
| 5/05 | $669 → $638 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 5/06 | $638 → $638 | plant {'STRAWBERRY': 1}; collect fertilizer 1 |
| 5/08 | $638 → $638 | build {'PASTURE': 1} |
| 5/09 | $638 → $607 | place animal {'COW': 1}; buy feed {'WHEAT': 1} |
| 5/10 | $607 → $607 | plant {'WHEAT': 1}; collect fertilizer 1 |
| 5/11 | $607 → $576 | buy feed {'WHEAT': 1} |
| 5/14 | $576 → $544 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 5/15 | $544 → $544 | collect fertilizer 1 |
| 5/17 | $544 → $544 | plant {'STRAWBERRY': 1} |
| 5/18 | $544 → $512 | buy feed {'WHEAT': 1} |
| 5/22 | $512 → $512 | plant {'STRAWBERRY': 1} |
| 6/00 | $512 → $964 | sell 5 FERTILIZER for $456 @ [92, 92, 91, 91, 90]; hire 3 ($4.0) |
| 6/02 | $964 → $964 | harvest {'WOOL': 5} |
| 6/04 | $964 → $932 | harvest {'WOOL': 5}; buy feed {'WHEAT': 1} |
| 6/05 | $932 → $932 | collect fertilizer 1 |
| 6/06 | $932 → $899 | buy feed {'WHEAT': 1} |
| 6/07 | $899 → $899 | collect fertilizer 1 |
| 6/08 | $899 → $866 | buy feed {'WHEAT': 1} |
| 6/09 | $866 → $866 | harvest {'WOOL': 5}; collect fertilizer 1 |
| 6/11 | $866 → $833 | buy feed {'WHEAT': 1} |
| 6/12 | $833 → $800 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 6/13 | $800 → $800 | collect fertilizer 1 |
| 6/15 | $800 → $800 | harvest {'WOOL': 5} |
| 6/16 | $800 → $1,120 | sell 3 FERTILIZER for $269 @ [90, 90, 89]; sell 5 WOOL for $1051 @ [218, 215, 212, 206, 200]; buy land 1 ($1000.0) |
| 6/17 | $1,120 → $7 | buy animal {'COW': 2}; buy seed {'STRAWBERRY': 3, 'WHEAT': 1}; hire 1 ($3.0) |
| 6/18 | $7 → $7 | collect fertilizer 1 |
| 6/20 | $7 → $7 | plant {'STRAWBERRY': 1}; build {'PASTURE': 2} |
| 6/21 | $7 → $7 | place animal {'COW': 1} |
| 6/23 | $7 → $7 | plant {'STRAWBERRY': 1} |
| 7/00 | $7 → $2,121 | buy animal {'COW': 2}; sell 3 FERTILIZER for $265 @ [89, 88, 88]; sell 15 WOOL for $2682 @ [199, 199, 197, 195, 193, 190, 187, 183, 179, 174, 169, 164, 158, 151, 144]; hire 7 ($33.0) |
| 7/01 | $2,121 → $987 | buy seed {'STRAWBERRY': 9, 'WHEAT': 3}; buy feed {'WHEAT': 6} |
| 7/03 | $987 → $953 | buy feed {'WHEAT': 1} |
| 7/04 | $953 → $918 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 7/05 | $918 → $883 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 7/06 | $883 → $883 | plant {'STRAWBERRY': 1}; collect fertilizer 1 |
| 7/07 | $883 → $848 | buy feed {'WHEAT': 1}; build {'PASTURE': 1} |
| 7/08 | $848 → $848 | plant {'STRAWBERRY': 1}; place animal {'COW': 1}; collect fertilizer 1 |
| 7/09 | $848 → $813 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 1} |
| 7/10 | $813 → $778 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 7/11 | $778 → $778 | plant {'STRAWBERRY': 1} |
| 7/12 | $778 → $778 | plant {'STRAWBERRY': 1}; build {'PASTURE': 1} |
| 7/13 | $778 → $778 | place animal {'COW': 1} |
| 7/14 | $778 → $743 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 1} |
| 7/15 | $743 → $708 | plant {'STRAWBERRY': 1, 'WHEAT': 1}; buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 7/16 | $708 → $708 | harvest {'WHEAT': 4} |
| 7/17 | $708 → $708 | plant {'WHEAT': 1}; collect fertilizer 1 |
| 7/18 | $708 → $708 | plant {'STRAWBERRY': 1} |
| 7/19 | $708 → $708 | place animal {'COW': 1} |
| 7/20 | $708 → $708 | plant {'WHEAT': 2} |
| 7/22 | $708 → $708 | plant {'STRAWBERRY': 1} |
| 8/00 | $708 → $535 | buy animal {'COW': 2}; buy seed {'WHEAT': 3}; sell 7 FERTILIZER for $605 @ [88, 87, 87, 86, 86, 86, 85]; sell 2 WHEAT for $72 @ [36, 36]; hire 6 ($20.0) |
| 8/01 | $535 → $213 | buy seed {'STRAWBERRY': 2, 'WHEAT': 5}; buy feed {'WHEAT': 2} |
| 8/03 | $213 → $141 | harvest {'MILK': 6}; buy feed {'WHEAT': 2} |
| 8/04 | $141 → $141 | collect fertilizer 2 |
| 8/05 | $141 → $105 | buy feed {'WHEAT': 1}; build {'PASTURE': 1} |
| 8/06 | $105 → $105 | place animal {'COW': 1}; collect fertilizer 1 |
| 8/07 | $105 → $33 | harvest {'WHEAT': 4}; buy feed {'WHEAT': 2} |
| 8/08 | $33 → $33 | plant {'WHEAT': 1}; collect fertilizer 2 |
| 8/10 | $33 → $33 | collect fertilizer 1 |
| 8/11 | $33 → $33 | build {'PASTURE': 1} |
| 8/12 | $33 → $33 | harvest {'WHEAT': 4}; place animal {'COW': 1}; collect fertilizer 1 |
| 8/13 | $33 → $33 | plant {'WHEAT': 1} |
| 8/14 | $33 → $33 | plant {'STRAWBERRY': 1} |
| 8/15 | $33 → $33 | collect fertilizer 1 |
| 8/16 | $33 → $33 | plant {'WHEAT': 1}; harvest {'WHEAT': 4} |
| 8/17 | $33 → $33 | plant {'STRAWBERRY': 1, 'WHEAT': 1}; harvest {'WHEAT': 4} |
| 8/18 | $33 → $33 | plant {'WHEAT': 1}; collect fertilizer 2 |
| 8/19 | $33 → $33 | plant {'WHEAT': 1} |
| 8/20 | $33 → $33 | plant {'WHEAT': 1} |
| 8/21 | $33 → $33 | harvest {'WHEAT': 4} |
| 8/22 | $33 → $33 | plant {'WHEAT': 1} |
| 9/00 | $33 → $2,658 | sell 10 FERTILIZER for $830 @ [85, 84, 84, 84, 83, 83, 82, 82, 82, 81]; sell 6 MILK for $1357 @ [229, 228, 227, 226, 224, 223]; sell 13 WHEAT for $471 @ [37, 37, 37, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36]; hire 7 ($33.0) |
| 9/01 | $2,658 → $2,648 | buy seed {'WHEAT': 1} |
| 9/02 | $2,648 → $2,648 | harvest {'WOOL': 4} |
| 9/03 | $2,648 → $2,612 | buy feed {'WHEAT': 1} |
| 9/04 | $2,612 → $2,504 | buy feed {'WHEAT': 3}; collect fertilizer 1 |
| 9/05 | $2,504 → $2,504 | collect fertilizer 3 |
| 9/07 | $2,504 → $2,468 | harvest {'WOOL': 4}; buy feed {'WHEAT': 1} |
| 9/08 | $2,468 → $2,396 | buy feed {'WHEAT': 2}; collect fertilizer 1 |
| 9/09 | $2,396 → $2,359 | buy feed {'WHEAT': 1}; collect fertilizer 2 |
| 9/10 | $2,359 → $2,359 | collect fertilizer 1 |
| 9/12 | $2,359 → $2,359 | harvest {'WOOL': 4} |
| 9/13 | $2,359 → $2,322 | buy feed {'WHEAT': 1} |
| 9/14 | $2,322 → $2,285 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 9/15 | $2,285 → $2,285 | collect fertilizer 1 |
| 9/17 | $2,285 → $2,285 | harvest {'WHEAT': 4} |
| 9/18 | $2,285 → $2,285 | plant {'WHEAT': 1}; harvest {'WOOL': 4} |
| 9/19 | $2,285 → $2,285 | collect fertilizer 1 |
| 9/21 | $2,285 → $2,285 | collect fertilizer 1 |
| 10/00 | $2,285 → $2,437 | sell 2 WHEAT for $74 @ [37, 37]; sell 16 WOOL for $2111 @ [181, 177, 172, 167, 161, 154, 148, 141, 133, 125, 116, 107, 98, 88, 77, 66]; hire 7 ($33.0); buy land 1 ($2000.0) |
| 10/01 | $2,437 → $4 | buy animal {'SHEEP': 2}; buy seed {'MELON': 6}; hire 7 ($953.0) |
| 10/02 | $4 → $4 | build {'PASTURE': 1} |
| 10/04 | $4 → $4 | build {'PASTURE': 1} |
| 10/05 | $4 → $4 | collect fertilizer 2; build {'PASTURE': 1} |
| 10/06 | $4 → $4 | harvest {'MELON': 6}; place animal {'SHEEP': 1}; collect fertilizer 2; build {'PASTURE': 1} |
| 10/07 | $4 → $4 | plant {'MELON': 1} |
| 10/08 | $4 → $4 | harvest {'MELON': 6} |
| 10/09 | $4 → $4 | plant {'MELON': 1}; collect fertilizer 1 |
| 10/10 | $4 → $4 | harvest {'MELON': 6}; collect fertilizer 3; build {'PASTURE': 1} |
| 10/11 | $4 → $4 | plant {'MELON': 1}; harvest {'MELON': 6}; place animal {'SHEEP': 1} |
| 10/12 | $4 → $221 | plant {'MELON': 1}; harvest {'MELON': 6}; buy animal {'SHEEP': 1}; buy seed {'MELON': 8, 'STRAWBERRY': 2}; buy feed {'WHEAT': 1}; sell 6 MELON for $1594 @ [272, 270, 268, 266, 262, 256] |
| 10/13 | $221 → $21 | plant {'MELON': 2, 'STRAWBERRY': 2}; buy seed {'STRAWBERRY': 2} |
| 10/14 | $21 → $21 | plant {'STRAWBERRY': 1} |
| 10/15 | $21 → $401 | buy seed {'STRAWBERRY': 7}; buy feed {'WHEAT': 11}; collect fertilizer 2; sell 6 MELON for $1498 @ [250, 250, 250, 250, 249, 249] |
| 10/16 | $401 → $401 | plant {'MELON': 1, 'STRAWBERRY': 1}; harvest {'MILK': 3} |
| 10/17 | $401 → $401 | plant {'MELON': 1, 'STRAWBERRY': 1}; collect fertilizer 1 |
| 10/18 | $401 → $1,835 | buy feed {'WHEAT': 1}; sell 6 MELON for $1472 @ [246, 246, 246, 245, 245, 244] |
| 10/19 | $1,835 → $1,797 | plant {'MELON': 1, 'STRAWBERRY': 1}; buy feed {'WHEAT': 1} |
| 10/20 | $1,797 → $3,243 | plant {'MELON': 1, 'STRAWBERRY': 1}; collect fertilizer 1; sell 6 MELON for $1446 @ [244, 243, 242, 240, 239, 238] |
| 10/22 | $3,243 → $4,627 | plant {'STRAWBERRY': 1}; buy seed {'WHEAT': 1}; sell 6 MELON for $1394 @ [236, 235, 233, 232, 230, 228] |
| 10/23 | $4,627 → $4,627 | plant {'MELON': 1, 'STRAWBERRY': 1, 'WHEAT': 1} |

Milestone funding:

- **land_1** at day 6, hour 16: bank $800 → $1,120; cumulative sales $4,242 {'FERTILIZER': 2649, 'WHEAT': 542, 'WOOL': 1051}; cumulative spending $6,122.
- **eight_cows** at day 8, hour 12: bank $33 → $33; cumulative sales $7,866 {'FERTILIZER': 3519, 'WHEAT': 614, 'WOOL': 3733}; cumulative spending $10,833.
- **land_2** at day 10, hour 0: bank $2,285 → $2,437; cumulative sales $12,709 {'FERTILIZER': 4349, 'MILK': 1357, 'WHEAT': 1159, 'WOOL': 5844}; cumulative spending $13,272.

## Victor @ Tufa Labs — episode 91870919 seat 1

Opponent: THUNDER THUNDER; seed: 1977148940.

| Day/hour | Bank before → after | Successful economic events |
|---|---:|---|
| 0/00 | $3,000 → $3 | buy animal {'COW': 1, 'SHEEP': 4}; buy seed {'MELON': 3, 'WHEAT': 5}; buy feed {'WHEAT': 11}; hire 4 ($7.0) |
| 0/01 | $3 → $15 | buy seed {'MELON': 2}; sell 6 WHEAT for $172 @ [29, 29, 29, 29, 28, 28] |
| 0/03 | $15 → $15 | build {'PASTURE': 1} |
| 0/04 | $15 → $15 | place animal {'SHEEP': 1}; build {'PASTURE': 1} |
| 0/05 | $15 → $15 | plant {'MELON': 1}; place animal {'COW': 1} |
| 0/07 | $15 → $15 | plant {'WHEAT': 1} |
| 0/08 | $15 → $15 | plant {'WHEAT': 1}; build {'PASTURE': 1} |
| 0/09 | $15 → $15 | place animal {'SHEEP': 1} |
| 0/10 | $15 → $15 | plant {'WHEAT': 1} |
| 0/12 | $15 → $15 | plant {'MELON': 1} |
| 0/13 | $15 → $15 | plant {'WHEAT': 1}; build {'PASTURE': 1} |
| 0/14 | $15 → $15 | place animal {'SHEEP': 1} |
| 0/15 | $15 → $15 | plant {'MELON': 1} |
| 0/16 | $15 → $15 | plant {'WHEAT': 1} |
| 0/19 | $15 → $15 | plant {'MELON': 1}; build {'PASTURE': 1} |
| 0/20 | $15 → $15 | place animal {'SHEEP': 1} |
| 0/22 | $15 → $15 | plant {'MELON': 1} |
| 1/00 | $15 → $14 | hire 1 ($1.0) |
| 1/02 | $14 → $14 | collect fertilizer 1 |
| 1/04 | $14 → $14 | collect fertilizer 1 |
| 1/07 | $14 → $14 | collect fertilizer 2 |
| 1/09 | $14 → $14 | collect fertilizer 1 |
| 2/00 | $14 → $332 | buy feed {'WHEAT': 6}; sell 5 FERTILIZER for $496 @ [100, 100, 99, 99, 98]; hire 2 ($2.0) |
| 2/03 | $332 → $302 | buy feed {'WHEAT': 1} |
| 2/04 | $302 → $302 | collect fertilizer 1 |
| 2/05 | $302 → $272 | buy feed {'WHEAT': 1} |
| 2/06 | $272 → $272 | collect fertilizer 1 |
| 2/09 | $272 → $242 | buy feed {'WHEAT': 1} |
| 2/10 | $242 → $242 | collect fertilizer 1 |
| 2/14 | $242 → $211 | buy feed {'WHEAT': 1} |
| 2/15 | $211 → $211 | collect fertilizer 1 |
| 2/18 | $211 → $180 | buy feed {'WHEAT': 1} |
| 2/19 | $180 → $180 | collect fertilizer 1 |
| 3/00 | $180 → $352 | buy seed {'STRAWBERRY': 3, 'WHEAT': 1}; sell 5 FERTILIZER for $486 @ [98, 98, 97, 97, 96]; hire 3 ($4.0) |
| 3/03 | $352 → $321 | buy feed {'WHEAT': 1} |
| 3/04 | $321 → $321 | collect fertilizer 1 |
| 3/05 | $321 → $290 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 1} |
| 3/06 | $290 → $290 | collect fertilizer 1 |
| 3/08 | $290 → $290 | plant {'STRAWBERRY': 1} |
| 3/09 | $290 → $258 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 3/10 | $258 → $258 | collect fertilizer 1 |
| 3/11 | $258 → $258 | plant {'STRAWBERRY': 1}; collect fertilizer 1 |
| 3/14 | $258 → $226 | plant {'WHEAT': 1}; buy feed {'WHEAT': 1} |
| 3/16 | $226 → $194 | buy feed {'WHEAT': 1} |
| 4/00 | $194 → $666 | sell 5 FERTILIZER for $476 @ [96, 96, 95, 95, 94]; hire 3 ($4.0) |
| 4/01 | $666 → $616 | buy seed {'WHEAT': 5} |
| 4/03 | $616 → $584 | buy feed {'WHEAT': 1} |
| 4/04 | $584 → $584 | collect fertilizer 1 |
| 4/05 | $584 → $551 | buy feed {'WHEAT': 1} |
| 4/06 | $551 → $551 | collect fertilizer 1 |
| 4/08 | $551 → $551 | harvest {'WHEAT': 4} |
| 4/09 | $551 → $551 | plant {'WHEAT': 1} |
| 4/10 | $551 → $551 | collect fertilizer 1 |
| 4/13 | $551 → $551 | harvest {'WHEAT': 4} |
| 4/14 | $551 → $551 | plant {'WHEAT': 1} |
| 4/15 | $551 → $551 | harvest {'WHEAT': 4}; collect fertilizer 1 |
| 4/16 | $551 → $551 | plant {'WHEAT': 1}; harvest {'WHEAT': 4} |
| 4/18 | $551 → $551 | harvest {'WHEAT': 4} |
| 4/19 | $551 → $551 | plant {'WHEAT': 2}; collect fertilizer 1 |
| 5/00 | $551 → $745 | buy animal {'COW': 1}; buy seed {'STRAWBERRY': 4, 'WHEAT': 1}; sell 5 FERTILIZER for $466 @ [94, 94, 93, 93, 92]; sell 17 WHEAT for $542 @ [33, 33, 33, 33, 32, 32, 32, 32, 32, 32, 32, 31, 31, 31, 31, 31, 31]; hire 3 ($4.0) |
| 5/01 | $745 → $714 | buy feed {'WHEAT': 1} |
| 5/04 | $714 → $683 | buy feed {'WHEAT': 1} |
| 5/05 | $683 → $652 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 5/06 | $652 → $652 | plant {'STRAWBERRY': 1}; collect fertilizer 1 |
| 5/08 | $652 → $652 | build {'PASTURE': 1} |
| 5/09 | $652 → $621 | place animal {'COW': 1}; buy feed {'WHEAT': 1} |
| 5/10 | $621 → $621 | plant {'WHEAT': 1}; collect fertilizer 1 |
| 5/11 | $621 → $590 | buy feed {'WHEAT': 1} |
| 5/14 | $590 → $558 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 5/15 | $558 → $558 | collect fertilizer 1 |
| 5/18 | $558 → $526 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 1} |
| 5/21 | $526 → $526 | plant {'STRAWBERRY': 1} |
| 6/00 | $526 → $978 | sell 5 FERTILIZER for $456 @ [92, 92, 91, 91, 90]; hire 3 ($4.0) |
| 6/02 | $978 → $978 | harvest {'WOOL': 5} |
| 6/04 | $978 → $946 | harvest {'WOOL': 5}; buy feed {'WHEAT': 1} |
| 6/05 | $946 → $946 | collect fertilizer 1 |
| 6/06 | $946 → $913 | buy feed {'WHEAT': 1} |
| 6/07 | $913 → $913 | collect fertilizer 1 |
| 6/08 | $913 → $880 | buy feed {'WHEAT': 1} |
| 6/09 | $880 → $880 | harvest {'WOOL': 5}; collect fertilizer 1 |
| 6/11 | $880 → $847 | buy feed {'WHEAT': 1} |
| 6/12 | $847 → $814 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 6/13 | $814 → $814 | collect fertilizer 1 |
| 6/15 | $814 → $814 | harvest {'WOOL': 5} |
| 6/16 | $814 → $1,134 | sell 3 FERTILIZER for $269 @ [90, 90, 89]; sell 5 WOOL for $1051 @ [218, 215, 212, 206, 200]; buy land 1 ($1000.0) |
| 6/17 | $1,134 → $21 | buy animal {'COW': 2}; buy seed {'STRAWBERRY': 3, 'WHEAT': 1}; hire 1 ($3.0) |
| 6/18 | $21 → $21 | collect fertilizer 1 |
| 6/20 | $21 → $21 | plant {'STRAWBERRY': 1}; build {'PASTURE': 2} |
| 6/21 | $21 → $21 | place animal {'COW': 1} |
| 7/00 | $21 → $2,135 | buy animal {'COW': 2}; sell 3 FERTILIZER for $265 @ [89, 88, 88]; sell 15 WOOL for $2682 @ [199, 199, 197, 195, 193, 190, 187, 183, 179, 174, 169, 164, 158, 151, 144]; hire 7 ($33.0) |
| 7/01 | $2,135 → $1,001 | buy seed {'STRAWBERRY': 9, 'WHEAT': 3}; buy feed {'WHEAT': 6} |
| 7/03 | $1,001 → $967 | buy feed {'WHEAT': 1} |
| 7/04 | $967 → $932 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 7/05 | $932 → $897 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 7/06 | $897 → $897 | plant {'STRAWBERRY': 1}; collect fertilizer 1 |
| 7/07 | $897 → $862 | buy feed {'WHEAT': 1}; build {'PASTURE': 1} |
| 7/08 | $862 → $862 | plant {'STRAWBERRY': 1}; place animal {'COW': 1}; collect fertilizer 1 |
| 7/09 | $862 → $827 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 1} |
| 7/10 | $827 → $792 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 7/11 | $792 → $792 | plant {'STRAWBERRY': 1} |
| 7/12 | $792 → $792 | plant {'STRAWBERRY': 1}; build {'PASTURE': 1} |
| 7/13 | $792 → $792 | place animal {'COW': 1} |
| 7/14 | $792 → $757 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 1} |
| 7/15 | $757 → $722 | plant {'STRAWBERRY': 1, 'WHEAT': 1}; buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 7/16 | $722 → $722 | harvest {'WHEAT': 4} |
| 7/17 | $722 → $722 | plant {'WHEAT': 1}; collect fertilizer 1 |
| 7/18 | $722 → $722 | plant {'STRAWBERRY': 1} |
| 7/19 | $722 → $722 | place animal {'COW': 1} |
| 7/20 | $722 → $722 | plant {'WHEAT': 2} |
| 7/22 | $722 → $722 | plant {'STRAWBERRY': 1} |
| 8/00 | $722 → $549 | buy animal {'COW': 2}; buy seed {'WHEAT': 3}; sell 7 FERTILIZER for $605 @ [88, 87, 87, 86, 86, 86, 85]; sell 2 WHEAT for $72 @ [36, 36]; hire 6 ($20.0) |
| 8/01 | $549 → $227 | buy seed {'STRAWBERRY': 2, 'WHEAT': 5}; buy feed {'WHEAT': 2} |
| 8/03 | $227 → $155 | harvest {'MILK': 6}; buy feed {'WHEAT': 2} |
| 8/04 | $155 → $155 | collect fertilizer 2 |
| 8/05 | $155 → $119 | buy feed {'WHEAT': 1}; build {'PASTURE': 1} |
| 8/06 | $119 → $119 | place animal {'COW': 1}; collect fertilizer 1 |
| 8/07 | $119 → $47 | harvest {'WHEAT': 4}; buy feed {'WHEAT': 2} |
| 8/08 | $47 → $47 | plant {'WHEAT': 1}; collect fertilizer 2 |
| 8/10 | $47 → $47 | collect fertilizer 1 |
| 8/11 | $47 → $47 | build {'PASTURE': 1} |
| 8/12 | $47 → $47 | harvest {'WHEAT': 4}; place animal {'COW': 1}; collect fertilizer 1 |
| 8/13 | $47 → $47 | plant {'WHEAT': 1} |
| 8/14 | $47 → $47 | plant {'STRAWBERRY': 1} |
| 8/15 | $47 → $47 | collect fertilizer 1 |
| 8/16 | $47 → $47 | plant {'WHEAT': 1}; harvest {'WHEAT': 4} |
| 8/17 | $47 → $47 | plant {'STRAWBERRY': 1, 'WHEAT': 1}; harvest {'WHEAT': 4} |
| 8/18 | $47 → $47 | plant {'WHEAT': 1}; collect fertilizer 2 |
| 8/19 | $47 → $47 | plant {'WHEAT': 1} |
| 8/20 | $47 → $47 | plant {'WHEAT': 1} |
| 8/21 | $47 → $47 | harvest {'WHEAT': 4} |
| 8/22 | $47 → $47 | plant {'WHEAT': 1} |
| 9/00 | $47 → $2,672 | sell 10 FERTILIZER for $830 @ [85, 84, 84, 84, 83, 83, 82, 82, 82, 81]; sell 6 MILK for $1357 @ [229, 228, 227, 226, 224, 223]; sell 13 WHEAT for $471 @ [37, 37, 37, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36]; hire 7 ($33.0) |
| 9/01 | $2,672 → $2,662 | buy seed {'WHEAT': 1} |
| 9/02 | $2,662 → $2,662 | harvest {'WOOL': 4} |
| 9/03 | $2,662 → $2,626 | buy feed {'WHEAT': 1} |
| 9/04 | $2,626 → $2,518 | buy feed {'WHEAT': 3}; collect fertilizer 1 |
| 9/05 | $2,518 → $2,518 | collect fertilizer 3 |
| 9/07 | $2,518 → $2,482 | harvest {'WOOL': 4}; buy feed {'WHEAT': 1} |
| 9/08 | $2,482 → $2,410 | buy feed {'WHEAT': 2}; collect fertilizer 1 |
| 9/09 | $2,410 → $2,373 | buy feed {'WHEAT': 1}; collect fertilizer 2 |
| 9/10 | $2,373 → $2,373 | collect fertilizer 1 |
| 9/12 | $2,373 → $2,373 | harvest {'WOOL': 4} |
| 9/13 | $2,373 → $2,336 | buy feed {'WHEAT': 1} |
| 9/14 | $2,336 → $2,299 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 9/15 | $2,299 → $2,299 | collect fertilizer 1 |
| 9/17 | $2,299 → $2,299 | harvest {'WHEAT': 4} |
| 9/18 | $2,299 → $2,299 | plant {'WHEAT': 1}; harvest {'WOOL': 4} |
| 9/19 | $2,299 → $2,299 | collect fertilizer 1 |
| 9/21 | $2,299 → $2,299 | collect fertilizer 1 |
| 10/00 | $2,299 → $3,097 | sell 9 FERTILIZER for $720 @ [81, 81, 80, 80, 80, 80, 80, 79, 79]; sell 16 WOOL for $2111 @ [181, 177, 172, 167, 161, 154, 148, 141, 133, 125, 116, 107, 98, 88, 77, 66]; hire 7 ($33.0); buy land 1 ($2000.0) |
| 10/01 | $3,097 → $1,744 | buy seed {'MELON': 5}; hire 7 ($953.0) |
| 10/04 | $1,744 → $1,670 | buy feed {'WHEAT': 2} |
| 10/05 | $1,670 → $1,670 | collect fertilizer 2 |
| 10/06 | $1,670 → $1,670 | harvest {'MELON': 6}; collect fertilizer 2 |
| 10/07 | $1,670 → $1,670 | plant {'MELON': 1} |
| 10/08 | $1,670 → $1,670 | harvest {'MELON': 6} |
| 10/09 | $1,670 → $1,670 | plant {'MELON': 1}; harvest {'MELON': 6}; collect fertilizer 1 |
| 10/10 | $1,670 → $1,670 | plant {'MELON': 1}; collect fertilizer 3 |
| 10/11 | $1,670 → $1,670 | harvest {'MELON': 6} |
| 10/12 | $1,670 → $1,907 | plant {'MELON': 2}; harvest {'MELON': 6}; buy seed {'MELON': 9, 'STRAWBERRY': 6}; buy feed {'WHEAT': 1}; sell 6 MELON for $1594 @ [272, 270, 268, 266, 262, 256] |
| 10/13 | $1,907 → $1,670 | plant {'MELON': 2, 'STRAWBERRY': 3}; buy seed {'STRAWBERRY': 2}; buy feed {'WHEAT': 1} |
| 10/15 | $1,670 → $2,140 | plant {'MELON': 1}; buy seed {'STRAWBERRY': 8}; buy feed {'WHEAT': 6}; collect fertilizer 2; sell 6 MELON for $1498 @ [250, 250, 250, 250, 249, 249] |
| 10/16 | $2,140 → $2,140 | plant {'MELON': 1, 'STRAWBERRY': 3} |
| 10/17 | $2,140 → $3,625 | harvest {'MILK': 3}; sell 6 MELON for $1485 @ [248, 248, 248, 247, 247, 247] |
| 10/18 | $3,625 → $3,625 | plant {'MELON': 1}; collect fertilizer 2 |
| 10/19 | $3,625 → $3,549 | plant {'MELON': 1, 'STRAWBERRY': 2}; buy feed {'WHEAT': 2} |
| 10/20 | $3,549 → $4,995 | plant {'STRAWBERRY': 1}; sell 6 MELON for $1446 @ [244, 243, 242, 240, 239, 238] |
| 10/21 | $4,995 → $4,995 | plant {'MELON': 1} |
| 10/22 | $4,995 → $6,379 | plant {'STRAWBERRY': 2}; buy seed {'WHEAT': 1}; sell 6 MELON for $1394 @ [236, 235, 233, 232, 230, 228] |

Milestone funding:

- **land_1** at day 6, hour 16: bank $814 → $1,134; cumulative sales $4,414 {'FERTILIZER': 2649, 'WHEAT': 714, 'WOOL': 1051}; cumulative spending $6,280.
- **eight_cows** at day 8, hour 12: bank $47 → $47; cumulative sales $8,038 {'FERTILIZER': 3519, 'WHEAT': 786, 'WOOL': 3733}; cumulative spending $10,991.
- **land_2** at day 10, hour 0: bank $2,299 → $3,097; cumulative sales $13,527 {'FERTILIZER': 5069, 'MILK': 1357, 'WHEAT': 1257, 'WOOL': 5844}; cumulative spending $13,430.

## Ueddy — episode 91870920 seat 0

Opponent: Abracadabra; seed: 1182001269.

| Day/hour | Bank before → after | Successful economic events |
|---|---:|---|
| 0/00 | $3,000 → $5 | buy animal {'COW': 1, 'SHEEP': 4}; buy seed {'MELON': 5, 'WHEAT': 5}; buy feed {'WHEAT': 5}; hire 5 ($12.0) |
| 0/03 | $5 → $5 | build {'PASTURE': 1} |
| 0/04 | $5 → $5 | place animal {'SHEEP': 1}; build {'PASTURE': 1} |
| 0/05 | $5 → $5 | plant {'MELON': 1}; place animal {'COW': 1} |
| 0/07 | $5 → $5 | plant {'WHEAT': 1} |
| 0/08 | $5 → $5 | plant {'WHEAT': 1}; build {'PASTURE': 1} |
| 0/09 | $5 → $5 | place animal {'SHEEP': 1} |
| 0/10 | $5 → $5 | plant {'WHEAT': 1} |
| 0/12 | $5 → $5 | plant {'MELON': 1} |
| 0/13 | $5 → $5 | plant {'WHEAT': 1}; build {'PASTURE': 1} |
| 0/14 | $5 → $5 | place animal {'SHEEP': 1} |
| 0/15 | $5 → $5 | plant {'MELON': 1} |
| 0/16 | $5 → $5 | plant {'WHEAT': 1} |
| 0/19 | $5 → $5 | plant {'MELON': 1}; build {'PASTURE': 1} |
| 0/20 | $5 → $5 | place animal {'SHEEP': 1} |
| 0/22 | $5 → $5 | plant {'MELON': 1} |
| 1/00 | $5 → $4 | hire 1 ($1.0) |
| 1/02 | $4 → $4 | collect fertilizer 1 |
| 1/04 | $4 → $4 | collect fertilizer 1 |
| 1/07 | $4 → $4 | collect fertilizer 2 |
| 1/09 | $4 → $4 | collect fertilizer 1 |
| 2/00 | $4 → $322 | buy feed {'WHEAT': 6}; sell 5 FERTILIZER for $496 @ [100, 100, 99, 99, 98]; hire 2 ($2.0) |
| 2/03 | $322 → $292 | buy feed {'WHEAT': 1} |
| 2/04 | $292 → $292 | collect fertilizer 1 |
| 2/05 | $292 → $262 | buy feed {'WHEAT': 1} |
| 2/06 | $262 → $262 | collect fertilizer 1 |
| 2/09 | $262 → $232 | buy feed {'WHEAT': 1} |
| 2/10 | $232 → $232 | collect fertilizer 1 |
| 2/14 | $232 → $201 | buy feed {'WHEAT': 1} |
| 2/15 | $201 → $201 | collect fertilizer 1 |
| 2/18 | $201 → $170 | buy feed {'WHEAT': 1} |
| 2/19 | $170 → $170 | collect fertilizer 1 |
| 3/00 | $170 → $342 | buy seed {'STRAWBERRY': 3, 'WHEAT': 1}; sell 5 FERTILIZER for $486 @ [98, 98, 97, 97, 96]; hire 3 ($4.0) |
| 3/03 | $342 → $311 | buy feed {'WHEAT': 1} |
| 3/04 | $311 → $311 | collect fertilizer 1 |
| 3/05 | $311 → $280 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 1} |
| 3/06 | $280 → $280 | collect fertilizer 1 |
| 3/08 | $280 → $280 | plant {'STRAWBERRY': 1} |
| 3/09 | $280 → $249 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 3/10 | $249 → $249 | collect fertilizer 1 |
| 3/11 | $249 → $249 | plant {'STRAWBERRY': 1}; collect fertilizer 1 |
| 3/14 | $249 → $217 | plant {'WHEAT': 1}; buy feed {'WHEAT': 1} |
| 3/16 | $217 → $185 | buy feed {'WHEAT': 1} |
| 4/00 | $185 → $657 | sell 5 FERTILIZER for $476 @ [96, 96, 95, 95, 94]; hire 3 ($4.0) |
| 4/01 | $657 → $607 | buy seed {'WHEAT': 5} |
| 4/03 | $607 → $575 | buy feed {'WHEAT': 1} |
| 4/04 | $575 → $575 | collect fertilizer 1 |
| 4/05 | $575 → $543 | buy feed {'WHEAT': 1} |
| 4/06 | $543 → $543 | collect fertilizer 1 |
| 4/08 | $543 → $543 | harvest {'WHEAT': 4} |
| 4/09 | $543 → $543 | plant {'WHEAT': 1} |
| 4/10 | $543 → $543 | collect fertilizer 1 |
| 4/13 | $543 → $543 | harvest {'WHEAT': 4} |
| 4/14 | $543 → $543 | plant {'WHEAT': 1} |
| 4/15 | $543 → $543 | harvest {'WHEAT': 4}; collect fertilizer 1 |
| 4/16 | $543 → $543 | plant {'WHEAT': 1}; harvest {'WHEAT': 4} |
| 4/18 | $543 → $543 | harvest {'WHEAT': 4} |
| 4/19 | $543 → $543 | plant {'WHEAT': 2}; collect fertilizer 1 |
| 5/00 | $543 → $720 | buy animal {'COW': 1}; buy seed {'STRAWBERRY': 4, 'WHEAT': 1}; sell 5 FERTILIZER for $466 @ [94, 94, 93, 93, 92]; sell 17 WHEAT for $525 @ [32, 32, 32, 32, 32, 31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29]; hire 3 ($4.0) |
| 5/01 | $720 → $691 | buy feed {'WHEAT': 1} |
| 5/04 | $691 → $661 | buy feed {'WHEAT': 1} |
| 5/05 | $661 → $631 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 5/06 | $631 → $631 | plant {'STRAWBERRY': 1}; collect fertilizer 1 |
| 5/08 | $631 → $631 | build {'PASTURE': 1} |
| 5/09 | $631 → $601 | place animal {'COW': 1}; buy feed {'WHEAT': 1} |
| 5/10 | $601 → $601 | plant {'WHEAT': 1}; collect fertilizer 1 |
| 5/11 | $601 → $571 | buy feed {'WHEAT': 1} |
| 5/14 | $571 → $541 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 5/15 | $541 → $541 | collect fertilizer 1 |
| 5/17 | $541 → $541 | plant {'STRAWBERRY': 1} |
| 5/18 | $541 → $510 | buy feed {'WHEAT': 1} |
| 5/22 | $510 → $510 | plant {'STRAWBERRY': 1} |
| 6/00 | $510 → $962 | sell 5 FERTILIZER for $456 @ [92, 92, 91, 91, 90]; hire 3 ($4.0) |
| 6/02 | $962 → $962 | harvest {'WOOL': 5} |
| 6/04 | $962 → $931 | harvest {'WOOL': 5}; buy feed {'WHEAT': 1} |
| 6/05 | $931 → $931 | collect fertilizer 1 |
| 6/06 | $931 → $900 | buy feed {'WHEAT': 1} |
| 6/07 | $900 → $900 | collect fertilizer 1 |
| 6/08 | $900 → $869 | buy feed {'WHEAT': 1} |
| 6/09 | $869 → $869 | harvest {'WOOL': 5}; collect fertilizer 1 |
| 6/11 | $869 → $837 | buy feed {'WHEAT': 1} |
| 6/12 | $837 → $805 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 6/13 | $805 → $805 | collect fertilizer 1 |
| 6/15 | $805 → $805 | harvest {'WOOL': 5} |
| 6/16 | $805 → $1,125 | sell 3 FERTILIZER for $269 @ [90, 90, 89]; sell 5 WOOL for $1051 @ [218, 215, 212, 206, 200]; buy land 1 ($1000.0) |
| 6/17 | $1,125 → $12 | buy animal {'COW': 2}; buy seed {'STRAWBERRY': 3, 'WHEAT': 1}; hire 1 ($3.0) |
| 6/18 | $12 → $12 | collect fertilizer 1 |
| 6/20 | $12 → $12 | plant {'STRAWBERRY': 1}; build {'PASTURE': 2} |
| 6/21 | $12 → $12 | place animal {'COW': 1} |
| 6/23 | $12 → $12 | plant {'STRAWBERRY': 1} |
| 7/00 | $12 → $2,126 | buy animal {'COW': 2}; sell 3 FERTILIZER for $265 @ [89, 88, 88]; sell 15 WOOL for $2682 @ [199, 199, 197, 195, 193, 190, 187, 183, 179, 174, 169, 164, 158, 151, 144]; hire 7 ($33.0) |
| 7/01 | $2,126 → $1,001 | buy seed {'STRAWBERRY': 9, 'WHEAT': 3}; buy feed {'WHEAT': 6} |
| 7/03 | $1,001 → $968 | buy feed {'WHEAT': 1} |
| 7/04 | $968 → $935 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 7/05 | $935 → $902 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 7/06 | $902 → $902 | plant {'STRAWBERRY': 1}; collect fertilizer 1 |
| 7/07 | $902 → $869 | buy feed {'WHEAT': 1}; build {'PASTURE': 1} |
| 7/08 | $869 → $869 | plant {'STRAWBERRY': 1}; place animal {'COW': 1}; collect fertilizer 1 |
| 7/09 | $869 → $835 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 1} |
| 7/10 | $835 → $801 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 7/11 | $801 → $801 | plant {'STRAWBERRY': 1} |
| 7/12 | $801 → $801 | build {'PASTURE': 1} |
| 7/13 | $801 → $801 | plant {'STRAWBERRY': 1}; place animal {'COW': 1} |
| 7/14 | $801 → $767 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 1} |
| 7/15 | $767 → $733 | plant {'WHEAT': 1}; buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 7/16 | $733 → $733 | plant {'STRAWBERRY': 1}; harvest {'WHEAT': 4} |
| 7/17 | $733 → $733 | plant {'WHEAT': 1}; collect fertilizer 1 |
| 7/19 | $733 → $733 | plant {'STRAWBERRY': 1}; place animal {'COW': 1} |
| 7/20 | $733 → $733 | plant {'WHEAT': 2} |
| 8/00 | $733 → $556 | buy animal {'COW': 2}; buy seed {'WHEAT': 3}; sell 7 FERTILIZER for $605 @ [88, 87, 87, 86, 86, 86, 85]; sell 2 WHEAT for $68 @ [34, 34]; hire 6 ($20.0) |
| 8/01 | $556 → $238 | buy seed {'STRAWBERRY': 2, 'WHEAT': 5}; buy feed {'WHEAT': 2} |
| 8/03 | $238 → $170 | harvest {'MILK': 6}; buy feed {'WHEAT': 2} |
| 8/04 | $170 → $170 | collect fertilizer 2 |
| 8/05 | $170 → $135 | buy feed {'WHEAT': 1}; build {'PASTURE': 1} |
| 8/06 | $135 → $135 | place animal {'COW': 1}; collect fertilizer 1 |
| 8/07 | $135 → $65 | harvest {'WHEAT': 4}; buy feed {'WHEAT': 2} |
| 8/08 | $65 → $65 | plant {'WHEAT': 1}; collect fertilizer 2 |
| 8/10 | $65 → $65 | collect fertilizer 1 |
| 8/11 | $65 → $65 | build {'PASTURE': 1} |
| 8/12 | $65 → $65 | harvest {'WHEAT': 4}; place animal {'COW': 1}; collect fertilizer 1 |
| 8/13 | $65 → $65 | plant {'WHEAT': 1} |
| 8/14 | $65 → $65 | plant {'STRAWBERRY': 1} |
| 8/15 | $65 → $65 | collect fertilizer 1 |
| 8/16 | $65 → $65 | plant {'WHEAT': 1}; harvest {'WHEAT': 4} |
| 8/17 | $65 → $65 | plant {'STRAWBERRY': 1, 'WHEAT': 1}; harvest {'WHEAT': 4} |
| 8/18 | $65 → $65 | plant {'WHEAT': 1}; collect fertilizer 2 |
| 8/19 | $65 → $65 | plant {'WHEAT': 1} |
| 8/20 | $65 → $65 | plant {'WHEAT': 1} |
| 8/21 | $65 → $275 | harvest {'WHEAT': 4}; sell 6 WHEAT for $210 @ [35, 35, 35, 35, 35, 35] |
| 8/22 | $275 → $275 | plant {'WHEAT': 1} |
| 9/00 | $275 → $2,363 | sell 10 FERTILIZER for $830 @ [85, 84, 84, 84, 83, 83, 82, 82, 82, 81]; sell 6 MILK for $1050 @ [186, 183, 179, 175, 169, 158]; sell 7 WHEAT for $241 @ [35, 35, 35, 34, 34, 34, 34]; hire 7 ($33.0) |
| 9/01 | $2,363 → $2,353 | buy seed {'WHEAT': 1} |
| 9/02 | $2,353 → $2,353 | harvest {'WOOL': 4} |
| 9/03 | $2,353 → $2,319 | buy feed {'WHEAT': 1} |
| 9/04 | $2,319 → $2,217 | buy feed {'WHEAT': 3}; collect fertilizer 1 |
| 9/05 | $2,217 → $2,217 | collect fertilizer 3 |
| 9/07 | $2,217 → $2,183 | harvest {'WOOL': 4}; buy feed {'WHEAT': 1} |
| 9/08 | $2,183 → $2,114 | buy feed {'WHEAT': 2}; collect fertilizer 1 |
| 9/09 | $2,114 → $2,079 | buy feed {'WHEAT': 1}; collect fertilizer 2 |
| 9/10 | $2,079 → $2,079 | collect fertilizer 1 |
| 9/12 | $2,079 → $2,079 | harvest {'WOOL': 4} |
| 9/13 | $2,079 → $2,044 | buy feed {'WHEAT': 1} |
| 9/14 | $2,044 → $2,009 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 9/15 | $2,009 → $2,009 | collect fertilizer 1 |
| 9/17 | $2,009 → $2,009 | harvest {'WHEAT': 4} |
| 9/18 | $2,009 → $2,009 | plant {'WHEAT': 1}; harvest {'WOOL': 4} |
| 9/19 | $2,009 → $2,009 | collect fertilizer 1 |
| 9/21 | $2,009 → $2,009 | collect fertilizer 1 |
| 10/00 | $2,009 → $2,157 | sell 2 WHEAT for $70 @ [35, 35]; sell 16 WOOL for $2111 @ [181, 177, 172, 167, 161, 154, 148, 141, 133, 125, 116, 107, 98, 88, 77, 66]; hire 7 ($33.0); buy land 1 ($2000.0) |
| 10/01 | $2,157 → $644 | buy seed {'MELON': 7}; hire 7 ($953.0) |
| 10/05 | $644 → $644 | collect fertilizer 2 |
| 10/06 | $644 → $644 | harvest {'MELON': 6}; collect fertilizer 2 |
| 10/07 | $644 → $644 | plant {'MELON': 1} |
| 10/08 | $644 → $644 | harvest {'MELON': 6} |
| 10/09 | $644 → $644 | plant {'MELON': 1}; harvest {'MELON': 6}; collect fertilizer 1 |
| 10/10 | $644 → $644 | plant {'MELON': 1}; collect fertilizer 3 |
| 10/11 | $644 → $644 | harvest {'MELON': 6} |
| 10/12 | $644 → $843 | plant {'MELON': 2}; harvest {'MELON': 6}; buy seed {'MELON': 7, 'STRAWBERRY': 8}; buy feed {'WHEAT': 1}; sell 6 MELON for $1594 @ [272, 270, 268, 266, 262, 256] |
| 10/13 | $843 → $643 | plant {'MELON': 2, 'STRAWBERRY': 3}; buy seed {'STRAWBERRY': 2} |
| 10/15 | $643 → $1,218 | plant {'MELON': 1}; buy seed {'STRAWBERRY': 6}; buy feed {'WHEAT': 9}; collect fertilizer 2; sell 6 MELON for $1498 @ [250, 250, 250, 250, 249, 249] |
| 10/16 | $1,218 → $1,218 | plant {'MELON': 1, 'STRAWBERRY': 3} |
| 10/17 | $1,218 → $2,698 | harvest {'MILK': 3}; sell 6 MELON for $1480 @ [248, 248, 247, 246, 246, 245] |
| 10/18 | $2,698 → $2,698 | plant {'MELON': 1}; collect fertilizer 2 |
| 10/19 | $2,698 → $2,626 | plant {'MELON': 1, 'STRAWBERRY': 2}; buy feed {'WHEAT': 2} |
| 10/20 | $2,626 → $4,072 | plant {'STRAWBERRY': 1}; sell 6 MELON for $1446 @ [244, 243, 242, 240, 239, 238] |
| 10/21 | $4,072 → $4,072 | plant {'MELON': 1} |
| 10/22 | $4,072 → $5,456 | plant {'STRAWBERRY': 2}; buy seed {'WHEAT': 1}; sell 6 MELON for $1394 @ [236, 235, 233, 232, 230, 228] |
| 10/23 | $5,456 → $5,456 | plant {'WHEAT': 1} |

Milestone funding:

- **land_1** at day 6, hour 16: bank $805 → $1,125; cumulative sales $4,225 {'FERTILIZER': 2649, 'WHEAT': 525, 'WOOL': 1051}; cumulative spending $6,100.
- **eight_cows** at day 8, hour 12: bank $65 → $65; cumulative sales $7,845 {'FERTILIZER': 3519, 'WHEAT': 593, 'WOOL': 3733}; cumulative spending $10,780.
- **land_2** at day 10, hour 0: bank $2,009 → $2,157; cumulative sales $12,357 {'FERTILIZER': 4349, 'MILK': 1050, 'WHEAT': 1114, 'WOOL': 5844}; cumulative spending $13,200.

## Abracadabra — episode 91870920 seat 1

Opponent: Ueddy; seed: 1182001269.

| Day/hour | Bank before → after | Successful economic events |
|---|---:|---|
| 0/00 | $3,000 → $4 | buy animal {'COW': 1, 'SHEEP': 4}; buy seed {'MELON': 5, 'WHEAT': 5}; buy feed {'WHEAT': 5}; hire 4 ($7.0) |
| 0/03 | $4 → $4 | build {'PASTURE': 1} |
| 0/04 | $4 → $4 | place animal {'SHEEP': 1}; build {'PASTURE': 1} |
| 0/05 | $4 → $4 | plant {'MELON': 1}; place animal {'COW': 1} |
| 0/07 | $4 → $4 | plant {'WHEAT': 1} |
| 0/08 | $4 → $4 | plant {'WHEAT': 1}; build {'PASTURE': 1} |
| 0/09 | $4 → $4 | place animal {'SHEEP': 1} |
| 0/10 | $4 → $4 | plant {'WHEAT': 1} |
| 0/12 | $4 → $4 | plant {'MELON': 1} |
| 0/13 | $4 → $4 | plant {'WHEAT': 1}; build {'PASTURE': 1} |
| 0/14 | $4 → $4 | place animal {'SHEEP': 1} |
| 0/15 | $4 → $4 | plant {'MELON': 1} |
| 0/16 | $4 → $4 | plant {'WHEAT': 1} |
| 0/19 | $4 → $4 | plant {'MELON': 1}; build {'PASTURE': 1} |
| 0/20 | $4 → $4 | place animal {'SHEEP': 1} |
| 0/22 | $4 → $4 | plant {'MELON': 1} |
| 1/00 | $4 → $3 | hire 1 ($1.0) |
| 1/02 | $3 → $3 | collect fertilizer 1 |
| 1/04 | $3 → $3 | collect fertilizer 1 |
| 1/07 | $3 → $3 | collect fertilizer 2 |
| 1/09 | $3 → $3 | collect fertilizer 1 |
| 2/00 | $3 → $321 | buy feed {'WHEAT': 6}; sell 5 FERTILIZER for $496 @ [100, 100, 99, 99, 98]; hire 2 ($2.0) |
| 2/03 | $321 → $291 | buy feed {'WHEAT': 1} |
| 2/04 | $291 → $291 | collect fertilizer 1 |
| 2/05 | $291 → $261 | buy feed {'WHEAT': 1} |
| 2/06 | $261 → $261 | collect fertilizer 1 |
| 2/09 | $261 → $231 | buy feed {'WHEAT': 1} |
| 2/10 | $231 → $231 | collect fertilizer 1 |
| 2/14 | $231 → $200 | buy feed {'WHEAT': 1} |
| 2/15 | $200 → $200 | collect fertilizer 1 |
| 2/18 | $200 → $169 | buy feed {'WHEAT': 1} |
| 2/19 | $169 → $169 | collect fertilizer 1 |
| 3/00 | $169 → $341 | buy seed {'STRAWBERRY': 3, 'WHEAT': 1}; sell 5 FERTILIZER for $486 @ [98, 98, 97, 97, 96]; hire 3 ($4.0) |
| 3/03 | $341 → $310 | buy feed {'WHEAT': 1} |
| 3/04 | $310 → $310 | collect fertilizer 1 |
| 3/05 | $310 → $279 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 1} |
| 3/06 | $279 → $279 | collect fertilizer 1 |
| 3/08 | $279 → $279 | plant {'STRAWBERRY': 1} |
| 3/09 | $279 → $248 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 3/10 | $248 → $248 | collect fertilizer 1 |
| 3/11 | $248 → $248 | plant {'STRAWBERRY': 1}; collect fertilizer 1 |
| 3/14 | $248 → $216 | plant {'WHEAT': 1}; buy feed {'WHEAT': 1} |
| 3/16 | $216 → $184 | buy feed {'WHEAT': 1} |
| 4/00 | $184 → $656 | sell 5 FERTILIZER for $476 @ [96, 96, 95, 95, 94]; hire 3 ($4.0) |
| 4/01 | $656 → $606 | buy seed {'WHEAT': 5} |
| 4/03 | $606 → $574 | buy feed {'WHEAT': 1} |
| 4/04 | $574 → $574 | collect fertilizer 1 |
| 4/05 | $574 → $542 | buy feed {'WHEAT': 1} |
| 4/06 | $542 → $542 | collect fertilizer 1 |
| 4/08 | $542 → $542 | harvest {'WHEAT': 4} |
| 4/09 | $542 → $542 | plant {'WHEAT': 1} |
| 4/10 | $542 → $542 | collect fertilizer 1 |
| 4/13 | $542 → $542 | harvest {'WHEAT': 4} |
| 4/14 | $542 → $542 | plant {'WHEAT': 1} |
| 4/15 | $542 → $542 | harvest {'WHEAT': 4}; collect fertilizer 1 |
| 4/16 | $542 → $542 | plant {'WHEAT': 1}; harvest {'WHEAT': 4} |
| 4/18 | $542 → $542 | harvest {'WHEAT': 4} |
| 4/19 | $542 → $542 | plant {'WHEAT': 2}; collect fertilizer 1 |
| 5/00 | $542 → $719 | buy animal {'COW': 1}; buy seed {'STRAWBERRY': 4, 'WHEAT': 1}; sell 5 FERTILIZER for $466 @ [94, 94, 93, 93, 92]; sell 17 WHEAT for $525 @ [32, 32, 32, 32, 32, 31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29]; hire 3 ($4.0) |
| 5/01 | $719 → $690 | buy feed {'WHEAT': 1} |
| 5/04 | $690 → $660 | buy feed {'WHEAT': 1} |
| 5/05 | $660 → $630 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 5/06 | $630 → $630 | plant {'STRAWBERRY': 1}; collect fertilizer 1 |
| 5/08 | $630 → $630 | build {'PASTURE': 1} |
| 5/09 | $630 → $600 | place animal {'COW': 1}; buy feed {'WHEAT': 1} |
| 5/10 | $600 → $600 | plant {'WHEAT': 1}; collect fertilizer 1 |
| 5/11 | $600 → $570 | buy feed {'WHEAT': 1} |
| 5/14 | $570 → $540 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 5/15 | $540 → $540 | collect fertilizer 1 |
| 5/18 | $540 → $509 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 1} |
| 5/21 | $509 → $509 | plant {'STRAWBERRY': 1} |
| 6/00 | $509 → $961 | sell 5 FERTILIZER for $456 @ [92, 92, 91, 91, 90]; hire 3 ($4.0) |
| 6/02 | $961 → $961 | harvest {'WOOL': 5} |
| 6/04 | $961 → $930 | harvest {'WOOL': 5}; buy feed {'WHEAT': 1} |
| 6/05 | $930 → $930 | collect fertilizer 1 |
| 6/06 | $930 → $899 | buy feed {'WHEAT': 1} |
| 6/07 | $899 → $899 | collect fertilizer 1 |
| 6/08 | $899 → $868 | buy feed {'WHEAT': 1} |
| 6/09 | $868 → $868 | harvest {'WOOL': 5}; collect fertilizer 1 |
| 6/11 | $868 → $836 | buy feed {'WHEAT': 1} |
| 6/12 | $836 → $804 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 6/13 | $804 → $804 | collect fertilizer 1 |
| 6/15 | $804 → $804 | harvest {'WOOL': 5} |
| 6/16 | $804 → $1,124 | sell 3 FERTILIZER for $269 @ [90, 90, 89]; sell 5 WOOL for $1051 @ [218, 215, 212, 206, 200]; buy land 1 ($1000.0) |
| 6/17 | $1,124 → $11 | buy animal {'COW': 2}; buy seed {'STRAWBERRY': 3, 'WHEAT': 1}; hire 1 ($3.0) |
| 6/18 | $11 → $11 | collect fertilizer 1 |
| 6/20 | $11 → $11 | plant {'STRAWBERRY': 1}; build {'PASTURE': 2} |
| 6/21 | $11 → $11 | place animal {'COW': 1} |
| 6/23 | $11 → $11 | plant {'STRAWBERRY': 1} |
| 7/00 | $11 → $2,125 | buy animal {'COW': 2}; sell 3 FERTILIZER for $265 @ [89, 88, 88]; sell 15 WOOL for $2682 @ [199, 199, 197, 195, 193, 190, 187, 183, 179, 174, 169, 164, 158, 151, 144]; hire 7 ($33.0) |
| 7/01 | $2,125 → $1,000 | buy seed {'STRAWBERRY': 9, 'WHEAT': 3}; buy feed {'WHEAT': 6} |
| 7/03 | $1,000 → $967 | buy feed {'WHEAT': 1} |
| 7/04 | $967 → $934 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 7/05 | $934 → $901 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 7/06 | $901 → $901 | plant {'STRAWBERRY': 1}; collect fertilizer 1 |
| 7/07 | $901 → $868 | buy feed {'WHEAT': 1}; build {'PASTURE': 1} |
| 7/08 | $868 → $868 | plant {'STRAWBERRY': 1}; place animal {'COW': 1}; collect fertilizer 1 |
| 7/09 | $868 → $834 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 1} |
| 7/10 | $834 → $800 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 7/11 | $800 → $800 | plant {'STRAWBERRY': 1} |
| 7/12 | $800 → $800 | plant {'STRAWBERRY': 1}; build {'PASTURE': 1} |
| 7/13 | $800 → $800 | place animal {'COW': 1} |
| 7/14 | $800 → $766 | plant {'STRAWBERRY': 1}; buy feed {'WHEAT': 1} |
| 7/15 | $766 → $732 | plant {'STRAWBERRY': 1, 'WHEAT': 1}; buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 7/16 | $732 → $732 | harvest {'WHEAT': 4} |
| 7/17 | $732 → $732 | plant {'WHEAT': 1}; collect fertilizer 1 |
| 7/18 | $732 → $732 | plant {'STRAWBERRY': 1} |
| 7/19 | $732 → $732 | place animal {'COW': 1} |
| 7/20 | $732 → $732 | plant {'WHEAT': 2} |
| 7/22 | $732 → $732 | plant {'STRAWBERRY': 1} |
| 8/00 | $732 → $555 | buy animal {'COW': 2}; buy seed {'WHEAT': 3}; sell 7 FERTILIZER for $605 @ [88, 87, 87, 86, 86, 86, 85]; sell 2 WHEAT for $68 @ [34, 34]; hire 6 ($20.0) |
| 8/01 | $555 → $237 | buy seed {'STRAWBERRY': 2, 'WHEAT': 5}; buy feed {'WHEAT': 2} |
| 8/03 | $237 → $169 | harvest {'MILK': 6}; buy feed {'WHEAT': 2} |
| 8/04 | $169 → $169 | collect fertilizer 2 |
| 8/05 | $169 → $134 | buy feed {'WHEAT': 1}; build {'PASTURE': 1} |
| 8/06 | $134 → $134 | place animal {'COW': 1}; collect fertilizer 1 |
| 8/07 | $134 → $64 | harvest {'WHEAT': 4}; buy feed {'WHEAT': 2} |
| 8/08 | $64 → $64 | plant {'WHEAT': 1}; collect fertilizer 2 |
| 8/10 | $64 → $64 | collect fertilizer 1 |
| 8/11 | $64 → $64 | build {'PASTURE': 1} |
| 8/12 | $64 → $64 | harvest {'WHEAT': 4}; place animal {'COW': 1}; collect fertilizer 1 |
| 8/13 | $64 → $64 | plant {'WHEAT': 1} |
| 8/14 | $64 → $64 | plant {'STRAWBERRY': 1} |
| 8/15 | $64 → $64 | collect fertilizer 1 |
| 8/16 | $64 → $64 | plant {'WHEAT': 1}; harvest {'WHEAT': 4} |
| 8/17 | $64 → $64 | plant {'STRAWBERRY': 1, 'WHEAT': 1}; harvest {'WHEAT': 4} |
| 8/18 | $64 → $64 | plant {'WHEAT': 1}; collect fertilizer 2 |
| 8/19 | $64 → $64 | plant {'WHEAT': 1} |
| 8/20 | $64 → $64 | plant {'WHEAT': 1} |
| 8/21 | $64 → $64 | harvest {'WHEAT': 4} |
| 8/22 | $64 → $64 | plant {'WHEAT': 1} |
| 9/00 | $64 → $2,356 | sell 10 FERTILIZER for $830 @ [85, 84, 84, 84, 83, 83, 82, 82, 82, 81]; sell 6 MILK for $1050 @ [186, 183, 179, 175, 169, 158]; sell 13 WHEAT for $445 @ [35, 35, 35, 34, 34, 34, 34, 34, 34, 34, 34, 34, 34]; hire 7 ($33.0) |
| 9/01 | $2,356 → $2,346 | buy seed {'WHEAT': 1} |
| 9/02 | $2,346 → $2,346 | harvest {'WOOL': 4} |
| 9/03 | $2,346 → $2,312 | buy feed {'WHEAT': 1} |
| 9/04 | $2,312 → $2,210 | buy feed {'WHEAT': 3}; collect fertilizer 1 |
| 9/05 | $2,210 → $2,210 | collect fertilizer 3 |
| 9/07 | $2,210 → $2,176 | harvest {'WOOL': 4}; buy feed {'WHEAT': 1} |
| 9/08 | $2,176 → $2,107 | buy feed {'WHEAT': 2}; collect fertilizer 1 |
| 9/09 | $2,107 → $2,072 | buy feed {'WHEAT': 1}; collect fertilizer 2 |
| 9/10 | $2,072 → $2,072 | collect fertilizer 1 |
| 9/12 | $2,072 → $2,072 | harvest {'WOOL': 4} |
| 9/13 | $2,072 → $2,037 | buy feed {'WHEAT': 1} |
| 9/14 | $2,037 → $2,002 | buy feed {'WHEAT': 1}; collect fertilizer 1 |
| 9/15 | $2,002 → $2,002 | collect fertilizer 1 |
| 9/17 | $2,002 → $2,002 | harvest {'WHEAT': 4} |
| 9/18 | $2,002 → $2,002 | plant {'WHEAT': 1}; harvest {'WOOL': 4} |
| 9/19 | $2,002 → $2,002 | collect fertilizer 1 |
| 9/21 | $2,002 → $2,002 | collect fertilizer 1 |
| 10/00 | $2,002 → $2,150 | sell 2 WHEAT for $70 @ [35, 35]; sell 16 WOOL for $2111 @ [181, 177, 172, 167, 161, 154, 148, 141, 133, 125, 116, 107, 98, 88, 77, 66]; hire 7 ($33.0); buy land 1 ($2000.0) |
| 10/01 | $2,150 → $797 | buy seed {'MELON': 5}; hire 7 ($953.0) |
| 10/04 | $797 → $727 | buy feed {'WHEAT': 2} |
| 10/05 | $727 → $727 | collect fertilizer 2 |
| 10/06 | $727 → $727 | harvest {'MELON': 6}; collect fertilizer 2 |
| 10/07 | $727 → $727 | plant {'MELON': 1} |
| 10/08 | $727 → $727 | harvest {'MELON': 6} |
| 10/09 | $727 → $727 | plant {'MELON': 1}; harvest {'MELON': 6}; collect fertilizer 1 |
| 10/10 | $727 → $727 | plant {'MELON': 1}; collect fertilizer 3 |
| 10/11 | $727 → $727 | harvest {'MELON': 6} |
| 10/12 | $727 → $966 | plant {'MELON': 2}; harvest {'MELON': 6}; buy seed {'MELON': 9, 'STRAWBERRY': 6}; buy feed {'WHEAT': 1}; sell 6 MELON for $1594 @ [272, 270, 268, 266, 262, 256] |
| 10/13 | $966 → $731 | plant {'MELON': 2, 'STRAWBERRY': 3}; buy seed {'STRAWBERRY': 2}; buy feed {'WHEAT': 1} |
| 10/15 | $731 → $1,214 | plant {'MELON': 1}; buy seed {'STRAWBERRY': 8}; buy feed {'WHEAT': 6}; collect fertilizer 2; sell 6 MELON for $1498 @ [250, 250, 250, 250, 249, 249] |
| 10/16 | $1,214 → $1,214 | plant {'MELON': 1, 'STRAWBERRY': 3} |
| 10/17 | $1,214 → $2,694 | harvest {'MILK': 3}; sell 6 MELON for $1480 @ [248, 248, 247, 246, 246, 245] |
| 10/18 | $2,694 → $2,694 | plant {'MELON': 1}; collect fertilizer 2 |
| 10/19 | $2,694 → $2,622 | plant {'MELON': 1, 'STRAWBERRY': 2}; buy feed {'WHEAT': 2} |
| 10/20 | $2,622 → $4,068 | plant {'STRAWBERRY': 1}; sell 6 MELON for $1446 @ [244, 243, 242, 240, 239, 238] |
| 10/21 | $4,068 → $4,068 | plant {'MELON': 1} |
| 10/22 | $4,068 → $5,452 | plant {'STRAWBERRY': 2}; buy seed {'WHEAT': 1}; sell 6 MELON for $1394 @ [236, 235, 233, 232, 230, 228] |
| 10/23 | $5,452 → $5,452 | plant {'WHEAT': 1} |

Milestone funding:

- **land_1** at day 6, hour 16: bank $804 → $1,124; cumulative sales $4,225 {'FERTILIZER': 2649, 'WHEAT': 525, 'WOOL': 1051}; cumulative spending $6,101.
- **eight_cows** at day 8, hour 12: bank $64 → $64; cumulative sales $7,845 {'FERTILIZER': 3519, 'WHEAT': 593, 'WOOL': 3733}; cumulative spending $10,781.
- **land_2** at day 10, hour 0: bank $2,002 → $2,150; cumulative sales $12,351 {'FERTILIZER': 4349, 'MILK': 1050, 'WHEAT': 1108, 'WOOL': 5844}; cumulative spending $13,201.
