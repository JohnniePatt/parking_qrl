"""Bicycle arc witnesses with bounded hybrid A* fallback for all stall templates.

No path found remains UNKNOWN; road traffic directions are enforced.
"""
from copy import deepcopy
import json
import math
from itertools import product
from collections import OrderedDict
from Arrange_tools.geometries import polygon, rotate
from Arrange_tools.vehicles import advance, footprint, minimum_radius, validate
from Arrange_tools.Policies import accesses


class Auditor:
    def __init__(self,profile,templates):
        validate(profile)
        self.profile=deepcopy(profile)
        self.templates=templates
        self.cache=OrderedDict()

    def audit(self,items,layout,resolution):
        key=json.dumps([items,layout,resolution,self.profile],sort_keys=True,allow_nan=False)
        if key in self.cache:
            self.cache.move_to_end(key)
            return deepcopy(self.cache[key])
        results=[]
        for slot in (i for i in items if i['kind']=='slot'):
            try:
                result=self._slot(slot,items,layout,resolution)
            except ImportError:
                result=dict(status='unknown',reason='shapely_dependency_missing',entry_path=[],exit_path=[])
            results.append(dict(slot_id=slot['id'],**result))
        report=dict(method='bicycle_templates_and_hybrid_astar_v2',vehicle=deepcopy(self.profile),
                    minimum_rear_axle_radius=minimum_radius(self.profile),
                    passed=sum(r['status']=='passed' for r in results),
                    failed=sum(r['status']=='failed' for r in results),
                    unknown=sum(r['status']=='unknown' for r in results),slots=results,
                    certification=False,other_stalls_assumed_occupied=True)
        self.cache[key]=deepcopy(report)
        while len(self.cache)>32:
            self.cache.popitem(last=False)
        return report

    def _slot(self,slot,items,layout,resolution):
        result=self._template(slot,items,layout,resolution)
        if result['status']!='unknown':
            return result
        from Arrange_tools.Policies.paths import plan
        allowed=self._allowed(slot,items,layout,resolution)
        return plan(self,slot,layout,allowed,[i for i in items if i['kind']=='road'])

    def _allowed(self,slot,items,layout,resolution):
        from shapely.geometry import Polygon, box
        from shapely.ops import unary_union
        from shapely.prepared import prep
        roads=[i for i in items if i['kind']=='road']
        # The angled rectangle's mouth lies above its projected frontage line.
        # Include that unmarked entrance apron, blocked by every other stall.
        angle=self.templates[slot['template']]['angle']
        mouth=[rotate((-slot['length']/2,side*slot['width']/2),angle) for side in (-1,1)]
        local_corners=[rotate((x-slot['x'],y-slot['y']),-slot['rotation']) for x,y in polygon(slot)]
        bottom=min(y for x,y in local_corners)-resolution-0.01
        apron=[]
        # Extend the stall mouth along the vehicle axis to the aisle, not vertically.
        # A vertical projection clips the rear corners of a car in an angled stall.
        theta=math.radians(angle)
        extension=max(0,(max(y for x,y in mouth)-bottom)/math.sin(theta)) if math.sin(theta)>1e-8 else 0
        approach=[(x-extension*math.cos(theta),y-extension*math.sin(theta)) for x,y in mouth]
        for x,y in [*mouth,*approach]:
            dx,dy=rotate((x,y),slot['rotation'])
            apron.append((slot['x']+dx,slot['y']+dy))
        zone=unary_union([Polygon(polygon(r)) for r in roads]+[
            Polygon(polygon(slot)).buffer(resolution+0.01,join_style=2),Polygon(apron).convex_hull])
        blockers=[Polygon(polygon(i)) for i in [*layout['obstacles'],*items]
                  if i.get('kind')!='road' and i['id']!=slot['id']]
        zone=zone.intersection(box(0,0,layout['width'],layout['height']))
        if blockers:
            zone=zone.difference(unary_union(blockers))
        return prep(zone)


    def _template(self,slot,items,layout,resolution):
        from shapely.geometry import Polygon, box
        from shapely.ops import unary_union
        from shapely.prepared import prep
        p=self.profile
        result=lambda status,reason:dict(status=status,reason=reason,entry_path=[],exit_path=[])
        if slot['length']<p['length']+2*p['clearance'] or slot['width']<p['width']+2*p['clearance']:
            return result('failed','vehicle_does_not_fit_stall')
        roads=[i for i in items if i['kind']=='road']
        if accesses.check(items,layout,self.templates,resolution):
            return result('failed','layout_access_policy_failed')
        if any(g['width']<p['width']+2*p['clearance'] for g in layout['gates']):
            return result('failed','gate_too_narrow_for_vehicle')
        if slot['template']=='parallel':
            return result('unknown','requires_maneuver_search')
        allowed=self._allowed(slot,items,layout,resolution)
        rotation=slot['rotation']
        alpha=math.radians(self.templates[slot['template']]['angle'])
        offset=p['length']/2-p['rear_overhang']
        gate_by_role={g['role']:g for g in layout['gates']}
        local_gates={}
        normals={'west':(1,0),'east':(-1,0),'north':(0,1),'south':(0,-1)}
        for role,g in gate_by_role.items():
            if g['side'] not in normals:
                return result('unknown','gate_orientation_not_supported')
            normal=rotate(normals[g['side']],-rotation)
            if abs(normal[1])>1e-8:
                return result('unknown','gate_not_aligned_with_row_axis')
            gx,gy=rotate((g['point'][0]-slot['x'],g['point'][1]-slot['y']),-rotation)
            local_gates[role]=(gx,gy,normal[0],g['width'])
        entry,exit_gate=local_gates['entry'],local_gates['exit']
        if entry[2]*exit_gate[2]>0:
            return result('unknown','opposite_gate_template_required')
        heading=0.0 if entry[2]>0 else math.pi
        rmin=minimum_radius(p)
        attempts=0
        modes=((alpha,1),(alpha+math.pi,-1))
        for (parking_heading,motion_sign),extra,final_distance in product(modes,p['radius_offsets'],p['final_straight_distances']):
            attempts+=1
            delta=(parking_heading-heading+math.pi)%(2*math.pi)-math.pi
            if abs(delta)<1e-8:
                continue
            goal=(-offset*math.cos(parking_heading),-offset*math.sin(parking_heading),parking_heading)
            curvature=math.copysign(1/(rmin+extra),delta*motion_sign)
            final_travel=motion_sign*final_distance
            ex=goal[0]-final_travel*math.cos(parking_heading)
            ey=goal[1]-final_travel*math.sin(parking_heading)
            sx=ex-(math.sin(parking_heading)-math.sin(heading))/curvature
            sy=ey-(math.cos(heading)-math.cos(parking_heading))/curvature
            if any(abs(sy-g[1])+p['width']/2+p['clearance']>g[3]/2 for g in (entry,exit_gate)):
                continue
            direction=entry[2]
            start_x=entry[0]+direction*(p['rear_overhang']+p['clearance']+0.01)
            exit_x=exit_gate[0]-direction*(p['length']-p['rear_overhang']+p['clearance']+0.01)
            approach=(sx-start_x)*direction
            departure=(exit_x-sx)*direction
            if min(approach,departure)<0:
                continue
            segments=[(approach,0.0),(delta/curvature,curvature),(final_travel,0.0)]
            local_path=[(start_x,sy,heading)]
            controls=[]
            for distance,k in segments:
                n=max(1,math.ceil(abs(distance)/p['sample_distance']))
                for _ in range(n):
                    ds=distance/n
                    local_path.append(advance(local_path[-1],ds,k))
                    controls.append((ds,k))
            if not self._safe(local_path,controls,slot,allowed,roads,slot):
                continue
            maneuver_count=sum(max(1,math.ceil(abs(d)/p['sample_distance'])) for d,k in segments[1:])
            exit_path=list(reversed(local_path[-maneuver_count-1:]))
            exit_controls=[(-ds,k) for ds,k in reversed(controls[-maneuver_count:])]
            n=max(1,math.ceil(departure/p['sample_distance']))
            for _ in range(n):
                ds=departure/n
                exit_path.append(advance(exit_path[-1],ds,0))
                exit_controls.append((ds,0))
            if not self._safe(exit_path,exit_controls,slot,allowed,roads,slot):
                continue
            return dict(status='passed',reason='entry_and_exit_path_witness_found',attempts=attempts,
                        parking_mode='forward_in' if motion_sign>0 else 'reverse_in',
                        turning_radius=rmin+extra,entry_path=self._serialize(local_path,controls,slot),
                        exit_path=self._serialize(exit_path,exit_controls,slot))
        return dict(**result('unknown','no_safe_path_in_bounded_template_search'),attempts=attempts)

    def _world(self,pose,slot):
        dx,dy=rotate(pose[:2],slot['rotation'])
        return slot['x']+dx,slot['y']+dy,pose[2]+math.radians(slot['rotation'])

    def _safe(self,path,controls,slot,allowed,roads=(),target=None):
        from shapely.geometry import Polygon
        from Arrange_tools.Policies.traffics import permits
        p=self.profile
        previous=Polygon(footprint(self._world(path[0],slot),p))
        if not allowed.covers(previous.buffer(p['clearance'])):
            return False
        for pose,(distance,k) in zip(path[1:],controls):
            world=self._world(pose,slot)
            if roads and not permits(world,distance,roads,target,p):
                return False
            body=Polygon(footprint(world,p))
            # An arc's corner trajectory may bulge outside endpoint convex hulls.
            # Bound that sagitta using the greatest possible corner/ICR radius.
            theta=abs(distance*k)
            padding=0 if not k else (1/abs(k)+p['length']+p['width'])*(1-math.cos(theta/2))
            swept=previous.union(body).convex_hull.buffer(p['clearance']+padding)
            if not allowed.covers(swept):
                return False
            previous=body
        return True

    def _serialize(self,path,controls,slot):
        result=[]
        for index,pose in enumerate(path):
            world=self._world(pose,slot)
            result.append(dict(x=world[0],y=world[1],heading=math.degrees(world[2]),
                               direction=1 if index==0 or controls[index-1][0]>=0 else -1,
                               travel_distance=0.0 if index==0 else controls[index-1][0],
                               curvature=0.0 if index==0 else controls[index-1][1],
                               footprint=footprint(world,self.profile)))
        return result
