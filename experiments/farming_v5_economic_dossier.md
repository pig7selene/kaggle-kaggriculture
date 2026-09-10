# Farming V5 economic dossier

## Policy classification

V5 is a **bounded state-adaptive guarded replay**. Its base is a replay/network assembled from attributed NIklitaCheporev and Kenjo1209 traces. Wrappers add sale allocation, weed and funding repair, observable demand-aligned COW/SHEEP substitution, a terminal animal frontier, latent-pasture activation/exact delivery, late-bundle diversification, and a final complete liquidation frontier. It uses public observation only—no opponent identity, hidden seed, reward, or future state.

## Economic phases

1. **Opening and first quadrant:** commit the day-0 melon and wheat geometry, begin the animal/structure route, and build low-cost labor.
2. **First production waves:** harvest/rotate wheat, service livestock, collect fertilizer, and sell into predefined nodes with funding repair.
3. **Information window:** `cow88` uses only direct Yarn evidence early; `cow150` sees the later shop state. V2 holds that direction through the `cow169`/`cow176` window.
4. **Expansion and strawberry buildout:** request land at steps 150 and 265; add later strawberry/wheat cohorts and continue bounded livestock substitutions.
5. **Mature economy:** monetize strawberry, milk, wool, fertilizer, wheat, and the melon cohort while the repair wrappers keep the replay feasible.
6. **Endgame:** stop through the inherited late programme and sell all visible sellable shed inventory at step 718.

## Mean six-condition dossier

| Metric | CurrentBest | V3 | V5 |
|---|---:|---:|---:|
| Final own money | 88869 | 103648 | 89540 |
| Advantage | 3776 | 19027 | 12542 |
| Peak hands | 12.0 | 12.0 | 12.0 |
| Peak animals | 13.3 | 17.0 | 14.0 |
| Land spend | 3000 | 3000 | 3000 |
| Labor spend | 5980 | 5914 | 6387 |
| Escape events | 0 | 0 | 6 |

The detailed commodity-level revenue, harvest, sales, realized prices, weighted sale days, and spending are preserved in `farming_v5_economic_attribution.json`.

## Crop cohorts

- **Melon:** the main 12-tile cohort is planted on day 0 (roughly steps 4–19), harvested around steps 245–264, and yields about 72 units. It is not the v2 innovation.
- **Strawberry:** multiple ongoing cohorts begin around the midgame and sell through roughly steps 381–701. Compared with V3, timing and quantities differ as part of another route, so there is no clean timing-only value estimate.
- **Wheat:** repeated small cohorts support both sales and livestock feed. Purchases/seeding continue late. At step 210 the exact-delivery system can still leave a pasture actor without carried feed, causing the documented escape.

## Livestock, labor, land, and market

The registered adaptive bundles are `cow88` (1), `cow150` (2), `cow169` (1), `cow176` (1), and `sheep313` (1). COW→SHEEP substitutions are capped at three and SHEEP→COW at one. The pressure score is `2*YARN_STORE + WOOL_price/200` versus `PIZZA + ICE_CREAM + SMOOTHIE + MILK_price/160`, adjusted by visible opponent cow/sheep balance.

Land timing is exactly the same as V3 and CurrentBest at requests 150/265. V5 typically reaches 12 hands. Its sale logic changes market exposure and can raise own money while helping the opponent even more: versus Crop Dusta, V5's paired own delta over CurrentBest is positive but its advantage delta is strongly negative.

## Terminal

The step-718 frontier is sensible and leaves only about 78 coins of mean measured sellable terminal value in the dossier. It was not introduced by the v2 timing change and was not isolated as a transferable gain.
