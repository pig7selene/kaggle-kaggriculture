"""Where do our losing games diverge from our winning ones?

Deliberately restricted to ground truth. The previous pass tried to reconstruct
sale revenue from SELL orders and got it wrong twice: order quantity is not
filled quantity, and even filled quantity cannot be priced from the pre-trade
quote, because the engine fills concurrently one unit at a time while the price
moves and then settles income at the end of the day. Rather than model engine
internals, this uses only quantities the replay states outright:

- farm money, for both seats, which is the thing the game is scored on
- productive tiles and hired hands, for both seats
- market price and inventory per resource, which are shared state

The question is which block the loss distribution separates from the win
distribution in, and what else is different at that block.
"""

from __future__ import annotations

import argparse

import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parent
CORPUS = Path("/private/tmp/kaggriculture_v233h_online")
OUTPUT = ROOT / "experiments" / "win_loss_divergence.json"
REPORT = ROOT / "experiments" / "win_loss_divergence.md"
TEAM = "pig7selene"
BLOCK = 72
PREMIUM = ("STRAWBERRY", "MELON", "MILK", "WOOL")

def productive(farm: dict) -> int:
    count = 0
    for row in farm["tiles"]:
        for tile in row:
            if isinstance(tile, dict) and (tile.get("kind") == "PLANT" or tile.get("animal")):
                count += 1
    return count

def episode(path: Path, team: str) -> dict | None:
    replay = json.loads(path.read_text())
    teams = list(replay["info"]["TeamNames"])
    if team not in teams or teams[0] == teams[1]:
        return None
    seat, other = teams.index(team), 1 - teams.index(team)
    steps = replay["steps"]
    base = dict(steps[0][seat]["observation"]["market"]["prices"])

    track = []
    for index in range(0, len(steps), BLOCK):
        obs = steps[index][seat]["observation"]
        farms = obs["farms"]
        prices, inventory = obs["market"]["prices"], obs["market"]["inventory"]
        track.append({
            "step": index,
            "money": float(farms[seat]["money"]),
            "opponent_money": float(farms[other]["money"]),
            "money_margin": float(farms[seat]["money"]) - float(farms[other]["money"]),
            "tiles": productive(farms[seat]),
            "opponent_tiles": productive(farms[other]),
            "hands": len(farms[seat].get("hands", [])),
            "opponent_hands": len(farms[other].get("hands", [])),
            "premium_price_vs_base": statistics.fmean(
                float(prices[r]) / base[r] for r in PREMIUM if base.get(r)
            ),
            "premium_inventory_excess": statistics.fmean(
                float(inventory[r]) - 10000.0 for r in PREMIUM if r in inventory
            ),
        })

    own = float(steps[-1][seat]["reward"])
    opp = float(steps[-1][other]["reward"])
    return {
        "episode_id": int(replay["info"].get("EpisodeId") or path.stem.split("-")[1]),
        "opponent": teams[other],
        "seat": seat,
        "final_margin": own - opp,
        "outcome": "win" if own > opp else "loss" if own < opp else "tie",
        "track": track,
    }

FIELDS = ("money", "money_margin", "tiles", "opponent_tiles", "hands", "opponent_hands",
          "premium_price_vs_base", "premium_inventory_excess")

def by_block(rows: list[dict]) -> dict:
    out: dict[int, dict] = {}
    steps = sorted({point["step"] for row in rows for point in row["track"]})
    for step in steps:
        points = [p for row in rows for p in row["track"] if p["step"] == step]
        if not points:
            continue
        out[step] = {f: statistics.median(p[f] for p in points) for f in FIELDS}
        out[step]["n"] = len(points)
    return out

def separation(wins: list[dict], losses: list[dict], step: int, field: str) -> float:
    """Probability a random loss scores below a random win on this field."""
    w = [p[field] for row in wins for p in row["track"] if p["step"] == step]
    l = [p[field] for row in losses for p in row["track"] if p["step"] == step]
    if not w or not l:
        return 0.5
    below = sum(1 for a in l for b in w if a < b)
    equal = sum(1 for a in l for b in w if a == b)
    return (below + 0.5 * equal) / (len(w) * len(l))

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

    wins = [r for r in rows if r["outcome"] == "win"]
    losses = [r for r in rows if r["outcome"] == "loss"]
    blocks = sorted({p["step"] for r in rows for p in r["track"]})
    separations = {
        field: {str(step): separation(wins, losses, step, field) for step in blocks}
        for field in FIELDS
    }
    data = {
        "schema_version": 1,
        "corpus": str(args.corpus),
        "submission_id": 56183575,
        "episodes": len(rows),
        "wins": len(wins), "losses": len(losses),
        "note": (
            "Ground truth only: farm money, tile and hand counts, market price and "
            "inventory. No sale revenue is reconstructed, because order quantity is not "
            "fill quantity and income settles at end of day."
        ),
        "median_by_block": {
            "wins": by_block(wins), "losses": by_block(losses), "all": by_block(rows),
        },
        "separation_loss_below_win": separations,
        "games": rows,
    }
    args.output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    w, l = data["median_by_block"]["wins"], data["median_by_block"]["losses"]
    lines = ["# Win/loss divergence, submission 56183575", "",
             f"{len(wins)} wins and {len(losses)} losses. {data['note']}", "",
             "## Median money margin by block", "",
             "| Step | Wins | Losses | Gap | Separation |",
             "| ---: | ---: | ---: | ---: | ---: |"]
    for step in blocks:
        if step not in w or step not in l:
            continue
        gap = w[step]["money_margin"] - l[step]["money_margin"]
        lines.append(
            f"| {step} | {w[step]['money_margin']:+,.0f} | {l[step]['money_margin']:+,.0f} | "
            f"{gap:+,.0f} | {separations['money_margin'][str(step)]:.2f} |"
        )
    lines += ["", "Separation is the probability that a random loss sits below a random "
                  "win on this measure at this block; 0.50 is no information and 1.00 is "
                  "perfect.", "",
              "## Median own money and production by block", "",
              "| Step | Win money | Loss money | Win tiles | Loss tiles | "
              "Win hands | Loss hands |", "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for step in blocks:
        if step not in w or step not in l:
            continue
        lines.append(
            f"| {step} | {w[step]['money']:,.0f} | {l[step]['money']:,.0f} | "
            f"{w[step]['tiles']:.0f} | {l[step]['tiles']:.0f} | "
            f"{w[step]['hands']:.0f} | {l[step]['hands']:.0f} |"
        )
    lines += ["", "## Shared market state by block", "",
              "Both seats face the same market, so this is context rather than an "
              "advantage; it says whether losses are played in crashed markets.", "",
              "| Step | Win premium price/base | Loss premium price/base | "
              "Win excess inventory | Loss excess inventory |",
              "| ---: | ---: | ---: | ---: | ---: |"]
    for step in blocks:
        if step not in w or step not in l:
            continue
        lines.append(
            f"| {step} | {w[step]['premium_price_vs_base']:.3f} | "
            f"{l[step]['premium_price_vs_base']:.3f} | "
            f"{w[step]['premium_inventory_excess']:+,.0f} | "
            f"{l[step]['premium_inventory_excess']:+,.0f} |"
        )
    lines += ["", "## Separation by field and block", "",
              "| Field | " + " | ".join(str(s) for s in blocks) + " |",
              "| --- | " + " | ".join("---:" for _ in blocks) + " |"]
    for field in FIELDS:
        lines.append(f"| {field} | " + " | ".join(
            f"{separations[field][str(s)]:.2f}" for s in blocks) + " |")
    args.report.write_text("\n".join(lines) + "\n")
    print(args.output)
    print(args.report)

if __name__ == "__main__":
    main()
