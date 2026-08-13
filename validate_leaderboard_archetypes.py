"""Re-execute public replay traces and compare their economic trajectories."""

from __future__ import annotations

import json
from pathlib import Path

from kaggle_environments import make

from run_epic_experiments import _recorded_shop_schedule, _run_with_fixed_shops
from run_leaderboard_breakthrough import REPLAY_CASES, HELDOUT_REPLAY_CASES, ROOT
from run_post_opening_validation import _load_opponent


OUTPUT = ROOT / "experiments" / "leaderboard_archetype_validation.json"
CHECKPOINT_DAYS = (2, 4, 6, 8, 10, 11, 12, 15, 20, 25, 29)


def _trace(path, player):
    return _load_opponent(f"trace:{ROOT / path}:{player}")


def _checkpoints(replay, player):
    rows = {}
    for day in CHECKPOINT_DAYS:
        index = min(day * 24 + 23, len(replay["steps"]) - 1)
        obs = replay["steps"][index][0]["observation"]
        farm = obs["farms"][player]
        productive = 0
        crops = {}
        animals = {}
        for tile_row in farm["tiles"]:
            for tile in tile_row:
                if not isinstance(tile, dict):
                    continue
                if tile.get("kind") == "PLANT":
                    productive += 1
                    crops[tile["crop"]] = crops.get(tile["crop"], 0) + 1
                elif tile.get("animal"):
                    productive += 1
                    animals[tile["animal"]] = animals.get(tile["animal"], 0) + 1
        rows[str(day)] = {
            "bank": float(farm["money"]),
            "quadrants": len(farm.get("unlocked_quadrants", [])),
            "hands": len(farm.get("hands", [])),
            "productive_tiles": productive,
            "crops": crops,
            "animals": animals,
        }
    return rows


def main():
    cases = {**REPLAY_CASES, **HELDOUT_REPLAY_CASES}
    rows = []
    for name, (episode_id, replay_path, selected_player) in cases.items():
        source = json.loads((ROOT / replay_path).read_text())
        seed = int(source["info"]["seed"])
        env = make(
            "kaggriculture",
            configuration={"episodeSteps": 720, "seed": seed},
            debug=True,
        )
        _run_with_fixed_shops(
            env,
            [_trace(replay_path, 0), _trace(replay_path, 1)],
            _recorded_shop_schedule(source),
        )
        reproduced = env.toJSON()
        source_final = [float(state["reward"]) for state in source["steps"][-1]]
        replay_final = [float(state["reward"]) for state in reproduced["steps"][-1]]
        source_points = _checkpoints(source, selected_player)
        replay_points = _checkpoints(reproduced, selected_player)
        max_bank_error = max(
            abs(source_points[day]["bank"] - replay_points[day]["bank"])
            for day in source_points
        )
        rows.append({
            "archetype": name,
            "episode_id": episode_id,
            "selected_player": selected_player,
            "selected_team": source["info"]["TeamNames"][selected_player],
            "source_final_money": source_final,
            "reproduced_final_money": replay_final,
            "final_money_error": [replay_final[i] - source_final[i] for i in (0, 1)],
            "max_selected_checkpoint_bank_error": max_bank_error,
            "selected_checkpoint_trajectory_exact": source_points == replay_points,
            "steps": len(reproduced["steps"]),
            "statuses": [state["status"] for state in reproduced["steps"][-1]],
        })
        print(name, rows[-1])
    payload = {
        "schema_version": 1,
        "method": "both original action traces, original seed, recorded shop schedule",
        "cases": rows,
        "all_trajectories_exact": all(row["selected_checkpoint_trajectory_exact"] for row in rows),
        "all_final_money_exact": all(row["final_money_error"] == [0.0, 0.0] for row in rows),
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(OUTPUT)


if __name__ == "__main__":
    main()
