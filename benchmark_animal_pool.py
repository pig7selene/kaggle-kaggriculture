"""Held-out benchmark for C0-C5 animal candidates against the frozen pool."""

import argparse
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from benchmark import DEFAULT_WORKERS, EXPERIMENTS_DIR, ROOT, _file_sha256
from benchmark_adaptive_pool import (
    OPPONENTS as FROZEN_OPPONENTS,
    _ranking,
    _run_pool_game,
    _summary,
    _write_markdown,
)


OPPONENTS = {
    **FROZEN_OPPONENTS,
    "adaptive_c_phased": ROOT / "agents" / "adaptive_c_phased.py",
}
CANDIDATES = {
    "C0_phased": ROOT / "agents" / "animal_c0_phased.py",
    "C1_geese": ROOT / "agents" / "animal_c1_geese.py",
    "C2_cows": ROOT / "agents" / "animal_c2_cows.py",
    "C3_sheep": ROOT / "agents" / "animal_c3_sheep.py",
    "C4_tuned_cows": ROOT / "agents" / "animal_c4_tuned_cows.py",
    "C5_adaptive": ROOT / "agents" / "animal_c5_adaptive.py",
}


def _candidate_result(candidate, games):
    overall = _summary(games)
    matchups = {
        opponent: _summary([game for game in games if game["opponent"] == opponent])
        for opponent in OPPONENTS
    }
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


def run_benchmark(seed_start, seeds_per_opponent, workers, selected, stem):
    candidates = CANDIDATES
    if selected:
        unknown = sorted(set(selected) - set(CANDIDATES))
        if unknown:
            raise ValueError(f"unknown candidates: {unknown}")
        candidates = {name: CANDIDATES[name] for name in selected}
    seeds = list(range(seed_start, seed_start + seeds_per_opponent))
    jobs = [
        (candidate, str(candidate_path), opponent, str(opponent_path), seed, seat)
        for candidate, candidate_path in candidates.items()
        for opponent, opponent_path in OPPONENTS.items()
        for seed in seeds
        for seat in (0, 1)
    ]
    games = []
    if workers == 1:
        for index, job in enumerate(jobs, 1):
            games.append(_run_pool_game(job))
            if index % 100 == 0 or index == len(jobs):
                print(f"completed {index}/{len(jobs)}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(_run_pool_game, job) for job in jobs]
            for index, future in enumerate(as_completed(futures), 1):
                games.append(future.result())
                if index % 100 == 0 or index == len(jobs):
                    print(f"completed {index}/{len(jobs)}", flush=True)
    games.sort(
        key=lambda game: (
            game["candidate"], game["opponent"], game["seed"], game["candidate_position"]
        )
    )
    results = {
        candidate: _candidate_result(
            candidate, [game for game in games if game["candidate"] == candidate]
        )
        for candidate in candidates
    }
    ranking = _ranking(results)
    result = {
        "schema_version": 1,
        "experiment": "animal_candidate_pool",
        "episode_steps": 720,
        "seeds": seeds,
        "positions_per_seed": [0, 1],
        "opponents": list(OPPONENTS),
        "opponent_paths": {name: str(path.relative_to(ROOT)) for name, path in OPPONENTS.items()},
        "opponent_sha256": {name: _file_sha256(path) for name, path in OPPONENTS.items()},
        "candidate_paths": {name: str(path.relative_to(ROOT)) for name, path in candidates.items()},
        "candidate_sha256": {name: _file_sha256(path) for name, path in candidates.items()},
        "games_per_candidate": len(OPPONENTS) * len(seeds) * 2,
        "candidate_results": results,
        "ranking": ranking,
        "games": games,
    }
    json_path = EXPERIMENTS_DIR / f"{stem}.json"
    md_path = EXPERIMENTS_DIR / f"{stem}.md"
    json_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    _write_markdown(md_path, result)
    for row in ranking:
        overall = row["overall"]
        livestock = results[row["candidate"]]["matchups"]["proxy_livestock_crop"]
        print(
            f"{row['rank']}. {row['candidate']}: "
            f"{overall['wins']}/{overall['losses']}/{overall['ties']} "
            f"win={overall['win_rate'] * 100:.2f}% money={overall['average_money']:.2f} "
            f"adv={overall['average_money_advantage']:+.2f} "
            f"p10={overall['worst_seed_percentile_10']:+.2f} "
            f"livestock={livestock['wins']}/{livestock['losses']}/{livestock['ties']} "
            f"{livestock['average_money_advantage']:+.2f}"
        )
    print(f"Saved {json_path}")
    print(f"Saved {md_path}")
    return result


def resummarize(json_path):
    result = json.loads(json_path.read_text(encoding="utf-8"))
    candidates = list(result["candidate_paths"])
    result["candidate_results"] = {
        candidate: _candidate_result(
            candidate,
            [game for game in result["games"] if game["candidate"] == candidate],
        )
        for candidate in candidates
    }
    result["ranking"] = _ranking(result["candidate_results"])
    json_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    _write_markdown(json_path.with_suffix(".md"), result)
    print(f"Resummarized {json_path}")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-start", type=int, default=8700)
    parser.add_argument("--seeds-per-opponent", type=int, default=16)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--candidate", action="append", dest="candidates")
    parser.add_argument("--stem", default="animal_pool_heldout_16_seeds")
    parser.add_argument("--from-json", type=Path)
    args = parser.parse_args()
    if args.from_json:
        resummarize(args.from_json)
        return
    run_benchmark(
        args.seed_start,
        args.seeds_per_opponent,
        args.workers,
        args.candidates,
        args.stem,
    )


if __name__ == "__main__":
    main()
