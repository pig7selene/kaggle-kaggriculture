"""Parameterized entry point used by the multi-wave research harness.

The harness loads this module with ``MULTIWAVE_CONFIG`` supplied through
``runpy.run_path``. It avoids one Python file per candidate while preserving
the exact same agent interface used by local games.
"""

from runpy import run_path


if "MULTIWAVE_CONFIG" not in globals():
    raise RuntimeError("MULTIWAVE_CONFIG is required")

agent = run_path("agents/multiwave_runtime.py")["make_agent"](MULTIWAVE_CONFIG)

