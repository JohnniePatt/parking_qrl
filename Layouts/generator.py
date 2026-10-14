"""Seeded rectangular research cases, with opposite-edge gates and a starter road."""
import random


def generate(seed=42):
    rng = random.Random(seed)
    y = rng.choice([9.0, 12.0, 15.0, 18.0, 21.0])
    reverse = rng.choice([False, True])
    gates = []
    for x, side in [(0,'west'), (48,'east')]:
        role = 'entry' if (x==0) != reverse else 'exit'
        gates.append(dict(id=role, role=role, side=side, point=[x,y], width=6,
                          reserve=dict(id=role+'_clearance', kind='reserve', x=1.5 if x==0 else 46.5,
                                       y=y, length=3, width=6, angle=0)))
    return dict(schema_version=1, id='rectangle_'+str(seed), seed=seed, units='metres',
                width=48, height=30, gates=gates,
                obstacles=[dict(id='core_1',kind='core',x=24,y=26.5,length=6,width=5,angle=0),
                           dict(id='column_1',kind='column',x=12,y=4,length=0.6,width=0.6,angle=0),
                           dict(id='column_2',kind='column',x=36,y=26,length=0.6,width=0.6,angle=0)],
                starter_actions=[dict(type='place',kind='road',x=24,y=y,length=48,width=6,rotation=0)])
