# E184: derivative of Moon v37; sale-window changes appended below.
# Historical comments describe their original layers, not the full derivative.
# Modified September 9, 2026 by prvsiyan: lossless single-file packaging only.
# Original policy and all 13 action tapes: yhay81, Shop Router 0909.
# https://www.kaggle.com/code/yhay81/shop-router-0909
# Sell timing / shed projection credit: aurax7 (see original docstring).
# Licensed under Apache License 2.0; full original license below.
# No routing, repair, sale, or liquidation rule has been changed.

"""Shop plans with small, observation-based repairs. Python standard library only.

The 13 complete action tapes live in actions.json. This file contains every rule:
choose a plan after two shops, delay weed-blocked work within the current day,
bring some planned sales forward one turn, and liquidate on the final turn.

Sell timing and shed projection follow aurax7's public Reactive Router:
https://www.kaggle.com/code/aurax7/kaggriculture-reactive-router
The shop-pair routes and worker-local, same-day queues were developed here.
"""

import copy
import json
from collections import deque
from pathlib import Path

import base64
import lzma
_INLINE_TAPES = json.loads((Path(__file__).resolve().parent / 'actions.json').read_text(encoding='utf-8'))

TURNS_PER_DAY = 24
ROUTE_STEP = 144
FINAL_PLAN_STEP = 648
LAST_STEP = 718
SHED_CAPACITY = 100
MAX_ORDERS = 10
PRODUCTS = (
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
    "EGG", "MILK", "WOOL", "FERTILIZER",
)
WEED_BLOCKED_WORK = {"PLANT", "BUILD_COOP", "BUILD_PASTURE"}
ANIMALS = {"GOOSE", "COW", "SHEEP"}

# Keys are the first two shops in their observed order; values index actions.json.
# All other pairs keep plan 0. Plan 1 is the previous yarn-market continuation.
# Plans 3..12 are the ten distinct continuations selected in the latest search.
SHOP_PLANS = {
    ("BAKERY", "YARN_STORE"): 3,
    ("BRUNCH_SPOT", "YARN_STORE"): 4,
    ("FARMERS_MARKET", "YARN_STORE"): 5,
    ("ICE_CREAM_SHOP", "YARN_STORE"): 6,
    ("PET_CAFE", "YARN_STORE"): 5,
    ("PIZZA_SHOP", "YARN_STORE"): 7,
    ("SMOOTHIE_SHOP", "YARN_STORE"): 8,
    ("YARN_STORE", "BAKERY"): 9,
    ("YARN_STORE", "BRUNCH_SPOT"): 9,
    ("YARN_STORE", "FARMERS_MARKET"): 1,
    ("YARN_STORE", "ICE_CREAM_SHOP"): 9,
    ("YARN_STORE", "PET_CAFE"): 10,
    ("YARN_STORE", "PIZZA_SHOP"): 6,
    ("YARN_STORE", "SMOOTHIE_SHOP"): 11,
    ("YARN_STORE", "YARN_STORE"): 12,
}


class FarmView:
    """Only the current own farm, private inventory, and public prices."""

    def __init__(self, observation):
        farm = observation["farms"][observation["player"]]
        private = observation["private"]
        self.tiles = farm["tiles"]
        self.positions = [farm["farmer"], *farm["hands"]]
        self.inventories = private["inventories"]
        self.shed = {item: max(0, int(qty)) for item, qty in private["shed"].items()}
        self.prices = observation["market"]["prices"]

    def inventory(self, worker):
        return self.inventories[worker] if worker < len(self.inventories) else {}

    def beside_shed(self, position):
        center = len(self.tiles) // 2
        return position[0] in (center - 1, center) and position[1] in (center - 1, center)


class DayState:
    """Per-player memory; queues expire at dawn and sales expire next turn."""

    def __init__(self):
        self.plan = 0
        self.last_step = -1
        self.day = -1
        self.queues = {}
        self.sale_due_step = -1
        self.advanced_sales = {}


def repair_weeds(action, view, state, step):
    """Insert DIG without consuming the blocked action; shift only this worker."""
    day = step // TURNS_PER_DAY
    if day != state.day:
        state.day = day
        state.queues.clear()  # Unfinished work never spills into tomorrow.

    workers = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
    for worker in range(min(len(workers), len(view.positions))):
        queue = state.queues.setdefault(worker, deque())
        queue.append(list(workers[worker]))
        x, y = view.positions[worker]
        tile = view.tiles[y][x]
        blocked = (queue[0][0] in WEED_BLOCKED_WORK
                   and isinstance(tile, dict) and tile.get("kind") == "WEED")
        workers[worker] = ["DIG"] if blocked else queue.popleft()
    action["farmer"], action["hands"] = workers[0], workers[1:]


def projected_shed(action, view):
    """Estimate stock after this turn's nearby PICKUP, DROP and PLACE actions.

    Preserve worker and inventory order: limited shed capacity can make it matter.
    This is the qualified lightweight estimate, not a full game simulation.
    """
    stock = {item: view.shed.get(item, 0) for item in PRODUCTS}
    stock.update(view.shed)
    total = sum(stock.values())
    workers = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
    for worker in range(min(len(workers), len(view.positions))):
        if not view.beside_shed(view.positions[worker]):
            continue
        work = workers[worker]
        operation = work[0] if work else "PASS"
        inventory = view.inventory(worker)
        if operation == "PICKUP" and len(work) >= 2 and work[1] in stock:
            quantity = max(0, int(work[2]) if len(work) >= 3 else 1)
            taken = min(stock[work[1]], quantity)
            stock[work[1]] -= taken
            total -= taken
        elif operation == "DROP":
            for item, held in inventory.items():
                added = min(max(0, int(held)), max(0, SHED_CAPACITY - total))
                if added > 0:
                    stock[item] = stock.get(item, 0) + added
                    total += added
        elif operation == "PLACE" and len(work) >= 2 and work[1] not in ANIMALS:
            item = work[1]
            quantity = max(0, int(work[2]) if len(work) >= 3 else 1)
            added = min(quantity, max(0, int(inventory.get(item, 0))),
                        max(0, SHED_CAPACITY - total))
            if added > 0:
                stock[item] = stock.get(item, 0) + added
                total += added
    return stock


def subtract_advanced_sales(action, state, step):
    """Remove quantities already requested one turn early, retaining order slots."""
    if state.sale_due_step == step:
        remaining = dict(state.advanced_sales)
        for order in action["market"]:
            if order and order[0] == "SELL" and len(order) >= 3:
                item = order[1]
                removed = min(max(0, int(order[2])), remaining.get(item, 0))
                if removed > 0:
                    order[2] = int(order[2]) - removed
                    remaining[item] -= removed
    state.advanced_sales = {}
    state.sale_due_step = -1


def advance_sales(action, view, state, tape, step):
    """Bring eligible sales from our next planned action forward by one turn."""
    next_step = step + 1
    if next_step > LAST_STEP or next_step % 72 == 0 or (step % 4 == 0 and step < 144):
        return
    planned = {}
    for order in tape[next_step].get("market") or []:
        if order and order[0] == "SELL" and len(order) >= 3 and order[1] in PRODUCTS:
            item = order[1]
            planned[item] = planned.get(item, 0) + max(0, int(order[2]))
    already_selling = {order[1] for order in action["market"]
                       if order and order[0] == "SELL" and len(order) > 1}
    stock = projected_shed(action, view)
    for item in PRODUCTS:
        if item in ("WHEAT", "FERTILIZER") or item in already_selling:
            continue
        quantity = min(stock.get(item, 0), planned.get(item, 0))
        if quantity <= 0 or int(view.prices.get(item, 0)) < 2:
            continue
        if len(action["market"]) >= MAX_ORDERS:
            break
        action["market"].append(["SELL", item, quantity])
        state.advanced_sales[item] = quantity
    if state.advanced_sales:
        state.sale_due_step = next_step


def liquidate(view):
    """On the last turn, drop reachable inventory and sell the projected shed."""
    workers = [["DROP"] if view.beside_shed(pos) and view.inventory(worker) else ["PASS"]
               for worker, pos in enumerate(view.positions)]
    action = {"farmer": workers[0], "hands": workers[1:], "market": []}
    stock = projected_shed(action, view)
    action["market"] = [["SELL", item, stock[item]] for item in PRODUCTS if stock[item] > 0]
    action["market"].sort(key=lambda order: -int(view.prices.get(order[1], 0)) * order[2])
    return action


class Policy:
    def __init__(self, folder):
        self.tapes = copy.deepcopy(_INLINE_TAPES)
        if len(self.tapes) != 13 or any(len(tape) != LAST_STEP + 1 for tape in self.tapes):
            raise ValueError("Expected 13 complete, 719-turn action tapes")
        self.players = {}

    def act(self, observation):
        step, player = int(observation["step"]), int(observation["player"])
        state = self.players.get(player)
        if state is None or step <= state.last_step:
            state = self.players[player] = DayState()
        state.last_step = step

        if step == ROUTE_STEP:
            shops = observation["town"]["unlocked_shops"]
            state.plan = SHOP_PLANS.get(tuple(shops[:2]), 0)
        if step == FINAL_PLAN_STEP:
            state.plan = 2

        view = FarmView(observation)
        tape = self.tapes[state.plan]
        action = copy.deepcopy(tape[step])
        repair_weeds(action, view, state, step)
        subtract_advanced_sales(action, state, step)
        advance_sales(action, view, state, tape, step)
        action["market"] = action["market"][:MAX_ORDERS]
        return liquidate(view) if step == LAST_STEP else action


_POLICY = None


def agent(observation, configuration=None):
    global _POLICY
    if _POLICY is None:
        # Kaggle's source loader omits __file__, but retains the code filename.
        folder = Path(agent.__code__.co_filename).resolve().parent
        _POLICY = Policy(folder)
    return _POLICY.act(observation)


# Full Apache license is retained in LICENSE.txt.

# Modified by prvsiyan: V216 adds an observed day-one hiring reserve.
# At most one wheat sale, at step23 only, preserving two projected wheat.
_V216_PARENT=agent
del agent

def agent(observation, configuration=None):
    action=_V216_PARENT(observation,configuration)
    step=int(observation['step'])
    if step!=23 or action.get('market'):
        return action
    player=int(observation['player'])
    state=_POLICY.players[player]
    tape=_POLICY.tapes[state.plan]
    hires=sum(bool(o) and o[0]=='HIRE' for o in tape[24].get('market',[]))
    if not 1<=hires<=5:
        return action
    mult=(configuration or {}).get('farmHandCostMult',1)
    required=sum((1,1,2,3,5)[i] for i in range(hires))*mult
    money=observation['farms'][player]['money']
    view=FarmView(observation)
    if (0<=money<required and projected_shed(action,view).get('WHEAT',0)>=3
            and view.prices.get('WHEAT',0)>=required-money):
        action=copy.deepcopy(action)
        action['market']=[['SELL','WHEAT',1]]
    return action


# Modified by prvsiyan: V217 adds bounded idle-farmer starvation rescue.
# Preserve native pending queues, planned feeds and wheat pickup obligations.
_V217_PARENT=agent
del agent
_V217_MOVES={'EAST':(1,0),'WEST':(-1,0),'NORTH':(0,-1),'SOUTH':(0,1)}

def _v217_farmer(tape, step):
    return list(tape[step].get('farmer') or ['PASS'])

def _v217_plan(view, st, step, action, pending):
    hour = step % 24
    if not 16 <= hour <= 21 or st.get('v217_used', 0) >= 2:
        return None
    if action.get('farmer') != ['PASS']:
        return None
    tape = _POLICY.tapes[st['plan']]
    end = min(step + 24 - hour, 719)
    if len(tape) < end:
        return None
    # Leave every existing planned feeding task intact. This conservative rule
    # also prevents a duplicate rescue when another worker is about to feed.
    reserved_wheat = sum(max(0,int(cmd[2]) if len(cmd)>2 else 1) for cmd in pending if len(cmd)>=2 and cmd[:2]==['PICKUP','WHEAT'])
    for planned in tape[step:end]:
        for cmd in [planned.get('farmer') or []] + list(planned.get('hands') or []):
            if cmd and cmd[0] == 'FEED':
                return None
            if len(cmd) >= 2 and cmd[:2] == ['PICKUP', 'WHEAT']:
                reserved_wheat += max(0, int(cmd[2]) if len(cmd) > 2 else 1)
    start = tuple(view.positions[0])
    inventory = view.inventory(0)
    need_pickup = inventory.get('WHEAT', 0) < 1
    if need_pickup:
        if any(inventory.values()) or not view.beside_shed(start):
            return None
        projected = projected_shed(action, view)
        if projected.get('WHEAT', 0) < max(2, reserved_wheat + 1):
            return None
    targets = []
    for y, row in enumerate(view.tiles):
        for x, tile in enumerate(row):
            if isinstance(tile, dict) and tile.get('animal') and not tile.get('fed_today') and tile.get('consecutive_unfed', 0) >= 1:
                targets.append((abs(x-start[0])+abs(y-start[1]), y, x))
    for distance, y, x in sorted(targets):
        moves = (['EAST'] * max(0, x-start[0]) + ['WEST'] * max(0, start[0]-x)
                 + ['SOUTH'] * max(0, y-start[1]) + ['NORTH'] * max(0, start[1]-y))
        opposite = {'EAST':'WEST','WEST':'EAST','NORTH':'SOUTH','SOUTH':'NORTH'}
        commands = ([['PICKUP','WHEAT']] if need_pickup else []) + [[m] for m in moves] + [['FEED']] + [[opposite[m]] for m in reversed(moves)]
        if len(commands) > end-step or any(_v217_farmer(tape, step+i) != ['PASS'] for i in range(len(commands))):
            continue
        positions = []
        pos = start
        for cmd in commands:
            positions.append(pos)
            if cmd[0] in _V217_MOVES:
                dx, dy = _V217_MOVES[cmd[0]]
                pos = (pos[0]+dx, pos[1]+dy)
        assert pos == start
        return {'step':step, 'route':st.get('plan'), 'commands':commands,
                'positions':positions, 'target':(x,y)}
    return None


def agent(observation, configuration=None):
    action=_V217_PARENT(observation,configuration)
    step=int(observation['step'])
    player=int(observation['player'])
    state=_POLICY.players[player]
    st=vars(state)
    view=FarmView(observation)
    task=st.get('v217_task')
    if task and step>=task['step']+len(task['commands']):
        task=st['v217_task']=None
    if task is None:
        # Pending work is part of this native router's actual schedule. Avoid
        # displacing the farmer or duplicating a delayed feed from any worker.
        pending=[cmd for queue in state.queues.values() for cmd in queue]
        if state.queues.get(0) or any(cmd and cmd[0]=='FEED' for cmd in pending):
            return action
        task=_v217_plan(view,st,step,action,pending)
        if task:
            st['v217_task']=task
            st['v217_used']=st.get('v217_used',0)+1
    if task is None:
        return action
    offset=step-task['step']
    if (not 0<=offset<len(task['commands']) or tuple(view.positions[0])!=task['positions'][offset]
            or state.plan!=task['route'] or action.get('farmer')!=['PASS']):
        st['v217_task']=None
        return action
    command=task['commands'][offset]
    if command==['FEED']:
        x,y=task['target'];tile=view.tiles[y][x]
        if not isinstance(tile,dict) or not tile.get('animal') or tile.get('fed_today') or view.inventory(0).get('WHEAT',0)<1:
            command=['PASS']
    action=copy.deepcopy(action)
    action['farmer']=command
    return action


# V218: terminal fertilizer collection by up to three otherwise idle workers.
# Inspired by Dmitrii Gluzdov's public Seven-Turn Rescue: collect, return, sell.
# https://www.kaggle.com/code/dmitriigluzdov/kaggriculture-seven-turn-rescue-best-lb-2800
# This smaller planner searches fertilizer-only trips. Existing productive tasks
# and market orders remain intact; a conservative physical bound rules out shed
# overflow. No future shared price or universal profit guarantee is assumed.
_V218_PARENT=agent
del agent
_V218_REPORT={'plans':0,'planned_units':0,'collections':0,'aborts':0,'capacity_declines':0}

def _v218_path(start, end, tiles):
    x,y=start
    result=[]
    for name,dx,dy,count in [('EAST',1,0,max(0,end[0]-x)),
                             ('WEST',-1,0,max(0,x-end[0])),
                             ('SOUTH',0,1,max(0,end[1]-y)),
                             ('NORTH',0,-1,max(0,y-end[1]))]:
        for _ in range(count):
            x+=dx;y+=dy
            if not (0<=y<len(tiles) and 0<=x<len(tiles[y])) or tiles[y][x]=='LOCKED':
                return None
            result.append([name])
    return result

def _v218_capacity_bound(view):
    total=sum(max(0,int(v)) for v in view.shed.values())
    total+=sum(max(0,int(v)) for inv in view.inventories for v in inv.values())
    for row in view.tiles:
        for tile in row:
            if not isinstance(tile,dict):continue
            total+=int(bool(tile.get('fertilizer_available')))
            if tile.get('animal') or tile.get('crop') in ('TOMATO','STRAWBERRY'):
                total+=max(0,int(tile.get('yield_units',0)))
            elif tile.get('crop'):
                # Absolute fertilized maxima, even for crops that will not be
                # harvested. Within steps712..718 there is no dawn production.
                bound={'WHEAT':12,'CARROT':8,'MELON':12}.get(tile['crop'])
                if bound is None:return 1000000
                total+=bound
    return total

def _v218_routes(start, targets, tiles, sheds):
    by_mask={}
    def visit(pos, mask, commands, count):
        if mask:
            for shed in sheds:
                home=_v218_path(pos,shed,tiles)
                if home is None:continue
                final=commands+home+[['DROP']]
                if len(final)<=7 and (mask not in by_mask or len(final)<len(by_mask[mask]['commands'])):
                    by_mask[mask]={'mask':mask,'count':count,'commands':final}
        if count>=3:return
        for i,target in enumerate(targets):
            if mask&(1<<i):continue
            walk=_v218_path(pos,target,tiles)
            if walk is None:continue
            route=commands+walk+[['COLLECT_FERTILIZER']]
            if len(route)>=7:continue
            if min(abs(target[0]-s[0])+abs(target[1]-s[1]) for s in sheds)+len(route)+1>7:continue
            visit(target,mask|(1<<i),route,count+1)
    visit(start,0,[],0)
    # Bounded search budget. All retained alternatives end with a real DROP.
    options=sorted(by_mask.values(),key=lambda r:(-r['count'],len(r['commands']),r['mask']))[:32]
    return options+[{'mask':0,'count':0,'commands':[]}]

def _v218_plan(observation, action):
    player=int(observation['player'])
    state=_POLICY.players[player]
    if state.plan!=2 or state.last_step!=712:return None
    view=FarmView(observation)
    if view.prices.get('FERTILIZER')!=1:return None
    tape=_POLICY.tapes[state.plan]
    remaining=tape[712:719]
    # No purchases, builds, planting, or fertilizer collection by the parent.
    # This keeps the physical production bound and target ownership simple.
    for planned in remaining:
        if any(o and o[0]!='SELL' for o in planned.get('market',[])):return None
        for c in [planned.get('farmer') or ['PASS']]+list(planned.get('hands') or []):
            if c and c[0] in ('PLANT','BUILD_COOP','BUILD_PASTURE','COLLECT_FERTILIZER'):return None
    if any(c and c[0] in ('PLANT','BUILD_COOP','BUILD_PASTURE','COLLECT_FERTILIZER')
           for queue in state.queues.values() for c in queue):return None
    if _v218_capacity_bound(view)>100:
        _V218_REPORT['capacity_declines']+=1
        return None
    current=[action.get('farmer') or ['PASS']]+list(action.get('hands') or [])
    idle=[]
    for i,pos in enumerate(view.positions):
        if any(view.inventory(i).values()) or state.queues.get(i):continue
        if i<len(current) and current[i]!=['PASS']:continue
        ready=True
        for planned in remaining[:-1]:
            commands=[planned.get('farmer') or ['PASS']]+list(planned.get('hands') or [])
            if i<len(commands) and commands[i]!=['PASS']:ready=False;break
        if ready:idle.append((i,tuple(pos)))
    idle=idle[:3]
    if not idle:return None
    half=len(view.tiles)//2
    sheds=[(x,y) for x,y in ((half-1,half-1),(half,half-1),(half-1,half),(half,half)) if view.tiles[y][x]!='LOCKED']
    targets=[(x,y) for y,row in enumerate(view.tiles) for x,t in enumerate(row)
             if isinstance(t,dict) and t.get('animal') and t.get('fertilizer_available')]
    if not targets or not sheds:return None
    choices=[_v218_routes(pos,targets,view.tiles,sheds) for i,pos in idle]
    best=[(-1,0),[]]
    def choose(index,used,chosen,count,cost):
        if index==len(choices):
            score=(count,-cost)
            if score>best[0]:best[:]=[score,list(chosen)]
            return
        for option in choices[index]:
            if used&option['mask']:continue
            choose(index+1,used|option['mask'],chosen+[option],count+option['count'],cost+len(option['commands']))
    choose(0,0,[],0,0)
    if best[0][0]<=0:return None
    tasks={}
    for (actor,start),option in zip(idle,best[1]):
        if not option['mask']:continue
        commands=option['commands']
        positions=[];pos=start
        for command in commands:
            positions.append(pos)
            if command[0] in _V217_MOVES:
                dx,dy=_V217_MOVES[command[0]];pos=(pos[0]+dx,pos[1]+dy)
        assert pos in sheds and commands[-1]==['DROP']
        tasks[actor]={'commands':commands,'positions':positions}
    _V218_REPORT['plans']+=1
    _V218_REPORT['planned_units']+=best[0][0]
    return tasks

def agent(observation, configuration=None):
    action=_V218_PARENT(observation,configuration)
    step=int(observation['step']);player=int(observation['player'])
    state=_POLICY.players[player]
    if step==712:
        state.v218_tasks=_v218_plan(observation,action)
    tasks=getattr(state,'v218_tasks',None)
    if not tasks or not 712<=step<=718:return action
    view=FarmView(observation)
    commands=[action.get('farmer') or ['PASS']]+list(action.get('hands') or [])
    commands+=[['PASS'] for _ in range(len(view.positions)-len(commands))]
    for actor,task in list(tasks.items()):
        offset=step-712
        if offset>=len(task['commands']):continue
        if actor>=len(view.positions) or tuple(view.positions[actor])!=task['positions'][offset]:
            del tasks[actor];_V218_REPORT['aborts']+=1;continue
        command=task['commands'][offset]
        if command==['COLLECT_FERTILIZER']:
            x,y=view.positions[actor];tile=view.tiles[y][x]
            if not isinstance(tile,dict) or not tile.get('fertilizer_available'):
                command=['PASS']
            else:_V218_REPORT['collections']+=1
        commands[actor]=command
    action=copy.deepcopy(action)
    action['farmer'],action['hands']=commands[0],commands[1:]
    return action

agent.telemetry=_V218_REPORT


# Appended to frozen V218 by build_v219_tomatoes.py.
# V219: a finite late tomato investment with dedicated, observed workers.
_V219_PARENT = agent
del agent
_V219_FERTILIZE = True  # Builder changes only this flag for the ablation.
_V219_STATES = {}
_V219_REPORT = {'commitments': 0, 'hire_requests': 0, 'confirmed_workers': 0,
                'hire_shortfalls': 0, 'plant_requests': 0, 'confirmed_plants': 0,
                'water_requests': 0, 'fertilize_requests': 0, 'harvest_requests': 0,
                'confirmed_harvest_units': 0, 'drop_requests': 0,
                'tomato_sale_requests': 0, 'budget_declines': 0, 'lost_plants': 0}


def _v219_fib(n):
    a, b = 1, 1
    for _ in range(n): a, b = b, a+b
    return a


def _v219_native_day(native, day):
    tape = _POLICY.tapes[2 if day >= 27 else native.plan]
    return tape[day*24:min((day+1)*24,719)]


def _v219_qualifies(obs, native):
    farm=obs['farms'][obs['player']]
    if len(farm['tiles']) != 10 or set(farm['unlocked_quadrants']) != {'NW','NE','SW'}:
        return False
    if farm['money'] < 12000 or obs['market']['prices']['TOMATO'] < 70:
        return False
    if sum(s in ('PIZZA_SHOP','FARMERS_MARKET') for s in obs['town']['unlocked_shops']) < 3:
        return False
    if any(farm['tiles'][y][x] != 'LOCKED' for y in (5,6) for x in range(5,10)):
        return False
    if obs['private']['seeds'].get('TOMATO',0) or obs['private']['shed'].get('TOMATO',0):
        return False
    if any(isinstance(t,dict) and t.get('crop')=='TOMATO' for row in farm['tiles'] for t in row):
        return False
    # The investment uses spare land and new worker indices. Avoid taking over
    # any native tomato or land purchase obligation on the known own schedule.
    for day in range(18,30):
        for a in _v219_native_day(native,day):
            if any(o and o[0]=='BUY_LAND' for o in a.get('market',[])):return False
            if any(c==['PLANT','TOMATO'] for c in [a.get('farmer')]+a.get('hands',[])):return False
    return True


def _v219_walk(pos, target):
    x,y=pos;tx,ty=target
    if x != tx:return ['EAST' if x < tx else 'WEST']
    if y != ty:return ['SOUTH' if y < ty else 'NORTH']
    return None


def _v219_home(pos):
    return min(((4,4),(5,4),(4,5),(5,5)),key=lambda p:abs(pos[0]-p[0])+abs(pos[1]-p[1]))


def _v219_request(obs, action, state, native):
    step=int(obs['step']);day=step//24;offset=step%24
    farm=obs['farms'][obs['player']];private=obs['private']
    # If the planting-day transaction could not complete, abandon investment.
    # Later purchases would miss the finite day26..29 production window.
    if not state.get('committed') and day!=18:return action
    if state.get('requested_day')==day or offset>3:return action
    planned=_v219_native_day(native,day)
    remaining=planned[offset+1:]
    if any(o and o[0]=='HIRE' for a in remaining for o in a.get('market',[])):
        return action
    parent_hires=sum(bool(o) and o[0]=='HIRE' for o in action['market'])
    expected=max(len(a.get('hands',[])) for a in planned)
    if len(farm['hands'])+parent_hires != expected:return action
    fertilizer=bool(_V219_FERTILIZE and day in (24,27) and obs['market']['prices']['FERTILIZER']<=30)
    # One watering tour: at most 2 entry moves + 9 between tiles + 10 waters.
    # A hire request by hour2 leaves at least21 callbacks after confirmation.
    crop_workers=1 if day in (19,20,21,22,23,25) and offset<=2 else (3 if 26<=day<=28 else 2)
    count=crop_workers+int(fertilizer and day==27)
    extra=[]
    if not state.get('committed'):
        extra += [['BUY_LAND'],['BUY_SEED','TOMATO',10]]
    if fertilizer:extra.append(['BUY_PRODUCT','FERTILIZER',10])
    extra += [['HIRE'] for _ in range(count)]
    if len(action['market'])+len(extra)>MAX_ORDERS:return action
    # No assumed sale proceeds. Reserve 3,000 for parent obligations and price
    # movement; the qualification separately requires 12,000 initial liquidity.
    budget=sum(_v219_fib(n) for n in range(farm['hires_today'],farm['hires_today']+parent_hires+count))
    if not state.get('committed'):budget+=4500
    if fertilizer:budget+=10*(obs['market']['prices']['FERTILIZER']+5)
    for order in action['market']:
        if not order:continue
        if order[0]=='BUY_PRODUCT':budget+=int(order[2])*(int(obs['market']['prices'][order[1]])+10)
        elif order[0]=='BUY_ANIMAL':budget+=int(order[2])*{'COW':400,'SHEEP':500,'GOOSE':300}[order[1]]
        elif order[0]=='BUY_SEED':budget+=int(order[2])*{'WHEAT':10,'CARROT':20,'TOMATO':50,'STRAWBERRY':100,'MELON':80}[order[1]]
    if farm['money']<budget+3000:
        _V219_REPORT['budget_declines']+=1;return action
    state['pending']={'step':step,'first_actor':expected+1,'count':count,'crop_workers':crop_workers,'fertilizer':fertilizer}
    state['requested_day']=day
    _V219_REPORT['hire_requests']+=count
    if not state.get('committed'):
        state['committed']=True;_V219_REPORT['commitments']+=1
    changed=copy.deepcopy(action);changed['market']+=extra
    return changed


def _v219_worker(obs, state, actor, role):
    day=int(obs['step'])//24;step=int(obs['step']);view=FarmView(obs)
    pos=tuple(view.positions[actor]);inv=view.inventory(actor)
    targets=role['targets']
    # Actual cargo differences, observed on the next callback, verify harvests.
    previous=state['last_work'].get(actor)
    if previous and previous['step']==step-1 and previous['command']==['HARVEST']:
        _V219_REPORT['confirmed_harvest_units']+=max(0,int(inv.get('TOMATO',0))-previous['tomatoes'])
    if role.get('needs_fertilizer') and not role.get('loaded'):
        home=_v219_home(pos)
        walk=_v219_walk(pos,home)
        if walk:return walk
        desired=10 if role['kind']=='fertilizer' else 5
        if inv.get('FERTILIZER',0)>=desired:role['loaded']=True
        elif role.get('pickup_requested'):
            # Never spend repeated turns waiting for stock that was not bought.
            role['loaded']=True;role['fertilizer_available']=int(inv.get('FERTILIZER',0))
        elif view.shed.get('FERTILIZER',0)>=desired:
            role['pickup_requested']=True;return ['PICKUP','FERTILIZER',desired]
        else:role['loaded']=True
    todo=[]
    for target in targets:
        x,y=target;tile=view.tiles[y][x]
        tomato=isinstance(tile,dict) and tile.get('crop')=='TOMATO'
        if tomato and target not in state['seen_plants']:
            state['seen_plants'].add(target);_V219_REPORT['confirmed_plants']+=1
        if target in state['seen_plants'] and not tomato and target not in state['lost']:
            state['lost'].add(target);_V219_REPORT['lost_plants']+=1
        command=None
        if role['kind']=='fertilizer':
            if tomato and tile.get('fertilized_until_day',-1)<day+2 and inv.get('FERTILIZER',0)>0:
                command=['FERTILIZE']
        elif day==18 and not tomato:
            if tile is None and obs['private']['seeds'].get('TOMATO',0)>0:command=['PLANT','TOMATO']
            elif isinstance(tile,dict) and tile.get('kind')=='WEED':command=['DIG']
        elif tomato:
            # No later production follows the final day, so watering then would
            # consume time needed to harvest and deliver the final cargo.
            if day<29 and not tile.get('watered_today'):command=['WATER']
            elif role.get('needs_fertilizer') and tile.get('fertilized_until_day',-1)<day+2 and inv.get('FERTILIZER',0)>0:
                command=['FERTILIZE']
            elif tile.get('yield_units',0)>0:command=['HARVEST']
        if command:todo.append((target,command))
    # Final return has priority once only the exact distance plus DROP remains.
    home=_v219_home(pos);distance=abs(pos[0]-home[0])+abs(pos[1]-home[1])
    if step>=718-distance and inv.get('TOMATO',0):
        return _v219_walk(pos,home) or ['PLACE','TOMATO',int(inv.get('TOMATO',0))]
    if todo:
        target,command=min(todo,key=lambda v:(abs(pos[0]-v[0][0])+abs(pos[1]-v[0][1]),targets.index(v[0])))
        return _v219_walk(pos,target) or command
    if inv.get('TOMATO',0):return _v219_walk(pos,home) or ['PLACE','TOMATO',int(inv['TOMATO'])]
    if any(inv.values()):return _v219_walk(pos,home) or ['DROP']
    return ['PASS']


def agent(observation, configuration=None):
    action=_V219_PARENT(observation,configuration)
    step=int(observation['step']);player=int(observation['player']);day=step//24
    state=_V219_STATES.get(player)
    if state is None or step<=state['last_step']:
        state={'last_step':step,'day':-1,'workers':{},'last_work':{},'seen_plants':set(),'lost':set(),
               'targets':[(x,y) for y in (5,6) for x in range(5,10)]}
        _V219_STATES[player]=state
    state['last_step']=step
    native=_POLICY.players[player]
    if step==432:state['eligible']=_v219_qualifies(observation,native)
    if not state.get('eligible') or day<18:return action
    if state['day']!=day:
        state['day']=day;state['workers']={};state['last_work']={}
    farm=observation['farms'][player]
    pending=state.pop('pending',None)
    if pending:
        if len(farm['hands'])+1 >= pending['first_actor']+pending['count'] and 'SE' in farm['unlocked_quadrants']:
            for index in range(pending['count']):
                fertilizer_worker=index==pending['crop_workers']
                if fertilizer_worker:targets=state['targets']
                elif pending['crop_workers']==1:targets=state['targets']
                elif pending['crop_workers']==2:targets=state['targets'][index*5:index*5+5]
                else:targets=[[(5,5),(6,5),(7,5)],[(8,5),(9,5),(9,6),(8,6)],[(5,6),(6,6),(7,6)]][index]
                state['workers'][pending['first_actor']+index]={'kind':'fertilizer' if fertilizer_worker else 'crop','targets':targets,
                    'needs_fertilizer':pending['fertilizer'] and (day==24 or fertilizer_worker)}
            _V219_REPORT['confirmed_workers']+=pending['count']
        else:_V219_REPORT['hire_shortfalls']+=pending['count']
    action=_v219_request(observation,action,state,native)
    if state['workers']:
        commands=[action.get('farmer') or ['PASS']]+list(action.get('hands') or [])
        commands += [['PASS'] for _ in range(len(farm['hands'])+1-len(commands))]
        for actor,role in state['workers'].items():
            if actor>=len(commands):continue
            command=_v219_worker(observation,state,actor,role)
            commands[actor]=command
            name={'PLANT':'plant_requests','WATER':'water_requests','FERTILIZE':'fertilize_requests',
                  'HARVEST':'harvest_requests','DROP':'drop_requests'}.get(command[0])
            if name:_V219_REPORT[name]+=1
            state['last_work'][actor]={'step':step,'command':command,'tomatoes':observation['private']['inventories'][actor].get('TOMATO',0)}
        action=copy.deepcopy(action);action['farmer'],action['hands']=commands[0],commands[1:]
    if state.get('committed') and len(action['market'])<MAX_ORDERS and not any(o[:2]==['SELL','TOMATO'] for o in action['market']):
        quantity=projected_shed(action,FarmView(observation)).get('TOMATO',0)
        if quantity>0:
            action=copy.deepcopy(action);action['market'].append(['SELL','TOMATO',quantity])
            _V219_REPORT['tomato_sale_requests']+=quantity
    return action


agent.telemetry=_V219_REPORT

# V221B: labor-only ablation of frozen V219G; not yet publicly scored.

# V224: prioritize already requested sales without crossing same-item purchases.
_V224_PARENT=agent
del agent
_V224_REPORT=dict(_V219_REPORT, reordered_market_turns=0)

def _v224_sales_first(action):
    original=action.get('market',[])[:MAX_ORDERS]
    orders=[list(o) for o in original if o and (o[0] in ('HIRE','BUY_LAND') or (len(o)>=3 and int(o[2])>0))]
    for index in range(len(orders)):
        order=orders[index]
        if order[0]!='SELL':continue
        cursor=index
        while cursor>0:
            previous=orders[cursor-1]
            if previous[0]=='SELL':break
            if previous[0] in ('BUY_PRODUCT','BUY_ANIMAL') and previous[1]==order[1]:break
            orders[cursor-1],orders[cursor]=orders[cursor],orders[cursor-1]
            cursor-=1
    if orders==original:return action
    _V224_REPORT['reordered_market_turns']+=1
    changed=copy.deepcopy(action);changed['market']=orders
    return changed

def agent(observation,configuration=None):
    action=_V224_PARENT(observation,configuration)
    if int(observation['step'])>=144:action=_v224_sales_first(action)
    _V224_REPORT.update(_V219_REPORT)
    return action

agent.telemetry=_V224_REPORT

# V224C: frozen sale timing ablation; no competition rating.

# V226: buy only a bounded shortage in already scheduled next-turn grain pickups.
_V226_PARENT=agent
del agent
_V226_DAY={}
_V226_REPORT=dict(_V224_REPORT, wheat_topup_orders=0, wheat_topup_units=0,
    wheat_topup_budget_declines=0, wheat_topup_capacity_declines=0)


def _v226_topup(obs,action,state,configuration=None):
    step=int(obs['step']);player=int(obs['player'])
    if configuration is not None and any(configuration.get(k,v)!=v for k,v in
        (('boardSize',10),('turnsPerDay',24),('shedCapacity',100),('maxMarketOrdersPerTurn',10))):return action
    if not 24<=step<696 or step%24==23 or (step+1)%72==0:return action
    market=action.get('market',[])[:MAX_ORDERS]
    if len(market)>=MAX_ORDERS:return action
    purchases={'HIRE','BUY_LAND','BUY_PRODUCT','BUY_ANIMAL','BUY_SEED'}
    if any(o and (o[0] in purchases or (len(o)>1 and o[1]=='WHEAT')) for o in market):return action
    tape=_POLICY.tapes[state.plan]
    nxt=tape[step+1]
    if any(o and o[0] in purchases for o in nxt.get('market',[])):return action
    view=FarmView(obs);commands=[action.get('farmer') or ['PASS'],*(action.get('hands') or [])]
    future=[nxt.get('farmer') or ['PASS'],*(nxt.get('hands') or [])]
    demand=0
    for actor,pos in enumerate(view.positions):
        current=commands[actor] if actor<len(commands) else ['PASS']
        x,y=pos
        if current and current[0] in _V217_MOVES:
            dx,dy=_V217_MOVES[current[0]];nx,ny=x+dx,y+dy
            if 0<=nx<10 and 0<=ny<10:x,y=nx,ny
        if not view.beside_shed((x,y)):continue
        pending=state.queues.get(actor)
        command=pending[0] if pending else (future[actor] if actor<len(future) else ['PASS'])
        task=vars(state).get('v217_task') if actor==0 else None
        if task:
            offset=step+1-task['step']
            if 0<=offset<len(task['commands']):command=task['commands'][offset]
        if len(command)>=2 and command[:2]==['PICKUP','WHEAT']:
            demand+=max(0,int(command[2]) if len(command)>2 else 1)
    stock=projected_shed(action,view)
    shortage=demand-stock.get('WHEAT',0)
    if not 0<shortage<=4:return action
    day=step//24
    previous=_V226_DAY.get(player)
    if previous is None or previous['day']!=day:
        previous=_V226_DAY[player]={'day':day,'units':0}
    if previous['units']+shortage>8:return action
    if sum(stock.values())+shortage>100:
        _V226_REPORT['wheat_topup_capacity_declines']+=1;return action
    quote=int(obs['market']['prices']['WHEAT'])
    if quote<1 or obs['farms'][player]['money']<100+shortage*(quote+10):
        _V226_REPORT['wheat_topup_budget_declines']+=1;return action
    result=copy.deepcopy(action)
    result['market']=market+[['BUY_PRODUCT','WHEAT',shortage]]
    previous['units']+=shortage
    _V226_REPORT['wheat_topup_orders']+=1;_V226_REPORT['wheat_topup_units']+=shortage
    return result


def agent(observation,configuration=None):
    if int(observation['step'])==0:_V226_DAY.pop(int(observation['player']),None)
    action=_V226_PARENT(observation,configuration)
    state=_POLICY.players[int(observation['player'])]
    action=_v226_topup(observation,action,state,configuration)
    _V226_REPORT.update(_V224_REPORT)
    return action

agent.telemetry=_V226_REPORT

# SPDX-License-Identifier: Apache-2.0
"""Bounded sale reservation across the next two or three known own actions.

Modified 2026-09-10 by Dmitrii Gluzdov. Extends the one-turn advancement in
yhay81 / aurax7 / prvsiyan's router, without reading future market observations.
This module is appended to the audited Moon policy during development staging.
"""

SALE_HORIZON = 2
ADVANCE_START = 288
_SALE_NATIVE_ADVANCE = advance_sales
_SALE_NATIVE_SUBTRACT = subtract_advanced_sales



def subtract_advanced_sales(action, state, step):
    # The opening finances land and the full herd. Preserve the parent's exact
    # behavior through day11, including any one-turn reservation due at288.
    if step < ADVANCE_START:
        return _SALE_NATIVE_SUBTRACT(action, state, step)
    if state.sale_due_step == step:
        _SALE_NATIVE_SUBTRACT(action, state, step)
    debts = getattr(state, 'sale_window_debts', {})
    due = debts.pop(step, {})
    for order in action['market']:
        if len(order) >= 3 and order[0] == 'SELL':
            removed = min(max(0, int(order[2])), due.get(order[1], 0))
            order[2] = int(order[2]) - removed
            due[order[1]] = due.get(order[1], 0) - removed
    state.sale_window_debts = {k: v for k, v in debts.items() if k > step}
    state.advanced_sales = {}
    state.sale_due_step = -1


def reserve_sales(action, view, state, tape, step):
    horizon = SALE_HORIZON if step >= 144 else 1
    if step < 144 and step % 4 == 0:
        return
    # Do not cross a route/shop boundary; its new plan is not chosen yet.
    end = min(LAST_STEP, step + horizon, (step // 72 + 1) * 72 - 1)
    if end <= step:
        return
    market = action['market']
    stock = projected_shed(action, view)
    blocked = {o[1] for o in market if len(o) > 1 and o[0] == 'BUY_PRODUCT'}
    selling = {}
    for order in market:
        if len(order) >= 3 and order[0] == 'SELL':
            selling.setdefault(order[1], []).append(order)
    blocked.update(c[1] for queue in state.queues.values() for c in queue
                   if len(c) > 1 and c[0] == 'PICKUP')
    blocked.update(c[1] for c in [action.get('farmer') or ['PASS'], *(action.get('hands') or [])]
                   if len(c) > 1 and c[0] == 'PICKUP')
    # Animal PLACE may fall back into the shed; the inherited projection does
    # not model it. Retain conservative no-advancement behavior in that case.
    commands = [action.get('farmer') or ['PASS'], *(action.get('hands') or [])]
    if any(len(c) > 1 and c[0] == 'PLACE' and c[1] in ANIMALS
           and view.inventory(i).get(c[1], 0) > 0 for i, c in enumerate(commands)):
        return
    debts = getattr(state, 'sale_window_debts', {})
    for item in PRODUCTS:
        if item in ('WHEAT', 'FERTILIZER') or item in blocked or view.prices.get(item, 0) < 2:
            continue
        current = sum(max(0, int(o[2])) for o in selling.get(item, []))
        available = max(0, int(stock.get(item, 0)) - current)
        if not available or (len(market) >= MAX_ORDERS and item not in selling):
            continue
        reservations = []
        for due_step in range(step + 1, end + 1):
            future = tape[due_step]
            # Preserve upcoming stock consumers, not just today's inventory.
            work = [future.get('farmer') or ['PASS'], *(future.get('hands') or [])]
            if any(len(c) > 1 and c[0] == 'PICKUP' and c[1] == item for c in work):
                break
            if any(len(o) > 1 and o[0] == 'BUY_PRODUCT' and o[1] == item for o in future.get('market', [])):
                break
            planned = sum(max(0, int(o[2])) for o in future.get('market', [])
                          if len(o) >= 3 and o[:2] == ['SELL', item])
            remaining = max(0, planned - debts.get(due_step, {}).get(item, 0))
            amount = min(available, remaining)
            if amount:
                reservations.append((due_step, amount))
                available -= amount
            if not available:
                break
        quantity = sum(amount for _, amount in reservations)
        if quantity:
            if item in selling:
                selling[item][-1][2] = int(selling[item][-1][2]) + quantity
            else:
                market.append(['SELL', item, quantity])
            for due_step, amount in reservations:
                debt = debts.setdefault(due_step, {})
                debt[item] = debt.get(item, 0) + amount
    state.sale_window_debts = debts


def advance_sales(action, view, state, tape, step):
    if step < ADVANCE_START:
        return _SALE_NATIVE_ADVANCE(action, view, state, tape, step)
    # The inherited call is before the tomato/fertilizer worker repairs. Defer
    # advancement until their final commands are available for stock projection.
    return None


_SALE_PARENT = agent


def agent(observation, configuration=None):
    action = _SALE_PARENT(observation, configuration)
    step = int(observation['step'])
    if step < ADVANCE_START or step >= LAST_STEP:
        return action
    state = _POLICY.players[int(observation['player'])]
    reserve_sales(action, FarmView(observation), state, _POLICY.tapes[state.plan], step)
    if step >= 144:
        action = _v224_sales_first(action)
    return action


agent.telemetry = _SALE_PARENT.telemetry

# SPDX-License-Identifier: Apache-2.0
"""A short extra lead only after repeated observed matching sale receipts.

September 11, 2026, Dmitrii Gluzdov. Conceptual inspiration: Aleksei Provorov's
public preemption probe. Matching cash is evidence, not knowledge of private
inventory. Preserve Herd-Safe's three-action window until two qualifying probes.
"""
MAX_SALE_HORIZON = 4
_RACE_STATES = {}
_RACE_PARENT = agent
_RACE_RESERVE = reserve_sales
_RACE_REPORT = {'probes':0, 'matched_probes':0, 'race_turns':0, 'extra_units':0}


def _race_signature(tile):
    if not isinstance(tile,dict):return None
    if tile.get('kind')=='PLANT':return ('PLANT',tile.get('crop'),tile.get('planted_day'))
    if tile.get('animal'):return (tile.get('kind'),tile.get('animal'),tile.get('placed_day'))
    return None


def _race_mirror(obs):
    a,b=obs['farms']
    if len(a['hands'])!=len(b['hands']) or set(a['unlocked_quadrants'])!=set(b['unlocked_quadrants']):return False
    aa=[_race_signature(t) for r in a['tiles'] for t in r]
    bb=[_race_signature(t) for r in b['tiles'] for t in r]
    if len(aa)!=len(bb):return False
    pairs=[(x,y) for x,y in zip(aa,bb) if x is not None or y is not None]
    return len(pairs)>=12 and sum(x==y for x,y in pairs)*10>=9*len(pairs)


def reserve_sales(action, view, state, tape, step):
    before={s:dict(v) for s,v in getattr(state,'sale_window_debts',{}).items()}
    _RACE_RESERVE(action,view,state,tape,step)
    state.race_probe=False
    for due,items in getattr(state,'sale_window_debts',{}).items():
        added=sum(max(0,n-before.get(due,{}).get(k,0)) for k,n in items.items())
        if due==step+3 and added>=4:state.race_probe=True
        if due>step+3:_RACE_REPORT['extra_units']+=added


def agent(observation,configuration=None):
    global SALE_HORIZON
    step,p=int(observation['step']),int(observation['player'])
    state=_RACE_STATES.get(p)
    if state is None or step!=state['last']+1:
        state=_RACE_STATES[p]={'last':step-1,'streak':0,'hits':0,'probe':False,'cash':None}
    mirror=_race_mirror(observation)
    state['streak']=state['streak']+1 if mirror else 0
    cash=tuple(int(observation['farms'][s]['money']) for s in (p,1-p))
    if state['probe'] and mirror and state['cash'] is not None:
        own,other=(cash[i]-state['cash'][i] for i in (0,1))
        if own>=100 and other>=100 and abs(own-other)<=max(5,own*.03):
            state['hits']+=1
            _RACE_REPORT['matched_probes']+=1
    race=step>=288 and state['streak']>=6 and state['hits']>=2
    SALE_HORIZON=MAX_SALE_HORIZON if race else 3
    if race:_RACE_REPORT['race_turns']+=1
    action=_RACE_PARENT(observation,configuration)
    logical=_POLICY.players[p]
    market=action.get('market',[])
    state['probe']=bool(step>=288 and mirror and getattr(logical,'race_probe',False)
                        and market and all(o[0]=='SELL' for o in market))
    if state['probe']:_RACE_REPORT['probes']+=1
    state['cash'],state['last']=cash,step
    return action


agent.telemetry=_RACE_REPORT

# SPDX-License-Identifier: Apache-2.0
"""Prioritize expensive existing sales within sale-only contiguous blocks.

Never move a sale across purchases or other market operations. Neither requested
quantities nor worker commands change. Current public quotes are not proceeds.
"""
SALE_PRIORITY_TOTAL = True
_PRIORITY_PARENT = agent

def _prioritize_sales(action, observation):
    if not 288 <= int(observation['step']) < 718:
        return action
    orders=action.get('market',[])
    prices=observation['market']['prices']
    result=list(orders)
    index=0
    while index<len(result):
        if len(result[index])<3 or result[index][0]!='SELL':
            index+=1
            continue
        end=index+1
        while end<len(result) and len(result[end])>=3 and result[end][0]=='SELL':end+=1
        block=result[index:end]
        # Repeated same-item orders can have execution-order meaning; abstain.
        if len({o[1] for o in block})==len(block):
            result[index:end]=sorted(block,key=lambda o: -max(0,int(prices.get(o[1],0)))*(max(0,int(o[2])) if SALE_PRIORITY_TOTAL else 1))
        index=end
    if result==orders:return action
    return dict(action,market=result)

def agent(observation,configuration=None):
    return _prioritize_sales(_PRIORITY_PARENT(observation,configuration),observation)

agent.telemetry=_PRIORITY_PARENT.telemetry

# E187: market-depth priority; official engine 1.32.7 price formula.
import math
DEPTH_MODE = 'impact'
MARKET_I0 = 10000

PRICE_FLOOR = 1

MARKET_PARAMS = {
    "WHEAT":      {"base":  25, "I0": MARKET_I0, "T": 400, "below_func": "sqrt",   "below_target": 0.80, "above_func": "log",    "above_target": 0.20},
    "CARROT":     {"base":  35, "I0": MARKET_I0, "T": 450, "below_func": "hinge",  "below_target": 1.00, "above_func": "sqrt",   "above_target": 0.70},
    "TOMATO":     {"base":  60, "I0": MARKET_I0, "T": 200, "below_func": "hinge",  "below_target": 0.40, "above_func": "sqrt",   "above_target": 0.60},
    "STRAWBERRY": {"base": 120, "I0": MARKET_I0, "T": 100, "below_func": "sqrt",   "below_target": 0.70, "above_func": "linear", "above_target": 1.60},
    "MELON":      {"base": 250, "I0": MARKET_I0, "T": 300, "below_func": "log",    "below_target": 0.20, "above_func": "sq",     "above_target": 3.60},
    "EGG":        {"base":  50, "I0": MARKET_I0, "T": 332, "below_func": "hinge",  "below_target": 0.40, "above_func": "log",    "above_target": 0.20},
    "MILK":       {"base": 160, "I0": MARKET_I0, "T": 122, "below_func": "sqrt",   "below_target": 0.60, "above_func": "linear", "above_target": 1.60},
    "WOOL":       {"base": 200, "I0": MARKET_I0, "T": 105, "below_func": "log",    "below_target": 0.20, "above_func": "sq",     "above_target": 3.20},
    "FERTILIZER": {"base": 100, "I0": MARKET_I0, "T": 200, "below_func": "linear", "below_target": 0.40, "above_func": "linear", "above_target": 0.40},
}

HINGE_GAIN = 8.0

def _shape(func, x, T=None):
    x = max(0.0, x)
    if func == "linear": return x
    if func == "sq":     return x * x
    if func == "sqrt":   return math.sqrt(x)
    if func == "log":    return math.log(1.0 + x)
    if func == "log10":  return math.log10(1.0 + x)
    if func == "hinge":
        # Degenerates to linear if T is missing or non-positive.
        if not T or T <= 0:
            return x
        u = x / T
        return u + HINGE_GAIN * max(0.0, u - 1.0) ** 2
    return x

def market_price(item, inventory, params=None):
    """Floor at PRICE_FLOOR."""
    p = (params or MARKET_PARAMS)[item]
    base = p["base"]
    I0 = p["I0"]
    T = p["T"]
    if inventory < I0:
        f = p["below_func"]
        amp = p["below_target"] * base / _shape(f, T, T)
        price = base + amp * _shape(f, I0 - inventory, T)
    else:
        f = p["above_func"]
        amp = p["above_target"] * base / _shape(f, T, T)
        price = base - amp * _shape(f, inventory - I0, T)
    return max(PRICE_FLOOR, int(round(price)))

def _depth_priority(action, observation):
    if not 288 <= int(observation['step']) < 718:
        return action
    view = FarmView(observation)
    commands = [action.get('farmer') or ['PASS'], *(action.get('hands') or [])]
    if any(len(c)>1 and c[0]=='PLACE' and c[1] in ANIMALS and view.inventory(i).get(c[1],0)>0 for i,c in enumerate(commands)):
        return action
    stock = projected_shed(action, view)
    inventory = observation['market'].get('inventory', {})
    params = observation['market'].get('params')
    orders = action.get('market', [])
    # The depth model supports one sale-only block with distinct products.
    # Abstain instead of guessing stock after a purchase or a prior sale block.
    if (params or len(orders)>10 or
        any(len(o)!=3 or o[0]!='SELL' or o[1] not in MARKET_PARAMS for o in orders) or
        len({o[1] for o in orders})!=len(orders)):
        return action
    if any(o[1] not in inventory or o[1] not in view.prices or
           market_price(o[1],inventory[o[1]])!=view.prices[o[1]] for o in orders):
        return action
    result = list(orders)
    def score(order):
        item = order[1]
        quantity = min(100, max(0,int(order[2])), max(0,int(stock.get(item,0))))
        if item not in inventory or item not in MARKET_PARAMS:
            return max(0,int(view.prices.get(item,0))) * quantity
        inv = inventory[item]
        immediate = sum(market_price(item,inv+k,params) for k in range(quantity))
        if DEPTH_MODE == 'net':
            return immediate
        # A stress scenario, NOT an estimate of hidden opponent inventory:
        # how much would this sale lose if a half-sized rival sale went first?
        delayed = sum(market_price(item,inv+(quantity+2-1)//2+k,params) for k in range(quantity))
        return immediate-delayed
    i = 0
    while i < len(result):
        if len(result[i])<3 or result[i][0]!='SELL':
            i += 1
            continue
        end = i+1
        while end<len(result) and len(result[end])>=3 and result[end][0]=='SELL':
            end += 1
        block = result[i:end]
        if len({o[1] for o in block}) == len(block):
            result[i:end] = sorted(block,key=lambda o:-score(o))
        i = end
    return action if result==orders else dict(action,market=result)

_DEPTH_PARENT = agent
def agent(observation, configuration=None):
    return _depth_priority(_DEPTH_PARENT(observation,configuration),observation)
agent.telemetry = _DEPTH_PARENT.telemetry

# V233: bounded, financed six-sheep SE discovery investment.
_V233_PARENT=agent
del agent
_V233_STATES={}
_V233_REPORT=dict(sheep_commit_requests=0,sheep_committed=0,sheep_hire_requests=0,
    sheep_workers_confirmed=0,sheep_hire_shortfalls=0,sheep_budget_declines=0,
    sheep_capacity_declines=0,sheep_purchase_shortfalls=0,sheep_feed_buy_requests=0,
    sheep_wool_harvested=0,sheep_fert_collected=0,sheep_extra_wool_sales=0,
    sheep_extra_fert_sales=0,sheep_rescue_feed_requests=0)

def _v233_eligible(obs,native):
    farm=obs['farms'][obs['player']];prices=obs['market']['prices']
    if len(farm['tiles'])!=10 or set(farm['unlocked_quadrants'])!={'NW','NE','SW'}:return False
    if obs['town']['unlocked_shops'].count('YARN_STORE')<2 or prices['WOOL']<220 or prices['WHEAT']>45:return False
    if any(farm['tiles'][y][x]!='LOCKED' for y in (5,6) for x in range(5,8)):return False
    if obs['private']['shed'].get('SHEEP',0) or any(i.get('SHEEP',0) for i in obs['private']['inventories']):return False
    for day in range(12,30):
        for a in _v219_native_day(native,day):
            if any(o and (o[0]=='BUY_LAND' or o[:2]==['BUY_ANIMAL','SHEEP']) for o in a.get('market',[])):return False
            if any(c and c[0] in ('PICKUP','PLACE') and len(c)>1 and c[1]=='SHEEP' for c in [a.get('farmer')]+a.get('hands',[])):return False
    return True

def _v233_request(obs,action,state,native):
    step=int(obs['step']);day=step//24;hour=step%24
    if hour>(2 if state.get('committed') else 1) or state.get('requested_day')==day:return action
    if not state.get('committed') and (day!=12 or not _v233_eligible(obs,native)):return action
    planned=_v219_native_day(native,day)
    if any(o and o[0]=='HIRE' for a in planned[hour+1:] for o in a.get('market',[])):return action
    farm=obs['farms'][obs['player']];market=action.get('market',[])
    parent_hires=sum(bool(o) and o[0]=='HIRE' for o in market)
    expected=max(len(a.get('hands',[])) for a in planned)
    if len(farm['hands'])+parent_hires!=expected:return action
    initial=not state.get('committed')
    extra=([['BUY_LAND'],['BUY_ANIMAL','SHEEP',6]] if initial else [])+[['BUY_PRODUCT','WHEAT',6],['HIRE'],['HIRE']]
    if len(market)+len(extra)>MAX_ORDERS:return action
    stock=projected_shed(action,FarmView(obs))
    incoming=6+6*initial
    budget=7000*initial+6*(int(obs['market']['prices']['WHEAT'])+10)
    budget+=sum(_v219_fib(n) for n in range(farm['hires_today'],farm['hires_today']+parent_hires+2))
    for o in market:
        if not o:continue
        if o[0]=='BUY_LAND':return action
        if o[0]=='BUY_PRODUCT':
            incoming+=int(o[2]);budget+=int(o[2])*(int(obs['market']['prices'][o[1]])+10)
        elif o[0]=='BUY_ANIMAL':
            incoming+=int(o[2]);budget+=int(o[2])*{'SHEEP':500,'COW':400,'GOOSE':300}[o[1]]
        elif o[0]=='BUY_SEED':budget+=int(o[2])*{'WHEAT':10,'CARROT':20,'TOMATO':50,'STRAWBERRY':100,'MELON':80}[o[1]]
    if sum(stock.values())+incoming>100:
        _V233_REPORT['sheep_capacity_declines']+=1;return action
    if farm['money']<budget+(3000 if initial else 1000):
        _V233_REPORT['sheep_budget_declines']+=1;return action
    state['requested_day']=day
    state['pending']={'first':expected+1,'initial':initial}
    _V233_REPORT['sheep_hire_requests']+=2;_V233_REPORT['sheep_feed_buy_requests']+=6
    if initial:_V233_REPORT['sheep_commit_requests']+=1
    result=copy.deepcopy(action);result['market']=market+extra
    return result

def _v233_worker(obs,actor,targets):
    farm=obs['farms'][obs['player']];private=obs['private'];step=int(obs['step'])
    pos=tuple(farm['hands'][actor-1]);inv=private['inventories'][actor]
    access=((4,4),(5,4),(4,5),(5,5))
    home=min(access,key=lambda p:(abs(pos[0]-p[0])+abs(pos[1]-p[1]),p))
    distance=abs(pos[0]-home[0])+abs(pos[1]-home[1])
    cargo=[item for item in ('WOOL','FERTILIZER') if inv.get(item,0)]
    if cargo and step%24 >= (22 if step//24==29 else 23)-distance:
        return _v219_walk(pos,home) or ['PLACE',cargo[0],inv[cargo[0]]]
    missing=sum(not(isinstance(farm['tiles'][y][x],dict) and farm['tiles'][y][x].get('animal')=='SHEEP') for x,y in targets)
    if missing and not inv.get('SHEEP',0) and private['shed'].get('SHEEP',0):
        return _v219_walk(pos,home) or ['PICKUP','SHEEP',min(missing,private['shed']['SHEEP'])]
    hungry=sum(not(isinstance(farm['tiles'][y][x],dict) and farm['tiles'][y][x].get('fed_today')) for x,y in targets)
    if hungry and not inv.get('WHEAT',0) and private['shed'].get('WHEAT',0):
        return _v219_walk(pos,home) or ['PICKUP','WHEAT',min(hungry,private['shed']['WHEAT'])]
    tasks=[]
    for target in targets:
        x,y=target;tile=farm['tiles'][y][x];command=None
        if tile is None:command=['BUILD_PASTURE']
        elif isinstance(tile,dict) and tile.get('kind')=='WEED':command=['DIG']
        elif isinstance(tile,dict) and tile.get('kind')=='PASTURE' and not tile.get('animal'):
            if inv.get('SHEEP',0):command=['PLACE','SHEEP']
        elif isinstance(tile,dict) and tile.get('animal')=='SHEEP':
            if not tile['fed_today'] and inv.get('WHEAT',0):command=['FEED']
            elif not tile['cared_today']:command=['CARE']
            elif tile['yield_units']:command=['HARVEST']
            elif tile['fertilizer_available']:command=['COLLECT_FERTILIZER']
        if command:tasks.append((abs(pos[0]-x)+abs(pos[1]-y),targets.index(target),target,command))
    if tasks:
        _,_,target,command=min(tasks);return _v219_walk(pos,target) or command
    if cargo:return _v219_walk(pos,home) or ['PLACE',cargo[0],inv[cargo[0]]]
    return ['PASS']

def _v234_rescue(obs,action,state):
    if not state['workers'] or int(obs['step'])%24>14:return action
    orders=action.get('market',[])
    if len(orders)>=MAX_ORDERS:return action
    if any(o and (o[0] in ('HIRE','BUY_LAND','BUY_ANIMAL','BUY_PRODUCT','BUY_SEED') or (len(o)>1 and o[1]=='WHEAT')) for o in orders):return action
    farm=obs['farms'][obs['player']];private=obs['private'];hungry=carried=0
    commands=[action.get('farmer') or ['PASS']]+list(action.get('hands') or [])
    for actor,targets in state['workers'].items():
        command=commands[actor]
        if command==['FEED'] or command[:2]==['PICKUP','WHEAT']:return action
        carried+=private['inventories'][actor].get('WHEAT',0)
        hungry+=sum(isinstance(farm['tiles'][y][x],dict) and farm['tiles'][y][x].get('animal')=='SHEEP' and not farm['tiles'][y][x].get('fed_today') for x,y in targets)
    stock=projected_shed(action,FarmView(obs))
    shortage=hungry-carried-stock.get('WHEAT',0)
    if not 0<shortage<=6 or state.get('rescue_today',0)+shortage>6:return action
    quote=int(obs['market']['prices']['WHEAT'])
    if quote<1 or farm['money']<1000+shortage*(quote+10) or sum(stock.values())+shortage>100:return action
    result=copy.deepcopy(action);result['market'].append(['BUY_PRODUCT','WHEAT',shortage])
    state['rescue_today']=state.get('rescue_today',0)+shortage
    _V233_REPORT['sheep_rescue_feed_requests']+=shortage
    return result

def agent(observation,configuration=None):
    action=_V233_PARENT(observation,configuration)
    step=int(observation['step']);player=int(observation['player']);day=step//24
    state=_V233_STATES.get(player)
    if state is None or step<=state['last_step']:
        state={'last_step':step,'day':-1,'workers':{},'work':{},'credit':{'WOOL':0,'FERTILIZER':0}}
        _V233_STATES[player]=state
    state['last_step']=step
    if configuration is not None and any(configuration.get(k,v)!=v for k,v in
        (('boardSize',10),('turnsPerDay',24),('shedCapacity',100),('maxMarketOrdersPerTurn',10))):return action
    if day<12:return action
    farm=observation['farms'][player];private=observation['private']
    if state['day']!=day:state['day']=day;state['workers']={};state['work']={};state['rescue_today']=0
    for actor,previous in state['work'].items():
        if previous['step']!=step-1 or actor>=len(private['inventories']):continue
        item={'HARVEST':'WOOL','COLLECT_FERTILIZER':'FERTILIZER'}.get(previous['command'][0])
        if item:
            gained=max(0,private['inventories'][actor].get(item,0)-previous['inventory'].get(item,0))
            state['credit'][item]+=gained
            _V233_REPORT['sheep_wool_harvested' if item=='WOOL' else 'sheep_fert_collected']+=gained
    pending=state.pop('pending',None)
    if pending:
        funded='SE' in farm['unlocked_quadrants'] and (not pending['initial'] or private['shed'].get('SHEEP',0)>=6)
        if not funded:_V233_REPORT['sheep_purchase_shortfalls']+=1
        elif len(farm['hands'])<pending['first']+1:_V233_REPORT['sheep_hire_shortfalls']+=1
        else:
            for i in range(2):state['workers'][pending['first']+i]=[(x,5+i) for x in range(5,8)]
            _V233_REPORT['sheep_workers_confirmed']+=2
            if pending['initial']:state['committed']=True;_V233_REPORT['sheep_committed']+=1
    action=_v233_request(observation,action,state,_POLICY.players[player])
    if not state.get('committed'):return action
    result=copy.deepcopy(action)
    commands=[result.get('farmer') or ['PASS']]+list(result.get('hands') or [])
    commands += [['PASS'] for _ in range(len(farm['hands'])+1-len(commands))]
    state['work']={}
    for actor,targets in state['workers'].items():
        command=_v233_worker(observation,actor,targets);commands[actor]=command
        state['work'][actor]={'step':step,'command':command,'inventory':dict(private['inventories'][actor])}
    result['farmer'],result['hands']=commands[0],commands[1:]
    result=_v234_rescue(observation,result,state)
    stock=projected_shed(result,FarmView(observation))
    for item in ('WOOL','FERTILIZER'):
        scheduled=sum(int(o[2]) for o in result['market'] if o[:2]==['SELL',item])
        count=min(state['credit'][item],max(0,stock.get(item,0)-scheduled))
        if count and len(result['market'])<MAX_ORDERS:
            result['market'].append(['SELL',item,count]);state['credit'][item]-=count
            _V233_REPORT['sheep_extra_wool_sales' if item=='WOOL' else 'sheep_extra_fert_sales']+=count
    return result

agent.telemetry=_V233_REPORT
kaggle_agent=agent

# V233H: reserve observed feed for animals already one missed refresh from escape.
_V233H_PARENT = agent
_V233H_REPORT = dict(at_risk_feed_orders=0, at_risk_feed_units=0,
                     at_risk_feed_capacity_declines=0, at_risk_feed_budget_declines=0)

def _v233h_feed_reserve(observation, action):
    step=int(observation['step']);player=int(observation['player']);day=step//24
    state=_V233_STATES.get(player)
    if not state or not state.get('committed') or step%24>14:return action
    if state.get('at_risk_feed_day')==day:return action
    farm=observation['farms'][player]
    at_risk=0
    for row in farm['tiles']:
        for tile in row:
            if (isinstance(tile,dict) and tile.get('animal') and not tile.get('fed_today')
                    and int(tile.get('consecutive_unfed',0))>=1):at_risk+=1
    if not at_risk:return action
    market=action.get('market',[])
    wheat_orders=[o for o in market if len(o)>=3 and o[:2]==['BUY_PRODUCT','WHEAT']]
    if not wheat_orders and len(market)>=MAX_ORDERS:return action
    units=min(6,at_risk)
    stock=projected_shed(action,FarmView(observation))
    incoming=sum(max(0,int(o[2])) for o in market if len(o)>=3 and o[0] in ('BUY_PRODUCT','BUY_ANIMAL'))
    if sum(stock.values())+incoming+units>SHED_CAPACITY:
        _V233H_REPORT['at_risk_feed_capacity_declines']+=1;return action
    quote=int(observation['market']['prices']['WHEAT'])
    if quote<1 or farm['money']<1000+units*(quote+10):
        _V233H_REPORT['at_risk_feed_budget_declines']+=1;return action
    result=copy.deepcopy(action);orders=result['market']
    existing=next((o for o in orders if len(o)>=3 and o[:2]==['BUY_PRODUCT','WHEAT']),None)
    if existing is None:orders.append(['BUY_PRODUCT','WHEAT',units])
    else:existing[2]=int(existing[2])+units
    state['at_risk_feed_day']=day
    _V233H_REPORT['at_risk_feed_orders']+=1;_V233H_REPORT['at_risk_feed_units']+=units
    return result

def agent(observation,configuration=None):
    action=_V233H_PARENT(observation,configuration)
    action=_v233h_feed_reserve(observation,action)
    _V233H_REPORT.update(_V233_PARENT.telemetry)
    return action

agent.telemetry=_V233H_REPORT
kaggle_agent=agent
