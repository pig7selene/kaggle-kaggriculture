"""Promoted V2 research best: JALKARNA complete elite route + frozen K3 repair."""

from runpy import run_path


agent = run_path("agents/super_replay_v2/backbone_common.py")["make_agent"](
    "super_raw_55463387"
)
