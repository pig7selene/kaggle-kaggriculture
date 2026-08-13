# V27 K3 standalone submission packaging

## Decision

**PASS.** `submission/main.py` is a standalone, behaviorally exact package of
the frozen `v27_victor_route_weed_guard_v1` agent. It is ready for **manual**
Kaggle submission. No Kaggle command, API, upload, or network submission action
was used.

## Frozen inputs and final hashes

| Artifact | SHA-256 |
|---|---|
| `agents/v27_replay_weed_guard.py`, expected | `dc0100ec0d029a6362f92618429b09d7baba5b8a5257f20a61385fe82afeda51` |
| frozen source, before packaging | `dc0100ec0d029a6362f92618429b09d7baba5b8a5257f20a61385fe82afeda51` |
| frozen source, after all validation | `dc0100ec0d029a6362f92618429b09d7baba5b8a5257f20a61385fe82afeda51` |
| final `submission/main.py` | `4ceb5a94a5c3c945853e09dd46a60267bec0948840be01363d49d8ac1b0cf521` |
| `experiments/current_best.json` | `53f6bf1ec81b07b44dc3cd51896037473481c8a9f68b361946c597b7de48c08e` |

The source hash matched before any package write and remained unchanged after
all testing.

## Packaging method

The source wrapper ultimately constructs stage K3 from
`agents/v27_backbone_common.py` and reads the selected Victor route from
`experiments/v27_route_manifest.json`. Packaging selected only the frozen
route `v27_family_3_victor_at_tufa_labs`, retained its 719 consensus actions
and 719 expected-state anchors, serialized the data as canonical compact JSON,
compressed it with zlib level 9, and embedded it as base64 in one Python file.
The standalone decodes this immutable route once at import.

The package copies the active K3 execution path exactly: worker matching,
legality checks, anchor measurements, worker-specific weed repair queues,
bounded retry/abort behavior, route action reconstruction, and telemetry. It
does not contain the stage-gated capital repair, hire heuristic, survival,
SELL scheduling, opponent-aware, or fallback behavior rejected in research.
The reproducible generator is `package_v27_submission.py`.

## Dependency audit

The final file exposes `agent(obs)` and imports only:

- Python standard library: `base64`, `copy`, `json`, `zlib`
- the installed competition environment module:
  `kaggle_environments.envs.kaggriculture.kaggriculture`

AST and source audits found zero project-local imports and zero runtime file,
manifest, replay, network, or working-directory access. Specifically, there
are no runtime `run_path`, `open`, `Path`, `requests`, `urllib`, or `socket`
calls. JSON serialization/deserialization of the decoded route also passed.

A clean-directory subprocess contained only `main.py`, imported it, and ran a
complete 720-state game against `starter`: 719 calls, statuses `DONE/DONE`,
final money 157,547 versus 3,465, and the same submission hash.

## Differential validation design

`validate_v27_submission.py` ran every condition independently for source and
standalone, from fresh agent instances and identical environment conditions.
For every one of the 719 requested actions it compared the complete farmer,
ordered hand, and ordered market action. It also compared observation-derived
trajectory hashes, day 4/6/8/10/11/15/20/25/29/final checkpoints, worker count
and positions, route anchor state, rematching and repair telemetry, final
money, livestock outcomes, and endgame inventory.

The completed suite contains 44 paired conditions / 88 differential games,
plus the clean standalone game:

| Group | Paired conditions | Exact pairs | Seats |
|---|---:|---:|---|
| known Victor source replay | 1 | 1 | source seat 0 |
| fresh seeds | 16 | 16 | 8 seeds, both seats |
| strong-opponent pool | 22 | 22 | 11 opponents, both seats |
| controlled weed cases | 5 | 5 | both represented |
| **Total** | **44** | **44** | **all required seats covered** |

Across 31,636 calls per implementation, action hashes, trajectory hashes,
telemetry hashes, checkpoints, and final money were identical for every pair.
There was no first mismatch to diagnose.

## Known Victor source replay

Episode 91876492, seed 507629282, Victor in seat 0 versus recorded Jince was
reproduced with the recorded town-shop schedule.

| Metric | Source | Standalone |
|---|---:|---:|
| requested actions matched | 719/719 | 719/719 |
| route components matched | 7,281/7,281 | 7,281/7,281 |
| final money | 94,884 | 94,884 |
| opponent money | 92,082 | 92,082 |
| final livestock | 9 cows, 5 sheep | 9 cows, 5 sheep |
| livestock escapes | 0 | 0 |
| stranded product value | 0 | 0 |
| repairs / rematches | 0 / 0 | 0 / 0 |

Farmer, ordered hand, and ordered market actions all had exact equality. The
action sequence SHA-256 was
`6b1f2cf16dbaffcacb735a2b55dc41c62fac169300cfef035e105737861e34ce`.

## Fresh-seed and both-seat equivalence

Fresh seeds 997300–997307 were tested in both seats against the frozen 803,
R3, and lifecycle agents. All 16/16 paired conditions matched exactly. Source
and standalone final money ranged from 93,373 to 158,499 and was identical in
every pair. All farmer/hand/market actions, trajectories, checkpoints, repair
state, and rematching state matched. There were zero runtime/schema failures,
escapes, or stranded-value games.

## Strong-opponent equivalence

The requested strong pool comprised the frozen 803 agent, R3, lifecycle, and
recorded routes for Filip, Amer, Yankang, Prashant, Jayveer, Pedro, Lucas, and
Alexander. Each was tested from both seats: 22/22 exact paired conditions.

| Opponent | Seat-0 money | Seat-1 money | Exact action/trajectory match |
|---|---:|---:|---|
| frozen 803 | 98,391 | 98,391 | yes / yes |
| R3 | 152,874 | 97,326 | yes / yes |
| lifecycle | 108,381 | 88,313 | yes / yes |
| Filip | 99,847 | 99,847 | yes / yes |
| Amer | 119,535 | 119,535 | yes / yes |
| Yankang | 100,786 | 100,786 | yes / yes |
| Prashant | 136,860 | 136,860 | yes / yes |
| Jayveer | 81,430 | 81,430 | yes / yes |
| Pedro | 77,342 | 77,342 | yes / yes |
| Lucas | 96,234 | 96,234 | yes / yes |
| Alexander | 96,812 | 96,812 | yes / yes |

These are equivalence results, not a new strategy benchmark: where a recorded
route is used, swapping seats preserves the scripted opponent action stream.

## Weed-repair fidelity

The controlled suite disabled random weed spawning and injected precise
blocking weeds into otherwise empty tiles. Source and standalone had identical
trigger, acting worker, DIG replacement, displaced-action queue, retry/abort,
backbone return, telemetry, actions, and final state in every case.

| Case | Injected block(s) | Result in both implementations |
|---|---|---|
| no weed | none | no repair; 7,281/7,281 route components |
| single farmer | step 4, farmer pasture | `DIG`, pasture retry, displaced animal service; success after 4 steps |
| single hand | step 5, hand 1 melon | `DIG`, melon retry, bounded queue; same step-13 abort |
| repeated/different workers | steps 5/134/247, units 1/2/8 | three identical repairs and three identical bounded aborts |
| critical segments | steps 164/247, units 0/8 | identical repair sequences around first/second land-route segments |

An abort here is the frozen K3 eight-step bound, not a packaging error. The
test intentionally demonstrates the same retry limit and return-to-backbone
behavior; no unplanned repair logic was added.

## Route fidelity and divergence causes

Aggregated over all 44 pairs:

| Implementation | Matched components | Requested components | Fidelity |
|---|---:|---:|---:|
| source | 320,219 | 320,364 | 99.954739% |
| standalone | 320,219 | 320,364 | 99.954739% |

The packaging delta is exactly **0.000000 percentage points**. The 145
component differences in each implementation are all explained by K3's
bounded weed-repair substitutions in natural or injected weed cases. The
known Victor source episode is 100%. The previously reported approximately
99.987% figure came from a different fresh-confirmation panel; this larger
suite deliberately contains adversarial weed injections and therefore has a
slightly lower aggregate fidelity. Worker rematch state was identical in all
pairs (zero rematches in this suite).

## Market and hand/hire preservation

Market actions are part of the exact action-sequence comparison, so SELL turn,
product, quantity, order position, all non-SELL orders, and complete market
ordering matched at every step in all 44 pairs. The frozen route market stream
hash was `e041245ef6eaa007a4f079dae725172559d44496e57a713ce850c1d68cf40522`.
No SELL reordering, future slot assignment, or dynamic hire logic exists in
the package.

The returned hand-action list matched the actual hired-hand count on all
31,636 standalone calls. Source and standalone market action equality also
proves the exact frozen HIRE stream was retained.

## Safety and endgame results

Across all 88 differential games:

- runtime exceptions: 0
- malformed/schema-invalid actions: 0
- environment terminal failures: 0
- route index errors: 0
- import/serialization failures: 0
- unsupported or project-local imports: 0
- unintended livestock escapes: 0
- meaningful stranded inventory games: 0; actual stranded product value was
  zero in every packaged validation game
- fallback activations: 0; K3 has no active fallback
- unexplained source/standalone divergence: 0

The semantic gate validates the exact Kaggriculture action envelope and the
installed environment's accepted command forms while preserving source syntax
verbatim (including the public route's accepted explicit item arguments).

## Runtime and file size

| Metric | Result |
|---|---:|
| file size | 61,605 bytes |
| import time, median / max | 13.904 ms / 21.735 ms |
| first call, median / max | 0.074 ms / 0.175 ms |
| typical call, median | 0.081 ms |
| maximum observed call | 137.496 ms |
| clean-process import | 7.631 ms |
| clean-process median / max call | 0.043 ms / 14.921 ms |

The isolated high maximum is a process-scheduling outlier under an eight-way
parallel suite; import and typical calls are orders of magnitude below a turn
budget. Route decompression occurs once at import, not per call.

## Final gate

| Gate | Result |
|---|---|
| Frozen source SHA correct | PASS |
| Source file unchanged | PASS |
| Standalone dependency test | PASS |
| 719/719 source replay equivalence | PASS |
| Source final-money equivalence | PASS |
| Fresh-seed equivalence | PASS |
| Both-seat equivalence | PASS |
| Strong-opponent equivalence | PASS |
| Weed-repair equivalence | PASS |
| Market-action equivalence | PASS |
| Route-fidelity equivalence | PASS |
| Runtime/schema safety | PASS |
| No meaningful stranded inventory | PASS |
| No serious livestock regression | PASS (zero losses) |

**`submission/main.py` is ready for manual Kaggle submission.**

The complete machine-readable per-condition evidence, action/trajectory/
telemetry hashes, checkpoints, repair traces, monies, audits, and timing is in
`experiments/v27_submission_packaging.json`.
