"""Validate the standalone submission in three full 720-turn games."""

from collections import Counter, defaultdict

from kaggle_environments import make

from benchmark import EPISODE_STEPS, ROOT, _load_agent


SUBMISSION_PATH = ROOT / "submission" / "main.py"
REFERENCE_PATH = ROOT / "agents" / "melon_scale_12.py"
CARROT_PATH = ROOT / "agents" / "carrot_scale_20.py"
TARGET_PLOTS = {
    (4, 4), (3, 4), (2, 4), (2, 3),
    (3, 3), (4, 3), (4, 2), (3, 2),
    (2, 2), (1, 2), (1, 3), (1, 4),
}
UNIT_ARITY = {
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


def _fib(index):
    a, b = 1, 1
    for _ in range(index):
        a, b = b, a + b
    return a


def _validate_unit_action(obs, position, action):
    assert isinstance(action, list) and action, f"malformed unit action: {action}"
    op = action[0]
    assert op in UNIT_ARITY, f"forbidden or unknown unit action: {action}"
    assert len(action) == UNIT_ARITY[op], f"wrong unit-action arity: {action}"

    me = obs["farms"][obs["player"]]
    x, y = position
    tile = me["tiles"][y][x]
    if op in {"NORTH", "SOUTH", "EAST", "WEST"}:
        dx = {"WEST": -1, "EAST": 1}.get(op, 0)
        dy = {"NORTH": -1, "SOUTH": 1}.get(op, 0)
        size = len(me["tiles"])
        assert 0 <= x + dx < size and 0 <= y + dy < size, "move leaves board"
    elif op == "PLANT":
        assert (x, y) in TARGET_PLOTS, "plant action is outside the 12 target plots"
        assert tile is None, "PLANT must target empty unlocked land"
        assert action[1] == "MELON", "submission may only plant melons"
        assert obs["hour"] < 23, "submission must not plant on the final daily turn"
    elif op == "WATER":
        assert isinstance(tile, dict) and tile.get("kind") == "PLANT"
        assert tile.get("crop") == "MELON", "submission may only tend melons"
        assert not tile.get("watered_today", False), "plant was already watered"
    elif op == "HARVEST":
        assert isinstance(tile, dict) and tile.get("kind") == "PLANT"
        assert tile.get("crop") == "MELON", "submission may only harvest melons"
        assert obs["day"] - tile["planted_day"] >= 10, "melon is immature"
        assert tile.get("yield_units", 0) > 0, "melon has no harvestable yield"
    elif op == "DIG":
        assert isinstance(tile, dict) and tile.get("kind") == "WEED"


def _validate_action(obs, action):
    assert isinstance(action, dict)
    assert set(action) == {"farmer", "hands", "market"}
    me = obs["farms"][obs["player"]]
    positions = [me["farmer"], *me["hands"]]
    unit_actions = [action["farmer"], *action["hands"]]
    assert len(action["hands"]) == len(me["hands"]), "one action is required per hand"
    assert len(unit_actions) == len(positions)

    for position, unit_action in zip(positions, unit_actions):
        _validate_unit_action(obs, position, unit_action)
    plants_requested = sum(unit_action[0] == "PLANT" for unit_action in unit_actions)
    assert plants_requested <= obs["private"]["seeds"].get("MELON", 0)

    market = action["market"]
    assert isinstance(market, list) and len(market) <= 10
    budget = float(me["money"])
    hires = me.get("hires_today", 0)
    melons_to_sell = 0
    for order in market:
        assert isinstance(order, list) and order
        if order[0] == "SELL":
            assert len(order) == 3 and order[1] == "MELON"
            assert isinstance(order[2], int) and order[2] > 0
            melons_to_sell += order[2]
        elif order[0] == "BUY_SEED":
            assert len(order) == 3 and order[1] == "MELON"
            assert isinstance(order[2], int) and order[2] > 0
            cost = 80 * order[2]
            assert budget >= cost, "seed order exceeds available capital"
            budget -= cost
        elif order[0] == "HIRE":
            assert len(order) == 1
            cost = _fib(hires)
            assert budget >= cost, "hire order exceeds available capital"
            budget -= cost
            hires += 1
        else:
            raise AssertionError(f"forbidden or unknown market action: {order}")
    assert melons_to_sell <= obs["private"]["shed"].get("MELON", 0)
    assert hires <= 2, "submission must target exactly two hands"


def _run_checked_game(opponent, label, seed):
    submission = _load_agent(str(SUBMISSION_PATH))
    reference = _load_agent(str(REFERENCE_PATH))
    operation_counts = Counter()
    hires_by_day = defaultdict(int)
    planted_positions = set()

    def checked_agent(obs):
        action = submission(obs)
        assert action == reference(obs), "standalone action diverged from melon_scale_12"
        _validate_action(obs, action)
        me = obs["farms"][obs["player"]]
        positions = [me["farmer"], *me["hands"]]
        unit_actions = [action["farmer"], *action["hands"]]
        for position, unit_action in zip(positions, unit_actions):
            operation_counts[unit_action[0]] += 1
            if unit_action[0] == "PLANT":
                planted_positions.add(tuple(position))
        for order in action["market"]:
            operation_counts[order[0]] += 1
            if order[0] == "HIRE":
                hires_by_day[obs["day"]] += 1
        return action

    env = make(
        "kaggriculture",
        configuration={"episodeSteps": EPISODE_STEPS, "seed": seed},
        debug=True,
    )
    env.run([checked_agent, opponent])
    final = env.steps[-1]
    statuses = [state.status for state in final]
    assert len(env.steps) == EPISODE_STEPS
    assert statuses == ["DONE", "DONE"]
    assert planted_positions == TARGET_PLOTS
    assert set(hires_by_day) == set(range(30))
    assert all(hires_by_day[day] == 2 for day in range(30))
    for required in ("PLANT", "WATER", "HARVEST", "SELL", "HIRE"):
        assert operation_counts[required] > 0
    print(
        f"PASS vs {label:<15} turns={len(env.steps)} "
        f"status={statuses[0]} rewards={[state.reward for state in final]}"
    )


def main():
    _run_checked_game("starter", "starter", 7101)
    _run_checked_game("random", "random", 7102)
    carrot = _load_agent(str(CARROT_PATH))
    _run_checked_game(carrot, "carrot_scale_20", 7103)
    print("All standalone submission checks passed.")


if __name__ == "__main__":
    main()
