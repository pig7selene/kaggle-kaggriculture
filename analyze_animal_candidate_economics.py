"""Component-level held-out decomposition for the selected animal candidate."""

import argparse
import json
import statistics
from collections import Counter

from analyze_livestock_economics import _load_agent, _player_trace, _run_traced
from benchmark import ROOT


COMPONENTS = (
    "crop_revenue",
    "animal_revenue",
    "fertilizer_revenue",
    "seed_spending",
    "animal_purchase_spending",
    "structure_spending",
    "labor_spending",
    "land_spending",
    "feed_purchase_spending",
)


def _mean(values):
    return statistics.fmean(values) if values else 0.0


def _durable_positive(values):
    for day, value in enumerate(values):
        if value >= 0 and all(later >= 0 for later in values[day:]):
            return day
    return None


def _aggregate(matchups, left_name, right_name):
    daily = []
    for day in range(30):
        row = {"day": day}
        for role in (left_name, right_name):
            source = [match[role]["days"][day] for match in matchups]
            for key in (
                "bank",
                *COMPONENTS,
                "daily_income",
                "daily_spending",
                "cumulative_income",
                "cumulative_spending",
                "productive_tiles",
                "total_inventory_value",
                "economic_position",
            ):
                row[f"{role}_{key}"] = _mean([value[key] for value in source])
        row["bank_advantage"] = row[f"{left_name}_bank"] - row[f"{right_name}_bank"]
        daily.append(row)

    totals = {}
    for role in (left_name, right_name):
        role_totals = {}
        for key in COMPONENTS:
            role_totals[key] = _mean(
                [sum(day[key] for day in match[role]["days"]) for match in matchups]
            )
        role_totals["final_money"] = _mean(
            [match[role]["days"][-1]["bank"] for match in matchups]
        )
        totals[role] = role_totals
    delta = {
        key: totals[left_name][key] - totals[right_name][key]
        for key in (*COMPONENTS, "final_money")
    }

    direct_payback_days = []
    for match in matchups:
        values = []
        for day in match[left_name]["days"]:
            values.append(
                day["animal_revenue"]
                + day["fertilizer_revenue"]
                - day["animal_purchase_spending"]
                - day["feed_purchase_spending"]
                + (values[-1] if values else 0)
            )
        direct_payback_days.append(_durable_positive(values))

    sales = {}
    for role in (left_name, right_name):
        product_units = Counter()
        product_revenue = Counter()
        product_weighted_step = Counter()
        for match in matchups:
            for product, item in match[role]["sale_timing"].items():
                product_units[product] += item["units"]
                product_revenue[product] += item["revenue"]
                product_weighted_step[product] += item["weighted_sale_step"] * item["units"]
        sales[role] = {
            product: {
                "average_units_per_game": product_units[product] / len(matchups),
                "average_revenue_per_game": product_revenue[product] / len(matchups),
                "weighted_sale_step": product_weighted_step[product] / product_units[product],
            }
            for product in sorted(product_units)
        }
    return {
        "games": len(matchups),
        "totals": totals,
        "candidate_minus_opponent": delta,
        "candidate_direct_animal_payback_days": direct_payback_days,
        "median_candidate_direct_animal_payback_day": statistics.median(direct_payback_days),
        "daily": daily,
        "sale_timing": sales,
    }


def _run_matchup(candidate_path, opponent_path, seed_start, seeds, opponent_name):
    matches = []
    for seed in range(seed_start, seed_start + seeds):
        for candidate_seat in (0, 1):
            candidate = _load_agent(str(candidate_path))
            opponent = _load_agent(str(opponent_path))
            agents = [opponent, opponent]
            agents[candidate_seat] = candidate
            env, events = _run_traced(agents, seed)
            opponent_seat = 1 - candidate_seat
            matches.append(
                {
                    "candidate": _player_trace(env, events, candidate_seat),
                    "opponent": _player_trace(env, events, opponent_seat),
                }
            )
            print(
                f"{opponent_name} seed={seed} candidate_seat={candidate_seat}",
                flush=True,
            )
    return _aggregate(matches, "candidate", "opponent")


def _write_markdown(path, result):
    livestock = result["matchups"]["proxy_livestock_crop"]
    baseline = result["matchups"]["adaptive_c_phased"]
    lines = [
        f"# {result['candidate']} economic decomposition",
        "",
        f"Held-out seeds: {result['seeds'][0]}–{result['seeds'][-1]}, both seats.",
        "",
        "## Component totals per game",
        "",
        "| Matchup | Side | Final money | Crop revenue | Animal revenue | Fertilizer revenue | Seeds | Animals | Structures | Labor | Land | Bought feed |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for matchup_name, matchup in result["matchups"].items():
        for role in ("candidate", "opponent"):
            value = matchup["totals"][role]
            lines.append(
                f"| {matchup_name} | {role} | {value['final_money']:.2f} | "
                f"{value['crop_revenue']:.2f} | {value['animal_revenue']:.2f} | "
                f"{value['fertilizer_revenue']:.2f} | {value['seed_spending']:.2f} | "
                f"{value['animal_purchase_spending']:.2f} | {value['structure_spending']:.2f} | "
                f"{value['labor_spending']:.2f} | {value['land_spending']:.2f} | "
                f"{value['feed_purchase_spending']:.2f} |"
            )
    lines.extend(
        [
            "",
            f"Median direct cow payback day versus livestock proxy: {livestock['median_candidate_direct_animal_payback_day']}",
            f"Median direct cow payback day versus phased baseline: {baseline['median_candidate_direct_animal_payback_day']}",
            "",
            "## Day-by-day candidate versus livestock proxy",
            "",
            "| Day | Candidate bank | Proxy bank | Advantage | Candidate crop rev | Cow-product rev | Fertilizer rev | Feed cost | Proxy crop rev | Proxy animal rev | Proxy fertilizer rev | Candidate productive tiles | Proxy productive tiles |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in livestock["daily"]:
        lines.append(
            "| {day} | {candidate_bank:.0f} | {opponent_bank:.0f} | {bank_advantage:+.0f} | "
            "{candidate_crop_revenue:.0f} | {candidate_animal_revenue:.0f} | "
            "{candidate_fertilizer_revenue:.0f} | {candidate_feed_purchase_spending:.0f} | "
            "{opponent_crop_revenue:.0f} | {opponent_animal_revenue:.0f} | "
            "{opponent_fertilizer_revenue:.0f} | {candidate_productive_tiles:.1f} | "
            "{opponent_productive_tiles:.1f} |".format(**row)
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-start", type=int, default=8700)
    parser.add_argument("--seeds", type=int, default=16)
    parser.add_argument("--candidate", default="animal_c2_cows")
    parser.add_argument("--stem", default="animal_c2_economic_decomposition")
    args = parser.parse_args()
    candidate = ROOT / "agents" / f"{args.candidate}.py"
    if not candidate.exists():
        parser.error(f"candidate does not exist: {candidate}")
    matchups = {
        "proxy_livestock_crop": _run_matchup(
            candidate,
            ROOT / "agents" / "proxies" / "livestock_crop.py",
            args.seed_start,
            args.seeds,
            "proxy_livestock_crop",
        ),
        "adaptive_c_phased": _run_matchup(
            candidate,
            ROOT / "agents" / "adaptive_c_phased.py",
            args.seed_start,
            args.seeds,
            "adaptive_c_phased",
        ),
    }
    result = {
        "schema_version": 1,
        "candidate": args.candidate,
        "seeds": list(range(args.seed_start, args.seed_start + args.seeds)),
        "positions": [0, 1],
        "matchups": matchups,
    }
    json_path = ROOT / "experiments" / f"{args.stem}.json"
    md_path = ROOT / "experiments" / f"{args.stem}.md"
    json_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    _write_markdown(md_path, result)
    print(f"Saved {json_path}")
    print(f"Saved {md_path}")


if __name__ == "__main__":
    main()
