"""Continuous metre geometry. Edge contact is allowed; positive overlap is not."""
import math

EPS = 1e-8


def rotate(point, angle):
    x, y = point
    a = math.radians(angle)
    return (x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a))


def polygon(item):
    corners = [(-item['length']/2, -item['width']/2),
               (item['length']/2, -item['width']/2),
               (item['length']/2, item['width']/2),
               (-item['length']/2, item['width']/2)]
    return [[item['x'] + p[0], item['y'] + p[1]]
            for p in (rotate(c, item.get('angle', 0)) for c in corners)]


def overlap(a, b):
    """Separating axis test for convex polygons, with strict interior overlap."""
    for poly in (a, b):
        for i, p in enumerate(poly):
            q = poly[(i + 1) % len(poly)]
            axis = (-(q[1] - p[1]), q[0] - p[0])
            pa = [x*axis[0] + y*axis[1] for x, y in a]
            pb = [x*axis[0] + y*axis[1] for x, y in b]
            if min(max(pa), max(pb)) - max(min(pa), min(pb)) <= EPS:
                return False
    return True


def contains(item, point):
    x, y = rotate((point[0]-item['x'], point[1]-item['y']), -item.get('angle', 0))
    return abs(x) <= item['length']/2 + EPS and abs(y) <= item['width']/2 + EPS


def bounds(item):
    p = polygon(item)
    return min(x for x,y in p), min(y for x,y in p), max(x for x,y in p), max(y for x,y in p)


def connected(a, b):
    """Axis-aligned roads must overlap or share a positive-width edge."""
    ax, ay, bx, by = bounds(a)
    cx, cy, dx, dy = bounds(b)
    ox, oy = min(bx, dx)-max(ax, cx), min(by, dy)-max(ay, cy)
    return (ox > EPS and oy >= -EPS) or (oy > EPS and ox >= -EPS)
