# SmallerShockV233HNonYarn0911 research candidate

## Decision

Lock `agents/smaller_market_shock_v233h_non_yarn_0911` as the current **local
research candidate** and package it for manual upload. Do **not** treat it as a
leaderboard improvement: it has never played an official episode, and its parent
scored below the frozen Terminal D online.

No Kaggle submission was made. `experiments/current_best.json` keeps Terminal D
as the highest verified leaderboard agent. Frozen Terminal D, FULL and 708-only
artifacts were asserted unchanged before and after every step.

## What changed versus V233H Safe

The parent is `SmallerShockV233HSafe` (submission 56183575, public score 2249.4,
109W/26L/1T over 136 public games, GSR 0.8051). The parent routes only 15
Yarn-related first-shop pairs to dedicated tapes and sends the other 49 ordered
pairs — roughly 77% of the natural shop distribution — to the inherited plan 0.
This candidate fills part of that gap.

| | Parent | Candidate |
| --- | ---: | ---: |
| Action tapes | 13 | 21 |
| Routed first-shop pairs | 15 | 57 |
| Non-Yarn pairs on plan-0 fallback | 49 | 7 |

Changes, all of them additive:

1. **42 non-Yarn routes added.** `SHOP_PLANS` is extended with 42 ordered
   non-Yarn first-shop pairs, routed to 8 complete continuations transplanted
   from the public Apache-2.0 notebook `yhay81, Shop Router 0911 Simple`. They
   become tape indices 13–20; tapes 0–12 stay byte-identical to the parent's.
2. **V233 sheep gate disabled on exactly those routes.** The six-sheep SE
   investment assumes the inherited tape's SE occupancy, which the donor
   continuations do not share, so `_v233_eligible` returns `False` on the 42
   enabled pairs.
3. **Hand-slot normalisation (V0911 layer).** Donor tapes carry a fixed number
   of hand actions; the appended layer truncates or pads them to the observed
   hired-hand count.
4. **NOTICE.txt extended** with the donor attribution Apache-2.0 requires.

Unchanged: `main.py`, `policy.py` and `settings.json` are byte-identical to the
parent, as are all 15 Yarn routes and every inherited repair, sale-reservation,
market-depth, liquidation and feed rule.

The build asserts opening-field equivalence between the donor and the parent for
all 144 steps before step 144, so the transplant cannot alter the pre-routing
opening.

## Which pairs were replaced, and why seven were not

The donor exposes 49 non-Yarn routes. Seven were excluded and keep the parent's
plan-0 behaviour:

`BRUNCH_SPOT+BRUNCH_SPOT`, `BRUNCH_SPOT+ICE_CREAM_SHOP`,
`FARMERS_MARKET+FARMERS_MARKET`, `FARMERS_MARKET+ICE_CREAM_SHOP`,
`ICE_CREAM_SHOP+FARMERS_MARKET`, `PET_CAFE+PIZZA_SHOP`,
`SMOOTHIE_SHOP+FARMERS_MARKET`

**Blacklist rule:** a pair is excluded if the transplanted continuation lost at
least one screen game against the V233H Safe baseline on that pair. Every one of
the seven has a recorded loss; the full evidence is in
`smaller_v233h_non_yarn_0911_lock_manifest.json` under `blacklist_provenance`.

| Excluded pair | Observed in | Losing margins |
| --- | --- | --- |
| SMOOTHIE_SHOP + FARMERS_MARKET | screen, full_screen | −7,745 ×2; −9,742 ×2 |
| PET_CAFE + PIZZA_SHOP | full_screen | −9,155 ×2 |
| ICE_CREAM_SHOP + FARMERS_MARKET | pair_screen | −8,348 ×2 |
| BRUNCH_SPOT + ICE_CREAM_SHOP | pair_screen | −7,753 ×2 |
| FARMERS_MARKET + ICE_CREAM_SHOP | full_screen | −1,256, −1,628 |
| BRUNCH_SPOT + BRUNCH_SPOT | full_screen, pair_screen | −179 ×2; −1,416, −1,072 |
| FARMERS_MARKET + FARMERS_MARKET | pair_screen | −1,115 |

There is no separate whitelist: the enabled set is the donor's 49 non-Yarn
routes minus these seven.

## Build generations

Three builds exist in the artifacts. Only the third is the locked candidate, and
the distinction matters when reading the panels.

| Gen | router SHA-256 | Routes | Hand normaliser | Panels |
| --- | --- | ---: | --- | --- |
| G1 | `ee54dedf…` | 49 | no | `screen` |
| G2 | `d468921b…` | 49 | yes | `full_screen`, `pair_screen` |
| **G3 (locked)** | `86893d15…` | 42 | yes | `whitelist_loss_screen`, `fixed_current_top_schedules`, `cross_lineage_gauntlet` |

G1 and G2 are **selection evidence**: they measured all 49 candidate routes and
produced the blacklist. G3 is **confirmation evidence** on the bytes that are
actually shipped.

## Validation

### Selection panels (superseded builds)

**Pair screen — 294 games, G2.** All 49 ordered non-Yarn pairs, 3 fresh
synthetic seeds per pair, both seats, against the V233H Safe baseline.

- 287W / 7L / 0T, GSR 0.9762
- mean advantage +1,724; median +1,602; worst −8,348
- pair classification: 45 positive, 4 negative
- 0 runtime errors, 0 agent errors, 0 semantic failures, 0 livestock escapes

**Full screen — 272 games, G2.** The realised shop schedules of all 136 public
episodes of submission 56183575, both seats.

- changed non-Yarn routes: 204W / 8L / 0T, mean +1,620, worst −9,742
- unchanged Yarn controls: 1W / 1L / 58T, mean 0 (the single −741 is a Yarn
  control, i.e. a seat/RNG effect, not attributable to this change)
- 0 runtime errors, 0 semantic failures, 0 livestock escapes

The earlier G1 `screen` recorded 12 candidate livestock escapes and 920 semantic
failures. Those belong to the build without hand normalisation and are the
reason that layer exists; G2 and G3 record zero of both.

### Confirmation panels (locked candidate, 292 games)

**Whitelist loss screen — 52 games.** The episodes the parent lost online,
candidate versus parent, both seats.

| Cell | Games | W-L-T | Mean advantage | Worst |
| --- | ---: | --- | ---: | ---: |
| Changed non-Yarn routes | 38 | 38-0-0 | **+1,782** | +475 |
| Unchanged Yarn controls | 14 | 0-0-14 | 0 | 0 |

The controls tie exactly, which is the intended behavioural proof: on Yarn
routes the candidate is the parent.

**Fixed current-top schedules — 90 games.** The exact eight-shop sequences of
the 15 current top-five official replays, forced locally, against
Top50RedBlackSafe, Top50HanserongSafe and EndToEndCohort, both seats.

- **90W / 0L / 0T**, GSR 1.000
- mean advantage +14,270; median +9,527; worst **+7**
- shop-schedule mismatches 0; runtime errors 0; semantic failures 0; livestock
  escapes 0 on both sides

**Cross-lineage gauntlet — 150 games.** The 15 official replay RNG seeds × 5
local opponent lineages × both seats.

- **148W / 2L / 0T**, GSR 0.9867
- mean advantage +35,464; median +37,387; p10 +6,047; worst **−689**
- mean money 111,340 versus 75,875
- 0 runtime errors, 0 agent errors, 0 semantic failures, 0 livestock escapes on
  either side

| Opponent | W-L | Mean advantage | Worst |
| --- | --- | ---: | ---: |
| Top50Portfolio | 28-2 | +14,119 | −689 |
| Top50HanserongSafe | 30-0 | +20,948 | +4,668 |
| EndToEndCohort | 30-0 | +16,323 | +164 |
| Cow6Capital | 30-0 | +62,965 | +42,430 |
| CropHeavy | 30-0 | +62,965 | +42,430 |

Seeds are official-replay anchors, not forced shop schedules: the local engine
shares a daily RNG between weed spawning and the shop draw, so changing farm
occupancy can change the realised sequence. Every realised sequence is retained
in the JSON.

### Episode 108109289 — the parent's only confirmed schedule loss

The parent lost this schedule (triple Ice Cream, `ICE_CREAM_SHOP ×3,
FARMERS_MARKET, SMOOTHIE_SHOP, PET_CAFE ×2, YARN_STORE`) by 109 coins against
RedBlack in both seats, and
`smaller_v233h_current_top_calibration_report.md` closed with the instruction to
fix it without regressing the other 14 schedules.

**Fixed.** On the exact schedule the candidate is now 6W / 0L across three
opponents and both seats, mean +6,325, median +844, worst +7. The other 14
schedules stay swept, so the overall panel is 90/90.

The margin is thin — the worst cell wins by 7 coins — so this is a repaired
edge, not a comfortable one.

### Aggregate error counts on the locked candidate

| | Count |
| --- | ---: |
| Runtime errors | 0 |
| Agent errors / exceptions | 0 |
| Semantic failures | 0 |
| Candidate livestock escapes | 0 |
| Opponent livestock escapes | 0 |
| Shop-schedule mismatches | 0 |

## Reproducibility

The candidate rebuilds from repository contents alone. `build_smaller_v233h_non_yarn_0911.py`
previously read its donor from `/private/tmp`, which macOS reaps; the donor now
lives at `agents/_donors/shop_router_0911_simple/main.py` with its provenance in
`agents/_donors/DONOR_MANIFEST.json`. A rebuild into a scratch directory
reproduced all five executable members byte-for-byte.

The two replay corpora the screens used (4.7 GB under `/private/tmp`) were
distilled by `build_replay_seed_manifests.py` into
`current_top_replay_schedule_manifest.json` (15 schedules) and
`v233h_online_replay_seed_manifest.json` (137 seeds), each cross-checked against
the original experiment artifacts with zero mismatches. The screens now read the
manifests and verify them against the corpora only when those still exist.

## Packaging

`package_smaller_v233h_safe.py --target non_yarn_0911` built
`submission/smaller_market_shock_v233h_non_yarn_0911.tar.gz`
(SHA-256 `baef9ecb866acb41a9bd069e813802a83353a7d772855a313082f4b605d43a03`,
226,007 bytes, seven root members, no extraneous entry).

The archive is deterministic — `mtime=0`, `uid=gid=0`, fixed mode, PAX format —
and a rebuild reproduced the same SHA-256. Every member hash equals the locked
research bytes.

Research-versus-packaged equivalence ran 4 conditions × 2 seats × 2 variants =
16 games: plan-trace, full-action, terminal-action, final-state and final-money
mismatches were all **0**, with 0 runtime errors, 0 agent errors, 0 semantic
failures and 0 livestock escapes. Frozen Terminal D, FULL and 708-only archives
hashed identically before and after. No Kaggle command was executed.

Receipt: `experiments/smaller_v233h_non_yarn_0911_packaging.json`.

## Known risks

1. **No online evidence whatsoever.** The candidate has never played an official
   episode. Its parent scored 2249.4, which is *below* the frozen Terminal D at
   2496.8. A local gain over that parent does not establish a leaderboard gain.
2. **Local panels are not leaderboard-calibrated.** `lb_calibration_report.md`
   (CASE D) found source lineage unknown for 99.05% of 529 official matches,
   and local GSR predicted the Terminal-D-to-front-run direction wrong
   (predicted +0.219/+0.250, actual −50.3/−34.9 points).
3. **The +1,782 figure is in-sample.** The blacklist was fitted on the same
   screens that measure the gain, so the changed-route mean is optimistic. No
   held-out pair set was reserved before fitting.
4. **The donor is a self-declared simplification.** Its author describes the
   notebook as a simplified release, not their scoring deployment, and
   `current_meta_frontier_recommendation.md` recorded very low field-action
   similarity between it and every sampled top-five submission.
5. **Thin margins on the repaired cell.** Episode 108109289 wins by as little as
   7 coins; ordinary RNG movement could flip it.
6. **Engine skew.** The local default is `kaggle-environments` 1.32.6 while
   official replays report 1.32.7.
7. **Structural ceiling unchanged.** This is still fixed-tape replay with
   bounded repairs. `current_meta_frontier_recommendation.md` concluded the
   current frontier is a production/economy generation — expansion timing,
   labour, shop-conditioned livestock mix — none of which this candidate
   touches.

## Why this is a candidate and not a proven improvement

Everything measured here is local self-play against a six-lineage opponent pool
that the calibration study already showed is unrepresentative of the official
population. The candidate is locked because it is reproducible, error-free and
beats its parent on every cell that its own selection procedure did not exclude
— not because there is evidence it scores higher on Kaggle. Confirming that
needs an actual submission and roughly 130 public episodes, and the decision to
spend a submission is deliberately left open.

## Artifacts

- Candidate: `agents/smaller_market_shock_v233h_non_yarn_0911`
- Lock: `experiments/smaller_v233h_non_yarn_0911_lock_manifest.json`
- Build receipt: `experiments/smaller_v233h_non_yarn_0911_build.json`
- Packaging receipt: `experiments/smaller_v233h_non_yarn_0911_packaging.json`
- Archive: `submission/smaller_market_shock_v233h_non_yarn_0911.tar.gz`
- Selection panels: `..._screen.json`, `..._full_screen.json`, `..._pair_screen.json`
- Confirmation panels: `..._whitelist_loss_screen.json`,
  `..._fixed_current_top_schedules.json`, `..._cross_lineage_gauntlet.json`
- Donor provenance: `agents/_donors/DONOR_MANIFEST.json`
- Parent online diagnosis: `experiments/smaller_v233h_online_submission.md`
- Parent calibration: `experiments/smaller_v233h_current_top_calibration_report.md`
