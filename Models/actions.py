"""Finite candidate catalogue; indices stay fixed across reset seeds."""
from copy import deepcopy
from Arrange_tools.grid import snap


def catalogue(layout, config):
    stride=float(config['candidate_stride_metres'])
    if stride<=0:
        raise ValueError('Candidate stride must be positive')
    res=config['resolution']
    xs=[snap(stride/2+i*stride,res) for i in range(int(layout['width']/stride))]
    ys=[snap(stride/2+i*stride,res) for i in range(int(layout['height']/stride))]
    actions=[dict(type='finish')]
    for y in [3,6,9,12,15,18,21,24,27]:
        for width in (3.5,6.0):
            actions.append(dict(type='place',kind='road',x=layout['width']/2,y=y,
                                length=layout['width'],width=width,rotation=0))
    for x in xs:
        for y in ys:
            for template in config['row_types']:
                for length in config['row_lengths']:
                    for rotation in (0,90,180,270):
                        actions.append(dict(type='place_row',template=template,x=x,y=y,
                                            row_length=length,rotation=rotation))
    return actions


def decode(actions, index):
    return deepcopy(actions[index])
