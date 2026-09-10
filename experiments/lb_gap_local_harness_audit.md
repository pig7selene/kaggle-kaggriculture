# Local evaluation harness audit

## Audited claims

The 64–0 broad league came from `run_shop_router_0909_hardened_final.py` under local `kaggle-environments==1.32.6`. It used eight historical opponents (`previous CurrentBest`, `V2`, `k3`, `nazmus`, `tetsuya`, `crop_dusta`, `oceanmix`, `farming_v3`), four seeds, both seats, and exactly eight games per opponent. Half the games (32/64) forced independently generated shop schedules; the other 32 used natural environment RNG. The 32 fixed games reduce to two fixed shop schedules repeated across eight opponents and both seats. Fresh environment instances and isolated agent imports reset every game.

The CurrentBest and V2 head-to-head claims each used 24 games: fixed and natural shop modes × six seeds × two seats. The score summaries were final own bank, raw bank advantage, and W/L/T—not Kaggle Skill Rating.

## Selection-bias findings

- The pool contained no Shop0909-derived near-mirror, no terminal-enhanced descendant, and no post-September-9 strategy.
- Historical replay/static families dominated. Opponent choice came after extensive local optimization against the same project lineage, creating family-level selection bias even when individual seed IDs were nominally fresh.
- Fixed shops were overweighted at 50%, whereas competition episodes use natural RNG.
- Only four broad-league seed IDs were used, with each opponent/fixed-mode/seat replication multiplying those conditions.
- The evaluator rewarded large margins. Official simulation rating ignores margin and observes only win/draw/loss, so +28,189 average advantage is not a score proxy.

## Refreshed design

The 1.32.7 primary panel used four frozen candidates, four public current-meta opponents, five natural seeds, and both seats (160 games; 40 per candidate). Two historical controls added 32 games. All shards were incremental/resumable and had zero runtime errors.
