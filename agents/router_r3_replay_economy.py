"""R3: scalable territory router with the frozen replay-inspired economy."""

from runpy import run_path


base = run_path("agents/replay_meta_full_schedule.py")["agent"]
router = run_path("agents/large_scale_router.py")
agent = router["make_routed_agent"](base)

