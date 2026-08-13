"""THIS GUARD IS INTENDED TO FIX: a low-milk-supply six-cow annuity shortfall.

Buy one (not two) extra cow in the existing day-13 window only when milk is
healthy and visible rival cow supply is light.  This is the smallest hedge
between frozen R3 and the volatile G4 two-cow recovery.
"""

from runpy import run_path


agent = run_path("agents/r3_guard_common.py")["make_guard"](
    cows="adaptive7",
    config={
        "late_cow_start_day": 13,
        "late_cow_max_day": 15,
        "late_cow_min_milk_price": 220,
        "late_cow_max_opponent_cows": 4,
        "late_cow_bank_reserve": 4000,
    },
)
