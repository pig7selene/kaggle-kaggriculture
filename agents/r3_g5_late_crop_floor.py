"""THIS GUARD IS INTENDED TO FIX: top-template crop throughput after day 20.

Keep strawberries while their live quote remains high enough to dominate the
short wheat close; retain R3's day-20 wheat conversion under severe strawberry
glut.  Filip is the motivating failure, with an $18 strawberry quote by day 24.
"""

from runpy import run_path


agent = run_path("agents/r3_guard_common.py")["make_guard"](
    config={"late_strawberry_price_guard": True, "late_strawberry_min_price": 150},
)
