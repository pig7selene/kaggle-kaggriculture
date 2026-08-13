"""Three-stage early-compounding search with adversarial held-out validation."""

from __future__ import annotations

import argparse
import copy
import json
import math
import statistics
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from runpy import run_path

from kaggle_environments import make

from analyze_livestock_economics import _player_trace, _run_traced
from benchmark import DEFAULT_WORKERS, EXPERIMENTS_DIR, ROOT, _file_sha256, _load_agent


ENGINE_PATH = ROOT / "agents" / "early_compound_common.py"
ENGINE = run_path(str(ENGINE_PATH))
BASE = copy.deepcopy(ENGINE["FROZEN_DAY14_CONFIG"])
PRODUCTS = set(ENGINE["BASE_PRICES"])

FROZEN_BEST = ROOT / "agents" / "animal_c2_land_day14_adaptive.py"
PATH_OPPONENTS = {
    "frozen_current_best": FROZEN_BEST,
    "gen_cow6_d8": ROOT / "agents" / "adversaries" / "gen_cow6_d8.py",
    "gen_land_d11_labor7_sell12": ROOT / "agents" / "adversaries" / "gen_land_d11_labor7_sell12.py",
    "gen_land_d8_labor6": ROOT / "agents" / "adversaries" / "gen_land_d8_labor6.py",
    "proxy_livestock_crop": ROOT / "agents" / "proxies" / "livestock_crop.py",
    "proxy_high_labor": ROOT / "agents" / "proxies" / "high_labor.py",
    "proxy_land_expander": ROOT / "agents" / "proxies" / "land_expander.py",
    "proxy_phased_rotation": ROOT / "agents" / "proxies" / "phased_rotation.py",
    "adaptive_c_phased": ROOT / "agents" / "adaptive_c_phased.py",
    "animal_c2_cows": ROOT / "agents" / "animal_c2_cows.py",
    "animal_c4_early_cows": ROOT / "agents" / "animal_c4_tuned_cows.py",
}


def _path_spec(path):
    return {"kind": "path", "path": str(path)}


def _config_spec(config):
    return {"kind": "config", "config": copy.deepcopy(config)}


def _load_opponent(spec):
    if spec["kind"] == "path":
        return _load_agent(spec["path"])
    return run_path(str(ENGINE_PATH))["make_agent"](copy.deepcopy(spec["config"]))


def _fib(index):
    a, b = 1, 1
    for _ in range(index):
        a, b = b, a + b
    return a


def _productive_tiles(farm):
    return sum(
        1 for row in farm["tiles"] for tile in row
        if isinstance(tile, dict)
        and (tile.get("kind") == "PLANT" or tile.get("animal") is not None)
    )


def _cow_count(farm):
    return sum(
        1 for row in farm["tiles"] for tile in row
        if isinstance(tile, dict) and tile.get("animal") == "COW"
    )


def _stranded(final_state, seat):
    private = final_state.observation["private"]
    total = sum(private["shed"].get(item, 0) for item in PRODUCTS)
    total += sum(
        inventory.get(item, 0)
        for inventory in private["inventories"]
        for item in PRODUCTS
    )
    farm = final_state.observation["farms"][seat]
    total += sum(
        tile.get("yield_units", 0)
        for row in farm["tiles"]
        for tile in row
        if isinstance(tile, dict) and tile.get("animal")
    )
    return total


def _run_game(job):
    candidate_name, config, opponent_name, opponent_spec, seed, seat = job
    namespace = run_path(str(ENGINE_PATH))
    candidate = namespace["make_agent"](copy.deepcopy(config))
    opponent = _load_opponent(opponent_spec)
    productive = []
    hands_daily = []
    workload = Counter()
    labor_cost = 0
    peak_cows = 0
    escaped_cows = 0
    first_cow_day = None
    target_cow_day = None
    land_days = []
    target_cows = max(count for _, count in candidate.animal_schedule)

    def tracked(obs):
        nonlocal labor_cost, peak_cows, escaped_cows, first_cow_day, target_cow_day
        action = candidate(obs)
        me = obs["farms"][obs["player"]]
        cows = _cow_count(me)
        if cows and first_cow_day is None:
            first_cow_day = obs["day"]
        if cows >= target_cows and target_cow_day is None:
            target_cow_day = obs["day"]
        if peak_cows > cows:
            escaped_cows = max(escaped_cows, peak_cows - cows)
        peak_cows = max(peak_cows, cows)
        if obs["hour"] == 23:
            productive.append(_productive_tiles(me))
            hands_daily.append(len(me["hands"]))
        next_hire = me.get("hires_today", 0)
        for unit_action in [action["farmer"], *action["hands"]]:
            workload[unit_action[0]] += 1
        for order in action["market"]:
            workload[order[0]] += 1
            if order[0] == "HIRE":
                labor_cost += _fib(next_hire)
                next_hire += 1
            elif order[0] == "BUY_LAND":
                land_days.append(obs["day"])
        return action

    agents = [opponent, opponent]
    agents[seat] = tracked
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
    final_cows = _cow_count(final[seat].observation["farms"][seat])
    if peak_cows > final_cows:
        escaped_cows = max(escaped_cows, peak_cows - final_cows)
    candidate_money = float(final[seat].reward)
    opponent_money = float(final[1 - seat].reward)
    movement = sum(workload[op] for op in ("NORTH", "SOUTH", "EAST", "WEST"))
    return {
        "candidate": candidate_name,
        "opponent": opponent_name,
        "seed": seed,
        "seat": seat,
        "candidate_money": candidate_money,
        "opponent_money": opponent_money,
        "advantage": candidate_money - opponent_money,
        "productive_tiles": statistics.fmean(productive) if productive else 0.0,
        "average_hands": statistics.fmean(hands_daily) if hands_daily else 0.0,
        "labor_cost": labor_cost,
        "workload": dict(workload),
        "movement_actions": movement,
        "pass_actions": workload["PASS"],
        "peak_cows": peak_cows,
        "final_cows": final_cows,
        "first_cow_day": first_cow_day,
        "target_cow_day": target_cow_day,
        "escaped_cows": escaped_cows,
        "land_days": land_days,
        "stranded_units": _stranded(final[seat], seat),
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


def _summary(games):
    advantages = [game["advantage"] for game in games]
    money = [game["candidate_money"] for game in games]
    wins = sum(value > 0 for value in advantages)
    losses = sum(value < 0 for value in advantages)
    ties = len(games) - wins - losses
    by_seed = {}
    for game in games:
        by_seed.setdefault(game["seed"], []).append(game["advantage"])
    seed_advantages = [statistics.fmean(values) for values in by_seed.values()]
    land_days = [day for game in games for day in game["land_days"]]
    first_cow_days = [g["first_cow_day"] for g in games if g["first_cow_day"] is not None]
    target_cow_days = [g["target_cow_day"] for g in games if g["target_cow_day"] is not None]
    return {
        "games": len(games),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "win_rate": wins / len(games),
        "score_rate": (wins + 0.5 * ties) / len(games),
        "average_money": statistics.fmean(money),
        "average_opponent_money": statistics.fmean(g["opponent_money"] for g in games),
        "average_advantage": statistics.fmean(advantages),
        "median_advantage": statistics.median(advantages),
        "p10_advantage": _percentile(seed_advantages, 0.10),
        "p5_advantage": _percentile(seed_advantages, 0.05),
        "money_variance": statistics.pvariance(money),
        "advantage_variance": statistics.pvariance(advantages),
        "average_productive_tiles": statistics.fmean(g["productive_tiles"] for g in games),
        "average_hands": statistics.fmean(g["average_hands"] for g in games),
        "average_labor_cost": statistics.fmean(g["labor_cost"] for g in games),
        "average_movement_actions": statistics.fmean(g["movement_actions"] for g in games),
        "average_pass_actions": statistics.fmean(g["pass_actions"] for g in games),
        "average_peak_cows": statistics.fmean(g["peak_cows"] for g in games),
        "average_first_cow_day": statistics.fmean(first_cow_days) if first_cow_days else None,
        "average_target_cow_day": statistics.fmean(target_cow_days) if target_cow_days else None,
        "average_land_day": statistics.fmean(land_days) if land_days else None,
        "average_land_purchases": statistics.fmean(len(g["land_days"]) for g in games),
        "max_escaped_cows": max(g["escaped_cows"] for g in games),
        "max_stranded_units": max(g["stranded_units"] for g in games),
    }


def _result(name, config, games, opponents):
    overall = _summary(games)
    matchups = {
        opponent: _summary([game for game in games if game["opponent"] == opponent])
        for opponent in opponents
    }
    ordered = sorted(
        matchups,
        key=lambda opponent: (
            matchups[opponent]["score_rate"],
            matchups[opponent]["average_advantage"],
        ),
    )
    matchup_wins = sum(row["wins"] > row["losses"] for row in matchups.values())
    matchup_losses = sum(row["wins"] < row["losses"] for row in matchups.values())
    direct = matchups.get("frozen_current_best", overall)
    search_score = (
        overall["average_advantage"]
        + 0.35 * overall["p10_advantage"]
        + 0.35 * direct["average_advantage"]
        + 0.15 * matchups[ordered[0]]["average_advantage"]
        + 1000 * (matchup_wins - matchup_losses)
    )
    if overall["max_escaped_cows"] or overall["max_stranded_units"]:
        search_score -= 100000
    return {
        "candidate": name,
        "config": copy.deepcopy(config),
        "overall": overall,
        "matchups": matchups,
        "matchup_wins": matchup_wins,
        "matchup_losses": matchup_losses,
        "matchup_ties": len(matchups) - matchup_wins - matchup_losses,
        "worst_opponent": ordered[0],
        "worst_five": ordered[:5],
        "search_score": search_score,
    }


def _evaluate(stage, candidates, opponents, seeds, workers):
    jobs = [
        (candidate, config, opponent, spec, seed, seat)
        for candidate, config in candidates.items()
        for opponent, spec in opponents.items()
        for seed in seeds
        for seat in (0, 1)
    ]
    games = []
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(_run_game, job) for job in jobs]
        for index, future in enumerate(as_completed(futures), 1):
            games.append(future.result())
            if index % 100 == 0 or index == len(jobs):
                print(f"{stage}: {index}/{len(jobs)}", flush=True)
    rows = [
        _result(
            name,
            config,
            [game for game in games if game["candidate"] == name],
            opponents,
        )
        for name, config in candidates.items()
    ]
    rows.sort(key=lambda row: row["search_score"], reverse=True)
    return {
        "stage": stage,
        "seeds": list(seeds),
        "opponents": list(opponents),
        "games_per_candidate": len(opponents) * len(seeds) * 2,
        "results": rows,
        "games": games,
    }


def _labor_capacity(plots, target_hands):
    added_target = max(0, target_hands - BASE.get("fixed_hands", 2))
    if added_target <= 0:
        return plots
    choices = [
        capacity for capacity in range(1, plots + 1)
        if min(target_hands, BASE.get("fixed_hands", 2) + math.ceil(plots / capacity))
        == target_hands
    ]
    return max(choices) if choices else max(1, plots // added_target)


def _config(
    schedule=((11, 4),),
    land_day=14,
    hands=5,
    plots=12,
    harvest_age=12,
    structure_day=0,
    animal_workers=None,
    labor_mode="staged",
):
    config = copy.deepcopy(BASE)
    max_cows = max(count for _, count in schedule)
    first_cow_day = min(day for day, _ in schedule)
    config.update({
        "animal_schedule": tuple(schedule),
        "animal_count": max_cows,
        "animal_start_day": first_cow_day,
        "structure_start_day": structure_day,
        "animal_workers": animal_workers or max(2, math.ceil(max_cows / 2)),
        "melon_harvest_age": harvest_age,
        "land_plots_per_quadrant": plots,
        "land_labor_mode": labor_mode,
        "land_plots_per_added_hand": _labor_capacity(plots, hands),
        "max_hands": hands,
        "semantic_validation": True,
    })
    if land_day == "roi":
        config.update({
            "land_policy": "dynamic_roi",
            "land_min_day": 8,
            "land_bank_thresholds": (0,),
            "max_land_purchases": 1,
        })
    else:
        config.update({
            "land_policy": "fixed",
            "land_purchase_days": (int(land_day),),
            "max_land_purchases": 1,
        })
    return config


def _broad_variants():
    variants = {"control_day14_c4_h5_p12": _config()}
    definitions = [
        ("c4d11_land11_h5", ((11, 4),), 11, 5, 16),
        ("c4d11_land11_h6", ((11, 4),), 11, 6, 16),
        ("c4d11_land11_h7", ((11, 4),), 11, 7, 16),
        ("c4d11_land10_h6", ((11, 4),), 10, 6, 16),
        ("c4d11_land10_h7", ((11, 4),), 10, 7, 16),
        ("c4d11_land12_h6", ((11, 4),), 12, 6, 16),
        ("c4d11_land12_h7", ((11, 4),), 12, 7, 16),
        ("c6d8_land10_h6", ((8, 6),), 10, 6, 16),
        ("c6d8_land10_h7", ((8, 6),), 10, 7, 16),
        ("c6d8_land11_h6", ((8, 6),), 11, 6, 16),
        ("c6d8_land11_h7", ((8, 6),), 11, 7, 16),
        ("c6d8_land12_h6", ((8, 6),), 12, 6, 16),
        ("c6d8_land12_h7", ((8, 6),), 12, 7, 16),
        ("c6d8_land14_h5", ((8, 6),), 14, 5, 12),
        ("c6d10_land11_h6", ((10, 6),), 11, 6, 16),
        ("c6d10_land11_h7", ((10, 6),), 11, 7, 16),
        ("c6d11_land11_h6", ((11, 6),), 11, 6, 16),
        ("c6d11_land11_h7", ((11, 6),), 11, 7, 16),
        ("c4d8_to6d13_land11_h6", ((8, 4), (13, 6)), 11, 6, 16),
        ("c4d8_to6d13_land11_h7", ((8, 4), (13, 6)), 11, 7, 16),
        ("c4d10_to6d14_land11_h6", ((10, 4), (14, 6)), 11, 6, 16),
        ("c4d10_to6d14_land11_h7", ((10, 4), (14, 6)), 11, 7, 16),
        ("c4d11_to6d15_land11_h7", ((11, 4), (15, 6)), 11, 7, 16),
        ("c4d10_to8d15_land10_h7", ((10, 4), (15, 8)), 10, 7, 16),
        ("c4d11_to8d16_land11_h8", ((11, 4), (16, 8)), 11, 8, 16),
        ("c6d8_roi_h7", ((8, 6),), "roi", 7, 16),
    ]
    for name, schedule, land, hands, plots in definitions:
        structure = max(0, schedule[0][0] - 1) if schedule[0][1] >= 6 else 0
        variants[name] = _config(schedule, land, hands, plots, 12, structure)
    for threshold in (2500, 5000, 8000):
        config = _config(((8, 6),), 11, 7, 16, 10, 7)
        config.update({
            "animal_start_mode": "day_and_bank",
            "animal_bank_threshold": threshold,
        })
        variants[f"c6d8_bank{threshold}_land11_h7"] = config
    for day in (8, 10):
        config = _config(((day, 4), (14, 6)), 11, 7, 16, 10, 0)
        config.update({
            "animal_start_mode": "day_and_bank",
            "animal_bank_threshold": 2500,
        })
        variants[f"c4d{day}_to6d14_bank2500_land11_h7"] = config
    return variants


def _canonical(config):
    value = copy.deepcopy(config)
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _refine_variants(rows):
    variants = {}
    seen = set()

    def add(name, config):
        fingerprint = _canonical(config)
        if fingerprint not in seen:
            seen.add(fingerprint)
            variants[name] = config

    for rank, row in enumerate(rows[:6], 1):
        base = copy.deepcopy(row["config"])
        prefix = f"r{rank}_{row['candidate']}"
        add(prefix, base)
        for threshold in (0, 2500, 5000, 8000):
            config = copy.deepcopy(base)
            config["animal_start_mode"] = "day_and_bank" if threshold else "day"
            config["animal_bank_threshold"] = threshold
            add(f"{prefix}_animalbank{threshold}", config)
        if base.get("land_policy") == "fixed":
            day = base["land_purchase_days"][0]
            for shifted in (max(8, day - 1), min(14, day + 1)):
                config = copy.deepcopy(base)
                config["land_purchase_days"] = (shifted,)
                add(f"{prefix}_land{shifted}", config)
        for hands in (
            max(5, base["max_hands"] - 1),
            min(8, base["max_hands"] + 1),
        ):
            config = copy.deepcopy(base)
            config["max_hands"] = hands
            config["land_plots_per_added_hand"] = _labor_capacity(
                config["land_plots_per_quadrant"], hands
            )
            add(f"{prefix}_hands{hands}", config)
        for plots in (12, 16, 20):
            config = copy.deepcopy(base)
            config["land_plots_per_quadrant"] = plots
            config["land_plots_per_added_hand"] = _labor_capacity(
                plots, config["max_hands"]
            )
            add(f"{prefix}_plots{plots}", config)
        for animal_workers in (2, 3, 4):
            config = copy.deepcopy(base)
            config["animal_workers"] = animal_workers
            add(f"{prefix}_animalworkers{animal_workers}", config)
        schedule = list(base["animal_schedule"])
        if len(schedule) > 1:
            for delta in (-1, 1):
                config = copy.deepcopy(base)
                changed = list(config["animal_schedule"])
                changed[-1] = (max(changed[0][0], changed[-1][0] + delta), changed[-1][1])
                config["animal_schedule"] = tuple(changed)
                add(f"{prefix}_secondcowshift{delta:+d}", config)
    return variants


def _capital_labor_variants(rows):
    variants = {}
    seen = set()

    def add(name, config):
        fingerprint = _canonical(config)
        if fingerprint not in seen:
            seen.add(fingerprint)
            variants[name] = config

    for rank, row in enumerate(rows[:5], 1):
        base = copy.deepcopy(row["config"])
        prefix = f"c{rank}_{row['candidate']}"
        add(prefix, base)
        for threshold in (0, 2500, 5000, 8000, 11000):
            config = copy.deepcopy(base)
            config["animal_start_mode"] = "day_and_bank" if threshold else "day"
            config["animal_bank_threshold"] = threshold
            add(f"{prefix}_animalbank{threshold}", config)
        for structure in (0, max(0, base["animal_schedule"][0][0] - 1)):
            config = copy.deepcopy(base)
            config["structure_start_day"] = structure
            add(f"{prefix}_structure{structure}", config)
        for workers in (2, 3, 4):
            config = copy.deepcopy(base)
            config["animal_workers"] = workers
            add(f"{prefix}_animalworkers{workers}", config)
        config = copy.deepcopy(base)
        config.update({"land_labor_mode": "workload", "land_crop_worker_capacity": 7})
        add(f"{prefix}_workloadlabor", config)
    return variants


def _mutations(best):
    variants = {"red_control": copy.deepcopy(best)}
    schedule = tuple(best["animal_schedule"])
    first = schedule[0][0]
    max_cows = max(count for _, count in schedule)
    for day in sorted(set((max(7, first - 2), max(7, first - 1), first, first + 1))):
        for cows in (4, 6, 8):
            config = copy.deepcopy(best)
            config["animal_schedule"] = ((day, cows),)
            config["animal_count"] = cows
            config["animal_start_day"] = day
            config["structure_start_day"] = max(0, day - 1)
            config["animal_workers"] = max(2, math.ceil(cows / 2))
            variants[f"red_cow{cows}_d{day}"] = config
    for day in (8, 9, 10, 11, 12, 13):
        config = copy.deepcopy(best)
        config.update({"land_policy": "fixed", "land_purchase_days": (day,)})
        variants[f"red_land{day}"] = config
    for hands in (5, 6, 7, 8):
        config = copy.deepcopy(best)
        config["max_hands"] = hands
        config["land_plots_per_added_hand"] = _labor_capacity(
            config["land_plots_per_quadrant"], hands
        )
        variants[f"red_hands{hands}"] = config
    for plots in (12, 16, 20):
        config = copy.deepcopy(best)
        config["land_plots_per_quadrant"] = plots
        config["land_plots_per_added_hand"] = _labor_capacity(plots, config["max_hands"])
        variants[f"red_plots{plots}"] = config
    for threshold in (0, 2500, 5000, 8000, 11000):
        config = copy.deepcopy(best)
        config["animal_start_mode"] = "day_and_bank" if threshold else "day"
        config["animal_bank_threshold"] = threshold
        variants[f"red_animalbank{threshold}"] = config
    for schedule_variant in (
        ((8, 4), (12, 6)),
        ((9, 4), (13, 6)),
        ((10, 4), (14, 8)),
        ((11, 4), (15, 8)),
    ):
        config = copy.deepcopy(best)
        config["animal_schedule"] = schedule_variant
        config["animal_count"] = schedule_variant[-1][1]
        config["animal_start_day"] = schedule_variant[0][0]
        config["structure_start_day"] = 0
        config["animal_workers"] = max(2, math.ceil(schedule_variant[-1][1] / 2))
        variants[f"red_stage_{schedule_variant[0][0]}_{schedule_variant[-1][0]}_{schedule_variant[-1][1]}"] = config
    return variants


def _diagnose():
    result = {}
    for opponent_name in (
        "gen_cow6_d8",
        "gen_land_d11_labor7_sell12",
        "gen_land_d8_labor6",
    ):
        matches = []
        for seed in (11000, 11001):
            for seat in (0, 1):
                baseline = _load_agent(str(FROZEN_BEST))
                opponent = _load_agent(str(PATH_OPPONENTS[opponent_name]))
                agents = [opponent, opponent]
                agents[seat] = baseline
                env, events = _run_traced(agents, seed)
                matches.append({
                    "baseline": _player_trace(env, events, seat),
                    "opponent": _player_trace(env, events, 1 - seat),
                })
        daily = []
        for day in range(30):
            row = {"day": day}
            for role in ("baseline", "opponent"):
                role_rows = [match[role]["days"][day] for match in matches]
                for key in (
                    "bank", "economic_position", "cumulative_income",
                    "cumulative_spending", "crop_revenue", "animal_revenue",
                    "fertilizer_revenue", "seed_spending",
                    "animal_purchase_spending", "labor_spending", "land_spending",
                    "feed_purchase_spending", "productive_tiles", "hands",
                    "quadrants", "total_inventory_value",
                ):
                    row[f"{role}_{key}"] = statistics.fmean(value[key] for value in role_rows)
                row[f"{role}_cows"] = statistics.fmean(
                    value["animal_tiles"].get("COW", 0) for value in role_rows
                )
            for metric in ("bank", "economic_position", "cumulative_income"):
                row[f"gap_{metric}"] = row[f"opponent_{metric}"] - row[f"baseline_{metric}"]
            daily.append(row)

        def durable(metric):
            return next(
                (day for day in range(30) if all(row[metric] > 0 for row in daily[day:])),
                None,
            )

        result[opponent_name] = {
            "games": len(matches),
            "durable_bank_lead_day": durable("gap_bank"),
            "durable_economic_position_lead_day": durable("gap_economic_position"),
            "durable_cumulative_income_lead_day": durable("gap_cumulative_income"),
            "daily": daily,
        }
    return result


def _path_pool(names):
    return {name: _path_spec(PATH_OPPONENTS[name]) for name in names}


def _checkpoint(payload):
    path = EXPERIMENTS_DIR / "3h_compounding_search.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"checkpoint {path}", flush=True)


def run(workers):
    result = {
        "schema_version": 1,
        "experiment": "3h_early_compounding",
        "frozen_best": str(FROZEN_BEST.relative_to(ROOT)),
        "frozen_best_sha256": _file_sha256(FROZEN_BEST),
        "engine": str(ENGINE_PATH.relative_to(ROOT)),
        "engine_sha256": _file_sha256(ENGINE_PATH),
        "seed_partitions": {
            "diagnosis": [11000, 11001],
            "broad": [11100, 11101],
            "refine": [11120, 11121],
            "capital_labor": [11140, 11142],
            "red_team": [11200, 11203],
            "prefinal": [11220, 11222],
            "heldout": [11300, 11311],
        },
        "diagnosis": _diagnose(),
        "stages": [],
    }
    _checkpoint(result)

    broad_opponents = _path_pool((
        "frozen_current_best", "gen_cow6_d8",
        "gen_land_d11_labor7_sell12", "gen_land_d8_labor6",
        "proxy_livestock_crop",
    ))
    broad = _evaluate(
        "broad_joint_screen", _broad_variants(), broad_opponents,
        range(11100, 11102), workers,
    )
    result["stages"].append(broad)
    _checkpoint(result)

    hard_paths = _path_pool((
        "frozen_current_best", "gen_cow6_d8",
        "gen_land_d11_labor7_sell12", "gen_land_d8_labor6",
        "proxy_livestock_crop", "proxy_high_labor", "proxy_land_expander",
    ))
    refine = _evaluate(
        "joint_refinement", _refine_variants(broad["results"]), hard_paths,
        range(11120, 11122), workers,
    )
    result["stages"].append(refine)
    _checkpoint(result)

    capital = _evaluate(
        "capital_labor_refinement", _capital_labor_variants(refine["results"]),
        hard_paths, range(11140, 11143), workers,
    )
    result["stages"].append(capital)
    _checkpoint(result)

    best_config = copy.deepcopy(capital["results"][0]["config"])
    red_variants = _mutations(best_config)
    red_opponent = {"frozen_candidate": _config_spec(best_config)}
    red_team = _evaluate(
        "red_team", red_variants, red_opponent, range(11200, 11204), workers
    )
    result["stages"].append(red_team)
    challengers = {
        row["candidate"]: _config_spec(row["config"])
        for row in red_team["results"]
        if row["candidate"] != "red_control"
    }
    challengers = dict(list(challengers.items())[:3])
    result["retained_red_team"] = challengers
    _checkpoint(result)

    finalist_candidates = {}
    for row in capital["results"][:4]:
        finalist_candidates[row["candidate"]] = row["config"]
    for row in red_team["results"][:4]:
        if row["candidate"] != "red_control":
            finalist_candidates[f"challenger_{row['candidate']}"] = row["config"]
    prefinal_opponents = {**hard_paths, **challengers}
    prefinal = _evaluate(
        "prefinal_hard_pool", finalist_candidates, prefinal_opponents,
        range(11220, 11223), workers,
    )
    result["stages"].append(prefinal)
    _checkpoint(result)

    serious = {"P0_frozen_control": _config()}
    fingerprints = {_canonical(serious["P0_frozen_control"])}
    for row in prefinal["results"]:
        fingerprint = _canonical(row["config"])
        if fingerprint in fingerprints:
            continue
        fingerprints.add(fingerprint)
        serious[row["candidate"]] = row["config"]
        if len(serious) >= 3:
            break
    heldout_paths = _path_pool((
        "frozen_current_best", "gen_cow6_d8",
        "gen_land_d11_labor7_sell12", "gen_land_d8_labor6",
        "proxy_livestock_crop", "proxy_high_labor", "proxy_land_expander",
        "proxy_phased_rotation", "adaptive_c_phased", "animal_c2_cows",
        "animal_c4_early_cows",
    ))
    heldout_opponents = {**heldout_paths, **challengers}
    heldout = _evaluate(
        "heldout_confirmation", serious, heldout_opponents,
        range(11300, 11312), workers,
    )
    result["serious_candidates"] = list(serious)
    result["heldout_opponents"] = heldout_opponents
    result["stages"].append(heldout)
    result["total_retained_simulations"] = 12 + sum(
        len(stage["games"]) for stage in result["stages"]
    )
    _checkpoint(result)
    for row in heldout["results"]:
        overall = row["overall"]
        direct = row["matchups"]["frozen_current_best"]
        print(
            f"HELDOUT {row['candidate']} {overall['wins']}/{overall['losses']}/{overall['ties']} "
            f"money={overall['average_money']:.1f} adv={overall['average_advantage']:+.1f} "
            f"p10={overall['p10_advantage']:+.1f} direct="
            f"{direct['wins']}/{direct['losses']}/{direct['ties']} "
            f"{direct['average_advantage']:+.1f}",
            flush=True,
        )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    args = parser.parse_args()
    run(args.workers)


if __name__ == "__main__":
    main()
