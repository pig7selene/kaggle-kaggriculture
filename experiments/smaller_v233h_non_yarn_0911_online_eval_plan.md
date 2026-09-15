# Online evaluation plan — SmallerShockV233HNonYarn0911

Status: **pre-registered, before any Kaggle submission of this candidate.**
Locked 2026-09-15. Do not edit the success criteria below after seeing results;
append a dated addendum instead if a criterion turns out to be unmeasurable.

## 1. Candidate identity

| Field | Value |
| --- | --- |
| Candidate path | `agents/smaller_market_shock_v233h_non_yarn_0911` |
| Research lock | `experiments/smaller_v233h_non_yarn_0911_lock_manifest.json` |
| Executable bundle SHA-256 | `acb8e2739b32bc9088145505af7034ed65fa576e00061ca19c3e2a97bf1f8651` |
| Full bundle SHA-256 (incl. LICENSE/NOTICE) | `04cd97b3d329813b148f55afde5df877ed8f73207a543d99447c278d19d2dd9e` |
| Archive path | `submission/smaller_market_shock_v233h_non_yarn_0911.tar.gz` |
| Archive SHA-256 | `baef9ecb866acb41a9bd069e813802a83353a7d772855a313082f4b605d43a03` |
| Parent | `agents/smaller_market_shock_v233h_safe` (`SmallerShockV233HSafe`) |
| Donor of the 8 non-Yarn tapes | yhay81, *Shop Router 0911 Simple* (Apache-2.0), `agents/_donors/shop_router_0911_simple/` |

## 2. Baselines

| Agent | Submission ID | Historical public score | Note |
| --- | ---: | ---: | --- |
| V233H Safe (this candidate's direct parent) | 56183575 | 2249.4 | 109W/26L/1T over 136 public games, GSR 0.8051 |
| Terminal D (`shop_router_0909_terminal`, highest verified LB agent) | 56138084 | 2496.8 | Different lineage entirely; not a parent/child of this candidate |

**Skill Rating caveat:** Gaussian Skill Rating is a dynamic, matchmaking-dependent
snapshot, not a fixed score. The two scores above were captured at different
times against different opponent pools (`experiments/lb_calibration_report.md`,
CASE D, found 99.05% of official opponents have unknown lineage, and separately
that local win/loss records failed to predict which of two of our own lineages
would rate higher online). Do **not** treat "candidate score > 2249.4" or
"candidate score > 2496.8" as a self-sufficient pass/fail number — it is one
input into the structural questions in §4, not the whole verdict.

## 3. Evaluation checkpoints

Analyze at official episode counts **30, 60, 100, 130+**, using
`analyze_online_submission.py --candidate non_yarn_0911` (§5). Each checkpoint
records, split where the tool supports it:

- W / L / T and GSR
- mean, median and worst cash margin (own money − opponent money)
- worst losses (bottom 10 by margin), separately for seat 0 and seat 1
- agent errors / incomplete episodes (non-`DONE` final status)
- livestock escapes, own and opponent
- shop-pair class: `yarn` / `added_non_yarn` (the 42 new routes) / `blacklisted_non_yarn`
  (the 7 pairs deliberately left on the inherited tape 0)
- per-shop-pair W/L/T and mean margin (`by_shop_pair` in the JSON output)
- opponent lineage, **only where independently identifiable** (team name match
  against a known public-agent list; do not guess from behavior alone)

Not automated, and out of scope for this pass (documented as a limitation in
`analyze_online_submission.py`'s module docstring): per-step semantic/action
legality checking against replay-recorded actions. Only the coarse
final-episode status flag is used as "agent_error" at each checkpoint.

## 4. Success criteria, defined before submission

**Primary question:**

> Do the 42 non-Yarn 0911 routes improve V233H Safe's non-Yarn weak spot on the
> real official opponent distribution?

Read from the checkpoint's `by_pair_class` breakdown: compare the
`added_non_yarn` class's W/L/T and mean margin against V233H Safe's own
non-Yarn performance. V233H Safe's local non-Yarn baseline is what motivated
this candidate in the first place (`experiments/smaller_v233h_non_yarn_0911_report.md`);
its **online** non-Yarn-only breakdown is not separately available (V233H
Safe's own online analysis did not classify by Yarn/non-Yarn), so this
comparison is necessarily: candidate's online non-Yarn cell vs. the *local*
non-Yarn screen result that justified the build, not an online-vs-online
comparison. State this limitation explicitly in every checkpoint write-up
rather than implying a same-domain comparison exists.

**Secondary questions**, each answered yes/no/inconclusive at every checkpoint:

1. **Tail losses**: is the candidate's `worst_margin` and count of losses below
   e.g. -5000 lower (less negative, fewer) than V233H Safe's online record
   (worst_margin -8176, from `experiments/smaller_v233h_online_submission.md`)?
2. **Yarn regression**: does the `yarn`-class cell (routes unchanged from the
   parent) show W/L/T or mean margin materially worse than V233H Safe's own
   online record? A regression here would mean something other than the
   intended change moved (e.g. the V0911 hand-slot normalizer layer touching
   Yarn routes it shouldn't).
3. **Unknown-lineage matchups**: among opponents that cannot be identified,
   does GSR or mean margin differ from the identified-opponent subset? (Only
   answerable if lineage identification succeeds for a nontrivial fraction —
   CASE D found it succeeds for under 1% of official opponents historically,
   so this question may stay "inconclusive: insufficient identified games"
   through every checkpoint, and that is an acceptable, honest answer.)
4. **Case-108109289-shaped failures**: any checkpoint loss on a market-shock /
   livestock-timing pattern resembling that seed (candidate holds a produced
   good through a premium-price collapse, or under-feeds livestock near a
   at-risk threshold)? Flag by hand from the worst-losses table; there is no
   automated detector for this specific pattern.
5. **New failure classes**: any livestock escape or agent error/incomplete
   episode that did not appear in V233H Safe's 136-game online record (which
   had zero of both)?

**Rating is one input, not the verdict.** A higher Skill Rating than 2249.4
without a "yes" on the primary question and no "yes" on secondary questions
2/5 is not sufficient to call the candidate an improvement — it could reflect
matchmaking-pool drift instead (see §2 caveat).

## 5. Analysis pipeline

Existing tooling, reused rather than rebuilt:

1. **Fetch episode list** — `kaggle competitions episodes <SUBMISSION_ID>` (per `AGENTS.md`).
2. **Download replays** — `kaggle competitions replay <EPISODE_ID> -p <replays-dir>` per episode id.
3. **Extract + classify + checkpoint** — new `analyze_online_submission.py`
   (this round's addition), which generalizes the existing
   `analyze_v233h_online_submission.py` (kept unchanged, still runs standalone
   for the V233H Safe baseline) to:
   - support any registered candidate via `--candidate`
   - resolve shop-pair Yarn/added-non-Yarn/blacklisted-non-Yarn class from the
     candidate's research lock's build receipt
   - compute the 30/60/100/130+ checkpoint table
   - detect livestock escapes and agent errors directly from official replay
     JSON (dict-shaped adaptation of `run_raw55899537_final_validation.animal_escapes`,
     which assumes local Struct-shaped `env.steps`)
   - diff against `experiments/v233h_safe_online_submission.json` when present

   **Verified working** against the still-present 136-game V233H Safe replay
   corpus at `/private/tmp/kaggriculture_v233h_online` (137 files, dated
   2026-09-13, not yet reaped): reproduced 109W/26L/1T, GSR 0.8051 exactly,
   matching the existing hand-written `smaller_v233h_online_submission.md`.
   The verification run's own output
   (`experiments/v233h_safe_online_submission.{json,md}`) was deleted after
   confirming the match, to avoid leaving a redundant near-duplicate of the
   existing report; re-running the command below regenerates it.

4. **Compare to baseline** — built into step 3's `baseline_diff` output when
   `--candidate non_yarn_0911` is used (looks for
   `experiments/v233h_safe_online_submission.json`). Regenerate that file
   first — `python analyze_online_submission.py --candidate v233h_safe
   --replays /private/tmp/kaggriculture_v233h_online` — before running the
   candidate's own analysis, since it was deleted per the note above (present
   only as long as that `/private/tmp` directory survives; see §6).

Command once episodes exist:

```bash
kaggle competitions episodes 56183575  # after actually submitting; replace with the real ID
kaggle competitions replay <EPISODE_ID> -p /private/tmp/kaggriculture_non_yarn_0911_online   # repeat per episode id
python analyze_online_submission.py --candidate non_yarn_0911 \
    --replays /private/tmp/kaggriculture_non_yarn_0911_online \
    --submission-id <ID> --public-score <SCORE>
```

## 6. Known risk to this plan itself

The V233H Safe replay corpus this plan's baseline diff depends on
(`/private/tmp/kaggriculture_v233h_online`, 4.2 GB, 137 files) lives outside
the repository and has already lost siblings to the same macOS `/private/tmp`
reaping that destroyed `v27_exact/`, `lb_gap_opponents/`, and 7
`current_meta_agents` entries (all reaped as of 2026-09-15 00:00; this
directory, dated 2026-09-13, has survived so far). Its aggregate is preserved
in the tracked `experiments/smaller_v233h_online_submission.md`, so the
Skill Rating / W-L-T / margin baseline is safe either way, but the per-episode
replay JSON needed to rebuild `experiments/v233h_safe_online_submission.json`
(and therefore the `by_pair_class`/`by_shop_pair` structural baseline this
plan's §4 secondary questions lean on) is not. This is flagged, not acted on,
per the same confirm-before-copying convention used for the Phase 2 donor
rescue.
