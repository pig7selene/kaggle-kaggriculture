"""What the current top-10 actually do, measured over hundreds of episodes.

The daily top-10 replay archive (ashok205/kaggriculture-top10-replay-archive,
CC0) holds 5,664 episodes from 2026-09-09..14 across 27 teams. Every earlier
frontier reading in this repository rested on 3 to 40 episodes of one or two
teams. This reads a sample per team and extracts the same plan-level signature
we measured for V43 and for Majkel, so V43's gap to the band is measured team
by team rather than inferred from one.

Two things per episode:

- the plan signature: land-unlock steps, cash at 221 and 288, peak productive
  tiles and hands, peak crop and animal mix, first sale step per premium good
- the opening fingerprint: the (step, verb, item, qty) set of market orders in
  steps 0-143. For a tape agent this does not depend on the seed or the shop
  draw, so it identifies the underlying public base directly. It is compared
  against V43 route 0's opening and against Lynn V44 and Moon run once locally.

Shards store one replay per row as a JSON string; rows are read by episode_id
filter so no shard is ever loaded whole.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics
import sys
import time

import pandas as pd
import pyarrow.parquet as pq

from analyze_production_profile import counts


ROOT = Path(__file__).resolve().parent
SEPT = Path("/private/tmp/kaggriculture_pull_0915/sept")
OUT = Path("/private/tmp/kaggriculture_pull_0915/out")
V43 = OUT / "kaggriculture-v43-recovering-lost-harvests/main.py"
PUBLIC = {
    "V43": V43,
    "LynnV44": OUT / "farming-score-v5-timing-optimized/main.py",
    "MoonMelons": OUT / "kaggriculture-frontier-the-moon-counts-melons/main.py",
}
OUTPUT = ROOT / "experiments" / "frontier_signature.json"
REPORT = ROOT / "experiments" / "frontier_signature.md"
OPENING = 144


def opening_orders(steps, seat) -> set:
    out = set()
    for index in range(min(OPENING, len(steps) - 1)):
        action = steps[index + 1][seat].get("action") or {}      # obs[i] pairs with action[i+1]
        for order in action.get("market") or []:
            if order:
                out.add((index, str(order[0]), str(order[1]) if len(order) > 1 else "-",
                         int(order[2]) if len(order) > 2 else 1))
    return out


def public_openings() -> dict[str, set]:
    """Run each public agent once locally and take its opening order set."""
    from kaggle_environments import make
    result = {}
    for name, path in PUBLIC.items():
        tag = "sig_" + hashlib.sha256(f"{path}{time.time_ns()}".encode()).hexdigest()[:12]
        spec = importlib.util.spec_from_file_location(tag, path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[tag] = module
        spec.loader.exec_module(module)
        agent = getattr(module, "agent", None) or getattr(module, "kaggle_agent")
        env = make("kaggriculture", configuration={"episodeSteps": 200, "seed": 1}, debug=False)
        env.run([agent, agent])
        steps = [[{"action": s[i].action, "observation": s[i].observation} for i in range(2)]
                 for s in env.steps]
        result[name] = opening_orders(steps, 0)
        sys.modules.pop(tag, None)
    return result


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def cash_at(steps, seat, step) -> float:
    return float(steps[min(step, len(steps) - 1)][seat]["observation"]["farms"][seat]["money"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-team", type=int, default=15)
    parser.add_argument("--min-team-episodes", type=int, default=20)
    parser.add_argument("--dates", default="2026-09-12,2026-09-13,2026-09-14")
    args = parser.parse_args()

    dates = args.dates.split(",")
    index = pd.read_parquet(SEPT / "episodes.parquet")
    index = index[index["date"].isin(dates)]
    team_counts = index.groupby("team_name")["episode_id"].count()
    teams = team_counts[team_counts >= args.min_team_episodes].index.tolist()
    picks = (index[index["team_name"].isin(teams)]
             .sort_values("daily_score_proxy", ascending=False)
             .groupby("team_name").head(args.per_team))
    print(f"teams {len(teams)}, episodes to read {len(picks)}", flush=True)

    refs = public_openings()
    print("public openings:", {k: len(v) for k, v in refs.items()}, flush=True)

    rows = []
    for shard, group in picks.groupby("replay_shard"):
        table = pq.read_table(SEPT / shard, filters=[("episode_id", "in", group["episode_id"].tolist())])
        frame = table.to_pandas()
        for _, rec in frame.iterrows():
            meta = group[group["episode_id"] == rec["episode_id"]].iloc[0]
            replay = json.loads(rec["replay_json"])
            team = meta["team_name"]
            teams_ = list(replay["info"]["TeamNames"])
            if team not in teams_ or teams_[0] == teams_[1]:
                continue
            seat = teams_.index(team)
            steps = replay["steps"]
            land, peak_t, peak_h = [], 0, 0
            pc, pa = Counter(), Counter()
            for i in range(len(steps)):
                farm = steps[i][seat]["observation"]["farms"][seat]
                c, a = counts(farm)
                peak_t = max(peak_t, sum(c.values()) + sum(a.values()))
                peak_h = max(peak_h, len(farm.get("hands", [])))
                for k, v in c.items():
                    pc[k] = max(pc[k], v)
                for k, v in a.items():
                    pa[k] = max(pa[k], v)
                if i < len(steps) - 1:
                    g = (len(steps[i + 1][seat]["observation"]["farms"][seat].get("unlocked_quadrants", []))
                         - len(farm.get("unlocked_quadrants", [])))
                    land += [i] * max(0, g)
            first_sell = {}
            for i in range(len(steps) - 1):
                for o in (steps[i + 1][seat].get("action") or {}).get("market") or []:
                    if o and o[0] == "SELL" and len(o) > 1 and o[1] not in first_sell:
                        first_sell[o[1]] = i
            opening = opening_orders(steps, seat)
            rows.append({
                "team": team, "episode_id": int(meta["episode_id"]),
                "score_proxy": float(meta["daily_score_proxy"]),
                "final_money": float(steps[-1][seat]["reward"]),
                "land_steps": land, "peak_tiles": peak_t, "peak_hands": peak_h,
                "cash_221": cash_at(steps, seat, 221), "cash_288": cash_at(steps, seat, 288),
                "crops": dict(pc), "animals": dict(pa),
                "first_sell": {k: first_sell.get(k) for k in ("MELON", "STRAWBERRY", "MILK", "WOOL")},
                "opening_jaccard": {k: round(jaccard(opening, v), 3) for k, v in refs.items()},
                "opening_orders": len(opening),
            })
            del replay, steps
        print(f"  {shard}: {len(rows)} episodes so far", flush=True)

    def med(xs):
        xs = [x for x in xs if x is not None]
        return statistics.median(xs) if xs else None

    summary = {}
    for team in sorted({r["team"] for r in rows}):
        rs = [r for r in rows if r["team"] == team]
        land_sig = Counter(tuple(r["land_steps"][:2]) for r in rs).most_common(1)[0]
        summary[team] = {
            "episodes": len(rs),
            "score_proxy": med([r["score_proxy"] for r in rs]),
            "final_money": med([r["final_money"] for r in rs]),
            "land_first_two_mode": list(land_sig[0]), "land_mode_share": land_sig[1] / len(rs),
            "land_second_median": med([r["land_steps"][1] for r in rs if len(r["land_steps"]) > 1]),
            "n_land_median": med([len(r["land_steps"]) for r in rs]),
            "cash_221": med([r["cash_221"] for r in rs]), "cash_288": med([r["cash_288"] for r in rs]),
            "peak_tiles": med([r["peak_tiles"] for r in rs]), "peak_hands": med([r["peak_hands"] for r in rs]),
            "tomato": med([r["crops"].get("TOMATO", 0) for r in rs]),
            "carrot": med([r["crops"].get("CARROT", 0) for r in rs]),
            "cows": med([r["animals"].get("COW", 0) for r in rs]),
            "sheep": med([r["animals"].get("SHEEP", 0) for r in rs]),
            "geese": med([r["animals"].get("GOOSE", 0) for r in rs]),
            "first_melon_sell": med([r["first_sell"]["MELON"] for r in rs]),
            "opening_jaccard": {k: med([r["opening_jaccard"][k] for r in rs]) for k in refs},
        }
    data = {"schema_version": 1, "dates": dates, "per_team": args.per_team,
            "public_reference_openings": {k: len(v) for k, v in refs.items()},
            "teams": summary, "episodes": rows}
    OUTPUT.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")

    lines = ["# Frontier plan signature (daily top-10, 2026-09-12..14)", "",
             f"{len(rows)} episodes, up to {args.per_team} per team, highest daily score first. "
             "Opening Jaccard is order-set overlap in steps 0-143 with each public agent run locally; "
             "a tape agent's opening does not depend on seed or shop draw.", "",
             "| Team | N | Score | Money | Land (mode) | Cash@221 | Tiles | Hands | Tomato | Cows/Sheep/Geese | J(V43) | J(V44) | J(Moon) |",
             "| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |"]
    for team, s in sorted(summary.items(), key=lambda kv: -(kv[1]["score_proxy"] or 0)):
        j = s["opening_jaccard"]
        lines.append(
            f"| {team} | {s['episodes']} | {s['score_proxy']:.0f} | {s['final_money']:,.0f} | "
            f"{'/'.join(map(str, s['land_first_two_mode']))} ({s['land_mode_share']:.0%}) | "
            f"{s['cash_221']:,.0f} | {s['peak_tiles']:.0f} | {s['peak_hands']:.0f} | {s['tomato']:.0f} | "
            f"{s['cows']:.0f}/{s['sheep']:.0f}/{s['geese']:.0f} | {j['V43']:.2f} | {j['LynnV44']:.2f} | {j['MoonMelons']:.2f} |"
        )
    lines += ["", "V43 (local self-play, seat 0): land 150/265(+433), cash@221 ~$880-1,345, 75 tiles, "
                  "11 hands, tomato 0, 8/6/3, first melon sell 249."]
    REPORT.write_text("\n".join(lines) + "\n")
    print(REPORT)
    print("\n".join(lines[4:]))


if __name__ == "__main__":
    main()
