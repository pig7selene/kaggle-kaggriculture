"""Router-only R0/R1 and R2/R3 ablations on a high-scale opponent pool."""

from __future__ import annotations

import argparse
import json
import statistics
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from kaggle_environments import make

from analyze_worker_routing import _combine_appearances, analyze_steps
from benchmark import DEFAULT_WORKERS, ROOT, _file_sha256, _load_agent
from test_economic_agents import _validate_action


CANDIDATES = {
    "R0_old_router_current_economy": ROOT / "agents" / "animal_c8_day12_land_day11.py",
    "R1_new_router_current_economy": ROOT / "agents" / "router_r1_current_economy.py",
    "R2_old_router_replay_economy": ROOT / "agents" / "replay_meta_full_schedule.py",
    "R3_new_router_replay_economy": ROOT / "agents" / "router_r3_replay_economy.py",
}
OPPONENTS = {
    "current_best": ROOT / "agents" / "animal_c8_day12_land_day11.py",
    "gen_land_d8_labor6": ROOT / "agents" / "adversaries" / "gen_land_d8_labor6.py",
    "gen_land_d11_labor7_sell12": ROOT / "agents" / "adversaries" / "gen_land_d11_labor7_sell12.py",
    "gen_cow6_d8": ROOT / "agents" / "adversaries" / "gen_cow6_d8.py",
    "proxy_livestock_crop": ROOT / "agents" / "proxies" / "livestock_crop.py",
    "proxy_high_labor": ROOT / "agents" / "proxies" / "high_labor.py",
    "proxy_land_expander": ROOT / "agents" / "proxies" / "land_expander.py",
}
ANIMAL_PRODUCTS = {"MILK", "WOOL", "EGG", "FERTILIZER"}
VALUABLE = ANIMAL_PRODUCTS | {
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "COW", "SHEEP", "GOOSE",
}


def _productive(farm):
    return sum(
        isinstance(tile, dict)
        and (tile.get("kind") == "PLANT" or tile.get("animal") is not None)
        for row in farm["tiles"] for tile in row
    )


def _cow_count(farm):
    return sum(
        isinstance(tile, dict) and tile.get("animal") == "COW"
        for row in farm["tiles"] for tile in row
    )


def _sheep_count(farm):
    return sum(
        isinstance(tile, dict) and tile.get("animal") == "SHEEP"
        for row in farm["tiles"] for tile in row
    )


def _stranded(state, seat):
    private = state.observation["private"]
    total = sum(private["shed"].get(item, 0) for item in VALUABLE)
    total += sum(
        inventory.get(item, 0)
        for inventory in private["inventories"] for item in VALUABLE
    )
    farm = state.observation["farms"][seat]
    total += sum(
        tile.get("yield_units", 0)
        for row in farm["tiles"] for tile in row
        if isinstance(tile, dict) and tile.get("animal") is not None
    )
    return total


def _run_game(job):
    candidate_name, candidate_path, opponent_name, opponent_path, seed, seat = job
    candidate = _load_agent(candidate_path)
    opponent = _load_agent(opponent_path)
    peak_hands = 0
    peak_productive = 0
    peak_cows = 0
    peak_sheep = 0

    def checked(obs):
        nonlocal peak_hands, peak_productive, peak_cows, peak_sheep
        action = candidate(obs)
        _validate_action(obs, action)
        farm = obs["farms"][obs["player"]]
        peak_hands = max(peak_hands, len(farm["hands"]))
        peak_productive = max(peak_productive, _productive(farm))
        peak_cows = max(peak_cows, _cow_count(farm))
        peak_sheep = max(peak_sheep, _sheep_count(farm))
        return action

    agents = [opponent, opponent]
    agents[seat] = checked
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
            f"failed {candidate_name} vs {opponent_name} seed={seed} seat={seat}: "
            f"turns={len(env.steps)} statuses={statuses}"
        )
    routing = analyze_steps(env.steps, env.configuration, [seat])[seat]
    revenue = routing.get("sale_revenue", {})
    farm = final[seat].observation["farms"][seat]
    money = float(final[seat].reward)
    opponent_money = float(final[1 - seat].reward)
    return {
        "candidate": candidate_name,
        "opponent": opponent_name,
        "seed": seed,
        "seat": seat,
        "money": money,
        "opponent_money": opponent_money,
        "advantage": money - opponent_money,
        "final_quadrants": len(farm["unlocked_quadrants"]),
        "peak_hands": peak_hands,
        "peak_productive_tiles": peak_productive,
        "peak_cows": peak_cows,
        "final_cows": _cow_count(farm),
        "peak_sheep": peak_sheep,
        "final_sheep": _sheep_count(farm),
        "stranded_units": _stranded(final[seat], seat),
        "crop_revenue": sum(value for product, value in revenue.items() if product not in ANIMAL_PRODUCTS),
        "animal_revenue": sum(revenue.get(product, 0) for product in ANIMAL_PRODUCTS),
        "sale_revenue": revenue,
        "routing": routing,
    }


def _percentile(values, fraction):
    values = sorted(values)
    index = fraction * (len(values) - 1)
    lower = int(index)
    upper = min(lower + 1, len(values) - 1)
    weight = index - lower
    return values[lower] * (1 - weight) + values[upper] * weight


def _summary(games):
    advantages = [game["advantage"] for game in games]
    wins = sum(value > 0 for value in advantages)
    losses = sum(value < 0 for value in advantages)
    by_seed = {}
    for game in games:
        by_seed.setdefault(game["seed"], []).append(game["advantage"])
    routing = _combine_appearances([{"routing": game["routing"]} for game in games])
    return {
        "games": len(games),
        "wins": wins,
        "losses": losses,
        "ties": len(games) - wins - losses,
        "score_rate": (wins + 0.5 * (len(games) - wins - losses)) / len(games),
        "average_money": statistics.fmean(game["money"] for game in games),
        "average_advantage": statistics.fmean(advantages),
        "p10_seed_advantage": _percentile(
            [statistics.fmean(values) for values in by_seed.values()], 0.10
        ),
        "average_crop_revenue": statistics.fmean(game["crop_revenue"] for game in games),
        "average_animal_revenue": statistics.fmean(game["animal_revenue"] for game in games),
        "average_final_quadrants": statistics.fmean(game["final_quadrants"] for game in games),
        "average_peak_hands": statistics.fmean(game["peak_hands"] for game in games),
        "average_peak_productive_tiles": statistics.fmean(game["peak_productive_tiles"] for game in games),
        "average_peak_cows": statistics.fmean(game["peak_cows"] for game in games),
        "average_peak_sheep": statistics.fmean(game["peak_sheep"] for game in games),
        "max_cow_loss": max(game["peak_cows"] - game["final_cows"] for game in games),
        "max_sheep_loss": max(game["peak_sheep"] - game["final_sheep"] for game in games),
        "max_stranded_units": max(game["stranded_units"] for game in games),
        "routing": routing,
    }


def _candidate_result(name, games):
    matchups = {
        opponent: _summary([game for game in games if game["opponent"] == opponent])
        for opponent in OPPONENTS
    }
    return {
        "candidate": name,
        "path": str(CANDIDATES[name].relative_to(ROOT)),
        "sha256": _file_sha256(CANDIDATES[name]),
        "overall": _summary(games),
        "matchups": matchups,
        "worst_opponent": min(
            matchups,
            key=lambda opponent: (
                matchups[opponent]["score_rate"], matchups[opponent]["average_advantage"]
            ),
        ),
    }


def _markdown(payload):
    lines = [
        "# Router-only ablation", "",
        "R0/R1 share the frozen C8 economy; R2/R3 share the frozen cow-only replay economy.", "",
        "| Candidate | Games | W/L/T | Score | Avg money | Avg advantage | P10 | Crop revenue | Animal revenue | Quadrants | Peak hands | Peak productive |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in payload["candidates"]:
        o = row["overall"]
        lines.append(
            f"| {row['candidate']} | {o['games']} | {o['wins']}/{o['losses']}/{o['ties']} | "
            f"{o['score_rate']:.1%} | {o['average_money']:.1f} | {o['average_advantage']:+.1f} | "
            f"{o['p10_seed_advantage']:+.1f} | {o['average_crop_revenue']:.1f} | "
            f"{o['average_animal_revenue']:.1f} | {o['average_final_quadrants']:.2f} | "
            f"{o['average_peak_hands']:.2f} | {o['average_peak_productive_tiles']:.2f} |"
        )
    lines.extend(["", "## Routing by capacity", ""])
    for row in payload["candidates"]:
        lines.extend([
            f"### {row['candidate']}", "",
            "| Capacity | Productive | Movement | PASS | Move/productive | Tile utilization | Critical water miss | Unfed | Uncared | Fert left |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ])
        for scale, metrics in row["overall"]["routing"]["by_scale"].items():
            lines.append(
                f"| {scale} | {metrics['productive_action_ratio']:.1%} | "
                f"{metrics['movement_action_ratio']:.1%} | {metrics['pass_action_ratio']:.1%} | "
                f"{metrics['movement_per_productive_action']:.2f} | "
                f"{metrics['productive_tile_utilization']:.1%} | "
                f"{metrics['critical_watering_miss_rate']:.1%} | "
                f"{metrics['animal_unfed_rate']:.1%} | {metrics['animal_uncared_rate']:.1%} | "
                f"{metrics['fertilizer_left_rate']:.1%} |"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--seed-start", type=int, default=12820)
    parser.add_argument("--seeds", type=int, default=3)
    args = parser.parse_args()
    seeds = list(range(args.seed_start, args.seed_start + args.seeds))
    jobs = [
        (candidate, str(path.resolve()), opponent, str(opponent_path.resolve()), seed, seat)
        for candidate, path in CANDIDATES.items()
        for opponent, opponent_path in OPPONENTS.items()
        for seed in seeds for seat in (0, 1)
    ]
    games = []
    if args.workers <= 1:
        for index, job in enumerate(jobs, 1):
            games.append(_run_game(job))
            if index % 25 == 0 or index == len(jobs):
                print(f"router ablation {index}/{len(jobs)}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = [executor.submit(_run_game, job) for job in jobs]
            for index, future in enumerate(as_completed(futures), 1):
                games.append(future.result())
                if index % 25 == 0 or index == len(jobs):
                    print(f"router ablation {index}/{len(jobs)}", flush=True)
    candidates = [
        _candidate_result(
            name, [game for game in games if game["candidate"] == name]
        )
        for name in CANDIDATES
    ]
    payload = {
        "schema_version": 1,
        "experiment": "router_only_ablation",
        "seeds": seeds,
        "both_seats": True,
        "opponents": {name: str(path.relative_to(ROOT)) for name, path in OPPONENTS.items()},
        "games_per_candidate": len(OPPONENTS) * len(seeds) * 2,
        "candidates": candidates,
        "games": games,
    }
    output = ROOT / "experiments" / "router_ablation.json"
    report = ROOT / "experiments" / "router_ablation.md"
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    report.write_text(_markdown(payload), encoding="utf-8")
    print(output)
    print(report)
    for row in candidates:
        o = row["overall"]
        print(
            row["candidate"], f"{o['wins']}/{o['losses']}/{o['ties']}",
            f"money={o['average_money']:.1f}", f"adv={o['average_advantage']:.1f}",
            f"worst={row['worst_opponent']}",
        )


if __name__ == "__main__":
    main()
