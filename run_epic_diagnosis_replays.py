"""Generate fixed-shop current-best replays against the two remaining losses."""

from __future__ import annotations

import json
from pathlib import Path
from runpy import run_path

from kaggle_environments import make

from run_crop_lifecycle_experiments import (
    _recorded_shop_schedule,
    _run_with_fixed_shops,
    _source_replay,
)
from run_post_opening_validation import ROOT, _load_opponent, _trace_spec
from test_economic_agents import _validate_action


CASES = {
    92008833: {"name": "jayveer", "our_seat": 1},
    92010768: {"name": "pedro", "our_seat": 0},
}
SOURCE = ROOT / "agents" / "lifecycle_lc_combined.py"
OUTPUT = ROOT / "experiments" / "epic_replays"


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for episode_id, case in CASES.items():
        source_replay = _source_replay(episode_id)
        schedule = _recorded_shop_schedule(source_replay)
        seed = int(source_replay["info"]["seed"])
        candidate = run_path(str(SOURCE))["agent"]
        opponent = _load_opponent(_trace_spec(episode_id))
        calls = 0

        def checked(obs):
            nonlocal calls
            action = candidate(obs)
            _validate_action(obs, action)
            calls += 1
            return action

        pair = [opponent, opponent]
        pair[case["our_seat"]] = checked
        env = make(
            "kaggriculture",
            configuration={"episodeSteps": 720, "seed": seed},
            debug=True,
        )
        _run_with_fixed_shops(env, pair, schedule)
        final = env.steps[-1]
        if len(env.steps) != 720 or calls != 719:
            raise RuntimeError((episode_id, len(env.steps), calls))
        destination = OUTPUT / f"lifecycle_vs_{case['name']}_{episode_id}.json"
        destination.write_text(json.dumps(env.toJSON()))
        row = {
            "episode_id": episode_id,
            "opponent": case["name"],
            "seed": seed,
            "our_seat": case["our_seat"],
            "opponent_seat": 1 - case["our_seat"],
            "replay": str(destination.relative_to(ROOT)),
            "our_money": float(final[case["our_seat"]].reward),
            "opponent_money": float(final[1 - case["our_seat"]].reward),
            "action_calls": calls,
            "recorded_shop_schedule": schedule,
        }
        manifest.append(row)
        print(row)
    output = OUTPUT / "manifest.json"
    output.write_text(json.dumps({"source": str(SOURCE.relative_to(ROOT)), "cases": manifest}, indent=2) + "\n")
    print(output)


if __name__ == "__main__":
    main()
