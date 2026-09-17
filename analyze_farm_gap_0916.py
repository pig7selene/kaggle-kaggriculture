"""Farm gap by town class from the 9/16 scan: V43-farm agents versus adapted farms."""
import json, statistics
from collections import defaultdict
rows=json.load(open("experiments/farm_gap_0916.rows.json"))
MILK={"PIZZA_SHOP","ICE_CREAM_SHOP","SMOOTHIE_SHOP"}; WOOL={"YARN_STORE"}; CARROT={"PET_CAFE","FARMERS_MARKET"}; TOM={"PIZZA_SHOP","FARMERS_MARKET"}
def cls(town):
    t=set(town[:2]); return ("yarn" if t&WOOL else "noyarn")+"/"+("milk" if t&MILK else "nomilk")
lin=lambda a: a>=0.9
g=defaultdict(list); mixes=defaultdict(list)
for r in rows:
    for s in range(2):
        me,op=s,1-s
        if lin(r["agree"][me]) and not lin(r["agree"][op]):
            g[cls(r["town"])].append(r["money"][op]-r["money"][me])
            mixes[cls(r["town"])].append((r["mix"][op][0], r["mix"][op][1], r["quads"][op], r["mix"][me][1], r["quads"][me]))
print("games where a V43-farm agent met a non-V43 agent, by first-two-shop class; margin = non-V43 minus V43:")
for k,v in sorted(g.items()):
    print(f"  {k:14s} n={len(v):3d} mean {statistics.mean(v):+8,.0f} median {statistics.median(v):+8,.0f} | non-V43 wins {sum(x>0 for x in v)/len(v):.0%}")
allv=[x for v in g.values() for x in v]; print(f"  overall n={len(allv)} mean {statistics.mean(allv):+,.0f} median {statistics.median(allv):+,.0f}")
print("\nnon-V43 opponents' animals and quadrants vs V43's, by class (means):")
for k,v in sorted(mixes.items()):
    def m(key, idx): 
        xs=[x[idx].get(key,0) for x in v]; return statistics.mean(xs)
    print(f"  {k:14s} them: COW {m('COW',1):.1f} SHEEP {m('SHEEP',1):.1f} GOOSE {m('GOOSE',1):.1f} quads {statistics.mean(x[2] for x in v):.1f} | V43: COW {m('COW',3):.1f} SHEEP {m('SHEEP',3):.1f} GOOSE {m('GOOSE',3):.1f} quads {statistics.mean(x[4] for x in v):.1f}")
    crops=defaultdict(list)
    for x in v:
        for c in ("WHEAT","CARROT","TOMATO","STRAWBERRY","MELON"): crops[c].append(x[0].get(c,0))
    print(f"  {'':14s} their crops: "+" ".join(f"{c} {statistics.mean(xs):.0f}" for c,xs in crops.items()))
# lineage vs lineage: how many, and V43 quads
ll=[r for r in rows if lin(r["agree"][0]) and lin(r["agree"][1])]; print(f"\nV43 vs V43 games: {len(ll)} | V43 quadrants at 500: {statistics.mean(q for r in rows for s in range(2) if lin(r['agree'][s]) for q in [r['quads'][s]]):.2f}")
