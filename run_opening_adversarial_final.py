"""Fresh-seed adversarial validation for the frozen public-compounding opening."""

from __future__ import annotations

import json
import statistics
from collections import Counter
from pathlib import Path
from runpy import run_path

from kaggle_environments import make

from analyze_top_player_replays import _transition_ledger
from test_economic_agents import SELLABLE, _validate_action


ROOT = Path(__file__).resolve().parent
SOURCE_PATH = "agents/opening_public_front_cow8_day6.py"
SEEDS = tuple(range(731001, 731009))
OPPONENTS = {
    # Direct pressure on the opening's three animal-derived capital bridges.
    "sheep_wool_heavy": "agents/router_meta_sheep_only.py",
    "sheep_to_cow": "agents/router_meta_sheep_to_cow.py",
    "cow_milk_heavy": "agents/router_meta_cow_only.py",
    "fertilizer_liquidator": "agents/router_meta_mixed_throughout.py",
    # Early deed and deployment pressure.
    "land_day5_day9": "agents/router_replay_land_5_9.py",
    "fast_land_high_labor": "agents/replay_archetypes/fast_land_high_labor.py",
    "high_labor": "agents/proxies/high_labor.py",
    # Required controls.
    "top_meta_mirror": SOURCE_PATH,
    "frozen_router": "agents/router_replay_hands12.py",
    # Hard agents retained from earlier frozen leagues.
    "livestock_crop": "agents/proxies/livestock_crop.py",
    "land_expander": "agents/proxies/land_expander.py",
    "phased_rotation": "agents/proxies/phased_rotation.py",
    "melon_heavy": "agents/proxies/melon_heavy.py",
    "gen_land_d8": "agents/adversaries/gen_land_d8_labor6.py",
    "gen_cow6_d8": "agents/adversaries/gen_cow6_d8.py",
    "conditional_land_planner": "agents/planner_p7_conditional_land.py",
}
VALUABLE = set(SELLABLE) | {"COW", "SHEEP", "GOOSE"}
_CACHE = {}


def _load(path):
    if path not in _CACHE:
        _CACHE[path] = run_path(str(ROOT / path))["agent"]
    return _CACHE[path]


def _animal_counts(obs):
    player = obs["player"]
    farm = obs["farms"][player]
    result = Counter()
    for row in farm["tiles"]:
        for tile in row:
            if isinstance(tile, dict) and tile.get("animal"):
                result[tile["animal"]] += 1
    private = obs["private"]
    for animal in ("COW", "SHEEP", "GOOSE"):
        result[animal] += private["shed"].get(animal, 0)
        result[animal] += sum(inv.get(animal, 0) for inv in private["inventories"])
    return result


def _stranded_value(final_obs):
    private = final_obs["private"]
    counts = Counter()
    for item in VALUABLE:
        counts[item] += private["shed"].get(item, 0)
        counts[item] += sum(inv.get(item, 0) for inv in private["inventories"])
    # Unharvested animal output is also immediately realizable value.
    player = final_obs["player"]
    for row in final_obs["farms"][player]["tiles"]:
        for tile in row:
            if isinstance(tile, dict) and tile.get("animal") and tile.get("yield_units", 0) > 0:
                product = {"COW": "MILK", "SHEEP": "WOOL", "GOOSE": "EGG"}[tile["animal"]]
                counts[product] += tile["yield_units"]
    return {item: count for item, count in sorted(counts.items()) if count}


def _run(opponent_name, opponent_path, seed, seat):
    base = _load(SOURCE_PATH)
    peak = Counter()

    def checked(obs):
        action = base(obs)
        _validate_action(obs, action)
        counts = _animal_counts(obs)
        for animal in ("COW", "SHEEP", "GOOSE"):
            peak[animal] = max(peak[animal], counts[animal])
        return action

    pair = [_load(opponent_path), _load(opponent_path)]
    pair[seat] = checked
    env = make(
        "kaggriculture",
        configuration={"episodeSteps": 720, "seed": seed},
        debug=True,
    )
    env.run(pair)
    final = env.steps[-1]
    statuses = [state.status for state in final]
    if len(env.steps) != 720 or statuses != ["DONE", "DONE"]:
        raise RuntimeError(
            f"failed {opponent_name}/{seed}/seat{seat}: "
            f"turns={len(env.steps)} statuses={statuses}"
        )

    replay = env.toJSON()
    land_days = []
    revenue = Counter()
    mismatches = []
    for step in range(1, len(replay["steps"])):
        previous = replay["steps"][step - 1]
        current = replay["steps"][step]
        ledgers, errors = _transition_ledger(previous, current, replay["configuration"])
        mismatches.extend(errors)
        day = int(previous[0]["observation"]["day"])
        ledger = ledgers[seat]
        land_days.extend([day] * int(ledger["land_count"]))
        if day in (6, 7):
            revenue["WOOL_D6_D7"] += ledger["sale_revenue"]["WOOL"]
        if day == 9:
            revenue["MILK_D9"] += ledger["sale_revenue"]["MILK"]
        if day in (9, 10):
            revenue["MILK_D9_D10"] += ledger["sale_revenue"]["MILK"]
    if mismatches:
        raise AssertionError(
            f"financial reconstruction mismatch in {opponent_name}/{seed}/seat{seat}: "
            f"{mismatches[:3]}"
        )

    final_obs = final[seat].observation
    final_counts = _animal_counts(final_obs)
    money = float(final[seat].reward)
    opponent_money = float(final[1 - seat].reward)
    return {
        "opponent": opponent_name,
        "opponent_path": opponent_path,
        "seed": seed,
        "seat": seat,
        "money": money,
        "opponent_money": opponent_money,
        "advantage": money - opponent_money,
        "first_land_by_day6": len(land_days) >= 1 and land_days[0] <= 6,
        "second_land_by_day10": len(land_days) >= 2 and land_days[1] <= 10,
        "land_purchase_days": land_days,
        "wool_revenue_day6_7": revenue["WOOL_D6_D7"],
        "milk_revenue_day9": revenue["MILK_D9"],
        "milk_revenue_day9_10": revenue["MILK_D9_D10"],
        "peak_animals": {animal: peak[animal] for animal in ("COW", "SHEEP", "GOOSE")},
        "final_animals": {animal: final_counts[animal] for animal in ("COW", "SHEEP", "GOOSE")},
        "livestock_losses": {
            animal: peak[animal] - final_counts[animal]
            for animal in ("COW", "SHEEP", "GOOSE")
        },
        "stranded_inventory": _stranded_value(final_obs),
    }


def _percentile(values, fraction):
    values = sorted(values)
    point = fraction * (len(values) - 1)
    lower = int(point)
    upper = min(lower + 1, len(values) - 1)
    weight = point - lower
    return values[lower] * (1 - weight) + values[upper] * weight


def _summarize(games):
    advantages = [game["advantage"] for game in games]
    wins = sum(value > 0 for value in advantages)
    losses = sum(value < 0 for value in advantages)
    ties = len(games) - wins - losses
    paired = {}
    for game in games:
        paired.setdefault(game["seed"], []).append(game["advantage"])
    paired_advantages = [statistics.fmean(values) for values in paired.values()]
    stranded_counts = [sum(game["stranded_inventory"].values()) for game in games]
    return {
        "games": len(games),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "score_rate": (wins + 0.5 * ties) / len(games),
        "average_money": statistics.fmean(game["money"] for game in games),
        "average_advantage": statistics.fmean(advantages),
        "p10_paired_advantage": _percentile(paired_advantages, 0.10),
        "first_land_by_day6_rate": statistics.fmean(game["first_land_by_day6"] for game in games),
        "second_land_by_day10_rate": statistics.fmean(game["second_land_by_day10"] for game in games),
        "average_wool_revenue_day6_7": statistics.fmean(game["wool_revenue_day6_7"] for game in games),
        "minimum_wool_revenue_day6_7": min(game["wool_revenue_day6_7"] for game in games),
        "average_milk_revenue_day9": statistics.fmean(game["milk_revenue_day9"] for game in games),
        "minimum_milk_revenue_day9": min(game["milk_revenue_day9"] for game in games),
        "average_milk_revenue_day9_10": statistics.fmean(game["milk_revenue_day9_10"] for game in games),
        "minimum_milk_revenue_day9_10": min(game["milk_revenue_day9_10"] for game in games),
        "total_livestock_losses": {
            animal: sum(game["livestock_losses"][animal] for game in games)
            for animal in ("COW", "SHEEP", "GOOSE")
        },
        "games_with_livestock_loss": sum(any(game["livestock_losses"].values()) for game in games),
        "games_with_stranded_inventory": sum(bool(value) for value in stranded_counts),
        "average_stranded_inventory": statistics.fmean(stranded_counts),
        "maximum_stranded_inventory": max(stranded_counts),
    }


def _markdown(payload):
    overall = payload["overall"]
    lines = [
        "# Final opening adversarial validation",
        "",
        f"Frozen source: `{SOURCE_PATH}`. Seeds {SEEDS[0]}-{SEEDS[-1]} were fresh and used in both seats.",
        "",
        "## Overall",
        "",
        f"- W/L/T: **{overall['wins']}/{overall['losses']}/{overall['ties']}**",
        f"- Average money: **{overall['average_money']:.0f}**",
        f"- Average advantage: **{overall['average_advantage']:+.0f}**",
        f"- P10 paired advantage: **{overall['p10_paired_advantage']:+.0f}**",
        f"- First land by day 6: **{overall['first_land_by_day6_rate']:.1%}**",
        f"- Second land by day 10: **{overall['second_land_by_day10_rate']:.1%}**",
        f"- Wool revenue days 6-7: **{overall['average_wool_revenue_day6_7']:.0f} avg**",
        f"- Milk revenue day 9: **{overall['average_milk_revenue_day9']:.0f} avg**; days 9-10 window: **{overall['average_milk_revenue_day9_10']:.0f} avg**",
        "",
        "## Matchups",
        "",
        "| Opponent | W/L/T | Avg money | Avg advantage | P10 | Land d6 | Land d10 | Wool d6-7 | Milk d9 / d9-10 | Animal-loss games | Stranded max |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, row in payload["matchups"].items():
        lines.append(
            f"| {name} | {row['wins']}/{row['losses']}/{row['ties']} | "
            f"{row['average_money']:.0f} | {row['average_advantage']:+.0f} | "
            f"{row['p10_paired_advantage']:+.0f} | {row['first_land_by_day6_rate']:.0%} | "
            f"{row['second_land_by_day10_rate']:.0%} | {row['average_wool_revenue_day6_7']:.0f} | "
            f"{row['average_milk_revenue_day9']:.0f} / {row['average_milk_revenue_day9_10']:.0f} | {row['games_with_livestock_loss']} | "
            f"{row['maximum_stranded_inventory']} |"
        )
    lines.extend(
        [
            "",
            f"Worst matchup: **{payload['worst_matchup']}**.",
            "",
            "The JSON artifact contains every game, exact successful land-purchase days, realized animal-product revenue, losses, and final stranded inventory by item.",
        ]
    )
    return "\n".join(lines) + "\n"


def main():
    games = []
    total = len(OPPONENTS) * len(SEEDS) * 2
    for opponent_name, opponent_path in OPPONENTS.items():
        for seed in SEEDS:
            for seat in (0, 1):
                games.append(_run(opponent_name, opponent_path, seed, seat))
                if len(games) % 16 == 0 or len(games) == total:
                    print(f"adversarial {len(games)}/{total}", flush=True)
    matchups = {
        name: _summarize([game for game in games if game["opponent"] == name])
        for name in OPPONENTS
    }
    worst = min(
        matchups,
        key=lambda name: (matchups[name]["score_rate"], matchups[name]["average_advantage"]),
    )
    payload = {
        "schema_version": 1,
        "experiment": "final_opening_adversarial_validation",
        "source": SOURCE_PATH,
        "fresh_seeds": list(SEEDS),
        "both_seats": True,
        "opponents": OPPONENTS,
        "overall": _summarize(games),
        "matchups": matchups,
        "worst_matchup": worst,
        "games": games,
    }
    json_path = ROOT / "experiments" / "opening_adversarial_final.json"
    md_path = ROOT / "experiments" / "opening_adversarial_final.md"
    json_path.write_text(json.dumps(payload, indent=2) + "\n")
    md_path.write_text(_markdown(payload))
    print(json_path)
    print(md_path)
    print(json.dumps({"overall": payload["overall"], "worst": worst}, indent=2))


if __name__ == "__main__":
    main()
