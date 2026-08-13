"""Re-run the four newest losses to explain T2's matchup-specific effects."""

from __future__ import annotations

import json
import statistics
from collections import Counter
from copy import deepcopy
from pathlib import Path
from runpy import run_path

from kaggle_environments import make

from analyze_crop_lifecycle import lifecycle_metrics
from analyze_top_player_replays import _transition_ledger
from run_post_opening_validation import LOSS_EPISODES, REPLAY_DIR, ROOT, _load_opponent, _trace_spec
from test_economic_agents import _validate_action


CANDIDATES = {
    "T0_current": "agents/opening_public_front_cow8_day6.py",
    "T2_deploy": "agents/post_opening_t2_deploy.py",
}
OUTPUT = ROOT / "experiments" / "t2_matchup_causality.json"
REPLAY_OUTPUT = ROOT / "experiments" / "crop_lifecycle_replays"


def _manifest():
    path = ROOT / "experiments" / "kaggle_episodes" / "submission_55435253" / "manifest.json"
    return {int(row["episode_id"]): row for row in json.loads(path.read_text())["episodes"]}


def _economics(replay, player, start_day=10, end_day=20):
    sales = Counter()
    revenue = Counter()
    harvests = Counter()
    daily = []
    day_sales = {day: Counter() for day in range(start_day, end_day + 1)}
    day_revenue = {day: Counter() for day in range(start_day, end_day + 1)}
    for index in range(1, len(replay["steps"])):
        previous = replay["steps"][index - 1]
        current = replay["steps"][index]
        day = int(previous[0]["observation"]["day"])
        if day < start_day or day > end_day:
            continue
        ledgers, errors = _transition_ledger(previous, current, replay["configuration"])
        if errors:
            raise AssertionError(errors[:3])
        ledger = ledgers[player]
        sales.update(ledger["sale_quantity"])
        revenue.update(ledger["sale_revenue"])
        harvests.update(ledger["harvest_quantity"])
        day_sales[day].update(ledger["sale_quantity"])
        day_revenue[day].update(ledger["sale_revenue"])
    for day in range(start_day, end_day + 1):
        daily.append({
            "day": day,
            "sales": dict(day_sales[day]),
            "sale_revenue": dict(day_revenue[day]),
        })
    return {
        "sales": dict(sales),
        "sale_revenue": dict(revenue),
        "harvest_units": dict(harvests),
        "weighted_sale_price": {
            product: revenue[product] / quantity
            for product, quantity in sorted(sales.items()) if quantity
        },
        "total_crop_revenue": sum(
            revenue[crop] for crop in ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")
        ),
        "daily": daily,
    }


def _run(candidate, path, episode_id, seat, opponent_spec, seed):
    base = run_path(str(ROOT / path))["agent"]
    opponent = _load_opponent(opponent_spec)

    def checked(obs):
        action = base(obs)
        _validate_action(obs, action)
        return action

    pair = [opponent, opponent]
    pair[seat] = checked
    env = make(
        "kaggriculture",
        configuration={"episodeSteps": 720, "seed": seed},
        debug=True,
    )
    env.run(pair)
    final = env.steps[-1]
    if len(env.steps) != 720 or [state.status for state in final] != ["DONE", "DONE"]:
        raise RuntimeError((candidate, episode_id, seat, len(env.steps)))
    replay = env.toJSON()
    REPLAY_OUTPUT.mkdir(parents=True, exist_ok=True)
    replay_path = REPLAY_OUTPUT / f"{candidate}_episode_{episode_id}_seat_{seat}.json"
    replay_path.write_text(json.dumps(replay))
    return {
        "candidate": candidate,
        "path": path,
        "episode_id": episode_id,
        "seat": seat,
        "seed": seed,
        "money": float(final[seat].reward),
        "opponent_money": float(final[1 - seat].reward),
        "advantage": float(final[seat].reward) - float(final[1 - seat].reward),
        "candidate_lifecycle": lifecycle_metrics(replay, seat),
        "opponent_lifecycle": lifecycle_metrics(replay, 1 - seat),
        "candidate_economics": _economics(replay, seat),
        "opponent_economics": _economics(replay, 1 - seat),
        "replay": str(replay_path.relative_to(ROOT)),
    }


def _paired_deltas(games, manifest):
    rows = []
    for episode_id in LOSS_EPISODES:
        original_seat = int(manifest[episode_id]["player"])
        for seat in (0, 1):
            t0 = next(row for row in games if row["candidate"] == "T0_current" and row["episode_id"] == episode_id and row["seat"] == seat)
            t2 = next(row for row in games if row["candidate"] == "T2_deploy" and row["episode_id"] == episode_id and row["seat"] == seat)
            life0 = t0["candidate_lifecycle"]
            life2 = t2["candidate_lifecycle"]
            econ0 = t0["candidate_economics"]
            econ2 = t2["candidate_economics"]
            rows.append({
                "episode_id": episode_id,
                "opponent": manifest[episode_id]["opponent"],
                "seat": seat,
                "original_seat": seat == original_seat,
                "advantage_delta": t2["advantage"] - t0["advantage"],
                "money_delta": t2["money"] - t0["money"],
                "opponent_money_delta": t2["opponent_money"] - t0["opponent_money"],
                "crop_revenue_delta": econ2["total_crop_revenue"] - econ0["total_crop_revenue"],
                "harvest_action_delta": life2["total_harvest_actions"] - life0["total_harvest_actions"],
                "harvest_unit_delta": life2["total_harvest_units"] - life0["total_harvest_units"],
                "productive_crop_tile_hour_delta": (
                    life2["productive_crop_tile_hours"] - life0["productive_crop_tile_hours"]
                ),
                "critical_miss_delta": (
                    life2["critical_watering_miss_rate"] - life0["critical_watering_miss_rate"]
                ),
                "harvest_delay_delta": (
                    life2["average_harvest_delay_turns"] - life0["average_harvest_delay_turns"]
                ),
                "replant_delay_delta": (
                    life2["average_replant_delay_turns"] - life0["average_replant_delay_turns"]
                ),
                "lifecycle_debt_delta": (
                    life2["lifecycle_debt_tile_hours"] - life0["lifecycle_debt_tile_hours"]
                ),
                "t0": {"money": t0["money"], "opponent_money": t0["opponent_money"], "advantage": t0["advantage"]},
                "t2": {"money": t2["money"], "opponent_money": t2["opponent_money"], "advantage": t2["advantage"]},
            })
    return rows


def main():
    manifest = _manifest()
    games = []
    for candidate, path in CANDIDATES.items():
        for episode_id in LOSS_EPISODES:
            source_replay = json.loads(next(REPLAY_DIR.glob(f"episode-{episode_id}-replay.json")).read_text())
            seed = int(source_replay["info"]["seed"])
            spec = _trace_spec(episode_id)
            for seat in (0, 1):
                games.append(_run(candidate, path, episode_id, seat, spec, seed))
                print(candidate, episode_id, seat, games[-1]["money"], games[-1]["opponent_money"], flush=True)
    payload = {
        "schema_version": 1,
        "window": [10, 20],
        "definitions": {
            "harvest_delay": "turns from economically ready yield (ongoing: any yield; one-time: target peak) to successful harvest",
            "replant_delay": "turns from crop removal/loss to successful planting on the same tile",
            "lifecycle_debt": "sum over hours of harvest-ready, critical-water, and replacement-pending tiles",
            "productive_crop_tile_hours": "living crop tiles summed over every observed hour",
        },
        "games": games,
        "deltas": _paired_deltas(games, manifest),
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(OUTPUT)


if __name__ == "__main__":
    main()
