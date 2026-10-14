from Arrange_tools.geometries import polygon, overlap


def check(item, others, layout):
    p = polygon(item)
    if any(x < -1e-8 or y < -1e-8 or x > layout['width']+1e-8 or y > layout['height']+1e-8 for x,y in p):
        return 'outside_boundary'
    for other in [*layout['obstacles'], *others]:
        if overlap(p, polygon(other)):
            return 'collision:' + other['id']
    for gate in layout['gates']:
        if item['kind'] == 'slot' and overlap(p, polygon(gate['reserve'])):
            return 'gate_clearance:' + gate['id']
    return None
