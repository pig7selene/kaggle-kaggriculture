# Plan to the deadline (written 2026-09-17, 13 days left)

Rules that shape it: 5 submissions a day; only the **latest 2** are tracked and
they are the two that play the final window; submissions lock 2026-09-30 23:59
UTC and games then run to about 10-15 October before a Bradley-Terry fit
produces the final board. So the overshoot after a submission is irrelevant,
and every submission is also a selection decision.

## What is settled

- Our band is a crowd of V43 forks (114 of 120 lineage opponents fingerprint as
  the shipped notebook). We beat them 60% of the time, mean margin +807.
- The top of the board is not V43 and makes 110-115k to our 103k. The
  difference is the price, not the farm: in the last day they sell premium at
  1.0 of base, we sell the same quantity at 0.61, because two V43 agents in one
  game flood wool and milk from 14 pastures each all game long.
- Importing a top agent's tape is impossible (4,194 instead of 116,326).
- Unilaterally producing *less* premium does not help while the opponent still
  floods it; only producing *something else* does, and that needs new tapes.

## The one untested cheap lever: an unconditional 8-step lead

Direct matches, 64 games each, zero errors:

| our agent | vs shipped | vs shipped with a 4-step lead | vs shipped with an 8-step lead |
|---|---|---|---|
| room_clamp | 58/6, +537 | 58/6, +636 | — |
| lead5 | 64/0, +1,946 | 64/0, +2,107 | **24/40, -162** |
| lead8 | 63/1, +1,589 | 63/1, +1,736 | **59/5, +646** |

lead8 is the only candidate that beats every reconstruction of the pool. Our
online losses are narrow -- 19 of 48 within 1,000 and 30 within 2,000 -- and
+1,589 of mean margin is exactly the size that flips them. adapt5 is not
evidence against this: its classifier fired at half strength online and, by
construction, switched the lead **off** against the modified forks we lose to.

Submitted as `submission/v43_room_clamp_lead8.tar.gz` (sha256 8e9a285c23134
7f0..., source 11a9ff6e3af17b88...). With the control this makes the tracked
pair {room_clamp bytes, lead8}: a clean same-window head-to-head, ~150
episodes each by tomorrow morning.

## Schedule

- **17 Sep**: submit lead8. Tracked pair = control room_clamp + lead8.
- **18 Sep**: read the head-to-head at equal episode counts. The winner is the
  incumbent that every later candidate must beat in direct matches.
- **17-24 Sep**: the only line that could reach the top 30 -- differentiate
  production from the opponent's. First the free version, forcing each of
  V43's 41 routes against shipped and reading the realized premium index
  (`run_route_vs_shipped.py`, running); if no route differentiates, a surgical
  pasture-to-crop substitution in the tape, keeping the trajectory's geometry.
  Hard stop on 24 Sep if it does not beat the incumbent on a holdout.
- **28-29 Sep**: submit the final two, freshest so they play the most episodes
  in the final window.

## Honest expectation

Within the fork cluster, 2700-2800 is reachable and top 30 (2916) is not. The
production line is the only path above that, and it is maybe a one-in-five
shot in the time available. Everything else measured this week -- tape
transplants, price gates, the sell planner, slot priority, sell-on-arrival,
route remaps against our own clone -- is closed.
