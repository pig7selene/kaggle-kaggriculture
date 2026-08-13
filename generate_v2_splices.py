"""Create a small evidence-backed set of coherent V2 phase replacements."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path

from generate_super_splices import _state_distance


ROOT = Path(__file__).resolve().parent
V1_BANK = ROOT / "experiments/super_replay_route_bank.json"
V2_BANK = ROOT / "experiments/v2_route_bank.json"
EXECUTOR = ROOT / "experiments/v2_route_executor.json"
INDEX = ROOT / "agents/super_replay_v2/index.json"
GRAPH = ROOT / "experiments/v2_phase_graph.json"
OUT = ROOT / "agents/super_replay_v2"
V1_ID = "super_raw_55459817"

SPECS = [
    # Full tails are controls: do coherent elite blocks outperform raw V1?
    ("v2_splice_jalkarna_p2_tail", "super_raw_55463387", 240, 719),
    ("v2_splice_jalkarna_p3_tail", "super_raw_55463387", 336, 719),
    ("v2_splice_jalkarna_p4_only", "super_raw_55463387", 336, 504),
    ("v2_splice_jalkarna_p3_p4", "super_raw_55463387", 240, 504),
    ("v2_splice_malelizar_p2_tail", "super_raw_55468815", 240, 719),
    ("v2_splice_malelizar_p3_p4", "super_raw_55468815", 240, 504),
    ("v2_splice_nazmus_p3_tail", "super_raw_55445174", 336, 719),
    ("v2_splice_nazmus_p4_only", "super_raw_55445174", 336, 504),
]


def main():
    v1 = next(row for row in json.loads(V1_BANK.read_text())["routes"] if row["route_id"] == V1_ID)
    v2 = {row["route_id"]: row for row in json.loads(V2_BANK.read_text())["routes"]}
    executor = json.loads(EXECUTOR.read_text())
    existing = {row["route_id"] for row in executor["routes"]}
    generated = []
    index = json.loads(INDEX.read_text())
    for name, donor_id, start, end in SPECS:
        donor = v2[donor_id]
        start_distance = _state_distance(v1["expected_state"][start], donor["expected_state"][start])
        end_distance = 0 if end == 719 else _state_distance(donor["expected_state"][end], v1["expected_state"][end])
        actions = deepcopy(v1["consensus_actions"])
        expected = deepcopy(v1["expected_state"])
        actions[start:end] = deepcopy(donor["consensus_actions"][start:end])
        expected[start:end] = deepcopy(donor["expected_state"][start:end])
        route_id = name.removeprefix("v2_")
        route = {
            "route_id": route_id, "family_id": "v2_evidence_backed_splice",
            "source_team": f"Ricardo->{donor['source_team']}->{('end' if end == 719 else 'Ricardo')}",
            "source_submission_id": donor["source_submission_id"],
            "source_episode_id": donor["source_episode_id"], "source_player": donor["source_player"],
            "source_seed": donor["source_seed"], "source_replay_path": donor["source_replay_path"],
            "consensus_actions": actions, "expected_state": expected,
            "milestones": v1.get("milestones", {}),
            "splice": {"donor_route_id": donor_id, "start": start, "end": end,
                       "entry_distance": start_distance, "exit_distance": end_distance},
            "action_sha256": hashlib.sha256(json.dumps(actions, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        }
        if route_id not in existing:
            executor["routes"].append(route); existing.add(route_id)
        path = OUT / f"{name}.py"
        path.write_text(
            '"""Evidence-backed coherent V2 phase splice + bounded K3 weed repair."""\n\n'
            'from runpy import run_path\n\n'
            f'agent = run_path("agents/super_replay_v2/backbone_common.py")["make_agent"]({route_id!r})\n'
        )
        index[name] = str(path.relative_to(ROOT)); generated.append(route)
    executor["route_count"] = len(executor["routes"])
    EXECUTOR.write_text(json.dumps(executor, separators=(",", ":")) + "\n")
    INDEX.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")
    GRAPH.write_text(json.dumps({
        "schema_version": 1, "baseline": V1_ID,
        "generation_rule": "Only stable routes supported by raw screen or phase economics; coherent P3/P4/tail blocks",
        "candidates": [{"route_id": row["route_id"], **row["splice"]} for row in generated],
    }, indent=2, sort_keys=True) + "\n")
    print(f"generated {len(generated)} phase candidates")
    for row in generated: print(row["route_id"], row["splice"])


if __name__ == "__main__":
    main()
