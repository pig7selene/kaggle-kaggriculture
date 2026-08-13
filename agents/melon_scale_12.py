"""Twelve melon plots with two hired hands per day."""

from runpy import run_path

_make_agent = run_path("agents/melon_scale_common.py")["make_agent"]
_agent = _make_agent(12)


def agent(obs):
    return _agent(obs)
