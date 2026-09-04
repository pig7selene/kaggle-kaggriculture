"""S3: S2 plus safe same-worker harvest -> replant chaining."""

from runpy import run_path

agent = run_path("agents/territory_lifecycle_common.py")["make_agent"]("S3")

