"""Counterfactual matched opening audit for the frozen current router.

For each representative public appearance, the frozen agent occupies that
player's original seat and the opponent replays its original public action
trace.  This preserves the seed, seat, and opponent intent while exposing the
first cash-flow divergence caused by our opening.
"""

from __future__ import annotations

import argparse
import json
import statistics
from copy import deepcopy
from pathlib import Path
from runpy import run_path

from kaggle_environments import make

from analyze_opening_capital_flow import ROOT, _aggregate, _analyze_appearance


TOP_ANALYSIS = ROOT / "experiments" / "opening_capital_flow_top.json"
DEFAULT_JSON = ROOT / "experiments" / "opening_current_matched.json"
DEFAULT_MARKDOWN = ROOT / "experiments" / "opening_current_matched.md"
CURRENT_AGENT = ROOT / "agents" / "router_replay_hands12.py"
EPISODE_STEPS = 288  # State at day 11/hour 0 includes all day-10 actions.


class ReplayActionAgent:
    def __init__(self, replay_steps, player):
        self.steps = replay_steps
        self.player = player

    def __call__(self, obs, configuration=None):
        # Kaggle stores an action on the state produced after that action, so
        # observation step s corresponds to the action stored at replay s+1.
        index = int(obs.get("step", 0)) + 1
        if index >= len(self.steps):
            return {"farmer": ["PASS"], "hands": [], "market": []}
        return deepcopy(self.steps[index][self.player].get("action") or {})


def _turn_revenue(appearance):
    return {
        row["step"]: {
            event["item"]: event["revenue"]
            for event in row["events"]["sales"]
        }
        for row in appearance["economic_turns"]
        if row["events"]["sales"]
    }


def _cumulative(values, step, products):
    result = {product: 0 for product in products}
    for event_step, revenue in values.items():
        if event_step > step:
            continue
        for product, amount in revenue.items():
            result[product] = result.get(product, 0) + amount
    return {key: value for key, value in sorted(result.items()) if value}


def _first_divergences(public, current, public_replay, local_replay, seat):
    public_revenue = _turn_revenue(public)
    current_revenue = _turn_revenue(current)
    products = {
        product
        for turns in (public_revenue, current_revenue)
        for revenue in turns.values()
        for product in revenue
    }
    first_return = None
    first_bank = None
    maximum = min(11 * 24, len(public_replay["steps"]) - 1, len(local_replay["steps"]) - 1)
    for step in range(24, maximum):
        public_cumulative = _cumulative(public_revenue, step, products)
        current_cumulative = _cumulative(current_revenue, step, products)
        if first_return is None and sum(public_cumulative.values()) > sum(current_cumulative.values()):
            first_return = {
                "step": step,
                "day": step // 24,
                "hour": step % 24,
                "public_cumulative_revenue": public_cumulative,
                "current_cumulative_revenue": current_cumulative,
                "revenue_gap": sum(public_cumulative.values()) - sum(current_cumulative.values()),
            }
        public_bank = float(public_replay["steps"][step][0]["observation"]["farms"][seat]["money"])
        current_bank = float(local_replay["steps"][step][0]["observation"]["farms"][seat]["money"])
        if first_bank is None and current_bank < public_bank:
            first_bank = {
                "step": step,
                "day": step // 24,
                "hour": step % 24,
                "public_bank": public_bank,
                "current_bank": current_bank,
                "bank_gap": public_bank - current_bank,
            }
        if first_return and first_bank:
            break
    return {"first_return_deficit": first_return, "first_bank_deficit": first_bank}


def _checkpoint_comparison(public, current):
    public_days = {row["day"]: row for row in public["daily_checkpoints"]}
    current_days = {row["day"]: row for row in current["daily_checkpoints"]}
    output = []
    for day in (4, 6, 8, 10):
        top = public_days[day]
        ours = current_days[day]
        output.append(
            {
                "day": day,
                "public_bank_start": top["bank_start"],
                "current_bank_start": ours["bank_start"],
                "public_bank_after_day": top["bank_after_day"],
                "current_bank_after_day": ours["bank_after_day"],
                "public_productive_tiles": top["farm_after_day"]["productive_tiles"],
                "current_productive_tiles": ours["farm_after_day"]["productive_tiles"],
                "public_quadrants": top["farm_after_day"]["quadrants"],
                "current_quadrants": ours["farm_after_day"]["quadrants"],
                "public_animals": top["farm_after_day"]["animals"],
                "current_animals": ours["farm_after_day"]["animals"],
                "public_max_hands": top["max_hands"],
                "current_max_hands": ours["max_hands"],
            }
        )
    return output


def _render_markdown(output, analysis):
    lines = [
        "# Frozen-router matched opening audit",
        "",
        "Each run uses the original public seed and seat. The other player emits the exact action trace from the public replay. Invalid counterfactual opponent orders remain silent no-ops under normal game rules.",
        "",
        f"- Frozen source: `{analysis['source_agent']}`",
        f"- Matched runs: {len(analysis['matches'])}",
        f"- Financial reconstruction mismatches: {analysis['financial_reconstruction_mismatches']}",
        "",
        "## Median checkpoint comparison",
        "",
        "| Day | Public bank after day | Current bank after day | Public tiles | Current tiles | Public quadrants | Current quadrants | Public cows/sheep | Current cows/sheep | Public/current max hands |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    top = analysis["public_aggregate"]["daily_checkpoints"]
    ours = analysis["current_aggregate"]["daily_checkpoints"]
    for day in (4, 6, 8, 10):
        p, c = top[str(day)], ours[str(day)]
        lines.append(
            f"| {day} | ${p['median_bank_after_day']:,.0f} | ${c['median_bank_after_day']:,.0f} | "
            f"{p['median_productive_tiles_after_day']} | {c['median_productive_tiles_after_day']} | "
            f"{p['median_quadrants_after_day']} | {c['median_quadrants_after_day']} | "
            f"{p['median_cows_after_day']}/{p['median_sheep_after_day']} | "
            f"{c['median_cows_after_day']}/{c['median_sheep_after_day']} | "
            f"{p['median_max_hands']}/{c['median_max_hands']} |"
        )
    lines.extend(["", "## First concrete divergences", ""])
    for match in analysis["matches"]:
        returned = match["divergence"]["first_return_deficit"]
        bank = match["divergence"]["first_bank_deficit"]
        lines.append(
            f"- **{match['team_name']} episode {match['episode_id']} seat {match['seat']}**: "
            f"return deficit day {returned['day']} hour {returned['hour']} "
            f"(${returned['revenue_gap']:,.0f}); "
            + (
                f"bank deficit day {bank['day']} hour {bank['hour']} (${bank['bank_gap']:,.0f})."
                if bank else "no bank deficit through day 10."
            )
        )
    output.write_text("\n".join(lines) + "\n")


def run(top_path, json_output, markdown_output, agent_path=CURRENT_AGENT):
    agent_path = agent_path.resolve()
    top = json.loads(top_path.read_text())
    public_aggregate = _aggregate(top["representative_appearances"])
    matches = []
    current_appearances = []
    for public in top["representative_appearances"]:
        replay_path = ROOT / public["source_replay"]
        public_replay = json.loads(replay_path.read_text())
        seat = public["player"]
        opponent = 1 - seat
        current_agent = run_path(str(agent_path))["agent"]
        trace = ReplayActionAgent(public_replay["steps"], opponent)
        agents = [trace, trace]
        agents[seat] = current_agent
        env = make(
            "kaggriculture",
            configuration={"episodeSteps": EPISODE_STEPS, "seed": public["seed"]},
            debug=True,
        )
        env.run(agents)
        local_replay = env.toJSON()
        local_replay["info"].update(
            {
                "EpisodeId": -int(public["episode_id"]),
                "TeamNames": [
                    agent_path.stem if index == seat else public["opponent"] + " [trace]"
                    for index in range(2)
                ],
            }
        )
        current = _analyze_appearance(
            ROOT / "experiments" / "counterfactual-local.json", local_replay, seat
        )
        current["episode_id"] = public["episode_id"]
        current["team_name"] = agent_path.stem
        current["opponent"] = public["opponent"] + " [trace]"
        current_appearances.append(current)
        matches.append(
            {
                "episode_id": public["episode_id"],
                "seed": public["seed"],
                "seat": seat,
                "team_name": public["team_name"],
                "opponent_trace": public["opponent"],
                "divergence": _first_divergences(
                    public, current, public_replay, local_replay, seat
                ),
                "checkpoints": _checkpoint_comparison(public, current),
                "public_milestones": public["milestones"],
                "current_milestones": current["milestones"],
                "current_economic_turns": current["economic_turns"],
                "current_capital_through_day_10": current["capital_through_day_10"],
            }
        )
    analysis = {
        "schema_version": 1,
        "method": "same seed/seat with original opponent public action trace",
        "source_agent": str(agent_path.relative_to(ROOT)),
        "episode_steps": EPISODE_STEPS,
        "financial_reconstruction_mismatches": sum(
            row["financial_reconstruction_mismatches"] for row in current_appearances
        ),
        "public_aggregate": public_aggregate,
        "current_aggregate": _aggregate(current_appearances),
        "matches": matches,
    }
    json_output.write_text(json.dumps(analysis, indent=2) + "\n")
    _render_markdown(markdown_output, analysis)
    return analysis


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=Path, default=TOP_ANALYSIS)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--agent", type=Path, default=CURRENT_AGENT)
    args = parser.parse_args()
    analysis = run(args.top, args.json, args.markdown, args.agent)
    print(
        f"matched {len(analysis['matches'])} openings; "
        f"mismatches={analysis['financial_reconstruction_mismatches']}"
    )


if __name__ == "__main__":
    main()
