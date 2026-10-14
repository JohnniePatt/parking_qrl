"""Low-speed bicycle geometry, with the pose origin at the rear axle."""
import math
from Arrange_tools.geometries import polygon


def validate(profile):
    required=('length','width','wheelbase','rear_overhang','max_steering_degrees','clearance','sample_distance')
    if any(not math.isfinite(profile[k]) for k in required):
        raise ValueError('Vehicle parameters must be finite')
    if min(profile['length'],profile['width'],profile['wheelbase'],profile['sample_distance'])<=0:
        raise ValueError('Vehicle dimensions and sampling distance must be positive')
    if profile['rear_overhang']<0 or profile['length']<=profile['rear_overhang']+profile['wheelbase']:
        raise ValueError('Vehicle overhang/wheelbase is inconsistent with length')
    if not 0<profile['max_steering_degrees']<80 or profile['clearance']<0:
        raise ValueError('Invalid steering limit or clearance')
    if not profile['radius_offsets'] or any(not math.isfinite(v) or v<0 for v in profile['radius_offsets']):
        raise ValueError('Invalid radius search offsets')
    if not profile['final_straight_distances'] or any(not math.isfinite(v) or v<0 for v in profile['final_straight_distances']):
        raise ValueError('Invalid straight-distance candidates')


def minimum_radius(profile):
    return profile['wheelbase']/math.tan(math.radians(profile['max_steering_degrees']))


def advance(pose,distance,curvature):
    x,y,theta=pose
    if abs(curvature)<1e-12:
        return x+distance*math.cos(theta),y+distance*math.sin(theta),theta
    end=theta+distance*curvature
    return x+(math.sin(end)-math.sin(theta))/curvature,y+(math.cos(theta)-math.cos(end))/curvature,end


def footprint(pose,profile):
    x,y,theta=pose
    offset=profile['length']/2-profile['rear_overhang']
    return polygon(dict(x=x+offset*math.cos(theta),y=y+offset*math.sin(theta),
                        length=profile['length'],width=profile['width'],angle=math.degrees(theta)))
