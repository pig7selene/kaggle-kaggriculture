"""Two-game action equivalence and semantic validation for the opening submission."""

from __future__ import annotations

import ast
import hashlib
import json
import os
from collections import Counter
from copy import deepcopy
from pathlib import Path
from runpy import run_path

from kaggle_environments import make

from test_economic_agents import SELLABLE, _validate_action


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "agents" / "opening_public_front_cow8_day6.py"
SUBMISSION = ROOT / "submission" / "main.py"
OPPONENT = ROOT / "agents" / "router_replay_hands12.py"
CASES = ((731101, 0), (731102, 1))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _imports(path):
    tree = ast.parse(path.read_text())
    result = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            result.append(node.module or "")
    return sorted(set(result))


def _animals(obs):
    farm = obs["farms"][obs["player"]]
    counts = Counter()
    for row in farm["tiles"]:
        for tile in row:
            if isinstance(tile, dict) and tile.get("animal"):
                counts[tile["animal"]] += 1
    return counts


def _stranded(obs):
    private = obs["private"]
    shed_or_units = Counter()
    for item in SELLABLE:
        shed_or_units[item] += private["shed"].get(item, 0)
        shed_or_units[item] += sum(inv.get(item, 0) for inv in private["inventories"])
    tile_yield = 0
    for row in obs["farms"][obs["player"]]["tiles"]:
        for tile in row:
            if isinstance(tile, dict) and tile.get("animal"):
                tile_yield += tile.get("yield_units", 0)
    return {
        "shed_or_unit": {key: value for key, value in sorted(shed_or_units.items()) if value},
        "animal_tile_yield": tile_yield,
    }


def _case(seed, seat):
    source_agent = run_path(str(SOURCE))["agent"]
    submission_agent = run_path(str(SUBMISSION))["agent"]
    opponent = run_path(str(OPPONENT))["agent"]
    comparisons = 0
    peak = Counter()

    def checked(obs):
        nonlocal comparisons
        source_action = source_agent(deepcopy(obs))
        submission_action = submission_agent(deepcopy(obs))
        if source_action != submission_action:
            raise AssertionError(
                f"action mismatch seed={seed} seat={seat} step={obs['step']}: "
                f"source={source_action!r} submission={submission_action!r}"
            )
        _validate_action(obs, submission_action)
        comparisons += 1
        counts = _animals(obs)
        for animal in ("COW", "SHEEP", "GOOSE"):
            peak[animal] = max(peak[animal], counts[animal])
        return submission_action

    pair = [opponent, opponent]
    pair[seat] = checked
    env = make(
        "kaggriculture",
        configuration={"episodeSteps": 720, "seed": seed},
        debug=True,
    )
    env.run(pair)
    final = env.steps[-1]
    statuses = [state.status for state in final]
    if len(env.steps) != 720 or statuses != ["DONE", "DONE"]:
        raise RuntimeError(
            f"failed seed={seed} seat={seat}: turns={len(env.steps)} statuses={statuses}"
        )
    final_obs = final[seat].observation
    final_animals = _animals(final_obs)
    return {
        "seed": seed,
        "seat": seat,
        "opponent": "agents/router_replay_hands12.py",
        "episode_steps": len(env.steps),
        "action_comparisons": comparisons,
        "all_actions_equal": True,
        "runtime_errors": 0,
        "semantic_errors": 0,
        "invalid_actions": 0,
        "candidate_money": final[seat].reward,
        "opponent_money": final[1 - seat].reward,
        "peak_animals": {animal: peak[animal] for animal in ("COW", "SHEEP", "GOOSE")},
        "final_animals": {
            animal: final_animals[animal] for animal in ("COW", "SHEEP", "GOOSE")
        },
        "livestock_losses": {
            animal: peak[animal] - final_animals[animal]
            for animal in ("COW", "SHEEP", "GOOSE")
        },
        "stranded_inventory": _stranded(final_obs),
    }


def main():
    imports = _imports(SUBMISSION)
    if imports != ["base64", "runpy", "zlib"]:
        raise AssertionError(f"unexpected standalone imports: {imports}")
    original_cwd = Path.cwd()
    try:
        os.chdir("/tmp")
        isolated = run_path(str(SUBMISSION))
        if not callable(isolated.get("agent")):
            raise AssertionError("standalone did not expose callable agent")
    finally:
        os.chdir(original_cwd)

    cases = [_case(seed, seat) for seed, seat in CASES]
    payload = {
        "schema_version": 1,
        "source": {"path": str(SOURCE.relative_to(ROOT)), "sha256": _sha256(SOURCE)},
        "submission": {
            "path": str(SUBMISSION.relative_to(ROOT)),
            "sha256": _sha256(SUBMISSION),
            "imports": imports,
            "loads_outside_repository_working_directory": True,
        },
        "equivalence": cases,
        "all_requirements_met": all(
            row["all_actions_equal"]
            and row["runtime_errors"] == 0
            and row["semantic_errors"] == 0
            and row["invalid_actions"] == 0
            for row in cases
        ),
    }
    output = ROOT / "experiments" / "opening_submission_packaging_validation.json"
    output.write_text(json.dumps(payload, indent=2) + "\n")
    print(output)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
