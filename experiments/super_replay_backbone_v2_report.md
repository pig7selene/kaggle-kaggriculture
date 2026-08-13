# Super Replay Backbone V2

## Decision

**Promoted research best:** `agents/super_replay_v2/super_backbone_v2.py`, a
complete, highly stable JALKARNA GAUTAM elite route from submission `55463387`
plus exactly the frozen K3 bounded worker-specific weed repair.

This is a stronger complete backbone, not a broader online planner. No new
capital, SELL, hire, animal, crop, routing, or fallback heuristic was added.
`submission/main.py` stayed unchanged and nothing was submitted or uploaded.

## 1. Preservation

| Protected artifact | Frozen SHA-256 |
|---|---|
| V1 source | `96bd9cefd7c31075e47719ec1f9d1ee9391b467f68b956c65e0dd96478adb516` |
| Historical K3 source | `dc0100ec0d029a6362f92618429b09d7baba5b8a5257f20a61385fe82afeda51` |
| Deployed `submission/main.py` | `0b7c4fb3587f446a414cad30464522dab68ac64d88bc8f4e776e090e9b4cf1d8` |
| Pre-V2 current-best metadata | `a0cc2dc55ae26615772a658ce45ad7b31b67dc9278a18fd56fdd5f30d167a864` |

The first three remained byte-identical. Research-best metadata was updated
only after the locked final gate passed.

## 2. Real V1 Kaggle diagnosis

Submission `55467403` had 77 currently available complete public episodes. All
77 replay files were downloaded and validated: 58 wins, 19 losses, no ties.

The expected-state comparison rejected the most tempting repair hypotheses:

- Losses retained both deeds, the hand schedule, all livestock, crop geometry,
  and about 74 productive tiles.
- Losses and wins had essentially identical worker utilization: about 52.5%
  productive actions, 42.9% movement, and 4.6% idle.
- Harvest volume was also nearly identical. Losses averaged 99.8 melon, 212
  milk, 283.1 strawberry, 512.8 wheat, and 130.2 wool versus normal wins at
  101.0, 214.1, 285.1, 515.9, and 131.5.
- There were no repeated delayed-land, delayed-hire, livestock, worker-position,
  productive-tile, crop-cohort, or endgame-stranding signatures.
- Fifteen of 19 losses eventually fell at least $1,500 below Ricardo's expected
  bank, but this occurred after intact physical production. The source was
  realized product value—especially milk/strawberry market interaction—not a
  failed capital purchase.
- Weed repair averaged 0.89 activations in losses versus 0.56 normal wins. It
  contributes drift in isolated games, but does not explain the population loss
  pattern.

Thus no generic capital, worker, harvest, animal, or liquidation repair was
supported by repeated real evidence.

Four replay-ledger discrepancies occurred in one opponent seat late in episode
92448476; none affected our V1 ledger or the diagnosis.

## 3. Deep current Top-20 corpus

The read-only collector selected each current Top-20 team's highest-public-score
submission version and requested its 12 newest public appearances.

| Corpus item | Count |
|---|---:|
| Current selected submissions | 20 |
| Requested appearances | 240 |
| Unique episode IDs | 182 |
| Valid unique full replays | 181 |
| Selected elite appearances | 255 |
| Deduplicated development appearances | 171 |
| Development episode IDs | 153 |
| Untouched final-holdout episode IDs | 29 |
| Download failures / invalid replays | 0 / 0 |

Two newest selected appearances per submission were withheld until the finalist
hash lock. No candidate was tuned on those 29 episode IDs.

## 4. Stability and meta movement

Seventeen of 20 current submissions were highly fixed; the rank-1 and rank-3
routes were genuinely state-dependent, and one additional route clustered with
the rank-1 family. Three structural families emerged. All are mutations of the
previous meta rather than wholly new skeletons:

- Family 1: 17 fixed Victor/Ricardo-like routes.
- Family 2: rank 1 adaptive plus rank 6 stable early-land/lean-labor route.
- Family 3: rank 3 adaptive mixed-wool route.

JALKARNA's submission was unusually suitable as a replay backbone: 11
development appearances, A-class stability, 96.7% opening field stability,
100% first-expansion field/market stability, 100% second-expansion field
stability, 100% midgame field stability, and 90.7–96.5% mid/late market
stability. It preserves Ricardo's land, animal, labor, and crop geometry while
using a more productive full-season action/SELL schedule.

## 5. Phase and action-window evidence

Economic phases were defined by real capital events: opening 0–96, first
capital accumulation 96–144, first land/labor 144–240, first crop wave
240–336, midgame reinvestment 336–504, second crop wave 504–648, and final
production/liquidation 648–719.

Multiple stable family-1 routes showed large reconstructed midgame gains, but
single-phase attribution was confounded by money carried into each phase. The
controlled route experiments resolved this:

- JALKARNA tail from step 240: best phase splice, +2.4k direct advantage over
  V1 in the cheap screen, safe but weaker than the complete route.
- JALKARNA P3/P4 or P4-only: only about +0.4k direct, with no replay-transfer
  advantage.
- Malelizar tail: positive but weaker than JALKARNA.
- Nazmus midgame splices: catastrophic because entry distance was 35.5 and
  animal/crop state was incompatible; 148–160 livestock losses. Rejected.

Six elite-supported low-confidence market windows (wool, milk, premium, and a
combined midgame window) were also isolated. The combined window gained only
about +0.4k direct and the individual windows ranged from neutral to harmful.
This confirms that the gain is a coherent full-route effect, not one magic SELL.

## 6. Raw complete routes

Nineteen current complete routes plus V1 received a 16-game cheap screen using
paired fixed/natural V1 and recent V1-loss/Top-20 traces, both seats.

- Nazmus (`55445174`) had the best cheap mean (+1,343) but a 50% win rate and
  later lost livestock.
- JALKARNA (`55463387`) won 12/16 and beat V1 in all eight direct games.
- Malelizar (`55468815`) also beat V1 directly but transferred less well.
- The rank-3 adaptive medoid was unsafe (107 livestock losses).

The serious 32-game confirmation retained V1 plus four raw finalists:

| Complete route | W/L/T | Avg money | Avg advantage | Direct vs V1 | P10 | Livestock loss |
|---|---:|---:|---:|---:|---:|---:|
| V1 | 7/17/8 | 85,933 | −2,183 | control | −8,537 | 0 |
| Nazmus | 19/13/0 | 91,301 | +2,901 | +5,509 | −2,849 | 2 |
| **JALKARNA** | **24/8/0** | 87,598 | +1,550 | **16/0, +5,178** | −5,901 | **0** |
| Malelizar | 22/8/2 | 87,376 | +1,324 | 16/0, +4,774 | −5,662 | 0 |
| Yusuke | 22/10/0 | 87,314 | +729 | 16/0, +4,280 | −6,039 | 0 |

Nazmus was not eligible for promotion because its gain depended on a route that
lost cows in both fixed and natural instances of one seed.

## 7. Economic mechanism

Sixteen additional fixed-shop paired games attributed JALKARNA versus V1:

| Component | Average delta |
|---|---:|
| Final money | **+4,077** |
| Gross sale revenue | +4,157 |
| Total recorded spending | +80 |
| Animal / land / labor spend | 0 / 0 / 0 |
| Seed / feed spend | +43 / +38 |
| Milk revenue | +1,486 |
| Strawberry revenue | +1,026 |
| Wool revenue | +1,023 |
| Wheat revenue | +492 |
| Melon + fertilizer revenue | +131 |

The candidate completes about +7.6 milk, +17 wheat, +2.8 wool, and +1.6
strawberry harvest units per game while preserving the same land, animals, and
labor. V2 therefore fixes V1's real weakness through a better coordinated
complete production-and-sale route, not extra capital intensity.

## 8. Selection gate

Four candidates ran 48 games each on eight previously unused development
traces and eight new fixed plus eight natural seeds, both seats.

| Candidate | W/L/T | Avg money | Avg advantage | P10 | P5 | Safety |
|---|---:|---:|---:|---:|---:|---|
| V1 | 6/14/28 | 84,133 | −214 | −2,330 | −4,070 | clean |
| Nazmus complete | 26/22/0 | 87,755 | +1,722 | −3,359 | −3,487 | **6 animals lost** |
| JALKARNA tail | 44/4/0 | 84,543 | +1,820 | +292 | −255 | clean |
| **JALKARNA complete** | **46/2/0** | **90,368** | **+3,345** | **+550** | **+139** | **clean** |

The complete route beat V1 in all 32 direct selection games and advanced.
Finalist source hashes were locked before holdout access.

## 9. Locked final unseen validation

The final used 29 untouched current-Top-20 episode IDs plus eight new fixed and
eight new natural seeds, both seats: 90 games per finalist.

| Candidate | W/L/T | Avg money | Avg advantage | Median | P10 | P5 | Worst | Fidelity |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| V1 | 29/44/17 | 92,911 | −1,272 | 0 | −4,509 | −9,146 | −19,005 | 99.9540% |
| **V2** | **76/14/0** | **94,172** | **+2,549** | **+3,838** | **−375** | −9,208 | −19,498 | **99.9578%** |

Direct V2 versus V1 was **32/0**, +4,617 average advantage: fixed +4,667 and
natural +4,567, both with positive P10. On the untouched Top-20 traces V2 was
44/14 at +1,408 average, versus V1 at 21/37 and −1,973.

V2's P10 is 4,133 coins better than V1. P5 and worst are essentially unchanged,
so the promotion does not remove the rare adaptive-opponent tail but does not
materially deepen it either. Both seats were included throughout.

V2 had zero runtime failures, semantic failures, fallback activations,
livestock losses, and meaningful stranded-inventory games. Its route fidelity
was 99.9578%, with 42 bounded weed repairs in 90 games.

## 10. Failure clusters, repairs, and branching

The 14 final losses comprise:

- 8 opponent-economic-superiority losses, concentrated against the adaptive
  rank-1/rank-3 routes and the high-income Nazmus route;
- 4 small market-edge losses;
- 2 losses with multiple weed repair activations.

There was no repeated animal-service, capital-milestone, worker-matching,
harvest, or liquidation failure. No narrow repair passed the evidence gate;
the strongest narrow repair remains K3 weed repair. Limited branching was not
implemented because the adaptive families did not expose a stable 2–5 branch
policy, and V1 failures did not separate on an observable milestone state.

## 11. Promotion and next direction

V2 passes the architectural gate: >60% decisive win rate, >+$2,000 final mean,
32/0 direct H2H, positive natural RNG, positive recent-replay validation,
substantially improved P10, high fidelity, and clean safety. The promoted file
is:

`agents/super_replay_v2/super_backbone_v2.py`

SHA-256:

`c39d82b4f796271603e32ea8cb4b70261fbbe3d4e17940886caf5f5a6bd9adef`

The underlying route action hash is
`9438f4a024ce5e219f08bb5ee22a6cf1df43d3d55fed9606f0e78f57fb479a28`.

Replay mining is not yet fully saturated because a stronger complete stable
route appeared immediately in the deeper Top-20 corpus. The next research
phase should analyze the small number of genuinely adaptive rank-1/rank-3
agents as a frozen backbone plus a few branch predicates. RL is premature.
If fixed-route mining later stalls and losses remain state-dependent, the right
learning direction is a residual policy over this frozen V2 backbone—not RL
from scratch.

No deployment package was modified and nothing was submitted to Kaggle.
