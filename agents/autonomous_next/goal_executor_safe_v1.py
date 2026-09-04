"""Safety-gated control for the goal executor prototype.

The crop executor is disabled in any state containing livestock.  This is an
intentional ablation: it measures whether the proposed architecture has any
value before we invest in a complete animal-service planner.
"""

from runpy import run_path


agent = run_path("agents/autonomous_next/goal_executor_v1.py")["make_agent"](
    switch_step=240, safe_mode=True
)
