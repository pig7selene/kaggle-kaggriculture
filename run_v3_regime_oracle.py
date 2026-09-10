"""Fresh, resumable three-policy oracle for the V3 specialist study.

Research-only: this runner never writes deployment files or packages submissions.
"""

from __future__ import annotations

from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path
import time

from kaggle_environments import make

from run_raw55899537_final_validation import (
    animal_escapes,
    digest,
    load_agent,
    semantic_validate,
    terminal_value,
)


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "experiments/v3_regime_runs"
POLICIES = {
    "CurrentBest": ROOT / "agents/top50_distilled/top50_observable_portfolio.py",
    "V3": ROOT / "agents/public_farming_v3/main.py",
    "Route1": ROOT / "agents/farming_v3_distilled/v1_force_route1.py",
}
OPPONENTS = {
    "CurrentBest": ROOT / "agents/top50_distilled/top50_observable_portfolio.py",
    "V2": ROOT / "agents/super_replay_v2/super_backbone_v2.py",
    "K3": ROOT / "agents/v27_k3_weed.py",
    "Nazmus": ROOT / "agents/super_replay_v4/n1_nazmus_weed.py",
    "tetsuya": ROOT / "agents/top3_tuned/raw_rank1_tetsuya.py",
    "crop_dusta": ROOT / "agents/top3_tuned/raw_rank2_crop_dusta.py",
    "oceanmix": ROOT / "agents/top3_tuned/raw_rank3_oceanmix.py",
    "FarmingV3": ROOT / "agents/public_farming_v3/main.py",
    "router_hands12": ROOT / "agents/router_replay_hands12.py",
    "victor": ROOT / "agents/leaderboard_archetypes/victor_top_template.py",
}
CHECKPOINTS = (0, 1, 24, 48, 72, 96, 120, 144)


def _plain(counter):
    return {key: int(value) for key, value in sorted(counter.items()) if value}


def _farm_features(farm, day):
    crops = Counter(); animals = Counter(); structures = Counter()
    crop_yield = Counter(); crop_age = Counter(); mature = Counter()
    weeds = productive = unfed = unwatered = 0
    for row in farm.get("tiles", []):
        for tile in row:
            if not isinstance(tile, dict):
                continue
            kind = tile.get("kind")
            if kind == "PLANT":
                crop = tile.get("crop", "UNKNOWN")
                crops[crop] += 1; productive += 1
                crop_yield[crop] += int(tile.get("yield_units", 0) or 0)
                age = max(0, int(day) - int(tile.get("planted_day", day) or day))
                crop_age[crop] += age
                if int(tile.get("yield_units", 0) or 0) > 0:
                    mature[crop] += 1
                unwatered += int(not tile.get("watered_today", False))
            elif kind in {"COOP", "PASTURE"}:
                structures[kind] += 1
                animal = tile.get("animal")
                if animal:
                    animals[animal] += 1; productive += 1
                    unfed += int(not tile.get("fed_today", False))
            elif kind == "WEED":
                weeds += 1
    return {
        "money": float(farm.get("money", 0)),
        "hands": len(farm.get("hands", [])),
        "hires_today": int(farm.get("hires_today", 0)),
        "quadrants": len(farm.get("unlocked_quadrants", [])),
        "crops": _plain(crops), "animals": _plain(animals),
        "structures": _plain(structures), "crop_yield": _plain(crop_yield),
        "crop_age_sum": _plain(crop_age), "mature_crops": _plain(mature),
        "productive": productive, "weeds": weeds, "unfed": unfed, "unwatered": unwatered,
    }


def _tile_signature(tile):
    if tile is None or isinstance(tile, str):
        return tile
    keys = (
        "kind", "crop", "animal", "planted_day", "placed_day", "yield_units",
        "watered_today", "fed_today", "cared_today", "consecutive_unwatered",
        "consecutive_unfed", "fertilized_until_day", "fertilizer_available",
        "pending_care_bonus",
    )
    return {key: tile.get(key) for key in keys if key in tile}


def _state_signature(obs, seat):
    farm = obs["farms"][seat]
    private = obs.get("private", {})
    return {
        "money": float(farm.get("money", 0)),
        "farmer": list(farm.get("farmer", [])),
        "hands": [list(position) for position in farm.get("hands", [])],
        "quadrants": list(farm.get("unlocked_quadrants", [])),
        "hires_today": int(farm.get("hires_today", 0)),
        "tiles": [[_tile_signature(tile) for tile in row] for row in farm.get("tiles", [])],
        "shed": dict(sorted(private.get("shed", {}).items())),
        "seeds": dict(sorted(private.get("seeds", {}).items())),
        "inventories": [dict(sorted(inv.items())) for inv in private.get("inventories", [])],
    }


def _snapshot(obs, seat):
    day = int(obs.get("day", 0))
    market = obs.get("market", {})
    private = obs.get("private", {})
    inventory_total = Counter(private.get("shed", {}))
    for carried in private.get("inventories", []):
        inventory_total.update(carried)
    return {
        "step": int(obs.get("step", 0)), "day": day, "hour": int(obs.get("hour", 0)),
        "self": _farm_features(obs["farms"][seat], day),
        "opponent": _farm_features(obs["farms"][1 - seat], day),
        "market_prices": {key: int(value) for key, value in sorted(market.get("prices", {}).items())},
        "market_inventory": {key: int(value) for key, value in sorted(market.get("inventory", {}).items())},
        "shops": list(obs.get("town", {}).get("unlocked_shops", [])),
        "own_inventory_total": _plain(inventory_total),
        "own_seeds": {key: int(value) for key, value in sorted(private.get("seeds", {}).items()) if value},
        "own_state": _state_signature(obs, seat),
    }


def run_game(job):
    policy_name, opponent_name, seed, seat = job
    started = time.perf_counter()
    policy = load_agent(POLICIES[policy_name])
    opponent = load_agent(OPPONENTS[opponent_name])
    actions = []
    checkpoints = {}
    semantic_failures = []
    exceptions = []

    def checked(obs):
        step = int(obs.get("step", 0))
        if step in CHECKPOINTS:
            checkpoints[str(step)] = _snapshot(obs, seat)
        try:
            action = policy(obs)
        except Exception as exc:
            exceptions.append({"step": step, "error": repr(exc)})
            raise
        actions.append(deepcopy(action))
        try:
            semantic_validate(obs, action)
        except Exception as exc:
            semantic_failures.append({"step": step, "error": repr(exc)})
        return action

    pair = [opponent, opponent]
    pair[seat] = checked
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": int(seed)}, debug=False)
    runtime_error = None
    try:
        env.run(pair)
    except Exception as exc:
        runtime_error = repr(exc)
    if len(getattr(env, "steps", [])) != 720:
        return {
            "policy": policy_name, "opponent": opponent_name, "seed": seed, "seat": seat,
            "runtime_error": runtime_error or f"steps={len(env.steps)}", "exceptions": exceptions,
            "semantic_failures": semantic_failures,
        }
    final = env.steps[-1]
    own = float(final[seat].reward); other = float(final[1 - seat].reward)
    return {
        "policy": policy_name, "opponent": opponent_name, "seed": int(seed), "seat": int(seat),
        "runtime_error": runtime_error, "exceptions": exceptions, "semantic_failures": semantic_failures,
        "elapsed_s": time.perf_counter() - started,
        "own_money": own, "opponent_money": other, "advantage": own - other,
        "action_hash": digest(actions), "action_prefix": actions[:145],
        "checkpoints": checkpoints,
        "livestock_escapes": animal_escapes(env.steps, seat),
        "terminal": terminal_value(final, seat),
    }


def jobs():
    return [
        (policy, opponent, seed, seat)
        for opponent_index, opponent in enumerate(OPPONENTS)
        for seed in range(910000 + opponent_index * 100, 910004 + opponent_index * 100)
        for seat in (0, 1)
        for policy in POLICIES
    ]


def key(values):
    return "|".join(map(str, values))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    partial = OUT / "oracle.partial.json"
    rows = json.loads(partial.read_text()) if partial.exists() else []
    done = {key((row["policy"], row["opponent"], row["seed"], row["seat"])) for row in rows}
    pending = [job for job in jobs() if key(job) not in done]
    print(f"oracle: {len(rows)} cached, {len(pending)} pending", flush=True)
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run_game, job): job for job in pending}
        for index, future in enumerate(as_completed(futures), 1):
            rows.append(future.result())
            if index % 4 == 0 or index == len(pending):
                partial.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n")
                print(f"oracle: {index}/{len(pending)} new games", flush=True)
    rows.sort(key=lambda row: (row["opponent"], row["seed"], row["seat"], row["policy"]))
    partial.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n")
    print("done", flush=True)


if __name__ == "__main__":
    main()

