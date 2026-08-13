"""Six-cow value scheduler plus Pedro's isolated wheat market mechanism."""

from runpy import run_path

common = run_path("agents/epic_candidate_common.py")
base = common["make_candidate"](cows=6, config={"value_scheduler": True})
agent = common["semantic_animal_guard"](
    common["oscillating_wheat_market_maker"](base)
)
