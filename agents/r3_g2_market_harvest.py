"""THIS GUARD IS INTENDED TO FIX: melon liquidation after visible rival supply.

Permit peak-day harvest without the final bonus only when the rival already
holds a large mature melon wave and the current quote is still near base.
This is the narrow market-collision hypothesis from Amer/Ayuma/Prashant.
"""

from runpy import run_path


agent = run_path("agents/r3_guard_common.py")["make_guard"](
    config={
        "capital_early_harvest": True,
        "capital_early_harvest_opponent_supply": 30,
        "capital_early_harvest_min_price": 235,
    }
)
