"""Run a deterministic round robin across the pure-melon scale agents."""

import argparse
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from itertools import combinations

from benchmark import DEFAULT_WORKERS, EXPERIMENTS_DIR, ROOT, _file_sha256
from round_robin_scaling import (
    _find_three_agent_cycles,
    _rank_agents,
    _run_round_robin_game,
    _summarize,
)


SCALES = (8, 12, 16, 20, 25)
AGENTS = {
    f"melon_scale_{scale:02d}": ROOT / "agents" / f"melon_scale_{scale:02d}.py"
    for scale in SCALES
}
SEED_START = 6200


def _write_markdown(path, result):
    names = result["agents"]
    labels = [name.removeprefix("melon_scale_") for name in names]
    lines = [
        "# Pure-Melon Scale Round Robin",
        "",
        f"- Games per matchup: {result['games_per_matchup']}",
        f"- Seeds per matchup: {len(result['seeds'])}",
        "- Every seed is played in both player positions.",
        f"- Total games: {result['total_games']}",
        "",
        "## Win-rate matrix",
        "",
        "Rows are the focal agent; columns are opponents.",
        "",
        "| Scale | " + " | ".join(labels) + " |",
        "| --- | " + " | ".join("---:" for _ in labels) + " |",
    ]
    for agent, label in zip(names, labels):
        cells = []
        for opponent in names:
            value = result["win_rate_matrix"][agent][opponent]
            cells.append("—" if value is None else f"{value * 100:.1f}%")
        lines.append(f"| {label} | " + " | ".join(cells) + " |")

    lines.extend(
        [
            "",
            "## Robustness ranking",
            "",
            "| Rank | Agent | W/L/T | Win rate | Avg money | Avg advantage | Matchups W/L/T |",
            "| ---: | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in result["ranking"]:
        lines.append(
            f"| {row['rank']} | {row['agent']} | "
            f"{row['wins']}/{row['losses']}/{row['ties']} | "
            f"{row['win_rate'] * 100:.2f}% | {row['average_money']:.2f} | "
            f"{row['average_money_advantage']:+.2f} | "
            f"{row['matchup_wins']}/{row['matchup_losses']}/{row['matchup_ties']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_round_robin(games_per_matchup, workers):
    if games_per_matchup < 100 or games_per_matchup % 2:
        raise SystemExit("--games-per-matchup must be an even number of at least 100")

    names = list(AGENTS)
    seeds = tuple(range(SEED_START, SEED_START + games_per_matchup // 2))
    jobs = [
        (agent_a, str(AGENTS[agent_a]), agent_b, str(AGENTS[agent_b]), seed, seat)
        for agent_a, agent_b in combinations(names, 2)
        for seed in seeds
        for seat in (0, 1)
    ]
    print(
        f"Running {len(jobs)} games across {len(list(combinations(names, 2)))} "
        f"matchups ({games_per_matchup} each, {workers} workers)...",
        flush=True,
    )
    games = []
    if workers == 1:
        for index, job in enumerate(jobs, start=1):
            games.append(_run_round_robin_game(job))
            if index % 100 == 0 or index == len(jobs):
                print(f"  completed {index}/{len(jobs)}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(_run_round_robin_game, job) for job in jobs]
            for index, future in enumerate(as_completed(futures), start=1):
                games.append(future.result())
                if index % 100 == 0 or index == len(jobs):
                    print(f"  completed {index}/{len(jobs)}", flush=True)

    games.sort(
        key=lambda game: (
            game["agent_a"], game["agent_b"], game["seed"], game["position_a"]
        )
    )
    matchups = {agent: {} for agent in names}
    for agent_a, agent_b in combinations(names, 2):
        pair_games = [
            game
            for game in games
            if game["agent_a"] == agent_a and game["agent_b"] == agent_b
        ]
        matchups[agent_a][agent_b] = _summarize(pair_games, agent_a)
        matchups[agent_b][agent_a] = _summarize(pair_games, agent_b)

    aggregate = {
        agent: _summarize(
            [game for game in games if agent in (game["agent_a"], game["agent_b"])],
            agent,
        )
        for agent in names
    }
    matrix = {
        agent: {
            opponent: (
                None if agent == opponent else matchups[agent][opponent]["win_rate"]
            )
            for opponent in names
        }
        for agent in names
    }
    ranking = _rank_agents(names, aggregate, matchups)
    result = {
        "schema_version": 1,
        "experiment": "pure_melon_scale_round_robin",
        "agents": names,
        "agent_paths": {
            agent: str(path.relative_to(ROOT)) for agent, path in AGENTS.items()
        },
        "agent_sha256": {agent: _file_sha256(path) for agent, path in AGENTS.items()},
        "shared_strategy_sha256": _file_sha256(
            ROOT / "agents" / "melon_scale_common.py"
        ),
        "episode_steps": 720,
        "games_per_matchup": games_per_matchup,
        "seeds": list(seeds),
        "positions_per_seed": [0, 1],
        "total_games": len(games),
        "aggregate": aggregate,
        "matchups": matchups,
        "win_rate_matrix": matrix,
        "ranking": ranking,
        "three_agent_cycles": _find_three_agent_cycles(names, matchups),
        "games": games,
    }

    stem = f"melon_scaling_round_robin_{games_per_matchup}"
    json_path = EXPERIMENTS_DIR / f"{stem}.json"
    markdown_path = EXPERIMENTS_DIR / f"{stem}.md"
    json_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    _write_markdown(markdown_path, result)

    print("\nRobustness ranking")
    for row in ranking:
        print(
            f"{row['rank']}. {row['agent']}: "
            f"W/L/T={row['wins']}/{row['losses']}/{row['ties']} "
            f"win={row['win_rate'] * 100:.2f}% "
            f"avg_money={row['average_money']:.2f} "
            f"avg_adv={row['average_money_advantage']:+.2f}"
        )
    print(f"Saved: {json_path}")
    print(f"Saved: {markdown_path}")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games-per-matchup", type=int, default=100)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be at least 1")
    run_round_robin(args.games_per_matchup, args.workers)


if __name__ == "__main__":
    main()
