"""Build one faithful public medoid-route reconstruction per current Top-3 team."""

from __future__ import annotations

import json
from pathlib import Path

from analyze_super_replays import _counts
from analyze_v27_routes import normalized_action, state_anchor


ROOT = Path(__file__).resolve().parent
EXP = ROOT / "experiments"
MANIFEST = EXP / "top3_corpus_manifest.json"
CORE = EXP / "top3_forensic_core.json"
OUT = EXP / "top3_raw_route_bank.json"


def main():
    manifest = json.loads(MANIFEST.read_text())
    core = json.loads(CORE.read_text())
    episode_rows = {int(row["episode_id"]): row for row in manifest["episodes"]}
    routes = []
    for summary in sorted(core["summaries"], key=lambda row: row["rank"]):
        episode_id = int(summary["representative"]["episode_id"])
        episode = episode_rows[episode_id]
        replay = json.loads((ROOT / episode["replay_path"]).read_text())
        appearance = next(
            row for row in episode["appearances"]
            if int(row["submission_id"]) == int(summary["submission_id"])
        )
        player = int(appearance["seat"])
        actions = [normalized_action(replay, player, step) for step in range(719)]
        expected = []
        for step in range(719):
            state = state_anchor(replay, player, step)
            state.update(_counts(replay["steps"][step][player]["observation"]["farms"][player]))
            expected.append(state)
        routes.append({
            "route_id": f"top3_rank{summary['rank']}_raw",
            "source_rank": summary["rank"], "source_team": summary["team"],
            "source_submission_id": summary["submission_id"],
            "source_episode_id": episode_id, "source_player": player,
            "source_seed": int(replay["info"]["seed"]),
            "source_replay_path": episode["replay_path"],
            "source_final_money": float(replay["steps"][-1][player]["reward"]),
            "source_opponent": replay["info"]["TeamNames"][1 - player],
            "actions": actions, "consensus_actions": actions,
            "expected_state": expected,
            "fidelity_limit": "One public medoid continuation. It does not claim to reconstruct unobserved adaptive source code.",
        })
    OUT.write_text(json.dumps({"schema_version": 1, "route_count": len(routes), "routes": routes}, indent=2) + "\n")
    print(OUT)


if __name__ == "__main__":
    main()
