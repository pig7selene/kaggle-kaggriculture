# Top-10 public strategy synthesis

This report summarizes the already-downloaded V3 Top-10 corpus; it does not use replay identity or future state as a runtime feature.

Corpus: 10 selected complete routes, 3 structural families, 82 deduplicated development appearances, 126 valid unique replay IDs.

## Consensus

| pattern | count / range |
| --- | --- |
| first extra quadrant | mode 160 (range [144, 160]) |
| second extra quadrant | mode 240 (range [217, 264]) |
| peak hands | mode 14 |
| mixed cow + sheep | 10/10 |
| eight or more cows | 9/10 |
| melon wave (10+) | 10/10 |
| strawberry wave (25+) | 10/10 |

## Route comparison

| rank | player | family | land 1/2 | max hands | max cows/sheep | max productive | class |
| ---: | --- | --- | --- | ---: | --- | ---: | --- |
| 1 | カワシギ | v3_family_02 | 148/264 | 12 | 10/4 | 74 | strongly_adaptive |
| 2 | researchstudio.site | v3_family_03 | 144/217 | 13 | 5/6 | 71 | strongly_adaptive |
| 3 | JALKARNA GAUTAM | v3_family_01 | 160/240 | 14 | 8/4 | 74 | fixed_bounded_repair |
| 4 | Yusuke Hayashi | v3_family_01 | 160/240 | 14 | 8/4 | 74 | fixed_bounded_repair |
| 5 | jasonstillchasin | v3_family_01 | 160/240 | 14 | 8/4 | 74 | fixed |
| 6 | MD. Nazmus Sakib Anik | v3_family_02 | 148/264 | 12 | 10/4 | 75 | fixed |
| 7 | MalelizarazoP | v3_family_01 | 160/240 | 14 | 8/4 | 74 | fixed_bounded_repair |
| 8 | Furious Monk | v3_family_01 | 160/240 | 14 | 8/4 | 74 | fixed |
| 9 | Suda | v3_family_01 | 160/240 | 14 | 8/4 | 74 | fixed_bounded_repair |
| 10 | Mohamed abdelrazik | v3_family_01 | 160/240 | 14 | 8/4 | 74 | fixed_bounded_repair |

## What this means for the current best

Current Top-50 parents use land [150] → [265], peak cows [7, 8, 9], sheep [4, 5, 6], and peak hands [12].

The most defensible missing complete package is the stable JALKARNA-like route (`v3_raw_55463387`): it shares the three-quadrant/melon/strawberry skeleton, has a distinct 160/240 capital calendar, and was previously safety-clean. The rank-1 and rank-2 routes are genuinely adaptive, but their raw transfers were already shown to be unsafe or economically negative; they remain evidence about conditional behavior, not parents to splice.

## Adjustment used

A candidate adds only `v3_raw_55463387` as a fourth complete parent and selects it at step 1 when the opponent's visible opening state is the exact low-bank/four-hand signature of the JALKARNA family. All other states follow the frozen selector. No mid-episode route splice is performed.
