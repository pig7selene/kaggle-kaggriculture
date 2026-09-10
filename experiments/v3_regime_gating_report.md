# V3 specialist regime gating report

## Result

The three-policy portfolio has major hindsight headroom but no safe observable gate. Across **80 fresh conditions / 240 games** (ten opponents, four new natural-RNG seeds each, both seats), the own-money oracle is **+9778.6** and the advantage oracle **+7997.0** per condition. Both oracle P10 and P5 are zero because CurrentBest is always available as the fallback.

With conservative tie-breaking, CurrentBest is own-optimal in **36/80 (45.0%)**, V3 in **23/80 (28.75%)**, and Route1 in **21/80 (26.25%)**. Tie-aware, Route1 is optimal in 35 conditions because published V3 selects Route1 in many regimes.

Route1 contains almost all of the portfolio value. CurrentBest+Route1 alone has a **+9727.3** own oracle; adding published V3 increases the full oracle by only **+51.4** per condition.

When V3 is optimal it gains **14200.7** versus CurrentBest. When selecting it is actually worse than CurrentBest, the mean loss is **-16994.0**, P10 **-35056.0**, and worst **-39047**. Route1's corresponding upside is **19261.5**; wrong-selection mean **-16734.0**, P10 **-34638.0**, worst **-39047**.

## Why the apparent specialist signal is not deployable

CurrentBest performs no market order on turn 0. V3 and Route1 buy 13 wheat. Their exact common action prefix is therefore zero turns, and the only unquestionably legal three-way selection time is before the first action. At that observation, every evaluated condition has the same economic state and market state; only seat differs. No allowed feature can distinguish the eventual winner.

By step 24 there is useful opponent information and near-compatible geometry: field layout and workforce agree in 80/80 CurrentBest/V3 conditions, and inventory in 72/80. Cash differs in all conditions, however, and by step 48 crop layout differs in 80/80. Step 24 is not an exact common prefix.

The best cross-seed step-24 signature rule uses an 8,000-coin safety threshold. It gains only **+1754.8 own / +1156.8 advantage** per condition, captures **17.9%** of the own oracle, activates in **23/80**, and is right only **56.5%** of activations. It makes 10 false activations and retains a **-36682** worst own-money loss. Adding the immediately previous checkpoint as history does not improve this result.

## CurrentBest-counter hypothesis

The fresh direct matchup is weaker than the discovery result. V3's mean own delta against CurrentBest is **+1140.6** and mean advantage delta **+4023.8**; it wins 6/8 direct games, not 8/8. More importantly, CurrentBest, Nazmus, and oceanmix are observationally identical at step 24, while their Route1 mean deltas are +1,631.6, −7,232.5, and −4,742.0. V3 counters the exact later CurrentBest trajectory in some market paths, not a reliably identifiable early “CurrentBest-like” family.

## Safety and decision

All 240 games completed with zero runtime errors, semantic errors, or livestock escapes. No selector candidate was created because doing so would require an unproven step-24 splice after a low-precision gate, violating the compatibility and false-positive constraints. No learned tree/ensemble was trained after the stop condition fired.

**Keep CurrentBest unchanged.** No finalist lock, final candidate validation, packaging, upload, or submission occurred. The next useful research direction is not a more complex classifier; it is a deliberately designed, validated common opening that preserves both continuations until randomized shop/market information becomes visible. That should be attempted only as a new architecture study with explicit state reconciliation, not as a blind replay splice.
