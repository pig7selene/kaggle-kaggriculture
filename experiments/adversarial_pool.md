# Replay-Backed Adversarial Pool

The pool is based on the two public opponents in submission 55412009's three
downloaded episodes. It intentionally broadens those two observations into
distinct stress tests; proxies are behavioral approximations, not attempts to
reconstruct private opponent code.

| Pool opponent | Local agent | Behavior approximated | Replay evidence |
| --- | --- | --- | --- |
| Current baseline | `agents/melon_scale_12.py` | Frozen 12-plot melon benchmark | Current best before this phase |
| Melon-heavy | `agents/proxies/melon_heavy.py` | 18 melons, two hands, immediate liquidation | Both public winners opened with 16–18 visible melons |
| Phased rotation | `agents/proxies/phased_rotation.py` | 18-melon opening, one hand, late wheat rotation, inventory-aware sales | indira rotated from melons to wheat/tomatoes after day 21 |
| Aggressive land | `agents/proxies/land_expander.py` | NE on day 0, remaining land after day 11, sparse labor | indira unlocked NE immediately and all quadrants after the first melon cycle |
| Inventory holder | `agents/proxies/inventory_holder.py` | 16 melons, premium holding, overflow guard, day-24 liquidation | Winners' weighted sale steps were 484/515 versus our 394; major melon lots sold on days 11 and 22–24 |
| Mixed crops | `agents/proxies/mixed_crop.py` | Fixed five-crop portfolio | Hubbahub planted four crop types; indira planted three |
| Livestock + crops | `agents/proxies/livestock_crop.py` | Melon/wheat rotation, land purchase, four cows, feed/care/fertilizer collection, held premiums | Hubbahub combined melons, strawberries, wheat, seven cows, milk, and fertilizer sales |
| High labor | `agents/proxies/high_labor.py` | Expanded 60-slot mixed farm with eight daily hands | Hubbahub ramped from three early hires to eleven daily hires late |

Every proxy uses legal observation/action formats and completed a checked
720-turn semantic-action test. The pool deliberately includes strategies that
share products with a candidate, because the market-price externality is a
central source of non-transitivity.

Limitations:

- Only two public opposing agents were available, so archetype coverage is
  necessarily speculative.
- Proxy quality measures local stress, not leaderboard representativeness.
- The livestock proxy is intentionally strong and is the closest approximation
  to the 50,801-coin Kaggle winner, but it is not a replay clone.
