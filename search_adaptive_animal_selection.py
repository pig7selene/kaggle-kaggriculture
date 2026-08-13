"""Search adaptive animal selection without re-running the full policy grid."""

import argparse
import json

from benchmark import DEFAULT_WORKERS, ROOT
from search_animal_parameters import _evaluate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-start", type=int, default=8610)
    parser.add_argument("--seeds", type=int, default=4)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--stem", default="adaptive_animal_selection_search")
    args = parser.parse_args()

    source = json.loads(
        (ROOT / "experiments" / "animal_parameter_search.json").read_text(
            encoding="utf-8"
        )
    )
    best = dict(source["overall_best"]["config"])
    best["require_animal_payback"] = True
    variants = {"fixed_cow_tuned": dict(best)}
    for count in (2, 4):
        for start_day in (0, 11, 12, 13):
            for impact in (1.0, 4.0, 8.0):
                config = dict(best)
                config.update(
                    {
                        "animal_type": "ADAPTIVE",
                        "animal_count": count,
                        "animal_start_day": start_day,
                        "animal_opponent_impact_weight": impact,
                        "animal_workers": 1 if count <= 2 else 2,
                    }
                )
                variants[f"adaptive_n{count}_d{start_day}_impact{impact:g}"] = config
    seeds = list(range(args.seed_start, args.seed_start + args.seeds))
    stage = _evaluate(variants, seeds, args.workers, "adaptive_animal_selection")
    result = {
        "schema_version": 1,
        "seeds": seeds,
        "positions": [0, 1],
        "stage": stage,
        "best": stage["variants"][0],
    }
    path = ROOT / "experiments" / f"{args.stem}.json"
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for row in stage["variants"][:10]:
        overall = row["overall"]
        livestock = row["matchups"]["proxy_livestock_crop"]
        print(
            f"{row['variant']}: win={overall['win_rate'] * 100:.1f}% "
            f"money={overall['average_money']:.0f} adv={overall['average_advantage']:+.0f} "
            f"p10={overall['p10_advantage']:+.0f} livestock={livestock['average_advantage']:+.0f}"
        )
    print(f"Saved {path}")


if __name__ == "__main__":
    main()
