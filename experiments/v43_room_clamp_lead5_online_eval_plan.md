# Online evaluation: submission 56270914 (V43 room_clamp + premium lead5)

Submitted 2026-09-16 05:53 UTC (13:53 local). Archive
`submission/v43_room_clamp_lead5.tar.gz`, sha256 5821a9bd215731d0...

## Baseline

56258686 (V43 + room_guard + clamp_sells), same chassis without the lead layer:
peak 2730 on 2026-09-15, 2660.7 at submission time (dormant drift). The
comparison is peak-to-peak and same-window; a dormant score is not a baseline.

## Local evidence

Direct matches against 56258686's exact agent: pilot 64/0 mean +1,557, holdout
(16 unseen pairs, 2 unseen seeds) 64/0 mean +1,713, worst game +121. About 30%
of the margin is our own revenue (+513 over lead2), 70% the clone's loss.

## Pre-registered reading

- The clone's-loss share applies only to V43-lineage opponents; their share of
  the 2600-2950 band is unknown (2 of the 16 daily top-10 teams; V43 is the
  most-forked public agent). Our own share applies to everyone.
- Expected peak: +80 to +200 over 2730, central ~2850. Top-30 line 2916.3.
- Checkpoints at 30 / 60 / 100 / 130+ episodes: report score, episode count,
  W/L, and opponent-lineage split (opening field agreement with V43 route 0).
- Success: peak above 2730 by >= 50 with 100+ episodes. Failure: peak <= 2730.
- Keep 56258686 as the registry's current best until 56270914's peak exceeds it.

## Follow-up: adapt5

Submitted next as `submission/v43_room_clamp_adapt5.tar.gz` (sha256 6e472b08...).
Identical to lead5 against V43-lineage opponents, identical to 56258686 against
everyone else. Read peak-to-peak against both 56258686 (2730) and 56270914
(lead5) in the same window; the gap lead5 - adapt5 estimates how much of the
population is not racing our lots.

## Competition timeline (from the Overview, pasted 2026-09-16)

- 2026-09-30 23:59 UTC final submission deadline.
- 2026-10-01 to ~10-15: games continue "until the leaderboard has reached
  convergence"; the leaderboard is final at the end of that period.

So the post-submission overshoot (peak 3-5 h in, -70..90 over the next 12 h)
is irrelevant to the final ranking; only the settled skill against the final
population counts. Selection rule: compare settled values at equal age with
100+ episodes; make sure the strongest agent is among the active submissions
at the deadline. Open question: how many submissions per team stay active, and
the daily submission limit (Evaluation section).
