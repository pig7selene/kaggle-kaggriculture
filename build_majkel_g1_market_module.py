"""A state-conditioned market module for Majkel G1, and its leave-one-out score.

Phase 1 established that whole-episode selection is capped: an oracle picking
the best source episode per 72-step block reaches 28.5% exact-action match and
under 3% after step 432, while the best realised routing gets 19.6%. The G0
report's prescription was that G1 must learn shop- and state-conditioned
modules rather than select a recorded episode, and both LOO studies ranked the
shop signal last and farm state first.

This builds the market channel of such a module: a small decision tree over
observable state that predicts the whole normalised market action for a step.
The market channel was chosen because it is the weakest subsystem in both prior
studies (54.5% under block routing, 56.3% under per-step nearest neighbour)
while the three channels fail near-independently, so a gain here multiplies
through the exact-action rate.

Baselines it has to beat, all on the same 40 development episodes:

- 38.9%, predicting the majority class (an empty market action) every step
- 54.5%, the block router's state_heavy profile on the market channel

Discipline: the sealed G1 holdout is not touched. Development is the 40
episodes named in experiments/majkel_g1_split_lock.json, and scoring here is
leave-one-episode-out inside that set. Freezing and opening the seal is a
separate, later step, and by the seal's own rule cannot be followed by tuning.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np

from analyze_v27_routes import normalized_action


ROOT = Path(__file__).resolve().parent
CORPUS = Path("/private/tmp/kaggriculture_majkel_56156662")
MANIFEST = ROOT / "experiments" / "majkel_56156662_corpus_manifest.json"
SEAL = ROOT / "experiments" / "majkel_g1_split_lock.json"
OUTPUT = ROOT / "experiments" / "majkel_g1_market_module.json"
REPORT = ROOT / "experiments" / "majkel_g1_market_module.md"
TEAM = "Majkel1337"
RESOURCES = ("CARROT", "EGG", "FERTILIZER", "MELON", "MILK", "STRAWBERRY",
             "TOMATO", "WHEAT", "WOOL")
SEEDS = ("CARROT", "MELON", "STRAWBERRY", "TOMATO", "WHEAT")
ANIMALS = ("COW", "SHEEP", "GOOSE")
SHOP_DEMAND = {
    "BAKERY": {"EGG": 1, "WHEAT": 1},
    "PIZZA_SHOP": {"MILK": 1, "TOMATO": 1, "WHEAT": 1},
    "BRUNCH_SPOT": {"EGG": 1, "WHEAT": 1, "STRAWBERRY": 1},
    "YARN_STORE": {"WOOL": 2},
    "ICE_CREAM_SHOP": {"STRAWBERRY": 1, "MILK": 1, "WHEAT": 1},
    "PET_CAFE": {"CARROT": 2},
    "SMOOTHIE_SHOP": {"STRAWBERRY": 1, "MILK": 1},
    "FARMERS_MARKET": {"WHEAT": 1, "CARROT": 1, "TOMATO": 1, "STRAWBERRY": 1},
}


def feature_names() -> list[str]:
    names = ["step", "day", "hour", "money", "hands", "quadrants", "productive_tiles"]
    names += [f"shed:{r}" for r in RESOURCES]
    names += [f"seed:{s}" for s in SEEDS]
    names += [f"inv_excess:{r}" for r in RESOURCES]
    names += [f"price_vs_base:{r}" for r in RESOURCES]
    names += [f"demand:{r}" for r in RESOURCES]
    names += [f"crop:{s}" for s in SEEDS]
    names += [f"animal:{a}" for a in ANIMALS]
    names += ["ripe_tiles", "unwatered_tiles"]
    return names


def features(obs: dict, seat: int, base: dict) -> list[float]:
    farm = obs["farms"][seat]
    private = obs.get("private", {})
    shed = private.get("shed", {}) or {}
    seeds = private.get("seeds", {}) or {}
    inventory = obs["market"]["inventory"]
    prices = obs["market"]["prices"]
    demand: Counter = Counter()
    for shop in obs["town"].get("unlocked_shops", []):
        demand.update(SHOP_DEMAND.get(shop, {}))

    crops, animals = Counter(), Counter()
    ripe = unwatered = 0
    for row in farm["tiles"]:
        for tile in row:
            if not isinstance(tile, dict):
                continue
            if tile.get("kind") == "PLANT":
                crops[str(tile.get("crop"))] += 1
                if tile.get("yield_units"):
                    ripe += 1
                if not tile.get("watered_today"):
                    unwatered += 1
            elif tile.get("animal"):
                animals[str(tile.get("animal"))] += 1

    step = int(obs.get("step", 0))
    row = [
        step, step // 24, step % 24, float(farm["money"]),
        len(farm.get("hands", [])), len(farm.get("unlocked_quadrants", [])),
        sum(crops.values()) + sum(animals.values()),
    ]
    row += [float(shed.get(r, 0)) for r in RESOURCES]
    row += [float(seeds.get(s, 0)) for s in SEEDS]
    row += [float(inventory.get(r, 10000)) - 10000.0 for r in RESOURCES]
    row += [float(prices.get(r, 0)) / base[r] if base.get(r) else 0.0 for r in RESOURCES]
    row += [float(demand.get(r, 0)) for r in RESOURCES]
    row += [float(crops.get(s, 0)) for s in SEEDS]
    row += [float(animals.get(a, 0)) for a in ANIMALS]
    row += [float(ripe), float(unwatered)]
    return row


class Tree:
    """Greedy classification tree with quantile-bucketed split candidates.

    Hand-rolled because scikit-learn is not installed and installing it is not
    this task's business. Bucketing keeps the split search to a handful of numpy
    passes per node, which matters because scoring is 40 leave-one-out fits.
    """

    __slots__ = ("max_depth", "min_leaf", "bins", "nodes")

    def __init__(self, max_depth=10, min_leaf=25, bins=32):
        self.max_depth, self.min_leaf, self.bins = max_depth, min_leaf, bins
        self.nodes: list = []

    @staticmethod
    def _impurity(counts: np.ndarray) -> float:
        total = counts.sum()
        if total <= 0:
            return 0.0
        p = counts[counts > 0] / total
        return float(-(p * np.log(p)).sum() * total)

    def _thresholds(self, column: np.ndarray) -> np.ndarray:
        qs = np.linspace(0, 1, self.bins + 1)[1:-1]
        return np.unique(np.quantile(column, qs))

    def fit(self, X: np.ndarray, y: np.ndarray, n_classes: int):
        self.nodes = []
        self._build(X, y, n_classes, 0)
        return self

    def _build(self, X, y, n_classes, depth) -> int:
        node_id = len(self.nodes)
        counts = np.bincount(y, minlength=n_classes)
        self.nodes.append({"leaf": True, "pred": int(counts.argmax())})
        if depth >= self.max_depth or len(y) < 2 * self.min_leaf or counts.max() == len(y):
            return node_id

        parent = self._impurity(counts)
        best = (0.0, -1, 0.0)
        for feature in range(X.shape[1]):
            column = X[:, feature]
            for threshold in self._thresholds(column):
                mask = column <= threshold
                left = int(mask.sum())
                if left < self.min_leaf or len(y) - left < self.min_leaf:
                    continue
                gain = parent - self._impurity(np.bincount(y[mask], minlength=n_classes)) \
                    - self._impurity(np.bincount(y[~mask], minlength=n_classes))
                if gain > best[0]:
                    best = (gain, feature, float(threshold))

        if best[1] < 0 or best[0] <= 0:
            return node_id
        mask = X[:, best[1]] <= best[2]
        self.nodes[node_id] = {"leaf": False, "feature": best[1], "threshold": best[2],
                               "left": None, "right": None}
        left_id = self._build(X[mask], y[mask], n_classes, depth + 1)
        right_id = self._build(X[~mask], y[~mask], n_classes, depth + 1)
        self.nodes[node_id]["left"] = left_id
        self.nodes[node_id]["right"] = right_id
        return node_id

    def predict(self, X: np.ndarray) -> np.ndarray:
        out = np.empty(len(X), dtype=np.int64)
        for i, row in enumerate(X):
            node = self.nodes[0]
            while not node["leaf"]:
                node = self.nodes[node["left"] if row[node["feature"]] <= node["threshold"]
                                  else node["right"]]
            out[i] = node["pred"]
        return out


def development_paths() -> list[Path]:
    manifest = json.loads(MANIFEST.read_text())
    sealed = set(manifest["seal_integrity"]["sealed_ids_declared"])
    paths = []
    for row in manifest["episodes"]:
        if row["sealed"] or row["episode_id"] in sealed:
            continue
        paths.append(Path(row["source_path"]) if "source_path" in row
                     else CORPUS / row["subset"] / row["replay_filename"])
    if {int(p.stem.split("-")[1]) for p in paths} & sealed:
        raise RuntimeError("sealed holdout episode entered development")
    return [p for p in paths if p.is_file()]


def load(paths: list[Path]):
    episodes = []
    for index, path in enumerate(paths, 1):
        replay = json.loads(path.read_text())
        teams = list(replay["info"]["TeamNames"])
        if TEAM not in teams:
            continue
        seat = teams.index(TEAM)
        base = dict(replay["steps"][0][seat]["observation"]["market"]["prices"])
        rows, labels = [], []
        for step in range(719):
            obs = replay["steps"][step][seat]["observation"]
            rows.append(features(obs, seat, base))
            labels.append(json.dumps(normalized_action(replay, seat, step)["market"]))
        episodes.append({
            "episode_id": int(replay["info"].get("EpisodeId") or path.stem.split("-")[1]),
            "X": np.asarray(rows, dtype=np.float64), "labels": labels,
        })
        print(f"  loaded {index}/{len(paths)}", flush=True)
    return episodes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-depth", type=int, default=12)
    parser.add_argument("--min-leaf", type=int, default=20)
    parser.add_argument("--folds", type=int, default=0,
                        help="limit leave-one-out folds for a smoke test; 0 runs all")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()

    episodes = load(development_paths())
    vocabulary = sorted({label for ep in episodes for label in ep["labels"]})
    index_of = {label: i for i, label in enumerate(vocabulary)}
    for ep in episodes:
        ep["y"] = np.asarray([index_of[l] for l in ep["labels"]], dtype=np.int64)

    all_labels = [l for ep in episodes for l in ep["labels"]]
    majority = Counter(all_labels).most_common(1)[0]
    names = feature_names()

    correct = total = 0
    per_episode, usage = [], Counter()
    folds = args.folds if args.folds > 0 else len(episodes)
    for held in range(folds):
        train = [ep for i, ep in enumerate(episodes) if i != held]
        X = np.concatenate([ep["X"] for ep in train])
        y = np.concatenate([ep["y"] for ep in train])
        tree = Tree(args.max_depth, args.min_leaf).fit(X, y, len(vocabulary))
        for node in tree.nodes:
            if not node["leaf"]:
                usage[names[node["feature"]]] += 1
        test = episodes[held]
        hit = int((tree.predict(test["X"]) == test["y"]).sum())
        correct += hit
        total += len(test["y"])
        per_episode.append({"episode_id": test["episode_id"], "steps": len(test["y"]),
                            "correct": hit, "accuracy": hit / len(test["y"])})
        print(f"  fold {held + 1}/{len(episodes)}  ep{test['episode_id']} "
              f"{hit / len(test['y']):.4f}  running {correct / total:.4f}", flush=True)

    accuracy = correct / total
    data = {
        "schema_version": 1,
        "channel": "market",
        "evaluation": "leave-one-episode-out over the 40 development episodes",
        "sealed_g1_holdout_opened": False,
        "development_episode_ids": sorted(ep["episode_id"] for ep in episodes),
        "model": {"kind": "decision tree", "max_depth": args.max_depth,
                  "min_leaf": args.min_leaf, "features": len(names),
                  "label_vocabulary": len(vocabulary)},
        "steps": total,
        "accuracy": accuracy,
        "baselines": {
            "majority_class": {"label": majority[0][:60],
                               "accuracy": majority[1] / len(all_labels)},
            "block_router_state_heavy_market": 0.5445,
            "per_step_nearest_neighbour_state_heavy_market": 0.5629,
        },
        "top_split_features": dict(usage.most_common(15)),
        "per_episode": per_episode,
    }
    args.output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    lines = ["# Majkel G1 market module", "",
             f"Decision tree over {len(names)} state features, "
             f"{len(vocabulary)} distinct market actions, "
             f"leave-one-episode-out over {len(episodes)} development episodes "
             f"({total:,} steps). Sealed G1 holdout not opened.", "",
             "| Model | Market-action accuracy |", "| --- | ---: |",
             f"| Majority class (empty action) | {majority[1] / len(all_labels):.4f} |",
             "| Block router, state_heavy | 0.5445 |",
             "| Per-step nearest neighbour, state_heavy | 0.5629 |",
             f"| **This module** | **{accuracy:.4f}** |", "",
             "## Most used split features", "",
             "| Feature | Splits |", "| --- | ---: |"]
    for name, count in usage.most_common(15):
        lines.append(f"| {name} | {count} |")
    args.report.write_text("\n".join(lines) + "\n")
    print(args.output)
    print(args.report)
    print(f"accuracy {accuracy:.4f}")


if __name__ == "__main__":
    main()
