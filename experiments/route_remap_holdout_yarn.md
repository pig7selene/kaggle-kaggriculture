# Route remap held-out check (route_remap_pilot_yarn)

Pairs whose pilot best_mean_margin exceeded 2,000 -- Yarn-family routes forced on non-Yarn pairs, where the baseline plays the 105 family -- replayed on seeds the pilot never used, both seats. 60 games, 0 errors. Margins are against what the baseline actually plays on the pair. (The pilot's own 'gain_over_current' for these pairs was inflated by a mislabelled 'current' of route 0, which the router never selects; it is not shown.)

| Pair | Pilot best | In-sample margin | Held-out margin of pilot best | route 10 held-out | route 11 held-out |
| --- | ---: | ---: | ---: | ---: | ---: |
| FARMERS_MARKET + FARMERS_MARKET | 11 | +12,991 | -9,522 | -8,945 | -9,522 |
| SMOOTHIE_SHOP + PET_CAFE | 10 | +6,932 | -9,152 | -9,152 | -8,952 |
| BRUNCH_SPOT + FARMERS_MARKET | 10 | +5,308 | -12,939 | -12,939 | -11,484 |
| PET_CAFE + SMOOTHIE_SHOP | 7 | +2,047 | -6,148 | -9,259 | -6,273 |

Pilot-best route still positive on unseen seeds: 0/4. Every candidate reversed sign, and routes 10 and 11 are negative on every pair out of sample. The in-sample gains were the maximum of twelve noisy means over four games.
