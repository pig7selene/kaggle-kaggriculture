"""R1: scalable territory router with the frozen C8 economic policy."""

from runpy import run_path


base = run_path("agents/animal_c8_day12_land_day11.py")["agent"]
router = run_path("agents/large_scale_router.py")
agent = router["make_routed_agent"](base)

