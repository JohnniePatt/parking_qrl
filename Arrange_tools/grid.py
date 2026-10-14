"""Grid anchors and conservative occupancy; dimensions stay in exact metres."""
import math
from Arrange_tools.geometries import bounds, polygon, overlap

RESOLUTIONS = (0.1, 0.25, 0.5)


def snap(value, resolution):
    return round(math.floor(float(value)/resolution + 0.5)*resolution, 6)


def dimensions(layout, resolution):
    if resolution not in RESOLUTIONS:
        raise ValueError('Grid must be 0.1, 0.25 or 0.5 m')
    return {'columns': math.ceil(layout['width']/resolution),
            'rows': math.ceil(layout['height']/resolution), 'resolution': resolution}


def occupied_cells(item, layout, resolution):
    """Any cell with positive intersection is occupied, including angled edges."""
    size = dimensions(layout, resolution)
    x0,y0,x1,y1 = bounds(item)
    for row in range(max(0, math.floor(y0/resolution)), min(size['rows'], math.ceil(y1/resolution))):
        for col in range(max(0, math.floor(x0/resolution)), min(size['columns'], math.ceil(x1/resolution))):
            x,y = col*resolution, row*resolution
            cell = [[x,y],[x+resolution,y],[x+resolution,y+resolution],[x,y+resolution]]
            if overlap(polygon(item), cell):
                yield col, row
