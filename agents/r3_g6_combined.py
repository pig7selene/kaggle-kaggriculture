"""THIS GUARD IS INTENDED TO FIX: low-rival-milk and healthy-strawberry tails.

Combination of the two isolated, replay-grounded post-capital guards.  The
destructive-crop completion rule remains unchanged unless G2 proves useful.
"""

from runpy import run_path


agent = run_path("agents/r3_guard_common.py")["make_guard"](
    cows="adaptive8",
    config={
        "late_cow_start_day": 13,
        "late_cow_max_day": 15,
        "late_cow_min_milk_price": 200,
        "late_cow_max_opponent_cows": 6,
        "late_cow_bank_reserve": 2500,
        "late_strawberry_price_guard": True,
        "late_strawberry_min_price": 150,
    },
)
