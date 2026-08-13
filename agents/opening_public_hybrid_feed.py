"""Public mixed opening: survival feed before land, daily feed afterward."""

from runpy import run_path


common = run_path("agents/opening_compound_common.py")
agent = common["make_opening_agent"](feed_mode="hybrid")
