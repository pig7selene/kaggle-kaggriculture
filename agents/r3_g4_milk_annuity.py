"""THIS GUARD IS INTENDED TO FIX: six cows losing a $14k-$17k milk annuity.

Retain R3's six-cow crop-focused opening through the capital window, then add
two cows only when milk remains economically healthy and visible rival cow
supply is not already high.  This targets the paired melon/livestock-pressure
tail without reverting unconditionally to the fragile nine-cow branch.
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
    },
)
