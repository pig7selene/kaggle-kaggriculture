"""B6 control: six cows with otherwise frozen lifecycle architecture."""

from runpy import run_path

agent = run_path("agents/epic_candidate_common.py")["make_candidate"](cows=6)
