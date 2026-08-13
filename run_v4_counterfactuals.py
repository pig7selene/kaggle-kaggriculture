"""Validated same-prestate counterfactual harness for V4."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from runpy import run_path
import statistics

from kaggle_environments import make

from run_epic_experiments import _recorded_shop_schedule, _run_with_fixed_shops
from run_post_opening_validation import _load_opponent
from run_v27_replay_backbone import _semantic_validate


ROOT = Path(__file__).resolve().parent
V2 = ROOT / "agents/super_replay_v2/super_backbone_v2.py"
MANIFEST = ROOT / "experiments/v3_real_v2_replays/manifest.json"
DIAGNOSTICS = ROOT / "experiments/v4_real_failure_diagnostics.json"


def new_v2():
    return run_path(str(V2))["agent"]


def trace_spec(path, player):
    return f"trace:{ROOT / path}:{int(player)}"


def run_full(meta):
    replay = json.loads((ROOT / meta["replay_path"]).read_text())
    seat = int(meta["seat"])
    opponent = _load_opponent(trace_spec(meta["replay_path"], 1 - seat))
    pair = [opponent, opponent]
    pair[seat] = new_v2()
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": int(meta["seed"])}, debug=True)
    _run_with_fixed_shops(env, pair, _recorded_shop_schedule(replay))
    return env, replay


def warm(agent, steps, seat, checkpoint):
    for step in range(checkpoint):
        obs = deepcopy(steps[step][seat].observation)
        obs["step"] = step
        agent(obs)
    return agent


def alter(action, obs, case):
    output = deepcopy(action)
    kind = case["kind"]
    item = case.get("item")
    if kind == "add_full_sell":
        quantity = int(obs["private"]["shed"].get(item, 0))
        if quantity > 0 and len(output["market"]) < 10:
            output["market"].append(["SELL", item, quantity])
    elif kind in {"remove_sell", "fraction_sell", "full_sell"}:
        market = []
        for order in output["market"]:
            if order and order[0] == "SELL" and order[1] == item:
                if kind == "remove_sell":
                    continue
                quantity = (
                    max(1, round(int(order[2]) * float(case["fraction"])))
                    if kind == "fraction_sell"
                    else int(obs["private"]["shed"].get(item, order[2]))
                )
                market.append(["SELL", item, quantity])
            else:
                market.append(order)
        output["market"] = market
    elif kind == "cow_quantity":
        market = []
        for order in output["market"]:
            if order and order[0] == "BUY_ANIMAL" and order[1] == "COW":
                quantity = int(case["quantity"])
                if quantity:
                    market.append(["BUY_ANIMAL", "COW", quantity])
            else:
                market.append(order)
        output["market"] = market
    elif kind == "remove_market_op":
        output["market"] = [order for order in output["market"] if not order or order[0] != case["op"]]
    elif kind == "liquidate_premium":
        for product in ("MELON", "STRAWBERRY", "MILK", "WOOL"):
            present = int(obs["private"]["shed"].get(product, 0))
            planned = sum(int(order[2]) for order in output["market"] if order and order[0] == "SELL" and order[1] == product)
            if present > planned and len(output["market"]) < 10:
                output["market"].append(["SELL", product, present - planned])
    return output


def resume(full, replay, meta, checkpoint, case=None):
    seat = int(meta["seat"])
    base = warm(new_v2(), full.steps, seat, checkpoint)
    semantic = []

    def candidate(obs):
        action = base(obs)
        if case and int(obs["step"]) == checkpoint:
            action = alter(action, obs, case)
        try:
            _semantic_validate(obs, action)
        except Exception as error:
            semantic.append({"step": int(obs["step"]), "error": repr(error), "action": action})
        return action

    opponent = _load_opponent(trace_spec(meta["replay_path"], 1 - seat))
    pair = [opponent, opponent]
    pair[seat] = candidate
    env = make(
        "kaggriculture", configuration={"episodeSteps": 720, "seed": int(meta["seed"])},
        steps=deepcopy(full.steps[:checkpoint + 1]), debug=True,
    )
    env.info.update(deepcopy(full.info))
    _run_with_fixed_shops(env, pair, _recorded_shop_schedule(replay))
    return env, semantic


CASES = {
    "market": [
        {"name": "sell_strawberry_one_step_early", "step": 398, "kind": "add_full_sell", "item": "STRAWBERRY"},
        {"name": "sell_strawberry_four_steps_early", "step": 395, "kind": "add_full_sell", "item": "STRAWBERRY"},
        {"name": "sell_strawberry_eight_steps_early", "step": 391, "kind": "add_full_sell", "item": "STRAWBERRY"},
        {"name": "sell_strawberry_twelve_steps_early", "step": 387, "kind": "add_full_sell", "item": "STRAWBERRY"},
        {"name": "delay_strawberry_399", "step": 399, "kind": "remove_sell", "item": "STRAWBERRY"},
        {"name": "quarter_strawberry_399", "step": 399, "kind": "fraction_sell", "item": "STRAWBERRY", "fraction": 0.25},
        {"name": "half_strawberry_399", "step": 399, "kind": "fraction_sell", "item": "STRAWBERRY", "fraction": 0.50},
        {"name": "three_quarter_strawberry_399", "step": 399, "kind": "fraction_sell", "item": "STRAWBERRY", "fraction": 0.75},
        {"name": "full_strawberry_399", "step": 399, "kind": "full_sell", "item": "STRAWBERRY"},
        {"name": "delay_milk_406", "step": 406, "kind": "remove_sell", "item": "MILK"},
        {"name": "half_milk_406", "step": 406, "kind": "fraction_sell", "item": "MILK", "fraction": 0.50},
    ],
    "capital": [
        {"name": "buy_zero_final_cows", "step": 192, "kind": "cow_quantity", "quantity": 0},
        {"name": "buy_one_final_cow", "step": 192, "kind": "cow_quantity", "quantity": 1},
    ],
    "endgame": [
        {"name": "skip_day25_seed", "step": 601, "kind": "remove_market_op", "op": "BUY_SEED"},
        {"name": "liquidate_premium_day27", "step": 648, "kind": "liquidate_premium"},
        {"name": "skip_day29_hires", "step": 696, "kind": "remove_market_op", "op": "HIRE"},
    ],
}


def aggregate(rows):
    output = {}
    for name in sorted({row["case"] for row in rows}):
        subset = [row for row in rows if row["case"] == name]
        deltas = [row["final_money_delta"] for row in subset]
        output[name] = {
            "games": len(subset), "average_final_money_delta": statistics.fmean(deltas),
            "median_final_money_delta": statistics.median(deltas),
            "wins": sum(value > 0 for value in deltas), "losses": sum(value < 0 for value in deltas),
            "ties": sum(value == 0 for value in deltas), "min_delta": min(deltas), "max_delta": max(deltas),
            "semantic_failures": sum(len(row["semantic_failures"]) for row in subset),
        }
    return output


def main():
    manifest = json.loads(MANIFEST.read_text())
    metadata = {int(row["episode_id"]): row for row in manifest["episodes"]}
    losses = sorted(
        [row for row in json.loads(DIAGNOSTICS.read_text())["episodes"] if row["result"] == "loss"],
        key=lambda row: (row["margin"], row["episode_id"]),
    )[:4]
    artifacts = {key: [] for key in CASES}
    resume_validation = []
    sources = []
    for loss in losses:
        meta = metadata[int(loss["episode_id"])]
        full, replay = run_full(meta)
        seat = int(meta["seat"])
        baseline = float(full.steps[-1][seat].reward)
        recorded = float(replay["steps"][-1][seat]["reward"])
        source = {
            "episode_id": loss["episode_id"], "opponent": loss["opponent"], "seat": seat,
            "seed": meta["seed"], "local_baseline_money": baseline, "recorded_money": recorded,
            "local_reconstruction_delta": baseline - recorded,
        }
        sources.append(source)
        for checkpoint in (160, 240, 480, 600):
            resumed, semantic = resume(full, replay, meta, checkpoint)
            resumed_money = float(resumed.steps[-1][seat].reward)
            resume_validation.append({
                "episode_id": loss["episode_id"], "checkpoint": checkpoint,
                "baseline_money": baseline, "resumed_money": resumed_money,
                "money_match": resumed_money == baseline,
                "final_observation_match": resumed.steps[-1][seat].observation == full.steps[-1][seat].observation,
                "semantic_failures": semantic,
            })
        for family, cases in CASES.items():
            for case in cases:
                branched, semantic = resume(full, replay, meta, int(case["step"]), case)
                money = float(branched.steps[-1][seat].reward)
                artifacts[family].append({
                    "episode_id": loss["episode_id"], "opponent": loss["opponent"],
                    "case": case["name"], "step": case["step"], "definition": case,
                    "baseline_money": baseline, "counterfactual_money": money,
                    "final_money_delta": money - baseline, "semantic_failures": semantic,
                })
        print(f"counterfactual episode {loss['episode_id']} complete", flush=True)

    validation = {
        "schema_version": 1, "sources": sources,
        "checkpoint_resume": resume_validation,
        "all_resume_money_match": all(row["money_match"] for row in resume_validation),
        "all_resume_observation_match": all(row["final_observation_match"] for row in resume_validation),
        "all_source_reconstructions_exact": all(row["local_reconstruction_delta"] == 0 for row in sources),
    }
    (ROOT / "experiments/v4_counterfactual_harness_validation.json").write_text(json.dumps(validation, indent=2, sort_keys=True) + "\n")
    targets = {
        "market": ROOT / "experiments/v4_market_counterfactuals.json",
        "capital": ROOT / "experiments/v4_capital_counterfactuals.json",
        "endgame": ROOT / "experiments/v4_endgame_counterfactuals.json",
    }
    for family, path in targets.items():
        payload = {
            "schema_version": 1, "family": family,
            "harness_validation": {
                "all_resume_money_match": validation["all_resume_money_match"],
                "all_resume_observation_match": validation["all_resume_observation_match"],
                "all_source_reconstructions_exact": validation["all_source_reconstructions_exact"],
            },
            "cases": CASES[family], "games": artifacts[family], "summary": aggregate(artifacts[family]),
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        print(path)
        for name, row in payload["summary"].items():
            print(f"  {name}: {row['wins']}/{row['losses']}/{row['ties']} {row['average_final_money_delta']:+.1f}")


if __name__ == "__main__":
    main()
