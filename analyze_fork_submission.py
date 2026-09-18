"""What a V43 fork does that the tape does not, step by step.

For each episode of a fork (a pulled submission, or a team in a daily dataset),
feed its recorded observations through shipped V43 to learn which route the
tape would have played, then compare the fork's actual actions with that tape:
farm actions by day and by unit (which crops it plants, what it builds and
places, when it buys land and how many hands it hires) and market orders by
item and hour. The result is the fork's edit list over V43, with its money and
the opponent's alongside, which is what we need to decide what to carry over.
"""
from __future__ import annotations
import argparse, gc, json, runpy, statistics, sys
from collections import Counter, defaultdict
from pathlib import Path
from analyze_v27_routes import normalized_action
from extract_lineage_frontier import field
from run_route_remap_pilot import load_agent

ROOT = Path(__file__).resolve().parent
SHIPPED = Path("/private/tmp/kaggriculture_v43_variants/shipped.py")
MOVES = {"NORTH", "SOUTH", "EAST", "WEST"}
route0_opening = runpy.run_path(str(SHIPPED), run_name="v43ship_open")["_ROUTES"][0]


def full_obs(rep, s, seat):
    o = dict(rep["steps"][s][seat]["observation"])
    for k in ("step", "day", "hour", "farms", "market", "town"):
        if k not in o:
            o[k] = rep["steps"][s][0]["observation"][k]
    return o


def route_for(rep, seat, tag, upto=200):
    agent = load_agent(SHIPPED, tag)
    for s in range(upto):
        try:
            agent(full_obs(rep, s, seat), rep.get("configuration"))
        except Exception:
            pass
    mod = sys.modules.get(agent.__module__) if hasattr(agent, "__module__") else None
    impl = getattr(mod, "_IMPL", None) if mod else None
    route = None
    try:
        route = impl.chassis.players[seat]["route"]
        tape = impl.chassis.routes[route]
    except Exception:
        tape = None
    for k in [k for k in sys.modules if k.startswith("remap_")]:
        sys.modules.pop(k, None)
    gc.collect()
    return route, tape


def units(a):
    return [a.get("farmer") or ["PASS"]] + list(a.get("hands") or [])


def mix(farm):
    crops, animals, kinds = Counter(), Counter(), Counter()
    for row in farm["tiles"]:
        for t in row:
            if isinstance(t, dict):
                kinds[t.get("kind")] += 1
                if t.get("kind") == "PLANT":
                    crops[t.get("crop")] += 1
                if t.get("animal"):
                    animals[t.get("animal")] += 1
            elif t is None:
                kinds["empty"] += 1
    return dict(crops), dict(animals), dict(kinds)


def analyze(rep, seat, tag):
    names = rep["info"]["TeamNames"]
    route, tape = route_for(rep, seat, tag)
    out = {"team": names[seat], "opp": names[1 - seat], "route": route,
           "money": rep["steps"][-1][seat]["reward"], "opp_money": rep["steps"][-1][1 - seat]["reward"],
           "town": rep["steps"][600][0]["observation"]["town"]["unlocked_shops"]}
    acts = [normalized_action(rep, seat, s) for s in range(719)]
    if tape is None:
        out["error"] = "no route"
        return out
    agree_day = defaultdict(lambda: [0, 0])
    first_div = None
    fork_ops, tape_ops = Counter(), Counter()
    plants_fork, plants_tape = Counter(), Counter()
    extra_unit_steps = Counter()
    land_fork, land_tape = [], []
    hires_fork, hires_tape = Counter(), Counter()
    sells_fork, sells_tape = Counter(), Counter()
    sell_hours_fork, sell_hours_tape = Counter(), Counter()
    for s in range(144, 719):
        a, t = acts[s], tape[s] if isinstance(tape[s], dict) else {}
        same = field(a) == field(t)
        agree_day[s // 24][0] += same
        agree_day[s // 24][1] += 1
        if not same and first_div is None:
            first_div = s
        ua, ut = units(a), units(t)
        for u in ua:
            if u:
                fork_ops[u[0]] += 1
                if u[0] == "PLANT" and len(u) > 1:
                    plants_fork[u[1]] += 1
        for u in ut:
            if u:
                tape_ops[u[0]] += 1
                if u[0] == "PLANT" and len(u) > 1:
                    plants_tape[u[1]] += 1
        if len(ua) > len(ut):
            extra_unit_steps[s // 24] += len(ua) - len(ut)
        for o in (a.get("market") or []):
            if not o:
                continue
            if o[0] == "BUY_LAND":
                land_fork.append(s)
            elif o[0] == "HIRE":
                hires_fork[s // 24] += 1
            elif o[0] == "SELL" and len(o) > 2 and int(o[2]) > 0:
                sells_fork[o[1]] += 1
                sell_hours_fork[(o[1], s % 24)] += 1
        for o in (t.get("market") or []):
            if not o:
                continue
            if o[0] == "BUY_LAND":
                land_tape.append(s)
            elif o[0] == "HIRE":
                hires_tape[s // 24] += 1
            elif o[0] == "SELL" and len(o) > 2 and int(o[2]) > 0:
                sells_tape[o[1]] += 1
                sell_hours_tape[(o[1], s % 24)] += 1
    opp_agree = sum(field(normalized_action(rep, 1 - seat, s)) == field(route0_opening[s]) for s in range(144)) / 144
    out["opp_agree"] = round(opp_agree, 3)
    out["opp_lineage"] = opp_agree >= 0.9
    farms500 = rep["steps"][500][0]["observation"]["farms"]
    farms700 = rep["steps"][700][0]["observation"]["farms"]
    out.update({
        "agree_by_day": {d: round(v[0] / v[1], 2) for d, v in sorted(agree_day.items())},
        "first_divergence": first_div,
        "fork_ops": dict(fork_ops), "tape_ops": dict(tape_ops),
        "plants_fork": dict(plants_fork), "plants_tape": dict(plants_tape),
        "extra_unit_steps_by_day": dict(extra_unit_steps),
        "land_fork": land_fork, "land_tape": land_tape,
        "hires_fork": dict(hires_fork), "hires_tape": dict(hires_tape),
        "sells_fork": dict(sells_fork), "sells_tape": dict(sells_tape),
        "sell_hours_fork": {f"{k[0]}@{k[1]}": v for k, v in sell_hours_fork.items()},
        "sell_hours_tape": {f"{k[0]}@{k[1]}": v for k, v in sell_hours_tape.items()},
        "mix500": mix(farms500[seat]), "opp_mix500": mix(farms500[1 - seat]),
        "mix700": mix(farms700[seat]), "quads500": len(farms500[seat]["unlocked_quadrants"]),
    })
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--submission", type=int, help="a pulled submission (manifest in experiments/)")
    ap.add_argument("--dir", type=Path, help="a daily dataset directory")
    ap.add_argument("--team", help="team name to analyze within --dir")
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--after", help="daily-dataset mode: only episodes created at or after this ISO time (UTC)")
    a = ap.parse_args()
    jobs = []
    if a.submission:
        man = json.loads((ROOT / "experiments" / f"online_{a.submission}_episodes_manifest.json").read_text())
        for e in man["episodes"][: a.limit]:
            jobs.append((Path(e["file"]), e["seat"]))
        label = str(a.submission)
    else:
        created = {}
        man = a.dir / "manifest.csv"
        if man.is_file():
            import csv
            for row in csv.DictReader(man.open()):
                created[row["episode_id"]] = row.get("create_time", "")
        for p in sorted(a.dir.glob("*.json")):
            if len(jobs) >= a.limit:
                break
            if a.after and created.get(p.stem, "") < a.after:
                continue
            try:
                names = json.loads(p.read_text())["info"]["TeamNames"]
            except Exception:
                continue
            if a.team in names:
                jobs.append((p, names.index(a.team)))
        label = a.team.replace(" ", "_")
    rows = []
    for i, (p, seat) in enumerate(jobs):
        rep = json.loads(p.read_text())
        r = analyze(rep, seat, f"fork:{label}:{i}")
        r["episode"] = p.stem
        rows.append(r)
        print(f"  {r['team'][:18]:18s} vs {r['opp'][:18]:18s} route {r['route']} money {r['money']:>9,.0f}/{r['opp_money']:>9,.0f} "
              f"first div {r.get('first_divergence')} land {r.get('land_fork')} plants {r.get('plants_fork')} quads {r.get('quads500')}", flush=True)
    out = a.out or (ROOT / "experiments" / f"fork_{label}_edits.json")
    out.write_text(json.dumps(rows, indent=0) + "\n")
    ok = [r for r in rows if "agree_by_day" in r]
    if not ok:
        return
    print(f"\n=== {label}: {len(ok)} episodes | money {statistics.mean(r['money'] for r in ok):,.0f} vs opp {statistics.mean(r['opp_money'] for r in ok):,.0f} ===")
    days = sorted({d for r in ok for d in r["agree_by_day"]})
    print("field agreement with the tape by day: " + " ".join(f"d{d}:{statistics.mean(r['agree_by_day'].get(d, 0) for r in ok):.2f}" for d in days))
    print("first divergence step: median", statistics.median(r["first_divergence"] or 719 for r in ok))
    def agg(key):
        c = Counter()
        for r in ok:
            c.update(r[key])
        return {k: round(v / len(ok), 1) for k, v in c.most_common()}
    print("unit ops per game  fork:", agg("fork_ops")); print("                   tape:", agg("tape_ops"))
    print("PLANT by crop      fork:", agg("plants_fork"), "| tape:", agg("plants_tape"))
    print("land buys fork:", Counter(s for r in ok for s in r["land_fork"]).most_common(6), "| tape:", Counter(s for r in ok for s in r["land_tape"]).most_common(4))
    print("hires/day fork:", {d: round(statistics.mean(r['hires_fork'].get(d, 0) for r in ok), 1) for d in range(6, 30)})
    print("hires/day tape:", {d: round(statistics.mean(r['hires_tape'].get(d, 0) for r in ok), 1) for d in range(6, 30)})
    print("SELL orders/game   fork:", agg("sells_fork")); print("                   tape:", agg("sells_tape"))
    print("crop mix @500 fork:", agg_mix := {k: round(statistics.mean(r['mix500'][0].get(k, 0) for r in ok), 1) for k in ("WHEAT", "STRAWBERRY", "TOMATO", "CARROT", "MELON")},
          "| animals:", {k: round(statistics.mean(r['mix500'][1].get(k, 0) for r in ok), 1) for k in ("COW", "SHEEP", "GOOSE")},
          "| quads:", statistics.mean(r["quads500"] for r in ok))


if __name__ == "__main__":
    main()
