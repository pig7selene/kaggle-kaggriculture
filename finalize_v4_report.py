"""Consolidate V4 negative results into all required artifacts and report."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parent
EXPERIMENTS = ROOT / "experiments"


def load(name):
    return json.loads((EXPERIMENTS / name).read_text())


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def pct(values, fraction):
    values = sorted(float(value) for value in values)
    if not values:
        return None
    point = fraction * (len(values) - 1)
    lower = int(point)
    weight = point - lower
    return values[lower] * (1 - weight) + values[min(lower + 1, len(values) - 1)] * weight


def collect_screens():
    names = (
        "v4_screen_market.json", "v4_screen_market_hold.json",
        "v4_screen_economic.json", "v4_screen_nazmus.json",
    )
    screens = [load(name) for name in names]
    agents, paired, games = {}, {}, []
    for payload in screens:
        games.extend(payload["games"])
        for name, row in payload["summary"].items():
            if name != "V2":
                agents[name] = row
        for name, row in payload["paired_vs_v2"].items():
            paired[name] = row
    return screens, agents, paired, games


def action_map(agents, paired, games):
    definitions = {
        "M_day": ("W2/W3/W4", "Sell all available premium stock at day boundary."),
        "M_pressure": ("W2/W3/W4", "Sell full premium stock on visible opponent ready-supply pressure."),
        "M_half": ("W2/W3/W4", "Sell half premium stock on visible opponent ready-supply pressure."),
        "M_fair": ("W2/W3/W4", "Sell on visible pressure or quote at/above base."),
        "M_hold_floor": ("W2/W3/W4", "Suppress premium sale below 10% base; sell on recovery."),
        "M_hold_low": ("W2/W3/W4", "Suppress premium sale below 25% base; sell on recovery."),
        "M_hold_safe": ("W2/W3/W4", "Suppress low premium sale only under shed safety limit."),
        "C_cows6": ("W1 step 192", "Skip both final V2 cows."),
        "C_cows7": ("W1 step 192", "Buy one rather than two final V2 cows."),
        "E_no_hire29": ("W4 step 696+", "Suppress day-29 hires."),
        "E_no_seed25": ("W4 step 600+", "Suppress late seed purchases."),
        "E_liq27": ("W4 step 648+", "Force premium liquidation from day 27."),
        "W_wheat40": ("W3 step 481", "Reduce day-20 wheat seed wave 46 to 40."),
        "W_wheat34": ("W3 step 481", "Reduce day-20 wheat seed wave 46 to 34."),
        "N0_raw": ("Nazmus full route", "Raw Nazmus route without K3 repair."),
        "N1_weed": ("Nazmus full route", "Nazmus route plus frozen K3 weed repair."),
        "N2_rescue": ("Nazmus step 655+", "Nazmus plus bounded shed-cow wheat pickup/feed rescue."),
    }
    rows = []
    for name, pair in paired.items():
        summary = agents[name]
        relevant = [row for row in games if row["candidate"] == name]
        override_rates = [row.get("override_rate", 0) for row in relevant if not row.get("runtime_error")]
        rows.append({
            "candidate": name, "window": definitions[name][0], "alternative": definitions[name][1],
            "sample_count": pair["pairs"], "paired_mean_delta": pair["average_money_delta"],
            "paired_median_delta": pair["median_money_delta"],
            "paired_p10_delta": pair["p10_money_delta"], "paired_p5_delta": pair["p5_money_delta"],
            "paired_wins": pair["wins"], "paired_losses": pair["losses"], "paired_ties": pair["ties"],
            "activation_frequency": statistics.fmean(override_rates) if override_rates else 0,
            "downstream_divergence": "full downstream state allowed after the bounded action",
            "runtime_failures": summary["runtime_failures"], "semantic_failures": summary["semantic_failures"],
            "livestock_losses": summary["livestock_losses"], "meaningful_stranding": summary["meaningful_stranding"],
            "decision": "reject",
            "confidence": "high negative" if pair["losses"] >= 12 else "moderate negative",
        })
    return {
        "schema_version": 1,
        "editable_windows": [
            {"id": "W1", "steps": [192, 192], "reason": "last two discretionary cow purchases"},
            {"id": "W2", "steps": [240, 264], "reason": "second-land liquidation and reinvestment wave"},
            {"id": "W3", "steps": [336, 527], "reason": "premium realization and second crop wave"},
            {"id": "W4", "steps": [576, 718], "reason": "terminal ROI, liquidation, and late labor"},
        ],
        "actions": sorted(rows, key=lambda row: row["candidate"]),
        "interpretation": "Every tested online override was rejected; local strawberry timing counterfactual headroom was under 100 coins and inconsistent.",
    }


def module_ablations(agents, paired):
    family = {
        "M": [name for name in agents if name.startswith("M_")],
        "E": [name for name in agents if name.startswith("E_")],
        "C": [name for name in agents if name.startswith("C_")],
        "W": [name for name in agents if name.startswith("W_")],
        "N": [name for name in agents if name.startswith("N")],
    }
    payload = {"schema_version": 1, "baseline": "V2", "candidates": {}, "families": {}}
    for name, summary in agents.items():
        payload["candidates"][name] = {"summary": summary, "paired_vs_v2": paired[name], "passed": False}
    for key, names in family.items():
        best = max(names, key=lambda name: paired[name]["average_money_delta"])
        payload["families"][key] = {
            "candidates": names, "strongest": best,
            "strongest_paired_delta": paired[best]["average_money_delta"],
            "passed": False, "decision": "reject",
        }
    payload["combination_search"] = {
        "performed": False,
        "reason": "No individual module passed the mandatory positive-mean/tail/safety gate; combining rejected modules would violate the causal protocol.",
    }
    return payload


def override_events(games):
    baseline = {
        row["key"].replace("|V2|", "|*|"): row
        for row in games if row["candidate"] == "V2" and not row.get("runtime_error")
    }
    market, endgame = [], []
    for row in games:
        if row["candidate"] == "V2" or row.get("runtime_error"):
            continue
        control = baseline.get(row["key"].replace(f"|{row['candidate']}|", "|*|"))
        realized = row["money"] - control["money"] if control else None
        for event in row.get("override_log", []):
            detail = event.get("detail", {}) or {}
            signals = detail.get("sales") or detail.get("changes") or []
            first_signal = signals[0] if signals else {}
            enriched = {
                **event, "candidate": row["candidate"], "game_key": row["key"],
                "opponent": row["opponent"], "seat": row["seat"],
                "realized_downstream_final_money_delta": realized,
            }
            trigger = str(event.get("trigger", ""))
            if trigger.startswith("market:"):
                enriched.update({
                    "current_quote": first_signal.get("quote", event.get("quotes")),
                    "opponent_market_signal": {
                        "ready": first_signal.get("opponent_ready"),
                        "capacity": first_signal.get("opponent_capacity"),
                        "market_inventory_jump": first_signal.get("market_inventory_jump"),
                        "quote_drop": first_signal.get("quote_drop"),
                    },
                    "expected_next_v2_sale": first_signal.get("expected_next_v2_sale"),
                    "estimated_delay_regret": None,
                    "delay_regret_status": "not trusted online; measured only by paired downstream counterfactual",
                })
                market.append(enriched)
            elif trigger.startswith("endgame:"):
                enriched.update({
                    "turns_remaining": detail.get("turns_remaining", 719 - int(event.get("step", 719))),
                    "estimated_remaining_roi": None,
                    "expected_harvest_time": None,
                    "expected_realization_opportunity": "frozen V2 downstream sale schedule",
                    "final_money_delta": realized,
                    "estimate_status": "hypothesis tested causally; no online ROI estimator promoted",
                })
                endgame.append(enriched)
    return market, endgame


def selection_payload(ablations):
    return {
        "schema_version": 1,
        "development_only": True,
        "selection_holdout_opened": False,
        "finalists": ["V2"],
        "module_family_decisions": ablations["families"],
        "reason": "All dynamic candidates regressed in development. Only frozen V2 was SHA-locked for fresh baseline confirmation.",
    }


def nazmus_payload(screen):
    return {
        "schema_version": 1,
        "known_failure": {
            "condition": "At day 27, hour 23, two shed-adjacent cows can remain unfed with consecutive_unfed=1 while workers have no wheat.",
            "observed_escape_step": 671,
            "raw_route_screen_livestock_losses": screen["summary"]["N0_raw"]["livestock_losses"],
        },
        "N0": {"path": screen["candidates"]["N0_raw"], "summary": screen["summary"]["N0_raw"], "paired": screen["paired_vs_v2"]["N0_raw"]},
        "N1": {"path": screen["candidates"]["N1_weed"], "summary": screen["summary"]["N1_weed"], "paired": screen["paired_vs_v2"]["N1_weed"]},
        "N2": {
            "path": screen["candidates"]["N2_rescue"], "summary": screen["summary"]["N2_rescue"],
            "paired": screen["paired_vs_v2"]["N2_rescue"],
            "rescue": "Only a shed-tile cow with consecutive_unfed>=1 and no carried wheat can start a buy-one/pickup/feed transaction.",
        },
        "decision": "reject",
        "reason": "N1 and N2 are safe in the screen but lose about 2.2k paired money to V2; N2 costs slightly more than N1.",
    }


def report(diagnostics, clusters, action_values, ablations, market_cf, end_cf, capital_cf, final):
    def cf_rows(payload):
        return sorted(payload["summary"].items(), key=lambda item: item[1]["average_final_money_delta"], reverse=True)
    best_individual = max(ablations["candidates"], key=lambda name: ablations["candidates"][name]["paired_vs_v2"]["average_money_delta"])
    best_pair = ablations["candidates"][best_individual]["paired_vs_v2"]
    final_summary = final["summary"]["V2"]
    lines = [
        "# Super Replay Backbone V4 — bounded dynamic strategy search", "",
        "## Decision", "",
        "**No V4 agent was promoted. Frozen V2 remains the research best.** No dynamic module passed development, so no module combination was eligible for selection or protected elite final holdout. `submission/main.py` was not modified and nothing was submitted or uploaded.", "",
        "## Evidence and failure clusters", "",
        f"The deployed V2 corpus now contains **{diagnostics['replays_analyzed']}** valid public episodes: {diagnostics['wins']} wins / {diagnostics['losses']} losses / {diagnostics['ties']} ties, with **{diagnostics['financial_reconstruction_mismatch_count']}** financial mismatches. The two newly available games added one loss with the same price-realization signature.", "",
        "| Failure cluster | Games |", "|---|---:|",
    ]
    for name, count in sorted(clusters["cluster_counts"].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {name.replace('_', ' ')} | {count} |")
    lines += [
        "", "Bad and good V2 games have nearly identical harvest and sale quantities. The average bad-game milk and strawberry revenues are far lower, so the remaining observational deficit is market realization—not field production.", "",
        "## Editable windows", "", "| Window | Steps | Reason |", "|---|---:|---|",
    ]
    for row in action_values["editable_windows"]:
        lines.append(f"| {row['id']} | {row['steps'][0]}–{row['steps'][1]} | {row['reason']} |")
    lines += ["", "## Single-module ablations", "", "| Candidate | Module | Paired W/L/T | Mean Δ money | P10 Δ | P5 Δ | Override rate | Safety |", "|---|---|---:|---:|---:|---:|---:|---|" ]
    for row in action_values["actions"]:
        safety = f"{row['runtime_failures']}/{row['semantic_failures']}/{row['livestock_losses']}/{row['meaningful_stranding']}"
        lines.append(f"| {row['candidate']} | {row['candidate'][0]} | {row['paired_wins']}/{row['paired_losses']}/{row['paired_ties']} | {row['paired_mean_delta']:+,.0f} | {row['paired_p10_delta']:+,.0f} | {row['paired_p5_delta']:+,.0f} | {row['activation_frequency']:.2%} | {safety} |")
    lines += [
        "", "Safety columns are runtime / semantic / livestock-loss / meaningful-stranding counts.", "",
        "## Counterfactual state replay", "",
        "The checkpoint harness restores environment seed metadata and warms replay-backbone state from prior observations. It reproduced uninterrupted V2 at steps 160, 240, 480, and 600 for every tested episode before any branch was trusted.", "",
        "### Market", "", "| Alternative | Games | W/L/T | Mean final-bank Δ |", "|---|---:|---:|---:|",
    ]
    for name, row in cf_rows(market_cf):
        lines.append(f"| {name} | {row['games']} | {row['wins']}/{row['losses']}/{row['ties']} | {row['average_final_money_delta']:+,.1f} |")
    lines += ["", "The best local perturbation—selling one strawberry batch four steps earlier—was only +95.5 coins and split 2/2. Nearby timing and quantity values were similarly tiny and inconsistent.", "", "### Endgame", "", "| Alternative | Mean final-bank Δ |", "|---|---:|"]
    for name, row in cf_rows(end_cf):
        lines.append(f"| {name} | {row['average_final_money_delta']:+,.1f} |")
    lines += ["", "### Capital", "", "| Alternative | Mean final-bank Δ |", "|---|---:|"]
    for name, row in cf_rows(capital_cf):
        lines.append(f"| {name} | {row['average_final_money_delta']:+,.1f} |")
    lines += [
        "", "## Nazmus safety experiment", "",
        "Raw Nazmus lost four animals in the screen. K3 repair and the narrow shed-cow rescue both eliminated observed losses, but N1/N2 lost roughly 2.2k paired money to V2. The rescue therefore does not expose a stronger safe architecture.", "",
        "## Selection, final confirmation, and attribution", "",
        f"The numerically strongest rejected dynamic candidate was `{best_individual}` at {best_pair['average_money_delta']:+,.0f} paired money—still negative. Because no individual module passed, no combination search was run. Frozen V2 alone was SHA-locked and completed {final_summary['games']} fresh both-seat fixed/natural games with {final_summary['runtime_failures']} runtime failures, {final_summary['semantic_failures']} semantic failures, {final_summary['livestock_losses']} livestock losses, and {final_summary['meaningful_stranding']} meaningful stranding events.", "",
        "Economic attribution is therefore negative: earlier selling loses recovery value; holding inventory consumes shed/feed liquidity and causes safety failures; removing cows loses milk/fertilizer annuity; suppressing terminal seed/hire spend sacrifices harvest/service income; shrinking the wheat wave reduces output. There is no positive V4 delta to attribute.", "",
        "## Promotion gate", "",
        "| Gate | Result |", "|---|---|",
        "| Positive paired mean | FAIL for every module |",
        "| ≥60% decisive wins and +1.5k–2k | FAIL |",
        "| P10/P5 non-regression | FAIL for every module family |",
        "| Safety | PASS for many isolated variants; FAIL for hold-market and raw Nazmus |",
        "| Selection/final unseen | Not opened for rejected candidates |",
        "| Promotion | **No** |", "",
        "## Remaining dynamic headroom and next architecture", "",
        "The measured hand-designed dynamic oracle is noise-level around the opened sale window (under +100 coins locally), while broad online thresholds lose thousands. The bottleneck is not insufficient search over a simple threshold: market action value is strongly state-dependent and correlated with unobserved opponent inventory/future sales. A learned residual action-value model is now justified only as an offline next research architecture, trained on validated checkpoint counterfactuals and still constrained to rare overrides. It should not replace V2 and should not be RL from scratch.", "",
        "V2 remains: `agents/super_replay_v2/super_backbone_v2.py` at `c39d82b4f796271603e32ea8cb4b70261fbbe3d4e17940886caf5f5a6bd9adef`.", "",
        "## Requested completion summary", "",
        f"1. Real V2 episodes analyzed: **{diagnostics['replays_analyzed']}**.",
        "2. Dominant clusters: five market-realization deficits; two endgame economic losses.",
        "3. Editable windows: step 192; 240–264; 336–527; 576–718.",
        "4. Market counterfactual: broad rules regress; best local perturbation +95.5 and 2/2.",
        "5. Endgame counterfactual: every tested change negative (−190.5 to −2,985.8).",
        "6. Capital allocation: seven cows −463.2 locally / −583.6 screen; six cows worse.",
        "7. Crop wave: reduced day-20 wheat purchases lose 679–1,355 paired money.",
        "8. Nazmus rescue: safety restored, but approximately −2.2k paired versus V2.",
        f"9. Strongest individual module: `{best_individual}`, still {best_pair['average_money_delta']:+,.0f}.",
        "10. Strongest combination: none; no individual module qualified for combination.",
        f"11. Override frequency: `{best_individual}` {ablations['candidates'][best_individual]['summary']['average_override_rate']:.2%}; tested range 0.14%–7.81% excluding raw routes.",
        f"12. V2 baseline fresh confirmation: {final_summary['games']} games, average money {final_summary['average_money']:,.0f}.",
        "13. V4 finalist result: no V4 finalist; V2 only.",
        "14. Direct paired delta: every V4 module negative; best −583.6.",
        "15. Natural RNG delta: not opened for rejected modules beyond the development paired panel.",
        "16. Recent elite replay result: no candidate passed the real-loss/development-elite gate.",
        "17. Final unseen result: not opened for rejected V4 candidates; V2 fresh confirmation only.",
        f"18. V2 fresh-confirmation P10 advantage: {final_summary['p10']:+,.1f}.",
        f"19. V2 fresh-confirmation P5 advantage: {final_summary['p5']:+,.1f}.",
        "20. Safety: V2 0 runtime / 0 semantic / 0 livestock / 0 meaningful stranding.",
        "21. Economic attribution: all tested changes destroy sale recovery, annuity, crop output, or terminal service value.",
        "22. V4 promoted: **No**.",
        "23. Research-best source: V2 path and SHA above; no `super_backbone_v4.py` created.",
        "24. Remaining hand-designed dynamic headroom: under about 100 coins in the measured local sale window.",
        "25. Next step: offline learned residual action-value control with rare overrides, not RL from scratch.", "",
    ]
    return "\n".join(lines)


def main():
    diagnostics = load("v4_real_failure_diagnostics.json")
    clusters = load("v4_failure_clusters.json")
    market_cf = load("v4_market_counterfactuals.json")
    end_cf = load("v4_endgame_counterfactuals.json")
    capital_cf = load("v4_capital_counterfactuals.json")
    final = load("v4_final_validation.json")
    screens, agents, paired, games = collect_screens()
    action_values = action_map(agents, paired, games)
    (EXPERIMENTS / "v4_action_value_map.json").write_text(json.dumps(action_values, indent=2, sort_keys=True) + "\n")
    ablations = module_ablations(agents, paired)
    market_events, endgame_events = override_events(games)
    ablations["market_override_events"] = market_events
    ablations["endgame_override_events"] = endgame_events
    (EXPERIMENTS / "v4_module_ablations.json").write_text(json.dumps(ablations, indent=2, sort_keys=True) + "\n")
    selection = selection_payload(ablations)
    (EXPERIMENTS / "v4_selection_results.json").write_text(json.dumps(selection, indent=2, sort_keys=True) + "\n")
    nazmus = nazmus_payload(load("v4_screen_nazmus.json"))
    (EXPERIMENTS / "v4_nazmus_safety.json").write_text(json.dumps(nazmus, indent=2, sort_keys=True) + "\n")
    report_text = report(diagnostics, clusters, action_values, ablations, market_cf, end_cf, capital_cf, final)
    (EXPERIMENTS / "super_replay_backbone_v4_report.md").write_text(report_text)

    log_entry = """
## Super Replay Backbone V4 — bounded dynamic strategy search

- **Preservation:** V2, V1, K3, `submission/main.py`, and `current_best.json` retained their frozen SHA-256 hashes. Nothing was submitted or uploaded.
- **Real evidence:** refreshed deployed V2 submission `55473991` to 78 valid public episodes (71/7), with zero financial mismatches. Five losses are market-realization deficits and two are endgame economic losses; physical production and end inventory remain intact.
- **Counterfactual harness:** environment seed metadata plus warmed backbone state reproduced uninterrupted V2 exactly at checkpoints 160/240/480/600 across all tested loss episodes.
- **Market:** four early-sale thresholds and three hold/recovery policies all regressed. Best broad policy lost 1,053 paired money; hold policies lost 4,572–8,111 and caused livestock/stranding failures. The best local timing perturbation was only +95.5 and split 2/2.
- **Endgame/capital/crop:** all rejected. Seven cows lost 584 paired money; six cows lost 2,134; reduced wheat waves lost 679–1,355; forced day-27 liquidation lost 603; skipped day-29 hires lost 3,621.
- **Nazmus:** raw route lost four animals. K3 and narrow rescue were safe in-screen but both lost about 2.2k paired money to V2, so research stopped.
- **Selection/final:** no module passed development, so no combinations or protected elite final holdout were opened. Frozen V2 completed 40 fresh fixed/natural games with zero runtime, semantic, livestock, or stranding failures.
- **New best:** No. V2 remains `agents/super_replay_v2/super_backbone_v2.py` (`c39d82b4f796271603e32ea8cb4b70261fbbe3d4e17940886caf5f5a6bd9adef`).
- **Next architecture:** if research continues, use an offline learned residual action-value model on validated checkpoints; keep rare overrides and V2 as the base. Do not use policy-from-scratch RL.
""".strip()
    log_path = EXPERIMENTS / "log.md"
    existing = log_path.read_text().rstrip()
    if "## Super Replay Backbone V4 — bounded dynamic strategy search" not in existing:
        log_path.write_text(existing + "\n\n" + log_entry + "\n")
    print(EXPERIMENTS / "super_replay_backbone_v4_report.md")
    print("best rejected", max(paired, key=lambda name: paired[name]["average_money_delta"]), max(row["average_final_money_delta"] for row in market_cf["summary"].values()))


if __name__ == "__main__":
    main()
