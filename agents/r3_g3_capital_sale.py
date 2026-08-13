"""THIS GUARD IS INTENDED TO FIX: a harvested cohort missing day-10 reinvestment.

This is a no-op control because R3 already drops opening melons immediately
and the economic layer sells shed inventory at the next observation.  The
regret audit found no delayed shed liquidation before either required deed.
"""

from runpy import run_path


agent = run_path("agents/r3_guard_common.py")["make_guard"]()
