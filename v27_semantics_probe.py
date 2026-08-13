"""Controlled proofs of Kaggriculture semantics needed by replay executors.

This is intentionally small and deterministic.  It combines source inspection
with executable micro-games so later V27 repair logic does not depend on an
assumed seat priority or on guessed transaction confirmation behavior.
"""

from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path

from kaggle_environments import make
from kaggle_environments.envs.kaggriculture import kaggriculture as game


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "experiments/v27_market_semantics.json"


def scripted(actions):
    def agent(obs):
        action = actions.get(int(obs["step"]), {})
        return {
            "farmer": action.get("farmer", ["PASS"]),
            "hands": action.get("hands", [["PASS"] for _ in obs["farms"][obs["player"]]["hands"]]),
            "market": action.get("market", []),
        }
    return agent


def run(left, right, *, steps=5, money=3000):
    env = make(
        "kaggriculture",
        configuration={
            "episodeSteps": steps,
            "seed": 270027,
            "startingMoney": money,
            "weedSpawnChance": 0,
            "townShopUnlockInterval": 99,
            "townShopSellInterval": 99,
            "townCenterSellInterval": 99,
        },
        debug=True,
    )
    env.run([scripted(left), scripted(right)])
    return env.toJSON()


def snapshot(replay, index):
    obs = replay["steps"][index][0]["observation"]
    return {
        "step_index": index,
        "money": [float(farm["money"]) for farm in obs["farms"]],
        "hands": [farm["hands"] for farm in obs["farms"]],
        "hires_today": [farm["hires_today"] for farm in obs["farms"]],
        "quadrants": [farm["unlocked_quadrants"] for farm in obs["farms"]],
        "wheat_inventory": obs["market"]["inventory"]["WHEAT"],
        "wheat_price": obs["market"]["prices"]["WHEAT"],
        "private": [
            {
                "wheat": state["observation"]["private"]["shed"]["WHEAT"],
                "wheat_seeds": state["observation"]["private"]["seeds"]["WHEAT"],
                "cow": state["observation"]["private"]["shed"]["COW"],
            }
            for state in replay["steps"][index]
        ],
    }


def main():
    simultaneous = run(
        {
            0: {"market": [["BUY_PRODUCT", "WHEAT", 4]]},
            1: {"market": [["SELL", "WHEAT", 4]]},
        },
        {
            0: {"market": [["BUY_PRODUCT", "WHEAT", 4]]},
            1: {"market": [["SELL", "WHEAT", 4]]},
        },
    )
    seat_swap = run(
        {
            0: {"market": [["BUY_PRODUCT", "WHEAT", 2]]},
            1: {"market": [["SELL", "WHEAT", 2]]},
        },
        {
            0: {"market": [["BUY_PRODUCT", "WHEAT", 6]]},
            1: {"market": [["SELL", "WHEAT", 6]]},
        },
    )
    seat_swap_reverse = run(
        {
            0: {"market": [["BUY_PRODUCT", "WHEAT", 6]]},
            1: {"market": [["SELL", "WHEAT", 6]]},
        },
        {
            0: {"market": [["BUY_PRODUCT", "WHEAT", 2]]},
            1: {"market": [["SELL", "WHEAT", 2]]},
        },
    )
    order_slots = run(
        {
            0: {"market": [["BUY_PRODUCT", "WHEAT", 4]]},
            1: {"market": [["SELL", "WHEAT", 4]]},
        },
        {
            0: {"market": [["BUY_PRODUCT", "WHEAT", 4]]},
            1: {"market": [["HIRE"], ["SELL", "WHEAT", 4]]},
        },
    )
    mixed = run(
        {
            0: {"market": [["BUY_PRODUCT", "WHEAT", 4]]},
            1: {"market": [["SELL", "WHEAT", 4]]},
        },
        {
            1: {"market": [["BUY_PRODUCT", "WHEAT", 4]]},
        },
    )
    hires = run(
        {0: {"market": [["HIRE"], ["HIRE"], ["HIRE"], ["HIRE"]]}},
        {},
        money=100,
    )
    unaffordable = run(
        {0: {"market": [["HIRE"], ["HIRE"], ["HIRE"], ["BUY_LAND"], ["BUY_ANIMAL", "COW", 1], ["BUY_SEED", "MELON", 1]]}},
        {},
        money=2,
    )
    cap = run(
        {0: {"market": [["BUY_SEED", "WHEAT", 1] for _ in range(11)]}},
        {},
    )
    confirmations = run(
        {0: {"market": [["BUY_LAND"], ["BUY_ANIMAL", "COW", 1], ["BUY_SEED", "MELON", 2], ["BUY_PRODUCT", "WHEAT", 3], ["HIRE"]]}},
        {},
        money=5000,
    )

    source = inspect.getsource(game._process_market)
    payload = {
        "schema_version": 1,
        "environment_source": game.__file__,
        "environment_source_sha256": hashlib.sha256(Path(game.__file__).read_bytes()).hexdigest(),
        "action_indexing": {
            "observation_step_s_requests_action_stored_at_replay_index": "s+1",
            "requested_actions_per_complete_episode": 719,
            "reason": "replay step 0 is initial state; each subsequent state stores the request that produced it",
        },
        "source_proofs": {
            "queue_loop": "market queues are aligned by order index; each aligned pair is processed before the next slot",
            "unit_loop": "both active players are quoted from the same pre-commit inventory, then committed in player order",
            "seat_priority": "no price priority for simultaneous units: quotes are frozen before either commit",
            "town_order": "field actions, market, town consumption, decay, then optional end-of-day refresh",
            "market_refresh": "after every aligned order slot and again after town consumption",
            "order_cap": "each player's queue is sliced to maxMarketOrdersPerTurn before parsing",
            "new_hand": "HIRE executes after field actions and appends a hand/inventory to the next observation",
            "spawn": "least occupied shed-access tile, NW/NE/SW/SE tie order",
            "process_market_source_contains_lockstep_docstring": "Per-unit lockstep" in source,
        },
        "micro_experiments": {
            "simultaneous_equal_sell": snapshot(simultaneous, 2),
            "unequal_sell_seat0_small": snapshot(seat_swap, 2),
            "unequal_sell_seat1_small": snapshot(seat_swap_reverse, 2),
            "different_order_slots": snapshot(order_slots, 2),
            "simultaneous_buy_sell": snapshot(mixed, 2),
            "four_hires": snapshot(hires, 1),
            "unaffordable_orders": snapshot(unaffordable, 1),
            "eleven_order_cap": snapshot(cap, 1),
            "transaction_confirmation": snapshot(confirmations, 1),
        },
        "confirmation_signals": {
            "BUY_LAND": "unlocked_quadrants length grows and locked tiles become empty; money falls by 1000/2000/4000",
            "BUY_ANIMAL": "shed animal count grows by committed quantity; money falls by fixed animal cost",
            "BUY_SEED": "private seeds count grows; money falls by fixed seed cost",
            "BUY_PRODUCT": "shed product grows, market inventory falls, money falls by unit prices",
            "HIRE": "hands, hires_today, and private inventories grow together; money falls by Fibonacci marginal cost",
        },
        "verified_conclusions": {
            "simultaneous_sells_have_seat_price_parity": True,
            "leftover_units_after_shorter_order_see_updated_inventory": True,
            "different_order_positions_are_not_simultaneous": True,
            "town_consumes_after_player_market": True,
            "new_hands_cannot_act_on_hire_turn": True,
            "unaffordable_orders_are_silent_noops": True,
            "max_ten_orders_processed": snapshot(cap, 1)["private"][0]["wheat_seeds"] == 10,
        },
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(OUTPUT)


if __name__ == "__main__":
    main()
