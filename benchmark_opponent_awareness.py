"""Deterministic opponent-awareness ablations with causal economic metrics.

Examples:
    python benchmark_opponent_awareness.py --stage dev
    python benchmark_opponent_awareness.py --stage selection --candidate O0 --candidate O1
    python benchmark_opponent_awareness.py --stage final --candidate O0 --candidate O1
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from runpy import run_path

from kaggle_environments import make

from analyze_top_player_replays import _transition_ledger
from benchmark import DEFAULT_WORKERS, EPISODE_STEPS, ROOT, _file_sha256, _load_agent
from test_economic_agents import SELLABLE, _validate_action


EXPERIMENTS = ROOT / "experiments"
CANDIDATES = {
    "O0": ROOT / "agents" / "router_replay_hands12.py",
    "O1": ROOT / "agents" / "opponent_o1_crop.py",
    "O2": ROOT / "agents" / "opponent_o2_selling.py",
    "O3": ROOT / "agents" / "opponent_o3_reinvestment.py",
    "O4": ROOT / "agents" / "opponent_o4_crop_selling.py",
    "O5": ROOT / "agents" / "opponent_o5_full.py",
}
REPLAY_ARCHETYPES = {
    "replay_fixed_template": ROOT / "agents" / "router_r3_replay_economy.py",
    "replay_strawberry_scaler": ROOT / "agents" / "replay_archetypes" / "aggressive_strawberry_scaler.py",
    "replay_fast_land_high_labor": ROOT / "agents" / "replay_archetypes" / "fast_land_high_labor.py",
    "replay_livestock_heavy": ROOT / "agents" / "replay_archetypes" / "livestock_heavy_scaler.py",
    "replay_early_supply_dump": ROOT / "agents" / "replay_archetypes" / "early_supply_dump.py",
    "replay_rapid_reinvestment": ROOT / "agents" / "replay_archetypes" / "rapid_sell_reinvestment.py",
}
HARD_LEAGUE = {
    "gen_cow6_d8": ROOT / "agents" / "adversaries" / "gen_cow6_d8.py",
    "gen_land_d11_labor7_sell12": ROOT / "agents" / "adversaries" / "gen_land_d11_labor7_sell12.py",
    "gen_land_d8_labor6": ROOT / "agents" / "adversaries" / "gen_land_d8_labor6.py",
    "red_cow8_d12_mirror": ROOT / "agents" / "animal_c8_day12_land_day11.py",
    "red_stage_4_to_8_day15": ROOT / "agents" / "adversaries" / "red_stage_4_to_8_day15.py",
    "red_c8_bank11000": ROOT / "agents" / "adversaries" / "red_c8_bank11000.py",
    "proxy_livestock_crop": ROOT / "agents" / "proxies" / "livestock_crop.py",
    "proxy_high_labor": ROOT / "agents" / "proxies" / "high_labor.py",
    "proxy_land_expander": ROOT / "agents" / "proxies" / "land_expander.py",
    "proxy_phased_rotation": ROOT / "agents" / "proxies" / "phased_rotation.py",
    "animal_c2_cows": ROOT / "agents" / "animal_c2_cows.py",
    "animal_c4_early_cows": ROOT / "agents" / "animal_c4_tuned_cows.py",
}
FULL_POOL = {"O0_direct": CANDIDATES["O0"], **REPLAY_ARCHETYPES, **HARD_LEAGUE}
RED_TEAM = {
    "fake_pressure_delayed_sale": ROOT / "agents" / "proxies" / "inventory_holder.py",
    "diversified_pressure": ROOT / "agents" / "proxies" / "mixed_crop.py",
    "mirror_switching": CANDIDATES["O1"],
    "aggressive_early_expansion": REPLAY_ARCHETYPES["replay_fast_land_high_labor"],
    "aggressive_livestock": REPLAY_ARCHETYPES["replay_livestock_heavy"],
    "fixed_high_quality_template": REPLAY_ARCHETYPES["replay_fixed_template"],
}
STAGE_SEEDS = {
    "dev": tuple(range(12000, 12003)),
    "selection": tuple(range(13000, 13006)),
    "final": tuple(range(14000, 14016)),
    "redteam": tuple(range(15000, 15016)),
}
CONFIGURATION = {"episodeSteps": EPISODE_STEPS}
PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
CROPS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")


def _percentile(values, fraction):
    if not values:
        return None
    values = sorted(values)
    if len(values) == 1:
        return values[0]
    position = fraction * (len(values) - 1)
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    weight = position - lower
    return values[lower] * (1 - weight) + values[upper] * weight


def _serialize_metrics(metrics):
    if not metrics:
        return {}
    return json.loads(json.dumps(metrics))


def _economic_metrics(env, position, candidate_metrics):
    sale_quantity = Counter()
    sale_revenue = Counter()
    sale_prices = defaultdict(list)
    crop_harvest = Counter()
    plantings = Counter()
    unsold = Counter()
    unsold_unit_turns = 0
    sale_events = []
    invalid_actions = 0
    configuration = dict(env.configuration)
    for index in range(1, len(env.steps)):
        prior = env.steps[index - 1][position]["observation"]
        action = env.steps[index][position].get("action") or {}
        try:
            _validate_action(prior, action)
        except AssertionError:
            invalid_actions += 1
        ledgers, mismatches = _transition_ledger(
            env.steps[index - 1], env.steps[index], configuration
        )
        if mismatches:
            raise RuntimeError(f"financial reconstruction mismatch at step {index}: {mismatches}")
        ledger = ledgers[position]
        sale_quantity.update(ledger["sale_quantity"])
        sale_revenue.update(ledger["sale_revenue"])
        crop_harvest.update(ledger["harvest_quantity"])
        plantings.update(ledger["plant_quantity"])
        for product, quantity in ledger["harvest_quantity"].items():
            unsold[product] += quantity
        for product, quantity in ledger["sale_quantity"].items():
            unsold[product] = max(0, unsold[product] - quantity)
            prices = list(ledger["sale_prices"][product])
            sale_prices[product].extend(prices)
            sale_events.append(
                {
                    "step": index - 1,
                    "product": product,
                    "quantity": quantity,
                    "average_price": statistics.fmean(prices),
                }
            )
        unsold_unit_turns += sum(unsold[product] for product in PRODUCTS)
    successful_pre_shock_quantity = Counter()
    for event in sale_events:
        future_index = min(len(env.steps) - 1, event["step"] + 48)
        future_price = env.steps[future_index][position]["observation"]["market"]["prices"][event["product"]]
        if future_price <= event["average_price"] * 0.85:
            successful_pre_shock_quantity[event["product"]] += event["quantity"]
    final_obs = env.steps[-1][position]["observation"]
    private = final_obs["private"]
    stranded = sum(private["shed"].get(item, 0) for item in SELLABLE)
    stranded += sum(
        inventory.get(item, 0)
        for inventory in private["inventories"] for item in SELLABLE
    )
    stranded += sum(
        int(tile.get("yield_units", 0))
        for row in final_obs["farms"][position]["tiles"] for tile in row
        if isinstance(tile, dict) and tile.get("animal")
    )
    realized_prices = {
        product: sale_revenue[product] / sale_quantity[product]
        for product in sale_quantity if sale_quantity[product]
    }
    return {
        "crop_revenue": {crop: sale_revenue[crop] for crop in CROPS if sale_revenue[crop]},
        "sale_quantity": dict(sale_quantity),
        "sale_revenue": dict(sale_revenue),
        "realized_average_price": realized_prices,
        "harvest_quantity": dict(crop_harvest),
        "plantings": dict(plantings),
        "estimated_unsold_unit_turns": unsold_unit_turns,
        "estimated_average_holding_turns": unsold_unit_turns / max(1, sum(sale_quantity.values())),
        "successful_pre_shock_quantity": dict(successful_pre_shock_quantity),
        "invalid_actions": invalid_actions,
        "stranded_endgame_units": stranded,
        "agent_instrumentation": _serialize_metrics(candidate_metrics),
    }


def _run_game(job):
    candidate_name, candidate_path, opponent_name, opponent_path, seed, position = job
    candidate = _load_agent(candidate_path)
    # A stateful opponent-aware mirror must have its own module state when the
    # same path occupies both seats.  Frozen/stateless paths can use the cache.
    opponent = (
        run_path(opponent_path)["agent"]
        if opponent_path == candidate_path
        else _load_agent(opponent_path)
    )
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
            f"failed {candidate_name} vs {opponent_name}, seed={seed}, seat={position}: "
            f"turns={len(env.steps)} statuses={statuses}"
        )
    metrics = candidate.get_metrics() if hasattr(candidate, "get_metrics") else {}
    economics = _economic_metrics(env, position, metrics)
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
        "advantage": candidate_money - opponent_money,
        "economics": economics,
    }


def _basic_summary(games):
    advantages = [game["advantage"] for game in games]
    money = [game["candidate_money"] for game in games]
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
        "median_money": statistics.median(money),
        "average_opponent_money": statistics.fmean(game["opponent_money"] for game in games),
        "average_advantage": statistics.fmean(advantages),
        "median_advantage": statistics.median(advantages),
        "p10_advantage": _percentile(advantages, 0.10),
        "money_variance": statistics.variance(money) if len(money) > 1 else 0.0,
        "advantage_variance": statistics.variance(advantages) if len(advantages) > 1 else 0.0,
    }


def _strategy_summary(games):
    crop_revenue = Counter()
    sale_quantity = Counter()
    sale_revenue = Counter()
    pre_shock = Counter()
    holding_turns = []
    switches = 0
    switched_games = 0
    hold_events = 0
    relative_hires = 0
    invalid = stranded = 0
    relative_by_day = defaultdict(list)
    for game in games:
        economics = game["economics"]
        crop_revenue.update(economics["crop_revenue"])
        sale_quantity.update(economics["sale_quantity"])
        sale_revenue.update(economics["sale_revenue"])
        pre_shock.update(economics["successful_pre_shock_quantity"])
        holding_turns.append(economics["estimated_average_holding_turns"])
        invalid += economics["invalid_actions"]
        stranded += economics["stranded_endgame_units"]
        instrumentation = economics.get("agent_instrumentation", {})
        game_switches = int(instrumentation.get("crop_switches", 0))
        switches += game_switches
        switched_games += game_switches > 0
        hold_events += int(instrumentation.get("hold_events", 0))
        relative_hires += int(instrumentation.get("relative_hires_added", 0))
        for row in instrumentation.get("relative_state_by_day", []):
            relative_by_day[int(row["day"])].append(row)
    realized = {
        product: sale_revenue[product] / sale_quantity[product]
        for product in sale_quantity if sale_quantity[product]
    }
    relative = []
    for day, rows in sorted(relative_by_day.items()):
        relative.append(
            {
                "day": day,
                **{
                    key: statistics.fmean(float(row[key]) for row in rows)
                    for key in ("bank_gap", "land_gap", "labor_gap", "productive_gap", "livestock_gap")
                },
            }
        )
    return {
        "average_crop_revenue": {
            crop: crop_revenue[crop] / len(games) for crop in CROPS
        },
        "realized_average_selling_price": realized,
        "average_estimated_holding_turns": statistics.fmean(holding_turns),
        "successful_pre_shock_sale_quantity": dict(pre_shock),
        "crop_switches": switches,
        "games_with_crop_switches": switched_games,
        "hold_events": hold_events,
        "relative_hires_added": relative_hires,
        "invalid_actions": invalid,
        "stranded_endgame_units": stranded,
        "average_relative_state_by_day": relative,
    }


def _candidate_summary(candidate, games, opponents):
    matchups = {
        opponent: _basic_summary([game for game in games if game["opponent"] == opponent])
        for opponent in opponents
    }
    worst_name, worst = min(
        matchups.items(),
        key=lambda item: (item[1]["score_rate"], item[1]["p10_advantage"], item[1]["average_advantage"]),
    )
    return {
        "candidate": candidate,
        "overall": _basic_summary(games),
        "strategy_metrics": _strategy_summary(games),
        "matchups": matchups,
        "worst_matchup": {"opponent": worst_name, **worst},
    }


def _paired_causal_deltas(games, candidates):
    by_key = {
        (game["candidate"], game["opponent"], game["seed"], game["candidate_position"]): game
        for game in games
    }
    output = {}
    for candidate in candidates:
        if candidate == "O0":
            continue
        rows = []
        for key, game in by_key.items():
            if key[0] != candidate:
                continue
            control = by_key.get(("O0", key[1], key[2], key[3]))
            if control is None:
                continue
            switched = game["economics"].get("agent_instrumentation", {}).get("crop_switches", 0) > 0
            candidate_crop = sum(game["economics"]["crop_revenue"].values())
            control_crop = sum(control["economics"]["crop_revenue"].values())
            rows.append(
                {
                    "money_delta": game["candidate_money"] - control["candidate_money"],
                    "crop_revenue_delta": candidate_crop - control_crop,
                    "switched": switched,
                }
            )
        output[candidate] = {
            "paired_games": len(rows),
            "average_money_delta_vs_O0_same_conditions": statistics.fmean(row["money_delta"] for row in rows) if rows else None,
            "average_crop_revenue_delta_vs_O0": statistics.fmean(row["crop_revenue_delta"] for row in rows) if rows else None,
            "switch_games": sum(row["switched"] for row in rows),
            "average_money_delta_when_switched": statistics.fmean(row["money_delta"] for row in rows if row["switched"]) if any(row["switched"] for row in rows) else None,
            "average_crop_revenue_delta_when_switched": statistics.fmean(row["crop_revenue_delta"] for row in rows if row["switched"]) if any(row["switched"] for row in rows) else None,
        }
    return output


def _markdown(result):
    lines = [
        f"# Opponent-awareness benchmark — {result['stage']}",
        "",
        f"Seeds: {result['seeds']} (both seats); opponents: {len(result['opponents'])}.",
        "",
        "| Candidate | W/L/T | Win rate | Avg money | Avg advantage | P10 advantage | Variance | Worst matchup | Switches | Holds | Extra hires |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |",
    ]
    for name in result["candidates"]:
        row = result["candidate_results"][name]
        overall = row["overall"]
        metrics = row["strategy_metrics"]
        worst = row["worst_matchup"]
        lines.append(
            f"| {name} | {overall['wins']}/{overall['losses']}/{overall['ties']} | "
            f"{overall['win_rate'] * 100:.1f}% | {overall['average_money']:.0f} | "
            f"{overall['average_advantage']:+.0f} | {overall['p10_advantage']:+.0f} | "
            f"{overall['money_variance']:.0f} | {worst['opponent']} "
            f"({worst['average_advantage']:+.0f}) | {metrics['crop_switches']} | "
            f"{metrics['hold_events']} | {metrics['relative_hires_added']} |"
        )
    lines.extend(["", "## Matchups", ""])
    for name in result["candidates"]:
        lines.extend(
            [
                f"### {name}",
                "",
                "| Opponent | W/L/T | Avg money | Avg advantage | P10 |",
                "| --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for opponent, row in result["candidate_results"][name]["matchups"].items():
            lines.append(
                f"| {opponent} | {row['wins']}/{row['losses']}/{row['ties']} | "
                f"{row['average_money']:.0f} | {row['average_advantage']:+.0f} | "
                f"{row['p10_advantage']:+.0f} |"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def run(stage, candidate_names, workers, seeds=None, pool_name="full", stem=None):
    if stage not in STAGE_SEEDS:
        raise ValueError(stage)
    selected_seeds = tuple(seeds) if seeds is not None else STAGE_SEEDS[stage]
    opponents = RED_TEAM if pool_name == "redteam" else FULL_POOL
    candidates = {name: CANDIDATES[name] for name in candidate_names}
    jobs = [
        (candidate, str(path), opponent, str(opponent_path), seed, position)
        for candidate, path in candidates.items()
        for opponent, opponent_path in opponents.items()
        for seed in selected_seeds
        for position in (0, 1)
    ]
    print(
        f"Running {len(jobs)} games: candidates={list(candidates)}, "
        f"opponents={len(opponents)}, seeds={len(selected_seeds)}, seats=2",
        flush=True,
    )
    games = []
    if workers == 1:
        for index, job in enumerate(jobs, 1):
            games.append(_run_game(job))
            if index % 20 == 0 or index == len(jobs):
                print(f"  completed {index}/{len(jobs)}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(_run_game, job) for job in jobs]
            for index, future in enumerate(as_completed(futures), 1):
                games.append(future.result())
                if index % 20 == 0 or index == len(jobs):
                    print(f"  completed {index}/{len(jobs)}", flush=True)
    games.sort(key=lambda row: (row["candidate"], row["opponent"], row["seed"], row["candidate_position"]))
    candidate_results = {
        name: _candidate_summary(name, [game for game in games if game["candidate"] == name], opponents)
        for name in candidates
    }
    result = {
        "schema_version": 1,
        "experiment": "opponent_awareness_ablation",
        "stage": stage,
        "pool": pool_name,
        "seeds": list(selected_seeds),
        "both_seats": True,
        "candidates": list(candidates),
        "candidate_paths": {name: str(path.relative_to(ROOT)) for name, path in candidates.items()},
        "candidate_sha256": {name: _file_sha256(path) for name, path in candidates.items()},
        "opponents": list(opponents),
        "opponent_paths": {name: str(path.relative_to(ROOT)) for name, path in opponents.items()},
        "opponent_sha256": {name: _file_sha256(path) for name, path in opponents.items()},
        "candidate_results": candidate_results,
        "paired_causal_deltas": _paired_causal_deltas(games, candidates),
        "games": games,
    }
    if stem is None:
        stem = f"opponent_awareness_{stage}_{pool_name}"
    json_path = EXPERIMENTS / f"{stem}.json"
    md_path = EXPERIMENTS / f"{stem}.md"
    json_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(_markdown(result), encoding="utf-8")
    for name, row in candidate_results.items():
        overall = row["overall"]
        print(
            f"{name}: W/L/T={overall['wins']}/{overall['losses']}/{overall['ties']} "
            f"win={overall['win_rate'] * 100:.1f}% money={overall['average_money']:.0f} "
            f"adv={overall['average_advantage']:+.0f} p10={overall['p10_advantage']:+.0f} "
            f"worst={row['worst_matchup']['opponent']}",
            flush=True,
        )
    print(f"Saved {json_path}")
    print(f"Saved {md_path}")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=tuple(STAGE_SEEDS), default="dev")
    parser.add_argument("--candidate", action="append", dest="candidates")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--seed-count", type=int)
    parser.add_argument("--pool", choices=("full", "redteam"), default="full")
    parser.add_argument("--stem")
    args = parser.parse_args()
    candidates = args.candidates or list(CANDIDATES)
    unknown = set(candidates) - set(CANDIDATES)
    if unknown:
        parser.error(f"unknown candidates: {sorted(unknown)}")
    seeds = STAGE_SEEDS[args.stage]
    if args.seed_count is not None:
        if args.seed_count < 1:
            parser.error("--seed-count must be positive")
        seeds = seeds[: args.seed_count]
    run(args.stage, candidates, args.workers, seeds, args.pool, args.stem)


if __name__ == "__main__":
    main()
