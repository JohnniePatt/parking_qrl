"""Topological connectivity and projected frontage, not vehicle swept paths."""
from Arrange_tools.geometries import polygon, connected, contains, rotate
import math


def directed_connection(a,b):
    if not connected(a,b):return False
    delta=(b['x']-a['x'],b['y']-a['y'])
    for road in (a,b):
        if abs(road['width']-3.5)<1e-6:
            theta=math.radians(road['angle'])
            if delta[0]*math.cos(theta)+delta[1]*math.sin(theta)<-1e-8:return False
    return True


def reachable_roads(roads, gate, reverse=False):
    normals={'west':(1,0),'east':(-1,0),'north':(0,1),'south':(0,-1)}
    normal=normals[gate['side']]
    def gate_ok(r):
        if abs(r['width']-3.5)>1e-6:return True
        theta=math.radians(r['angle'])
        return (normal[0]*math.cos(theta)+normal[1]*math.sin(theta))*(-1 if reverse else 1)>0.5
    seen = {r['id'] for r in roads if contains(r, gate['point']) and gate_ok(r)}
    while True:
        more = {r['id'] for r in roads if any(
            directed_connection(r,q) if reverse else directed_connection(q,r)
            for q in roads if q['id'] in seen)}
        if more <= seen:return seen
        seen |= more


def frontage_roads(slot, roads, minimum_width, tolerance=0.26):
    # In the row frame, the aisle is below the lowest edge of the slot envelope.
    # Quarter turns choose which side of the slot faces the aisle.
    rotation = slot.get('rotation', 0)
    local = [rotate((x-slot['x'], y-slot['y']), -rotation) for x,y in polygon(slot)]
    xmin, xmax = min(x for x,y in local), max(x for x,y in local)
    ymin = min(y for x,y in local)
    probes = []
    for fraction in (0.02, 0.25, 0.5, 0.75, 0.98):
        dx,dy = rotate((xmin+(xmax-xmin)*fraction, ymin-tolerance), rotation)
        probes.append((slot['x']+dx, slot['y']+dy))
    return {r['id'] for r in roads if r['width'] >= minimum_width
            and r['angle'] % 180 == rotation % 180
            and all(contains(r,p) for p in probes)}


def check(items, layout, templates, resolution=0.25):
    roads = [i for i in items if i['kind'] == 'road']
    entry = reachable_roads(roads, next(g for g in layout['gates'] if g['role']=='entry'))
    exit_ids = reachable_roads(roads, next(g for g in layout['gates'] if g['role']=='exit'),reverse=True)
    for slot in (i for i in items if i['kind']=='slot'):
        front = frontage_roads(slot, roads, templates[slot['template']]['minimum_aisle_width'],resolution+0.01)
        if not front:
            return 'slot_requires_adjacent_aisle:' + slot['id']
        if not (front & entry & exit_ids):
            return 'slot_requires_entry_exit_connection:' + slot['id']
    return None
