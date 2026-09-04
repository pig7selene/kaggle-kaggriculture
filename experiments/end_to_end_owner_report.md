# End-to-end route/state owner — bounded lifecycle test

Date: 2026-09-02

## Scope and frozen state

The validated research best remained
`agents/top50_distilled/top50_observable_portfolio.py` (SHA-256
`f9ca672848ccffdfe56888d99bcdf5a9d7644062b9eec0cf0cdea13574931233`).
`submission/main.py` was not touched.  This stage created only research
agents and harnesses; no Kaggle submission was made.

The purpose was to test the remaining architectural hypothesis from the
coherent-owner proof: a lifecycle cannot be safely borrowed after day 10, so
worker/crop capacity must be reserved before the opening route commits.  The
owner therefore creates a reservation ledger at turn 0 and carries it through
the complete route.

## Candidates

| artifact | behavior |
|---|---|
| `agents/autonomous_next/end_to_end_owner_v1.py` | Control owner. Calls the frozen portfolio and records a day-0 farmer/WHEAT reservation plus per-unit commitment ledger. It never consumes the reservation. |
| `agents/autonomous_next/end_to_end_owner_crop_v1.py` | Same owner, with one capital-gated WHEAT lifecycle after step 240. It adds one seed only when a market slot and cash buffer exist, uses the reserved farmer only on base `PASS` turns, waters/harvests, and sells the realized units. No land, animals, fertilizer, or other economic decisions are changed. |

The lifecycle is deliberately bounded to one tile and closes admission at
step 432. It rejects a turn whenever the reserved farmer is unavailable or
the base route has no other executable commitment action to carry the visible
animal/crop obligations. The tile transition ledger also recognizes a harvest
performed by the inherited route, preventing inventory from being silently
lost.

## Exact control equivalence

`run_end_to_end_owner.py` compared the control owner and the frozen portfolio
from turn 0 through turn 718 (719 requested actions), with fresh module
instances and both seats:

| seed | seat | actions compared | mismatches | frozen money | owner money | schema failures |
|---:|---:|---:|---:|---:|---:|---:|
| 57400 | 0 | 719 | 0 | 83,195 | 83,195 | 0 |
| 57400 | 1 | 719 | 0 | 83,195 | 83,195 | 0 |
| 57401 | 0 | 719 | 0 | 40,919 | 40,919 | 0 |
| 57401 | 1 | 719 | 0 | 40,919 | 40,919 | 0 |

All episodes completed 720 simulator steps. This establishes that the
reservation ledger itself does not perturb the route or its hidden state.

## Controlled lifecycle screen

Development seeds 57400–57403, both seats, paired against the frozen portfolio
(8 conditions):

| metric | result |
|---|---:|
| runtime failures | 0 |
| schema/semantic failures | 0 |
| animal-loss conditions | 0 |
| admissions / plantings / harvested / sell requests | 8 / 8 / 8 / 8 |
| mean own-money delta | **+25.75** |
| median own-money delta | +24.5 |
| P10 own-money delta | +23.0 |
| mean advantage delta | +33.75 |
| terminal inventory value | 12.0 in both candidate and control (inherited route value) |

Held-out seeds 57500–57501, both seats (4 conditions):

| metric | result |
|---|---:|
| runtime / schema failures | 0 / 0 |
| animal-loss conditions | 0 |
| admissions / plantings / harvested / sell requests | 4 / 4 / 4 / 4 |
| mean own-money delta | **+29.5** |
| median own-money delta | +29.5 |
| P10 own-money delta | +29.0 |
| mean advantage delta | +34.5 |

The absolute gain is the expected small wheat margin (one low-yield crop
cycle), not a recovery of the missing premium-crop headroom. Final inventory
value was identical to control (12 coins), so the candidate introduced no
incremental stranding.

## Hard-opponent confirmation

Seeds 57510–57511, both seats, paired candidate/control against six fixed hard
opponents (24 games): tetsuya, Crop Dusta, OceanMix, livestock/crop,
land-expander, and high-labor.

| opponent | games | mean own-money Δ | median Δ | P10 Δ | mean advantage Δ | candidate W/L/T | runtime / schema / animal loss |
|---|---:|---:|---:|---:|---:|---:|---|
| tetsuya | 4 | 0.0 | 0.0 | 0.0 | 0.0 | 4/0/0 | 0 / 0 / 0 |
| Crop Dusta | 4 | 0.0 | 0.0 | 0.0 | +2.0 | 4/0/0 | 0 / 0 / 0 |
| OceanMix | 4 | +20.0 | +20.0 | +19.0 | +28.0 | 2/2/0 | 0 / 0 / 0 |
| livestock/crop | 4 | −2.5 | −2.5 | −3.0 | −3.0 | 4/0/0 | 0 / 0 / 0 |
| land-expander | 4 | −1.0 | −1.0 | −2.0 | −1.0 | 4/0/0 | 0 / 0 / 0 |
| high-labor | 4 | −0.5 | −0.5 | −1.0 | +1.5 | 4/0/0 | 0 / 0 / 0 |
| **overall** | **24** | **+2.67** | **0.0** | **−2.0** | **+4.58** | **22/2/0** | **0 / 0 / 0** |

The 24-game panel is a safety/interaction check, not a promotion-sized
benchmark. The lifecycle remained fully realized in all rows and did not
create a catastrophic matchup, but its economic effect was effectively zero
against most opponents.

## Causal interpretation

The experiment answers two questions separately:

1. **Ownership:** planning a reservation at turn 0 is safe. A complete owner
   can preserve the frozen route exactly; action/state equivalence and all
   schema checks passed.
2. **Headroom:** one reserved wheat cycle is not the missing breakthrough. It
   adds roughly 25–30 coins, with a median held-out gain of 29.5 and a small
   negative tail in the hard panel. This is orders of magnitude below the
   observed 30k–40k crop-revenue gap.

The earlier checkpoint overlay produced zero admissions because it tried to
borrow workers after commitments were already fixed. This owner admits at
least one cycle on every tested seed because the reservation is declared
before day 10, yet the resulting value is still tiny. Therefore the remaining
bottleneck is not simply “one extra idle worker”; it is a larger, coherent
pre-opening crop cohort whose capital, tile ownership, watering lanes, harvest
timing, and sale exposure are planned together.

## Decision

Do **not** promote `end_to_end_owner_crop_v1.py`. It is safe and slightly
positive, but the gain is not material and the hard-opponent tail includes
small regressions. Keep the frozen portfolio and `submission/main.py`
unchanged.

The next justified experiment is a single complete pre-day-10 cohort owned by
the route from turn 0 (not an overlay): reserve a dedicated worker lane and a
small set of tiles, model the crop's full water/harvest path, and include the
capital and market effect in the same economic program. It should first be
tested as a state-equivalence/control pair, then on unseen seeds; do not tune
the current one-tile gate or launch a broad parameter sweep.

## Reproducibility artifacts

- `experiments/end_to_end_owner_screen_v1.json`
- `experiments/end_to_end_owner_heldout.json`
- `experiments/end_to_end_owner_league.json`
- `run_end_to_end_owner.py`
- `run_end_to_end_owner_league.py`

