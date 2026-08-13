"""A: frozen C2 shadow using the isolated land experiment engine."""

from runpy import run_path

namespace = run_path("agents/animal_land_common.py")
config = dict(namespace["C2_LAND_BASE"])
agent = namespace["make_agent"](config)
