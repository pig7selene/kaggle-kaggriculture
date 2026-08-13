"""Strict standalone equivalence and semantic validation for lifecycle v1."""

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
from kaggle_environments.envs.kaggriculture import kaggriculture as game

from analyze_post_opening_real_gap import _field_analysis
from analyze_top_player_replays import _transition_ledger
from test_economic_agents import SELLABLE, _validate_action


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "agents" / "lifecycle_lc_combined.py"
SUBMISSION = ROOT / "submission" / "main.py"
EQUIVALENCE_OPPONENT = ROOT / "agents" / "opening_public_front_cow8_day6.py"
SMOKE_OPPONENT = ROOT / "agents" / "replay_archetypes" / "aggressive_strawberry_scaler.py"
CASES = ((731101, 0), (731102, 1))
SMOKE = (731103, 0)
CROPS = tuple(game.CROPS)
ANIMALS = tuple(game.ANIMALS)


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


def _animals_in_farm(farm):
    counts = Counter()
    for row in farm["tiles"]:
        for tile in row:
            if isinstance(tile, dict) and tile.get("animal"):
                counts[tile["animal"]] += 1
    return counts


def _owned_animals(state, player):
    obs = state.observation
    counts = _animals_in_farm(obs["farms"][player])
    private = obs["private"]
    for animal in ANIMALS:
        counts[animal] += private["shed"].get(animal, 0)
        counts[animal] += sum(
            inventory.get(animal, 0) for inventory in private["inventories"]
        )
    return counts


def _market_request_counts(action):
    counts = Counter()
    for order in action.get("market", []):
        op = order[0]
        if op in {"HIRE", "BUY_LAND"}:
            counts[(op, None)] += 1
        else:
            counts[(op, order[1])] += int(order[2])
    return counts


def _market_actual_counts(ledger):
    counts = Counter()
    counts[("HIRE", None)] = ledger["hire_count"]
    counts[("BUY_LAND", None)] = ledger["land_count"]
    for item, quantity in ledger["seed_quantity"].items():
        counts[("BUY_SEED", item)] += quantity
    for item, quantity in ledger["product_quantity"].items():
        counts[("BUY_PRODUCT", item)] += quantity
    for item, quantity in ledger["animal_quantity"].items():
        counts[("BUY_ANIMAL", item)] += quantity
    for item, quantity in ledger["sale_quantity"].items():
        counts[("SELL", item)] += quantity
    return counts


def _transition_audit(replay, player):
    rejected = []
    bank_mismatches = []
    purchases = Counter()
    for index in range(1, len(replay["steps"])):
        previous = replay["steps"][index - 1]
        current = replay["steps"][index]
        ledgers, errors = _transition_ledger(previous, current, replay["configuration"])
        bank_mismatches.extend(errors)
        ledger = ledgers[player]
        purchases.update(ledger["animal_quantity"])
        action = current[player].get("action") or {}
        requested = _market_request_counts(action)
        actual = _market_actual_counts(ledger)
        if requested != actual:
            rejected.append({
                "step": index - 1,
                "requested": {f"{op}:{item}": value for (op, item), value in requested.items()},
                "executed": {f"{op}:{item}": value for (op, item), value in actual.items()},
            })
    return rejected, bank_mismatches, purchases


def _stranded_value(final_state, player):
    obs = final_state.observation
    private = obs["private"]
    farm = obs["farms"][player]
    prices = obs["market"]["prices"]
    liquid = Counter()
    for item in SELLABLE:
        liquid[item] += private["shed"].get(item, 0)
        liquid[item] += sum(
            inventory.get(item, 0) for inventory in private["inventories"]
        )
    animal_yield = Counter()
    crop_yield = Counter()
    fertilizer = 0
    for row in farm["tiles"]:
        for tile in row:
            if not isinstance(tile, dict):
                continue
            held = int(tile.get("yield_units", 0))
            if tile.get("kind") == "PLANT" and held > 0:
                crop_yield[tile["crop"]] += held
            elif tile.get("animal") and held > 0:
                animal_yield[game.ANIMALS[tile["animal"]]["product"]] += held
            if tile.get("animal") and tile.get("fertilizer_available", False):
                fertilizer += 1
    if fertilizer:
        crop_yield["FERTILIZER"] += fertilizer
    liquid_value = sum(quantity * prices[item] for item, quantity in liquid.items())
    animal_yield_value = sum(
        quantity * prices[item] for item, quantity in animal_yield.items()
    )
    nonliquid_field_value = sum(
        quantity * prices[item] for item, quantity in crop_yield.items()
    )
    # Preserve the project's established packaging definition: inventory that
    # can be liquidated directly plus animal product already held on a tile.
    # Crop yield and uncollected fertilizer are reported separately because
    # converting them to money requires field/logistics actions and is not
    # equivalent to stranded inventory.
    total = liquid_value + animal_yield_value
    money = float(final_state.reward)
    threshold = max(100.0, 0.005 * money)
    return {
        "liquid_inventory": {key: liquid[key] for key in sorted(liquid) if liquid[key]},
        "liquid_inventory_value": liquid_value,
        "animal_tile_yield": {
            key: animal_yield[key] for key in sorted(animal_yield) if animal_yield[key]
        },
        "animal_tile_yield_value": animal_yield_value,
        "total_liquidatable_or_held_animal_value": total,
        "meaningful_threshold": threshold,
        "meaningful_stranded_value": total > threshold,
        "nonliquid_field_potential": {
            key: crop_yield[key] for key in sorted(crop_yield) if crop_yield[key]
        },
        "nonliquid_field_potential_value": nonliquid_field_value,
    }


def _audit_replay(env, seat):
    replay = env.toJSON()
    routing = _field_analysis(replay, [seat])[seat]
    field_invalid = sum(
        day["counts"].get("invalid", 0) for day in routing["daily"]
    )
    rejected, bank_mismatches, purchases = _transition_audit(replay, seat)
    final = env.steps[-1]
    final_owned = _owned_animals(final[seat], seat)
    losses = {
        animal: max(0, purchases[animal] - final_owned[animal])
        for animal in ANIMALS
    }
    return {
        "invalid_field_actions": field_invalid,
        "rejected_or_partial_market_orders": rejected,
        "transition_bank_mismatches": bank_mismatches,
        "animal_purchases": {animal: purchases[animal] for animal in ANIMALS},
        "final_owned_animals": {animal: final_owned[animal] for animal in ANIMALS},
        "livestock_losses": losses,
        "stranded_endgame": _stranded_value(final[seat], seat),
    }


def _run(seed, seat, opponent_path, compare_source):
    source_agent = run_path(str(SOURCE))["agent"] if compare_source else None
    submission_agent = run_path(str(SUBMISSION))["agent"]
    opponent = run_path(str(opponent_path))["agent"]
    comparisons = 0

    def checked(obs):
        nonlocal comparisons
        submission_action = submission_agent(deepcopy(obs))
        _validate_action(obs, submission_action)
        if source_agent is not None:
            source_action = source_agent(deepcopy(obs))
            if source_action != submission_action:
                raise AssertionError(
                    f"action mismatch seed={seed} seat={seat} step={obs['step']}: "
                    f"source={source_action!r} submission={submission_action!r}"
                )
            comparisons += 1
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
    audit = _audit_replay(env, seat)
    return {
        "seed": seed,
        "seat": seat,
        "opponent": str(opponent_path.relative_to(ROOT)),
        "episode_steps": len(env.steps),
        "requested_actions": 719,
        "action_comparisons": comparisons,
        "all_actions_equal": comparisons == 719 if compare_source else None,
        "runtime_errors": 0,
        "semantic_errors": 0,
        "candidate_money": final[seat].reward,
        "opponent_money": final[1 - seat].reward,
        **audit,
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

    equivalence = [
        _run(seed, seat, EQUIVALENCE_OPPONENT, True) for seed, seat in CASES
    ]
    smoke = _run(SMOKE[0], SMOKE[1], SMOKE_OPPONENT, False)
    all_rows = [*equivalence, smoke]
    equivalence_and_standalone_integrity_passed = (
        all(row["all_actions_equal"] for row in equivalence)
        and all(row["runtime_errors"] == 0 and row["semantic_errors"] == 0 for row in all_rows)
        and all(not row["rejected_or_partial_market_orders"] for row in all_rows)
        and all(not row["transition_bank_mismatches"] for row in all_rows)
        and all(not row["stranded_endgame"]["meaningful_stranded_value"] for row in all_rows)
    )
    strict_zero_effect_noops = all(row["invalid_field_actions"] == 0 for row in all_rows)
    strict_zero_livestock_losses = all(
        not any(row["livestock_losses"].values()) for row in all_rows
    )
    payload = {
        "schema_version": 1,
        "source": {"path": str(SOURCE.relative_to(ROOT)), "sha256": _sha256(SOURCE)},
        "submission": {
            "path": str(SUBMISSION.relative_to(ROOT)),
            "sha256": _sha256(SUBMISSION),
            "imports": imports,
            "loads_outside_repository_working_directory": True,
        },
        "equivalence": equivalence,
        "standalone_smoke": smoke,
        "equivalence_and_standalone_integrity_passed": equivalence_and_standalone_integrity_passed,
        "strict_zero_effect_noops": strict_zero_effect_noops,
        "strict_zero_livestock_losses": strict_zero_livestock_losses,
        "source_equivalence_note": (
            "Any effect no-op or livestock loss is source-equivalent because every requested "
            "action matched the source in both equivalence games."
        ),
    }
    if not equivalence_and_standalone_integrity_passed:
        raise AssertionError(json.dumps(payload, indent=2))
    output = ROOT / "experiments" / "lifecycle_submission_packaging_validation.json"
    output.write_text(json.dumps(payload, indent=2) + "\n")
    print(output)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
