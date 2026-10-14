"""Bounded hybrid A* with exact bicycle primitives and swept-body collision checks."""
import heapq
import math
from itertools import count
from Arrange_tools.vehicles import advance, minimum_radius


def search(auditor, start, gate, slot, allowed, roads, reverse_search=False):
    p=auditor.profile
    inward={'west':0,'east':math.pi,'north':math.pi/2,'south':-math.pi/2}[gate['side']]
    heading=inward if reverse_search else inward+math.pi
    direction=(math.cos(inward),math.sin(inward))
    inset=(p['rear_overhang'] if reverse_search else p['length']-p['rear_overhang'])+p['clearance']+.15
    target=(gate['point'][0]+direction[0]*inset,gate['point'][1]+direction[1]*inset)
    identity=dict(x=0,y=0,rotation=0)
    def error(a,b):return abs((a-b+math.pi)%(2*math.pi)-math.pi)
    def key(q,gear):return (round(q[0]/.15),round(q[1]/.15),round(q[2]/(math.pi/48))%96,gear)
    def heuristic(q):return math.hypot(q[0]-target[0],q[1]-target[1])+minimum_radius(p)*error(q[2],heading)*.25
    serial=count();queue=[(heuristic(start),next(serial),0,0)];nodes=[(start,None,[],[],1)]
    best={key(start,1):0};expanded=0
    while queue and expanded<12000:
        _,_,cost,index=heapq.heappop(queue)
        pose,parent,_,_,gear=nodes[index]
        if cost>best.get(key(pose,gear),float('inf'))+1e-9:continue
        expanded+=1
        delta=(pose[0]-target[0],pose[1]-target[1])
        lateral=abs(delta[0]*-direction[1]+delta[1]*direction[0])
        longitudinal=abs(delta[0]*direction[0]+delta[1]*direction[1])
        if longitudinal<.65 and lateral<max(0,(gate['width']-p['width'])/2-p['clearance']) and error(pose[2],heading)<.10:
            chunks=[]
            while index is not None:
                node=nodes[index];chunks.append((node[2],node[3]));index=node[1]
            path=[start];controls=[]
            for points,commands in reversed(chunks):path.extend(points);controls.extend(commands)
            return path,controls,expanded
        for sign in (1,-1):
            # Reverse driving remains local to parking; transit uses forward gear.
            if (sign*(-1 if reverse_search else 1))<0 and math.hypot(pose[0]-slot['x'],pose[1]-slot['y'])>8:continue
            for curvature in (0,1/minimum_radius(p),-1/minimum_radius(p),.5/minimum_radius(p),-.5/minimum_radius(p)):
                step=.10 if math.hypot(pose[0]-start[0],pose[1]-start[1])<7 else .25
                ds=sign*step;points=[];q=pose
                for _ in range(3):q=advance(q,ds,curvature);points.append(q)
                commands=[(ds,curvature)]*3
                check_path=[pose,*points];check_controls=commands
                if reverse_search:
                    check_path=list(reversed(check_path));check_controls=[(-d,k) for d,k in reversed(commands)]
                if not auditor._safe(check_path,check_controls,identity,allowed,roads,slot):continue
                newcost=cost+3*step*(1 if sign>0 else 1.25)+(.4 if sign!=gear else 0)
                state=key(q,sign)
                if newcost>=best.get(state,float('inf')):continue
                best[state]=newcost;nodes.append((q,index,points,commands,sign))
                heapq.heappush(queue,(newcost+1.6*heuristic(q),next(serial),newcost,len(nodes)-1))
    return None,None,expanded


def plan(auditor,slot,layout,allowed,roads):
    p=auditor.profile;offset=p['length']/2-p['rear_overhang'];attempts=0
    gates={g['role']:g for g in layout['gates']}
    for angle in (slot['angle'],slot['angle']+180):
        theta=math.radians(angle)
        goal=(slot['x']-offset*math.cos(theta),slot['y']-offset*math.sin(theta),theta)
        entry,ec,n=search(auditor,goal,gates['entry'],slot,allowed,roads,True);attempts+=n
        if entry is None:continue
        exit_path,xc,n=search(auditor,goal,gates['exit'],slot,allowed,roads);attempts+=n
        if exit_path is None:continue
        entry=list(reversed(entry));ec=[(-d,k) for d,k in reversed(ec)]
        identity=dict(x=0,y=0,rotation=0)
        return dict(status='passed',reason='entry_and_exit_path_witness_found',attempts=attempts,
                    parking_mode='searched_maneuver',turning_radius=minimum_radius(p),
                    entry_path=auditor._serialize(entry,ec,identity),exit_path=auditor._serialize(exit_path,xc,identity))
    return dict(status='unknown',reason='search_budget_exhausted_or_no_path',attempts=attempts,entry_path=[],exit_path=[])
