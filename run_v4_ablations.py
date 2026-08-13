"""Checkpointed paired ablations for bounded V4 modules."""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import json
from pathlib import Path
from runpy import run_path
import statistics

from kaggle_environments import make

from run_epic_experiments import _independent_shop_schedule, _recorded_shop_schedule, _run_with_fixed_shops
from run_post_opening_validation import _load_opponent
from run_v27_replay_backbone import _farm_counts, _inventory_value, _semantic_validate


ROOT = Path(__file__).resolve().parent
V2 = "agents/super_replay_v2/super_backbone_v2.py"
V2_MANIFEST = ROOT / "experiments/v3_real_v2_replays/manifest.json"
V2_DIAGNOSTICS = ROOT / "experiments/v4_real_failure_diagnostics.json"
ELITE_MANIFEST = ROOT / "experiments/v3_top10_corpus_manifest.json"

ALL_CANDIDATES = {
    "V2": V2,
    "M_day": "agents/super_replay_v4/m_day_boundary.py",
    "M_pressure": "agents/super_replay_v4/m_visible_pressure.py",
    "M_half": "agents/super_replay_v4/m_visible_pressure_half.py",
    "M_fair": "agents/super_replay_v4/m_pressure_or_fair.py",
    "M_hold_floor": "agents/super_replay_v4/m_hold_floor.py",
    "M_hold_low": "agents/super_replay_v4/m_hold_low.py",
    "M_hold_safe": "agents/super_replay_v4/m_hold_safe.py",
    "C_cows6": "agents/super_replay_v4/c_cows6.py",
    "C_cows7": "agents/super_replay_v4/c_cows7.py",
    "E_no_hire29": "agents/super_replay_v4/e_no_day29_hires.py",
    "E_no_seed25": "agents/super_replay_v4/e_no_seed_after_day25.py",
    "E_liq27": "agents/super_replay_v4/e_liquidate_day27.py",
    "W_wheat40": "agents/super_replay_v4/w_wheat40_day20.py",
    "W_wheat34": "agents/super_replay_v4/w_wheat34_day20.py",
    "N0_raw": "agents/super_replay_v4/n0_raw_nazmus.py",
    "N1_weed": "agents/super_replay_v4/n1_nazmus_weed.py",
    "N2_rescue": "agents/super_replay_v4/n2_nazmus_rescue.py",
}


def percentile(values, fraction):
    values = sorted(float(value) for value in values)
    if not values:
        return None
    point = fraction * (len(values) - 1)
    lower = int(point)
    weight = point - lower
    return values[lower] * (1 - weight) + values[min(lower + 1, len(values) - 1)] * weight


def trace(path, player):
    return f"trace:{ROOT / path}:{int(player)}"


def real_loss_traces(limit=None):
    manifest = json.loads(V2_MANIFEST.read_text())
    metadata = {int(row["episode_id"]): row for row in manifest["episodes"]}
    diagnostics = json.loads(V2_DIAGNOSTICS.read_text())
    losses = sorted(
        [row for row in diagnostics["episodes"] if row["result"] == "loss"],
        key=lambda row: (row["margin"], row["episode_id"]),
    )
    if limit:
        losses = losses[:limit]
    output = []
    for row in losses:
        meta = metadata[int(row["episode_id"])]
        replay = json.loads((ROOT / meta["replay_path"]).read_text())
        output.append({
            "name": f"real_loss_{row['episode_id']}_{row['opponent']}",
            "episode_id": row["episode_id"], "path": meta["replay_path"],
            "player": 1 - int(meta["seat"]), "seed": int(meta["seed"]),
            "schedule": _recorded_shop_schedule(replay), "family": "real_v2_loss",
        })
    return output


def elite_traces(split="development", limit=4):
    manifest = json.loads(ELITE_MANIFEST.read_text())
    ids = set(manifest["splits"][f"{split}_episode_ids"])
    output, seen = [], set()
    episodes = sorted(manifest["episodes"], key=lambda row: row["episode_id"], reverse=True)
    for episode in episodes:
        if int(episode["episode_id"]) not in ids:
            continue
        for app in episode.get("appearances", []):
            sid = int(app.get("submission_id") or 0)
            if not app.get("is_selected_elite_submission") or sid in seen:
                continue
            seen.add(sid)
            replay_path = f"experiments/v3_top10_corpus/replays/episode-{episode['episode_id']}-replay.json"
            replay = json.loads((ROOT / replay_path).read_text())
            output.append({
                "name": f"elite_r{app.get('leaderboard_rank')}_{sid}_{episode['episode_id']}",
                "episode_id": episode["episode_id"], "path": replay_path,
                "player": int(app["seat"]), "seed": int(episode["seed"]),
                "schedule": _recorded_shop_schedule(replay), "family": "elite_trace",
            })
            break
        if len(output) >= limit:
            break
    return output


def jobs(candidates, mode):
    rows = []
    if mode == "screen":
        traces = real_loss_traces(4) + elite_traces("development", 2)
        fixed_seeds, natural_seeds = range(941000, 941001), range(941100, 941101)
    elif mode == "serious":
        traces = real_loss_traces() + elite_traces("development", 6)
        fixed_seeds, natural_seeds = range(942000, 942004), range(942100, 942104)
    elif mode == "selection":
        traces = elite_traces("selection", 6)
        fixed_seeds, natural_seeds = range(943000, 943006), range(943100, 943106)
    else:
        traces = []
        fixed_seeds, natural_seeds = range(944000, 944010), range(944100, 944110)

    for name, path in candidates.items():
        for opponent in traces:
            for seat in (0, 1):
                rows.append((
                    f"{mode}|{name}|{opponent['name']}|{seat}", name, path,
                    opponent["family"], opponent["name"], trace(opponent["path"], opponent["player"]),
                    opponent["seed"], seat, opponent["schedule"], {},
                ))
        for seed in fixed_seeds:
            for seat in (0, 1):
                rows.append((f"{mode}|{name}|v2_fixed|{seed}|{seat}", name, path, "direct_v2_fixed", "V2", V2, seed, seat, _independent_shop_schedule(seed), {}))
        for seed in natural_seeds:
            for seat in (0, 1):
                rows.append((f"{mode}|{name}|v2_natural|{seed}|{seat}", name, path, "direct_v2_natural", "V2", V2, seed, seat, None, {}))
    return rows, traces


def run_one(job):
    key, name, path, group, opponent, opponent_spec, seed, seat, schedule, config = job
    candidate = run_path(str(ROOT / path))["agent"]
    rival = _load_opponent(opponent_spec)
    semantic = []
    bought = Counter()

    def checked(obs):
        action = candidate(obs)
        try:
            _semantic_validate(obs, action)
        except Exception as error:
            semantic.append({"step": int(obs["step"]), "error": repr(error), "action": action})
        for order in action.get("market", []):
            if order and order[0] == "BUY_ANIMAL":
                bought[order[1]] += int(order[2])
        return action

    pair = [rival, rival]
    pair[seat] = checked
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": int(seed), **config}, debug=True)
    runtime = None
    try:
        if schedule is None:
            env.run(pair)
        else:
            _run_with_fixed_shops(env, pair, schedule)
    except Exception as error:
        runtime = repr(error)
    if runtime or len(env.steps) != 720:
        return {"key": key, "candidate": name, "path": path, "group": group, "opponent": opponent,
                "seed": seed, "seat": seat, "runtime_error": runtime or f"steps={len(env.steps)}",
                "semantic_failures": semantic}
    final = env.steps[-1]
    stranded, quantities = _inventory_value(final[seat])
    _, animals, weeds = _farm_counts(final[seat].observation["farms"][seat])
    losses = {animal: max(0, bought[animal] - animals[animal]) for animal in ("GOOSE", "COW", "SHEEP")}
    telemetry = deepcopy(getattr(candidate, "telemetry", {}))
    requests = int(telemetry.get("backbone_actions_requested", 719))
    overrides = int(telemetry.get("dynamic_overrides", 0))
    return {
        "key": key, "candidate": name, "path": path, "group": group, "opponent": opponent,
        "seed": int(seed), "seat": int(seat), "money": float(final[seat].reward),
        "opponent_money": float(final[1-seat].reward),
        "advantage": float(final[seat].reward) - float(final[1-seat].reward),
        "runtime_error": None, "semantic_failures": semantic, "stranded_value": float(stranded),
        "stranded_quantities": quantities, "livestock_losses": losses, "final_weeds": weeds,
        "overrides": overrides, "override_rate": overrides / max(1, requests),
        "backbone_unchanged": int(telemetry.get("backbone_actions_unchanged", requests - overrides)),
        "override_counts": {key: int(telemetry.get(key, 0)) for key in (
            "market_overrides", "endgame_overrides", "capital_overrides",
            "crop_wave_overrides", "livestock_rescue_overrides",
        )},
        "override_log": telemetry.get("override_log", []),
    }


def summarize(games):
    output = {}
    for name in sorted({row["candidate"] for row in games}):
        rows = [row for row in games if row["candidate"] == name]
        valid = [row for row in rows if not row.get("runtime_error")]
        advantages = [row["advantage"] for row in valid]
        output[name] = {
            "games": len(rows), "valid_games": len(valid),
            "wins": sum(value > 0 for value in advantages), "losses": sum(value < 0 for value in advantages),
            "ties": sum(value == 0 for value in advantages),
            "average_money": statistics.fmean(row["money"] for row in valid) if valid else None,
            "average_advantage": statistics.fmean(advantages) if advantages else None,
            "p10": percentile(advantages, .10), "p5": percentile(advantages, .05),
            "variance": statistics.pvariance(advantages) if len(advantages) > 1 else 0,
            "average_override_rate": statistics.fmean(row["override_rate"] for row in valid) if valid else None,
            "runtime_failures": sum(bool(row.get("runtime_error")) for row in rows),
            "semantic_failures": sum(len(row.get("semantic_failures", [])) for row in rows),
            "livestock_losses": sum(sum(row.get("livestock_losses", {}).values()) for row in rows),
            "meaningful_stranding": sum(row.get("stranded_value", 0) > 500 for row in rows),
            "by_group": {},
        }
        for group in sorted({row["group"] for row in valid}):
            subset = [row for row in valid if row["group"] == group]
            output[name]["by_group"][group] = {
                "games": len(subset), "average_money": statistics.fmean(row["money"] for row in subset),
                "average_advantage": statistics.fmean(row["advantage"] for row in subset),
                "wins": sum(row["advantage"] > 0 for row in subset),
                "losses": sum(row["advantage"] < 0 for row in subset),
                "p10": percentile([row["advantage"] for row in subset], .10),
            }
    return output


def paired(games):
    baseline = {row["key"].replace("|V2|", "|*|"): row for row in games if row["candidate"] == "V2" and not row.get("runtime_error")}
    output = {}
    for name in sorted({row["candidate"] for row in games if row["candidate"] != "V2"}):
        deltas, rows = [], []
        for row in games:
            if row["candidate"] != name or row.get("runtime_error"):
                continue
            control = baseline.get(row["key"].replace(f"|{name}|", "|*|"))
            if not control:
                continue
            delta = row["money"] - control["money"]
            deltas.append(delta)
            rows.append({"key": row["key"], "money_delta": delta, "candidate_money": row["money"],
                         "v2_money": control["money"], "advantage_delta": row["advantage"] - control["advantage"]})
        output[name] = {
            "pairs": len(deltas), "wins": sum(value > 0 for value in deltas),
            "losses": sum(value < 0 for value in deltas), "ties": sum(value == 0 for value in deltas),
            "decisive_win_rate": sum(value > 0 for value in deltas) / max(1, sum(value != 0 for value in deltas)),
            "average_money_delta": statistics.fmean(deltas) if deltas else None,
            "median_money_delta": statistics.median(deltas) if deltas else None,
            "p10_money_delta": percentile(deltas, .10), "p5_money_delta": percentile(deltas, .05),
            "rows": rows,
        }
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("screen", "serious", "selection", "final"), default="screen")
    parser.add_argument("--names", default="")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    candidates = ALL_CANDIDATES
    if args.names:
        requested = set(args.names.split(",")) | {"V2"}
        candidates = {name: path for name, path in candidates.items() if name in requested}
    run_jobs, traces = jobs(candidates, args.mode)
    output = Path(args.output) if args.output else ROOT / f"experiments/v4_{args.mode}_ablations.json"
    partial = output.with_suffix(output.suffix + ".partial")
    games = json.loads(partial.read_text()).get("games", []) if partial.exists() else []
    done = {row["key"] for row in games}
    todo = [job for job in run_jobs if job[0] not in done]
    if args.workers <= 1:
        completed = ((index, run_one(job)) for index, job in enumerate(todo, 1))
    else:
        try:
            pool = ProcessPoolExecutor(max_workers=args.workers)
            futures = [pool.submit(run_one, job) for job in todo]
            completed = ((index, future.result()) for index, future in enumerate(as_completed(futures), 1))
        except (PermissionError, OSError):
            print("process workers unavailable; falling back to sequential execution", flush=True)
            completed = ((index, run_one(job)) for index, job in enumerate(todo, 1))
            pool = None
    try:
        for index, result in completed:
            games.append(result)
            if index % 8 == 0 or index == len(todo):
                partial.write_text(json.dumps({"schema_version": 1, "games": games}) + "\n")
                print(f"{args.mode} {index}/{len(todo)} total={len(games)}", flush=True)
    finally:
        if args.workers > 1 and 'pool' in locals() and pool is not None:
            pool.shutdown()
    payload = {
        "schema_version": 1, "mode": args.mode, "candidates": candidates,
        "trace_pool": traces, "games_expected": len(run_jobs), "games": games,
        "summary": summarize(games), "paired_vs_v2": paired(games),
    }
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    for name, row in payload["summary"].items():
        paired_row = payload["paired_vs_v2"].get(name, {})
        print(name, row["games"], f"{row['wins']}/{row['losses']}/{row['ties']}",
              round(row["average_money"], 1), round(row["average_advantage"], 1),
              "paired", paired_row.get("wins"), paired_row.get("losses"),
              round(paired_row.get("average_money_delta", 0), 1),
              "p10", round(paired_row.get("p10_money_delta", 0), 1),
              "safety", row["runtime_failures"], row["semantic_failures"], row["livestock_losses"], row["meaningful_stranding"])


if __name__ == "__main__":
    main()
