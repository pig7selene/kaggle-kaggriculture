"""Old version versus new, for each strong fork.

Puts a fork's 9/16 edit list (from the daily dataset) beside its current
submission's (from the pulled episodes): unit-op deltas against the tape,
plantings by crop, sell orders by item, and money against the opponent. What
moved between the two versions is what the team changed this week.
"""
from __future__ import annotations
import json, statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAIRS = {"Driz Lo": ("Driz_Lo", "Driz_Lo_0917"), "Thomas Tschinkel": ("Thomas_Tschinkel", "Thomas_Tschinkel_0917"),
         "Catalyst": ("Catalyst", "Catalyst_0917"), "mikelou1": ("mikelou1", "mikelou1_0917")}
OPS = ("FERTILIZE", "FEED", "CARE", "WATER", "PASS", "HARVEST", "PLANT", "PICKUP", "DROP", "PLACE", "DIG")


def load(label):
    p = ROOT / "experiments" / f"fork_{label}_edits.json"
    if not p.is_file():
        return []
    return [r for r in json.loads(p.read_text()) if "fork_ops" in r]


def agg(rows, key):
    c = Counter()
    for r in rows:
        c.update(r[key])
    return {k: v / len(rows) for k, v in c.items()} if rows else {}


def summarize(rows):
    fo, to = agg(rows, "fork_ops"), agg(rows, "tape_ops")
    return {"n": len(rows),
            "money": statistics.mean(r["money"] for r in rows) if rows else None,
            "opp_money": statistics.mean(r["opp_money"] for r in rows) if rows else None,
            "margin": statistics.mean(r["money"] - r["opp_money"] for r in rows) if rows else None,
            "ops_delta": {k: fo.get(k, 0) - to.get(k, 0) for k in OPS},
            "plants": agg(rows, "plants_fork"), "plants_tape": agg(rows, "plants_tape"),
            "sells": agg(rows, "sells_fork"), "sells_tape": agg(rows, "sells_tape"),
            "land_extra": statistics.mean(len(r["land_fork"]) - len(r["land_tape"]) for r in rows) if rows else None,
            "quads": statistics.mean(r["quads500"] for r in rows) if rows else None}


def main() -> None:
    out = []
    for team, (old_label, new_label) in PAIRS.items():
        old, new = summarize(load(old_label)), summarize(load(new_label))
        out.append(f"\n## {team}: 9/16 (n={old['n']}) -> today (n={new['n']})")
        if old["n"] and new["n"]:
            out.append(f"money {old['money']:,.0f} -> {new['money']:,.0f} | margin vs opp {old['margin']:+,.0f} -> {new['margin']:+,.0f} | quads {old['quads']:.2f} -> {new['quads']:.2f} | extra land {old['land_extra']:.2f} -> {new['land_extra']:.2f}")
            out.append("| op delta vs tape | 9/16 | today | change |"); out.append("|---|---:|---:|---:|")
            for k in OPS:
                a, b = old["ops_delta"][k], new["ops_delta"][k]
                if abs(a) >= 3 or abs(b) >= 3:
                    out.append(f"| {k} | {a:+.0f} | {b:+.0f} | {b - a:+.0f} |")
            out.append("| PLANT by crop (fork / tape) | 9/16 | today |"); out.append("|---|---|---|")
            for c in ("WHEAT", "CARROT", "STRAWBERRY", "TOMATO", "MELON"):
                out.append(f"| {c} | {old['plants'].get(c, 0):.0f} / {old['plants_tape'].get(c, 0):.0f} | {new['plants'].get(c, 0):.0f} / {new['plants_tape'].get(c, 0):.0f} |")
            out.append("| SELL orders (fork / tape) | 9/16 | today |"); out.append("|---|---|---|")
            for it in ("WHEAT", "FERTILIZER", "WOOL", "MILK", "EGG", "STRAWBERRY", "CARROT"):
                out.append(f"| {it} | {old['sells'].get(it, 0):.0f} / {old['sells_tape'].get(it, 0):.0f} | {new['sells'].get(it, 0):.0f} / {new['sells_tape'].get(it, 0):.0f} |")
        else:
            out.append(f"(missing: old n={old['n']}, new n={new['n']})")
    text = "\n".join(out)
    (ROOT / "experiments" / "fork_versions_compare.md").write_text("# Strong forks: 9/16 version vs current submission\n" + text + "\n")
    print(text)


if __name__ == "__main__":
    main()
