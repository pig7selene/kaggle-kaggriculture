"""B0 isolated control: frozen lifecycle behavior through the epic copies."""

from runpy import run_path

agent = run_path("agents/epic_candidate_common.py")["make_candidate"]()
