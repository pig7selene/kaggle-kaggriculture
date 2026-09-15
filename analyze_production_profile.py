"""Put our agent's production profile next to a frontier agent's, same units.

The frontier recommendation (2026-09-12) established that the current top five
reach 73-75 productive tiles, 11-13 peak hands and 144k-168k final money, and
called the gap an economy/production generation rather than a terminal-timing
one. What was never done is measuring our own agent in those same units, so the
~59k money gap has never been decomposed into scale (fewer tiles, fewer hands)
versus efficiency (same production, worse prices or timing). Those two diagnoses
point at completely different work, so this script measures both.

Seal discipline: Majkel episodes are enumerated from
experiments/majkel_56156662_corpus_manifest.json and only rows with
`sealed: false` are read. The six sealed G1 holdout episodes cannot enter this
analysis even by accident, and the script asserts that none did.

Caveat carried into the output: the market is global, so an opponent's selling
moves our prices. Two agents measured against different opponent pools are not
cleanly comparable on money alone; tiles and hands are own-farm quantities and
are not subject to that confound.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parent
MAJKEL_MANIFEST = ROOT / "experiments" / "majkel_56156662_corpus_manifest.json"
MAJKEL_CORPUS = Path("/private/tmp/kaggriculture_majkel_56156662")
OURS_CORPUS = Path("/private/tmp/kaggriculture_v233h_online")
OUTPUT = ROOT / "experiments" / "production_profile_gap.json"
REPORT = ROOT / "experiments" / "production_profile_gap.md"
BLOCK = 72


def counts(farm: dict) -> tuple[Counter, Counter]:
    crops, animals = Counter(), Counter()
    for row in farm["tiles"]:
        for tile in row:
            if not isinstance(tile, dict):
                continue
            if tile.get("kind") == "PLANT":
                crops[str(tile.get("crop"))] += 1
            elif tile.get("animal"):
                animals[str(tile.get("animal"))] += 1
    return crops, animals


def profile(path: Path, team: str) -> dict | None:
    replay = json.loads(path.read_text())
    teams = list(replay["info"]["TeamNames"])
    if team not in teams or teams[0] == teams[1]:
        return None
    seat = teams.index(team)
    other = 1 - seat
    steps = replay["steps"]
    last = len(steps) - 1

    peak_tiles = peak_hands = 0
    peak_crops, peak_animals = Counter(), Counter()
    land_steps: list[int] = []
    trajectory = []

    for index in range(last + 1):
        farm = steps[index][seat]["observation"]["farms"][seat]
        crops, animals = counts(farm)
        productive = sum(crops.values()) + sum(animals.values())
        peak_tiles = max(peak_tiles, productive)
        peak_hands = max(peak_hands, len(farm.get("hands", [])))
        for item, n in crops.items():
            peak_crops[item] = max(peak_crops[item], n)
        for item, n in animals.items():
            peak_animals[item] = max(peak_animals[item], n)
        if index < last:
            nxt = steps[index + 1][seat]["observation"]["farms"][seat]
            gain = len(nxt.get("unlocked_quadrants", [])) - len(farm.get("unlocked_quadrants", []))
            land_steps.extend([index] * max(0, gain))
        if index % BLOCK == 0:
            trajectory.append({
                "step": index,
                "money": float(farm.get("money", 0)),
                "productive_tiles": productive,
                "hands": len(farm.get("hands", [])),
            })

    final_money = float(steps[-1][seat]["reward"])
    return {
        "episode_id": int(replay["info"].get("EpisodeId") or path.stem.split("-")[1]),
        "opponent": teams[other],
        "final_money": final_money,
        "opponent_final_money": float(steps[-1][other]["reward"]),
        "peak_productive_tiles": peak_tiles,
        "peak_hands": peak_hands,
        "money_per_productive_tile": final_money / peak_tiles if peak_tiles else None,
        "land_steps": land_steps,
        "peak_crops": dict(sorted(peak_crops.items())),
        "peak_animals": dict(sorted(peak_animals.items())),
        "trajectory": trajectory,
    }


def median_counts(rows, field):
    items = sorted({item for row in rows for item in row[field]})
    return {item: statistics.median(row[field].get(item, 0) for row in rows) for item in items}


def outcome_stats(rows: list[dict]) -> dict:
    """Win rate and margin distribution. Rating depends on wins, not on margin
    size, so the margin *spread* matters more here than the mean."""
    margins = [row["final_money"] - row["opponent_final_money"] for row in rows]
    tally = Counter("win" if m > 0 else "loss" if m < 0 else "tie" for m in margins)
    wins = tally["win"]
    return {
        "wins": wins, "losses": tally["loss"], "ties": tally["tie"],
        "gsr": (wins + 0.5 * tally["tie"]) / len(rows),
        "mean_margin": statistics.fmean(margins),
        "median_margin": statistics.median(margins),
        "p10_margin": statistics.quantiles(margins, n=10)[0],
        "worst_margin": min(margins),
        "narrow_win_share": (
            sum(1 for m in margins if 0 < m < 5000) / wins if wins else None
        ),
    }


def summarise(label: str, rows: list[dict]) -> dict:
    med = lambda f: statistics.median(row[f] for row in rows if row[f] is not None)
    by_step: dict[int, list[dict]] = {}
    for row in rows:
        for point in row["trajectory"]:
            by_step.setdefault(point["step"], []).append(point)
    return {
        "label": label,
        "episodes": len(rows),
        "outcomes": outcome_stats(rows),
        "median_final_money": med("final_money"),
        "median_opponent_final_money": med("opponent_final_money"),
        "median_peak_productive_tiles": med("peak_productive_tiles"),
        "median_peak_hands": med("peak_hands"),
        "median_money_per_productive_tile": med("money_per_productive_tile"),
        "land_step_variants": {
            "+".join(map(str, k)): v for k, v in
            sorted(Counter(tuple(row["land_steps"]) for row in rows).items(),
                   key=lambda kv: -kv[1])[:5]
        },
        "median_peak_crops": median_counts(rows, "peak_crops"),
        "median_peak_animals": median_counts(rows, "peak_animals"),
        "trajectory": [
            {
                "step": step,
                "median_money": statistics.median(p["money"] for p in points),
                "median_productive_tiles": statistics.median(p["productive_tiles"] for p in points),
                "median_hands": statistics.median(p["hands"] for p in points),
            }
            for step, points in sorted(by_step.items())
        ],
    }


def majkel_paths() -> list[Path]:
    manifest = json.loads(MAJKEL_MANIFEST.read_text())
    paths = []
    for row in manifest["episodes"]:
        if row["sealed"]:
            continue
        if "source_path" in row:
            paths.append(Path(row["source_path"]))
        else:
            paths.append(MAJKEL_CORPUS / row["subset"] / row["replay_filename"])
    sealed = set(json.loads(MAJKEL_MANIFEST.read_text())["seal_integrity"]["sealed_ids_declared"])
    chosen = {int(p.stem.split("-")[1]) for p in paths}
    if chosen & sealed:
        raise RuntimeError("sealed holdout episode entered the production profile")
    return [p for p in paths if p.is_file()]


def collect(label, paths, team):
    rows = []
    for index, path in enumerate(paths, 1):
        row = profile(path, team)
        if row:
            rows.append(row)
        if index % 20 == 0 or index == len(paths):
            print(f"  {label}: {index}/{len(paths)}", flush=True)
    if not rows:
        raise RuntimeError(f"no episodes for {team} in {label}")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ours-corpus", type=Path, default=OURS_CORPUS)
    parser.add_argument("--ours-team", default="pig7selene")
    parser.add_argument("--ours-label", default="SmallerShock V233H Safe (submission 56183575)")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()

    print("collecting…", flush=True)
    majkel = collect("majkel", majkel_paths(), "Majkel1337")
    ours = collect("ours", sorted(args.ours_corpus.glob("episode-*-replay.json")), args.ours_team)

    panels = [summarise("Majkel1337 (submission 56156662)", majkel),
              summarise(args.ours_label, ours)]
    m, o = panels
    gap = {
        "money_ratio": m["median_final_money"] / o["median_final_money"],
        "tile_ratio": m["median_peak_productive_tiles"] / o["median_peak_productive_tiles"],
        "hands_ratio": m["median_peak_hands"] / o["median_peak_hands"],
        "money_per_tile_ratio": (
            m["median_money_per_productive_tile"] / o["median_money_per_productive_tile"]
        ),
        "decomposition_note": (
            "money_ratio decomposes as tile_ratio * money_per_tile_ratio. A tile_ratio "
            "near 1 means the deficit is efficiency; a money_per_tile_ratio near 1 means "
            "it is scale."
        ),
    }
    data = {
        "schema_version": 1,
        "sealed_g1_holdout_opened": False,
        "confound": (
            "Market inventory is global, so opponent selling moves prices. The two "
            "panels faced different opponent pools, so money comparisons are "
            "confounded; peak tiles and peak hands are own-farm quantities and are not."
        ),
        "panels": panels,
        "gap": gap,
    }
    args.output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    lines = ["# Production profile gap", "",
             f"Majkel {m['episodes']} episodes vs ours {o['episodes']} episodes. "
             "Sealed G1 holdout not opened.", "",
             "| Metric | Majkel | Ours | Ratio |", "| --- | ---: | ---: | ---: |"]
    for key, name in (("median_final_money", "Median final money"),
                      ("median_peak_productive_tiles", "Median peak productive tiles"),
                      ("median_peak_hands", "Median peak hands"),
                      ("median_money_per_productive_tile", "Median money per productive tile")):
        lines.append(f"| {name} | {m[key]:,.1f} | {o[key]:,.1f} | {m[key]/o[key]:.3f} |")
    mo, oo = m["outcomes"], o["outcomes"]
    lines += ["", "## Outcomes", "",
              "Rating moves on wins, not on how much a win is won by, so the spread "
              "of the margin distribution matters more here than its mean.", "",
              "| Metric | Majkel | Ours |", "| --- | ---: | ---: |",
              f"| W/L/T | {mo['wins']}/{mo['losses']}/{mo['ties']} | "
              f"{oo['wins']}/{oo['losses']}/{oo['ties']} |",
              f"| GSR | {mo['gsr']:.4f} | {oo['gsr']:.4f} |",
              f"| Mean margin | {mo['mean_margin']:+,.0f} | {oo['mean_margin']:+,.0f} |",
              f"| Median margin | {mo['median_margin']:+,.0f} | {oo['median_margin']:+,.0f} |",
              f"| p10 margin | {mo['p10_margin']:+,.0f} | {oo['p10_margin']:+,.0f} |",
              f"| Worst margin | {mo['worst_margin']:+,.0f} | {oo['worst_margin']:+,.0f} |",
              f"| Wins under +5k | {mo['narrow_win_share']:.0%} | {oo['narrow_win_share']:.0%} |"]
    lines += ["", "## Trajectory (median)", "",
              "| Step | Majkel money | Ours money | Majkel tiles | Ours tiles | Majkel hands | Ours hands |",
              "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for mt, ot in zip(m["trajectory"], o["trajectory"]):
        lines.append(
            f"| {mt['step']} | {mt['median_money']:,.0f} | {ot['median_money']:,.0f} | "
            f"{mt['median_productive_tiles']:.0f} | {ot['median_productive_tiles']:.0f} | "
            f"{mt['median_hands']:.0f} | {ot['median_hands']:.0f} |"
        )
    lines += ["", "## Median peak portfolio", "",
              f"- Majkel crops: {m['median_peak_crops']}",
              f"- Ours crops: {o['median_peak_crops']}",
              f"- Majkel animals: {m['median_peak_animals']}",
              f"- Ours animals: {o['median_peak_animals']}",
              "", f"- Majkel land steps: {m['land_step_variants']}",
              f"- Ours land steps: {o['land_step_variants']}",
              "", "## Confound", "", data["confound"], ""]
    args.report.write_text("\n".join(lines) + "\n")
    print(args.output)
    print(args.report)
    print(json.dumps(gap, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
