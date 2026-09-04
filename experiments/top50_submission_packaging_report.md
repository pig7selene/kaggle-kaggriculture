# Top-50 Observable Portfolio submission packaging

## Outcome

**READY for manual Kaggle submission.** The locked research strategy was
mechanically converted into one standalone `submission/main.py`. No strategy
logic, route, selector condition, repair, order, or fallback was changed.
Nothing was submitted or uploaded.

## Frozen source and package

| Artifact | Raw SHA-256 | LF-normalized SHA-256 | Bytes |
|---|---|---|---:|
| `agents/top50_distilled/top50_observable_portfolio.py` | `f9ca672848ccffdfe56888d99bcdf5a9d7644062b9eec0cf0cdea13574931233` | `f9ca672848ccffdfe56888d99bcdf5a9d7644062b9eec0cf0cdea13574931233` | 1,906 |
| Previous V2 `submission/main.py` | `a4f753d46a95e8d972098504f4930165e7e66f8ce292092e9ab090e4741310c3` | `a4f753d46a95e8d972098504f4930165e7e66f8ce292092e9ab090e4741310c3` | 91,462 |
| New `submission/main.py` | `789bb9bbd5122eb4891983e776a13777328e3e87736cbbc0b4bc86d13fc33f9b` | `789bb9bbd5122eb4891983e776a13777328e3e87736cbbc0b4bc86d13fc33f9b` | 272,360 |

The historical V2 deployment remains reproducible from its frozen V2 source
and `package_v2_submission.py`; its pre-replacement hashes are recorded in the
packaging manifest.

## Standalone audit

- Runtime imports: Python standard-library `base64`, `copy`, `json`, `zlib`,
  plus the competition's installed Kaggriculture constants.
- Repository-local imports: **0**.
- Runtime file reads: **0**.
- Network access: **0**.
- Absolute/local paths or external payload references: **0**.
- Clean directory containing only `main.py`: **PASS**, 719 calls and 720 steps.
- Same imported module across sequential seat-0 then seat-1 games: **PASS**;
  action hashes and terminal states matched fresh imports exactly.

## Selector and parent integrity

Selector agreement was **110/110 public-state cases (100%)**, covering every
threshold boundary and all three choices. Full-game parent usage was Dmitry 12,
Hanserong 2, and redblack 2.

| Parent | Route actions SHA-256 | Expected-state SHA-256 | Steps | Result |
|---|---|---|---:|---|
| Dmitry | `754939475e323d591989ba507675db8722764312ee36d61e6db4ddf8b68001fd` | `b92048cc9281a9aa699d52321843c38e33afeba2ca5905f04d3a5ae7f8673cad` | 719 | exact |
| Hanserong | `383e80ba4b554e4d844f4967fb701182725ae0efd427d504fb28388b82944192` | `8894aa722a3c5cee975452ae15fb1447424fd2ddc511ff2cbdccf8c676f0b1e7` | 719 | exact |
| redblack | `be7d9e537db1e764cdc0e2906b1d3d7204f818356a332ac66fd1dec8fb85a2ec` | `0261451a76800eef0163fc994c001d865eea63ccb988c5766d85dc68a780c9ad` | 719 | exact |

All three safety policies and payloads matched the research parents exactly.
Feature leakage audit passed: the selector uses only current public opponent
money and current public opponent hand count at step 1.

## Action-for-action equivalence

Sixteen full conditions used eight fresh seeds, both seats, and these opponents:

- V2
- K3
- Nazmus
- rank-1 adaptive
- ResearchStudio adaptive
- V1
- portfolio mirror
- Top-50 family-03 medoid

Results:

| Gate | Result |
|---|---:|
| Complete games | 16/16 |
| Actions | 11,504/11,504 identical |
| Per-game action count | 719/719 |
| Final-money delta | 0 in every game |
| Final-advantage delta | 0 in every game |
| Land/hands/animals/inventory/terminal state | exact in every game |

## Deployment safety and performance

| Check | Result |
|---|---:|
| Runtime failures | 0 |
| Semantic failures | 0 |
| Actual livestock escapes | 0 |
| Meaningful stranded inventory (>500 coins) | 0 |
| Unexpected fallback | 0 |
| Mean call time | 0.818 ms |
| P95 call time | 1.415 ms |
| Maximum observed call time | 261.309 ms |
| Median import time | 26.233 ms |

The isolated clean-directory game was faster: 0.755 ms mean, 1.285 ms P95,
and 24.581 ms maximum. The larger validation maximum occurred under concurrent
validator load, not repeated route decoding.

## Small V2 sanity panel

Eight fresh games, four seeds and both seats: **8/0/0**, average money
**112,003**, average advantage **+9,356**. This is a deployment sanity result,
not a new strategy benchmark.

Machine-readable result: `experiments/top50_submission_package.json`.

No Kaggle submission, upload, remote modification, or Git push was performed.
