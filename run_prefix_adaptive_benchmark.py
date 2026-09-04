"""Paired benchmark for the prefix-compatible adaptive route probe.

The candidate and the frozen Top-50 portfolio are each played from the same
deterministic seeds, against the same opponent, in both seats.  Results are
written after every completed game so an interrupted run can be resumed or
audited without losing the completed rows.
"""

from __future__ import annotations

import argparse
import json
import statistics
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from kaggle_environments import make

from benchmark import EPISODE_STEPS, ROOT, _file_sha256, _load_agent


BASELINE = ROOT / "agents" / "top50_distilled" / "top50_observable_portfolio.py"
CANDIDATES = {
    "current_best": BASELINE,
    "prefix_adaptive_v1": ROOT / "agents" / "autonomous_next" / "prefix_adaptive_portfolio_v1.py",
}
OPPONENTS = {
    "current_best": BASELINE,
    "tetsuya": ROOT / "agents" / "top3_tuned" / "raw_rank1_tetsuya.py",
    "crop_dusta": ROOT / "agents" / "top3_tuned" / "raw_rank2_crop_dusta.py",
    "oceanmix": ROOT / "agents" / "top3_tuned" / "raw_rank3_oceanmix.py",
    "livestock_crop": ROOT / "agents" / "proxies" / "livestock_crop.py",
    "land_expander": ROOT / "agents" / "proxies" / "land_expander.py",
    "high_labor": ROOT / "agents" / "proxies" / "high_labor.py",
    "phased_rotation": ROOT / "agents" / "proxies" / "phased_rotation.py",
}


def _run(job):
    candidate_name, candidate_path, opponent_name, opponent_path, seed, seat = job
    candidate = _load_agent(candidate_path)
    opponent = _load_agent(opponent_path)
    players = [opponent, opponent]
    players[seat] = candidate
    env = make("kaggriculture", configuration={"episodeSteps": EPISODE_STEPS, "seed": seed}, debug=True)
    env.run(players)
    final = env.steps[-1]
    statuses = [state.status for state in final]
    if len(env.steps) != EPISODE_STEPS or statuses != ["DONE", "DONE"]:
        raise RuntimeError(f"incomplete game: {candidate_name} vs {opponent_name} seed={seed} seat={seat}")
    money = [float(state.reward) for state in final]
    own = money[seat]
    other = money[1 - seat]
    telemetry = getattr(candidate, "telemetry", {}) or {}
    return {
        "candidate": candidate_name,
        "opponent": opponent_name,
        "seed": int(seed),
        "candidate_position": int(seat),
        "candidate_money": own,
        "opponent_money": other,
        "money_advantage": own - other,
        "runtime_error": None,
        "calls": int(telemetry.get("calls", 0)),
        "selected_route": telemetry.get("selected"),
        "switches": int(telemetry.get("switches", 0)),
    }


def _percentile(values, fraction):
    values = sorted(values)
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    index = fraction * (len(values) - 1)
    lo = int(index)
    hi = min(lo + 1, len(values) - 1)
    weight = index - lo
    return values[lo] * (1 - weight) + values[hi] * weight


def _summary(rows):
    adv = [r["money_advantage"] for r in rows]
    money = [r["candidate_money"] for r in rows]
    wins = sum(value > 0 for value in adv)
    losses = sum(value < 0 for value in adv)
    return {
        "games": len(rows),
        "wins": wins,
        "losses": losses,
        "ties": len(rows) - wins - losses,
        "win_rate": wins / len(rows) if rows else 0.0,
        "average_money": statistics.fmean(money) if money else 0.0,
        "median_money": statistics.median(money) if money else 0.0,
        "average_advantage": statistics.fmean(adv) if adv else 0.0,
        "median_advantage": statistics.median(adv) if adv else 0.0,
        "p10_advantage": _percentile(adv, 0.10),
        "p5_advantage": _percentile(adv, 0.05),
        "worst_advantage": min(adv) if adv else 0.0,
        "advantage_variance": statistics.variance(adv) if len(adv) > 1 else 0.0,
        "runtime_failures": sum(r.get("runtime_error") is not None for r in rows),
        "calls_short": sum(r.get("calls", 0) not in (0, 719) for r in rows),
    }


def _write_markdown(path, result):
    lines = [
        "# Prefix-compatible adaptive route benchmark",
        "",
        f"Seeds: `{result['seeds'][0]}–{result['seeds'][-1]}` ({len(result['seeds'])}); both seats; 720 turns.",
        "The candidate can switch only at turn 72 after an exact shared route prefix.",
        "",
        "| Candidate | Games | W/L/T | Win rate | Avg money | Avg advantage | Median advantage | P10 | P5 | Worst | SD advantage |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, row in result["summaries"].items():
        lines.append(
            f"| {name} | {row['games']} | {row['wins']}/{row['losses']}/{row['ties']} | "
            f"{100*row['win_rate']:.2f}% | {row['average_money']:.1f} | {row['average_advantage']:+.1f} | "
            f"{row['median_advantage']:+.1f} | {row['p10_advantage']:+.1f} | {row['p5_advantage']:+.1f} | "
            f"{row['worst_advantage']:+.1f} | {row['advantage_variance']**0.5:.1f} |"
        )
    lines.extend(["", "## Matchups", ""])
    for candidate in result["candidates"]:
        lines.extend([f"### {candidate}", "", "| Opponent | Games | W/L/T | Avg money | Avg advantage | P10 | Switches |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"])
        for opponent in result["opponents"]:
            rows = [r for r in result["games"] if r["candidate"] == candidate and r["opponent"] == opponent]
            item = _summary(rows)
            switches = sum(r.get("switches", 0) for r in rows)
            lines.append(f"| {opponent} | {item['games']} | {item['wins']}/{item['losses']}/{item['ties']} | {item['average_money']:.1f} | {item['average_advantage']:+.1f} | {item['p10_advantage']:+.1f} | {switches} |")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def run(seed_start, seeds_count, workers, stem):
    seeds = list(range(int(seed_start), int(seed_start) + int(seeds_count)))
    jobs = [
        (candidate, str(candidate_path), opponent, str(opponent_path), seed, seat)
        for candidate, candidate_path in CANDIDATES.items()
        for opponent, opponent_path in OPPONENTS.items()
        for seed in seeds
        for seat in (0, 1)
    ]
    print(f"Running {len(jobs)} games with {workers} workers", flush=True)
    rows = []
    errors = []
    out_json = ROOT / "experiments" / f"{stem}.json"
    out_md = ROOT / "experiments" / f"{stem}.md"

    def persist():
        summaries = {name: _summary([r for r in rows if r["candidate"] == name]) for name in CANDIDATES}
        payload = {
            "schema_version": 1,
            "experiment": "prefix_adaptive_portfolio",
            "seed_start": seed_start,
            "seeds": seeds,
            "candidates": list(CANDIDATES),
            "opponents": list(OPPONENTS),
            "candidate_paths": {name: str(path.relative_to(ROOT)) for name, path in CANDIDATES.items()},
            "candidate_sha256": {name: _file_sha256(path) for name, path in CANDIDATES.items()},
            "opponent_paths": {name: str(path.relative_to(ROOT)) for name, path in OPPONENTS.items()},
            "summaries": summaries,
            "games": sorted(rows, key=lambda r: (r["candidate"], r["opponent"], r["seed"], r["candidate_position"])),
            "errors": errors,
        }
        out_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        _write_markdown(out_md, payload)
        return payload

    if workers <= 1:
        for index, job in enumerate(jobs, 1):
            try:
                rows.append(_run(job))
            except Exception as exc:
                errors.append({"job": job, "error": repr(exc)})
            persist()
            print(f"completed {index}/{len(jobs)}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_run, job): job for job in jobs}
            for index, future in enumerate(as_completed(futures), 1):
                job = futures[future]
                try:
                    rows.append(future.result())
                except Exception as exc:
                    errors.append({"job": job, "error": repr(exc)})
                if index % 4 == 0 or index == len(jobs):
                    persist()
                    print(f"completed {index}/{len(jobs)}", flush=True)
    result = persist()
    print(json.dumps(result["summaries"], indent=2))
    print(f"Saved {out_json}\nSaved {out_md}")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-start", type=int, default=61000)
    parser.add_argument("--seeds", type=int, default=2)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--stem", default="prefix_adaptive_dev")
    args = parser.parse_args()
    run(args.seed_start, args.seeds, args.workers, args.stem)


if __name__ == "__main__":
    main()
