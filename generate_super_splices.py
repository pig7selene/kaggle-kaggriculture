"""Generate only synchronization-compatible coherent route phase splices."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BANK_PATH = ROOT / "experiments/super_replay_route_bank.json"
INDEX_PATH = ROOT / "agents/super_replay/index.json"
OUT = ROOT / "agents/super_replay"
GRAPH_OUT = ROOT / "experiments/super_replay_phase_graph.json"

SPLICES = {
    "p1": 160,
    "p2": 240,
    "mid": 336,
    "late": 504,
    "end": 648,
}


def _state_distance(left, right):
    score = 0.0
    score += abs(left["hand_count"] - right["hand_count"]) * 3
    score += abs(len(left["quadrants"]) - len(right["quadrants"])) * 20
    for animal in ("COW", "SHEEP", "GOOSE"):
        score += abs(left["animals"].get(animal, 0) - right["animals"].get(animal, 0)) * 5
    for crop in ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"):
        score += abs(left["crops"].get(crop, 0) - right["crops"].get(crop, 0))
    score += abs(float(left["money"]) - float(right["money"])) / 1000
    score += sum(abs(int(left.get("seeds", {}).get(item, 0)) - int(right.get("seeds", {}).get(item, 0))) for item in ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")) * .5
    # Worker spatial compatibility is essential for a route replay.
    score += abs(len(left.get("hands", [])) - len(right.get("hands", []))) * 5
    score += sum(
        abs(a[0] - b[0]) + abs(a[1] - b[1])
        for a, b in zip(left.get("hands", []), right.get("hands", []))
    ) * .25
    return score


def _fingerprint(actions):
    return hashlib.sha256(json.dumps(actions, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main():
    bank = json.loads(BANK_PATH.read_text())
    routes = {row["route_id"]: row for row in bank["routes"]}
    # Use successful Generation-0 routes only, leaving unseen ranks untouched.
    results = json.loads((ROOT / "experiments/super_replay_generation_results.json").read_text())
    ranked = sorted(
        (
            (Path(path).stem, row) for path, row in results["summary"].items()
            if "agents/super_replay/" in path and row["average_advantage"] > 12000
            and row["livestock_losses"] == 0 and row["meaningful_stranding_games"] == 0
        ),
        key=lambda value: value[1]["average_advantage"], reverse=True,
    )
    name_to_route = {route_id.lower(): route for route_id, route in routes.items()}
    parents = []
    for stem, _ in ranked[:10]:
        if stem in name_to_route:
            parents.append(name_to_route[stem])
    victor = json.loads((ROOT / "experiments/v27_route_manifest.json").read_text())
    victor = next(row for row in victor["routes"] if row["route_id"] == "v27_family_3_victor_at_tufa_labs")
    victor = {**victor, "route_id": "K3_victor"}
    parents.append(victor)

    graph_edges = []
    for left in parents:
        for right in parents:
            if left["route_id"] == right["route_id"]:
                continue
            for phase, step in SPLICES.items():
                distance = _state_distance(left["expected_state"][step], right["expected_state"][step])
                graph_edges.append({
                    "from": left["route_id"], "to": right["route_id"], "step": step,
                    "phase": phase, "compatibility_distance": distance,
                    "compatible": distance <= 8,
                })
    compatible = [row for row in graph_edges if row["compatible"]]
    compatible.sort(key=lambda row: row["compatibility_distance"])
    candidates = []
    seen = set()
    # Single coherent tail substitutions. Limit to a disciplined Generation 1.
    for edge in compatible:
        left, right, step = routes.get(edge["from"], victor if edge["from"] == "K3_victor" else None), routes.get(edge["to"], victor if edge["to"] == "K3_victor" else None), edge["step"]
        actions = deepcopy(left.get("consensus_actions", left["actions"])[:step]) + deepcopy(right.get("consensus_actions", right["actions"])[step:])
        fingerprint = _fingerprint(actions)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        route_id = f"super_splice_{len(candidates)+1:03d}_{edge['phase']}"
        candidates.append({
            "route_id": route_id, "family_id": "super_splice_generation_1",
            "source_submission_id": left.get("source_submission_id"),
            "source_team": f"{left['route_id']}->{right['route_id']}",
            "source_episode_id": left.get("source_episode_id"), "source_player": left.get("source_player"),
            "source_seed": left.get("source_seed"), "source_replay_path": left.get("source_replay_path"),
            "source_final_money": left.get("source_final_money"), "source_opponent": left.get("source_opponent"),
            "actions": actions, "consensus_actions": actions,
            "expected_state": deepcopy(left["expected_state"][:step]) + deepcopy(right["expected_state"][step:]),
            "milestones": left.get("milestones", {}),
            "splice": edge,
        })
        if len(candidates) >= 80:
            break
    bank["routes"].extend(candidates)
    bank["route_count"] = len(bank["routes"])
    BANK_PATH.write_text(json.dumps(bank, indent=2, ensure_ascii=False) + "\n")
    index = json.loads(INDEX_PATH.read_text())
    for route in candidates:
        path = OUT / f"{route['route_id']}.py"
        path.write_text(
            '"""Compatible elite route phase splice + frozen K3 weed repair."""\n\n'
            'from runpy import run_path\n\n'
            f'agent = run_path("agents/super_replay/super_backbone_common.py")["make_super_agent"]({route["route_id"]!r})\n'
        )
        index[route["route_id"]] = str(path.relative_to(ROOT))
    INDEX_PATH.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")
    GRAPH_OUT.write_text(json.dumps({
        "schema_version": 1, "nodes": [row["route_id"] for row in parents],
        "edges": graph_edges, "compatible_edges": len(compatible),
        "generated_candidates": [{"route_id": row["route_id"], "splice": row["splice"]} for row in candidates],
        "compatibility_threshold": 8,
    }, indent=2) + "\n")
    print(f"parents={len(parents)} compatible_edges={len(compatible)} generated={len(candidates)}")


if __name__ == "__main__":
    main()
