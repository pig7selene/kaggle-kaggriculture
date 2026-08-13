"""Full-season format and semantic-action checks for economic agents/proxies."""

from pathlib import Path

from kaggle_environments import make

from benchmark import EPISODE_STEPS, ROOT, _load_agent


UNIT_ARITY = {
    "NORTH": 1, "SOUTH": 1, "EAST": 1, "WEST": 1, "PASS": 1,
    "PLANT": 2, "WATER": 1, "HARVEST": 1, "FERTILIZE": 1, "DIG": 1,
    "BUILD_COOP": 1, "BUILD_PASTURE": 1, "PICKUP": (2, 3), "DROP": 1,
    "PLACE": (2, 3), "FEED": 1, "CARE": 1,
    "COLLECT_FERTILIZER": 1,
}
CROP_FIRST = {"WHEAT": 2, "CARROT": 2, "TOMATO": 8, "STRAWBERRY": 10, "MELON": 10}
ANIMAL_STRUCTURE = {"GOOSE": "COOP", "COW": "PASTURE", "SHEEP": "PASTURE"}
MARKET_ARITY = {
    "HIRE": 1, "BUY_LAND": 1, "BUY_SEED": 3,
    "BUY_PRODUCT": 3, "BUY_ANIMAL": 3, "SELL": 3,
}
SHED_TILES = {(4, 4), (5, 4), (4, 5), (5, 5)}
SELLABLE = {
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
    "EGG", "MILK", "WOOL", "FERTILIZER",
}


def _valid_arity(action, expected):
    return len(action) in expected if isinstance(expected, tuple) else len(action) == expected


def _validate_unit(obs, position, inventory, action):
    assert isinstance(action, list) and action
    op = action[0]
    assert op in UNIT_ARITY, f"unknown unit action: {action}"
    assert _valid_arity(action, UNIT_ARITY[op]), f"bad unit arity: {action}"
    me = obs["farms"][obs["player"]]
    x, y = position
    tile = me["tiles"][y][x]
    if op in {"NORTH", "SOUTH", "EAST", "WEST"}:
        dx = {"WEST": -1, "EAST": 1}.get(op, 0)
        dy = {"NORTH": -1, "SOUTH": 1}.get(op, 0)
        assert 0 <= x + dx < 10 and 0 <= y + dy < 10
    elif op == "PLANT":
        assert tile is None and action[1] in CROP_FIRST
    elif op == "WATER":
        assert isinstance(tile, dict) and tile.get("kind") == "PLANT"
        assert not tile.get("watered_today", False)
    elif op == "FERTILIZE":
        assert isinstance(tile, dict) and tile.get("kind") == "PLANT"
        assert inventory.get("FERTILIZER", 0) > 0
    elif op == "HARVEST":
        assert isinstance(tile, dict) and tile.get("yield_units", 0) > 0
        if tile.get("kind") == "PLANT":
            assert obs["day"] - tile["planted_day"] >= CROP_FIRST[tile["crop"]]
        else:
            assert tile.get("animal") in ANIMAL_STRUCTURE
    elif op == "DIG":
        assert tile not in (None, "LOCKED")
        assert not (isinstance(tile, dict) and tile.get("animal"))
    elif op in {"BUILD_COOP", "BUILD_PASTURE"}:
        assert tile is None
    elif op == "PICKUP":
        assert (x, y) in SHED_TILES
        assert obs["private"]["shed"].get(action[1], 0) > 0
        if len(action) == 3:
            assert isinstance(action[2], int) and action[2] > 0
    elif op == "DROP":
        assert (x, y) in SHED_TILES and any(inventory.values())
    elif op == "PLACE":
        item = action[1]
        if item in ANIMAL_STRUCTURE:
            assert isinstance(tile, dict) and tile.get("kind") == ANIMAL_STRUCTURE[item]
            assert not tile.get("animal")
            assert inventory.get(item, 0) > 0
        else:
            assert (x, y) in SHED_TILES and inventory.get(item, 0) > 0
    elif op == "FEED":
        assert isinstance(tile, dict) and tile.get("animal") in ANIMAL_STRUCTURE
        assert not tile.get("fed_today", False) and inventory.get("WHEAT", 0) > 0
    elif op == "CARE":
        assert isinstance(tile, dict) and tile.get("animal") in ANIMAL_STRUCTURE
        assert not tile.get("cared_today", False)
    elif op == "COLLECT_FERTILIZER":
        assert isinstance(tile, dict) and tile.get("animal") in ANIMAL_STRUCTURE
        assert tile.get("fertilizer_available", False)


def _validate_action(obs, action):
    assert isinstance(action, dict)
    assert set(action) == {"farmer", "hands", "market"}
    me = obs["farms"][obs["player"]]
    positions = [me["farmer"], *me["hands"]]
    inventories = obs["private"]["inventories"]
    actions = [action["farmer"], *action["hands"]]
    assert len(action["hands"]) == len(me["hands"])
    for position, inventory, unit_action in zip(positions, inventories, actions):
        _validate_unit(obs, position, inventory, unit_action)
    plant_counts = {}
    for unit_action in actions:
        if unit_action[0] == "PLANT":
            crop = unit_action[1]
            plant_counts[crop] = plant_counts.get(crop, 0) + 1
    for crop, count in plant_counts.items():
        assert count <= obs["private"]["seeds"].get(crop, 0)

    assert isinstance(action["market"], list) and len(action["market"]) <= 10
    sells = {}
    for order in action["market"]:
        assert isinstance(order, list) and order and order[0] in MARKET_ARITY
        assert _valid_arity(order, MARKET_ARITY[order[0]])
        if len(order) == 3:
            assert isinstance(order[2], int) and order[2] > 0
        if order[0] == "BUY_SEED":
            assert order[1] in CROP_FIRST
        elif order[0] == "BUY_PRODUCT":
            assert order[1] in {"WHEAT", "FERTILIZER"}
        elif order[0] == "BUY_ANIMAL":
            assert order[1] in ANIMAL_STRUCTURE
        elif order[0] == "SELL":
            assert order[1] in SELLABLE
            sells[order[1]] = sells.get(order[1], 0) + order[2]
    for product, quantity in sells.items():
        assert quantity <= obs["private"]["shed"].get(product, 0)


def _run(path, seed):
    base = _load_agent(str(path))

    def checked(obs):
        action = base(obs)
        _validate_action(obs, action)
        return action

    env = make(
        "kaggriculture",
        configuration={"episodeSteps": EPISODE_STEPS, "seed": seed},
        debug=True,
    )
    env.run([checked, "pass"])
    final = env.steps[-1]
    assert len(env.steps) == EPISODE_STEPS
    assert [state.status for state in final] == ["DONE", "DONE"]
    private = final[0].observation["private"]
    if path.parent.name != "proxies":
        stranded = sum(private["shed"].get(item, 0) for item in SELLABLE)
        stranded += sum(inv.get(item, 0) for inv in private["inventories"] for item in SELLABLE)
        if path.name.startswith("animal_"):
            farm = final[0].observation["farms"][0]
            stranded += sum(
                tile.get("yield_units", 0)
                for row in farm["tiles"]
                for tile in row
                if isinstance(tile, dict) and tile.get("animal")
            )
        assert stranded == 0, f"valuable endgame inventory stranded: {stranded}"
    print(f"PASS {path.relative_to(ROOT)} money={final[0].reward:.0f}")


def main():
    paths = sorted((ROOT / "agents").glob("adaptive_*.py"))
    paths += sorted((ROOT / "agents").glob("animal_c*.py"))
    paths += sorted((ROOT / "agents").glob("animal_only_*.py"))
    paths += sorted((ROOT / "agents" / "proxies").glob("*.py"))
    for index, path in enumerate(paths):
        _run(path, 9000 + index)
    print("All economic-agent semantic checks passed.")


if __name__ == "__main__":
    main()
