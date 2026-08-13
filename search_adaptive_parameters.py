"""Systematic held-out parameter search for the adaptive economic engine."""

import argparse
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from runpy import run_path

from kaggle_environments import make

from benchmark import DEFAULT_WORKERS, EPISODE_STEPS, EXPERIMENTS_DIR, ROOT, _load_agent
from benchmark_adaptive_pool import OPPONENTS, _summary


SEARCH_OPPONENTS = {
    name: OPPONENTS[name]
    for name in (
        "melon_scale_12",
        "proxy_melon_heavy",
        "proxy_phased_rotation",
        "proxy_livestock_crop",
        "proxy_high_labor",
    )
}
SEARCH_SEED_START = 8500


def _variants():
    variants = {
        "base_adaptive_selling": {
            "crop_mode": "adaptive", "selling": "aware",
        },
        "phase_weighted": {
            "crop_mode": "adaptive", "selling": "aware", "phased_weights": True,
        },
    }
    # Joint crop-concentration × selling-threshold grid.
    for melon_limit in (0.50, 0.67, 0.84):
        for premium_threshold in (0.85, 0.95, 1.05):
            variants[f"allocation_{melon_limit:.2f}_sell_{premium_threshold:.2f}"] = {
                "crop_mode": "adaptive",
                "selling": "aware",
                "allocation_limits": {"MELON": melon_limit},
                "premium_sell_threshold": premium_threshold,
            }
    # Inventory reserve and forced-liquidation timing grid.
    for reserve in (40, 70):
        for liquidation in (600, 672):
            variants[f"reserve_{reserve}_liquidate_{liquidation}"] = {
                "crop_mode": "adaptive",
                "selling": "aware",
                "reserve_level": reserve,
                "overflow_trigger": reserve + 20,
                "liquidation_step": liquidation,
            }
    # Land scale, ROI hurdle, and workload capacity grid. Each combination is
    # evaluated by exactly the same seeds and opponents as the no-land cases.
    for max_plots, hurdle, plots_per_worker in (
        (24, 1.25, 7),
        (24, 1.75, 9),
        (24, 2.25, 11),
        (36, 1.25, 7),
        (36, 1.75, 9),
        (36, 2.25, 11),
    ):
        variants[f"land_{max_plots}_hurdle_{hurdle:.2f}_labor_{plots_per_worker}"] = {
            "crop_mode": "adaptive",
            "selling": "aware",
            "enable_land": True,
            "dynamic_labor": True,
            "max_plots": max_plots,
            "land_hurdle": hurdle,
            "plots_per_worker": plots_per_worker,
            "phased_weights": True,
        }
    # Forecast sensitivity isolates whether holding responds too strongly or
    # weakly to projected town/opponent flows.
    for ratio in (0.90, 0.98, 1.06):
        variants[f"forecast_ratio_{ratio:.2f}"] = {
            "crop_mode": "adaptive",
            "selling": "aware",
            "forecast_sell_ratio": ratio,
        }
    for threshold, ratio in ((1.00, 1.05), (1.10, 1.05), (1.20, 1.10)):
        variants[f"hold_threshold_{threshold:.2f}_forecast_{ratio:.2f}"] = {
            "crop_mode": "adaptive",
            "selling": "aware",
            "sell_threshold": threshold,
            "premium_sell_threshold": threshold,
            "forecast_sell_ratio": ratio,
            "overflow_trigger": 88,
            "reserve_level": 65,
        }
    for day in (11, 14):
        variants[f"land_forced_day_{day}"] = {
            "crop_mode": "adaptive",
            "selling": "aware",
            "forced_land_days": (day,),
            "max_plots": 24,
            "dynamic_labor": True,
            "plots_per_worker": 9,
            "phased_weights": True,
        }
    for strawberry_bias in (1.25, 1.60, 2.00, 2.50):
        for melon_bias in (0.70, 0.90, 1.10):
            variants[
                f"phase_mid_strawberry_{strawberry_bias:.2f}_melon_{melon_bias:.2f}"
            ] = {
                "crop_mode": "adaptive",
                "selling": "aware",
                "phased_weights": True,
                "phase_biases": {
                    "early": {"MELON": 1.40},
                    "mid": {
                        "MELON": melon_bias,
                        "STRAWBERRY": strawberry_bias,
                        "TOMATO": 1.05,
                    },
                    "late": {"WHEAT": 1.50, "CARROT": 1.20},
                },
            }
    for deviation in (1.00, 1.15, 1.30, 1.50, 2.00):
        variants[f"hybrid_override_{deviation:.2f}"] = {
            "crop_mode": "hybrid",
            "phase_schedule": ((0, "MELON"), (11, "STRAWBERRY"), (21, "WHEAT")),
            "hybrid_deviation": deviation,
            "selling": "aware",
            "allocation_limits": {
                "MELON": 1.00,
                "STRAWBERRY": 1.00,
                "TOMATO": 0.34,
                "CARROT": 1.00,
                "WHEAT": 1.00,
            },
        }
    return variants


VARIANTS = _variants()


def _run_search_game(job):
    variant, config, opponent_name, opponent_path, seed, position = job
    make_agent = run_path(str(ROOT / "agents" / "economic_common.py"))["make_agent"]
    candidate = make_agent(config)
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
            f"failed variant={variant} opponent={opponent_name} seed={seed} "
            f"seat={position}: turns={len(env.steps)} statuses={statuses}"
        )
    other = 1 - position
    candidate_money = float(final[position].reward)
    opponent_money = float(final[other].reward)
    return {
        "variant": variant,
        "opponent": opponent_name,
        "seed": seed,
        "candidate_position": position,
        "candidate_money": candidate_money,
        "opponent_money": opponent_money,
        "money_advantage": candidate_money - opponent_money,
    }


def _variant_result(name, games):
    overall = _summary(games)
    matchups = {
        opponent: _summary([game for game in games if game["opponent"] == opponent])
        for opponent in SEARCH_OPPONENTS
    }
    worst = min(
        matchups.items(),
        key=lambda item: (item[1]["score_rate"], item[1]["average_money_advantage"]),
    )
    wins = sum(item["wins"] > item["losses"] for item in matchups.values())
    losses = sum(item["wins"] < item["losses"] for item in matchups.values())
    return {
        "variant": name,
        "config": VARIANTS[name],
        "overall": overall,
        "matchups": matchups,
        "matchup_wins": wins,
        "matchup_losses": losses,
        "matchup_ties": len(matchups) - wins - losses,
        "worst_matchup": {"opponent": worst[0], **worst[1]},
    }


def run_search(seeds_per_opponent, workers, selected_variants=None, stem=None):
    variants = VARIANTS
    if selected_variants:
        unknown = set(selected_variants) - set(VARIANTS)
        if unknown:
            raise SystemExit(f"unknown variants: {sorted(unknown)}")
        variants = {name: VARIANTS[name] for name in selected_variants}
    seeds = tuple(range(SEARCH_SEED_START, SEARCH_SEED_START + seeds_per_opponent))
    jobs = [
        (variant, config, opponent, str(path), seed, position)
        for variant, config in variants.items()
        for opponent, path in SEARCH_OPPONENTS.items()
        for seed in seeds
        for position in (0, 1)
    ]
    print(
        f"Running {len(jobs)} parameter-search games: {len(variants)} variants × "
        f"{len(SEARCH_OPPONENTS)} opponents × {len(seeds)} seeds × 2 seats...",
        flush=True,
    )
    games = []
    if workers == 1:
        for index, job in enumerate(jobs, start=1):
            games.append(_run_search_game(job))
            if index % 100 == 0 or index == len(jobs):
                print(f"  completed {index}/{len(jobs)}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(_run_search_game, job) for job in jobs]
            for index, future in enumerate(as_completed(futures), start=1):
                games.append(future.result())
                if index % 100 == 0 or index == len(jobs):
                    print(f"  completed {index}/{len(jobs)}", flush=True)
    games.sort(
        key=lambda game: (
            game["variant"], game["opponent"], game["seed"], game["candidate_position"]
        )
    )
    results = {
        variant: _variant_result(
            variant, [game for game in games if game["variant"] == variant]
        )
        for variant in variants
    }
    ranking = list(results.values())
    ranking.sort(
        key=lambda row: (
            row["matchup_wins"] - row["matchup_losses"],
            row["worst_matchup"]["score_rate"],
            row["overall"]["score_rate"],
            row["overall"]["worst_seed_percentile_10"],
            row["overall"]["average_money_advantage"],
        ),
        reverse=True,
    )
    for rank, row in enumerate(ranking, start=1):
        row["rank"] = rank
    result = {
        "schema_version": 1,
        "experiment": "adaptive_parameter_search",
        "episode_steps": EPISODE_STEPS,
        "seeds": list(seeds),
        "positions_per_seed": [0, 1],
        "opponents": list(SEARCH_OPPONENTS),
        "variants": variants,
        "games_per_variant": len(SEARCH_OPPONENTS) * len(seeds) * 2,
        "results": results,
        "ranking": ranking,
        "games": games,
    }
    if stem is None:
        stem = "adaptive_parameter_search"
    json_path = EXPERIMENTS_DIR / f"{stem}.json"
    json_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("\nTop parameter variants")
    for row in ranking[:10]:
        overall = row["overall"]
        print(
            f"{row['rank']}. {row['variant']}: "
            f"W/L/T={overall['wins']}/{overall['losses']}/{overall['ties']} "
            f"win={overall['win_rate'] * 100:.2f}% money={overall['average_money']:.2f} "
            f"adv={overall['average_money_advantage']:+.2f} "
            f"p10={overall['worst_seed_percentile_10']:+.2f} "
            f"matchups={row['matchup_wins']}/{row['matchup_losses']}/{row['matchup_ties']}"
        )
    print(f"Saved: {json_path}")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds-per-opponent", type=int, default=4)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--variant", action="append", dest="variants")
    parser.add_argument("--stem")
    args = parser.parse_args()
    if args.seeds_per_opponent < 1:
        parser.error("--seeds-per-opponent must be positive")
    if args.workers < 1:
        parser.error("--workers must be positive")
    run_search(args.seeds_per_opponent, args.workers, args.variants, args.stem)


if __name__ == "__main__":
    main()
