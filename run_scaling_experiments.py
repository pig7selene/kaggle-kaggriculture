"""Run the controlled carrot farm-scale tournament.

Each candidate is compared to the current best on identical seeds and both
player positions. A candidate is promoted only when benchmark.py marks its
paired-seed improvement as reliable.
"""

import argparse
import json
from pathlib import Path

from benchmark import (
    CURRENT_BEST_REGISTRY,
    DEFAULT_WORKERS,
    EXPERIMENTS_DIR,
    ROOT,
    run_head_to_head,
)


SCALES = (4, 8, 12, 16, 20, 25)
INITIAL_BEST_PATH = ROOT / "agents" / "baseline_carrot.py"
INITIAL_BEST_VERSION = "baseline_carrot_v1"


def run_scaling_tournament(mode, workers):
    best_path = INITIAL_BEST_PATH
    best_version = INITIAL_BEST_VERSION
    comparisons = []

    for scale in SCALES:
        candidate_path = ROOT / "agents" / f"carrot_scale_{scale:02d}.py"
        candidate_version = f"carrot_scale_{scale:02d}_v1"
        result = run_head_to_head(
            agent_path=candidate_path,
            agent_version=candidate_version,
            best_agent_path=best_path,
            best_version=best_version,
            mode=mode,
            workers=workers,
        )
        promoted = result["summary"]["reliable_improvement"]
        comparisons.append(
            {
                "scale": scale,
                "hands_per_day": (scale + 3) // 4 - 1,
                "candidate_version": candidate_version,
                "compared_to": best_version,
                "summary": result["summary"],
                "promoted": promoted,
            }
        )
        if promoted:
            best_path = candidate_path
            best_version = candidate_version
            print(f"PROMOTED: {candidate_version}\n", flush=True)
        else:
            print(f"NOT PROMOTED: {candidate_version}\n", flush=True)

    tournament = {
        "schema_version": 1,
        "experiment": "carrot_farm_scale",
        "mode": mode,
        "promotion_rule": (
            "positive paired-seed average advantage with 95% CI above zero"
        ),
        "initial_best": INITIAL_BEST_VERSION,
        "comparisons": comparisons,
        "final_best_version": best_version,
        "final_best_path": str(best_path.relative_to(ROOT)),
    }
    output_path = EXPERIMENTS_DIR / f"scaling_summary_{mode}.json"
    output_path.write_text(json.dumps(tournament, indent=2) + "\n", encoding="utf-8")
    registry = {
        "agent_version": best_version,
        "agent_path": str(best_path.relative_to(ROOT)),
        "initial_best_version": INITIAL_BEST_VERSION,
        "selected_by": str(output_path.relative_to(ROOT)),
        "promotion_rule": tournament["promotion_rule"],
    }
    CURRENT_BEST_REGISTRY.write_text(
        json.dumps(registry, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Scaling summary saved: {output_path}")
    print(f"Current-best registry saved: {CURRENT_BEST_REGISTRY}")
    print(f"Final best: {best_version} ({best_path.relative_to(ROOT)})")
    return tournament


def _parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("quick", "full"), default="quick")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be at least 1")
    return args


def main():
    args = _parse_args()
    run_scaling_tournament(args.mode, args.workers)


if __name__ == "__main__":
    main()
