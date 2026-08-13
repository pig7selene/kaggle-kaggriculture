"""Routed replay economy capped at eight cows."""

from runpy import run_path


common = run_path("agents/router_replay_variant_common.py")
agent = common["make_variant"](
    animal_schedule=((0, 1), (5, 2), (6, 4), (7, 6), (8, 8)),
)

