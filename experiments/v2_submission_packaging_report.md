# Super Replay Backbone V2 submission packaging

## Outcome

`submission/main.py` is a compact, standalone, behaviorally equivalent package
of frozen `agents/super_replay_v2/super_backbone_v2.py`. All packaging gates
passed. Nothing was submitted or uploaded to Kaggle.

## Freeze and hashes

| Artifact | SHA-256 |
|---|---|
| V2 source, before and after | `c39d82b4f796271603e32ea8cb4b70261fbbe3d4e17940886caf5f5a6bd9adef` |
| Frozen V1 source | `96bd9cefd7c31075e47719ec1f9d1ee9391b467f68b956c65e0dd96478adb516` |
| Frozen K3 source | `dc0100ec0d029a6362f92618429b09d7baba5b8a5257f20a61385fe82afeda51` |
| Previous submission before replacement | `0b7c4fb3587f446a414cad30464522dab68ac64d88bc8f4e776e090e9b4cf1d8` |
| `experiments/current_best.json`, unchanged | `759560406c002798aeeb5a6c3e6f8f56c33bc5de3a9bce4ec29c6a01998b9136` |
| Final standalone submission | `a4f753d46a95e8d972098504f4930165e7e66f8ce292092e9ab090e4741310c3` |

## Dependency audit

The frozen execution graph was:

1. `agents/super_replay_v2/super_backbone_v2.py`
2. `agents/super_replay_v2/backbone_common.py`
3. route `super_raw_55463387` in `experiments/v2_route_executor.json`
4. `make_v27_agent(stage=3)` in `agents/v27_backbone_common.py`
5. standard library plus installed Kaggriculture constants

Only the deterministic JALKARNA route, expected worker positions, worker
rematching, telemetry, schema alignment, and bounded K3 worker-specific weed
transaction repair execute at stage 3. Capital repair, adaptive hiring,
livestock overrides, SELL reordering, opponent logic, and fallback are inactive
and were not bundled. Static audit found no project-local imports, runtime file
reads, network access, route-bank access, or cwd dependency.

## Route compaction and integrity

Only `route_id`, 719 ordered actions, and 719 expected-state records were
retained. Canonical JSON (1,069,263 bytes) was
compressed with zlib level 9 (54,688 bytes), base64
encoded, decoded once at import, and cached.

| Payload | Source and standalone SHA-256 | Result |
|---|---|---|
| Complete ordered route | `9438f4a024ce5e219f08bb5ee22a6cf1df43d3d55fed9606f0e78f57fb479a28` | PASS |
| Expected states | `00402cd1c747a54d67c0d2335e0ab510e997055dce1747e30657f42383b95a6f` | PASS |
| Farmer actions | `ac6b32fb5de4a53a87a02556a619b30e732669a878059c2da6e85fe70ed04bc6` | PASS |
| Ordered worker actions | `43549466d1cef212a4bffbf05196543cce7d9ded89f326d2156bfa2ac9fb1d72` | PASS |
| Ordered market actions | `5cbb78b7a731af303154371cf0a47a246aa218efe2ddcd1009d0464bcd696a08` | PASS |

No stability annotations, economic analyses, family labels, confidence maps,
phase graphs, replays, or research route banks are shipped.

## Differential equivalence

The suite ran 32 paired conditions, or
65 complete games including the clean-directory
smoke game.

| Group | Passed |
|---|---:|
| JALKARNA source replay, all actions | 719/719 |
| Fresh seeds, both seats | 16/16 pairs |
| Strong opponents, both seats | 10/10 pairs |
| Controlled weed cases | 5/5 pairs |
| Total | 32/32 pairs |

The representative replay was episode 92468241, seat 1. Source and standalone
both finished with 82,372 coins. Every
pair had identical farmer actions, ordered worker actions, market orders,
observation trajectory, route step, worker-rematching telemetry, repair state,
final money, livestock outcome, and final inventory value.

### Strong-opponent validation money

| Opponent | Seat | Standalone money | Equivalence |
|---|---:|---:|---|
| V1 | 0 | 91,616 | PASS |
| V1 | 1 | 92,563 | PASS |
| K3 | 0 | 85,617 | PASS |
| K3 | 1 | 85,617 | PASS |
| JALKARNA_raw | 0 | 53,434 | PASS |
| JALKARNA_raw | 1 | 53,434 | PASS |
| Nazmus_raw | 0 | 51,618 | PASS |
| Nazmus_raw | 1 | 52,206 | PASS |
| adaptive_rank1 | 0 | 96,457 | PASS |
| adaptive_rank1 | 1 | 92,909 | PASS |

The pool included V1, K3, JALKARNA raw, Nazmus raw, and a state-dependent
rank-one replay route. These are equivalence checks, not new strategy results.

## Weed repair exactness

No-weed, single-farmer, single-hand, repeated-worker, and important-route
cases were tested. Across all cases, source and standalone had identical DIG
substitution, affected identity, retry queue, displaced actions, eight-turn
horizon, day-boundary abort/success behavior, worker rematching, and return to
the route. No cross-worker contamination occurred.

## Safety and fidelity

| Metric | Source | Standalone |
|---|---:|---:|
| Route matches / requests | 235,789 / 235,914 | 235,789 / 235,914 |
| Route fidelity | 99.947015% | 99.947015% |
| Fidelity delta | — | 0.0 percentage points |
| Runtime failures | 0 | 0 |
| Schema/command failures | 0 | 0 |
| Livestock escapes | 0 | 0 |
| Meaningful stranded-inventory games | 0 | 0 |
| Unexpected fallback | 0 | 0 |

All route divergences were identical and caused only by the intentionally
retained K3 weed repair. Market actions and worker ordering were exact in every
pair.

## Clean-directory and performance

A temporary directory containing only `main.py` completed a 720-step game
against `starter`: 719 calls, both agents `DONE`, final money
131,274 versus 3,498.

| Metric | Result |
|---|---:|
| Final file size | 91,462 bytes |
| Import time | 12.716 ms |
| First call | 0.061 ms |
| Average call | 0.075 ms |
| Median call | 0.067 ms |
| Maximum call | 1.200 ms |
| Process peak RSS | 268,976,128 bytes |

Peak RSS includes Python and the full Kaggle environment, not just the agent.
The package decodes one 54.7 KB compressed payload once and performs no route
bank I/O per turn.

## Final gate checklist

- v2 source sha unchanged: **PASS**
- v1 source unchanged: **PASS**
- k3 source unchanged: **PASS**
- old submission hash recorded: **PASS**
- clean directory: **PASS**
- route payload hash preserved: **PASS**
- 719 step equivalence: **PASS**
- fresh paired equivalence: **PASS**
- both seats: **PASS**
- strong opponent equivalence: **PASS**
- weed repair equivalence: **PASS**
- market and hand ordering: **PASS**
- route fidelity delta zero: **PASS**
- runtime and schema failures zero: **PASS**
- livestock regressions zero: **PASS**
- stranding regressions zero: **PASS**
- unexpected fallback zero: **PASS**

`submission/main.py` is ready for manual Kaggle submission. No submission or
network upload was performed.
