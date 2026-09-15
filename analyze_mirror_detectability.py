"""How early, and from what, can we tell we are facing our own lineage?

The loss-mode analysis found that 55% of our official opponents run our own
tape lineage under another team name, that we score 0.767 GSR against them
versus 0.852 against everyone else, and that 65% of our losses come from that
group. The mechanism is that both seats dump about 6,188 wool into a market
whose equilibrium inventory is 10,000, so the price hits the floor and the same
volume that fetches 1.4M in other games fetches about 10,600.

Any adaptive response needs a trigger, and the trigger has to fire early enough
to still be worth something. This script asks two questions:

1. At each step, how separable are mirror and non-mirror games from what we can
   actually observe? The opponent's farm is visible in the observation -- money,
   hands, tiles, unlocked quadrants -- so the natural detector is how closely
   the opponent's board tracks our own.
2. Given the step at which detection becomes reliable, which interventions are
   still open? Buying fewer sheep is only available before the sheep are bought;
   shifting the wool sale window is available until the wool is sold.

Labels come from end-of-game sale volumes, which is the thing we are trying to
predict early. Nothing is downloaded and no sealed material is read.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parent
CORPUS = Path("/private/tmp/kaggriculture_v233h_online")
LOSS_MODE = ROOT / "experiments" / "loss_mode_analysis.json"
OUTPUT = ROOT / "experiments" / "mirror_detectability.json"
REPORT = ROOT / "experiments" / "mirror_detectability.md"
TEAM = "pig7selene"
SAMPLE_EVERY = 24          # one probe per in-game day
FEATURES = ("board_l1", "money_gap", "hands_gap", "quadrant_gap")


def board_vector(farm: dict) -> Counter:
    vec = Counter()
    for row in farm["tiles"]:
        for tile in row:
            if not isinstance(tile, dict):
                continue
            if tile.get("kind") == "PLANT":
                vec[f"crop:{tile.get('crop')}"] += 1
            elif tile.get("animal"):
                vec[f"animal:{tile.get('animal')}"] += 1
            elif tile.get("kind"):
                vec[f"kind:{tile.get('kind')}"] += 1
    return vec


def features_at(steps, index: int, seat: int, other: int) -> dict:
    farms = steps[index][seat]["observation"]["farms"]
    ours, theirs = farms[seat], farms[other]
    ov, tv = board_vector(ours), board_vector(theirs)
    keys = set(ov) | set(tv)
    l1 = sum(abs(ov[k] - tv[k]) for k in keys)
    scale = max(1, sum(ov.values()))
    return {
        "board_l1": l1 / scale,
        "money_gap": abs(float(ours["money"]) - float(theirs["money"]))
        / max(1.0, abs(float(ours["money"]))),
        "hands_gap": abs(len(ours.get("hands", [])) - len(theirs.get("hands", []))),
        "quadrant_gap": abs(len(ours.get("unlocked_quadrants", []))
                            - len(theirs.get("unlocked_quadrants", []))),
    }


def first_purchase(steps, seat: int, kind: str, what: str) -> int | None:
    for index, entry in enumerate(steps):
        for order in (entry[seat].get("action") or {}).get("market") or []:
            if order and order[0] == kind and len(order) > 1 and order[1] == what:
                return index
    return None


def auc(positive: list[float], negative: list[float]) -> float:
    """Probability a random mirror scores below a random non-mirror.

    Lower feature values mean 'more similar to us', so a good detector gives an
    AUC near 1 when mirrors sit below non-mirrors.
    """
    if not positive or not negative:
        return 0.5
    wins = ties = 0
    for p in positive:
        for n in negative:
            if p < n:
                wins += 1
            elif p == n:
                ties += 1
    return (wins + 0.5 * ties) / (len(positive) * len(negative))


def best_threshold(positive: list[float], negative: list[float]) -> tuple[float, float]:
    candidates = sorted(set(positive) | set(negative))
    best, cut = 0.0, 0.0
    total = len(positive) + len(negative)
    for value in candidates:
        correct = sum(1 for p in positive if p <= value) + sum(1 for n in negative if n > value)
        if correct / total > best:
            best, cut = correct / total, value
    return best, cut


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=CORPUS)
    parser.add_argument("--team", default=TEAM)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()

    loss_mode = json.loads(LOSS_MODE.read_text())
    reference = loss_mode["mirror_fingerprint"]["our_reference_volumes"]
    tolerance = loss_mode["mirror_fingerprint"]["tolerance"]
    label_by_episode, outcome_by_episode = {}, {}
    for game in loss_mode["games"]:
        hits = 0
        for resource, mine in reference.items():
            theirs = game["theirs"].get(resource)
            if theirs and abs(theirs["units"] - mine) <= max(50.0, mine * tolerance):
                hits += 1
        label_by_episode[game["episode_id"]] = hits >= 3
        outcome_by_episode[game["episode_id"]] = game["outcome"]

    probes = list(range(0, 720, SAMPLE_EVERY))
    samples: dict[int, dict[str, dict[str, list]]] = {
        step: {f: {"mirror": [], "non_mirror": []} for f in FEATURES} for step in probes
    }
    timing = {"first_sheep_purchase": [], "first_wool_sale": [], "last_wool_sale": []}

    paths = sorted(args.corpus.glob("episode-*-replay.json"))
    for count, path in enumerate(paths, 1):
        replay = json.loads(path.read_text())
        teams = list(replay["info"]["TeamNames"])
        if args.team not in teams or teams[0] == teams[1]:
            continue
        episode_id = int(replay["info"].get("EpisodeId") or path.stem.split("-")[1])
        if episode_id not in label_by_episode:
            continue
        seat, other = teams.index(args.team), 1 - teams.index(args.team)
        steps = replay["steps"]
        bucket = "mirror" if label_by_episode[episode_id] else "non_mirror"
        for step in probes:
            if step >= len(steps):
                continue
            values = features_at(steps, step, seat, other)
            for feature in FEATURES:
                samples[step][feature][bucket].append(values[feature])
        sheep = first_purchase(steps, seat, "BUY_ANIMAL", "SHEEP")
        if sheep is not None:
            timing["first_sheep_purchase"].append(sheep)
        wool_steps = [i for i, e in enumerate(steps)
                      for o in ((e[seat].get("action") or {}).get("market") or [])
                      if o and o[0] == "SELL" and len(o) > 1 and o[1] == "WOOL"]
        if wool_steps:
            timing["first_wool_sale"].append(min(wool_steps))
            timing["last_wool_sale"].append(max(wool_steps))
        if count % 20 == 0 or count == len(paths):
            print(f"  {count}/{len(paths)}", flush=True)

    curves = {}
    for feature in FEATURES:
        rows = []
        for step in probes:
            pos = samples[step][feature]["mirror"]
            neg = samples[step][feature]["non_mirror"]
            if not pos or not neg:
                continue
            accuracy, cut = best_threshold(pos, neg)
            rows.append({"step": step, "auc": auc(pos, neg), "accuracy": accuracy,
                         "threshold": cut, "n_mirror": len(pos), "n_non_mirror": len(neg)})
        curves[feature] = rows

    def earliest(rows, target):
        for row in rows:
            if row["accuracy"] >= target:
                return row
        return None

    timing_summary = {
        k: {"median": statistics.median(v), "min": min(v), "max": max(v), "n": len(v)}
        for k, v in timing.items() if v
    }
    data = {
        "schema_version": 1,
        "corpus": str(args.corpus),
        "submission_id": 56183575,
        "sample_every": SAMPLE_EVERY,
        "labels": {"mirror": sum(label_by_episode.values()),
                   "non_mirror": sum(1 for v in label_by_episode.values() if not v)},
        "curves": curves,
        "earliest_step_at_accuracy": {
            feature: {str(t): earliest(curves[feature], t) for t in (0.80, 0.90, 0.95)}
            for feature in FEATURES
        },
        "our_commitment_timing": timing_summary,
        "sealed_g1_holdout_opened": False,
    }
    args.output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    lines = ["# Mirror detectability", "",
             f"{data['labels']['mirror']} mirror and {data['labels']['non_mirror']} non-mirror "
             f"episodes of submission 56183575, probed every {SAMPLE_EVERY} steps. Lower "
             "feature values mean the opponent's board is tracking ours.", "",
             "## Earliest step reaching a given classification accuracy", "",
             "| Feature | 80% | 90% | 95% |", "| --- | ---: | ---: | ---: |"]
    for feature in FEATURES:
        cells = []
        for target in ("0.8", "0.9", "0.95"):
            row = data["earliest_step_at_accuracy"][feature][target]
            cells.append(f"{row['step']}" if row else "never")
        lines.append(f"| {feature} | " + " | ".join(cells) + " |")
    lines += ["", "## Accuracy by step (best single feature per step)", "",
              "| Step | " + " | ".join(FEATURES) + " |",
              "| ---: | " + " | ".join("---:" for _ in FEATURES) + " |"]
    for index, step in enumerate(probes):
        cells = []
        for feature in FEATURES:
            row = next((r for r in curves[feature] if r["step"] == step), None)
            cells.append(f"{row['accuracy']:.2f}" if row else "-")
        if any(c != "-" for c in cells) and step % 72 == 0:
            lines.append(f"| {step} | " + " | ".join(cells) + " |")
    lines += ["", "## What is still open when detection fires", "",
              "| Commitment | Median step | Earliest | Latest |", "| --- | ---: | ---: | ---: |"]
    for key, row in timing_summary.items():
        lines.append(f"| {key} | {row['median']:.0f} | {row['min']} | {row['max']} |")
    args.report.write_text("\n".join(lines) + "\n")
    print(args.output)
    print(args.report)


if __name__ == "__main__":
    main()
