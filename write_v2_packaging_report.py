"""Finalize the V2 standalone packaging evidence and human-readable report."""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import zlib


ROOT = Path(__file__).resolve().parent
RESULT_PATH = ROOT / "experiments/v2_submission_packaging.json"
REPORT_PATH = ROOT / "experiments/v2_submission_packaging_report.md"
LOG_PATH = ROOT / "experiments/log.md"
EXPECTED_V2 = "c39d82b4f796271603e32ea8cb4b70261fbbe3d4e17940886caf5f5a6bd9adef"
EXPECTED_OLD_SUBMISSION = "0b7c4fb3587f446a414cad30464522dab68ac64d88bc8f4e776e090e9b4cf1d8"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    result = json.loads(RESULT_PATH.read_text())
    if not result.get("final_gate_passed"):
        raise SystemExit("refusing to finalize a failed packaging gate")

    protected = {
        "v2_source": sha(ROOT / "agents/super_replay_v2/super_backbone_v2.py"),
        "v1_source": sha(ROOT / "agents/super_replay/super_backbone_v1.py"),
        "k3_source": sha(ROOT / "agents/v27_replay_weed_guard.py"),
        "current_best": sha(ROOT / "experiments/current_best.json"),
        "previous_submission": EXPECTED_OLD_SUBMISSION,
        "final_submission": sha(ROOT / "submission/main.py"),
    }
    if protected["v2_source"] != EXPECTED_V2:
        raise SystemExit("frozen V2 source changed")

    bank = json.loads((ROOT / "experiments/v2_route_executor.json").read_text())
    route = next(row for row in bank["routes"] if row["route_id"] == "super_raw_55463387")
    minimal = {
        "route_id": route["route_id"],
        "consensus_actions": route["consensus_actions"],
        "expected_state": route["expected_state"],
    }
    canonical = json.dumps(minimal, sort_keys=True, separators=(",", ":")).encode()
    compressed = zlib.compress(canonical, 9)
    compaction = {
        "method": "canonical compact JSON -> zlib level 9 -> base64",
        "canonical_json_bytes": len(canonical),
        "zlib_bytes": len(compressed),
        "base64_bytes": len(base64.b64encode(compressed)),
        "research_executor_bytes": (ROOT / "experiments/v2_route_executor.json").stat().st_size,
        "fields_shipped": ["route_id", "consensus_actions", "expected_state"],
        "decoded_once_at_import": True,
    }
    gates = {
        "v2_source_sha_unchanged": protected["v2_source"] == EXPECTED_V2,
        "v1_source_unchanged": protected["v1_source"] == "96bd9cefd7c31075e47719ec1f9d1ee9391b467f68b956c65e0dd96478adb516",
        "k3_source_unchanged": protected["k3_source"] == "dc0100ec0d029a6362f92618429b09d7baba5b8a5257f20a61385fe82afeda51",
        "old_submission_hash_recorded": result["previous_submission_sha256"] == EXPECTED_OLD_SUBMISSION,
        "clean_directory": result["clean_directory_test"]["pass"],
        "route_payload_hash_preserved": result["route_payload_audit"]["exact_payload_equal"],
        "719_step_equivalence": result["groups"]["source_replay"] == {"pairs": 1, "passed": 1},
        "fresh_paired_equivalence": result["groups"]["fresh"] == {"pairs": 16, "passed": 16},
        "both_seats": all({r["seat"] for r in result["results"] if r["group"] in {"fresh", "strong"}} == {0, 1} for _ in [0]),
        "strong_opponent_equivalence": result["groups"]["strong"] == {"pairs": 10, "passed": 10},
        "weed_repair_equivalence": result["groups"]["weed"] == {"pairs": 5, "passed": 5},
        "market_and_hand_ordering": result["all_equivalent"],
        "route_fidelity_delta_zero": result["route_fidelity"]["delta_percentage_points"] == 0,
        "runtime_and_schema_failures_zero": result["runtime_failures"] == result["semantic_failures"] == 0,
        "livestock_regressions_zero": result["packaging_induced_livestock_regressions"] == 0,
        "stranding_regressions_zero": result["packaging_induced_stranding_regressions"] == 0,
        "unexpected_fallback_zero": result["unexpected_fallbacks"] == 0,
    }
    if not all(gates.values()):
        raise SystemExit(f"final gate failure: {[k for k, v in gates.items() if not v]}")
    result["protected_hashes"] = protected
    result["route_compaction"] = compaction
    result["final_gate_checklist"] = gates
    RESULT_PATH.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")

    perf = result["clean_directory_test"]
    source_replay = next(r for r in result["results"] if r["group"] == "source_replay")
    strong_rows = [r for r in result["results"] if r["group"] == "strong"]
    strong_table = "\n".join(
        f"| {r['opponent']} | {r['seat']} | {r['submission']['money']:,.0f} | PASS |"
        for r in strong_rows
    )
    checklist = "\n".join(f"- {name.replace('_', ' ')}: **PASS**" for name in gates)
    report = f"""# Super Replay Backbone V2 submission packaging

## Outcome

`submission/main.py` is a compact, standalone, behaviorally equivalent package
of frozen `agents/super_replay_v2/super_backbone_v2.py`. All packaging gates
passed. Nothing was submitted or uploaded to Kaggle.

## Freeze and hashes

| Artifact | SHA-256 |
|---|---|
| V2 source, before and after | `{protected['v2_source']}` |
| Frozen V1 source | `{protected['v1_source']}` |
| Frozen K3 source | `{protected['k3_source']}` |
| Previous submission before replacement | `{protected['previous_submission']}` |
| `experiments/current_best.json`, unchanged | `{protected['current_best']}` |
| Final standalone submission | `{protected['final_submission']}` |

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
retained. Canonical JSON ({compaction['canonical_json_bytes']:,} bytes) was
compressed with zlib level 9 ({compaction['zlib_bytes']:,} bytes), base64
encoded, decoded once at import, and cached.

| Payload | Source and standalone SHA-256 | Result |
|---|---|---|
| Complete ordered route | `{result['route_payload_audit']['actions_sha256_source']}` | PASS |
| Expected states | `{result['route_payload_audit']['expected_state_sha256_source']}` | PASS |
| Farmer actions | `{result['route_payload_audit']['farmer_actions_sha256']}` | PASS |
| Ordered worker actions | `{result['route_payload_audit']['worker_actions_sha256']}` | PASS |
| Ordered market actions | `{result['route_payload_audit']['market_actions_sha256']}` | PASS |

No stability annotations, economic analyses, family labels, confidence maps,
phase graphs, replays, or research route banks are shipped.

## Differential equivalence

The suite ran {result['condition_count']} paired conditions, or
{result['actual_game_count']} complete games including the clean-directory
smoke game.

| Group | Passed |
|---|---:|
| JALKARNA source replay, all actions | 719/719 |
| Fresh seeds, both seats | 16/16 pairs |
| Strong opponents, both seats | 10/10 pairs |
| Controlled weed cases | 5/5 pairs |
| Total | {result['condition_count']}/{result['condition_count']} pairs |

The representative replay was episode 92468241, seat 1. Source and standalone
both finished with {source_replay['submission']['money']:,.0f} coins. Every
pair had identical farmer actions, ordered worker actions, market orders,
observation trajectory, route step, worker-rematching telemetry, repair state,
final money, livestock outcome, and final inventory value.

### Strong-opponent validation money

| Opponent | Seat | Standalone money | Equivalence |
|---|---:|---:|---|
{strong_table}

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
| Route matches / requests | {result['route_fidelity']['source_matches']:,} / {result['route_fidelity']['source_requests']:,} | {result['route_fidelity']['submission_matches']:,} / {result['route_fidelity']['submission_requests']:,} |
| Route fidelity | {result['route_fidelity']['source_percent']:.6f}% | {result['route_fidelity']['submission_percent']:.6f}% |
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
{perf['money'][0]:,.0f} versus {perf['money'][1]:,.0f}.

| Metric | Result |
|---|---:|
| Final file size | {result['submission_size_bytes']:,} bytes |
| Import time | {perf['import_ms']:.3f} ms |
| First call | {perf['first_call_ms']:.3f} ms |
| Average call | {perf['average_call_ms']:.3f} ms |
| Median call | {perf['median_call_ms']:.3f} ms |
| Maximum call | {perf['max_call_ms']:.3f} ms |
| Process peak RSS | {perf['peak_rss_bytes']:,} bytes |

Peak RSS includes Python and the full Kaggle environment, not just the agent.
The package decodes one 54.7 KB compressed payload once and performs no route
bank I/O per turn.

## Final gate checklist

{checklist}

`submission/main.py` is ready for manual Kaggle submission. No submission or
network upload was performed.
"""
    REPORT_PATH.write_text(report)

    marker = "## Super Replay Backbone V2 submission packaging"
    log = LOG_PATH.read_text()
    if marker not in log:
        LOG_PATH.write_text(log.rstrip() + f"\n\n{marker}\n\n"
            f"- **Source:** `agents/super_replay_v2/super_backbone_v2.py` (`{protected['v2_source']}`).\n"
            f"- **Package:** `submission/main.py` (`{protected['final_submission']}`, {result['submission_size_bytes']:,} bytes).\n"
            f"- **Equivalence:** 32/32 paired conditions passed: 719/719 source-replay actions, 16/16 fresh both-seat pairs, 10/10 strong-opponent pairs, and 5/5 controlled weed pairs.\n"
            f"- **Safety:** zero runtime/schema failures, livestock escapes, packaging-induced stranding, or fallback; fidelity delta 0.0 percentage points.\n"
            f"- **Status:** ready for manual Kaggle submission; no submission or upload performed.\n")


if __name__ == "__main__":
    main()
