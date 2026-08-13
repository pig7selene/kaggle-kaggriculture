"""Select diverse survivors and recombine multi-wave economic architectures."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from copy import deepcopy
from pathlib import Path

from run_multiwave_search import CONFIG_PATH, _add, _clean


ROOT = Path(__file__).resolve().parent


def _signature(config):
    opening = config["opening_extension_mix"]
    wave1 = config["wave1_mix"]
    wave2 = config["wave2_mix"]
    return (
        max(opening, key=opening.get),
        max(wave1, key=wave1.get),
        max(wave2, key=wave2.get),
        config["wave1_structure"], config["wave2_structure"],
        config["liquidation_mode"],
        config["wave1_start_day"], config["wave2_start_day"],
    )


def _pareto(rows):
    metrics = (
        "top_template_win_rate", "top_template_average_advantage",
        "worst_top_template_advantage", "direct_r3_average_advantage",
        "regression_average_advantage",
    )
    frontier = []
    for row in rows:
        dominated = False
        for other in rows:
            if other is row:
                continue
            if all(other[key] >= row[key] for key in metrics) and any(
                other[key] > row[key] for key in metrics
            ):
                dominated = True
                break
        if not dominated:
            frontier.append(row)
    return frontier


def select_generation1(result_path, count=20):
    results = json.loads(Path(result_path).read_text())
    registry = json.loads(CONFIG_PATH.read_text())
    source = registry["generation0"]
    ranked = results["candidates"]
    selected = []
    seen = set()

    def admit(candidate):
        if candidate not in seen and len(selected) < count:
            selected.append(candidate); seen.add(candidate)

    for row in _pareto(ranked):
        admit(row["candidate"])
    for row in ranked[: max(8, count // 2)]:
        admit(row["candidate"])
    by_signature = defaultdict(list)
    for row in ranked:
        by_signature[_signature(source[row["candidate"]]["config"])].append(row)
    for rows in by_signature.values():
        admit(rows[0]["candidate"])
    for row in ranked:
        admit(row["candidate"])

    configs = {candidate: source[candidate] for candidate in selected}
    registry["generation1"] = configs
    CONFIG_PATH.write_text(json.dumps(registry, indent=2) + "\n")
    manifest = {
        "schema_version": 1,
        "selection_rule": "Pareto frontier, top transfer score, then best representative per structural signature",
        "selected": selected,
        "pareto_front": [row["candidate"] for row in _pareto(ranked)],
    }
    path = ROOT / "experiments/multiwave_generation1_manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(path, len(configs))


def evolve_generation2(result_path, count=42):
    results = json.loads(Path(result_path).read_text())
    registry = json.loads(CONFIG_PATH.read_text())
    parents = registry["generation1"]
    ranked = results["candidates"]
    parent_rows = {row["candidate"]: row for row in ranked}
    configs = {}

    # Keep six structurally distinct parents as architecture controls.
    chosen = []
    signatures = set()
    for row in ranked:
        signature = _signature(parents[row["candidate"]]["config"])
        if signature not in signatures or len(chosen) < 3:
            chosen.append(row["candidate"]); signatures.add(signature)
        if len(chosen) >= 8:
            break
    for candidate in chosen:
        row = parents[candidate]
        _add(configs, row["config"], "g1_survivor", row["hypothesis"], (candidate,))

    top = [row["candidate"] for row in ranked[:8]]
    # Recombine best first-wave economics with best second-wave/close policies.
    for left_index, left in enumerate(top[:6]):
        for right in top[left_index + 1:left_index + 4]:
            a, b = parents[left]["config"], parents[right]["config"]
            cfg = deepcopy(a)
            for key in (
                "wave2_start_day", "wave2_mix", "wave2_structure",
                "wave3_start_day", "wave3_mix", "wave3_structure",
                "cash_reserve_wave2", "cash_reserve_wave3",
            ):
                cfg[key] = deepcopy(b[key])
            _add(configs, cfg, "recombined", "best first-wave parent plus best later-wave parent", (left, right))

    # Failure-driven mutations. Top replays show 11-12 opening melons only
    # when crop deployment begins above R3's ten-crop target; explicitly test
    # the capital/workload frontier rather than assuming that scale is free.
    for parent in top[:4]:
        base = parents[parent]["config"]
        for target in (14, 18):
            cfg = deepcopy(base)
            cfg["core_crop_targets"] = {"0": target, "1": target, "2": target}
            cfg["opening_extension_mix"] = {"MELON": .70, "WHEAT": .30}
            _add(configs, cfg, "larger_opening", f"test {target}-tile day-0 cohort and capital constraint", (parent,))
        cfg = deepcopy(base)
        cfg["wave1_structure"] = "quadrant"
        cfg["wave2_structure"] = "quadrant"
        _add(configs, cfg, "spatial_mutation", "increase crop/quadrant purity after observed fragmentation", (parent,))
        cfg = deepcopy(base)
        cfg["wave1_structure"] = "staggered"
        cfg["plant_admission"] = True
        _add(configs, cfg, "workload_mutation", "stagger first wave with workload admission", (parent,))
        cfg = deepcopy(base)
        cfg["cash_reserve_wave1"] = 0; cfg["cash_reserve_wave2"] = 0
        cfg["seed_reinvestment_fraction"] = 1.0; cfg["liquidation_mode"] = "immediate"
        _add(configs, cfg, "fast_reinvestment", "eliminate artificial cash idle time after liquidation", (parent,))

    # Cross the empirically strongest crop mixes independent of the scalar
    # winner, retaining synchronized and staggered hypotheses.
    best_first = max(ranked, key=lambda row: row["groups"]["top_diagnosis"]["average_money"])["candidate"]
    best_direct = max(ranked, key=lambda row: row["direct_r3_average_advantage"])["candidate"]
    for structure in ("synchronized", "staggered", "quadrant"):
        cfg = deepcopy(parents[best_first]["config"])
        cfg["wave2_mix"] = deepcopy(parents[best_direct]["config"]["wave2_mix"])
        cfg["wave1_structure"] = structure
        cfg["wave2_structure"] = structure
        _add(configs, cfg, "pareto_recombined", "top-template first wave plus direct-R3 later wave", (best_first, best_direct))

    # Fill deterministically with one-axis mutations of the best candidates.
    mutation_index = 0
    while len(configs) < count:
        parent = top[mutation_index % len(top)]
        cfg = deepcopy(parents[parent]["config"])
        axis = mutation_index % 6
        if axis == 0:
            cfg["wave1_start_day"] = max(9, min(11, cfg["wave1_start_day"] + (-1 if mutation_index % 2 else 1)))
        elif axis == 1:
            cfg["wave2_start_day"] = max(18, min(21, cfg["wave2_start_day"] + (-1 if mutation_index % 2 else 1)))
        elif axis == 2:
            cfg["productive_targets"]["10"] = max(55, min(68, cfg["productive_targets"]["10"] + (5 if mutation_index % 2 else -5)))
        elif axis == 3:
            cfg["wave1_mix"]["MELON"] = min(.55, cfg["wave1_mix"].get("MELON", 0) + .08)
        elif axis == 4:
            cfg["wave2_mix"]["STRAWBERRY"] = min(.85, cfg["wave2_mix"].get("STRAWBERRY", 0) + .10)
        else:
            cfg["wave3_start_day"] = max(22, min(25, cfg["wave3_start_day"] + (1 if mutation_index % 2 else -1)))
        _add(configs, cfg, "targeted_mutation", f"one-axis failure-driven mutation {axis}", (parent,))
        mutation_index += 1
        if mutation_index > count * 20:
            break

    registry["generation2"] = dict(list(configs.items())[:count])
    CONFIG_PATH.write_text(json.dumps(registry, indent=2) + "\n")
    manifest = {
        "schema_version": 1, "parents": top,
        "generation2_count": len(registry["generation2"]),
        "families": defaultdict(int),
    }
    family_counts = defaultdict(int)
    for row in registry["generation2"].values():
        family_counts[row["family"]] += 1
    manifest["families"] = dict(family_counts)
    path = ROOT / "experiments/multiwave_generation2_manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(path, len(registry["generation2"]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("select-g1", "evolve-g2"))
    parser.add_argument("results")
    parser.add_argument("--count", type=int)
    args = parser.parse_args()
    if args.mode == "select-g1":
        select_generation1(args.results, args.count or 20)
    else:
        evolve_generation2(args.results, args.count or 42)


if __name__ == "__main__":
    main()

