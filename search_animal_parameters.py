"""Systematic staged search for animal policies on the phased crop baseline."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from runpy import run_path

from kaggle_environments import make

from benchmark import DEFAULT_WORKERS, ROOT, _load_agent


OPPONENTS = {
    "adaptive_c_phased": ROOT / "agents" / "adaptive_c_phased.py",
    "proxy_livestock_crop": ROOT / "agents" / "proxies" / "livestock_crop.py",
    "proxy_high_labor": ROOT / "agents" / "proxies" / "high_labor.py",
    "proxy_phased_rotation": ROOT / "agents" / "proxies" / "phased_rotation.py",
    "proxy_melon_heavy": ROOT / "agents" / "proxies" / "melon_heavy.py",
}

PHASED = {
    "crop_mode": "phased",
    "phase_schedule": ((0, "MELON"), (11, "STRAWBERRY"), (21, "WHEAT")),
    "selling": "immediate",
}

ANIMAL_BASE = {
    **PHASED,
    "animal_count": 4,
    "animal_start_day": 11,
    "structure_start_day": 0,
    "animal_region": "NW",
    "animal_clear_weeds": True,
    "animal_payback_hurdle": 0.0,
    "animal_workers": 2,
    "feed_policy": "daily",
    "care_policy": "daily",
    "fertilizer_policy": "collect",
    "animal_harvest_threshold": 1,
    "wheat_policy": "market",
    "wheat_reserve_days": 2,
    "animal_selling": "aware",
    "animal_sell_threshold": 0.92,
    "animal_premium_sell_threshold": 0.90,
    "animal_hold_days": 3,
    "animal_endgame_priority": True,
    "endgame_return_hour": 12,
}


def _run_game(job):
    name, config, opponent_name, opponent_path, seed, seat = job
    make_agent = run_path(str(ROOT / "agents" / "economic_common.py"))["make_agent"]
    candidate = make_agent(config)
    opponent = _load_agent(str(opponent_path))
    agents = [opponent, opponent]
    agents[seat] = candidate
    env = make(
        "kaggriculture",
        configuration={"episodeSteps": 720, "seed": seed},
        debug=True,
    )
    env.run(agents)
    final = env.steps[-1]
    if len(env.steps) != 720 or [state.status for state in final] != ["DONE", "DONE"]:
        raise RuntimeError(f"failed {name} vs {opponent_name} seed={seed} seat={seat}")
    candidate_money = float(final[seat].reward)
    opponent_money = float(final[1 - seat].reward)
    return {
        "variant": name,
        "opponent": opponent_name,
        "seed": seed,
        "seat": seat,
        "candidate_money": candidate_money,
        "opponent_money": opponent_money,
        "advantage": candidate_money - opponent_money,
    }


def _percentile(values, fraction):
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    index = fraction * (len(ordered) - 1)
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _summarize(games):
    advantages = [game["advantage"] for game in games]
    money = [game["candidate_money"] for game in games]
    wins = sum(value > 0 for value in advantages)
    losses = sum(value < 0 for value in advantages)
    ties = len(games) - wins - losses
    by_seed = {}
    for game in games:
        by_seed.setdefault(game["seed"], []).append(game["advantage"])
    seed_advantages = [statistics.fmean(values) for values in by_seed.values()]
    return {
        "games": len(games),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "win_rate": wins / len(games),
        "average_money": statistics.fmean(money),
        "average_advantage": statistics.fmean(advantages),
        "p10_advantage": _percentile(seed_advantages, 0.10),
        "variance": statistics.pvariance(money),
        "standard_deviation": statistics.pstdev(money),
    }


def _variant_result(name, config, games):
    matchups = {
        opponent: _summarize([game for game in games if game["opponent"] == opponent])
        for opponent in OPPONENTS
    }
    overall = _summarize(games)
    worst = min(matchups, key=lambda opponent: matchups[opponent]["average_advantage"])
    livestock = matchups["proxy_livestock_crop"]
    # Search score values pool income and downside, with explicit weight on the
    # known livestock gap.  Final selection still uses held-out constraints.
    search_score = (
        overall["average_advantage"]
        + 0.25 * overall["p10_advantage"]
        + 0.35 * livestock["average_advantage"]
        + 0.10 * matchups[worst]["average_advantage"]
    )
    return {
        "variant": name,
        "config": config,
        "overall": overall,
        "matchups": matchups,
        "worst_opponent": worst,
        "search_score": search_score,
    }


def _evaluate(variants, seeds, workers, stage):
    jobs = [
        (name, config, opponent, path, seed, seat)
        for name, config in variants.items()
        for opponent, path in OPPONENTS.items()
        for seed in seeds
        for seat in (0, 1)
    ]
    games = []
    if workers == 1:
        for index, job in enumerate(jobs, 1):
            games.append(_run_game(job))
            if index % 100 == 0 or index == len(jobs):
                print(f"{stage}: {index}/{len(jobs)}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(_run_game, job) for job in jobs]
            for index, future in enumerate(as_completed(futures), 1):
                games.append(future.result())
                if index % 100 == 0 or index == len(jobs):
                    print(f"{stage}: {index}/{len(jobs)}", flush=True)
    results = [
        _variant_result(
            name,
            config,
            [game for game in games if game["variant"] == name],
        )
        for name, config in variants.items()
    ]
    results.sort(key=lambda row: row["search_score"], reverse=True)
    return {"stage": stage, "variants": results, "games": games}


def _screen_variants():
    variants = {"C0_phased": dict(PHASED)}
    for animal in ("GOOSE", "COW", "SHEEP"):
        only = dict(ANIMAL_BASE)
        only.update(
            {
                "animal_type": animal,
                "animal_start_day": 0,
                "base_plots": 0,
                "max_plots": 8,
                "wheat_policy": "market",
            }
        )
        variants[f"{animal.lower()}_only"] = only
        hybrid = dict(ANIMAL_BASE)
        hybrid["animal_type"] = animal
        variants[f"phased_{animal.lower()}_default"] = hybrid
    for animal in ("GOOSE", "COW", "SHEEP"):
        for count in (1, 2, 4, 6):
            for start_day in (0, 5, 11, 13, 15):
                config = dict(ANIMAL_BASE)
                config.update(
                    {
                        "animal_type": animal,
                        "animal_count": count,
                        "animal_start_day": start_day,
                        "animal_workers": 1 if count <= 2 else 2,
                    }
                )
                variants[f"{animal.lower()}_n{count}_d{start_day}"] = config
    return variants


def _best_animal_config(stage):
    eligible = [
        row
        for row in stage["variants"]
        if row["config"].get("animal_type") in {"GOOSE", "COW", "SHEEP"}
        and row["config"].get("base_plots", 12) == 12
    ]
    return dict(eligible[0]["config"]), eligible[0]["variant"]


def _policy_variants(base):
    variants = {}
    for feed in ("daily", "production", "survival"):
        for care in ("daily", "preproduction", "none"):
            for fertilizer in ("collect", "none"):
                for threshold in (1, 3):
                    config = dict(base)
                    config.update(
                        {
                            "feed_policy": feed,
                            "care_policy": care,
                            "fertilizer_policy": fertilizer,
                            "animal_harvest_threshold": threshold,
                        }
                    )
                    name = f"policy_feed-{feed}_care-{care}_fert-{fertilizer}_h{threshold}"
                    variants[name] = config
    return variants


def _feed_capital_selling_variants(base):
    variants = {"policy_best": dict(base)}
    count = base["animal_count"]
    for policy, plots in (
        ("market", 0),
        ("mixed", max(1, math.ceil(count / 2))),
        ("mixed", count),
        ("self", count),
        ("self", count + 1),
    ):
        for reserve in (1, 2, 3):
            config = dict(base)
            config.update(
                {
                    "wheat_policy": policy,
                    "wheat_feed_plots": plots,
                    "wheat_reserve_days": reserve,
                    "max_plots": max(base.get("max_plots", 36), 12 + plots),
                }
            )
            variants[f"feed_{policy}_plots{plots}_reserve{reserve}"] = config
    for day in (9, 11, 13):
        for threshold in (6000, 10000, 14000):
            config = dict(base)
            config.update(
                {
                    "animal_start_day": day,
                    "animal_start_mode": "day_and_bank",
                    "animal_bank_threshold": threshold,
                }
            )
            variants[f"capital_d{day}_bank{threshold}"] = config
    for hurdle in (0.25, 0.50, 0.75, 1.0):
        config = dict(base)
        config["animal_payback_hurdle"] = hurdle
        variants[f"payback_hurdle_{hurdle:.2f}"] = config
    immediate = dict(base)
    immediate["animal_selling"] = "immediate"
    variants["animal_sell_immediate"] = immediate
    for threshold in (0.80, 0.90, 1.00, 1.10):
        for hold_days in (2, 4):
            config = dict(base)
            config.update(
                {
                    "animal_selling": "aware",
                    "animal_sell_threshold": threshold,
                    "animal_premium_sell_threshold": threshold,
                    "animal_hold_days": hold_days,
                }
            )
            variants[f"animal_sell_{threshold:.2f}_hold{hold_days}"] = config
    return variants


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-start", type=int, default=8600)
    parser.add_argument("--seeds", type=int, default=4)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--stem", default="animal_parameter_search")
    args = parser.parse_args()
    seeds = list(range(args.seed_start, args.seed_start + args.seeds))

    screen = _evaluate(_screen_variants(), seeds, args.workers, "screen_timing_count")
    best_config, best_name = _best_animal_config(screen)
    policies = _evaluate(_policy_variants(best_config), seeds, args.workers, "care_feed_harvest_fertilizer")
    best_policy = dict(policies["variants"][0]["config"])
    feed_capital = _evaluate(
        _feed_capital_selling_variants(best_policy),
        seeds,
        args.workers,
        "feed_capital_selling",
    )
    result = {
        "schema_version": 1,
        "seeds": seeds,
        "positions": [0, 1],
        "opponents": list(OPPONENTS),
        "games_per_variant": len(OPPONENTS) * len(seeds) * 2,
        "screen_selected": best_name,
        "stages": [screen, policies, feed_capital],
        "overall_best": feed_capital["variants"][0],
    }
    path = ROOT / "experiments" / f"{args.stem}.json"
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("Top final variants")
    for row in feed_capital["variants"][:10]:
        overall = row["overall"]
        livestock = row["matchups"]["proxy_livestock_crop"]
        print(
            f"{row['variant']}: score={row['search_score']:+.1f} "
            f"win={overall['win_rate'] * 100:.1f}% money={overall['average_money']:.0f} "
            f"adv={overall['average_advantage']:+.0f} p10={overall['p10_advantage']:+.0f} "
            f"livestock={livestock['wins']}/{livestock['losses']}/{livestock['ties']} "
            f"{livestock['average_advantage']:+.0f}"
        )
    print(f"Saved {path}")


if __name__ == "__main__":
    main()
