"""B8 research finalist: six cows, action value, semantic collision guard."""

from runpy import run_path

common = run_path("agents/epic_candidate_common.py")
base = common["make_candidate"](cows=6, config={"value_scheduler": True})
agent = common["semantic_animal_guard"](base)
