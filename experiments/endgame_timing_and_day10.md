# Score hump and the final-day dump (2026-09-16)

## Score trajectories (track_submission_scores.py samples, 15-min cadence)

| submission | peak | at | later |
|---|---:|---:|---|
| 56258686 V43+room_clamp | 2730.1 | +3.0h | +4h 2714, +11h 2686, +13h 2658, +16h 2642 |
| 56255914 V43 baseline | 2628.2 | +4.6h | +7h 2616, +14h 2600, +16h 2560 |
| 56270914 lead5 | 2677.0 | +2.3h | +2.8h 2652 (still climbing/settling) |
| 56250442 (0911 candidate) | 2030.7 | +7h | frozen at 2026.6 from +7h on |
| 56138084 Terminal D | 2496.8 | — | frozen for 130h+ |

A fresh submission overshoots to a peak 3-5 hours in, gives back ~70-90 over
the next 12 hours while it still plays, then freezes once matchmaking stops
scheduling it. The peak is the rating's early overshoot; the settled value is
the skill estimate. Comparisons between submissions must be at equal age.

Consequence for the deadline (2026-09-30 23:59): if the leaderboard freezes at
the deadline, a fresh copy of the best agent submitted ~4 hours before it shows
the overshoot (+70-90); if a post-deadline evaluation period follows, only the
settled skill matters and the timing is irrelevant. The competition's
evaluation text decides which; it is not readable through the CLI.

## Final-day dump: too small to chase

adapt5 self-play, 4 seeds, both seats. Units sold at the $1 floor on day 10:
MILK 10, STRAWBERRY 6, FERTILIZER 5 per seat-game (worth ~1.4k if sold at half
base); in the last three steps 5 units of MILK (~400). Days 1-9 carry the real
floor losses (MILK 25, STRAWBERRY 55 units, ~5.3k) and those are the holding
problem the gates and planner could not price. Endgame work is closed, in line
with the neutral Terminal D graft.
