"""O3: frozen routed best plus relative-state reinvestment only."""

from runpy import run_path


common = run_path("agents/opponent_aware_common.py")
agent = common["make_agent"](reinvestment=True)

