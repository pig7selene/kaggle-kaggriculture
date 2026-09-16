"""Pull the frontier teams that run our own public lineage, and diff them against V43.

The frontier signature found two daily-top-10 teams whose opening order set
overlaps V43's at 0.91-0.94 -- the same public lineage we run -- and whose land
timing (150/265), tile count and animal mix match V43's plan, yet who score
roughly 300 leaderboard points above our V43 build. Whatever they changed is
after step 144 and is not visible in the plan signature.

Two things follow, and this script sets up both:

1. An action-level diff. For each of their episodes, take the first-two-shop
   pair, look up the route V43 would play on it, and compare step by step from
   144: field verbs, market orders, and per-item SELL timing. Where and how the
   two diverge is the change itself.
2. Transplant candidacy. Majkel's tapes failed in V43's chassis because his farm
   layout differs, so his actions referenced tiles holding other things. These
   teams share V43's opening and plan, so their layouts should match V43's and
   their tails may replay cleanly. Their replays are saved as per-episode JSON
   in the same shape the Majkel corpus uses, so build_v43_majkel_hybrid.py can
   be pointed at them unchanged.

Replays are read from the archive shards by episode_id filter; nothing is
loaded whole. Named with 'manifest' so the summary stays tracked.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import runpy
import statistics

import pandas as pd
import pyarrow.parquet as pq

from analyze_v27_routes import normalized_action


ROOT = Path(__file__).resolve().parent
SEPT = Path("/private/tmp/kaggriculture_pull_0915/sept")
V43 = Path("/private/tmp/kaggriculture_pull_0915/out/kaggriculture-v43-recovering-lost-harvests/main.py")
CORPUS = Path("/private/tmp/kaggriculture_frontier_lineage")
MANIFEST = ROOT / "experiments" / "frontier_lineage_corpus_manifest.json"
REPORT = ROOT / "experiments" / "frontier_lineage_diff.md"
TEAMS = ("アルモンド", "redblackbst")
SPLIT = 144


def field(action) -> list:
    return [action.get("farmer"), *(action.get("hands") or [])]


def sells(action) -> dict:
    out: dict[str, int] = {}
    for o in action.get("market") or []:
        if o and o[0] == "SELL" and len(o) > 2:
            out[o[1]] = out.get(o[1], 0) + int(o[2])
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--teams", default=",".join(TEAMS))
    parser.add_argument("--max-per-team", type=int, default=60)
    args = parser.parse_args()
    teams = [t for t in args.teams.split(",") if t]

    ns = runpy.run_path(str(V43))
    routes, non_yarn, yarn = ns["_ROUTES"], ns["_R108_SHOP_ROUTES"], ns["_R110_OLD_SHOPS"]

    def v43_route_for(pair: tuple) -> int:
        return yarn.get(pair, 0) if "YARN_STORE" in pair else non_yarn.get(pair, 100)

    index = pd.read_parquet(SEPT / "episodes.parquet")
    index = index[index["team_name"].isin(teams)].sort_values("daily_score_proxy", ascending=False)
    picks = index.groupby("team_name").head(args.max_per_team)
    print({t: int((picks["team_name"] == t).sum()) for t in teams}, "episodes to pull", flush=True)

    episodes, diffs = [], []
    for shard, group in picks.groupby("replay_shard"):
        table = pq.read_table(SEPT / shard, filters=[("episode_id", "in", group["episode_id"].tolist())])
        for _, rec in table.to_pandas().iterrows():
            meta = group[group["episode_id"] == rec["episode_id"]].iloc[0]
            team = meta["team_name"]
            raw = rec["replay_json"].encode()
            replay = json.loads(raw)
            names = list(replay["info"]["TeamNames"])
            if team not in names or names[0] == names[1]:
                continue
            seat = names.index(team)
            steps = replay["steps"]
            shops = tuple(steps[-1][seat]["observation"]["town"]["unlocked_shops"][:2])
            out_dir = CORPUS / team
            out_dir.mkdir(parents=True, exist_ok=True)
            path = out_dir / f"episode-{int(meta['episode_id'])}-replay.json"
            path.write_bytes(raw)

            # Diff against the V43 route this pair maps to, from step 144.
            route = v43_route_for(shops)
            tape = routes[route]
            field_same = market_same = 0
            first_div = None
            sell_lead: dict[str, list[int]] = defaultdict(list)
            for step in range(SPLIT, 719):
                theirs = normalized_action(replay, seat, step)
                ours = tape[step]
                f_eq = field(theirs) == field(ours)
                m_eq = sorted(map(json.dumps, theirs["market"])) == sorted(map(json.dumps, ours.get("market") or []))
                field_same += f_eq
                market_same += m_eq
                if first_div is None and not (f_eq and m_eq):
                    first_div = step
            # Opening agreement, as a control: should be near-identical.
            open_same = sum(field(normalized_action(replay, seat, s)) == field(routes[0][s]) for s in range(SPLIT))
            their_sells = Counter()
            our_sells = Counter()
            for step in range(SPLIT, 719):
                for k, v in sells(normalized_action(replay, seat, step)).items():
                    their_sells[k] += v
                for k, v in sells(tape[step]).items():
                    our_sells[k] += v
            row = {
                "team": team, "episode_id": int(meta["episode_id"]), "seat": seat,
                "opponent": names[1 - seat], "shops": list(shops), "v43_route": route,
                "score_proxy": float(meta["daily_score_proxy"]),
                "final_money": float(steps[-1][seat]["reward"]),
                "opponent_money": float(steps[-1][1 - seat]["reward"]),
                "opening_field_agreement": open_same / SPLIT,
                "tail_field_agreement": field_same / (719 - SPLIT),
                "tail_market_agreement": market_same / (719 - SPLIT),
                "first_divergence_step": first_div,
                "their_sell_orders_by_item": dict(their_sells),
                "v43_sell_orders_by_item": dict(our_sells),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "path": str(path),
            }
            episodes.append(row)
            del replay, steps, raw
        print(f"  {shard}: {len(episodes)} episodes", flush=True)

    summary = {}
    for team in teams:
        rs = [r for r in episodes if r["team"] == team]
        if not rs:
            continue
        med = lambda k: statistics.median(r[k] for r in rs if r[k] is not None)
        their = Counter()
        ours = Counter()
        for r in rs:
            their.update(r["their_sell_orders_by_item"])
            ours.update(r["v43_sell_orders_by_item"])
        summary[team] = {
            "episodes": len(rs), "distinct_pairs": len({tuple(r["shops"]) for r in rs}),
            "score_proxy": med("score_proxy"), "final_money": med("final_money"),
            "opening_field_agreement": med("opening_field_agreement"),
            "tail_field_agreement": med("tail_field_agreement"),
            "tail_market_agreement": med("tail_market_agreement"),
            "first_divergence_step": med("first_divergence_step"),
            "sell_orders_per_episode_theirs": {k: round(v / len(rs), 1) for k, v in sorted(their.items())},
            "sell_orders_per_episode_v43": {k: round(v / len(rs), 1) for k, v in sorted(ours.items())},
        }
    MANIFEST.write_text(json.dumps({
        "schema_version": 1, "corpus": str(CORPUS), "teams": summary, "episodes": episodes,
        "v43_main_sha256": hashlib.sha256(V43.read_bytes()).hexdigest(),
    }, indent=1, ensure_ascii=False) + "\n")

    lines = ["# Frontier teams on our lineage: diff against V43 from step 144", "",
             "Opening agreement is the fraction of steps 0-143 whose field actions equal V43 route 0's; "
             "tail agreement is the same from 144 against the V43 route the pair maps to.", "",
             "| Team | N | Pairs | Score | Money | Opening field agr. | Tail field agr. | Tail market agr. | First divergence |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for team, s in summary.items():
        lines.append(f"| {team} | {s['episodes']} | {s['distinct_pairs']} | {s['score_proxy']:.0f} | "
                     f"{s['final_money']:,.0f} | {s['opening_field_agreement']:.2f} | "
                     f"{s['tail_field_agreement']:.2f} | {s['tail_market_agreement']:.2f} | "
                     f"{s['first_divergence_step']:.0f} |")
    for team, s in summary.items():
        lines += ["", f"## {team}: SELL orders per episode from step 144 (theirs vs V43's route)", "",
                  "| Item | Theirs | V43 |", "| --- | ---: | ---: |"]
        for item in sorted(set(s["sell_orders_per_episode_theirs"]) | set(s["sell_orders_per_episode_v43"])):
            lines.append(f"| {item} | {s['sell_orders_per_episode_theirs'].get(item, 0)} | "
                         f"{s['sell_orders_per_episode_v43'].get(item, 0)} |")
    REPORT.write_text("\n".join(lines) + "\n")
    print(REPORT)
    print("\n".join(lines[4:]))


if __name__ == "__main__":
    main()
