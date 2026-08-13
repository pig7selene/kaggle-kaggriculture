"""Full-season validation and fresh held-out confirmation for opening finalists."""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from runpy import run_path

from kaggle_environments import make

from test_economic_agents import _validate_action


ROOT = Path(__file__).resolve().parent
CANDIDATES = {
    "frozen_current": "agents/router_replay_hands12.py",
    "front_day0_hires": "agents/opening_public_front_hires.py",
    "front_cow8_day6": "agents/opening_public_front_cow8_day6.py",
}
OPPONENTS = {
    "frozen_current": "agents/router_replay_hands12.py",
    "livestock_crop": "agents/proxies/livestock_crop.py",
    "high_labor": "agents/proxies/high_labor.py",
    "land_expander": "agents/proxies/land_expander.py",
    "phased_rotation": "agents/proxies/phased_rotation.py",
    "melon_heavy": "agents/proxies/melon_heavy.py",
    "gen_land_d8": "agents/adversaries/gen_land_d8_labor6.py",
    "gen_cow6_d8": "agents/adversaries/gen_cow6_d8.py",
}
VALIDATION_SEEDS = tuple(range(15000, 15006))
HELDOUT_SEEDS = tuple(range(15100, 15108))
VALUABLE = {
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
    "EGG", "MILK", "WOOL", "FERTILIZER", "COW", "SHEEP", "GOOSE",
}
_CACHE = {}


def _agent(path):
    if path not in _CACHE:
        _CACHE[path] = run_path(str(ROOT / path))["agent"]
    return _CACHE[path]


def _animals(farm):
    result = {"COW": 0, "SHEEP": 0, "GOOSE": 0}
    for row in farm["tiles"]:
        for tile in row:
            if isinstance(tile, dict) and tile.get("animal"):
                result[tile["animal"]] += 1
    return result


def _run(candidate, candidate_path, opponent, opponent_path, seed, seat):
    base = _agent(candidate_path)
    peak = {"COW": 0, "SHEEP": 0, "GOOSE": 0}

    def checked(obs):
        action = base(obs)
        _validate_action(obs, action)
        counts = _animals(obs["farms"][obs["player"]])
        for animal in peak:
            peak[animal] = max(peak[animal], counts[animal])
        return action

    agents = [_agent(opponent_path), _agent(opponent_path)]
    agents[seat] = checked
    env = make(
        "kaggriculture",
        configuration={"episodeSteps": 720, "seed": seed},
        debug=True,
    )
    env.run(agents)
    final = env.steps[-1]
    statuses = [state.status for state in final]
    if len(env.steps) != 720 or statuses != ["DONE", "DONE"]:
        raise RuntimeError(
            f"failed {candidate}/{opponent}/{seed}/seat{seat}: "
            f"steps={len(env.steps)} statuses={statuses}"
        )
    money = float(final[seat].reward)
    opponent_money = float(final[1 - seat].reward)
    private = final[seat].observation["private"]
    stranded = sum(private["shed"].get(item, 0) for item in VALUABLE)
    stranded += sum(
        inventory.get(item, 0)
        for inventory in private["inventories"] for item in VALUABLE
    )
    final_animals = _animals(final[seat].observation["farms"][seat])
    return {
        "candidate": candidate,
        "opponent": opponent,
        "seed": seed,
        "seat": seat,
        "money": money,
        "opponent_money": opponent_money,
        "advantage": money - opponent_money,
        "peak_animals": peak,
        "final_animals": final_animals,
        "animal_losses": {
            animal: peak[animal] - final_animals[animal] for animal in peak
        },
        "stranded_inventory": stranded,
    }


def _percentile(values, fraction):
    values = sorted(values)
    point = fraction * (len(values) - 1)
    lower = int(point)
    upper = min(lower + 1, len(values) - 1)
    weight = point - lower
    return values[lower] * (1 - weight) + values[upper] * weight


def _summary(games):
    advantages = [game["advantage"] for game in games]
    wins = sum(value > 0 for value in advantages)
    losses = sum(value < 0 for value in advantages)
    ties = len(games) - wins - losses
    paired = {}
    for game in games:
        paired.setdefault((game["opponent"], game["seed"]), []).append(game["advantage"])
    seed_advantages = [statistics.fmean(values) for values in paired.values()]
    return {
        "games": len(games),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "score_rate": (wins + 0.5 * ties) / len(games),
        "average_money": statistics.fmean(game["money"] for game in games),
        "average_advantage": statistics.fmean(advantages),
        "p10_paired_advantage": _percentile(seed_advantages, 0.10),
        "advantage_variance": statistics.variance(advantages) if len(advantages) > 1 else 0,
        "max_cow_loss": max(game["animal_losses"]["COW"] for game in games),
        "max_sheep_loss": max(game["animal_losses"]["SHEEP"] for game in games),
        "max_stranded_inventory": max(game["stranded_inventory"] for game in games),
    }


def _candidate_summary(name, games):
    matchups = {
        opponent: _summary([game for game in games if game["opponent"] == opponent])
        for opponent in OPPONENTS
    }
    worst = min(
        matchups,
        key=lambda opponent: (
            matchups[opponent]["score_rate"], matchups[opponent]["average_advantage"]
        ),
    )
    return {
        "candidate": name,
        "path": CANDIDATES[name],
        "overall": _summary(games),
        "matchups": matchups,
        "worst_opponent": worst,
    }


def _run_suite(candidates, seeds, label):
    games = []
    total = len(candidates) * len(OPPONENTS) * len(seeds) * 2
    index = 0
    for candidate in candidates:
        for opponent in OPPONENTS:
            for seed in seeds:
                for seat in (0, 1):
                    games.append(
                        _run(
                            candidate, CANDIDATES[candidate],
                            opponent, OPPONENTS[opponent], seed, seat,
                        )
                    )
                    index += 1
                    if index % 32 == 0 or index == total:
                        print(f"{label} {index}/{total}", flush=True)
    return games


def _write_markdown(payload):
    lines = [
        "# Opening full-season validation",
        "",
        "The opening was the only experimental component. Day 11 onward uses the frozen replay crop phases, land allocation, labor caps, and unchanged large-scale router.",
        "",
        "## Validation seeds",
        "",
        "| Candidate | Games | W/L/T | Score | Avg money | Avg advantage | P10 paired | Variance | Worst opponent | Cow/sheep loss | Stranded max |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|",
    ]
    for row in payload["validation"]["candidates"]:
        s = row["overall"]
        lines.append(
            f"| {row['candidate']} | {s['games']} | {s['wins']}/{s['losses']}/{s['ties']} | "
            f"{s['score_rate']:.1%} | {s['average_money']:.0f} | {s['average_advantage']:+.0f} | "
            f"{s['p10_paired_advantage']:+.0f} | {s['advantage_variance']:.0f} | "
            f"{row['worst_opponent']} | {s['max_cow_loss']}/{s['max_sheep_loss']} | "
            f"{s['max_stranded_inventory']} |"
        )
    row = payload["heldout"]["candidate"]
    s = row["overall"]
    lines.extend(
        [
            "",
            "## Fresh held-out confirmation",
            "",
            f"Selected from validation: **{row['candidate']}**.",
            "",
            f"Held-out: {s['games']} games, {s['wins']}/{s['losses']}/{s['ties']}, "
            f"score {s['score_rate']:.1%}, average money {s['average_money']:.0f}, "
            f"average advantage {s['average_advantage']:+.0f}, P10 {s['p10_paired_advantage']:+.0f}; "
            f"worst matchup `{row['worst_opponent']}`.",
        ]
    )
    (ROOT / "experiments" / "opening_full_validation.md").write_text("\n".join(lines) + "\n")


def main():
    validation_games = _run_suite(tuple(CANDIDATES), VALIDATION_SEEDS, "validation")
    validation_rows = [
        _candidate_summary(
            candidate,
            [game for game in validation_games if game["candidate"] == candidate],
        )
        for candidate in CANDIDATES
    ]
    validation_rows.sort(
        key=lambda row: (
            row["overall"]["score_rate"],
            row["overall"]["average_advantage"],
            row["overall"]["average_money"],
        ),
        reverse=True,
    )
    winner = validation_rows[0]["candidate"]
    heldout_games = _run_suite((winner,), HELDOUT_SEEDS, "heldout")
    heldout_row = _candidate_summary(winner, heldout_games)
    payload = {
        "schema_version": 1,
        "experiment": "opening_full_season_validation",
        "opponents": OPPONENTS,
        "validation": {
            "seeds": list(VALIDATION_SEEDS),
            "both_seats": True,
            "candidates": validation_rows,
            "games": validation_games,
        },
        "heldout": {
            "seeds": list(HELDOUT_SEEDS),
            "both_seats": True,
            "candidate": heldout_row,
            "games": heldout_games,
        },
    }
    output = ROOT / "experiments" / "opening_full_validation.json"
    output.write_text(json.dumps(payload, indent=2) + "\n")
    _write_markdown(payload)
    print(output)
    for row in validation_rows:
        s = row["overall"]
        print(
            row["candidate"], f"{s['wins']}/{s['losses']}/{s['ties']}",
            f"score={s['score_rate']:.1%}", f"money={s['average_money']:.0f}",
            f"adv={s['average_advantage']:+.0f}", f"worst={row['worst_opponent']}",
        )
    s = heldout_row["overall"]
    print(
        "heldout", winner, f"{s['wins']}/{s['losses']}/{s['ties']}",
        f"score={s['score_rate']:.1%}", f"money={s['average_money']:.0f}",
        f"adv={s['average_advantage']:+.0f}",
    )


if __name__ == "__main__":
    main()
