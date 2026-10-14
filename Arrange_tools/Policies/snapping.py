"""Grid placement policy: snap the centre anchor, preserve real dimensions."""
from Arrange_tools.grid import RESOLUTIONS, snap


def prepare(item, resolution):
    if resolution not in RESOLUTIONS:
        raise ValueError('Unsupported grid resolution')
    return {**item, 'x': snap(item['x'], resolution), 'y': snap(item['y'], resolution)}


def check(item, resolution):
    if resolution not in RESOLUTIONS:
        return 'unsupported_grid_resolution'
    if any(abs(item[axis]-snap(item[axis],resolution)) > 1e-8 for axis in ('x','y')):
        return 'object_anchor_must_snap_to_grid:' + item['id']
    return None
