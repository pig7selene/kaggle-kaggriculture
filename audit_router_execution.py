"""Compare old local routing efficiency with the public top-player paths."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from kaggle_environments import make

from analyze_worker_routing import _combine_appearances, analyze_steps
from benchmark import ROOT, _load_agent


AGENTS = {
    "current_best_old_router": ROOT / "agents" / "animal_c8_day12_land_day11.py",
    "replay_land_labor_old_router": ROOT / "agents" / "replay_meta_land_labor.py",
    "replay_full_old_router": ROOT / "agents" / "replay_meta_full_schedule.py",
}
DEFAULT_OPPONENT = ROOT / "agents" / "adversaries" / "gen_land_d8_labor6.py"
ANIMAL_PRODUCTS = {"MILK", "WOOL", "EGG", "FERTILIZER"}


def _run(path, opponent_path, seed, seat):
    candidate = _load_agent(str(path.resolve()))
    opponent = _load_agent(str(opponent_path.resolve()))
    agents = [opponent, opponent]
    agents[seat] = candidate
    env = make(
        "kaggriculture",
        configuration={"episodeSteps": 720, "seed": int(seed)},
        debug=True,
    )
    env.run(agents)
    final = env.steps[-1]
    statuses = [state.status for state in final]
    if len(env.steps) != 720 or statuses != ["DONE", "DONE"]:
        raise RuntimeError(
            f"failed {path.name} seed={seed} seat={seat}: "
            f"turns={len(env.steps)} statuses={statuses}"
        )
    routing = analyze_steps(env.steps, env.configuration, [seat])[seat]
    revenue = routing.get("sale_revenue", {})
    return {
        "seed": seed,
        "seat": seat,
        "money": float(final[seat].reward),
        "opponent_money": float(final[1 - seat].reward),
        "advantage": float(final[seat].reward - final[1 - seat].reward),
        "crop_revenue": sum(value for product, value in revenue.items() if product not in ANIMAL_PRODUCTS),
        "animal_revenue": sum(revenue.get(product, 0) for product in ANIMAL_PRODUCTS),
        "routing": routing,
    }


def _summarize(games):
    appearances = [{"routing": game["routing"]} for game in games]
    return {
        "games": len(games),
        "average_money": statistics.fmean(game["money"] for game in games),
        "average_advantage": statistics.fmean(game["advantage"] for game in games),
        "average_crop_revenue": statistics.fmean(game["crop_revenue"] for game in games),
        "average_animal_revenue": statistics.fmean(game["animal_revenue"] for game in games),
        "routing": _combine_appearances(appearances),
    }


def _markdown(payload):
    top = payload["top_population"]["by_scale"]
    lines = [
        "# Old-router execution audit", "",
        "Identical routing instrumentation is used for public and local paths.", "",
        "## Public top-player reference", "",
        "| Capacity | Productive | Movement | PASS | Move/productive | Tile utilization | Critical water miss | Unfed | Uncared |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for scale, row in top.items():
        lines.append(
            f"| {scale} | {row['productive_action_ratio']:.1%} | {row['movement_action_ratio']:.1%} | "
            f"{row['pass_action_ratio']:.1%} | {row['movement_per_productive_action']:.2f} | "
            f"{row['productive_tile_utilization']:.1%} | {row['critical_watering_miss_rate']:.1%} | "
            f"{row['animal_unfed_rate']:.1%} | {row['animal_uncared_rate']:.1%} |"
        )
    for name, result in payload["agents"].items():
        lines.extend([
            "", f"## {name}", "",
            f"Games: {result['games']}; average money {result['average_money']:.1f}; "
            f"crop revenue {result['average_crop_revenue']:.1f}; animal revenue {result['average_animal_revenue']:.1f}.",
            "", "| Capacity | Productive | Movement | PASS | Invalid | Move/productive | Tile utilization | Critical water miss | Unfed | Uncared | Fert left |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ])
        for scale, row in result["routing"]["by_scale"].items():
            lines.append(
                f"| {scale} | {row['productive_action_ratio']:.1%} | {row['movement_action_ratio']:.1%} | "
                f"{row['pass_action_ratio']:.1%} | {row['invalid_action_ratio']:.1%} | "
                f"{row['movement_per_productive_action']:.2f} | {row['productive_tile_utilization']:.1%} | "
                f"{row['critical_watering_miss_rate']:.1%} | {row['animal_unfed_rate']:.1%} | "
                f"{row['animal_uncared_rate']:.1%} | {row['fertilizer_left_rate']:.1%} |"
            )
        delay = result["routing"]["land_first_use_delay_turns"]
        lines.append(
            f"\nLand-to-first-use median {delay['median']} turns, range {delay['range']}."
        )
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-start", type=int, default=12700)
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--opponent", type=Path, default=DEFAULT_OPPONENT)
    args = parser.parse_args()
    top = json.loads((ROOT / "experiments" / "top_player_worker_routing.json").read_text())
    games_by_agent = {}
    all_games = {}
    for name, path in AGENTS.items():
        games = []
        for seed in range(args.seed_start, args.seed_start + args.seeds):
            for seat in (0, 1):
                games.append(_run(path, args.opponent, seed, seat))
                print(f"audited {name} seed={seed} seat={seat}", flush=True)
        all_games[name] = games
        games_by_agent[name] = _summarize(games)
    payload = {
        "schema_version": 1,
        "experiment": "old_router_execution_audit",
        "seeds": list(range(args.seed_start, args.seed_start + args.seeds)),
        "both_seats": True,
        "opponent": str(args.opponent.relative_to(ROOT)),
        "top_population": top["population"],
        "agents": games_by_agent,
        "games": all_games,
    }
    output = ROOT / "experiments" / "router_execution_audit.json"
    report = ROOT / "experiments" / "router_execution_audit.md"
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    report.write_text(_markdown(payload), encoding="utf-8")
    print(output)
    print(report)


if __name__ == "__main__":
    main()

