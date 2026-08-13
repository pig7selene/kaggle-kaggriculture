"""Adversarial league construction and P0-P7 planner evaluation."""

from __future__ import annotations

import argparse
import copy
import json
import math
import statistics
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from runpy import run_path

from analyze_livestock_economics import _run_traced
from benchmark import DEFAULT_WORKERS, EXPERIMENTS_DIR, ROOT, _file_sha256, _load_agent
from test_economic_agents import SELLABLE, _validate_action


ENGINE_PATH = ROOT / "agents" / "planner_common.py"
ENGINE = run_path(str(ENGINE_PATH))
PRODUCTS = tuple(ENGINE["BASE_PRICES"])
CROPS = tuple(ENGINE["CROPS"])
ANIMAL_PRODUCTS = {data["product"] for data in ENGINE["ANIMALS"].values()}
CURRENT_BEST = ROOT / "agents" / "animal_c2_land_day14_adaptive.py"


def _path_spec(path):
    return {"kind": "path", "path": str(path)}


def _config_spec(config):
    return {"kind": "config", "config": copy.deepcopy(config)}


def _load_spec(spec):
    if spec["kind"] == "path":
        return _load_agent(spec["path"])
    namespace = run_path(str(ENGINE_PATH))
    return namespace["make_agent"](copy.deepcopy(spec["config"]))


HISTORICAL_LEAGUE = {
    "melon_scale_12": _path_spec(ROOT / "agents" / "melon_scale_12.py"),
    "adaptive_c_phased": _path_spec(ROOT / "agents" / "adaptive_c_phased.py"),
    "animal_c2_cows": _path_spec(ROOT / "agents" / "animal_c2_cows.py"),
    "animal_c2_land_day14": _path_spec(CURRENT_BEST),
    "proxy_livestock_crop": _path_spec(ROOT / "agents" / "proxies" / "livestock_crop.py"),
    "proxy_high_labor": _path_spec(ROOT / "agents" / "proxies" / "high_labor.py"),
    "proxy_land_expander": _path_spec(ROOT / "agents" / "proxies" / "land_expander.py"),
    "proxy_phased_rotation": _path_spec(ROOT / "agents" / "proxies" / "phased_rotation.py"),
    "proxy_inventory_holder": _path_spec(ROOT / "agents" / "proxies" / "inventory_holder.py"),
    "proxy_mixed_crop": _path_spec(ROOT / "agents" / "proxies" / "mixed_crop.py"),
    "proxy_melon_heavy": _path_spec(ROOT / "agents" / "proxies" / "melon_heavy.py"),
    "animal_c3_sheep": _path_spec(ROOT / "agents" / "animal_c3_sheep.py"),
    "animal_c4_early_cows": _path_spec(ROOT / "agents" / "animal_c4_tuned_cows.py"),
    "animal_c5_adaptive": _path_spec(ROOT / "agents" / "animal_c5_adaptive.py"),
}


def _generated_adversaries():
    variants = {}
    mixtures = (
        ("melon_strawberry", ("MELON", "STRAWBERRY", "MELON", "WHEAT")),
        ("wheat_strawberry", ("WHEAT", "STRAWBERRY", "WHEAT", "STRAWBERRY")),
        ("tomato_wheat", ("TOMATO", "WHEAT", "TOMATO", "CARROT")),
        ("premium_mix", ("STRAWBERRY", "MELON", "TOMATO", "WHEAT")),
        ("staple_mix", ("WHEAT", "CARROT", "WHEAT", "TOMATO")),
        ("counter_mix", ("CARROT", "TOMATO", "STRAWBERRY", "WHEAT", "MELON")),
    )
    for index, (label, pattern) in enumerate(mixtures):
        for cohorts in (1, 3):
            config = {
                "crop_mode": "mixed",
                "mixed_pattern": pattern,
                "base_plots": 20 if index % 2 == 0 else 24,
                "plots_per_land": 12,
                "max_plots": 36,
                "fixed_hands": 4 if cohorts == 1 else 6,
                "forced_land_days": (11 if index % 2 == 0 else 14,),
                "selling": "aware" if index % 3 == 0 else "immediate",
                "cohort_mode": "synchronized" if cohorts == 1 else "fixed",
                "cohort_count": cohorts,
                "cohort_spacing_days": 2,
            }
            variants[f"gen_mix_{label}_c{cohorts}"] = _config_spec(config)

    for label, schedule in (
        ("melon_wheat", ((0, "MELON"), (20, "WHEAT"))),
        ("melon_straw", ((0, "MELON"), (11, "STRAWBERRY"), (22, "WHEAT"))),
        ("tomato_carrot", ((0, "TOMATO"), (18, "CARROT"))),
        ("straw_wheat", ((0, "STRAWBERRY"), (19, "WHEAT"))),
    ):
        for cohorts in (2, 4):
            variants[f"gen_phase_{label}_c{cohorts}"] = _config_spec({
                "crop_mode": "phased",
                "phase_schedule": schedule,
                "base_plots": 20,
                "max_plots": 32,
                "fixed_hands": 5,
                "forced_land_days": (11,),
                "selling": "aware",
                "cohort_mode": "fixed",
                "cohort_count": cohorts,
                "cohort_spacing_days": 2,
            })

    animal_base = copy.deepcopy(ENGINE["CURRENT_BEST_CONFIG"])
    for animal in ("COW", "SHEEP", "GOOSE"):
        for count, day in ((2, 8), (4, 11), (6, 8)):
            config = copy.deepcopy(animal_base)
            config.update({
                "animal_type": animal,
                "animal_count": count,
                "animal_start_day": day,
                "structure_start_day": max(0, day - 1),
                "animal_workers": max(1, math.ceil(count / 2)),
                "land_purchase_days": (11 if count == 6 else 14,),
                "selling": "aware",
            })
            variants[f"gen_{animal.lower()}{count}_d{day}"] = _config_spec(config)

    for day, labor, horizon in ((8, 6, 0), (11, 7, 12), (14, 5, 24), (16, 6, "planner")):
        config = copy.deepcopy(ENGINE["CURRENT_BEST_CONFIG"])
        config.update({
            "land_purchase_days": (day,),
            "land_plots_per_quadrant": 16,
            "land_plots_per_added_hand": max(3, 16 // max(1, labor - 2)),
            "max_hands": labor,
            "selling_horizon": horizon,
            "planner_opponent_forecast": True,
        })
        variants[f"gen_land_d{day}_labor{labor}_sell{horizon}"] = _config_spec(config)

    for bias_label, biases, cohorts in (
        ("anti_melon", {"MELON": 0.35, "STRAWBERRY": 1.4, "WHEAT": 1.2}, 2),
        ("premium", {"MELON": 1.2, "STRAWBERRY": 1.5, "MILK": 1.0}, 3),
        ("staples", {"WHEAT": 1.7, "CARROT": 1.4, "MELON": 0.5}, 4),
    ):
        config = copy.deepcopy(ENGINE["PLANNER_BASE"])
        config.update({
            "planner_opponent_forecast": True,
            "planner_self_impact": True,
            "crop_bias": biases,
            "cohort_mode": "fixed",
            "cohort_count": cohorts,
            "selling_horizon": "planner",
        })
        variants[f"gen_planner_{bias_label}_c{cohorts}"] = _config_spec(config)
    return variants


def _count_productive(farm):
    return sum(
        1 for row in farm["tiles"] for tile in row
        if isinstance(tile, dict)
        and (tile.get("kind") == "PLANT" or tile.get("animal") is not None)
    )


def _stranded(state, seat):
    private = state.observation["private"]
    total = sum(private["shed"].get(item, 0) for item in SELLABLE)
    total += sum(inv.get(item, 0) for inv in private["inventories"] for item in SELLABLE)
    farm = state.observation["farms"][seat]
    total += sum(
        tile.get("yield_units", 0) for row in farm["tiles"] for tile in row
        if isinstance(tile, dict) and tile.get("animal")
    )
    return total


def _run_game(job):
    candidate_name, candidate_spec, opponent_name, opponent_spec, seed, seat = job
    candidate = _load_spec(candidate_spec)
    opponent = _load_spec(opponent_spec)
    namespace = run_path(str(ENGINE_PATH))
    productive = []
    workload = Counter()
    land_events = []
    market_impact = 0.0
    invalid_actions = 0
    lots = {product: [] for product in PRODUCTS}
    previous_shed = Counter()
    pending_sales = Counter()
    held_turns = 0.0
    held_units = 0

    def consume(product, quantity, step):
        nonlocal held_turns, held_units
        remaining = quantity
        while remaining > 0 and lots[product]:
            born, count = lots[product][0]
            used = min(remaining, count)
            held_turns += used * max(0, step - born)
            held_units += used
            remaining -= used
            count -= used
            if count:
                lots[product][0] = (born, count)
            else:
                lots[product].pop(0)

    def tracked(obs):
        nonlocal market_impact, invalid_actions, previous_shed, pending_sales
        step = int(obs.get("step", 0))
        current_shed = Counter(obs["private"]["shed"])
        for product in PRODUCTS:
            arrived = current_shed[product] - previous_shed[product] + pending_sales[product]
            if arrived > 0:
                lots[product].append((step, arrived))
        previous_shed = current_shed
        pending_sales = Counter()
        action = candidate(obs)
        try:
            _validate_action(obs, action)
        except Exception:
            invalid_actions += 1
            raise
        me = obs["farms"][obs["player"]]
        if obs["hour"] == 23:
            productive.append(_count_productive(me))
        for unit_action in [action["farmer"], *action["hands"]]:
            workload[unit_action[0]] += 1
        for order in action["market"]:
            workload[order[0]] += 1
            if order[0] == "SELL":
                product, quantity = order[1], order[2]
                consume(product, quantity, step)
                pending_sales[product] += quantity
                flat = quantity * obs["market"]["prices"][product]
                sequential = namespace["_sale_value"](
                    product, quantity, obs["market"]["inventory"][product]
                )
                market_impact += max(0.0, flat - sequential)
            elif order[0] == "BUY_LAND":
                try:
                    land_events.append(
                        namespace["_land_economics"](obs, candidate.config)
                    )
                except (AttributeError, KeyError, TypeError):
                    land_events.append(None)
        return action

    agents = [opponent, opponent]
    agents[seat] = tracked
    env, events = _run_traced(agents, seed)
    final = env.steps[-1]
    candidate_money = float(final[seat].reward)
    opponent_money = float(final[1 - seat].reward)
    revenue = Counter()
    spending = Counter()
    sale_units = Counter()
    for event in events:
        if event["player"] != seat:
            continue
        if event["kind"] == "sale":
            revenue[event["item"]] += event["amount"]
            sale_units[event["item"]] += 1
        else:
            spending[event["kind"]] += event["amount"]
    crop_revenue = {crop: revenue[crop] for crop in CROPS}
    animal_revenue = sum(revenue[item] for item in ANIMAL_PRODUCTS)
    fertilizer_revenue = revenue["FERTILIZER"]
    return {
        "candidate": candidate_name,
        "opponent": opponent_name,
        "seed": seed,
        "seat": seat,
        "candidate_money": candidate_money,
        "opponent_money": opponent_money,
        "advantage": candidate_money - opponent_money,
        "productive_tiles": statistics.fmean(productive) if productive else 0.0,
        "labor_cost": spending["labor_spending"],
        "crop_revenue": crop_revenue,
        "animal_revenue": animal_revenue,
        "fertilizer_revenue": fertilizer_revenue,
        "land_spending": spending["land_spending"],
        "land_events": [event for event in land_events if event],
        "market_impact": market_impact,
        "average_holding_turns": held_turns / max(1, held_units),
        "workload": dict(workload),
        "invalid_actions": invalid_actions,
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
    by_seed = defaultdict(list)
    for game in games:
        by_seed[game["seed"]].append(game["advantage"])
    seed_advantages = [statistics.fmean(values) for values in by_seed.values()]
    crop_revenue = {
        crop: statistics.fmean(game["crop_revenue"][crop] for game in games)
        for crop in CROPS
    }
    land_events = [event for game in games for event in game["land_events"]]
    paid_back_land_events = [
        event for event in land_events if event["payback_day"] is not None
    ]
    return {
        "games": len(games),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "win_rate": wins / len(games),
        "score_rate": (wins + 0.5 * ties) / len(games),
        "average_money": statistics.fmean(money),
        "average_advantage": statistics.fmean(advantages),
        "median_advantage": statistics.median(advantages),
        "p10_advantage": _percentile(seed_advantages, 0.10),
        "p5_advantage": _percentile(seed_advantages, 0.05),
        "money_variance": statistics.pvariance(money),
        "advantage_variance": statistics.pvariance(advantages),
        "average_productive_tiles": statistics.fmean(g["productive_tiles"] for g in games),
        "average_labor_cost": statistics.fmean(g["labor_cost"] for g in games),
        "crop_revenue": crop_revenue,
        "average_animal_revenue": statistics.fmean(g["animal_revenue"] for g in games),
        "average_fertilizer_revenue": statistics.fmean(g["fertilizer_revenue"] for g in games),
        "average_land_spending": statistics.fmean(g["land_spending"] for g in games),
        "average_land_purchases": statistics.fmean(len(g["land_events"]) for g in games),
        "average_land_roi": (
            statistics.fmean(event["roi"] for event in land_events) if land_events else 0.0
        ),
        "average_land_payback_day": (
            statistics.fmean(event["payback_day"] for event in paid_back_land_events)
            if paid_back_land_events else None
        ),
        "average_market_impact": statistics.fmean(g["market_impact"] for g in games),
        "average_inventory_holding_turns": statistics.fmean(g["average_holding_turns"] for g in games),
        "max_invalid_actions": max(g["invalid_actions"] for g in games),
        "max_stranded_units": max(g["stranded_units"] for g in games),
    }


def _result(name, spec, games, opponents):
    overall = _summary(games)
    matchups = {
        opponent: _summary([g for g in games if g["opponent"] == opponent])
        for opponent in opponents
    }
    ordered = sorted(
        matchups.items(),
        key=lambda item: (item[1]["score_rate"], item[1]["average_advantage"]),
    )
    wins = sum(row["wins"] > row["losses"] for row in matchups.values())
    losses = sum(row["wins"] < row["losses"] for row in matchups.values())
    search_score = (
        overall["average_advantage"]
        + 0.30 * overall["p10_advantage"]
        + 0.15 * ordered[0][1]["average_advantage"]
        + 1000 * (wins - losses)
    )
    return {
        "candidate": name,
        "spec": spec,
        "overall": overall,
        "matchups": matchups,
        "matchup_wins": wins,
        "matchup_losses": losses,
        "matchup_ties": len(matchups) - wins - losses,
        "worst_opponent": ordered[0][0],
        "worst_five": [name for name, _ in ordered[:5]],
        "search_score": search_score,
    }


def _evaluate(stage, candidates, opponents, seeds, workers):
    jobs = [
        (candidate, spec, opponent, opponent_spec, seed, seat)
        for candidate, spec in candidates.items()
        for opponent, opponent_spec in opponents.items()
        for seed in seeds
        for seat in (0, 1)
    ]
    games = []
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(_run_game, job) for job in jobs]
        for index, future in enumerate(as_completed(futures), 1):
            games.append(future.result())
            if index % 50 == 0 or index == len(jobs):
                print(f"{stage}: {index}/{len(jobs)}", flush=True)
    rows = [
        _result(name, spec, [g for g in games if g["candidate"] == name], opponents)
        for name, spec in candidates.items()
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


def _spec_fingerprint(spec):
    """Return a stable behavioral-configuration key for finalist deduplication."""
    if spec["kind"] == "config":
        resolved = ENGINE["make_agent"](copy.deepcopy(spec["config"])).config
        value = {"kind": "config", "config": resolved}
    else:
        value = spec
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _select_distinct_serious(architecture_search, architectures, limit=3):
    names = ["P0_current_best"]
    seen = {_spec_fingerprint(architectures["P0_current_best"])}
    for row in architecture_search["results"]:
        name = row["candidate"]
        if name == "P0_current_best":
            continue
        fingerprint = _spec_fingerprint(architectures[name])
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        names.append(name)
        if len(names) >= limit:
            break
    return names


def _hard_subset(selected):
    result = {
        "animal_c2_land_day14": HISTORICAL_LEAGUE["animal_c2_land_day14"],
        "proxy_livestock_crop": HISTORICAL_LEAGUE["proxy_livestock_crop"],
        "proxy_high_labor": HISTORICAL_LEAGUE["proxy_high_labor"],
        "proxy_land_expander": HISTORICAL_LEAGUE["proxy_land_expander"],
        "animal_c4_early_cows": HISTORICAL_LEAGUE["animal_c4_early_cows"],
    }
    for name, spec in list(selected.items())[:5]:
        result[name] = spec
    return result


def _planner_config(opponent=False, impact=False):
    config = copy.deepcopy(ENGINE["PLANNER_BASE"])
    config.update({
        "planner_opponent_forecast": opponent,
        "planner_self_impact": impact,
    })
    return config


def _write_markdown(path, result):
    lines = [
        "# Full-farm Planner and Adversarial League", "",
        f"Permanent league size: {len(result['league'])} opponents.", "",
    ]
    for stage in result["stages"]:
        lines.extend([
            f"## {stage['stage']}", "",
            f"Seeds: {stage['seeds']}; games/candidate: {stage['games_per_candidate']}.", "",
            "| Rank | Candidate | W/L/T | Win rate | Avg money | Avg advantage | Median | P10 | P5 | Variance | Worst |",
            "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ])
        for rank, row in enumerate(stage["results"], 1):
            o = row["overall"]
            lines.append(
                f"| {rank} | {row['candidate']} | {o['wins']}/{o['losses']}/{o['ties']} | "
                f"{o['win_rate']*100:.1f}% | {o['average_money']:.1f} | "
                f"{o['average_advantage']:+.1f} | {o['median_advantage']:+.1f} | "
                f"{o['p10_advantage']:+.1f} | {o['p5_advantage']:+.1f} | "
                f"{o['money_variance']:.1f} | {row['worst_opponent']} |"
            )
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(workers):
    generated = _generated_adversaries()
    adversarial = _evaluate(
        "adversarial_search",
        generated,
        {"frozen_current_best": _path_spec(CURRENT_BEST)},
        range(10000, 10004),
        workers,
    )
    selected_names = [row["candidate"] for row in adversarial["results"][:12]]
    selected = {name: generated[name] for name in selected_names}
    league = {**HISTORICAL_LEAGUE, **selected}
    hard = _hard_subset(selected)

    p3 = _planner_config(True, True)
    cohort_variants = {}
    for label, mode, count in (
        ("S0_sync", "synchronized", 1),
        ("S1_two", "fixed", 2),
        ("S2_three", "fixed", 3),
        ("S3_four", "fixed", 4),
        ("S4_planner", "planner", 1),
    ):
        config = copy.deepcopy(p3)
        config.update({"cohort_mode": mode, "cohort_count": count})
        cohort_variants[label] = _config_spec(config)
    cohorts = _evaluate(
        "cohort_search", cohort_variants, hard, range(10020, 10022), workers
    )
    best_cohort = copy.deepcopy(cohorts["results"][0]["spec"]["config"])

    selling_variants = {}
    for horizon in (0, 6, 12, 24, "planner"):
        config = copy.deepcopy(best_cohort)
        config["selling_horizon"] = horizon
        selling_variants[f"sell_{horizon}"] = _config_spec(config)
    selling = _evaluate(
        "selling_search", selling_variants, hard, range(10030, 10032), workers
    )
    best_selling = copy.deepcopy(selling["results"][0]["spec"]["config"])

    animal_variants = {}
    for animal, count in ((None, 0), ("COW", 2), ("COW", 4), ("COW", 6),
                          ("SHEEP", 2), ("SHEEP", 4), ("SHEEP", 6), ("GOOSE", 4)):
        config = copy.deepcopy(best_selling)
        config.update({
            "dynamic_animal_capital": False,
            "animal_portfolio": (),
            "animal_type": animal,
            "animal_count": count,
            "animal_workers": max(1, math.ceil(count / 2)) if count else 0,
            "structure_start_day": 0,
        })
        animal_variants[f"animal_{animal or 'none'}_{count}"] = _config_spec(config)
    mixed = copy.deepcopy(best_selling)
    mixed.update({
        "dynamic_animal_capital": False,
        "animal_type": "COW",
        "animal_count": 4,
        "animal_portfolio": (("COW", 2), ("SHEEP", 2)),
        "animal_workers": 2,
        "structure_start_day": 0,
    })
    animal_variants["animal_mixed_2cow_2sheep"] = _config_spec(mixed)
    dynamic = copy.deepcopy(best_selling)
    dynamic.update({
        "dynamic_animal_capital": True,
        "animal_decision_day": 10,
        "structure_start_day": 10,
        "animal_type_options": ("COW", "SHEEP", "GOOSE"),
        "animal_count_options": (0, 2, 4, 6),
    })
    animal_variants["animal_dynamic"] = _config_spec(dynamic)
    animals = _evaluate(
        "animal_capital_search", animal_variants, hard, range(10040, 10042), workers
    )
    best_animal = copy.deepcopy(animals["results"][0]["spec"]["config"])

    land_variants = {"land_one_only": _config_spec(copy.deepcopy(best_animal))}
    for threshold, day in ((20000, 18), (30000, 18), (40000, 18), (30000, 20)):
        config = copy.deepcopy(best_animal)
        config.update({
            "conditional_second_land": True,
            "max_land_purchases": 2,
            "second_land_min_day": day,
            "second_land_bank_threshold": threshold,
            "second_land_opponent_trigger": True,
            "second_land_roi_hurdle": 0.10,
        })
        land_variants[f"land_second_bank{threshold}_day{day}"] = _config_spec(config)
    lands = _evaluate(
        "conditional_land_search", land_variants, hard, range(10050, 10052), workers
    )
    best_land = copy.deepcopy(lands["results"][0]["spec"]["config"])

    architectures = {
        "P0_current_best": _path_spec(CURRENT_BEST),
        "P1_full_farm": _config_spec(_planner_config(False, False)),
        "P2_opponent": _config_spec(_planner_config(True, False)),
        "P3_self_impact": _config_spec(p3),
        "P4_staggered": _config_spec(best_cohort),
        "P5_forecast_selling": _config_spec(best_selling),
        "P6_animal_capital": _config_spec(best_animal),
        "P7_conditional_land": _config_spec(best_land),
    }
    architecture_search = _evaluate(
        "architecture_search", architectures, league, range(10060, 10062), workers
    )
    serious_names = _select_distinct_serious(architecture_search, architectures)
    serious = {name: architectures[name] for name in serious_names}
    heldout = _evaluate(
        "heldout_confirmation", serious, league, range(10100, 10105), workers
    )

    result = {
        "schema_version": 1,
        "experiment": "full_farm_planner_league",
        "engine": str(ENGINE_PATH.relative_to(ROOT)),
        "engine_sha256": _file_sha256(ENGINE_PATH),
        "frozen_best": str(CURRENT_BEST.relative_to(ROOT)),
        "frozen_best_sha256": _file_sha256(CURRENT_BEST),
        "seed_partitions": {
            "adversarial": [10000, 10003],
            "component_development": [10020, 10051],
            "architecture_search": [10060, 10061],
            "heldout": [10100, 10104],
        },
        "generated_count": len(generated),
        "selected_adversaries": selected_names,
        "league": league,
        "architectures": architectures,
        "serious_candidates": serious_names,
        "stages": [adversarial, cohorts, selling, animals, lands,
                   architecture_search, heldout],
    }
    json_path = EXPERIMENTS_DIR / "planner_league_results.json"
    md_path = EXPERIMENTS_DIR / "planner_league_results.md"
    league_path = EXPERIMENTS_DIR / "policy_league.json"
    json_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    league_path.write_text(json.dumps({
        "schema_version": 1,
        "historical": HISTORICAL_LEAGUE,
        "generated_search_count": len(generated),
        "selected_generated": selected,
        "league": league,
        "adversarial_search": adversarial,
    }, indent=2) + "\n", encoding="utf-8")
    _write_markdown(md_path, result)
    print(f"Saved {json_path}")
    print(f"Saved {md_path}")
    print(f"Saved {league_path}")
    for row in heldout["results"]:
        o = row["overall"]
        direct = row["matchups"]["animal_c2_land_day14"]
        print(
            f"HELDOUT {row['candidate']} {o['wins']}/{o['losses']}/{o['ties']} "
            f"money={o['average_money']:.1f} adv={o['average_advantage']:+.1f} "
            f"p10={o['p10_advantage']:+.1f} direct={direct['wins']}/{direct['losses']}/{direct['ties']} "
            f"{direct['average_advantage']:+.1f}"
        )
    return result


def complete_distinct_heldout(workers):
    """Replace a duplicate finalist with the next distinct architecture only."""
    json_path = EXPERIMENTS_DIR / "planner_league_results.json"
    md_path = EXPERIMENTS_DIR / "planner_league_results.md"
    result = json.loads(json_path.read_text(encoding="utf-8"))
    stages = {stage["stage"]: stage for stage in result["stages"]}
    architecture_search = stages["architecture_search"]
    heldout = stages["heldout_confirmation"]
    architectures = result["architectures"]
    league = result["league"]
    serious_names = _select_distinct_serious(architecture_search, architectures)
    retained_games = [
        game for game in heldout["games"] if game["candidate"] in serious_names
    ]
    completed = {game["candidate"] for game in retained_games}
    missing = {
        name: architectures[name] for name in serious_names if name not in completed
    }
    if missing:
        added = _evaluate(
            "heldout_distinct_completion", missing, league, range(10100, 10105), workers
        )
        retained_games.extend(added["games"])
    heldout["games"] = retained_games
    heldout["results"] = [
        _result(
            name,
            architectures[name],
            [game for game in retained_games if game["candidate"] == name],
            league,
        )
        for name in serious_names
    ]
    heldout["results"].sort(key=lambda row: row["search_score"], reverse=True)
    heldout["games_per_candidate"] = len(league) * 10
    result["serious_candidates"] = serious_names
    json_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    _write_markdown(md_path, result)
    print(f"Saved {json_path}")
    print(f"Saved {md_path}")
    for row in heldout["results"]:
        o = row["overall"]
        direct = row["matchups"]["animal_c2_land_day14"]
        print(
            f"HELDOUT {row['candidate']} {o['wins']}/{o['losses']}/{o['ties']} "
            f"money={o['average_money']:.1f} adv={o['average_advantage']:+.1f} "
            f"p10={o['p10_advantage']:+.1f} "
            f"direct={direct['wins']}/{direct['losses']}/{direct['ties']} "
            f"{direct['average_advantage']:+.1f}"
        )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument(
        "--complete-distinct-heldout",
        action="store_true",
        help="evaluate only a missing distinct held-out finalist",
    )
    args = parser.parse_args()
    if args.complete_distinct_heldout:
        complete_distinct_heldout(args.workers)
    else:
        run(args.workers)


if __name__ == "__main__":
    main()
