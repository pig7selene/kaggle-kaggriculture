"""Run a deterministic full round robin across the six carrot scale agents."""

import argparse
import json
import statistics
from concurrent.futures import ProcessPoolExecutor, as_completed
from itertools import combinations
from pathlib import Path

from benchmark import (
    DEFAULT_WORKERS,
    EXPERIMENTS_DIR,
    ROOT,
    _file_sha256,
    _run_head_to_head_game,
)


AGENTS = {
    f"carrot_scale_{scale:02d}": ROOT / "agents" / f"carrot_scale_{scale:02d}.py"
    for scale in (4, 8, 12, 16, 20, 25)
}
SEED_START = 4000


def _run_round_robin_game(job):
    agent_a, path_a, agent_b, path_b, seed, position_a = job
    game = _run_head_to_head_game((path_a, path_b, seed, position_a))
    return {
        "agent_a": agent_a,
        "agent_b": agent_b,
        "seed": seed,
        "position_a": position_a,
        "money_a": game["candidate_final_money"],
        "money_b": game["best_final_money"],
        "advantage_a": game["money_advantage"],
    }


def _perspective(game, agent):
    if game["agent_a"] == agent:
        return game["money_a"], game["money_b"], game["advantage_a"]
    if game["agent_b"] == agent:
        return game["money_b"], game["money_a"], -game["advantage_a"]
    raise ValueError(f"{agent} did not play in game")


def _summarize(games, agent):
    outcomes = [_perspective(game, agent) for game in games]
    money = [outcome[0] for outcome in outcomes]
    opponent_money = [outcome[1] for outcome in outcomes]
    advantages = [outcome[2] for outcome in outcomes]
    wins = sum(value > 0 for value in advantages)
    losses = sum(value < 0 for value in advantages)
    ties = len(games) - wins - losses
    return {
        "games": len(games),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "win_rate": wins / len(games),
        "score_rate": (wins + 0.5 * ties) / len(games),
        "average_money": statistics.fmean(money),
        "average_opponent_money": statistics.fmean(opponent_money),
        "average_money_advantage": statistics.fmean(advantages),
        "median_money_advantage": statistics.median(advantages),
    }


def _find_three_agent_cycles(agent_names, matchups):
    def beats(first, second):
        return matchups[first][second]["wins"] > matchups[first][second]["losses"]

    cycles = []
    for first, second, third in combinations(agent_names, 3):
        if beats(first, second) and beats(second, third) and beats(third, first):
            cycles.append([first, second, third, first])
        elif beats(first, third) and beats(third, second) and beats(second, first):
            cycles.append([first, third, second, first])
    return cycles


def _rank_agents(agent_names, aggregate, matchups):
    ranking_rows = []
    for agent in agent_names:
        opponent_results = list(matchups[agent].values())
        matchup_wins = sum(item["wins"] > item["losses"] for item in opponent_results)
        matchup_losses = sum(item["wins"] < item["losses"] for item in opponent_results)
        matchup_ties = len(opponent_results) - matchup_wins - matchup_losses
        worst = min(
            matchups[agent].items(),
            key=lambda item: (item[1]["score_rate"], item[1]["average_money_advantage"]),
        )
        best = max(
            matchups[agent].items(),
            key=lambda item: (item[1]["score_rate"], item[1]["average_money_advantage"]),
        )
        ranking_rows.append(
            {
                "agent": agent,
                **aggregate[agent],
                "matchup_wins": matchup_wins,
                "matchup_losses": matchup_losses,
                "matchup_ties": matchup_ties,
                "copeland_score": matchup_wins - matchup_losses,
                "worst_matchup": {"opponent": worst[0], **worst[1]},
                "best_matchup": {"opponent": best[0], **best[1]},
            }
        )

    # Robustness first: head-to-head pool coverage (Copeland), then the weakest
    # matchup, then aggregate performance and money advantage.
    ranking_rows.sort(
        key=lambda row: (
            row["copeland_score"],
            row["worst_matchup"]["score_rate"],
            row["score_rate"],
            row["average_money_advantage"],
        ),
        reverse=True,
    )
    for rank, row in enumerate(ranking_rows, start=1):
        row["rank"] = rank
    return ranking_rows


def _matrix_markdown(agent_names, matrix, percent=False):
    labels = [name.removeprefix("carrot_scale_") for name in agent_names]
    lines = [
        "| Agent | " + " | ".join(labels) + " |",
        "| --- | " + " | ".join("---:" for _ in labels) + " |",
    ]
    for agent, label in zip(agent_names, labels):
        cells = []
        for opponent in agent_names:
            value = matrix[agent][opponent]
            if value is None:
                cells.append("—")
            elif percent:
                cells.append(f"{value * 100:.1f}%")
            else:
                cells.append(f"{value:+.2f}")
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    return lines


def _write_markdown(path, result):
    names = result["agents"]
    lines = [
        "# Carrot Scale Round Robin",
        "",
        f"- Games per matchup: {result['games_per_matchup']}",
        f"- Seeds per matchup: {len(result['seeds'])}",
        "- Both player positions are used for every seed.",
        f"- Total games: {result['total_games']}",
        "",
        "## Win-rate matrix",
        "",
        "Rows are the focal agent; columns are opponents.",
        "",
        *_matrix_markdown(names, result["win_rate_matrix"], percent=True),
        "",
        "## Average money-advantage matrix",
        "",
        *_matrix_markdown(names, result["average_advantage_matrix"]),
        "",
        "## Robustness ranking",
        "",
        "| Rank | Agent | W/L/T | Win rate | Avg money | Avg advantage | Matchups W/L/T | Worst matchup | Best matchup |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for row in result["ranking"]:
        worst = row["worst_matchup"]
        best = row["best_matchup"]
        lines.append(
            f"| {row['rank']} | {row['agent']} | "
            f"{row['wins']}/{row['losses']}/{row['ties']} | "
            f"{row['win_rate'] * 100:.2f}% | {row['average_money']:.2f} | "
            f"{row['average_money_advantage']:+.2f} | "
            f"{row['matchup_wins']}/{row['matchup_losses']}/{row['matchup_ties']} | "
            f"{worst['opponent']} ({worst['win_rate'] * 100:.1f}%, "
            f"{worst['average_money_advantage']:+.2f}) | "
            f"{best['opponent']} ({best['win_rate'] * 100:.1f}%, "
            f"{best['average_money_advantage']:+.2f}) |"
        )

    lines.extend(["", "## Pair details", ""])
    lines.extend(
        [
            "| Agent | Opponent | W/L/T | Win rate | Avg money | Avg opponent | Avg advantage |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for agent in names:
        for opponent in names:
            if agent >= opponent:
                continue
            item = result["matchups"][agent][opponent]
            lines.append(
                f"| {agent} | {opponent} | "
                f"{item['wins']}/{item['losses']}/{item['ties']} | "
                f"{item['win_rate'] * 100:.2f}% | {item['average_money']:.2f} | "
                f"{item['average_opponent_money']:.2f} | "
                f"{item['average_money_advantage']:+.2f} |"
            )

    lines.extend(["", "## Non-transitive cycles", ""])
    cycles = result["three_agent_cycles"]
    if cycles:
        lines.extend(f"- {' beats '.join(cycle)}" for cycle in cycles)
    else:
        lines.append("No directed three-agent cycles were detected.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_round_robin(games_per_matchup, workers):
    if games_per_matchup < 100 or games_per_matchup % 2:
        raise SystemExit("--games-per-matchup must be an even number of at least 100")

    agent_names = list(AGENTS)
    seeds = tuple(range(SEED_START, SEED_START + games_per_matchup // 2))
    jobs = [
        (agent_a, str(AGENTS[agent_a]), agent_b, str(AGENTS[agent_b]), seed, position)
        for agent_a, agent_b in combinations(agent_names, 2)
        for seed in seeds
        for position in (0, 1)
    ]
    print(
        f"Running {len(jobs)} games across 15 matchups "
        f"({games_per_matchup} each, {workers} workers)...",
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
            game["agent_a"],
            game["agent_b"],
            game["seed"],
            game["position_a"],
        )
    )
    matchups = {agent: {} for agent in agent_names}
    for agent_a, agent_b in combinations(agent_names, 2):
        pair_games = [
            game
            for game in games
            if game["agent_a"] == agent_a and game["agent_b"] == agent_b
        ]
        matchups[agent_a][agent_b] = _summarize(pair_games, agent_a)
        matchups[agent_b][agent_a] = _summarize(pair_games, agent_b)

    aggregate = {}
    for agent in agent_names:
        agent_games = [
            game for game in games if agent in (game["agent_a"], game["agent_b"])
        ]
        aggregate[agent] = _summarize(agent_games, agent)

    win_rate_matrix = {
        agent: {
            opponent: None if agent == opponent else matchups[agent][opponent]["win_rate"]
            for opponent in agent_names
        }
        for agent in agent_names
    }
    advantage_matrix = {
        agent: {
            opponent: (
                None
                if agent == opponent
                else matchups[agent][opponent]["average_money_advantage"]
            )
            for opponent in agent_names
        }
        for agent in agent_names
    }
    cycles = _find_three_agent_cycles(agent_names, matchups)
    ranking = _rank_agents(agent_names, aggregate, matchups)
    result = {
        "schema_version": 1,
        "experiment": "carrot_scale_round_robin",
        "agents": agent_names,
        "agent_paths": {
            agent: str(path.relative_to(ROOT)) for agent, path in AGENTS.items()
        },
        "agent_sha256": {agent: _file_sha256(path) for agent, path in AGENTS.items()},
        "shared_strategy_sha256": _file_sha256(
            ROOT / "agents" / "carrot_scale_common.py"
        ),
        "episode_steps": 720,
        "games_per_matchup": games_per_matchup,
        "seeds": list(seeds),
        "positions_per_seed": [0, 1],
        "total_games": len(games),
        "ranking_method": (
            "Copeland score, then worst-matchup score rate, overall score rate, "
            "then average money advantage"
        ),
        "aggregate": aggregate,
        "matchups": matchups,
        "win_rate_matrix": win_rate_matrix,
        "average_advantage_matrix": advantage_matrix,
        "ranking": ranking,
        "three_agent_cycles": cycles,
        "games": games,
    }

    stem = f"scaling_round_robin_{games_per_matchup}"
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
            f"avg_adv={row['average_money_advantage']:+.2f} "
            f"matchups={row['matchup_wins']}/{row['matchup_losses']}/"
            f"{row['matchup_ties']}"
        )
    print(f"Three-agent cycles: {len(cycles)}")
    print(f"Saved: {json_path}")
    print(f"Saved: {markdown_path}")
    return result


def _parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games-per-matchup", type=int, default=200)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be at least 1")
    return args


def main():
    args = _parse_args()
    run_round_robin(args.games_per_matchup, args.workers)


if __name__ == "__main__":
    main()
