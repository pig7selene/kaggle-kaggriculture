# Super Replay Backbone V3 research report

## Decision

V3 was **not promoted**. Frozen V2 remains the research best. The one-branch
policy improved opponent-relative results, but failed the causal promotion gate:
paired own money was -16.0 in selection
and -30.1 on final holdout. Final paired
W/L/T was 12/16/16, only
42.9% decisive wins.

`submission/main.py` was not modified and nothing was submitted to Kaggle.

## 1–4. Corpus, versions, stability, families

The current Top-10 snapshot contains 10 active submission versions and 126
valid unique replays: 71 development, 24 selection, and 31 final holdout.
Those splits were fixed before action mining. Development contributed 82
deduplicated elite appearances. All 71 development replays had exact bank
reconstruction with zero unexplained mismatches.

Stability distribution: {'strongly_adaptive': 2, 'fixed_bounded_repair': 5, 'fixed': 3}. Three structural families were
found: a seven-route JALKARNA-like family, a rank-1/Nazmus family, and the
distinct researchstudio route.

| Rank | Team | Submission | Dev appearances | Stability | Avg source money |
|---:|---|---:|---:|---|---:|
| 1 | カワシギ | `55425101` | 9 | strongly_adaptive | 112,578 |
| 2 | researchstudio.site | `55435941` | 12 | strongly_adaptive | 91,322 |
| 3 | JALKARNA GAUTAM | `55463387` | 8 | fixed_bounded_repair | 102,655 |
| 4 | Yusuke Hayashi | `55463671` | 9 | fixed_bounded_repair | 85,987 |
| 5 | jasonstillchasin | `55470275` | 7 | fixed | 85,662 |
| 6 | MD. Nazmus Sakib Anik | `55445174` | 9 | fixed | 94,579 |
| 7 | MalelizarazoP | `55468815` | 5 | fixed_bounded_repair | 85,050 |
| 8 | Furious Monk | `55474695` | 9 | fixed | 84,277 |
| 9 | Suda | `55469248` | 9 | fixed_bounded_repair | 77,389 |
| 10 | Mohamed abdelrazik | `55476469` | 5 | fixed_bounded_repair | 98,051 |

## 5. Complete-route screen

| Route | W/L/T | Avg money | Avg advantage | P10 | P5 | Livestock losses |
|---|---:|---:|---:|---:|---:|---:|
| v3_raw_55445174 | 12/4/0 | 103,689 | +4,166 | -5,403 | -5,403 | 0 |
| v3_raw_55425101 | 6/10/0 | 109,017 | +982 | -6,090 | -7,063 | 2 |
| v3_raw_55474695 | 12/4/0 | 100,157 | +906 | -1,178 | -3,524 | 0 |
| v3_raw_55476469 | 13/3/0 | 112,998 | +854 | -2,925 | -6,440 | 0 |
| v3_raw_55469248 | 12/4/0 | 100,114 | +514 | -1,450 | -3,498 | 0 |
| v3_raw_55468815 | 7/9/0 | 99,888 | +170 | -1,700 | -3,497 | 0 |
| v3_raw_55463387 | 6/10/0 | 99,367 | +52 | -2,022 | -4,343 | 0 |
| super_backbone_v2 | 6/6/4 | 113,536 | -44 | -4,864 | -7,485 | 0 |
| v3_raw_55470275 | 7/9/0 | 100,020 | -45 | -2,656 | -5,604 | 0 |
| v3_raw_55463671 | 3/13/0 | 97,383 | -3,205 | -5,672 | -5,971 | 0 |
| v3_raw_55435941 | 0/16/0 | 94,891 | -8,509 | -14,292 | -15,834 | 80 |

Nazmus (`55445174`) was the strongest complete route: the serious paired set
showed 18/6 money wins against V2 and +25,436 average paired money. It was
rejected because two cows actually escaped at step 671 in two paired conditions
(four loss flags across fixed/natural records). Rank 1 was also unsafe. No
safe complete route robustly dominated V2.

## 6. Strongest coherent tail

The best compatible replacement was the Furious Monk tail at step 160
(`v3_tail_55474695_160`), entry distance 0.006. Its cheap screen was 12/4 with
+911 average advantage and zero losses. Direct paired money was only -77 over
16 states; in the larger development counterfactual set it was +5. The adjacent
step-240 version was nearly identical (+908); the Jason step-336 tail was
weaker (+236). Incompatible families were never spliced.

## 7. V2 failure clusters

Deployed V2 submission `55473991` had 76 valid public episodes: 70 wins and six
losses, with zero financial reconstruction mismatches. Land, hires, livestock,
crop cohorts, productive scale, worker routing, and end inventory remained
intact. Four of six losses developed a capital shortfall after preserved
physical production. The repeated weakness remains realized market revenue.

| Episode | Opponent | Cluster | First divergence | Margin |
|---:|---|---|---:|---:|
| 92546177 | Subramanya N | market_realization_deficit | 597 | -16,162 |
| 92567612 | Furious Monk | endgame_economic_disadvantage | 662 | -454 |
| 92570512 | Kris Adamatzky | market_realization_deficit | 529 | -5,024 |
| 92576132 | NIklitaCheporev | market_realization_deficit | 454 | -867 |
| 92588379 | CemBas | market_realization_deficit | 505 | -1,860 |
| 92613464 | Rayk Kretzschmar | endgame_economic_disadvantage | 670 | -1,192 |

## 8–10. Branch point, predicate, activation

Only synchronization-compatible step 160 was promoted to branch testing. The
best development rule was:

```text
if opponent_bank_at_step_160 <= 644:
    choose Furious-Monk tail
else:
    remain on V2
```

Development activation was 58.3% (14/24)
with +73.4 average gain. Selection activation
was 42.9%; final activation was
63.6%. Crucially, activated unseen states lost
-37.2 coins in selection and
-47.2 in final. The observational
threshold did not generalize causally.

## 11–18. Baseline, branch, selection, and final results

| Tier / agent | Games | W/L/T vs opponent | Avg money | Avg advantage | P10 | P5 |
|---|---:|---:|---:|---:|---:|---:|
| Selection V2 | 28 | 12/8/8 | 93,251 | -992 | -1,569 | -14,509 |
| Selection branch | 28 | 18/8/2 | 93,236 | -723 | -1,569 | -14,509 |
| Final V2 | 44 | 16/20/8 | 92,838 | +527 | -1,861 | -2,906 |
| Final branch | 44 | 25/15/4 | 92,808 | +994 | -1,254 | -2,700 |

Final natural-RNG paired own-money delta was
-49.0; fixed
RNG was -11.4;
elite traces were -29.9.

## 14 and 25. Oracle and remaining headroom

On 24 development counterfactual states:

- fixed V2 gain: 0 by definition;
- always-tail gain: +4.5;
- best simple branch gain: +73.4;
- perfect future-aware route oracle: +84.7.

The final two-route oracle gained only
+43.1. This is too little
headroom to justify a learned selector: the compatible replay family is near
its route-selection ceiling.

## 19–22. Tail, safety, and fidelity

Final branch P10 was -1,254 versus V2 -1,861; P5 was
-2,700 versus -2,906. These opponent-relative tail gains
did not compensate for negative paired own money. Both finalists had zero
runtime failures, semantic failures, livestock losses, meaningful stranding,
or fallback. Final route fidelity was 99.949126% for both.

## 23–26. Promotion and next architecture decision

- V3 promoted: **No**.
- Research best remains `agents/super_replay_v2/super_backbone_v2.py` SHA `c39d82b4f796271603e32ea8cb4b70261fbbe3d4e17940886caf5f5a6bd9adef`.
- Candidate branch SHA: `c61bbdcb92bcb872b5df16593cff892692ecac778f81464e95e702cc09c198c4` (research only, rejected).
- Remaining compatible replay-branch headroom: approximately 35–85 coins per
  game in these counterfactual pools—noise-level relative to V2 income.
- V4 should **not** add more replay branches and should **not** begin RL or a
  learned route selector: the oracle is not large enough. Continue replay
  mining only when a genuinely new, safe coherent family appears; otherwise
  study a narrowly bounded learned residual/market correction with a separate
  causal gate, not route selection and not policy-from-scratch RL.

## Final promotion checklist

- Positive paired mean: FAIL
- >=60% decisive paired wins: FAIL
- Positive natural RNG: FAIL
- Selection and final positive own-money delta: FAIL
- P10/P5 non-regression: PASS (opponent-relative)
- Runtime/semantic/livestock/stranding safety: PASS
- Low complexity: PASS (one branch)

The evidence does not justify replacing V2.
