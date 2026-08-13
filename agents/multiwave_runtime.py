"""Runtime loader for deterministic multi-wave candidate configurations."""

from __future__ import annotations

from runpy import run_path


COMMON = run_path("agents/epic_candidate_common.py")


def make_agent(config):
    agent = COMMON["make_multiwave_candidate"](config)
    agent.multiwave_config = config
    return agent

