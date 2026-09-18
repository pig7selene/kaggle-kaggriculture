"""Task-level accounting of a fork's day against the tape's day.

Hands are dismissed at the end of every day and re-hired the next morning, so a
day's hand work is separable: only the farmer's position carries over. That
makes "what did the fork do with its hands today" a well-posed question. For
each day this lists the tasks the tape would perform (tile, op) and the tasks
the fork actually performed, the ones dropped and added, where the freed steps
went, and -- for animals -- the feeding calendar of both, which is what decides
whether feeding less is safe.
"""
from __future__ import annotations
import argparse, gc, json, sys
from collections import Counter, defaultdict
from pathlib import Path
from analyze_v27_routes import normalized_action
from run_route_remap_pilot import load_agent

ROOT = Path(__file__).resolve().parent
SHIPPED = Path("/private/tmp/kaggriculture_v43_variants/shipped.py")
MOVES = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}
WORK = {"WATER", "HARVEST", "PLANT", "FEED", "CARE", "COLLECT_FERTILIZER", "FERTILIZE", "DIG",
        "BUILD_COOP", "BUILD_PASTURE", "PICKUP", "PLACE", "DROP"}


def full_obs(rep, s, seat):
    o = dict(rep["steps"][s][seat]["observation"])
    for k in ("step", "day", "hour", "farms", "market", "town"):
        if k not in o:
            o[k] = rep["steps"][s][0]["observation"][k]
    return o


def tape_for(rep, seat, tag):
    agent = load_agent(SHIPPED, tag)
    for s in range(200):
        try:
            agent(full_obs(rep, s, seat), rep.get("configuration"))
        except Exception:
            pass
    mod = sys.modules.get(agent.__module__)
    impl = getattr(mod, "_IMPL", None)
    route = impl.chassis.players[seat]["route"]
    tape = impl.chassis.routes[route]
    for k in [k for k in sys.modules if k.startswith("remap_")]:
        sys.modules.pop(k, None)
    gc.collect()
    return route, tape


def tape_tasks(tape, day, start_positions, n_units):
    """Walk the tape's day from the same starting positions and record (unit, hour, pos, op)."""
    pos = [list(p) for p in start_positions]
    tasks = []
    for h in range(24):
        a = tape[day * 24 + h] if day * 24 + h < len(tape) else {}
        if not isinstance(a, dict):
            continue
        units = [a.get("farmer") or ["PASS"]] + list(a.get("hands") or [])
        for i in range(min(len(units), len(pos))):
            u = units[i]
            if not u:
                continue
            if u[0] in MOVES:
                d = MOVES[u[0]]
                nx, ny = pos[i][0] + d[0], pos[i][1] + d[1]
                if 0 <= nx < 10 and 0 <= ny < 10:
                    pos[i] = [nx, ny]
            elif u[0] in WORK:
                tasks.append((i, h, tuple(pos[i]), u[0], tuple(u[1:])))
    return tasks


def actual_tasks(rep, seat, day):
    tasks = []
    for h in range(24):
        s = day * 24 + h
        if s >= 719:
            break
        a = normalized_action(rep, seat, s)
        farm = rep["steps"][s][0]["observation"]["farms"][seat]
        pos = [farm["farmer"]] + list(farm["hands"])
        units = [a.get("farmer") or ["PASS"]] + list(a.get("hands") or [])
        for i in range(min(len(units), len(pos))):
            u = units[i]
            if u and u[0] in WORK:
                tasks.append((i, h, tuple(pos[i]), u[0], tuple(u[1:])))
    return tasks


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--replay", type=Path, required=True)
    ap.add_argument("--team", required=True)
    ap.add_argument("--days", default="12,16,20,24")
    a = ap.parse_args()
    rep = json.loads(a.replay.read_text())
    names = rep["info"]["TeamNames"]
    seat = names.index(a.team)
    route, tape = tape_for(rep, seat, "dp")
    print(f"{a.team} vs {names[1-seat]} | route {route} | money {rep['steps'][-1][seat]['reward']:,.0f} vs {rep['steps'][-1][1-seat]['reward']:,.0f}")

    # animal feeding calendar, both sides, from the board at hour 23
    print("\n=== animal feeding calendar (hour 23 fed_today; . = not fed) ===")
    cal = defaultdict(dict)
    for day in range(6, 30):
        s = min(day * 24 + 23, 718)
        farm = rep["steps"][s][0]["observation"]["farms"][seat]
        for y, row in enumerate(farm["tiles"]):
            for x, t in enumerate(row):
                if isinstance(t, dict) and t.get("animal"):
                    cal[(x, y, t["animal"])][day] = bool(t.get("fed_today"))
    for k in sorted(cal, key=lambda k: (k[2], k[1], k[0])):
        row = "".join("F" if cal[k].get(d) else ("." if d in cal[k] else " ") for d in range(6, 30))
        fed = sum(1 for d in cal[k] if cal[k][d])
        print(f"  {k[2]:6s} ({k[0]},{k[1]}): {row}  fed {fed}/{len(cal[k])}")

    # per-day task accounting
    for day in [int(d) for d in a.days.split(",")]:
        s0 = day * 24
        if s0 >= 719:
            continue
        farm0 = rep["steps"][s0][0]["observation"]["farms"][seat]
        start = [farm0["farmer"]] + list(farm0["hands"])
        tt = tape_tasks(tape, day, start, len(start))
        at = actual_tasks(rep, seat, day)
        tc = Counter((p, op, args) for _, _, p, op, args in tt)
        ac = Counter((p, op, args) for _, _, p, op, args in at)
        dropped = tc - ac
        added = ac - tc
        print(f"\n=== day {day}: tape {len(tt)} tasks, fork {len(at)} tasks ===")
        print(f"  ops tape: {dict(Counter(op for _,_,_,op,_ in tt).most_common())}")
        print(f"  ops fork: {dict(Counter(op for _,_,_,op,_ in at).most_common())}")
        print(f"  dropped ({sum(dropped.values())}): {dict(Counter(op for (_, op, _), n in dropped.items() for _ in range(n)).most_common())}")
        print(f"  added   ({sum(added.values())}): {dict(Counter(op for (_, op, _), n in added.items() for _ in range(n)).most_common())}")
        for label, c in (("dropped", dropped), ("added", added)):
            items = [f"{op}{list(args) if args else ''}@{p}" for (p, op, args), n in c.items() for _ in range(n)]
            if items:
                print(f"  {label} detail: {', '.join(items[:24])}{' ...' if len(items) > 24 else ''}")


if __name__ == "__main__":
    main()
