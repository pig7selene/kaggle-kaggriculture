"""Reproducible multi-seed benchmarks for Kaggriculture agents.

Quick (100 games):
    python benchmark.py --mode quick

Full (600 games):
    python benchmark.py --mode full
"""

import argparse
import hashlib
import importlib.util
import json
import math
import os
import random
import statistics
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

try:
    from kaggle_environments import make
except ImportError as exc:  # pragma: no cover - only used on an unprepared machine
    raise SystemExit(
        "Missing dependency. Install it with: pip install -U kaggle-environments"
    ) from exc


ROOT = Path(__file__).resolve().parent
DEFAULT_AGENT = ROOT / "agents" / "baseline_carrot.py"
EXPERIMENTS_DIR = ROOT / "experiments"
CURRENT_BEST_REGISTRY = EXPERIMENTS_DIR / "current_best.json"
EPISODE_STEPS = 720
DEFAULT_WORKERS = min(4, os.cpu_count() or 1)

# Full mode is a strict superset of quick mode. Every seed is evaluated with
# the candidate in both player positions.
SEED_SETS = {
    "quick": {
        "starter": tuple(range(1000, 1040)),  # 40 seeds x 2 seats = 80 games
        "random": tuple(range(2000, 2010)),   # 10 seeds x 2 seats = 20 games
    },
    "full": {
        "starter": tuple(range(1000, 1250)),  # 250 seeds x 2 = 500 games
        "random": tuple(range(2000, 2050)),   # 50 seeds x 2 = 100 games
    },
}

# Candidate-vs-best suites use the same seed in both seat assignments. The
# paired outcomes are also used to calculate a confidence interval for
# promotion decisions.
HEAD_TO_HEAD_SEEDS = {
    "quick": tuple(range(3000, 3050)),   # 50 seeds x 2 seats = 100 games
    "full": tuple(range(3000, 3300)),    # 300 seeds x 2 seats = 600 games
}

_AGENT_CACHE = {}


def _current_best():
    """Return the registered best agent, falling back to the initial baseline."""
    if CURRENT_BEST_REGISTRY.is_file():
        registry = json.loads(CURRENT_BEST_REGISTRY.read_text(encoding="utf-8"))
        path = ROOT / registry["agent_path"]
        if path.is_file():
            return path, registry["agent_version"]
    return DEFAULT_AGENT, "baseline_carrot_v1"


class SeededBuiltinRandom:
    """Deterministic equivalent of the bundled `random` opponent.

    The installed built-in creates an unseeded ``random.Random`` every turn,
    which makes fixed environment seeds insufficient for reproducibility. This
    class preserves that agent's choices and probabilities while using one RNG
    seeded from the episode seed.
    """

    crop_costs = {
        "WHEAT": 10,
        "CARROT": 20,
        "TOMATO": 50,
        "STRAWBERRY": 100,
        "MELON": 80,
    }
    farmer_ops = ("NORTH", "SOUTH", "EAST", "WEST", "WATER", "HARVEST", "PASS")

    def __init__(self, seed):
        self.rng = random.Random(seed)

    def __call__(self, obs, configuration=None):
        farms = obs.get("farms", [])
        player = obs.get("player", 0)
        private = obs.get("private", {}) or {}
        farm = farms[player] if farms and player < len(farms) else None
        if farm is None:
            return {"farmer": ["PASS"], "hands": [], "market": []}

        market = []
        affordable = [
            crop for crop, cost in self.crop_costs.items() if cost <= farm["money"]
        ]
        if affordable and self.rng.random() < 0.1:
            market.append(["BUY_SEED", self.rng.choice(affordable), 1])

        seeds = private.get("seeds", {})
        available = [crop for crop, count in seeds.items() if count > 0]
        if available and self.rng.random() < 0.3:
            farmer = ["PLANT", self.rng.choice(available)]
        else:
            farmer = [self.rng.choice(self.farmer_ops)]

        hands = [[self.rng.choice(self.farmer_ops)] for _ in farm.get("hands", [])]
        return {"farmer": farmer, "hands": hands, "market": market}


def _file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_agent(agent_path):
    """Load and cache an agent function inside each benchmark worker."""
    if agent_path in _AGENT_CACHE:
        return _AGENT_CACHE[agent_path]

    path = Path(agent_path)
    module_name = f"bench_agent_{hashlib.sha256(agent_path.encode()).hexdigest()[:12]}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load agent module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    candidate = getattr(module, "agent", None)
    if not callable(candidate):
        raise RuntimeError(f"{path} does not define a callable agent(obs)")
    _AGENT_CACHE[agent_path] = candidate
    return candidate


def _run_game(job):
    """Run one game; designed as a top-level function for process workers."""
    agent_path, opponent, seed, player_position = job
    candidate = _load_agent(agent_path)
    opponent_agent = "starter" if opponent == "starter" else SeededBuiltinRandom(seed)
    agents = [opponent_agent, opponent_agent]
    agents[player_position] = candidate

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
            f"failed game opponent={opponent} seed={seed} seat={player_position}: "
            f"turns={len(env.steps)} statuses={statuses}"
        )

    money = [float(state.reward) for state in final]
    opponent_position = 1 - player_position
    return {
        "opponent": opponent,
        "seed": seed,
        "player_position": player_position,
        "final_money": money[player_position],
        "opponent_money": money[opponent_position],
        "money_advantage": money[player_position] - money[opponent_position],
    }


def _run_head_to_head_game(job):
    """Run one candidate-vs-best game on a specified seat and seed."""
    candidate_path, best_path, seed, candidate_position = job
    candidate = _load_agent(candidate_path)
    best = _load_agent(best_path)
    agents = [best, best]
    agents[candidate_position] = candidate

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
            f"failed head-to-head game seed={seed} seat={candidate_position}: "
            f"turns={len(env.steps)} statuses={statuses}"
        )

    money = [float(state.reward) for state in final]
    best_position = 1 - candidate_position
    return {
        "seed": seed,
        "candidate_position": candidate_position,
        "candidate_final_money": money[candidate_position],
        "best_final_money": money[best_position],
        "money_advantage": money[candidate_position] - money[best_position],
    }


def _summary(games):
    final_money = [game["final_money"] for game in games]
    opponent_money = [game["opponent_money"] for game in games]
    advantages = [game["money_advantage"] for game in games]
    wins = sum(value > 0 for value in advantages)
    losses = sum(value < 0 for value in advantages)
    ties = len(games) - wins - losses
    return {
        "games": len(games),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "win_rate": wins / len(games),
        "average_final_money": statistics.fmean(final_money),
        "median_final_money": statistics.median(final_money),
        "average_opponent_money": statistics.fmean(opponent_money),
        "average_money_advantage": statistics.fmean(advantages),
        "min_final_money": min(final_money),
        "max_final_money": max(final_money),
    }


def _head_to_head_summary(games):
    candidate_money = [game["candidate_final_money"] for game in games]
    best_money = [game["best_final_money"] for game in games]
    advantages = [game["money_advantage"] for game in games]
    wins = sum(value > 0 for value in advantages)
    losses = sum(value < 0 for value in advantages)
    ties = len(games) - wins - losses

    by_seed = {}
    for game in games:
        by_seed.setdefault(game["seed"], []).append(game["money_advantage"])
    if any(len(values) != 2 for values in by_seed.values()):
        raise RuntimeError("head-to-head results must contain both seats per seed")
    paired_advantages = [statistics.fmean(by_seed[seed]) for seed in sorted(by_seed)]
    paired_mean = statistics.fmean(paired_advantages)
    if len(paired_advantages) > 1:
        margin = 1.96 * statistics.stdev(paired_advantages) / math.sqrt(
            len(paired_advantages)
        )
    else:
        margin = 0.0
    ci_low = paired_mean - margin
    ci_high = paired_mean + margin

    return {
        "games": len(games),
        "seeds": len(by_seed),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "win_rate": wins / len(games),
        "average_candidate_final_money": statistics.fmean(candidate_money),
        "average_best_final_money": statistics.fmean(best_money),
        "average_money_advantage": statistics.fmean(advantages),
        "median_advantage": statistics.median(advantages),
        "paired_seed_average_advantage": paired_mean,
        "paired_seed_advantage_ci_95": [ci_low, ci_high],
        "reliable_improvement": paired_mean > 0 and ci_low > 0,
    }


def _build_jobs(agent_path, mode):
    return [
        (str(agent_path), opponent, seed, position)
        for opponent, seeds in SEED_SETS[mode].items()
        for seed in seeds
        for position in (0, 1)
    ]


def _print_summary(label, summary):
    print(
        f"{label:<18} "
        f"games={summary['games']:>3}  "
        f"W/L/T={summary['wins']}/{summary['losses']}/{summary['ties']}  "
        f"win={summary['win_rate'] * 100:>6.2f}%  "
        f"money avg/med={summary['average_final_money']:.2f}/"
        f"{summary['median_final_money']:.2f}  "
        f"opp avg={summary['average_opponent_money']:.2f}  "
        f"adv={summary['average_money_advantage']:+.2f}  "
        f"min/max={summary['min_final_money']:.2f}/{summary['max_final_money']:.2f}"
    )


def _print_head_to_head_summary(candidate_version, best_version, summary):
    ci_low, ci_high = summary["paired_seed_advantage_ci_95"]
    print(f"\nHead-to-head: {candidate_version} vs {best_version}")
    print(
        f"games={summary['games']} seeds={summary['seeds']} "
        f"W/L/T={summary['wins']}/{summary['losses']}/{summary['ties']} "
        f"win={summary['win_rate'] * 100:.2f}%"
    )
    print(
        f"candidate avg={summary['average_candidate_final_money']:.2f} "
        f"best avg={summary['average_best_final_money']:.2f} "
        f"adv avg/median={summary['average_money_advantage']:+.2f}/"
        f"{summary['median_advantage']:+.2f}"
    )
    print(
        f"paired-seed advantage 95% CI=[{ci_low:+.2f}, {ci_high:+.2f}] "
        f"reliable improvement={'YES' if summary['reliable_improvement'] else 'NO'}"
    )


def run_benchmark(agent_path, agent_version, mode, workers, output_path=None):
    agent_path = agent_path.resolve()
    if not agent_path.is_file():
        raise SystemExit(f"agent file does not exist: {agent_path}")

    jobs = _build_jobs(agent_path, mode)
    games = []
    print(
        f"Running {len(jobs)} games for {agent_version} "
        f"({mode}, {workers} worker{'s' if workers != 1 else ''})...",
        flush=True,
    )
    if workers == 1:
        for index, job in enumerate(jobs, start=1):
            games.append(_run_game(job))
            if index % 10 == 0 or index == len(jobs):
                print(f"  completed {index}/{len(jobs)}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(_run_game, job) for job in jobs]
            for index, future in enumerate(as_completed(futures), start=1):
                games.append(future.result())
                if index % 10 == 0 or index == len(jobs):
                    print(f"  completed {index}/{len(jobs)}", flush=True)

    games.sort(key=lambda game: (game["opponent"], game["seed"], game["player_position"]))
    summaries = {}
    for opponent in SEED_SETS[mode]:
        opponent_games = [game for game in games if game["opponent"] == opponent]
        summaries[opponent] = _summary(opponent_games)
        for position in (0, 1):
            seat_games = [
                game for game in opponent_games if game["player_position"] == position
            ]
            summaries[f"{opponent}_player_{position}"] = _summary(seat_games)
    summaries["overall"] = _summary(games)

    result = {
        "schema_version": 1,
        "agent_version": agent_version,
        "agent_path": str(agent_path.relative_to(ROOT)),
        "agent_sha256": _file_sha256(agent_path),
        "mode": mode,
        "episode_steps": EPISODE_STEPS,
        "seed_sets": {key: list(value) for key, value in SEED_SETS[mode].items()},
        "positions_per_seed": [0, 1],
        "random_opponent": (
            "deterministic seeded equivalent of the bundled random agent"
        ),
        "summaries": summaries,
        "games": games,
    }

    print("\nResults")
    for opponent in SEED_SETS[mode]:
        _print_summary(opponent, summaries[opponent])
        _print_summary(f"{opponent} as P0", summaries[f"{opponent}_player_0"])
        _print_summary(f"{opponent} as P1", summaries[f"{opponent}_player_1"])
    _print_summary("overall", summaries["overall"])

    if output_path is None:
        output_path = EXPERIMENTS_DIR / f"{agent_version}_{mode}.json"
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"\nSaved: {output_path}")
    return result


def run_head_to_head(
    agent_path,
    agent_version,
    best_agent_path,
    best_version,
    mode,
    workers,
    output_path=None,
):
    """Benchmark a candidate against the current best on paired seats/seeds."""
    agent_path = agent_path.resolve()
    best_agent_path = best_agent_path.resolve()
    for label, path in (("candidate", agent_path), ("best agent", best_agent_path)):
        if not path.is_file():
            raise SystemExit(f"{label} file does not exist: {path}")

    jobs = [
        (str(agent_path), str(best_agent_path), seed, position)
        for seed in HEAD_TO_HEAD_SEEDS[mode]
        for position in (0, 1)
    ]
    games = []
    print(
        f"Running {len(jobs)} head-to-head games: {agent_version} vs "
        f"{best_version} ({mode}, {workers} worker{'s' if workers != 1 else ''})...",
        flush=True,
    )
    if workers == 1:
        for index, job in enumerate(jobs, start=1):
            games.append(_run_head_to_head_game(job))
            if index % 10 == 0 or index == len(jobs):
                print(f"  completed {index}/{len(jobs)}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(_run_head_to_head_game, job) for job in jobs]
            for index, future in enumerate(as_completed(futures), start=1):
                games.append(future.result())
                if index % 10 == 0 or index == len(jobs):
                    print(f"  completed {index}/{len(jobs)}", flush=True)

    games.sort(key=lambda game: (game["seed"], game["candidate_position"]))
    summary = _head_to_head_summary(games)
    result = {
        "schema_version": 1,
        "benchmark_type": "head_to_head",
        "candidate_version": agent_version,
        "candidate_path": str(agent_path.relative_to(ROOT)),
        "candidate_sha256": _file_sha256(agent_path),
        "best_version": best_version,
        "best_path": str(best_agent_path.relative_to(ROOT)),
        "best_sha256": _file_sha256(best_agent_path),
        "mode": mode,
        "episode_steps": EPISODE_STEPS,
        "seeds": list(HEAD_TO_HEAD_SEEDS[mode]),
        "positions_per_seed": [0, 1],
        "summary": summary,
        "games": games,
    }
    _print_head_to_head_summary(agent_version, best_version, summary)

    if output_path is None:
        output_path = EXPERIMENTS_DIR / (
            f"{agent_version}_vs_{best_version}_{mode}.json"
        )
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Saved: {output_path}")
    return result


def _parse_args():
    current_best_path, current_best_version = _current_best()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=sorted(SEED_SETS), default="quick")
    parser.add_argument("--agent", type=Path, default=DEFAULT_AGENT)
    parser.add_argument("--agent-version", default="baseline_carrot_v1")
    parser.add_argument(
        "--head-to-head",
        action="store_true",
        help="compare --agent against --best-agent on paired seeds and seats",
    )
    parser.add_argument("--best-agent", type=Path, default=current_best_path)
    parser.add_argument("--best-version", default=current_best_version)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be at least 1")
    return args


def main():
    args = _parse_args()
    if args.head_to_head:
        run_head_to_head(
            agent_path=args.agent,
            agent_version=args.agent_version,
            best_agent_path=args.best_agent,
            best_version=args.best_version,
            mode=args.mode,
            workers=args.workers,
            output_path=args.output,
        )
    else:
        run_benchmark(
            agent_path=args.agent,
            agent_version=args.agent_version,
            mode=args.mode,
            workers=args.workers,
            output_path=args.output,
        )


if __name__ == "__main__":
    main()
