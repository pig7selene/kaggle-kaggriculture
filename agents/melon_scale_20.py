"""Twenty melon plots with four hired hands per day."""

from runpy import run_path

_make_agent = run_path("agents/melon_scale_common.py")["make_agent"]
_agent = _make_agent(20)


def agent(obs):
    return _agent(obs)
