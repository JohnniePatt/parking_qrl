"""Road rotation is the travel direction: 0 east, 90 south, 180 west, 270 north."""
import math
from Arrange_tools.geometries import contains


def permits(pose, distance, roads, slot, profile):
    offset=profile['length']/2-profile['rear_overhang']
    centre=(pose[0]+offset*math.cos(pose[2]),pose[1]+offset*math.sin(pose[2]))
    lanes=[r for r in roads if contains(r,centre)]
    if not lanes or any(abs(r['width']-6)<1e-6 for r in lanes):
        return True
    for road in lanes:
        angle=math.radians(road['angle'])
        alignment=math.cos(pose[2]-angle)
        if alignment*(1 if distance>=0 else -1)>=-.05:
            return True
        # Reversing for parking is local and the car must face the traffic direction.
        if distance<0 and alignment>0 and math.hypot(centre[0]-slot['x'],centre[1]-slot['y'])<=6:
            return True
    return False
