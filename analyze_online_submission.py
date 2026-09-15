"""Analyze official Kaggle episodes for a submitted agent, at checkpoint windows.

This generalizes ``analyze_v233h_online_submission.py`` (kept unchanged and
still runnable standalone) so the same extraction logic covers any tracked
candidate, and adds what that script did not need for a single baseline run:

- checkpoint windows at 30/60/100/130+ games instead of a fixed first/last 25
- shop-pair classification into yarn / added_non_yarn / blacklisted_non_yarn,
  read from a candidate's build receipt inside its research lock manifest
- livestock-escape detection, adapted from run_raw55899537_final_validation's
  animal_escapes() to dict-shaped official replay JSON instead of local
  Struct-shaped env.steps
- an agent_error flag from each episode's final-step status
- a structural diff against the V233H Safe online baseline summary, when its
  JSON is present locally (it is gitignored, so this only works on a machine
  that ran that baseline's own analysis first)

Known limitation, stated rather than silently skipped: the deeper per-step
semantic_check() action-legality validator used by local screens (e.g.
run_smaller_v233h_cross_lineage_gauntlet.py, run_latest_public_challenger_screen.py)
is NOT ported here. It validates the exact action dict an agent returned
against that step's observation, and porting it against official replay JSON
(where the action is recorded rather than intercepted) has not been verified
to match shapes exactly. Only the coarse final-step status flag is checked
here for "semantic failure" in the online-checkpoint sense; a true positive
would need re-running semantic_check against replay-recorded actions as a
follow-up, not assumed working.

Usage (after, per AGENTS.md, `kaggle competitions episodes <SUBMISSION_ID>`
then `kaggle competitions replay <EPISODE_ID> -p <replays-dir>` for each
episode id returned):

    python analyze_online_submission.py --candidate non_yarn_0911 \\
        --replays /path/to/downloaded/replays \\
        --submission-id <ID> [--public-score <SCORE>]

Writes experiments/<candidate>_online_submission.json (checkpoint-resolved
data, gitignored like other generated experiment JSON) and
experiments/<candidate>_online_submission.md (report).
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parent
CHECKPOINTS = (30, 60, 100, 130)

CANDIDATES = {
    "v233h_safe": {
        "team": "pig7selene",
        "default_submission_id": 56183575,
        "default_public_score": 2249.4,
        "lock": None,
        "baseline_of": None,
    },
    "non_yarn_0911": {
        "team": "pig7selene",
        "default_submission_id": None,
        "default_public_score": None,
        "lock": ROOT / "experiments/smaller_v233h_non_yarn_0911_lock_manifest.json",
        "baseline_of": "v233h_safe",
    },
}


def _pair_classifier(lock_path):
    """Return classify(pair) -> 'added_non_yarn'|'blacklisted_non_yarn'|'yarn', or None."""
    if lock_path is None or not lock_path.is_file():
        return None
    build = json.loads(lock_path.read_text())["build"]
    added = {tuple(pair) for pair in build["added_non_yarn_pairs"]}
    blacklisted = {tuple(pair) for pair in build["blacklisted_non_yarn_pairs"]}

    def classify(pair):
        pair = tuple(pair)
        if pair in added:
            return "added_non_yarn"
        if pair in blacklisted:
            return "blacklisted_non_yarn"
        return "yarn"

    return classify


def _counts(farm):
    crops, animals = Counter(), Counter()
    for row in farm["tiles"]:
        for tile in row:
            if not isinstance(tile, dict):
                continue
            if tile.get("kind") == "PLANT":
                crops[str(tile.get("crop"))] += 1
            elif tile.get("animal"):
                animals[str(tile.get("animal"))] += 1
    return crops, animals


def _livestock_escapes(steps, seat):
    """Dict-shaped adaptation of run_raw55899537_final_validation.animal_escapes,
    which assumes local Struct-shaped env.steps (`.observation`) instead of the
    plain-dict shape official replay JSON downloads in."""
    escapes = []
    for index in range(1, len(steps)):
        before = steps[index - 1][seat]["observation"]["farms"][seat]["tiles"]
        after = steps[index][seat]["observation"]["farms"][seat]["tiles"]
        for y, row in enumerate(before):
            for x, old in enumerate(row):
                old_animal = old.get("animal") if isinstance(old, dict) else None
                new = after[y][x]
                new_animal = new.get("animal") if isinstance(new, dict) else None
                if (
                    old_animal and not new_animal
                    and isinstance(new, dict) and new.get("kind") in {"COOP", "PASTURE"}
                ):
                    escapes.append({"step": index - 1, "animal": old_animal, "position": [x, y]})
    return escapes


def _appearance(path, replay, team, classify):
    teams = list(replay["info"]["TeamNames"])
    if team not in teams or teams[0] == teams[1]:
        return None
    seat = teams.index(team)
    opponent = 1 - seat
    final_states = replay["steps"][-1]
    rewards = [float(state["reward"]) for state in final_states]
    statuses = [str(state.get("status")) for state in final_states]
    peak_hands = [0, 0]
    peak_productive = [0, 0]
    peak_crops = [Counter(), Counter()]
    peak_animals = [Counter(), Counter()]
    land_steps = [[], []]
    last_step = min(719, len(replay["steps"]) - 1)

    for step in range(last_step):
        farms = replay["steps"][step][seat]["observation"]["farms"]
        next_farms = replay["steps"][step + 1][seat]["observation"]["farms"]
        for player in (0, 1):
            farm = farms[player]
            crops, animals = _counts(farm)
            peak_hands[player] = max(peak_hands[player], len(farm.get("hands", [])))
            peak_productive[player] = max(
                peak_productive[player], sum(crops.values()) + sum(animals.values())
            )
            for item, quantity in crops.items():
                peak_crops[player][item] = max(peak_crops[player][item], quantity)
            for item, quantity in animals.items():
                peak_animals[player][item] = max(peak_animals[player][item], quantity)
            quadrant_gain = len(next_farms[player].get("unlocked_quadrants", [])) - len(
                farm.get("unlocked_quadrants", [])
            )
            land_steps[player].extend([step] * max(0, quadrant_gain))

    shops = list(replay["steps"][last_step][seat]["observation"]["town"]["unlocked_shops"])
    pair = tuple(shops[:2])
    own_money, opponent_money = rewards[seat], rewards[opponent]
    return {
        "episode_id": int(replay["info"].get("EpisodeId") or path.stem.split("-")[1]),
        "seat": seat,
        "opponent": teams[opponent],
        "own_money": own_money,
        "opponent_money": opponent_money,
        "margin": own_money - opponent_money,
        "outcome": (
            "win" if own_money > opponent_money else "loss" if own_money < opponent_money else "tie"
        ),
        "shops": shops,
        "pair_class": classify(pair) if classify else None,
        "complete": len(replay["steps"]) - 1 == 719,
        "agent_error": any(status not in {"DONE", "Status.DONE"} for status in statuses),
        "livestock_escapes": _livestock_escapes(replay["steps"], seat),
        "opponent_livestock_escapes": _livestock_escapes(replay["steps"], opponent),
        "land_steps": land_steps[seat],
        "opponent_land_steps": land_steps[opponent],
        "max_hands": peak_hands[seat],
        "opponent_max_hands": peak_hands[opponent],
        "max_productive_tiles": peak_productive[seat],
        "opponent_max_productive_tiles": peak_productive[opponent],
        "peak_animals": dict(sorted(peak_animals[seat].items())),
        "opponent_peak_animals": dict(sorted(peak_animals[opponent].items())),
        "peak_crops": dict(sorted(peak_crops[seat].items())),
        "opponent_peak_crops": dict(sorted(peak_crops[opponent].items())),
    }


def _window(rows):
    if not rows:
        return None
    outcomes = Counter(row["outcome"] for row in rows)
    margins = [row["margin"] for row in rows]
    return {
        "games": len(rows),
        "wins": outcomes["win"],
        "losses": outcomes["loss"],
        "ties": outcomes["tie"],
        "gsr": (outcomes["win"] + 0.5 * outcomes["tie"]) / len(rows),
        "mean_own_money": statistics.fmean(row["own_money"] for row in rows),
        "mean_opponent_money": statistics.fmean(row["opponent_money"] for row in rows),
        "mean_margin": statistics.fmean(margins),
        "median_margin": statistics.median(margins),
        "worst_margin": min(margins),
        "agent_errors": sum(row["agent_error"] for row in rows),
        "incomplete_episodes": sum(not row["complete"] for row in rows),
        "livestock_escapes": sum(len(row["livestock_escapes"]) for row in rows),
        "opponent_livestock_escapes": sum(len(row["opponent_livestock_escapes"]) for row in rows),
    }


def _by_pair_class(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["pair_class"] or "unclassified"].append(row)
    return {cls: _window(subset) for cls, subset in sorted(grouped.items())}


def _by_shop_pair(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[tuple(row["shops"][:2])].append(row)
    out = []
    for pair, subset in grouped.items():
        window = _window(subset)  # subset is never empty: it came from grouping real rows
        assert window is not None
        out.append({"shops": list(pair), "pair_class": subset[0]["pair_class"], **window})
    out.sort(key=lambda row: (row["mean_margin"], row["shops"]))
    return out


def _worst_losses(rows, n=10):
    losses = sorted((row for row in rows if row["outcome"] == "loss"), key=lambda r: r["margin"])
    return losses[:n]


def _checkpoint(rows, n):
    subset = rows[:n]
    if len(subset) < n:
        return None
    return {
        "n": n,
        "overall": _window(subset),
        "by_pair_class": _by_pair_class(subset),
        "worst_losses_by_seat": {
            str(seat): _worst_losses([r for r in subset if r["seat"] == seat])
            for seat in (0, 1)
        },
    }


def _aggregate(rows, submission_id, public_score):
    return {
        "submission_id": submission_id,
        "public_score": public_score,
        "all": _window(rows),
        "checkpoints": {str(n): _checkpoint(rows, n) for n in CHECKPOINTS},
        "by_pair_class": _by_pair_class(rows),
        "by_shop_pair": _by_shop_pair(rows),
        "worst_losses_by_seat": {
            str(seat): _worst_losses([r for r in rows if r["seat"] == seat])
            for seat in (0, 1)
        },
    }


def _baseline_diff(summary, baseline_path):
    if baseline_path is None or not baseline_path.is_file():
        return None
    baseline = json.loads(baseline_path.read_text())["summary"]
    b_all, c_all = baseline["all"], summary["all"]
    return {
        "baseline_submission_id": baseline["submission_id"],
        "baseline_public_score": baseline["public_score"],
        "baseline_games": b_all["games"],
        "gsr_delta": c_all["gsr"] - b_all["gsr"],
        "mean_margin_delta": c_all["mean_margin"] - b_all["mean_margin"],
        "median_margin_delta": c_all["median_margin"] - b_all["median_margin"],
        "worst_margin_delta": c_all["worst_margin"] - b_all["worst_margin"],
        "note": (
            "Skill Rating snapshots from different time windows are not directly "
            "comparable; this diff is a structural signal (margin, tail losses, "
            "error/escape counts), not a rating comparison."
        ),
    }


def _report(data, candidate_name):
    summary = data["summary"]
    overall = summary["all"]
    if overall is None:
        return f"# {candidate_name} online submission diagnosis\n\nNo qualifying episodes yet.\n"
    lines = [
        f"# {candidate_name} online submission diagnosis",
        "",
        f"Submission {summary['submission_id']}"
        + (f" at public score {summary['public_score']:.1f}" if summary["public_score"] else "")
        + f". {overall['games']} public games parsed.",
        "",
        "## Overall",
        "",
        f"- W/L/T: {overall['wins']}/{overall['losses']}/{overall['ties']}, GSR {overall['gsr']:.4f}",
        f"- Mean/median/worst margin: {overall['mean_margin']:+.0f} / "
        f"{overall['median_margin']:+.0f} / {overall['worst_margin']:+.0f}",
        f"- Agent errors: {overall['agent_errors']}, incomplete episodes: "
        f"{overall['incomplete_episodes']}",
        f"- Livestock escapes: {overall['livestock_escapes']} (own), "
        f"{overall['opponent_livestock_escapes']} (opponent)",
        "",
        "## Checkpoints",
        "",
        "| N | W-L-T | GSR | Mean margin | Worst margin | Errors | Escapes |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for n in CHECKPOINTS:
        cp = summary["checkpoints"].get(str(n))
        if cp is None:
            lines.append(f"| {n} | not yet reached | | | | | |")
            continue
        o = cp["overall"]
        lines.append(
            f"| {n} | {o['wins']}-{o['losses']}-{o['ties']} | {o['gsr']:.3f} | "
            f"{o['mean_margin']:+.0f} | {o['worst_margin']:+.0f} | {o['agent_errors']} | "
            f"{o['livestock_escapes']} |"
        )
    lines.extend(["", "## By shop-pair class (yarn / added non-Yarn / blacklisted non-Yarn)", "",
                  "| Class | N | W-L-T | Mean margin | Worst margin |",
                  "| --- | ---: | ---: | ---: | ---: |"])
    for cls, w in summary["by_pair_class"].items():
        if w is None:
            continue
        lines.append(
            f"| {cls} | {w['games']} | {w['wins']}-{w['losses']}-{w['ties']} | "
            f"{w['mean_margin']:+.0f} | {w['worst_margin']:+.0f} |"
        )
    if data.get("baseline_diff"):
        d = data["baseline_diff"]
        lines.extend([
            "", "## Structural diff vs V233H Safe baseline "
            f"(submission {d['baseline_submission_id']}, {d['baseline_games']} games)", "",
            f"- GSR delta: {d['gsr_delta']:+.4f}",
            f"- Mean/median/worst margin delta: {d['mean_margin_delta']:+.0f} / "
            f"{d['median_margin_delta']:+.0f} / {d['worst_margin_delta']:+.0f}",
            f"- {d['note']}",
        ])
    lines.extend(["", "## Worst losses by seat", ""])
    for seat, rows in summary["worst_losses_by_seat"].items():
        lines.append(f"### Seat {seat}")
        lines.append("")
        lines.append("| Episode | Opponent | Margin | Shops | Class |")
        lines.append("| ---: | --- | ---: | --- | --- |")
        for row in rows:
            lines.append(
                f"| {row['episode_id']} | {row['opponent']} | {row['margin']:+.0f} | "
                f"{' + '.join(row['shops'])} | {row['pair_class']} |"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, choices=sorted(CANDIDATES))
    parser.add_argument("--replays", type=Path, required=True)
    parser.add_argument("--submission-id", type=int, default=None)
    parser.add_argument("--public-score", type=float, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()

    config = CANDIDATES[args.candidate]
    submission_id = args.submission_id or config["default_submission_id"]
    public_score = args.public_score if args.public_score is not None else config["default_public_score"]
    classify = _pair_classifier(config["lock"])
    output = args.output or ROOT / f"experiments/{args.candidate}_online_submission.json"
    report_path = args.report or ROOT / f"experiments/{args.candidate}_online_submission.md"

    rows, skipped = [], []
    paths = sorted(args.replays.glob("episode-*-replay.json"))
    if not paths:
        raise RuntimeError(f"no episode-*-replay.json files found under {args.replays}")
    for index, path in enumerate(paths, 1):
        replay = json.loads(path.read_text())
        row = _appearance(path, replay, config["team"], classify)
        if row is None:
            skipped.append(path.name)
        else:
            rows.append(row)
        if index % 20 == 0 or index == len(paths):
            print(f"parsed {index}/{len(paths)}", flush=True)
    rows.sort(key=lambda row: row["episode_id"])
    if not rows:
        raise RuntimeError(f"team {config['team']!r} not found in any replay under {args.replays}")

    summary = _aggregate(rows, submission_id, public_score)
    baseline_path = None
    if config["baseline_of"]:
        baseline_path = ROOT / f"experiments/{config['baseline_of']}_online_submission.json"
    data = {
        "schema_version": 1,
        "candidate": args.candidate,
        "source_directory": str(args.replays),
        "team": config["team"],
        "replay_files": len(paths),
        "skipped_validation_or_non_team_files": skipped,
        "summary": summary,
        "baseline_diff": _baseline_diff(summary, baseline_path),
        "games": rows,
    }
    output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    report_path.write_text(_report(data, args.candidate))
    print(output)
    print(report_path)


if __name__ == "__main__":
    main()
