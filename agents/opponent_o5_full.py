"""O5: full conservative opponent-aware layer around the frozen routed best."""

from runpy import run_path


common = run_path("agents/opponent_aware_common.py")
agent = common["make_agent"](crop=True, selling=True, reinvestment=True)

