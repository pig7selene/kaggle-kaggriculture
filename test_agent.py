"""Run the local Kaggriculture baseline through two full-season smoke tests.

Usage:
    python test_agent.py
"""

from collections import Counter

try:
    from kaggle_environments import make
except ImportError as exc:  # pragma: no cover - only used on an unprepared machine
    raise SystemExit(
        "Missing dependency. Install it with: pip install -U kaggle-environments"
    ) from exc

from main import agent


EPISODE_STEPS = 720
UNIT_OPS = {
    "NORTH": 1,
    "SOUTH": 1,
    "EAST": 1,
    "WEST": 1,
    "PASS": 1,
    "PLANT": 2,
    "WATER": 1,
    "HARVEST": 1,
    "DIG": 1,
}
MARKET_OPS = {"BUY_SEED", "SELL"}


def _validate_action(obs, action):
    """Reject malformed or inapplicable actions emitted by our baseline."""
    assert isinstance(action, dict), "agent action must be a dict"
    assert set(action) == {"farmer", "hands", "market"}, (
        "action must contain exactly farmer, hands, and market"
    )

    farmer = action["farmer"]
    assert isinstance(farmer, list) and farmer, "farmer action must be a list"
    assert farmer[0] in UNIT_OPS, f"unsupported farmer action: {farmer}"
    assert len(farmer) == UNIT_OPS[farmer[0]], f"wrong action arity: {farmer}"

    player = obs["player"]
    me = obs["farms"][player]
    assert action["hands"] == [], "baseline must not emit hand actions"
    assert len(action["hands"]) == len(me["hands"]), (
        "hand actions must correspond exactly to hired hands"
    )

    market = action["market"]
    assert isinstance(market, list), "market action must be a list"
    assert len(market) <= 10, "too many market orders"
    seen_items = Counter()
    for order in market:
        assert isinstance(order, list) and len(order) == 3, (
            f"malformed market order: {order}"
        )
        op, item, count = order
        assert op in MARKET_OPS, f"unsupported market order: {order}"
        assert item == "CARROT", f"unexpected market item: {order}"
        assert isinstance(count, int) and count > 0, f"invalid quantity: {order}"
        seen_items[(op, item)] += count

    seeds = obs["private"]["seeds"].get("CARROT", 0)
    shed = obs["private"]["shed"].get("CARROT", 0)
    assert seen_items[("SELL", "CARROT")] <= shed, "cannot sell missing carrots"
    assert seen_items[("BUY_SEED", "CARROT")] * 20 <= me["money"], (
        "cannot afford requested seeds"
    )

    x, y = me["farmer"]
    tile = me["tiles"][y][x]
    op = farmer[0]
    if op == "PLANT":
        assert tile is None and seeds > 0, "PLANT must target empty owned land"
        assert farmer[1] == "CARROT", "baseline only plants carrots"
    elif op == "WATER":
        assert isinstance(tile, dict) and tile.get("kind") == "PLANT", (
            "WATER must target a plant"
        )
        assert not tile.get("watered_today", False), "plant is already watered"
    elif op == "HARVEST":
        assert isinstance(tile, dict) and tile.get("kind") == "PLANT", (
            "HARVEST must target a plant"
        )
        assert tile.get("yield_units", 0) > 0, "nothing is ready to harvest"
        assert obs["day"] - tile["planted_day"] >= 2, "crop is immature"
    elif op == "DIG":
        assert isinstance(tile, dict) and tile.get("kind") == "WEED", (
            "DIG must target a weed"
        )
    elif op in {"NORTH", "SOUTH", "EAST", "WEST"}:
        dx = {"WEST": -1, "EAST": 1}.get(op, 0)
        dy = {"NORTH": -1, "SOUTH": 1}.get(op, 0)
        size = len(me["tiles"])
        assert 0 <= x + dx < size and 0 <= y + dy < size, "move leaves board"


def _run_game(opponent, seed):
    counts = Counter()

    def checked_agent(obs):
        action = agent(obs)
        _validate_action(obs, action)
        counts[action["farmer"][0]] += 1
        for order in action["market"]:
            counts[order[0]] += 1
        return action

    env = make(
        "kaggriculture",
        configuration={"episodeSteps": EPISODE_STEPS, "seed": seed},
        debug=True,
    )
    env.run([checked_agent, opponent])

    assert len(env.steps) == EPISODE_STEPS, (
        f"expected {EPISODE_STEPS} recorded turns, got {len(env.steps)}"
    )
    final = env.steps[-1]
    statuses = [state.status for state in final]
    assert statuses == ["DONE", "DONE"], f"unexpected final statuses: {statuses}"
    for required in ("PLANT", "WATER", "HARVEST", "SELL"):
        assert counts[required] > 0, f"baseline never performed {required}"

    rewards = [state.reward for state in final]
    print(
        f"PASS vs {opponent:<7} | turns={len(env.steps)} "
        f"| status={statuses[0]} | rewards={rewards}"
    )


def main():
    _run_game("random", seed=101)
    _run_game("starter", seed=202)
    print("All full-season baseline tests passed.")


if __name__ == "__main__":
    main()
