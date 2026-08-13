"""THIS GUARD IS INTENDED TO FIX: R3's six-cow milk-annuity paired tail.

After the day-20 melon capital cohort is safely converted, add two cows only
when milk remains scarce, rival cow supply is light, and cash can cover both
animals plus a feed/seed reserve.  The late gate avoids the natural-RNG damage
seen when G4 diverted day-13 capital from the proven crop wave.
"""

from runpy import run_path


agent = run_path("agents/r3_guard_common.py")["make_guard"](
    cows="adaptive8",
    config={
        "late_cow_start_day": 21,
        "late_cow_max_day": 21,
        "late_cow_min_milk_price": 220,
        "late_cow_max_opponent_cows": 4,
        "late_cow_bank_reserve": 8000,
    },
)
