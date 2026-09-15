"""Map RNG seeds to the first two town shops they produce.

Any experiment conditioned on the first-two-shop pair -- and the route remap
is one -- needs seeds known to produce each pair. The shop draw is a function of
the seed alone (uniform with replacement, independent of play), so it can be
read once and cached. Two PASS agents are enough to get the town to step 150,
where both of the first two shops are unlocked.

The truncated episode length is validated against seeds whose pairs were seen in
full 720-step games earlier in this repository; a mismatch raises rather than
writing a manifest that would silently mis-seed every downstream run.

Named with 'manifest' so the existing !experiments/*manifest*.json rule keeps it
tracked.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path

from kaggle_environments import make


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "experiments" / "seed_first_shops_manifest.json"
STEPS = 720  # a 150-step episode draws different shops than a full one; validated below

# Seed -> first two shops as seen identically by six different agents across the
# 256-game public tournament of 2026-09-15 (experiments/public_agent_tournament.json).
# An earlier three-entry table carried a wrong value for seed 1 taken from a
# malfunctioning agent run; this table is the authoritative one.
KNOWN = {
    1: ('FARMERS_MARKET', 'PIZZA_SHOP'),
    2: ('YARN_STORE', 'BAKERY'),
    3: ('BAKERY', 'YARN_STORE'),
    4: ('ICE_CREAM_SHOP', 'BAKERY'),
    5: ('BAKERY', 'BRUNCH_SPOT'),
    6: ('PET_CAFE', 'SMOOTHIE_SHOP'),
    7: ('SMOOTHIE_SHOP', 'BAKERY'),
    8: ('BRUNCH_SPOT', 'PET_CAFE'),
    9: ('PIZZA_SHOP', 'BRUNCH_SPOT'),
    10: ('BRUNCH_SPOT', 'BAKERY'),
    11: ('PIZZA_SHOP', 'BAKERY'),
    12: ('BRUNCH_SPOT', 'BAKERY'),
    13: ('SMOOTHIE_SHOP', 'ICE_CREAM_SHOP'),
    14: ('SMOOTHIE_SHOP', 'BAKERY'),
    15: ('BAKERY', 'ICE_CREAM_SHOP'),
    16: ('PIZZA_SHOP', 'BRUNCH_SPOT'),
}


# The shop draw is NOT a pure function of the seed: two PASS agents draw
# different shops than real agents on the same seed, presumably because the town
# RNG shares state with play-dependent events. The scan therefore plays the same
# baseline the remap experiments use in both seats. Every forced-route variant is
# byte-identical to this baseline through step 143, and the first two shops are
# drawn by step 144, so the pair observed here is the pair those runs will see.
BASELINE = Path("/private/tmp/kaggriculture_v43_variants/room_plus_clamp.py")


def load_baseline(tag: str):
    import hashlib, importlib.util, sys, time
    name = "seedscan_" + hashlib.sha256(f"{tag}:{time.time_ns()}".encode()).hexdigest()[:20]
    spec = importlib.util.spec_from_file_location(name, BASELINE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {BASELINE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return getattr(module, "agent", None) or getattr(module, "kaggle_agent")


def shops_for(seed: int) -> tuple[int, list[str]]:
    env = make("kaggriculture", configuration={"episodeSteps": STEPS, "seed": seed}, debug=False)
    env.run([load_baseline(f"a{seed}"), load_baseline(f"b{seed}")])
    town = env.steps[-1][0].observation["town"]
    return seed, list(town.get("unlocked_shops", []))[:2]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=500)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    by_seed: dict[int, list[str]] = {}
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(shops_for, s) for s in range(1, args.seeds + 1)]
        for done, future in enumerate(as_completed(futures), 1):
            seed, shops = future.result()
            by_seed[seed] = shops
            if done % 100 == 0:
                print(f"  {done}/{args.seeds}", flush=True)

    for seed, expected in KNOWN.items():
        got = tuple(by_seed.get(seed, []))
        if got != expected:
            raise RuntimeError(
                f"seed {seed}: truncated run gives {got}, full game gave {expected}; "
                f"episodeSteps={STEPS} is not a faithful shop scan"
            )

    by_pair: dict[str, list[int]] = defaultdict(list)
    for seed in sorted(by_seed):
        if len(by_seed[seed]) == 2:
            by_pair[" + ".join(by_seed[seed])].append(seed)

    data = {
        "schema_version": 1,
        "purpose": "seed -> first two unlocked shops, for shop-pair-conditioned experiments",
        "episode_steps_used": STEPS,
        "seeds_scanned": args.seeds,
        "validated_against_full_games": {str(k): list(v) for k, v in KNOWN.items()},
        "pairs_observed": len(by_pair),
        "min_seeds_per_observed_pair": min(len(v) for v in by_pair.values()),
        "by_pair": dict(sorted(by_pair.items())),
        "by_seed": {str(k): v for k, v in sorted(by_seed.items())},
    }
    args.output.write_text(json.dumps(data, indent=2) + "\n")
    print(args.output)
    print(f"pairs observed {len(by_pair)}/64, min seeds per pair "
          f"{data['min_seeds_per_observed_pair']}, validation passed")


if __name__ == "__main__":
    main()
