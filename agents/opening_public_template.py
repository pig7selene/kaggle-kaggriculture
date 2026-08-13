"""Public 1-cow/4-sheep, 5-wheat/5-melon opening control."""

from runpy import run_path


common = run_path("agents/opening_compound_common.py")
agent = common["make_opening_agent"]()
