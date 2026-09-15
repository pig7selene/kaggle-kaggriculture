"""Compositional market module for Majkel G1: one predictor per order slot.

The flat version of this module predicted the whole market action as one of
2,720 atomic classes and scored 0.5511 leave-one-out, against 0.5445 for block
routing on the same 40 episodes. It is capped by construction: a tree leaf
votes for a single class, and classes seen fewer than five times cover 10.7% of
all steps, fewer than twenty 17.1%. No amount of tuning reaches those steps.

A market action is not an atomic symbol, it is a list of orders drawn from only
20 distinct (verb, resource) slots. Predicting each slot's quantity separately
and composing collapses the label space by a factor of 136, gives every slot
hundreds to thousands of training examples instead of a long tail of triples,
and can emit combinations that never occur in training, which the flat model
can never do.

Composition needs an order for the emitted list, because the metric is exact
match against an ordered list. Measured on the development set: the component
set alone determines the order in 83.1% of non-empty steps, and taking the most
frequent order per component set covers 94.0%, so order reconstruction costs at
most about 3.7% of all steps.

Discipline unchanged: development is the 40 episodes named in
experiments/majkel_g1_split_lock.json, scoring is leave-one-episode-out inside
that set, and the sealed G1 holdout is not touched.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

import numpy as np

from analyze_v27_routes import normalized_action
from build_majkel_g1_market_module import (
    Tree, development_paths, feature_names, features,
)


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "experiments" / "majkel_g1_market_module_compositional.json"
REPORT = ROOT / "experiments" / "majkel_g1_market_module_compositional.md"
TEAM = "Majkel1337"
QTY_CAP = 12          # quantities above this share one bucket
VERB_ORDER = ("HIRE", "BUY_LAND", "BUY_ANIMAL", "BUY_SEED", "BUY_PRODUCT", "SELL")


def slot_of(order) -> tuple[str, str]:
    return (str(order[0]), str(order[1]) if len(order) > 1 else "-")


def quantity_of(order) -> int:
    return int(order[2]) if len(order) > 2 else 1


def load(paths: list[Path]) -> list[dict]:
    episodes = []
    for index, path in enumerate(paths, 1):
        replay = json.loads(path.read_text())
        teams = list(replay["info"]["TeamNames"])
        if TEAM not in teams:
            continue
        seat = teams.index(TEAM)
        base = dict(replay["steps"][0][seat]["observation"]["market"]["prices"])
        rows, actions = [], []
        for step in range(719):
            rows.append(features(replay["steps"][step][seat]["observation"], seat, base))
            actions.append([o for o in normalized_action(replay, seat, step)["market"] if o])
        episodes.append({
            "episode_id": int(replay["info"].get("EpisodeId") or path.stem.split("-")[1]),
            "X": np.asarray(rows, dtype=np.float64),
            "actions": actions,
        })
        print(f"  loaded {index}/{len(paths)}", flush=True)
    return episodes


def slot_labels(actions, slot) -> np.ndarray:
    """Quantity for this slot at each step, 0 when the slot is absent."""
    out = np.zeros(len(actions), dtype=np.int64)
    for index, orders in enumerate(actions):
        for order in orders:
            if slot_of(order) == slot:
                out[index] = min(quantity_of(order), QTY_CAP)
    return out


def canonical_orders(train_actions) -> dict:
    """Most frequent emission order for each component set seen in training."""
    tally: dict[tuple, Counter] = defaultdict(Counter)
    for orders in train_actions:
        if not orders:
            continue
        slots = tuple(slot_of(o) for o in orders)
        tally[tuple(sorted(slots))][slots] += 1
    return {key: counter.most_common(1)[0][0] for key, counter in tally.items()}


def compose(predicted: dict, canonical: dict) -> list:
    """Assemble an ordered market action from predicted per-slot quantities."""
    if not predicted:
        return []
    key = tuple(sorted(predicted))
    if key in canonical:
        sequence = canonical[key]
    else:
        # Unseen combination: fall back to a fixed verb order, resource-sorted.
        sequence = tuple(sorted(
            predicted, key=lambda s: (VERB_ORDER.index(s[0]) if s[0] in VERB_ORDER
                                      else len(VERB_ORDER), s[1])
        ))
    out = []
    for slot in sequence:
        quantity = predicted.get(slot)
        if quantity is None:
            continue
        out.append([slot[0]] if slot[0] == "HIRE" else [slot[0], slot[1], int(quantity)])
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-depth", type=int, default=12)
    parser.add_argument("--min-leaf", type=int, default=30)
    parser.add_argument("--folds", type=int, default=0)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()

    episodes = load(development_paths())
    slots = sorted({slot_of(o) for ep in episodes for orders in ep["actions"] for o in orders})
    print(f"slots: {len(slots)}", flush=True)
    for ep in episodes:
        ep["slot_y"] = {slot: slot_labels(ep["actions"], slot) for slot in slots}
        ep["truth"] = [json.dumps(orders) for orders in ep["actions"]]

    names = feature_names()
    correct = total = 0
    per_episode, usage = [], Counter()
    slot_hits = {slot: [0, 0] for slot in slots}
    folds = args.folds if args.folds > 0 else len(episodes)

    for held in range(folds):
        train = [ep for i, ep in enumerate(episodes) if i != held]
        X = np.concatenate([ep["X"] for ep in train])
        canonical = canonical_orders([a for ep in train for a in ep["actions"]])
        test = episodes[held]

        predictions: dict[tuple, np.ndarray] = {}
        for slot in slots:
            y = np.concatenate([ep["slot_y"][slot] for ep in train])
            if y.max() == 0:
                predictions[slot] = np.zeros(len(test["X"]), dtype=np.int64)
                continue
            tree = Tree(args.max_depth, args.min_leaf).fit(X, y, int(y.max()) + 1)
            for node in tree.nodes:
                if not node["leaf"]:
                    usage[names[node["feature"]]] += 1
            predictions[slot] = tree.predict(test["X"])
            truth = test["slot_y"][slot]
            slot_hits[slot][0] += int((predictions[slot] == truth).sum())
            slot_hits[slot][1] += len(truth)

        hit = 0
        for index in range(len(test["X"])):
            chosen = {slot: int(predictions[slot][index]) for slot in slots
                      if predictions[slot][index] > 0}
            if json.dumps(compose(chosen, canonical)) == test["truth"][index]:
                hit += 1
        correct += hit
        total += len(test["X"])
        per_episode.append({"episode_id": test["episode_id"], "steps": len(test["X"]),
                            "correct": hit, "accuracy": hit / len(test["X"])})
        print(f"  fold {held + 1}/{folds}  ep{test['episode_id']} "
              f"{hit / len(test['X']):.4f}  running {correct / total:.4f}", flush=True)

    accuracy = correct / total
    data = {
        "schema_version": 1,
        "channel": "market",
        "model": {"kind": "one decision tree per (verb, resource) slot",
                  "slots": len(slots), "max_depth": args.max_depth,
                  "min_leaf": args.min_leaf, "quantity_cap": QTY_CAP,
                  "features": len(names)},
        "evaluation": "leave-one-episode-out over the 40 development episodes",
        "sealed_g1_holdout_opened": False,
        "folds_run": folds,
        "steps": total,
        "accuracy": accuracy,
        "baselines": {
            "majority_class": 0.3887,
            "block_router_state_heavy_market": 0.5445,
            "flat_tree_same_data": 0.5511,
            "per_step_nearest_neighbour_state_heavy_market_15_episodes_only": 0.5629,
        },
        "per_slot_accuracy": {
            f"{slot[0]} {slot[1]}": (hits / seen if seen else None)
            for slot, (hits, seen) in slot_hits.items()
        },
        "top_split_features": dict(usage.most_common(15)),
        "per_episode": per_episode,
    }
    args.output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    lines = ["# Majkel G1 market module, compositional", "",
             f"One decision tree per (verb, resource) slot, {len(slots)} slots, "
             f"leave-one-episode-out over {folds} development episodes "
             f"({total:,} steps). Sealed G1 holdout not opened.", "",
             "| Model | Market-action accuracy | Same data |",
             "| --- | ---: | --- |",
             "| Majority class (empty action) | 0.3887 | 40 episodes |",
             "| Block router, state_heavy | 0.5445 | 40 episodes |",
             "| Flat tree over 2,720 atomic classes | 0.5511 | 40 episodes |",
             f"| **This module** | **{accuracy:.4f}** | "
             f"{'40 episodes' if folds == len(episodes) else f'{folds} folds'} |",
             "| Per-step nearest neighbour, state_heavy | 0.5629 | 15 episodes, not comparable |",
             "", "## Per-slot accuracy", "", "| Slot | Accuracy |", "| --- | ---: |"]
    for slot, (hits, seen) in sorted(slot_hits.items(), key=lambda kv: -kv[1][1]):
        if seen:
            lines.append(f"| {slot[0]} {slot[1]} | {hits / seen:.4f} |")
    lines += ["", "## Most used split features", "", "| Feature | Splits |", "| --- | ---: |"]
    for name, count in usage.most_common(15):
        lines.append(f"| {name} | {count} |")
    args.report.write_text("\n".join(lines) + "\n")
    print(args.output)
    print(args.report)
    print(f"accuracy {accuracy:.4f}")


if __name__ == "__main__":
    main()
