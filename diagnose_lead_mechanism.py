import sys, json, statistics
sys.path.insert(0, "/Users/infiniteejl/Projects/kaggriculture")
from pathlib import Path
from collections import defaultdict
from kaggle_environments import make
import kaggle_environments.envs.kaggriculture.kaggriculture as K
from run_route_remap_pilot import load_agent, BASE
PREM=("WOOL","MILK","STRAWBERRY","MELON"); PRODUCTS=list(K.MARKET_PARAMS)
LOG=[]; CUR={"step":None,"farms":None}
_orig_pm=K._process_market; _orig_cu=K._commit_unit
def pm(state, env):
    CUR["step"]=int(state[0].observation.step); CUR["farms"]=[id(f) for f in state[0].observation.farms]; return _orig_pm(state, env)
def cu(op,item,price,farm,private,market,shed_capacity=100):
    ok=_orig_cu(op,item,price,farm,private,market,shed_capacity)
    if ok and op=="SELL": LOG.append((CUR["step"], CUR["farms"].index(id(farm)), item, price))
    return ok
K._process_market=pm; K._commit_unit=cu
def play(variant, seed):
    LOG.clear()
    v=load_agent(Path(variant), f"d:{seed}:{variant[-8:]}"); b=load_agent(BASE, f"db:{seed}:{variant[-8:]}")
    env=make("kaggriculture", configuration={"episodeSteps":720,"seed":seed}, debug=False); env.run([v,b])
    return env, list(LOG)
seed=int(sys.argv[1]) if len(sys.argv)>1 else 4242
envA, logA = play("/private/tmp/kaggriculture_v43_variants/lead5.py", seed)
envB, logB = play(str(BASE), seed)
def summarize(name, env, log):
    last=env.steps[-1]; print(f"## {name}: money seat0 {last[0]['reward']:,.0f} seat1 {last[1]['reward']:,.0f}")
    rev=defaultdict(lambda:[0,0.0,0]); 
    for s,p,it,pr in log:
        r=rev[(p,it)]; r[0]+=1; r[1]+=pr; r[2]+= (pr<=1)
    print("| seat | item | units | revenue | avg | floor units |")
    for p in (0,1):
        for it in PREM+("EGG","CARROT","WHEAT","FERTILIZER","TOMATO"):
            u,r,f=rev[(p,it)]
            if u: print(f"| {p} | {it} | {u} | {r:,.0f} | {r/u:.0f} | {f} |")
    return rev
rA=summarize("lead5 (seat0) vs base (seat1)", envA, logA); rB=summarize("base vs base (counterfactual)", envB, logB)
print("\n## per-item revenue change vs counterfactual (seat0 = lead5 / base; seat1 = clone)")
for it in PREM:
    a0=rA[(0,it)][1]-rB[(0,it)][1]; a1=rA[(1,it)][1]-rB[(1,it)][1]
    print(f"{it}: ours {a0:+,.0f} (units {rA[(0,it)][0]-rB[(0,it)][0]:+d}, floor {rA[(0,it)][2]-rB[(0,it)][2]:+d}) | clone {a1:+,.0f} (units {rA[(1,it)][0]-rB[(1,it)][0]:+d}, floor {rA[(1,it)][2]-rB[(1,it)][2]:+d})")
# money split incl. non-premium
tot=lambda rev,p: sum(v[1] for (q,it),v in rev.items() if q==p)
print(f"total sell revenue: ours {tot(rA,0)-tot(rB,0):+,.0f} clone {tot(rA,1)-tot(rB,1):+,.0f}")
# ---- inference validation on game A: opp fills from inventory delta
steps=envA.steps; shops=steps[-1][0]["observation"]["town"]["unlocked_shops"]
def consumption(t, shops_t):
    c=defaultdict(int)
    if t%4==0:
        for sh in shops_t:
            prods=K.SHOPS[sh]; m=2 if len(prods)==1 else 1
            for it in prods: c[it]+=m
    if t%24==0:
        for it in K.TOWN_CENTER_PRODUCTS: c[it]+=1
    return c
true=defaultdict(lambda: defaultdict(int))   # (t,item) -> seat -> non-floor fills
for s,p,it,pr in logA:
    if pr>1: true[(s,it)][p]+=1
err=defaultdict(int); n=0; abs_err=0; tot_true=0
for t in range(0,718):
    inv0=steps[t][0]["observation"]["market"]["inventory"]; inv1=steps[t+1][0]["observation"]["market"]["inventory"]
    shops_t=steps[t][0]["observation"]["town"]["unlocked_shops"]; cons=consumption(t, shops_t)
    for it in PREM:
        est_opp=(inv1[it]-inv0[it]) + cons[it] - true[(t,it)][0]   # using our TRUE fills
        e=est_opp-true[(t,it)][1]; abs_err+=abs(e); tot_true+=true[(t,it)][1]; n+=1
        if e: err[e]+=1
print(f"\n## inference check (seat0's fills known exactly): abs error {abs_err} over {tot_true} true non-floor clone premium units; nonzero-error steps: {dict(sorted(err.items()))}")
# runtime-feasible estimate of OUR fills: sequential min(qty, shed at obs) — how far off is it?
off=0; ours_true=0
for t in range(0,718):
    obs=steps[t][0]["observation"]; shed=dict(obs["private"]["shed"]); act=steps[t+1][0]["action"] if isinstance(steps[t+1][0].get("action"),dict) else {}
    est=defaultdict(int)
    for o in (act.get("market") or []):
        if o and o[0]=="SELL" and len(o)>2 and o[1] in PREM:
            q=min(int(o[2]), shed.get(o[1],0)); shed[o[1]]=shed.get(o[1],0)-q; est[o[1]]+=q
    for it in PREM:
        tr=sum(1 for s,p,i2,pr in logA if s==t and p==0 and i2==it)
        off+=abs(est[it]-tr); ours_true+=tr
print(f"our-fill estimator (min(qty, shed at obs), premium): abs error {off} over {ours_true} true units")
