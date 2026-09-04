# `top50_raw_55899537` worst-case review

## Scope and method

This is the locked, post-run review of the final independent validation.  The
candidate is `agents/autonomous_next/top50_raw_55899537.py`; the comparison is
the frozen `agents/top50_distilled/top50_observable_portfolio.py`.  The review
uses the ten paired rows with the smallest candidate-minus-baseline own-money
delta from `raw55899537_worst_case_rows.json`.  Candidate and baseline were
rerun with the same opponent, seed, seat, and 720-step configuration.  A row's
"first durable negative day" is the first end-of-day day after which the
candidate bank delta never returned to zero or above.  The repeated seat rows
are retained because both seats are part of the locked sample; in symmetric
conditions they have identical trajectories.

## Worst rows and first durable divergence

| rank | panel / opponent | seed / seat | own-money delta | advantage delta | first durable negative day | bank delta day 10 | bank delta day 20 |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | top3 / OceanMix | 50109 / 0 | -62,075 | -9,533 | 4 | -862 | -17,807 |
| 2 | top3 / OceanMix | 50109 / 1 | -62,075 | -9,533 | 4 | -862 | -17,807 |
| 3 | top3 / tetsuya | 50110 / 0 | -55,949 | -40,226 | 6 | -5,275 | -25,918 |
| 4 | top3 / tetsuya | 50110 / 1 | -55,949 | -40,226 | 6 | -5,275 | -25,918 |
| 5 | top3 / tetsuya | 50104 / 1 | -46,062 | -25,908 | 6 | -5,446 | -27,431 |
| 6 | direct / CurrentBest | 50058 / 0 | -45,912 | +3,985 | 12 | -702 | -14,338 |
| 7 | direct / CurrentBest | 50058 / 1 | -45,912 | +3,985 | 12 | -702 | -14,338 |
| 8 | direct / CurrentBest | 50051 / 0 | -45,291 | +1,945 | 4 | -847 | -17,296 |
| 9 | direct / CurrentBest | 50051 / 1 | -45,291 | +1,945 | 4 | -847 | -17,296 |
| 10 | natural RNG / CurrentBest | 50322 / 0 | -36,582 | +1,996 | 4 | -887 | -14,155 |

The first visible bank divergence is usually small (tens to hundreds of coins)
in days 1–5.  The durable losses occur when premium-product revenue begins,
not when the route is being set up.  In the tetsuya rows the delta is already
below -1,000 on day 8; in the OceanMix rows it crosses that level on day 12.

## Structured economic decomposition

### OceanMix 50109 (the two largest losses)

The candidate and baseline realize the same route milestones: first land at
step 151 (day 6, hour 7), second land at step 266 (day 11, hour 2), 12 peak
hands, and nine cows/five sheep at the end.  Both have 100% route realization,
zero repairs, zero escapes, and only 12 coins of terminal fertilizer value.
Thus this is not a routing or safety failure.

The candidate's revenue deltas are: milk **-46,623**, strawberry **-17,307**,
while wheat is **+1,720**, carrot **+24**, and fertilizer **+153**.  Daily
revenue is already -773 cumulatively by day 10, briefly improves on day 11,
then falls to -1,636 on day 12, -7,187 on day 15, and -18,753 on day 20.
The matched bank delta follows -862 (day 10), -1,733 (day 12), -12,440
(day 18), and -62,075 at season end.  The mechanism is a shared-market
premium-product realization difference: the raw route sells materially less
milk and strawberry at the prevailing curve.  The candidate's own cash loss is
partly masked in H2H terms because it also reduces the opponent's realization;
the final advantage delta is -9,533 rather than -62,075.

### tetsuya 50110 and 50104

These rows are the clearest capital-compounding failure.  At the end, the
candidate has only six cows/four sheep (ten animals) versus the baseline's six
cows/six sheep (twelve animals), despite identical three-quadrant land and
12-hand ceilings.  The candidate spends 1,623 more on labor but 1,000 less on
sheep purchases, indicating that cash was consumed without reaching the
baseline's livestock scale.  Revenue deltas in the worst 50110 row are milk
**-29,145**, strawberry **-19,053**, melon **-3,117**, wheat **-1,553**, and
fertilizer **-1,803**; wool is only **+376**.  In 50104, wool also falls
**-10,707** and milk **-25,083**.

The candidate is ahead only through day 5 (bank delta +382 in 50110), falls to
-444 on day 6, and is permanently negative from day 6.  By day 8 it is below
-1,000, by day 10 below -5,000, and by day 20 below -25,000.  No route repair,
semantic failure, or animal escape occurred.  Tetsuya's economy compounds
through an additional sheep cohort and associated product sales; the raw
candidate's state-conditioned parent choice does not preserve that capital
chain under this visible opponent state.

### Direct CurrentBest 50058 and 50051

Both rows finish with the same nine-cow/five-sheep economy and three quadrants
for candidate and baseline, with zero safety events and full route realization.
The candidate nevertheless realizes less milk (about **-30.7k to -37.3k**) and
wool (up to **-21.5k**) while gaining strawberry (+10.7k in 50058) and wheat
(+2.0k).  In 50058 the bank delta becomes permanently negative on day 12; in
50051 it does so on day 4 and reaches -17.3k by day 20.  The candidate still
wins the H2H advantage because the shared market suppresses the opponent more
than it suppresses the candidate.  This is a competitive externality, not an
own-income improvement.

### Natural RNG 50322

The natural fresh-seed row has the same stable route milestones and no safety
issues.  The candidate is -887 by day 10 and -14,155 by day 20.  Revenue is
lower in milk (-27,370), strawberry (-9,996), and wool (-167), with small wheat
and carrot offsets.  The candidate's advantage delta remains +1,996 because
the opponent loses more to the same market shift.  This confirms that the
tail is not confined to replay-derived shop states.

## Largest wins (counter-evidence)

| opponent / seed / seat | own-money delta | advantage delta | first permanently positive day | main revenue deltas |
|---|---:|---:|---:|---|
| router_hands12 / 50207 / 0 | +68,264 | +38,253 | 9 | milk +34,139; strawberry +28,818; wool +10,726; fertilizer -8,530; wheat -10,315 |
| CurrentBest / 50032 / 0 | +67,215 | +3,193 | 16 | milk +30,713; strawberry +36,572; wool -1,051 |
| CurrentBest / 50032 / 1 | +67,215 | +3,193 | 16 | same symmetric trajectory |
| router_hands12 / 50202 / 1 | +52,807 | +25,407 | 16 | milk +21,266; strawberry +36,523; fertilizer -8,957 |
| OceanMix / 50114 / 0 | +47,324 | +9,736 | 13 | milk +39,508; strawberry +13,865; wool -7,005 |

The winning rows become positive when the candidate's larger milk/strawberry
realization compounds after days 12–16.  This is the same mechanism as the
losses with the sign reversed; the route is coherent, but its product mix and
market interaction are regime-sensitive.

## Failure-shape conclusion

When the candidate loses to a strong Top-3 opponent, it generally loses both
own money and advantage (especially tetsuya).  Against the frozen CurrentBest
and in natural RNG, it can lose own money while still winning advantage because
opponent cash is suppressed more.  The losses are therefore not caused by
terminal inventory: candidate mean stranded value is 45.6 coins across the
full panel, and these worst rows have only 8–12 coins (or 168 coins in the
tetsuya row) of residual value.  They are economic realization failures:
premium-product timing, market saturation, and in tetsuya's case failure to
fund the final sheep cohort.

No candidate code, route, threshold, opponent list, or seed was changed after
the finalist lock.  This review records the failure modes for future research;
it does not patch them.
