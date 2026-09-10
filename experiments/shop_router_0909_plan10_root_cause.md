# Shop Router 0909 Plan-10 root cause

## Finding

The sheep at `[7,4]` escapes during the end-of-day refresh after action step **383** and is first absent in observation step **384**. Both seats reproduce the same sequence.

The initiating resource decision is the step-332 order `SELL WHEAT 9`. It earns 342 coins but leaves only 16 held wheat at the start of day 14 for 17 animals. Ordered pickups then starve the final feeder: at step 339 it requests two wheat but receives one, feeds `[6,4]` at step 341, and reaches `[7,4]` empty. Its step-345 `FEED` is a silent no-op. The day-14 refresh leaves the target at `consecutive_unfed=1`.

Day 15 contains 21 wheat, enough in aggregate after later harvests, but the tape allocates it incorrectly. At step 360 the main farmer takes five wheat and never uses any wheat that day. Three earlier workers take five each. Only one remains when the final feeder requests two at step 363. It spends that unit at `[6,4]` on step 365, reaches `[7,4]` on time, but its step-369 `FEED` silently fails because its inventory has no wheat. `CARE` at step 370 succeeds but cannot substitute for feeding. The second consecutive unfed refresh after step 383 removes the sheep.

## Classification

- Primary root cause: wheat allocation/order contention.
- Initiating action: step-332 sale of nine wheat.
- First observed service failure: step-345 empty-inventory feed.
- First unavoidable point for the eventual escape on the existing tape: step 363, when the day-15 final feeder receives only one of two requested wheat after the farmer's unused five-unit pickup.
- Decisive second failed feed: step 369.
- Not causal: movement, hand count, shop randomness after route selection, or late arrival. The feeder reaches both animals at the planned turns.

## Causal verification of the selected patch

The hardened wrapper changes only step 360 under Plan 10: the farmer picks up four rather than five wheat. The final feeder then receives two wheat at step 363, retains one after feeding `[6,4]`, and successfully feeds `[7,4]` at step 369. At step 384 the sheep remains present and its counter has reset to zero. No action is inserted and no tape index shifts.
