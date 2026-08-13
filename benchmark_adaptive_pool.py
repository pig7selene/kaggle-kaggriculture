"""Benchmark adaptive-economy ablations against a diverse deterministic pool."""

import argparse
import json
import statistics
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from kaggle_environments import make

from benchmark import DEFAULT_WORKERS, EPISODE_STEPS, EXPERIMENTS_DIR, ROOT, _file_sha256, _load_agent


OPPONENTS = {
    "melon_scale_12": ROOT / "agents" / "melon_scale_12.py",
    "proxy_melon_heavy": ROOT / "agents" / "proxies" / "melon_heavy.py",
    "proxy_phased_rotation": ROOT / "agents" / "proxies" / "phased_rotation.py",
    "proxy_land_expander": ROOT / "agents" / "proxies" / "land_expander.py",
    "proxy_inventory_holder": ROOT / "agents" / "proxies" / "inventory_holder.py",
    "proxy_mixed_crop": ROOT / "agents" / "proxies" / "mixed_crop.py",
    "proxy_livestock_crop": ROOT / "agents" / "proxies" / "livestock_crop.py",
    "proxy_high_labor": ROOT / "agents" / "proxies" / "high_labor.py",
}
CANDIDATES = {
    "melon_scale_12": ROOT / "agents" / "melon_scale_12.py",
    "adaptive_control": ROOT / "agents" / "adaptive_control.py",
    "adaptive_a_crop": ROOT / "agents" / "adaptive_a_crop.py",
    "adaptive_b_selling": ROOT / "agents" / "adaptive_b_selling.py",
    "adaptive_c_phased": ROOT / "agents" / "adaptive_c_phased.py",
    "adaptive_d_land_labor": ROOT / "agents" / "adaptive_d_land_labor.py",
    "adaptive_e_crop_selling": ROOT / "agents" / "adaptive_e_crop_selling.py",
    "adaptive_f_full": ROOT / "agents" / "adaptive_f_full.py",
    "adaptive_g_tuned": ROOT / "agents" / "adaptive_g_tuned.py",
    "adaptive_h_hybrid": ROOT / "agents" / "adaptive_h_hybrid.py",
}
SEED_START = 8000


def _run_pool_game(job):
    candidate_name, candidate_path, opponent_name, opponent_path, seed, position = job
    candidate = _load_agent(candidate_path)
    opponent = _load_agent(opponent_path)
    agents = [opponent, opponent]
    agents[position] = candidate
    env = make(
        "kaggriculture",
        configuration={"episodeSteps": EPISODE_STEPS, "seed": seed},
        debug=True,
    )
    env.run(agents)
    final = env.steps[-1]
    statuses = [state.status for state in final]
    if len(env.steps) != EPISODE_STEPS or statuses != ["DONE", "DONE"]:
        raise RuntimeError(
            f"failed {candidate_name} vs {opponent_name}, seed={seed}, "
            f"seat={position}: turns={len(env.steps)} statuses={statuses}"
        )
    opponent_position = 1 - position
    candidate_money = float(final[position].reward)
    opponent_money = float(final[opponent_position].reward)
    return {
        "candidate": candidate_name,
        "opponent": opponent_name,
        "seed": seed,
        "candidate_position": position,
        "candidate_money": candidate_money,
        "opponent_money": opponent_money,
        "money_advantage": candidate_money - opponent_money,
    }


def _percentile(values, fraction):
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    index = fraction * (len(ordered) - 1)
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _summary(games):
    money = [game["candidate_money"] for game in games]
    opponent_money = [game["opponent_money"] for game in games]
    advantages = [game["money_advantage"] for game in games]
    wins = sum(value > 0 for value in advantages)
    losses = sum(value < 0 for value in advantages)
    ties = len(games) - wins - losses
    by_seed = {}
    for game in games:
        by_seed.setdefault(game["seed"], []).append(game["money_advantage"])
    seed_advantages = [statistics.fmean(values) for values in by_seed.values()]
    return {
        "games": len(games),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "win_rate": wins / len(games),
        "score_rate": (wins + 0.5 * ties) / len(games),
        "average_money": statistics.fmean(money),
        "median_money": statistics.median(money),
        "average_opponent_money": statistics.fmean(opponent_money),
        "average_money_advantage": statistics.fmean(advantages),
        "median_money_advantage": statistics.median(advantages),
        "worst_seed_percentile_10": _percentile(seed_advantages, 0.10),
        "money_variance": statistics.variance(money) if len(money) > 1 else 0.0,
        "money_stddev": statistics.stdev(money) if len(money) > 1 else 0.0,
        "advantage_variance": statistics.variance(advantages) if len(advantages) > 1 else 0.0,
        "advantage_stddev": statistics.stdev(advantages) if len(advantages) > 1 else 0.0,
    }


def _candidate_result(candidate, games):
    overall = _summary(games)
    matchups = {}
    for opponent in OPPONENTS:
        matchups[opponent] = _summary(
            [game for game in games if game["opponent"] == opponent]
        )
    worst = min(
        matchups.items(),
        key=lambda item: (item[1]["score_rate"], item[1]["average_money_advantage"]),
    )
    matchup_wins = sum(item["wins"] > item["losses"] for item in matchups.values())
    matchup_losses = sum(item["wins"] < item["losses"] for item in matchups.values())
    return {
        "candidate": candidate,
        "overall": overall,
        "matchups": matchups,
        "matchup_wins": matchup_wins,
        "matchup_losses": matchup_losses,
        "matchup_ties": len(matchups) - matchup_wins - matchup_losses,
        "worst_matchup": {"opponent": worst[0], **worst[1]},
    }


def _ranking(candidate_results):
    rows = list(candidate_results.values())
    rows.sort(
        key=lambda row: (
            row["matchup_wins"] - row["matchup_losses"],
            row["worst_matchup"]["score_rate"],
            row["overall"]["score_rate"],
            row["overall"]["worst_seed_percentile_10"],
            row["overall"]["average_money_advantage"],
        ),
        reverse=True,
    )
    for index, row in enumerate(rows, start=1):
        row["rank"] = index
    return rows


def _write_markdown(path, result):
    lines = [
        "# Adaptive Economy Pool Benchmark",
        "",
        f"- Seeds per opponent: {len(result['seeds'])}",
        "- Every seed is played in both positions.",
        f"- Opponents: {len(result['opponents'])}",
        f"- Games per candidate: {result['games_per_candidate']}",
        "- Worst-seed percentile is the 10th percentile of seat- and opponent-averaged money advantage by seed.",
        "",
        "| Rank | Candidate | W/L/T | Win rate | Avg money | Avg advantage | P10 seed advantage | Money SD | Matchups W/L/T | Worst matchup |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in result["ranking"]:
        overall = row["overall"]
        worst = row["worst_matchup"]
        lines.append(
            f"| {row['rank']} | {row['candidate']} | "
            f"{overall['wins']}/{overall['losses']}/{overall['ties']} | "
            f"{overall['win_rate'] * 100:.2f}% | {overall['average_money']:.2f} | "
            f"{overall['average_money_advantage']:+.2f} | "
            f"{overall['worst_seed_percentile_10']:+.2f} | "
            f"{overall['money_stddev']:.2f} | "
            f"{row['matchup_wins']}/{row['matchup_losses']}/{row['matchup_ties']} | "
            f"{worst['opponent']} ({worst['win_rate'] * 100:.1f}%, "
            f"{worst['average_money_advantage']:+.2f}) |"
        )
    lines.extend(["", "## Matchup details", ""])
    for row in result["ranking"]:
        lines.extend(
            [
                f"### {row['candidate']}",
                "",
                "| Opponent | W/L/T | Win rate | Avg money | Avg advantage | P10 seed advantage |",
                "| --- | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for opponent, item in row["matchups"].items():
            lines.append(
                f"| {opponent} | {item['wins']}/{item['losses']}/{item['ties']} | "
                f"{item['win_rate'] * 100:.1f}% | {item['average_money']:.2f} | "
                f"{item['average_money_advantage']:+.2f} | "
                f"{item['worst_seed_percentile_10']:+.2f} |"
            )
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def run_benchmark(seeds_per_opponent, workers, selected_candidates=None, stem=None):
    if seeds_per_opponent < 1:
        raise SystemExit("--seeds-per-opponent must be positive")
    candidates = CANDIDATES
    if selected_candidates:
        unknown = set(selected_candidates) - set(CANDIDATES)
        if unknown:
            raise SystemExit(f"unknown candidates: {sorted(unknown)}")
        candidates = {name: CANDIDATES[name] for name in selected_candidates}
    seeds = tuple(range(SEED_START, SEED_START + seeds_per_opponent))
    jobs = [
        (candidate, str(candidate_path), opponent, str(opponent_path), seed, position)
        for candidate, candidate_path in candidates.items()
        for opponent, opponent_path in OPPONENTS.items()
        for seed in seeds
        for position in (0, 1)
    ]
    print(
        f"Running {len(jobs)} games: {len(candidates)} candidates × "
        f"{len(OPPONENTS)} opponents × {seeds_per_opponent} seeds × 2 seats...",
        flush=True,
    )
    games = []
    if workers == 1:
        for index, job in enumerate(jobs, start=1):
            games.append(_run_pool_game(job))
            if index % 100 == 0 or index == len(jobs):
                print(f"  completed {index}/{len(jobs)}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(_run_pool_game, job) for job in jobs]
            for index, future in enumerate(as_completed(futures), start=1):
                games.append(future.result())
                if index % 100 == 0 or index == len(jobs):
                    print(f"  completed {index}/{len(jobs)}", flush=True)
    games.sort(
        key=lambda game: (
            game["candidate"], game["opponent"], game["seed"], game["candidate_position"]
        )
    )
    candidate_results = {
        candidate: _candidate_result(
            candidate, [game for game in games if game["candidate"] == candidate]
        )
        for candidate in candidates
    }
    ranking = _ranking(candidate_results)
    result = {
        "schema_version": 1,
        "experiment": "adaptive_economy_pool",
        "episode_steps": EPISODE_STEPS,
        "seeds": list(seeds),
        "positions_per_seed": [0, 1],
        "opponents": list(OPPONENTS),
        "opponent_paths": {
            name: str(path.relative_to(ROOT)) for name, path in OPPONENTS.items()
        },
        "opponent_sha256": {name: _file_sha256(path) for name, path in OPPONENTS.items()},
        "candidate_paths": {
            name: str(path.relative_to(ROOT)) for name, path in candidates.items()
        },
        "candidate_sha256": {name: _file_sha256(path) for name, path in candidates.items()},
        "games_per_candidate": len(OPPONENTS) * len(seeds) * 2,
        "candidate_results": candidate_results,
        "ranking": ranking,
        "games": games,
    }
    if stem is None:
        stem = f"adaptive_pool_{seeds_per_opponent}_seeds"
    json_path = EXPERIMENTS_DIR / f"{stem}.json"
    markdown_path = EXPERIMENTS_DIR / f"{stem}.md"
    json_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    _write_markdown(markdown_path, result)

    print("\nRobustness ranking")
    for row in ranking:
        overall = row["overall"]
        print(
            f"{row['rank']}. {row['candidate']}: "
            f"W/L/T={overall['wins']}/{overall['losses']}/{overall['ties']} "
            f"win={overall['win_rate'] * 100:.2f}% money={overall['average_money']:.2f} "
            f"adv={overall['average_money_advantage']:+.2f} "
            f"p10={overall['worst_seed_percentile_10']:+.2f} "
            f"matchups={row['matchup_wins']}/{row['matchup_losses']}/{row['matchup_ties']} "
            f"worst={row['worst_matchup']['opponent']}"
        )
    print(f"Saved: {json_path}")
    print(f"Saved: {markdown_path}")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds-per-opponent", type=int, default=16)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--candidate", action="append", dest="candidates")
    parser.add_argument("--stem")
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be at least 1")
    run_benchmark(args.seeds_per_opponent, args.workers, args.candidates, args.stem)


if __name__ == "__main__":
    main()
