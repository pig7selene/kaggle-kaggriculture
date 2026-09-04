# Pre-opening owner capacity audit

Date: 2026-09-02

This offline audit reads the frozen Top-50 route bank only.  It does
not run a simulator and does not alter any strategy or submission.

## Route-level capacity

| route | team | first land | max hands d2 | max hands d6 | max hands d10 | seed+hire slots (d0–10) | hire slots | PASS market turns |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| super_family_01_medoid | 张广麒 | 150 | 4 | 8 | 11 | 90 | 91 | 22 |
| super_family_02_medoid | Ryo Hasegawa | 120 | 3 | 7 | 12 | 56 | 56 | 9 |
| super_family_03_medoid | Subramanya N | 150 | 5 | 6 | 12 | 87 | 88 | 28 |
| super_family_04_medoid | tetsuya | 168 | 7 | 7 | 12 | 46 | 47 | 40 |
| super_family_05_medoid | Crop Dusta | 121 | 4 | 8 | 12 | 95 | 97 | 2 |
| super_raw_55908608 | Alex Paul | 150 | 4 | 8 | 11 | 112 | 113 | 62 |
| super_raw_55886665 | Hanserong | 150 | 4 | 8 | 11 | 88 | 88 | 48 |
| super_raw_55899537 | cygn | 150 | 4 | 8 | 11 | 106 | 108 | 61 |
| super_raw_55909034 | Michael Shihong Zhang | 150 | 4 | 8 | 11 | 112 | 113 | 65 |
| super_raw_55909139 | gogogo | 150 | 4 | 8 | 11 | 92 | 93 | 22 |
| super_raw_55906837 | rian | 150 | 4 | 8 | 11 | 114 | 115 | 66 |
| super_raw_55879161 | Ryo Takaki | 150 | 4 | 8 | 11 | 113 | 114 | 67 |
| super_raw_55890191 | redblackbst | 150 | 4 | 8 | 11 | 110 | 111 | 63 |
| super_raw_55885045 | Kaito Fukami | 150 | 4 | 8 | 11 | 112 | 113 | 65 |
| super_raw_55904387 | Chiranjieev | 150 | 4 | 8 | 11 | 112 | 113 | 64 |
| super_raw_55908027 | GIN | 150 | 4 | 8 | 11 | 92 | 93 | 22 |
| super_raw_55859516 | Dmitry Larko | 150 | 4 | 8 | 11 | 106 | 108 | 52 |
| super_raw_55905597 | boatlee | 150 | 4 | 8 | 11 | 92 | 93 | 22 |
| super_raw_55892033 | Mc10nys0n | 150 | 4 | 8 | 11 | 88 | 88 | 48 |
| super_raw_55871126 | One-For-All | 150 | 4 | 8 | 11 | 112 | 113 | 64 |
| super_raw_55884271 | Borrun | 150 | 4 | 8 | 11 | 109 | 110 | 62 |
| super_raw_55885628 | Ueddy | 150 | 4 | 8 | 11 | 109 | 110 | 61 |
| super_raw_55889058 | cmasch | 150 | 4 | 8 | 11 | 92 | 93 | 22 |

## Interpretation

The route bank shows a recurring structural constraint: the initial NW
quadrant is effectively full by day 2, so a pre-opening crop owner must
reserve a future-quadrant tile before first land.  An additional hand
also needs a daily market slot; a turn with ten existing orders cannot
fund it without replacing a route purchase or hire.  PASS counts are
only a necessary condition, not proof of safe execution, because the
route's crop/animal obligations can still occupy those units on later
turns.

The next complete-owner experiment should therefore be restricted to a
route/day window that has both a reserved future tile and recurring
seed-plus-hire slots.  If no route provides that window through the
entire lifecycle, adding a cohort requires a coherent route rewrite
rather than an overlay.

## Reproducibility

- `experiments/preopening_owner_capacity_audit.json`
- `analyze_preopening_owner_capacity.py`
