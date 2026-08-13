# V27 replay backbone + bounded closed-loop correction

Date: 2026-08-12  
Decision: **promote `agents/v27_replay_weed_guard.py` as the research current best**  
Submission: unchanged; nothing submitted

## Executive conclusion

The public evidence confirms the requested architectural hypothesis. The
strongest observed route families are overwhelmingly scripted: Victor's four
appearances have **99.65% combined-field** and **99.20% market** modal
stability across all 719 decisions, while Abracadabra reaches 99.65%/98.92%,
Ueddy 99.53%/96.94%, Valmorlee 99.69%/96.91%, and Hak 99.13%/98.78%. Their
small differences concentrate in weed handling and environment-dependent
SELL quantities. THUNDER and Dmitry are materially more state-dependent and
were not used as the executable backbone.

The selected Victor route reproduced its medoid source episode exactly:
**719/719 requested actions**, identical checkpoints, and identical final
money (**94,884**). On the serious 48-game selection set the raw K0 route went
**48/0/0**, averaged **108,187** money and **+48,253** advantage, with P10
**+27,535**. It reversed all eight severe held-out top-template matchups and
all four reconstructed real-loss matchups. The result is not a small local
gain; it is a different economic architecture.

The only correction that survived ablation and fresh confirmation is the
worker-specific, bounded weed transaction. K3 preserves **99.987%** of route
actions on 32 fresh games, goes **32/0/0**, averages **122,464** money and
**+53,559** advantage, and raises fresh P10 from K0's +32,996 to **+39,977**.
It has zero runtime/schema failures, livestock losses, meaningful stranding,
or fallback activations. It is promoted as `v27_victor_route_weed_guard_v1`.

Capital retries, HIRE suppression, safety guards, current-turn SELL ordering,
future-slot assignment, and catastrophic fallback were implemented and tested
as later stages, but they are not enabled in the promoted K3 candidate. K4's
capital retries regress the fresh KKS route and become noisy under artificial
capital pressure. K7 finds no profitable current-turn reorder. K8 future-slot
assignment loses 1,846 average advantage versus K7 and creates meaningful
stranding in 25/48 games. K9 therefore fails the promotion gate even though
the underlying route remains strong.

## 1. Frozen state and parked research

Protected hashes before/after the study:

| Artifact | SHA-256 |
| --- | --- |
| `submission/main.py` | `d0fbf1205a7e27f8294f1f9a06afd581cfb3e926f8ab88acc0b7f7a8b72620cf` |
| `agents/leaderboard_r3_cow6_capital.py` | `57a4d38a72fffe75061271423b5580dec79c8c0e0423db4bef8899b3993b8fad` |
| `agents/opening_public_front_cow8_day6.py` | `3ede0041921010b0136abb538395faa5951e9af1fb9b76be41467246885da6a8` |
| `agents/lifecycle_lc_combined.py` | `db12d32912843e012c3dfd7e84c2c384ce998694bf02b98fc7e1fe9189c17e78` |
| `experiments/current_best.json` before promotion | `0b2e47f9034914888fe90079997fef8495081437ffdf74f78fb55486ed6e86b1` |

After the authorized promotion, `experiments/current_best.json` is the only
entry in this table that intentionally changes (new hash
`53f6bf1ec81b07b44dc3cd51896037473481c8a9f68b361946c597b7de48c08e`).
All four frozen strategy/submission hashes remain identical.

The interrupted multi-wave study was safely stopped after its last checkpoint:
`experiments/multiwave_generation0.json.partial`, **600/1536 games**, 4,075,722
bytes, last modified 2026-08-12 22:50. It was not resumed or overwritten.

## 2. Replay corpus, identities, and indexing

The extraction corpus contains **25 unique public episodes** and **35 selected
appearances** from eight high-rated submissions captured at ratings
3,097.1–3,216.7. Because selected players sometimes played each other, an
episode can contribute two appearances. Identity is submission ID plus action
fingerprint and structural trajectory, not player name alone.

| Player | Submission | Rating | Appearances | Mean final money | Medoid episode |
| --- | ---: | ---: | ---: | ---: | ---: |
| THUNDER THUNDER | 55373222 | 3216.7 | 4 | 88,551 | 91853249 |
| Dmitry Larko | 55412236 | 3151.6 | 5 | 85,569 | 91843967 |
| Abracadabra | 55391753 | 3148.0 | 4 | 68,643 | 91856955 |
| Ueddy | 55407883 | 3144.7 | 5 | 83,423 | 91861610 |
| Victor @ Tufa Labs | 55417289 | 3140.8 | 4 | **102,852** | 91876492 |
| Erfan Eshratifar | 55418684 | 3103.0 | 5 | 80,281 | 91867088 |
| Valmorlee | 55388560 | 3100.9 | 4 | 70,814 | 91867069 |
| Hak | 55413692 | 3097.1 | 4 | 72,130 | 91869019 |

Replay indexing was verified in source and by reconstruction: observation step
`s` requests the action stored at `replay.steps[s+1][player].action`. A full
episode has 719 requested actions; replay step 0 is initial state.

The route manifest retains complete episode IDs, seats, seeds, opponents,
actions and expected states. The trace analyzers used were
`analyze_top_player_replays.py`, `analyze_v27_routes.py`,
`analyze_v27_market_risk.py`, and the existing leaderboard reconstruction
tools.

## 3. Exact semantics proved

`v27_semantics_probe.py` combines installed-source inspection with deterministic
micro-games. Its machine-readable output is `v27_market_semantics.json`.

- Market queues interleave by **order index**. Both players' current orders are
  processed before either advances to the next slot.
- Within an aligned SELL/BUY order, units execute lockstep. Both seats receive
  quotes from the same pre-commit inventory, then commits occur in player
  order. Equal simultaneous units have quote parity; player 0 does not get a
  special first-sale price.
- When one quantity finishes first, the other player's remaining units see
  refreshed inventory. Different order slots are not simultaneous.
- Atomic HIRE/BUY_LAND orders are processed once at their aligned slot in
  player order. The 10-order cap slices each queue before parsing.
- Town demand executes after field actions and player market actions; prices
  refresh after every order slot and again after town consumption.
- A hired worker cannot act on the hire turn. It appears in the next
  observation at the least-occupied shed-access tile, ties NW/NE/SW/SE.
  `hires_today` increments only on a successful hire. Marginal costs are
  Fibonacci `1,1,2,3,5,...`; unaffordable orders silently no-op.
- Confirmations are observable via quadrant count, owned animal count, seed
  count, shed product count, and next-observation hand count.
- Public V27 commonly emits surplus arguments such as `['FEED','WHEAT']` and
  `['FERTILIZE','FERTILIZER']`. The installed interpreter accepts these because
  it dispatches on `action[0]` and ignores the surplus. The older repository
  validator's exact-arity assumption was therefore not used to alter public
  replay requests.

## 4. Route fingerprints and stability

Four connected route families emerge at the predeclared ≥0.80 medoid-action
similarity threshold. Importantly, voting occurs only within one submission;
unrelated routes are never mixed per step.

| Family | Teams | Selected route | Appearances | Full field stability | Full market stability |
| --- | --- | --- | ---: | ---: | ---: |
| F1 | THUNDER | THUNDER | 4 | 41.97% | 74.48% |
| F2 | Dmitry, Erfan | Dmitry | 5 | 74.08% | 85.84% |
| F3 | Valmorlee, Abracadabra, Victor | **Victor** | 4 | **99.65%** | **99.20%** |
| F4 | Ueddy, Hak | Ueddy | 5 | 99.53% | 96.94% |

F1/F2 remain in the research Route Bank as structurally distinct families but
are marked state-dependent by their stability evidence. F3 is the strongest
raw backbone: its selected submission has the largest mean final money in the
corpus, non-SELL market actions are 100% stable, and its full field route is
99.65% stable. F4 is an alternative high-stability route, not blended into F3.

For individual submissions, the highest full-field stability is Valmorlee
(99.69%), followed by Victor/Abracadabra (99.65%), Ueddy (99.53%), Erfan
(99.39%), and Hak (99.13%). Victor has the strongest observed economy among
these stable submissions.

## 5. Backbone fidelity and raw transfer

The representative route is Victor episode 91876492, seat 0, seed 507629282.
Re-executing it against the recorded opponent trace yields:

- 719/719 requested actions identical;
- final money 94,884 versus recorded 94,884;
- opponent final 92,082 versus recorded 92,082;
- zero checkpoint divergence.

Across Victor's other appearances the fixed representative matches 97.77%,
99.44%, and 98.19% of whole-turn requests. Differences are 0–16 steps per
episode and concentrate in SELL quantities, four hand requests, and six
farmer requests. This is direct evidence that the route body is fixed while a
small environment-dependent surface remains.

### Raw K0 serious transfer

| Set | Games | W/L/T | Avg money | Avg advantage | Worst advantage |
| --- | ---: | ---: | ---: | ---: | ---: |
| Four reconstructed losses | 8 | 8/0/0 | 87,907 | +47,083 | +41,014 |
| Eight held-out real routes | 16 | 16/0/0 | 109,314 | +34,850 | +18,238 |
| Frozen direct, fixed shops | 12 | 12/0/0 | 112,291 | +54,027 | +35,324 |
| Frozen direct, natural RNG | 12 | 12/0/0 | 116,101 | +61,130 | +54,390 |
| **Total** | **48** | **48/0/0** | **108,187** | **+48,253** | **+18,238** |

Raw transfer retained exact expected hand counts and land milestones in all 48
games. The first universal divergence was money, caused by opponent/shop market
interaction (median first step 25.5). Only 22 games diverged in crop count and
eight in animal count; no hand-count or land-count mismatch occurred. The
recognized failure causes were stochastic weeds blocking route planting/build,
occasional downstream animal loss from that positional offset, and
environment-specific sale/feed quantities. No general routing failure was
observed.

## 6. Strict ablation ladder

The common opponent/shop/seed panel has 48 games per stage. Action fidelity is
measured against K1 after actual hand-count alignment.

| Stage | Added mechanism | W/L/T | Avg money | Avg advantage | P10 | Route fidelity | Decision |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| K0 | raw representative trace | 48/0/0 | 108,187 | +48,253 | +27,535 | 100.000% | proves architecture |
| K1 | within-submission stable route | 48/0/0 | 108,187 | +48,253 | +27,535 | 100.000% | same; route is stable |
| K2 | anchors + worker matching | 48/0/0 | 108,187 | +48,253 | +27,535 | 100.000% | dormant; no drift |
| **K3** | **weed transaction** | **48/0/0** | **107,297** | **+48,505** | **+27,535** | **99.965%** | **retain** |
| K4 | capital confirmation/retry | 48/0/0 | 107,361 | +48,512 | +27,535 | 99.959% | reject after fresh/pressure |
| K5 | cost-aware planned-HIRE gate | 48/0/0 | 107,361 | +48,512 | +27,535 | 99.959% | dormant |
| K6 | hard survival guard | 48/0/0 | 107,361 | +48,512 | +27,535 | 99.959% | dormant |
| K7 | current-turn SELL permutation | 48/0/0 | 107,361 | +48,512 | +27,535 | 99.959% | no reorders |
| K8 | future existing-slot assignment | 48/0/0 | 105,817 | +46,659 | +27,535 | 99.843% | **reject** |
| K9 | K8 + one-way fallback | 48/0/0 | 105,817 | +46,659 | +27,535 | 99.843% | **reject** |

K3 triggered 21 weed transactions in the serious panel. Fifteen resynchronized
within the eight-step window; six aborted safely. It removed all nine raw-route
livestock losses and the promoted version has no meaningful endgame stranding.
Artificial 3% weed pressure confirms the mechanism direction: K3 improves
average advantage by 836 versus K0. The real benefit is concentrated rather
than universal, which is exactly appropriate for a bounded correction.

K4 retried 18 feed purchases in the serious set and looks neutral there, but
under 3× hire cost or 2,400 starting capital it launches 276 retry actions,
records 18 failed milestones, and loses 4,653 average advantage versus K3. In
fresh KKS transfer it loses 7,921 money relative to K3 and creates 36 apparent
livestock losses across the 32 fresh games. It is not promoted.

K5 suppressed no ordinary HIRE in the serious set. Suppression occurs only
under artificial 3× cost, where a route-target worker lacks enough remaining
value or would break capital reserve. This answers the economic question but
does not justify enabling the module for standard rules.

## 7. Market simulator, hazard, and delay regret

The exact simulator uses installed `market_price`, unit-by-unit inventory
changes, order cap, fixed non-SELL slots, exact buy costs, town timing, and the
proved simultaneous quote semantics. Across K7's serious games, original V27
SELL requests realize an exact modeled **4,175,847** coins with **198,858**
coins of self-impact versus `quantity × current quote`. The original final-
quote approximation would overstate the loss because it prices every early
unit as if sold at the terminal quote.

The public-state hazard model uses visible mature crops/animal output, worker
presence near shed, quote, inventory pressure, and day/hour. Entire
Victor/Abracadabra/Valmorlee family appearances are held out. It beats a
constant-rate baseline at every horizon:

| Horizon | Validation Brier | Constant-base Brier |
| ---: | ---: | ---: |
| 1 turn | 0.02184 | 0.02534 |
| 4 turns | 0.06150 | 0.07631 |
| 8 turns | 0.08344 | 0.12422 |
| 12 turns | 0.08884 | 0.16070 |

Inventory changes can infer net external flow after subtracting our known
orders and adding deterministic town consumption. They cannot always identify
the opponent action uniquely: WHEAT/FERTILIZER may be bought or sold, $1 sales
do not add supply, and duplicate town shops create product-specific demand.
The artifact therefore reports interval-valued quantities and confidence.

Self-impact alone is not theoretically sufficient because it ignores an
opponent-first sale and capital-window value. Empirically, however, the
current V27 ordering is already optimal under exact current-turn permutations:
K7 makes **zero** changes. K8's hazard-driven future assignment makes 232 slot
changes, loses 1,846 average advantage, worsens the worst game from +18,238 to
+16,447, and creates meaningful stranded inventory in 25/48 games. The harm
comes from displacing a coordinated later liquidation, which then changes feed
confirmation and capital dependencies. Delay-regret modeling adds no validated
value in this implementation and is rejected.

## 8. Fresh confirmation and promotion

Four previously unused strong real routes (harmo-miu, Somasundar, KKS, Asuran)
and seeds 991001–991002 against all three frozen anchors produced 32 games per
finalist, both seats, fixed and natural shops.

| Candidate | W/L/T | Avg money | Avg advantage | Median | P25 | P10 | P5 | Worst | Fidelity |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| K0 raw | 32/0/0 | 121,759 | +52,775 | +56,777 | +41,469 | +32,996 | +30,357 | +28,119 | 100.000% |
| **K3 weed** | **32/0/0** | **122,464** | **+53,559** | **+56,868** | **+42,818** | **+39,977** | **+34,588** | **+28,119** | **99.987%** |
| K4 capital | 32/0/0 | 122,054 | +53,123 | +56,859 | +42,611 | +32,729 | +30,217 | +28,119 | 99.970% |

K3 improves paired own money by 705 and paired game advantage by 785 over K0;
28 games are identical and four improve, with no regression. The largest
effect is harmo-miu: both seats gain about 10.6k own money and 11.9k advantage.
TRACK occupies 22,974/23,008 decision steps; REPAIR only 34; FALLBACK zero.
Six weed triggers produce four completed transactions (2–7 steps) and two
bounded aborts. No repair exceeds eight steps.

Fresh K3 results by key comparison:

| Opponent | Games | W/L/T | Avg money | Avg advantage | P10 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 803 opening | 8 | 8/0/0 | 118,620 | +61,469 | +43,198 |
| R3 | 8 | 8/0/0 | 100,942 | +46,146 | +28,119 |
| lifecycle | 8 | 8/0/0 | 120,274 | +57,551 | +39,880 |
| harmo-miu | 2 | 2/0/0 | 153,261 | +44,149 | +44,149 |
| Somasundar | 2 | 2/0/0 | 161,609 | +66,872 | +66,518 |
| KKS | 2 | 2/0/0 | 145,168 | +41,676 | +41,676 |
| Asuran | 2 | 2/0/0 | 140,038 | +43,588 | +43,588 |

Controlled-shop and natural-RNG conclusions have the same positive sign.
Seat-0/seat-1 average advantages are +53,489/+53,630. There are zero runtime
failures, schema failures, livestock losses, meaningful stranded inventory,
failed critical transactions, or fallback activations. Two additional full
720-turn smoke games at seeds 997001/997002 complete DONE/DONE with money
142,458 and 130,727 for the candidate.

This passes the requested architectural promotion gate. The registry now
points to `agents/v27_replay_weed_guard.py`. `submission/main.py` remains
unchanged; standalone packaging is a separate milestone.

## 9. Direct answers to the 28 research questions

1. **Do strong agents replay stable routes?** Yes for the strongest observed
   F3/F4 submissions; no for every top submission. THUNDER/Dmitry are more
   state-dependent.
2. **Highest stability?** Valmorlee (99.69% field), Victor/Abracadabra
   (99.65%), Ueddy (99.53%); Victor combines stability with the strongest mean
   final economy.
3. **How many route families?** Four at the predeclared structural threshold.
4. **Strongest raw backbone?** Victor submission 55417289, medoid episode
   91876492.
5. **Raw unseen transfer?** 48/0/0, 108,187 money, +48,253 advantage, P10
   +27,535; fresh K0 32/0/0 and +52,775.
6. **Desynchronization events?** Stochastic weed blockage, then bounded
   positional/action offset; rare environment-specific crop/animal counts and
   sale/feed quantities. No hand/land drift in standard tests.
7. **Is weed repair necessary?** It triggers rarely but removes nine selection
   livestock losses and materially improves four fresh games; yes.
8. **Critical milestones?** Day-6/day-10 deeds, opening animal/seed waves,
   large strawberry/wheat seed waves and recurring feed are confirmable. They
   succeed reliably under standard rules; broad retries are harmful.
9. **Planned/actual hand mismatch?** Zero in standard 80 serious+fresh games.
10. **When suppress HIRE?** Only when actual hands already meet target or under
    nonstandard marginal cost/capital pressure; no standard suppression was
    justified.
11. **Infer opponent market?** Net flow yes; exact WHEAT/FERTILIZER action not
    always.
12. **Prediction accuracy?** Held-family-out Brier improves over constant
    baselines at all four horizons, most strongly at 8/12 turns.
13. **Is self-impact sufficient?** No theoretically; it omits opponent-first
    and capital timing, though V27's current ordering is already locally good.
14. **Delay-regret value?** Negative in K8: -1,846 average advantage versus K7.
15. **Current-turn reorder?** No. Exact permutation found zero beneficial
    changes.
16. **Future-slot assignment?** No validated gain; it creates stranding.
17. **Which reorders hurt?** Pulling a high-value future batch forward while
    displacing the current batch breaks later liquidation/feed/capital
    coordination.
18. **Useful existing safety guard?** None fired beneficially after weed repair
    on standard tests; K6 is identical to K5.
19. **Fallback?** It hides route bugs under artificial pressure and is never
    needed in standard tests; reject it for promotion.
20. **V27 action share?** 99.987% on fresh K3; 99.965% in selection.
21. **Largest correction improvement?** Worker-specific weed transactions.
22. **Trajectory preserved?** Yes: fixed hand/land trajectory, source exact,
    99.987% actions, 99.85% time in TRACK.
23. **Beat 803?** 8/0 selection and 8/0 fresh; fresh +61,469 average.
24. **Beat R3?** 8/0 selection and 8/0 fresh; fresh +46,146 average.
25. **Improve severe cluster?** Filip/Amer/Yankang/Prashant all become 2/0,
    with +18.2k/+41.6k/+21.7k/+43.3k.
26. **Fixed and natural RNG?** Both positive, with no sign conflict.
27. **Strongest final candidate?** `agents/v27_replay_weed_guard.py` (K3).
28. **Ready for packaging/Kaggle?** The evidence is clearly strong enough to
    justify a separate standalone packaging and Kaggle submission milestone.
    This study intentionally did neither.

## 10. Artifacts

- `agents/v27_backbone_common.py` and `agents/v27_k0_raw.py` …
  `agents/v27_k9_full.py`
- promoted wrapper: `agents/v27_replay_weed_guard.py`
- `v27_semantics_probe.py`
- `analyze_v27_routes.py`
- `analyze_v27_market_risk.py`
- `run_v27_replay_backbone.py`
- `experiments/v27_market_semantics.json`
- `experiments/v27_route_manifest.json`
- `experiments/v27_route_stability.json`
- `experiments/v27_market_risk_analysis.json`
- `experiments/v27_replay_backbone_results.json` (full telemetry)
- `experiments/v27_replay_backbone_results.compact.json`
- `experiments/v27_replay_backbone_fresh_confirmation.json`
