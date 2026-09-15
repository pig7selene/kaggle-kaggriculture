"""Find what separates our losing online games from our winning ones.

The production profile showed we match the frontier on scale (75 vs 74 peak
productive tiles, 11 vs 11 peak hands) and are close on mean margin (+6,835 vs
+7,674), but our margin distribution is far wider: our tenth percentile is a
3,319 loss where Majkel's is a 654 win, and our worst game is -8,176 against his
-3,235. Since Gaussian Skill Rating moves on wins and not on margin size, that
left tail is where the rating gap lives.

This script asks what the left tail has in common, using the 136 official
episodes of submission 56183575 that we already hold. Nothing is downloaded and
no sealed material is touched.

Measured per episode, for both seats:

- every SELL order, with the pre-trade price and market inventory at that step
- realised price as a fraction of the step-0 price, which is the base price
  because every resource starts at the equilibrium inventory I0 = 10000
- units sold into a distressed market (under a quarter of base), which is what
  the premium-goods crash to the $1 floor looks like from the seller's side
- how much of our selling was concurrent with the opponent selling the same
  resource, since market inventory is global and both seats push the same price
- the step from which we fell behind on money and never recovered

The pre-trade price is a proxy: the engine fills a multi-unit order as the price
moves, so realised revenue differs. It is the right proxy anyway, because it is
what the agent could see when it decided to sell.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parent
CORPUS = Path("/private/tmp/kaggriculture_v233h_online")
OUTPUT = ROOT / "experiments" / "loss_mode_analysis.json"
REPORT = ROOT / "experiments" / "loss_mode_analysis.md"
TEAM = "pig7selene"
DISTRESS = 0.25   # fraction of base price below which a sale is distressed
PREMIUM = ("STRAWBERRY", "MELON", "MILK", "WOOL")


def sells(step_entry) -> list[tuple[str, int]]:
    """Filled units, not ordered units.

    The terminal liquidation layer submits speculative SELL orders of a fixed
    size -- 1000 units at a time over steps 713-718 -- whatever the shed
    actually holds, and the shed is usually empty by then. Order quantity is
    therefore a tape constant, not a measurement: read naively it reports an
    identical 6,188-unit wool 'volume' in every game and a gross of over a
    million, when the real filled volume is around 32 units. The engine fills a
    sell out of the shed, so the fill is capped by the holding going into the
    step, and repeated orders on one resource draw down the same pool.
    """
    action = step_entry.get("action") or {}
    shed = dict((step_entry.get("observation") or {}).get("private", {}).get("shed", {}) or {})
    out = []
    for order in action.get("market") or []:
        if order and order[0] == "SELL" and len(order) >= 3:
            resource = str(order[1])
            available = int(shed.get(resource, 0))
            filled = min(int(order[2]), available)
            if filled > 0:
                shed[resource] = available - filled
                out.append((resource, filled))
    return out


def order_similarity(steps, seat: int, other: int) -> float:
    """Jaccard overlap of the (step, resource) sets each seat sold on.

    An identity signal rather than an economic one, and the right one for
    lineage: two agents running the same tape submit the same orders at the
    same steps, liquidation no-ops included. Filled volume cannot serve here,
    because the fills are a few dozen units and carry almost no information.
    """
    def order_set(s):
        return {(index, str(o[1]))
                for index, entry in enumerate(steps)
                for o in ((entry[s].get("action") or {}).get("market") or [])
                if o and o[0] == "SELL" and len(o) > 1}

    ours, theirs = order_set(seat), order_set(other)
    union = ours | theirs
    return len(ours & theirs) / len(union) if union else 0.0


def episode(path: Path, team: str) -> dict | None:
    replay = json.loads(path.read_text())
    teams = list(replay["info"]["TeamNames"])
    if team not in teams or teams[0] == teams[1]:
        return None
    seat, other = teams.index(team), 1 - teams.index(team)
    steps = replay["steps"]
    base = dict(steps[0][seat]["observation"]["market"]["prices"])

    def blank() -> dict:
        return {"units": 0, "gross": 0.0, "distressed_units": 0, "first": None, "last": None}

    stats: dict[int, dict[str, dict]] = {s: defaultdict(blank) for s in (seat, other)}
    sold_at_step = {seat: defaultdict(set), other: defaultdict(set)}

    for index, entry in enumerate(steps):
        prices = entry[seat]["observation"]["market"]["prices"]
        for s in (seat, other):
            for resource, qty in sells(entry[s]):
                price = float(prices.get(resource, 0))
                row = stats[s][resource]
                row["units"] += qty
                row["gross"] += price * qty
                if base.get(resource) and price < DISTRESS * base[resource]:
                    row["distressed_units"] += qty
                row["first"] = index if row["first"] is None else row["first"]
                row["last"] = index
                sold_at_step[s][resource].add(index)

    # Concurrency: our sale steps where the opponent also sold the same resource
    # within the same hour, on the shared market.
    concurrent = 0
    own_total = 0
    for resource, our_steps in sold_at_step[seat].items():
        their = sold_at_step[other].get(resource, set())
        own_total += len(our_steps)
        concurrent += len(our_steps & their)

    # Money divergence: last step from which we trail for the rest of the game.
    behind_from = None
    for index in range(len(steps) - 1, -1, -1):
        farms = steps[index][seat]["observation"]["farms"]
        if float(farms[seat]["money"]) >= float(farms[other]["money"]):
            behind_from = index + 1 if index + 1 < len(steps) else None
            break
    else:
        behind_from = 0

    own = float(steps[-1][seat]["reward"])
    opp = float(steps[-1][other]["reward"])

    def pack(s):
        out = {}
        for resource, row in stats[s].items():
            if not row["units"]:
                continue
            out[resource] = {
                "units": row["units"],
                "gross": row["gross"],
                "avg_price": row["gross"] / row["units"],
                "avg_price_vs_base": (
                    (row["gross"] / row["units"]) / base[resource] if base.get(resource) else None
                ),
                "distressed_units": row["distressed_units"],
                "distressed_share": row["distressed_units"] / row["units"],
                "first_sale_step": row["first"],
                "last_sale_step": row["last"],
            }
        return out

    return {
        "episode_id": int(replay["info"].get("EpisodeId") or path.stem.split("-")[1]),
        "opponent": teams[other],
        "seat": seat,
        "shops": list(steps[-1][seat]["observation"]["town"]["unlocked_shops"])[:2],
        "own_money": own,
        "opponent_money": opp,
        "margin": own - opp,
        "outcome": "win" if own > opp else "loss" if own < opp else "tie",
        "behind_from_step": behind_from,
        "concurrent_sale_steps": concurrent,
        "own_sale_steps": own_total,
        "concurrency_share": concurrent / own_total if own_total else None,
        "order_similarity": order_similarity(steps, seat, other),
        "ours": pack(seat),
        "theirs": pack(other),
    }


def mirror_fingerprint(rows: list[dict], thresholds=(0.5, 0.6, 0.7)) -> dict:
    """Split games by how closely the opponent's sell-order pattern tracks ours.

    CASE D concluded that 99% of official opponents have unknown lineage, which
    was true of the *names*: every opponent in this corpus is a distinct person
    playing one or two games. By order pattern the ladder is far more
    homogeneous. Reported at several thresholds rather than one, because the
    split is only as good as the cut and the reader should see whether a
    difference survives moving it.
    """
    values = sorted(row["order_similarity"] for row in rows)
    total_losses = max(1, sum(1 for row in rows if row["outcome"] == "loss"))
    out = {
        "metric": "jaccard overlap of the (step, resource) sets each seat sold on",
        "distribution": {
            "min": values[0], "p25": statistics.quantiles(values, n=4)[0],
            "median": statistics.median(values),
            "p75": statistics.quantiles(values, n=4)[2], "max": values[-1],
        },
        "splits": {},
    }
    for threshold in thresholds:
        parts = {"mirror": [r for r in rows if r["order_similarity"] >= threshold],
                 "non_mirror": [r for r in rows if r["order_similarity"] < threshold]}
        entry = {}
        for name, subset in parts.items():
            if not subset:
                continue
            tally = Counter(r["outcome"] for r in subset)
            entry[name] = {
                "episodes": len(subset),
                "wins": tally["win"], "losses": tally["loss"], "ties": tally["tie"],
                "gsr": (tally["win"] + 0.5 * tally["tie"]) / len(subset),
                "median_margin": statistics.median(r["margin"] for r in subset),
            }
        entry["mirror_share_of_losses"] = (
            sum(1 for r in parts["mirror"] if r["outcome"] == "loss") / total_losses
        )
        out["splits"][str(threshold)] = entry
    return out


def group(rows, name):
    def agg(field, resource=None):
        vals = []
        for row in rows:
            if resource:
                cell = row["ours"].get(resource)
                if cell and cell[field] is not None:
                    vals.append(cell[field])
            elif row[field] is not None:
                vals.append(row[field])
        return statistics.median(vals) if vals else None

    out = {
        "group": name,
        "episodes": len(rows),
        "median_margin": statistics.median(r["margin"] for r in rows),
        "median_behind_from_step": agg("behind_from_step"),
        "median_concurrency_share": agg("concurrency_share"),
        "by_resource": {},
    }
    for resource in PREMIUM + ("WHEAT", "CARROT", "EGG", "TOMATO"):
        present = [r for r in rows if resource in r["ours"]]
        if not present:
            continue
        out["by_resource"][resource] = {
            "episodes_selling": len(present),
            "median_units": agg("units", resource),
            "median_avg_price_vs_base": agg("avg_price_vs_base", resource),
            "median_distressed_share": agg("distressed_share", resource),
            "median_gross": agg("gross", resource),
        }
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=CORPUS)
    parser.add_argument("--team", default=TEAM)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()

    paths = sorted(args.corpus.glob("episode-*-replay.json"))
    rows = []
    for index, path in enumerate(paths, 1):
        row = episode(path, args.team)
        if row:
            rows.append(row)
        if index % 20 == 0 or index == len(paths):
            print(f"  {index}/{len(paths)}", flush=True)
    rows.sort(key=lambda r: r["margin"])

    losses = [r for r in rows if r["outcome"] == "loss"]
    wins = [r for r in rows if r["outcome"] == "win"]
    tail = rows[: max(1, len(rows) // 10)]          # worst decile by margin
    best = rows[-max(1, len(rows) // 10):]          # best decile

    groups = [group(losses, "losses"), group(tail, "worst decile"),
              group(wins, "wins"), group(best, "best decile")]
    data = {
        "schema_version": 1,
        "corpus": str(args.corpus),
        "submission_id": 56183575,
        "episodes": len(rows),
        "distress_threshold_fraction_of_base": DISTRESS,
        "groups": groups,
        "mirror_fingerprint": mirror_fingerprint(rows),
        "worst_games": [
            {k: r[k] for k in ("episode_id", "opponent", "seat", "shops", "margin",
                               "behind_from_step", "concurrency_share")}
            for r in tail
        ],
        "loss_opponents": dict(Counter(r["opponent"] for r in losses).most_common()),
        "loss_shop_pairs": dict(
            Counter(" + ".join(r["shops"]) for r in losses).most_common()
        ),
        "games": rows,
    }
    args.output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    lines = ["# Loss-mode analysis, submission 56183575", "",
             f"{len(rows)} official episodes. {len(wins)} wins, {len(losses)} losses. "
             f"A sale is 'distressed' below {DISTRESS:.0%} of the step-0 base price.", "",
             "| Metric | " + " | ".join(g["group"] for g in groups) + " |",
             "| --- | " + " | ".join("---:" for _ in groups) + " |",
             "| Episodes | " + " | ".join(str(g["episodes"]) for g in groups) + " |",
             "| Median margin | " + " | ".join(f"{g['median_margin']:+,.0f}" for g in groups) + " |",
             "| Median step fell behind | " + " | ".join(
                 f"{g['median_behind_from_step']:.0f}" if g["median_behind_from_step"] is not None
                 else "-" for g in groups) + " |",
             "| Median concurrency share | " + " | ".join(
                 f"{g['median_concurrency_share']:.2f}" if g["median_concurrency_share"] is not None
                 else "-" for g in groups) + " |"]

    mf = data["mirror_fingerprint"]
    dist = mf["distribution"]
    lines += ["", "## Same-lineage opponents", "",
              "Similarity is the Jaccard overlap of the (step, resource) sets each seat "
              "submitted SELL orders on: an identity signal, not an economic one. Two "
              "agents running the same tape order at the same steps, liquidation no-ops "
              "included.", "",
              f"Distribution over {len(rows)} episodes: min {dist['min']:.3f}, p25 "
              f"{dist['p25']:.3f}, median {dist['median']:.3f}, p75 {dist['p75']:.3f}, max "
              f"{dist['max']:.3f}. A median of {dist['median']:.2f} means the ladder is "
              "largely forks of one public agent.", "",
              "| Threshold | Group | N | W/L/T | GSR | Median margin |",
              "| ---: | --- | ---: | ---: | ---: | ---: |"]
    for threshold, entry in mf["splits"].items():
        for name in ("mirror", "non_mirror"):
            grp = entry.get(name)
            if grp:
                lines.append(
                    f"| {threshold} | {name} | {grp['episodes']} | "
                    f"{grp['wins']}/{grp['losses']}/{grp['ties']} | {grp['gsr']:.3f} | "
                    f"{grp['median_margin']:+,.0f} |"
                )
    lines += ["",
              "Mirror games are consistently closer, by roughly 3,000 of median margin at "
              "every threshold, which is what playing a near-copy of yourself should look "
              "like. The win-rate difference is not robust: it runs 0.02 to 0.04 and "
              "changes sign between thresholds, so these data do not support a claim that "
              "we lose disproportionately to our own lineage."]

    for resource in PREMIUM + ("WHEAT", "CARROT", "EGG", "TOMATO"):
        cells = [g["by_resource"].get(resource) for g in groups]
        if not any(cells):
            continue
        lines.append("")
        lines.append(f"### {resource}")
        lines.append("")
        lines.append("| Metric | " + " | ".join(g["group"] for g in groups) + " |")
        lines.append("| --- | " + " | ".join("---:" for _ in groups) + " |")
        for key, name, fmt in (("episodes_selling", "Episodes selling", "{:.0f}"),
                               ("median_units", "Median units sold", "{:,.0f}"),
                               ("median_avg_price_vs_base", "Median price vs base", "{:.3f}"),
                               ("median_distressed_share", "Median distressed share", "{:.2f}"),
                               ("median_gross", "Median gross", "{:,.0f}")):
            lines.append(f"| {name} | " + " | ".join(
                fmt.format(c[key]) if c and c.get(key) is not None else "-" for c in cells
            ) + " |")
    args.report.write_text("\n".join(lines) + "\n")
    print(args.output)
    print(args.report)


if __name__ == "__main__":
    main()
