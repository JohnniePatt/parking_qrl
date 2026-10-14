"""Expand a row into real slot rectangles; no state mutation or policy bypass."""
import math
from Arrange_tools.geometries import rotate


def expand(command, templates, resolution, row_id, prepare):
    template_id = command.get('template', 'perpendicular')
    if template_id not in ('perpendicular', 'angled'):
        raise ValueError('Rows currently support 90 and 45 degree parking')
    t = templates[template_id]
    length = float(command.get('row_length', 15))
    rotation = float(command.get('rotation', 0))
    x, y = float(command['x']), float(command['y'])
    if rotation not in (0,90,180,270) or not all(math.isfinite(v) for v in (x,y,length)):
        raise ValueError('Invalid row coordinates or rotation')
    if not 2.5 <= length <= 48:
        raise ValueError('Row length must be 2.5-48 m')
    angle = math.radians(t['angle'])
    span = abs(math.cos(angle))*t['length'] + abs(math.sin(angle))*t['width']
    pitch = math.ceil((t['width']/math.sin(angle))/resolution-1e-9)*resolution
    count = math.floor((length-span+1e-8)/pitch)+1
    if count < 1:
        raise ValueError('Row length is too short for this template')
    first = prepare(dict(id=row_id+'_1',kind='slot',template=template_id,x=x,y=y,
                         length=t['length'],width=t['width'],angle=t['angle']+rotation,
                         rotation=rotation),resolution)
    items = []
    for index in range(count):
        dx,dy = rotate((index*pitch,0),rotation)
        item = prepare({**first,'id':row_id+'_'+str(index+1),
                        'x':first['x']+dx,'y':first['y']+dy},resolution)
        item.update(row_id=row_id,row_index=index,row_length=length,row_pitch=pitch)
        items.append(item)
    return items
