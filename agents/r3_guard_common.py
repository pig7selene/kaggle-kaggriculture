"""Narrow replay-grounded guards around the frozen R3 construction.

The factory does not mutate the frozen candidate.  Each opt-in guard maps to
one measured tail cluster and leaves the opening, land, router and crop
economy otherwise identical.
"""

from __future__ import annotations

from runpy import run_path


COMMON = run_path("agents/epic_candidate_common.py")
BASE = {"capital_yield_completion": True, "value_scheduler": True}


def make_guard(*, cows=6, config=None):
    merged = dict(BASE)
    merged.update(config or {})
    return COMMON["make_candidate"](
        cows=cows,
        phase="capital_window",
        config=merged,
    )
