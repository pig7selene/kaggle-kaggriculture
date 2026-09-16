"""Decompose a team's post-144 behaviour by day: money, field verbs, market orders.

Frontier teams on our lineage (アルモンド, redblackbst) run V43's opening tape
byte-for-byte and then a state-dependent policy that is worth ~300 points online.
The tapes cannot be transplanted (two transplants failed the same way), so the
next question is *where* in the game and in *which* action class the policy
differs from V43. This reads Kaggle replays for a team (and its opponents) or
local self-play replays of a V43 variant, and prints per-day means so the two
can be laid side by side.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import statistics

from analyze_v27_routes import normalized_action

ROOT = Path(__file__).resolve().parent
DAY = 72
PRODUCTS = ("CARROT", "EGG", "FERTILIZER", "MELON", "MILK", "STRAWBERRY", "TOMATO", "WHEAT", "WOOL")


def verb(x) -> str:
    if isinstance(x, (list, tuple)) and x:
        return str(x[0])
    if x in (None, "PASS", [], ""):
        return "PASS"
    if isinstance(x, dict):
        return str(x.get("action") or x.get("type") or "DICT")
    return str(x)[:12]


def plant_item(x) -> str | None:
    if isinstance(x, (list, tuple)) and x and str(x[0]) == "PLANT":
        strs = [e for e in x[1:] if isinstance(e, str)]
        return strs[-1] if strs else None
    return None


def profile(replay: dict, seat: int) -> dict:
    steps = replay["steps"]
    days = {}
    for d in range(1, 11):
        lo, hi = DAY * (d - 1), min(DAY * d, 719)
        verbs, plants, mk = Counter(), Counter(), Counter()
        for s in range(lo, hi):
            a = normalized_action(replay, seat, s)
            verbs["F:" + verb(a.get("farmer"))] += 1
            for h in a.get("hands") or []:
                verbs["H:" + verb(h)] += 1
                if (it := plant_item(h)):
                    plants[it] += 1
            if (it := plant_item(a.get("farmer"))):
                plants[it] += 1
            orders = a.get("market") or []
            if orders:
                mk["steps_with_market"] += 1
            dump_items = set()
            for o in orders:
                if not o:
                    continue
                mk[f"{o[0]}_orders"] += 1
                if o[0] == "SELL" and len(o) > 2:
                    qty = int(o[2])
                    mk["sell_items:" + str(o[1])] += 1
                    if qty >= 1000:
                        # "sell whatever is in the shed": the fill is capped by the shed
                        mk["dump_orders"] += 1
                        dump_items.add(o[1])
                    else:
                        mk["small_sell_orders"] += 1
                        mk["small_sell_qty"] += qty
            if len(dump_items) >= 5:
                mk["dump_all_steps"] += 1
        # shed occupancy: products only (animals share the dict), mean over the day,
        # at the day's last step, and after the end-of-day drop (first step of next day)
        occ = []
        for s in range(lo, hi):
            shed_s = steps[s][seat]["observation"].get("private", {}).get("shed", {}) or {}
            occ.append(sum(int(v) for k, v in shed_s.items() if k in PRODUCTS))
        nxt = steps[min(hi, len(steps) - 1)][seat]["observation"].get("private", {}).get("shed", {}) or {}
        mk["shed_mean"] = statistics.mean(occ) if occ else 0
        mk["shed_last_step"] = occ[-1] if occ else 0
        mk["shed_after_eod"] = sum(int(v) for k, v in nxt.items() if k in PRODUCTS)
        # money lives in the per-seat farm record; `reward` is only written at the end
        end = min(DAY * d, len(steps) - 1)
        farm = steps[end][seat]["observation"].get("farms", [{}] * 2)
        money = farm[seat].get("money") if isinstance(farm, list) and len(farm) > seat else None
        if money is None:
            money = steps[end][seat]["reward"] or 0
        days[d] = {"money": float(money), "verbs": verbs, "plants": plants, "market": mk}
    return days


def mean_table(profiles: list[dict]) -> dict:
    out = {}
    for d in range(1, 11):
        money = [p[d]["money"] for p in profiles]
        prev = [p[d - 1]["money"] for p in profiles] if d > 1 else [0.0] * len(profiles)
        keys = defaultdict(list)
        for p in profiles:
            for section in ("verbs", "plants", "market"):
                for k, v in p[d][section].items():
                    keys[(section, k)].append(v)
        row = {"money": statistics.mean(money), "income": statistics.mean(m - q for m, q in zip(money, prev))}
        for (section, k), vals in keys.items():
            row[f"{section}.{k}"] = sum(vals) / len(profiles)
        out[d] = row
    return out


def render(name: str, table: dict, n: int, keys: list[str]) -> str:
    lines = [f"## {name} (n={n})", "", "| day | " + " | ".join(keys) + " |", "|" + "---:|" * (len(keys) + 1)]
    for d in range(1, 11):
        row = table[d]
        lines.append(f"| {d} | " + " | ".join(f"{row.get(k, 0):,.1f}" for k in keys) + " |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--team")
    parser.add_argument("--local-dir", type=Path, help="self-play env.toJSON() replays; both seats used")
    parser.add_argument("--name", default=None)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    groups: dict[str, list[dict]] = defaultdict(list)
    if args.manifest:
        manifest = json.loads(args.manifest.read_text())
        for row in manifest["episodes"]:
            if args.team and row.get("team") != args.team:
                continue
            replay = json.loads(Path(row["path"]).read_text())
            teams = list(replay["info"]["TeamNames"])
            seat = teams.index(args.team) if args.team in teams else int(row["seat"])
            groups[args.name or args.team].append(profile(replay, seat))
            groups[(args.name or args.team) + "_opponents"].append(profile(replay, 1 - seat))
    if args.local_dir:
        for path in sorted(args.local_dir.glob("*.json")):
            replay = json.loads(path.read_text())
            for seat in (0, 1):
                groups[args.name or args.local_dir.name].append(profile(replay, seat))

    keys = ["money", "income", "verbs.F:PASS", "verbs.H:PASS", "verbs.H:HARVEST", "verbs.H:PLANT",
            "verbs.H:WATER", "verbs.H:FERTILIZE", "verbs.H:CARE", "verbs.H:FEED",
            "market.steps_with_market", "market.SELL_orders", "market.small_sell_orders",
            "market.small_sell_qty", "market.dump_orders", "market.dump_all_steps",
            "market.BUY_SEED_orders", "market.BUY_PRODUCT_orders", "market.HIRE_orders",
            "market.shed_mean", "market.shed_last_step", "market.shed_after_eod"]
    # add any verb not in the fixed list
    seen = set()
    for profiles in groups.values():
        for p in profiles:
            for d in p.values():
                seen.update("verbs." + k for k in d["verbs"])
                seen.update("plants." + k for k in d["plants"])
    extra = sorted(k for k in seen if k not in keys)
    report = []
    for name, profiles in groups.items():
        table = mean_table(profiles)
        report.append(render(name, table, len(profiles), keys))
        report.append(render(name + " (other verbs / plants)", table, len(profiles), extra))
        report.append("")
    text = "\n".join(report)
    print(text)
    if args.out:
        args.out.write_text(text + "\n")


if __name__ == "__main__":
    main()
