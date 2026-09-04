"""Independent, locked final validation for the raw 55899537 route.

This runner intentionally contains no tuning logic.  It verifies the finalist
lock, runs the pre-declared paired panels, and writes the required diagnostic
artifacts in one pass.  Candidate and baseline are loaded fresh for every
game so stateful route executors cannot leak state between conditions.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import statistics
import time

from kaggle_environments import make


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "experiments/raw55899537_final_config.json"
LOCK_PATH = ROOT / "experiments/raw55899537_finalist_lock.json"
AUDIT_PATH = ROOT / "experiments/raw55899537_seed_audit.json"
CANDIDATE = ROOT / "agents/autonomous_next/top50_raw_55899537.py"
BASELINE = ROOT / "agents/top50_distilled/top50_observable_portfolio.py"
V2 = ROOT / "agents/super_replay_v2/super_backbone_v2.py"
SCRIPT = ROOT / "run_raw55899537_final_validation.py"

UNIT_OPS = {
    "NORTH", "SOUTH", "EAST", "WEST", "PASS", "PLANT", "WATER",
    "HARVEST", "FERTILIZE", "DIG", "BUILD_COOP", "BUILD_PASTURE",
    "PICKUP", "DROP", "PLACE", "FEED", "CARE", "COLLECT_FERTILIZER",
}
MARKET_OPS = {"HIRE", "BUY_LAND", "BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL"}
PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
ANIMAL_PRODUCT = {"GOOSE": "EGG", "COW": "MILK", "SHEEP": "WOOL"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def lf_sha256(path: Path) -> str:
    raw = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(raw).hexdigest()


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def percentile(values, q):
    values = sorted(float(x) for x in values)
    if not values:
        return None
    point = (len(values) - 1) * float(q)
    low = int(point)
    high = min(len(values) - 1, low + 1)
    weight = point - low
    return values[low] * (1 - weight) + values[high] * weight


def bootstrap_mean_ci(values, resamples=10000, seed=912559):
    """Deterministic percentile bootstrap; compact and dependency-free."""
    values = [float(x) for x in values]
    if not values:
        return {"mean": None, "low": None, "high": None, "resamples": 0}
    # A local LCG avoids importing random state into agent processes.
    state = int(seed) & 0x7FFFFFFF
    means = []
    n = len(values)
    for _ in range(int(resamples)):
        total = 0.0
        for _ in range(n):
            state = (1103515245 * state + 12345) & 0x7FFFFFFF
            total += values[state % n]
        means.append(total / n)
    return {
        "mean": statistics.fmean(values),
        "low": percentile(means, 0.025),
        "high": percentile(means, 0.975),
        "resamples": int(resamples),
    }


def sign_test(values):
    nonzero = [float(x) for x in values if x != 0]
    positive = sum(x > 0 for x in nonzero)
    negative = sum(x < 0 for x in nonzero)
    n = positive + negative
    if n == 0:
        return {"n_nonzero": 0, "positive": 0, "negative": 0, "two_sided_p": 1.0}
    # Exact two-sided binomial sign-test p-value.
    tail = sum(math.comb(n, k) for k in range(0, min(positive, negative) + 1)) / (2 ** n)
    p = min(1.0, 2.0 * tail)
    return {"n_nonzero": n, "positive": positive, "negative": negative, "two_sided_p": p}


def semantic_validate(obs, action):
    if not isinstance(action, dict) or set(action) != {"farmer", "hands", "market"}:
        raise AssertionError("action must contain farmer/hands/market only")
    if not isinstance(action["farmer"], list) or not action["farmer"] or action["farmer"][0] not in UNIT_OPS:
        raise AssertionError("invalid farmer operation")
    expected_hands = len(obs["farms"][obs["player"]].get("hands", []))
    if not isinstance(action["hands"], list) or len(action["hands"]) != expected_hands:
        raise AssertionError("wrong hand action count")
    for request in action["hands"]:
        if not isinstance(request, list) or not request or request[0] not in UNIT_OPS:
            raise AssertionError("invalid hand operation")
    if not isinstance(action["market"], list) or len(action["market"]) > 10:
        raise AssertionError("invalid market queue")
    for order in action["market"]:
        if not isinstance(order, list) or not order or order[0] not in MARKET_OPS:
            raise AssertionError("invalid market operation")
        if order[0] in {"HIRE", "BUY_LAND"}:
            if len(order) != 1:
                raise AssertionError("wrong zero-argument market order")
        elif len(order) != 3 or not isinstance(order[2], int) or order[2] <= 0:
            raise AssertionError("wrong quantity market order")


def load_agent(path: Path):
    name = "final558_" + hashlib.sha256(str(path).encode()).hexdigest()[:16]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.agent


def farm_counts(farm):
    crops, animals, structures = Counter(), Counter(), Counter()
    productive = weeds = 0
    for row in farm.get("tiles", []):
        for tile in row:
            if not isinstance(tile, dict):
                continue
            kind = tile.get("kind")
            if kind == "PLANT":
                crops[tile.get("crop")] += 1
                productive += 1
            elif kind in {"COOP", "PASTURE"}:
                structures[kind] += 1
                if tile.get("animal"):
                    animals[tile["animal"]] += 1
                    productive += 1
            elif kind == "WEED":
                weeds += 1
    return {
        "crops": dict(sorted(crops.items())),
        "animals": dict(sorted(animals.items())),
        "structures": dict(sorted(structures.items())),
        "productive": productive,
        "weeds": weeds,
    }


def animal_escapes(states, seat):
    escapes = []
    for index in range(1, len(states)):
        before = states[index - 1][seat].observation["farms"][seat]["tiles"]
        after = states[index][seat].observation["farms"][seat]["tiles"]
        for y, row in enumerate(before):
            for x, old in enumerate(row):
                old_animal = old.get("animal") if isinstance(old, dict) else None
                new = after[y][x]
                new_animal = new.get("animal") if isinstance(new, dict) else None
                if old_animal and not new_animal and isinstance(new, dict) and new.get("kind") in {"COOP", "PASTURE"}:
                    escapes.append({"step": index - 1, "animal": old_animal, "position": [x, y]})
    return escapes


def terminal_value(state, seat):
    obs = state[seat].observation
    farm = obs["farms"][seat]
    private = obs["private"]
    prices = obs.get("market", {}).get("prices", {})
    quantities = Counter(private.get("shed", {}))
    for inventory in private.get("inventories", []):
        quantities.update(inventory)
    stranded = {item: int(quantities[item]) for item in PRODUCTS if quantities[item]}
    value = sum(int(quantities[item]) * float(prices.get(item, 1)) for item in PRODUCTS)
    field = Counter()
    for row in farm.get("tiles", []):
        for tile in row:
            if not isinstance(tile, dict):
                continue
            if tile.get("kind") == "PLANT" and tile.get("yield_units", 0) > 0:
                item = tile.get("crop")
                field[item] += int(tile.get("yield_units", 0))
                value += int(tile.get("yield_units", 0)) * float(prices.get(item, 1))
            elif tile.get("animal") and tile.get("yield_units", 0) > 0:
                item = ANIMAL_PRODUCT.get(tile.get("animal"))
                if item:
                    field[item] += int(tile.get("yield_units", 0))
                    value += int(tile.get("yield_units", 0)) * float(prices.get(item, 1))
    return {"units": int(sum(stranded.values()) + sum(field.values())), "value": float(value), "shed_inventory": stranded, "field_inventory": dict(field)}


def route_telemetry(agent):
    raw = deepcopy(getattr(agent, "telemetry", {}))
    requests = int(raw.get("all_route_requests", 0))
    matches = int(raw.get("all_route_matches", 0))
    repairs = raw.get("repairs", {}) or {}
    return {
        "route_requests": requests,
        "route_matches": matches,
        "route_realization_rate": matches / requests if requests else 0.0,
        "fallback_actions": int((raw.get("mode_steps", {}) or {}).get("FALLBACK", 0)),
        "repair_actions": int(sum(int(v) for v in repairs.values())),
        "repair_breakdown": {str(k): int(v) for k, v in repairs.items()},
        "repair_success": int(raw.get("repair_success", 0)),
        "repair_abort": int(raw.get("repair_abort", 0)),
        "critical_confirmed": int(raw.get("critical_confirmed", 0)),
        "critical_failed": int(raw.get("critical_failed", 0)),
        "hire_suppressed": int(raw.get("hire_suppressed", 0)),
        "semantic_sanitizations": int(raw.get("semantic_sanitizations", 0)),
        "worker_rematches": int(raw.get("worker_rematches", 0)),
        "position_error_sum": float(raw.get("position_error_sum", 0)),
        "position_error_observations": int(raw.get("position_error_observations", 0)),
        "mode_steps": {str(k): int(v) for k, v in (raw.get("mode_steps", {}) or {}).items()},
    }


def milestone_summary(states, seat):
    first_land = second_land = None
    previous_quads = 1
    peak_hands = peak_animals = 0
    first_animals = None
    for state in states:
        obs = state[seat].observation
        farm = obs["farms"][seat]
        step = int(obs.get("step", 0))
        quads = len(farm.get("unlocked_quadrants", []))
        if quads > previous_quads:
            if first_land is None:
                first_land = step
            elif second_land is None:
                second_land = step
            previous_quads = quads
        counts = farm_counts(farm)
        animals = sum(counts["animals"].values())
        if first_animals is None and animals:
            first_animals = {"step": step, "animals": counts["animals"]}
        peak_hands = max(peak_hands, len(farm.get("hands", [])))
        peak_animals = max(peak_animals, animals)
    final_farm = states[-1][seat].observation["farms"][seat]
    final_counts = farm_counts(final_farm)
    return {
        "first_land_step": first_land,
        "second_land_step": second_land,
        "peak_hands": peak_hands,
        "peak_animals": peak_animals,
        "first_animals": first_animals,
        "final_quadrants": list(final_farm.get("unlocked_quadrants", [])),
        "final_counts": final_counts,
    }


def daily_bank(states, seat):
    by_day = {}
    for state in states:
        obs = state[seat].observation
        day = int(obs.get("day", 0))
        by_day.setdefault(day, []).append(float(obs["farms"][seat]["money"]))
    return [{"day": day, "start": vals[0], "end": vals[-1], "mean": statistics.fmean(vals)} for day, vals in sorted(by_day.items())]


def economic_summary(replay, seat):
    """Use the project's observed-bank ledger, retaining only compact totals."""
    try:
        from mine_top50_strategies import _economic_timeline
        timeline, reconciliation = _economic_timeline(replay, seat)
    except Exception as exc:
        return {"error": repr(exc), "reconciliation_events": 0}
    revenue = Counter(); sales = Counter(); harvest = Counter(); seed_spend = Counter(); product_spend = Counter(); animal_spend = Counter(); sale_days = defaultdict(list); avg_prices = defaultdict(list)
    land_spend = labor_spend = 0.0
    daily = []
    for row in timeline:
        revenue.update(row.get("sale_revenue", {})); sales.update(row.get("sale_quantity", {})); harvest.update(row.get("harvest_quantity", {}))
        seed_spend.update(row.get("seed_spend", {})); product_spend.update(row.get("product_spend", {})); animal_spend.update(row.get("animal_spend", {}))
        land_spend += float(row.get("land_spend", 0)); labor_spend += float(row.get("labor_spend", 0))
        for item, quantity in row.get("sale_quantity", {}).items():
            sale_days[item].extend([int(row["day"])] * int(quantity))
        for item, price in row.get("sale_average_prices", {}).items():
            avg_prices[item].append(float(price))
        daily.append({"day": int(row["day"]), "revenue": float(row.get("total_sale_revenue", 0)), "spend": float(row.get("total_spend", 0)), "sales": dict(row.get("sale_quantity", {}))})
    return {
        "revenue": dict(revenue), "sales": dict(sales), "harvest": dict(harvest),
        "seed_spend": dict(seed_spend), "product_spend": dict(product_spend), "animal_spend": dict(animal_spend),
        "land_spend": land_spend, "labor_spend": labor_spend,
        "sale_day_weighted": {item: statistics.fmean(days) for item, days in sale_days.items() if days},
        "sale_average_prices": {item: statistics.fmean(values) for item, values in avg_prices.items() if values},
        "daily": daily, "reconciliation_events": len(reconciliation),
    }


def run_game(job):
    """Run one fresh game and return compact candidate/baseline diagnostics."""
    variant, agent_path, opponent_name, opponent_path, seed, seat, panel, configuration = job
    started = time.perf_counter()
    agent = load_agent(Path(agent_path))
    opponent = load_agent(Path(opponent_path)) if opponent_path not in {"starter", "random", "pass"} else opponent_path
    actions = []
    semantic_failures = []
    exceptions = []

    def checked(obs):
        try:
            action = agent(obs)
        except Exception as exc:
            exceptions.append({"step": int(obs.get("step", -1)), "error": repr(exc)})
            raise
        actions.append(deepcopy(action))
        try:
            semantic_validate(obs, action)
        except Exception as exc:
            semantic_failures.append({"step": int(obs.get("step", -1)), "error": repr(exc), "action": deepcopy(action)})
        return action

    pair = [opponent, opponent]
    pair[seat] = checked
    config = dict(configuration or {})
    config.setdefault("episodeSteps", 720)
    config["seed"] = int(seed)
    runtime_error = None
    env = None
    try:
        env = make("kaggriculture", configuration=config, debug=False)
        env.run(pair)
    except Exception as exc:
        runtime_error = repr(exc)
    elapsed = time.perf_counter() - started
    if env is None or len(getattr(env, "steps", [])) != 720:
        return {
            "variant": variant, "panel": panel, "opponent": opponent_name, "seed": int(seed), "seat": int(seat),
            "runtime_error": runtime_error or f"steps={len(getattr(env, 'steps', [])) if env else 0}",
            "semantic_failures": semantic_failures, "exceptions": exceptions, "actions": len(actions), "elapsed_s": elapsed,
        }
    states = env.steps
    final = states[-1]
    own = final[seat]
    other = final[1 - seat]
    replay = env.toJSON()
    telemetry = route_telemetry(agent)
    terminal = terminal_value(final, seat)
    escapes = animal_escapes(states, seat)
    milestones = milestone_summary(states, seat)
    return {
        "variant": variant, "panel": panel, "opponent": opponent_name, "seed": int(seed), "seat": int(seat),
        "runtime_error": None, "semantic_failures": semantic_failures, "exceptions": exceptions,
        "actions": len(actions), "action_hash": digest(actions), "elapsed_s": elapsed,
        "own_money": float(own.reward), "opponent_money": float(other.reward),
        "advantage": float(own.reward) - float(other.reward),
        "terminal": terminal, "livestock_escapes": escapes, "milestones": milestones,
        "daily_bank": daily_bank(states, seat), "telemetry": telemetry,
        "economics": economic_summary(replay, seat),
    }


def pair_key(row):
    return (row["panel"], row["opponent"], int(row["seed"]), int(row["seat"]))


def make_jobs(config):
    opponents = config["opponents"]
    jobs = []
    def add_panel(panel, seeds, opponent_names, cfg_by_name=None):
        for opponent_name in opponent_names:
            opponent_path = str(ROOT / opponents[opponent_name])
            for seed in seeds:
                condition_cfg = dict((cfg_by_name or {}).get(opponent_name, {"episodeSteps": 720}))
                for seat in (0, 1):
                    for variant, path in (("candidate", CANDIDATE), ("baseline", BASELINE)):
                        jobs.append((variant, str(path), opponent_name, opponent_path, int(seed), seat, panel, condition_cfg))
    add_panel("direct_currentbest", config["primary_direct_currentbest_seeds"], ["current_best"])
    add_panel("top3", config["top3_seeds"], ["tetsuya", "crop_dusta", "oceanmix"])
    add_panel("historical_strong", config["historical_strong_seeds"], ["v2", "k3", "nazmus", "router_hands12", "victor"])
    # Natural/fresh games use fixed seeds but no replay-derived state or shop schedule.
    add_panel("natural_rng", config["natural_rng_seeds"], ["current_best"])
    for stress in config["stress"]:
        add_panel("stress_" + stress["name"], stress["seeds"], [config["stress_opponent"]], {config["stress_opponent"]: stress["configuration"]})
    return jobs


def summarize_pairs(rows):
    by_key = defaultdict(dict)
    for row in rows:
        by_key[pair_key(row)][row["variant"]] = row
    paired = []
    for key, values in sorted(by_key.items()):
        if "candidate" not in values or "baseline" not in values:
            continue
        c, b = values["candidate"], values["baseline"]
        paired.append({
            "panel": key[0], "opponent": key[1], "seed": key[2], "seat": key[3],
            "candidate_money": c.get("own_money"), "baseline_money": b.get("own_money"),
            "own_money_delta": (c.get("own_money") - b.get("own_money")) if c.get("own_money") is not None and b.get("own_money") is not None else None,
            "candidate_advantage": c.get("advantage"), "baseline_advantage": b.get("advantage"),
            "advantage_delta": (c.get("advantage") - b.get("advantage")) if c.get("advantage") is not None and b.get("advantage") is not None else None,
            "opponent_money_delta": (c.get("opponent_money") - b.get("opponent_money")) if c.get("opponent_money") is not None and b.get("opponent_money") is not None else None,
            "candidate_runtime_error": c.get("runtime_error"), "baseline_runtime_error": b.get("runtime_error"),
            "candidate_semantic_failures": len(c.get("semantic_failures", [])), "baseline_semantic_failures": len(b.get("semantic_failures", [])),
            "candidate_escapes": len(c.get("livestock_escapes", [])), "baseline_escapes": len(b.get("livestock_escapes", [])),
            "candidate_stranded_value": c.get("terminal", {}).get("value"), "baseline_stranded_value": b.get("terminal", {}).get("value"),
            "candidate_route_realization": c.get("telemetry", {}).get("route_realization_rate"), "baseline_route_realization": b.get("telemetry", {}).get("route_realization_rate"),
            "candidate_row": c, "baseline_row": b,
        })
    return paired


def aggregate(pairs, panel=None, opponent=None):
    selected = [p for p in pairs if (panel is None or p["panel"] == panel) and (opponent is None or p["opponent"] == opponent) and p["own_money_delta"] is not None]
    own = [p["own_money_delta"] for p in selected]
    adv = [p["advantage_delta"] for p in selected if p["advantage_delta"] is not None]
    cwin = sum((p["candidate_advantage"] or 0) > 0 for p in selected)
    closs = sum((p["candidate_advantage"] or 0) < 0 for p in selected)
    ctie = len(selected) - cwin - closs
    return {
        "games": len(selected), "wins": cwin, "losses": closs, "ties": ctie,
        "decisive_win_rate": cwin / (cwin + closs) if cwin + closs else None,
        "candidate_mean_money": statistics.fmean(p["candidate_money"] for p in selected) if selected else None,
        "baseline_mean_money": statistics.fmean(p["baseline_money"] for p in selected) if selected else None,
        "own_money_delta": {"mean": statistics.fmean(own), "median": statistics.median(own), "p25": percentile(own, .25), "p10": percentile(own, .10), "p5": percentile(own, .05), "worst": min(own), "negative_rate": sum(x < 0 for x in own) / len(own), "below_minus_1000_rate": sum(x < -1000 for x in own) / len(own), "below_minus_3000_rate": sum(x < -3000 for x in own) / len(own), "below_minus_5000_rate": sum(x < -5000 for x in own) / len(own)},
        "advantage_delta": {"mean": statistics.fmean(adv), "median": statistics.median(adv), "p25": percentile(adv, .25), "p10": percentile(adv, .10), "p5": percentile(adv, .05), "worst": min(adv), "negative_rate": sum(x < 0 for x in adv) / len(adv)},
        "runtime_failures": sum(bool(p["candidate_runtime_error"] or p["baseline_runtime_error"]) for p in selected),
        "semantic_failures": sum(p["candidate_semantic_failures"] + p["baseline_semantic_failures"] for p in selected),
        "candidate_livestock_escapes": sum(p["candidate_escapes"] for p in selected),
        "baseline_livestock_escapes": sum(p["baseline_escapes"] for p in selected),
        "candidate_stranded_value_mean": statistics.fmean(p["candidate_stranded_value"] or 0 for p in selected) if selected else None,
        "baseline_stranded_value_mean": statistics.fmean(p["baseline_stranded_value"] or 0 for p in selected) if selected else None,
        "candidate_route_realization_mean": statistics.fmean(p["candidate_route_realization"] or 0 for p in selected) if selected else None,
        "baseline_route_realization_mean": statistics.fmean(p["baseline_route_realization"] or 0 for p in selected) if selected else None,
    }


def combine_economics(pairs):
    result = {"candidate": {"revenue": Counter(), "sales": Counter(), "harvest": Counter(), "seed_spend": Counter(), "product_spend": Counter(), "animal_spend": Counter(), "land_spend": 0.0, "labor_spend": 0.0}, "baseline": {"revenue": Counter(), "sales": Counter(), "harvest": Counter(), "seed_spend": Counter(), "product_spend": Counter(), "animal_spend": Counter(), "land_spend": 0.0, "labor_spend": 0.0}}
    for p in pairs:
        for role, row_key in (("candidate", "candidate_row"), ("baseline", "baseline_row")):
            econ = p[row_key].get("economics", {})
            if econ.get("error"): continue
            for field in ("revenue", "sales", "harvest", "seed_spend", "product_spend", "animal_spend"):
                result[role][field].update(econ.get(field, {}))
            result[role]["land_spend"] += float(econ.get("land_spend", 0)); result[role]["labor_spend"] += float(econ.get("labor_spend", 0))
    for role in result:
        for field in ("revenue", "sales", "harvest", "seed_spend", "product_spend", "animal_spend"):
            result[role][field] = dict(result[role][field])
    result["delta_candidate_minus_baseline"] = {}
    for field in ("revenue", "sales", "harvest", "seed_spend", "product_spend", "animal_spend"):
        keys = set(result["candidate"][field]) | set(result["baseline"][field])
        result["delta_candidate_minus_baseline"][field] = {k: result["candidate"][field].get(k, 0) - result["baseline"][field].get(k, 0) for k in sorted(keys)}
    result["delta_candidate_minus_baseline"]["land_spend"] = result["candidate"]["land_spend"] - result["baseline"]["land_spend"]
    result["delta_candidate_minus_baseline"]["labor_spend"] = result["candidate"]["labor_spend"] - result["baseline"]["labor_spend"]
    return result


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=lambda x: float(x)) + "\n", encoding="utf-8")


def main():
    config = json.loads(CONFIG_PATH.read_text())
    lock = json.loads(LOCK_PATH.read_text())
    if sha256(CANDIDATE) != lock["candidate_raw_sha256"] or lf_sha256(CANDIDATE) != lock["candidate_lf_sha256"]:
        raise SystemExit("locked candidate hash mismatch")
    if sha256(BASELINE) != lock["baseline_raw_sha256"] or lf_sha256(BASELINE) != lock["baseline_lf_sha256"]:
        raise SystemExit("locked baseline hash mismatch")
    if sha256(V2) != lock["v2_sha256"]:
        raise SystemExit("V2 reference hash mismatch")
    if sha256(SCRIPT) != lock["validation_code_sha256"]:
        raise SystemExit("validation code changed after finalist lock")
    if sha256(CONFIG_PATH) != lock["evaluation_config_sha256"]:
        raise SystemExit("evaluation config changed after finalist lock")

    jobs = make_jobs(config)
    print(f"Running {len(jobs)} locked games with {config['workers']} workers", flush=True)
    rows = []
    with ProcessPoolExecutor(max_workers=int(config["workers"])) as pool:
        for index, row in enumerate(pool.map(run_game, jobs), 1):
            rows.append(row)
            if index % 20 == 0 or index == len(jobs):
                print(f"{index}/{len(jobs)} completed", flush=True)
    pairs = summarize_pairs(rows)
    valid_pairs = [p for p in pairs if p["own_money_delta"] is not None]
    summaries = {"overall": aggregate(valid_pairs)}
    panels = sorted({p["panel"] for p in valid_pairs})
    opponents = sorted({p["opponent"] for p in valid_pairs})
    summaries["by_panel"] = {panel: aggregate(valid_pairs, panel=panel) for panel in panels}
    summaries["by_opponent"] = {opp: aggregate(valid_pairs, opponent=opp) for opp in opponents}
    summaries["by_panel_opponent"] = {f"{panel}|{opp}": aggregate(valid_pairs, panel=panel, opponent=opp) for panel in panels for opp in opponents if any(p["panel"] == panel and p["opponent"] == opp for p in valid_pairs)}
    # Keep the final paired artifact inspectable without duplicating the full raw rows.
    compact_pairs = []
    for p in valid_pairs:
        q = dict(p)
        q.pop("candidate_row", None); q.pop("baseline_row", None)
        compact_pairs.append(q)
    write_json(ROOT / "experiments/raw55899537_paired_results.json", {"schema_version": 1, "pairs": compact_pairs, "summary": summaries["overall"]})
    write_json(ROOT / "experiments/raw55899537_final_validation.json", {"schema_version": 1, "lock_sha256": sha256(LOCK_PATH), "config_sha256": sha256(CONFIG_PATH), "games": len(rows), "paired_conditions": len(valid_pairs), "summary": summaries, "rows": rows})
    write_json(ROOT / "experiments/raw55899537_h2h_currentbest.json", {"schema_version": 1, "seeds": config["primary_direct_currentbest_seeds"], "summary": summaries["by_panel"].get("direct_currentbest", {}), "pairs": [p for p in compact_pairs if p["panel"] == "direct_currentbest"]})
    write_json(ROOT / "experiments/raw55899537_top3_results.json", {"schema_version": 1, "seeds": config["top3_seeds"], "summary": {o: summaries["by_panel_opponent"].get(f"top3|{o}", {}) for o in ("tetsuya", "crop_dusta", "oceanmix")}, "pairs": [p for p in compact_pairs if p["panel"] == "top3"]})
    write_json(ROOT / "experiments/raw55899537_natural_rng.json", {"schema_version": 1, "seeds": config["natural_rng_seeds"], "summary": summaries["by_panel"].get("natural_rng", {}), "pairs": [p for p in compact_pairs if p["panel"] == "natural_rng"]})
    # Route stability and safety are summarized for every panel and opponent.
    stability_rows = []
    safety_rows = []
    for row in rows:
        stability_rows.append({"variant": row["variant"], "panel": row["panel"], "opponent": row["opponent"], "seed": row["seed"], "seat": row["seat"], "actions": row.get("actions", 0), "action_hash": row.get("action_hash"), "telemetry": row.get("telemetry", {}), "milestones": row.get("milestones", {}), "runtime_error": row.get("runtime_error")})
        safety_rows.append({"variant": row["variant"], "panel": row["panel"], "opponent": row["opponent"], "seed": row["seed"], "seat": row["seat"], "runtime_error": row.get("runtime_error"), "semantic_failures": row.get("semantic_failures", []), "livestock_escapes": row.get("livestock_escapes", []), "stranded": row.get("terminal", {}), "critical_failed": row.get("telemetry", {}).get("critical_failed", 0), "repair_abort": row.get("telemetry", {}).get("repair_abort", 0)})
    write_json(ROOT / "experiments/raw55899537_route_stability.json", {"schema_version": 1, "rows": stability_rows, "summary": {"games": len(stability_rows), "candidate_route_realization": summaries["overall"].get("candidate_route_realization_mean"), "baseline_route_realization": summaries["overall"].get("baseline_route_realization_mean")}})
    write_json(ROOT / "experiments/raw55899537_safety.json", {"schema_version": 1, "rows": safety_rows, "summary": {"runtime_failures": sum(bool(r.get("runtime_error")) for r in rows), "semantic_failures": sum(len(r.get("semantic_failures", [])) for r in rows), "candidate_livestock_escapes": sum(len(r.get("livestock_escapes", [])) for r in rows if r["variant"] == "candidate"), "candidate_mean_stranded_value": summaries["overall"].get("candidate_stranded_value_mean"), "candidate_critical_failures": sum(int(r.get("telemetry", {}).get("critical_failed", 0)) for r in rows if r["variant"] == "candidate")}})
    econ_pairs = [p for p in valid_pairs if p["panel"] != "natural_rng"]
    write_json(ROOT / "experiments/raw55899537_final_economic_attribution.json", {"schema_version": 1, "pair_count": len(econ_pairs), "scope": "all fixed-seed paired panels excluding natural_rng", "attribution": combine_economics(econ_pairs)})
    externality = []
    for p in compact_pairs:
        externality.append({"panel": p["panel"], "opponent": p["opponent"], "seed": p["seed"], "seat": p["seat"], "candidate_own_delta": p["own_money_delta"], "opponent_money_delta": p["opponent_money_delta"], "net_advantage_delta": p["advantage_delta"]})
    write_json(ROOT / "experiments/raw55899537_market_externality.json", {"schema_version": 1, "rows": externality, "summary": {"candidate_own_delta_mean": statistics.fmean(x["candidate_own_delta"] for x in externality), "opponent_delta_mean": statistics.fmean(x["opponent_money_delta"] for x in externality), "net_advantage_delta_mean": statistics.fmean(x["net_advantage_delta"] for x in externality)}})
    own_delta = [p["own_money_delta"] for p in compact_pairs]
    adv_delta = [p["advantage_delta"] for p in compact_pairs]
    stats = {"own_money_delta": bootstrap_mean_ci(own_delta, config["bootstrap_resamples"], 912559), "advantage_delta": bootstrap_mean_ci(adv_delta, config["bootstrap_resamples"], 912560), "decisive_win_rate": bootstrap_mean_ci([1.0 if p["candidate_advantage"] > 0 else 0.0 for p in compact_pairs if p["candidate_advantage"] != 0], config["bootstrap_resamples"], 912561), "sign_test_own_money": sign_test(own_delta), "sign_test_advantage": sign_test(adv_delta), "sample_size": len(compact_pairs)}
    write_json(ROOT / "experiments/raw55899537_statistical_analysis.json", stats)
    # Manifest records exact counts and split definitions; reports consume this file.
    manifest = {"schema_version": 1, "candidate": str(CANDIDATE.relative_to(ROOT)), "baseline": str(BASELINE.relative_to(ROOT)), "v2": str(V2.relative_to(ROOT)), "lock_sha256": sha256(LOCK_PATH), "config_sha256": sha256(CONFIG_PATH), "seed_audit_sha256": sha256(AUDIT_PATH), "total_games": len(rows), "paired_conditions": len(compact_pairs), "panels": panels, "opponents": opponents, "seats": [0, 1], "fresh_seed_count": len(set(int(x["seed"]) for x in compact_pairs)), "summary": summaries}
    write_json(ROOT / "experiments/raw55899537_final_manifest.json", manifest)
    # Worst-case artifact is structured first; the markdown companion is emitted below.
    worst = sorted(compact_pairs, key=lambda p: (p["own_money_delta"], p["advantage_delta"]))[:10]
    best = sorted(compact_pairs, key=lambda p: (p["own_money_delta"], p["advantage_delta"]), reverse=True)[:5]
    write_json(ROOT / "experiments/raw55899537_worst_case_rows.json", {"worst": worst, "largest_wins": best})
    print(json.dumps({"games": len(rows), "paired": len(compact_pairs), "overall": summaries["overall"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
