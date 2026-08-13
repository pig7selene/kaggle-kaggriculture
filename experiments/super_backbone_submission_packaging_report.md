# Super Replay Backbone submission packaging

## Outcome

`submission/main.py` is a standalone, behaviorally equivalent package of the
frozen `agents/super_replay/super_backbone_v1.py`. The final packaging gate
passed. Nothing was submitted or uploaded to Kaggle.

## Freeze and hashes

The promoted source matched the required SHA-256 before packaging and remained
byte-identical after validation.

| Artifact | SHA-256 |
|---|---|
| Promoted source, before and after | `96bd9cefd7c31075e47719ec1f9d1ee9391b467f68b956c65e0dd96478adb516` |
| Frozen K3 source | `dc0100ec0d029a6362f92618429b09d7baba5b8a5257f20a61385fe82afeda51` |
| Previous submission, before replacement | `4ceb5a94a5c3c945853e09dd46a60267bec0948840be01363d49d8ac1b0cf521` |
| `experiments/current_best.json`, unchanged | `a0cc2dc55ae26615772a658ce45ad7b31b67dc9278a18fd56fdd5f30d167a864` |
| Final standalone submission | `0b7c4fb3587f446a414cad30464522dab68ac64d88bc8f4e776e090e9b4cf1d8` |

## Dependency audit

The frozen dependency graph was:

1. `agents/super_replay/super_backbone_v1.py`
2. `agents/super_replay/super_backbone_common.py`
3. route `super_raw_55459817` in `experiments/super_replay_route_executor.json`
4. `make_v27_agent(stage=3)` in `agents/v27_backbone_common.py`
5. Python standard library and installed Kaggriculture game constants

The package retains only the Ricardo consensus actions, expected state anchors,
worker rematching, action formatting, telemetry, and bounded worker-specific K3
weed transaction repair. Capital repair, SELL reordering, hire heuristics,
animal overrides, opponent awareness, and fallback remain disabled.

Static inspection found no project-local imports, runtime file reads, network
access, route-bank access, or cwd dependency. Runtime imports are `base64`,
`copy`, `json`, `zlib`, and the installed
`kaggle_environments.envs.kaggriculture.kaggriculture` module.

## Route compaction and integrity

Only `route_id`, 719 `consensus_actions`, and 719 `expected_state` records were
retained. Canonical compact JSON (1,072,707 bytes) was compressed with zlib
level 9 and base64-encoded once as a static payload (73,048 bytes). It is
decoded once at module import and cached. The 340,599,232-byte research route
bank is not loaded or shipped.

| Payload | Frozen source | Standalone | Result |
|---|---|---|---|
| All route actions | `6fe9928c31162b6cf4da2ad7af2b8999e99174ae2a9c0e1da3ccbc20dbec4193` | same | PASS |
| Expected states | `ead2fee52b58fc34cb63b8ad9a9a1b5fbaab2294b9b259f8b9debf0d174fb9be` | same | PASS |
| Farmer actions | `ac6b32fb5de4a53a87a02556a619b30e732669a878059c2da6e85fe70ed04bc6` | same embedded payload | PASS |
| Ordered worker actions | `0c909024798ec35ae0d8f5aa46fb9c52b173ed3e894406a127062d3574145341` | same embedded payload | PASS |
| Ordered market actions | `a9d13fd34a3c7a20c82939d3d103e7de4a5292f3d11532f6e6b62a581a1dc9f6` | same embedded payload | PASS |

## Equivalence validation

Forty paired conditions ran the frozen source and standalone separately under
identical seed, opponent, seat, shop schedule, and controlled injections. Every
pair completed 719 agent calls. Including the clean-directory game, validation
executed 81 full 720-step episodes.

| Gate | Result |
|---|---:|
| Ricardo episode 92368798, all requested actions | 719/719 exact |
| Fresh paired games, both seats | 16/16 passed |
| Strong-opponent paired games, both seats | 18/18 passed |
| Controlled weed cases | 5/5 passed |
| All paired conditions | 40/40 passed |

The strong pool included K3, frozen 803, R3, lifecycle, Family 2, Ricardo raw,
and three replay-derived family traces. Exact action equality covers farmer
actions, ordered hand actions, SELL and non-SELL market timing/quantity/order,
and hand schema alignment. Final money, observation trajectories, route index,
repair activations, worker rematching telemetry, livestock outcomes, and final
inventory value also matched in every pair.

## Weed repair exactness

The no-weed control produced no repair. The single-farmer and single-hand cases
each produced one identical repair. The repeated-worker case produced three
identical worker-specific repairs, and the economic-sequence case produced two
identical repairs near land-related route events. For all cases, DIG
substitution, retry queue, displaced-action replay, bounded duration, worker
identity, and return to the Ricardo route matched source behavior exactly; no
cross-worker mismatch occurred.

## Safety and route fidelity

| Metric | Source | Standalone |
|---|---:|---:|
| Route matches / requests | 295,124 / 295,272 | 295,124 / 295,272 |
| Route fidelity | 99.9498767% | 99.9498767% |
| Fidelity delta | — | 0.0 percentage points |
| Runtime failures | 0 | 0 |
| Semantic/schema failures | 0 | 0 |
| Livestock escapes | 0 | 0 |
| Meaningful stranded-inventory games | 0 | 0 |
| Unexpected fallback activations | 0 | 0 |

All route divergences in both implementations were identical and attributable
only to the intentionally retained bounded weed transaction repair.

## Clean-directory and performance audit

A temporary directory containing only `main.py` completed a 720-step game
against `starter` with both statuses `DONE`, 719 calls, and final money
144,942 versus 3,483. No repository file was present or accessed.

| Metric | Result |
|---|---:|
| Final file size | 91,596 bytes |
| Clean import time | 10.562 ms |
| Clean first-call latency | 0.060 ms |
| Clean average per-turn latency | 0.046 ms |
| Clean median per-turn latency | 0.042 ms |
| Clean maximum per-turn latency | 0.741 ms |
| Clean process peak RSS | 259,112,960 bytes |

Peak RSS includes the Python interpreter and Kaggle environment/game instance,
not only the agent payload. Across the 40 differential package runs, median
import time was 14.377 ms and the median per-game average call latency was
0.092 ms. The standalone file is approximately 0.027% of the 340.6 MB research
route bank.

## Final gate checklist

- Promoted source SHA unchanged: PASS
- Standalone clean-directory execution: PASS
- Exact route payload hashes and 719 steps: PASS
- 719-step Ricardo action equivalence: PASS
- Fresh paired and both-seat equivalence: PASS
- Strong-opponent equivalence: PASS
- Weed repair, market order, and hand order equivalence: PASS
- Route-fidelity delta 0.0 percentage points: PASS
- Runtime/schema failures: 0, PASS
- Livestock regressions/losses: 0, PASS
- Meaningful stranded-inventory regressions/games: 0, PASS
- Unexpected fallback: 0, PASS

The package is ready for manual Kaggle submission. No submission or network
upload was performed.
