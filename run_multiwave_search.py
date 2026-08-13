"""Deterministic large-scale search for crop-wave economic architectures.

The search stores configurations separately from agents. Candidate IDs are a
hash of canonical JSON. Each stage emits a complete manifest and slim game
records with economic wave metrics, making interrupted runs reproducible.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
from pathlib import Path

from run_epic_experiments import _independent_shop_schedule, _recorded_shop_schedule, _run
from run_leaderboard_breakthrough import HELDOUT_REPLAY_CASES, REPLAY_CASES, _source, _trace_spec


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "experiments/multiwave_candidate_configs.json"
SPLIT_PATH = ROOT / "experiments/multiwave_split_manifest.json"
TOP_ROUTING = ROOT / "experiments/top_player_worker_routing.json"
R3 = "agents/leaderboard_r3_cow6_capital.py"
PUBLIC_803 = "agents/opening_public_front_cow8_day6.py"
TOP_DIAGNOSIS = {
    key: HELDOUT_REPLAY_CASES[key]
    for key in (
        "Filip_top_template", "Amer_high_scale",
        "Yankang_wheat_close", "Prashant_crop_scaler",
    )
}
REGRESSION = {
    key: REPLAY_CASES[key]
    for key in (
        "Jayveer_melon_burst", "Pedro_wheat_turnover",
        "Lucas_four_quadrant", "Alexander_cow_melon",
    )
}


def _sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def _candidate_id(config):
    raw = json.dumps(config, sort_keys=True, separators=(",", ":")).encode()
    return "mw_" + hashlib.sha256(raw).hexdigest()[:12]


def _normalize_mix(mix):
    values = {crop: round(max(0.0, float(value)), 6) for crop, value in mix.items() if value > 0}
    total = sum(values.values())
    return {crop: round(value / total, 6) for crop, value in sorted(values.items())}


def _base_config():
    return {
        "opening_extension_mix": {"MELON": .20, "STRAWBERRY": .60, "WHEAT": .20},
        "opening_structure": "staggered",
        "wave1_start_day": 10,
        "wave1_mix": {"MELON": .20, "STRAWBERRY": .65, "WHEAT": .15},
        "wave1_structure": "synchronized",
        "wave2_start_day": 20,
        "wave2_mix": {"STRAWBERRY": .55, "WHEAT": .45},
        "wave2_structure": "staggered",
        "wave3_start_day": 23,
        "wave3_mix": {"STRAWBERRY": .15, "WHEAT": .85},
        "wave3_structure": "staggered",
        "productive_targets": {"6": 22, "7": 34, "8": 42, "10": 60},
        "core_crop_targets": {},
        "cash_reserve_wave1": 0,
        "cash_reserve_wave2": 0,
        "cash_reserve_wave3": 0,
        "seed_reinvestment_fraction": 1.0,
        "liquidation_mode": "immediate",
        "liquidation_batch": 18,
        "liquidation_overflow": 78,
        "liquidation_days": {"MELON": 10, "STRAWBERRY": 18, "WHEAT": 24},
        "plant_admission": False,
        "plant_cutoff_hour": 20,
        "cow_target": 6,
        "hand_policy": "replay",
    }


def _clean(config):
    config = deepcopy(config)
    for key in ("opening_extension_mix", "wave1_mix", "wave2_mix", "wave3_mix"):
        config[key] = _normalize_mix(config[key])
    config["productive_targets"] = {
        str(key): int(value) for key, value in sorted(config["productive_targets"].items(), key=lambda row: int(row[0]))
    }
    config["core_crop_targets"] = {
        str(key): int(value) for key, value in sorted(config.get("core_crop_targets", {}).items(), key=lambda row: int(row[0]))
    }
    return config


def _add(configs, config, family, hypothesis, parents=()):
    config = _clean(config)
    candidate = _candidate_id(config)
    configs[candidate] = {
        "candidate": candidate, "family": family,
        "hypothesis": hypothesis, "parents": list(parents), "config": config,
    }
    return candidate


def _lhs(index, count, low, high, salt):
    rng = random.Random(0x5A17 + salt)
    bins = list(range(count))
    rng.shuffle(bins)
    point = (bins[index] + rng.random()) / count
    return low + point * (high - low)


def generation0_configs(count=96):
    configs = {}
    base = _base_config()
    _add(configs, base, "control", "R3-like three-wave control expressed by the new economic layer")

    # Explicit counterfactual derivatives around the replay-grounded control.
    for melon in (.05, .20, .35, .50, .65):
        cfg = deepcopy(base)
        cfg["opening_extension_mix"] = {"MELON": melon, "STRAWBERRY": .75 - .65 * melon, "WHEAT": .25 - .35 * melon}
        _add(configs, cfg, "opening_derivative", f"measure marginal final value of opening extension melon share {melon:.2f}")
    for melon in (.05, .15, .25, .35, .45):
        cfg = deepcopy(base)
        cfg["wave1_mix"] = {"MELON": melon, "STRAWBERRY": .80 - .6 * melon, "WHEAT": .20 - .4 * melon}
        _add(configs, cfg, "wave1_mix_derivative", f"measure first post-deed melon cohort share {melon:.2f}")
    for day in (18, 19, 20, 21):
        cfg = deepcopy(base); cfg["wave2_start_day"] = day
        _add(configs, cfg, "wave2_timing_derivative", f"shift second-wave intent to day {day}")
    for reserve in (0, 500, 1000, 1500):
        cfg = deepcopy(base); cfg["cash_reserve_wave1"] = reserve; cfg["cash_reserve_wave2"] = reserve
        _add(configs, cfg, "reserve_derivative", f"reserve {reserve} for wave deployment")
    for fraction in (.70, .85, 1.0):
        cfg = deepcopy(base); cfg["seed_reinvestment_fraction"] = fraction
        _add(configs, cfg, "reinvestment_derivative", f"deploy {fraction:.0%} of residual cash into seeds")
    for mode in ("immediate", "daily_batch", "window"):
        cfg = deepcopy(base); cfg["liquidation_mode"] = mode
        _add(configs, cfg, "liquidation_derivative", f"test {mode} crop liquidation")
    for structure in ("synchronized", "staggered", "quadrant"):
        cfg = deepcopy(base); cfg["wave1_structure"] = structure; cfg["wave2_structure"] = structure
        _add(configs, cfg, "spatial_derivative", f"test {structure} cohort geometry")

    # Replay-informed Latin-hypercube samples fill the remaining broad search.
    remaining = max(1, count - len(configs))
    for index in range(remaining * 3):
        if len(configs) >= count:
            break
        cfg = deepcopy(base)
        opening_melon = _lhs(index % remaining, remaining, .02, .62, 1)
        opening_wheat = _lhs(index % remaining, remaining, .08, .32, 2)
        cfg["opening_extension_mix"] = {
            "MELON": opening_melon,
            "WHEAT": opening_wheat,
            "STRAWBERRY": max(.05, 1 - opening_melon - opening_wheat),
        }
        w1_melon = _lhs(index % remaining, remaining, .08, .46, 3)
        w1_wheat = _lhs(index % remaining, remaining, .08, .30, 4)
        cfg["wave1_mix"] = {
            "MELON": w1_melon, "WHEAT": w1_wheat,
            "STRAWBERRY": max(.10, 1 - w1_melon - w1_wheat),
        }
        w2_straw = _lhs(index % remaining, remaining, .25, .78, 5)
        w2_melon = _lhs(index % remaining, remaining, 0, .20, 6)
        cfg["wave2_mix"] = {
            "MELON": w2_melon, "STRAWBERRY": w2_straw,
            "WHEAT": max(.10, 1 - w2_melon - w2_straw),
        }
        carrot = .10 if index % 11 == 0 else 0
        straw3 = _lhs(index % remaining, remaining, 0, .28, 7)
        cfg["wave3_mix"] = {"WHEAT": max(.55, 1 - carrot - straw3), "STRAWBERRY": straw3}
        if carrot:
            cfg["wave3_mix"]["CARROT"] = carrot
        cfg["wave1_start_day"] = (9, 10, 11)[index % 3]
        cfg["wave2_start_day"] = (18, 19, 20, 21)[(index // 3) % 4]
        cfg["wave3_start_day"] = (22, 23, 24, 25)[(index // 7) % 4]
        cfg["opening_structure"] = ("staggered", "synchronized", "quadrant")[index % 3]
        cfg["wave1_structure"] = ("synchronized", "staggered", "quadrant")[(index // 2) % 3]
        cfg["wave2_structure"] = ("staggered", "synchronized", "quadrant")[(index // 5) % 3]
        cfg["productive_targets"] = {
            "6": (20, 22, 24)[index % 3],
            "7": (31, 34, 37)[(index // 2) % 3],
            "8": (38, 42, 46)[(index // 4) % 3],
            "10": (55, 60, 65)[(index // 8) % 3],
        }
        cfg["cash_reserve_wave1"] = (0, 500, 1000, 1500)[(index // 3) % 4]
        cfg["cash_reserve_wave2"] = (0, 500, 1000)[(index // 6) % 3]
        cfg["seed_reinvestment_fraction"] = (.70, .85, 1.0)[(index // 9) % 3]
        cfg["liquidation_mode"] = ("immediate", "daily_batch", "window")[(index // 12) % 3]
        cfg["liquidation_batch"] = (12, 18, 24)[(index // 4) % 3]
        cfg["plant_admission"] = index % 8 == 0
        _add(configs, cfg, "lhs", "replay-range Latin-hypercube economic architecture")
    return configs


def make_split_manifest():
    rows = json.loads(TOP_ROUTING.read_text())["appearances"]
    known = {case[0] for case in TOP_DIAGNOSIS.values()} | {case[0] for case in REGRESSION.values()}
    unique = {}
    for row in rows:
        key = (int(row["episode_id"]), int(row["player_index"]))
        if key[0] not in known:
            unique[key] = {
                "episode_id": key[0], "player": key[1], "team": row["team_name"],
                "path": f"experiments/top_player_replays/replays/episode-{key[0]}-replay.json",
            }
    ordered = sorted(
        unique.values(),
        key=lambda row: hashlib.sha256(f"multiwave-split-{row['episode_id']}-{row['player']}".encode()).hexdigest(),
    )
    payload = {
        "schema_version": 1,
        "rule": "SHA-256 order of episode/player; assigned before candidate evaluation",
        "development": ordered[16:24],
        "selection": ordered[8:16],
        "final": ordered[:8],
    }
    SPLIT_PATH.write_text(json.dumps(payload, indent=2) + "\n")
    return payload


def _trace_job(candidate, spec, group, name, case):
    _, replay_path, player = case
    replay = _source(replay_path)
    seed = int(replay["info"]["seed"])
    schedule = _recorded_shop_schedule(replay)
    return [
        (candidate, spec, group, name, _trace_spec(replay_path, player), seed, seat, schedule)
        for seat in (0, 1)
    ]


def _manifest_trace_job(candidate, spec, group, row):
    replay = _source(row["path"])
    seed = int(replay["info"]["seed"])
    schedule = _recorded_shop_schedule(replay)
    opponent = f"{row['team']}_{row['episode_id']}_{row['player']}"
    return [
        (candidate, spec, group, opponent, _trace_spec(row["path"], row["player"]), seed, seat, schedule)
        for seat in (0, 1)
    ]


def _jobs(stage, configs, seed_start, seed_count, split):
    jobs = []
    for candidate, row in configs.items():
        spec = {"multiwave_config": row["config"]}
        for name, case in TOP_DIAGNOSIS.items():
            jobs.extend(_trace_job(candidate, spec, "top_diagnosis", name, case))
        regressions = ("Jayveer_melon_burst", "Pedro_wheat_turnover") if stage == "generation0" else tuple(REGRESSION)
        for name in regressions:
            jobs.extend(_trace_job(candidate, spec, "real_regression", name, REGRESSION[name]))
        if stage != "generation0":
            split_name = "development" if stage == "generation1" else "selection"
            for appearance in split[split_name]:
                jobs.extend(_manifest_trace_job(candidate, spec, f"top_{split_name}", appearance))
        for seed in range(seed_start, seed_start + seed_count):
            for seat in (0, 1):
                schedule = _independent_shop_schedule(seed)
                jobs.append((candidate, spec, "direct_r3_fixed", "R3_fixed", R3, seed, seat, schedule))
                jobs.append((candidate, spec, "direct_803_fixed", "R0_803_fixed", PUBLIC_803, seed, seat, schedule))
                if stage != "generation0":
                    jobs.append((candidate, spec, "direct_r3_natural", "R3_natural", R3, seed, seat, None))
                    jobs.append((candidate, spec, "direct_803_natural", "R0_803_natural", PUBLIC_803, seed, seat, None))
    return jobs


def _slim(row):
    return {
        key: row[key] for key in (
            "candidate", "group", "opponent", "seed", "seat", "money",
            "opponent_money", "advantage", "calls", "runtime_failures",
            "semantic_failures", "stranded_value", "stranded",
            "animals_bought", "animals_remaining", "livestock_losses",
            "checkpoints", "land_days", "major_sale_windows", "cash_waves",
        )
    } | {
        "crop_revenue": row["economics"]["full"]["crop_revenue"],
        "animal_revenue": row["economics"]["full"]["animal_revenue"],
        "labor_spend": row["economics"]["full"]["labor_spend"],
        "harvests_day10_29": (
            row["lifecycle_day10_20"]["total_harvest_actions"]
            + row["lifecycle_day21_29"]["total_harvest_actions"]
        ),
        "critical_miss": row["lifecycle_day10_20"]["critical_watering_miss_rate"],
        "worker_idle": row["routing_day10_29"]["idle_rate"],
        "territory_crossings": row["routing_day10_29"]["territory_crossings"],
        "invalid_actions": row["routing_day10_29"]["invalid_actions"],
    }


def _pct(values, fraction):
    values = sorted(values)
    if not values:
        return None
    point = fraction * (len(values) - 1)
    lower, upper = int(point), min(len(values) - 1, int(point) + 1)
    weight = point - lower
    return values[lower] * (1 - weight) + values[upper] * weight


def _summary(rows):
    adv = [row["advantage"] for row in rows]
    pairs = defaultdict(list)
    for row in rows:
        pairs[(row["group"], row["opponent"], row["seed"])].append(row["advantage"])
    paired = [statistics.fmean(values) for values in pairs.values()]
    return {
        "games": len(rows), "wins": sum(value > 0 for value in adv),
        "losses": sum(value < 0 for value in adv), "ties": sum(value == 0 for value in adv),
        "average_money": statistics.fmean(row["money"] for row in rows),
        "average_advantage": statistics.fmean(adv),
        "median_advantage": statistics.median(paired),
        "p25_advantage": _pct(paired, .25), "p10_advantage": _pct(paired, .10),
        "worst_advantage": min(paired),
        "average_crop_revenue": statistics.fmean(row["crop_revenue"] for row in rows),
        "average_animal_revenue": statistics.fmean(row["animal_revenue"] for row in rows),
        "average_harvests_day10_29": statistics.fmean(row["harvests_day10_29"] for row in rows),
        "average_critical_miss": statistics.fmean(row["critical_miss"] for row in rows),
        "average_worker_idle": statistics.fmean(row["worker_idle"] for row in rows),
        "average_labor_spend": statistics.fmean(row["labor_spend"] for row in rows),
        "total_invalid_actions": sum(row["invalid_actions"] for row in rows),
        "total_livestock_losses": sum(sum(row["livestock_losses"].values()) for row in rows),
        "max_stranded_value": max(row["stranded_value"] for row in rows),
    }


def _score(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[row["group"]].append(row)
    top = groups["top_diagnosis"] + groups.get("top_development", []) + groups.get("top_selection", [])
    regression = groups["real_regression"]
    direct_r3 = groups["direct_r3_fixed"] + groups.get("direct_r3_natural", [])
    direct_803 = groups["direct_803_fixed"] + groups.get("direct_803_natural", [])
    top_adv = statistics.fmean(row["advantage"] for row in top)
    top_rate = sum(row["advantage"] > 0 for row in top) / max(1, len(top))
    worst = min(row["advantage"] for row in top)
    regression_adv = statistics.fmean(row["advantage"] for row in regression)
    r3_adv = statistics.fmean(row["advantage"] for row in direct_r3)
    public_adv = statistics.fmean(row["advantage"] for row in direct_803)
    # Capped terms prevent weak-pool blowouts from overwhelming real transfer.
    score = (
        .38 * max(-30000, min(30000, top_adv))
        + 16000 * top_rate
        + .16 * max(-30000, min(10000, worst))
        + .14 * max(-15000, min(15000, regression_adv))
        + .18 * max(-15000, min(15000, r3_adv))
        + .06 * max(-15000, min(15000, public_adv))
    )
    return {
        "real_transfer_score": score,
        "top_template_win_rate": top_rate,
        "top_template_average_advantage": top_adv,
        "worst_top_template_advantage": worst,
        "regression_average_advantage": regression_adv,
        "direct_r3_average_advantage": r3_adv,
        "direct_803_average_advantage": public_adv,
    }


def _candidate_summaries(games, configs):
    output = []
    for candidate, config in configs.items():
        rows = [row for row in games if row["candidate"] == candidate]
        groups = {group: _summary([row for row in rows if row["group"] == group]) for group in sorted({row["group"] for row in rows})}
        matchups = {opponent: _summary([row for row in rows if row["opponent"] == opponent]) for opponent in sorted({row["opponent"] for row in rows})}
        output.append({
            "candidate": candidate, "family": config["family"],
            "hypothesis": config["hypothesis"], "parents": config["parents"],
            **_score(rows), "overall": _summary(rows),
            "groups": groups, "matchups": matchups,
        })
    return sorted(output, key=lambda row: row["real_transfer_score"], reverse=True)


def run_stage(stage, configs, seed_start, seed_count, workers, output):
    split = json.loads(SPLIT_PATH.read_text()) if SPLIT_PATH.exists() else make_split_manifest()
    jobs = _jobs(stage, configs, seed_start, seed_count, split)
    games = []
    partial = output.with_suffix(output.suffix + ".partial")
    if partial.exists():
        try:
            games = json.loads(partial.read_text()).get("games", [])
        except (json.JSONDecodeError, OSError):
            games = []
    complete = {
        (row["candidate"], row["group"], row["opponent"], row["seed"], row["seat"])
        for row in games
    }
    jobs = [
        job for job in jobs
        if (job[0], job[2], job[3], int(job[5]), int(job[6])) not in complete
    ]
    if workers <= 1:
        iterator = ((_run(job), index) for index, job in enumerate(jobs, 1))
        for result, index in iterator:
            games.append(_slim(result))
            if index % 100 == 0 or index == len(jobs):
                print(f"{stage} {index}/{len(jobs)}", flush=True)
                partial.write_text(json.dumps({"games": games}) + "\n")
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(_run, job) for job in jobs]
            for index, future in enumerate(as_completed(futures), 1):
                games.append(_slim(future.result()))
                if index % 100 == 0 or index == len(jobs):
                    print(f"{stage} {index}/{len(jobs)}", flush=True)
                    partial.write_text(json.dumps({"games": games}) + "\n")
    summaries = _candidate_summaries(games, configs)
    payload = {
        "schema_version": 1, "stage": stage,
        "seed_partition": {"start": seed_start, "count": seed_count},
        "source_hashes": {
            "R3": _sha(R3), "public_803": _sha(PUBLIC_803),
            "multiwave_runtime": _sha("agents/multiwave_runtime.py"),
            "epic_candidate_common": _sha("agents/epic_candidate_common.py"),
            "epic_opening_common": _sha("agents/epic_opening_common.py"),
            "epic_router": _sha("agents/epic_router.py"),
        },
        "candidate_count": len(configs), "job_count": len(jobs),
        "candidates": summaries, "games": games,
    }
    output.write_text(json.dumps(payload, indent=2) + "\n")
    if partial.exists():
        partial.unlink()
    for row in summaries[:20]:
        print(
            row["candidate"], row["family"],
            f"score={row['real_transfer_score']:+.0f}",
            f"top={row['top_template_win_rate']:.0%}/{row['top_template_average_advantage']:+.0f}",
            f"R3={row['direct_r3_average_advantage']:+.0f}",
            f"money={row['overall']['average_money']:.0f}",
        )
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("generation0", "generation1", "generation2"), default="generation0")
    parser.add_argument("--seed-start", type=int, default=966000)
    parser.add_argument("--seed-count", type=int, default=1)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--configs")
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.stage == "generation0" and not args.configs:
        configs = generation0_configs()
        CONFIG_PATH.write_text(json.dumps({"schema_version": 1, "generation0": configs}, indent=2) + "\n")
        make_split_manifest()
    else:
        source = Path(args.configs) if args.configs else CONFIG_PATH
        payload = json.loads(source.read_text())
        configs = payload.get(args.stage, payload.get("configs", payload.get("generation0")))
    output = Path(args.output) if args.output else ROOT / "experiments" / f"multiwave_{args.stage}.json"
    run_stage(args.stage, configs, args.seed_start, args.seed_count, args.workers, output)


if __name__ == "__main__":
    main()
