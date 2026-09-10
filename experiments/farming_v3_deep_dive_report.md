# Farming Score V3 deep-dive report

## Executive result

The current public notebook was reconstructed exactly and is a genuinely strong policy, but it does not justify replacing the frozen CurrentBest. The exact V3 source won all 16 direct head-to-head games against CurrentBest and improved direct advantage by **+7,053.6** on average (95% bootstrap **+3,999.1 to +10,124.2**). Across the six-opponent league, however, its paired own-bank delta was only **+368.5** (95% bootstrap **−5,550.9 to +6,525.4**), with a **51.8%** negative rate and **−41,977** worst case. It was particularly weaker than CurrentBest against crop_dusta and nazmus.

## Provenance and reconstruction

Kaggle's current API identifies notebook version 4, last run 2026-09-05T14:29:18.4057716Z. The extracted source SHA-256 `d36ae976ad4a6316e6c1a27a5d04e9cc8e30300f21bdd31e749127c67a9311c4` matches the notebook's embedded expected hash. The agent compiles and completed 320 persisted local games with zero runtime or action-schema failures. Historical V1–V3 source could not be retrieved; apparent public score snapshots conflict and are treated only as unstable context.

## Architecture

This is **bounded adaptive replay**:

- two complete 719-turn tapes;
- one observable decision at turn 360;
- exactly 72 differing turns (360–431);
- an affordability guard at 72-turn boundaries;
- exception-safe PASS fallback.

The core farm is a wheat/premium-crop plus cow/sheep engine: two land expansions, 12-hand peak, 17 productive livestock placements, continuous feed/care/fertilizer loops, strawberry/melon revenue, and broad ongoing liquidation.

## Causal findings

The midseason route is the real innovation. Forced route 1 beat forced route 0 in **32/32** same-opening continuations by **+926.9 own coins** on average (95% bootstrap **+755.2 to +1,109.5**). Representative accounting attributes +528.5 to net revenue and +568 to lower spend, exactly reconciling a +1,096.5 bank difference in that smaller detailed sample.

The published selector chose route 1 in only 12 of 56 raw-league V3 appearances. Because forced route 1 won every causal continuation, the local evidence supports route 1 but does not validate the need for the BAKERY/PET_CAFE thresholds. The guard did not fire under normal cash. Under $2,000 starting cash it sold four wheat at turn 72 in all eight appearances and averaged +798 coins versus no guard, although that small CI crossed zero.

## Candidate and selection

A faithful one-change candidate, `agents/farming_v3_distilled/v1_force_route1.py`, was built. Its behavior was hash-equivalent to the evaluated force-route-1 wrapper in an explicit replay check. It raised the broad paired-own mean versus CurrentBest from +368.5 for published V3 to +839.7, but retained the same severe tail, a 51.8% negative rate, and an **−18,644 own / −22,692 advantage** mean regression versus crop_dusta. It therefore failed the conservative development gate; no finalist was locked and no independent final-validation panel was spent.

## Practical takeaways for CurrentBest

1. Preserve coherent multi-day continuations. V3's strongest gain is a complete 72-turn state-compatible block, consistent with earlier failures from arbitrary replay splicing.
2. Prefer the economic shape of route 1: fewer fertilizer purchases and hires during the midseason transition, with milk/wool revenue substituting for some wheat/fertilizer sales.
3. Separate private income from opponent suppression. V3 often improves advantage far more than own bank, which can look strong while masking fragile wealth production.
4. Keep the guard as a low-cash design pattern, not a normal-game source of score. It protects upcoming obligations cleanly, but it is inactive at standard cash in this sample.
5. Do not transplant raw turn actions into CurrentBest without a state owner/executor capable of preserving the whole farm trajectory.

## Decision

**Keep `agents/top50_distilled/top50_observable_portfolio.py` as CurrentBest.** Retain exact V3 and the force-route-1 candidate as research references. `experiments/current_best.json` and `submission/main.py` remain unchanged, and no Kaggle submission or upload was performed.
