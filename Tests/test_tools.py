"""Behaviour tests for geometric feasibility, atomic actions and reproducibility."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from Arrange_tools.controller import Controller
from Arrange_tools.grid import dimensions, occupied_cells
from Arrange_tools.geometries import polygon, overlap
from Arrange_tools.Policies.validator import Validator
from Layouts.generator import generate
from Layouts.repository import load
from Outputs.repository import Repository

ROOT = Path(__file__).resolve().parents[1]


class ToolsTests(unittest.TestCase):
    def setUp(self):
        self.templates=load(ROOT/'Arrange_tools/Slot_layouts/slots.json')['templates']
        self.validator=Validator(load(ROOT/'Arrange_tools/policies.json'),self.templates)
        self.layout=generate(42)
        self.road_y=self.layout['gates'][0]['point'][1]
        self.c=Controller(self.layout,self.templates,self.validator)
        self.assertTrue(self.c.apply(self.layout['starter_actions'][0])['accepted'])

    def slot(self, **overrides):
        return dict(type='place',kind='slot',template='perpendicular',x=8,y=self.road_y+5.75,**overrides)

    def test_overlap_rejection_is_atomic_and_logged(self):
        self.assertTrue(self.c.apply(self.slot())['accepted'])
        before=deepcopy(self.c.items)
        result=self.c.apply(self.slot())
        self.assertFalse(result['accepted'])
        self.assertEqual(before,self.c.items)
        self.assertEqual(result['before'],result['after'])
        self.assertEqual(len(self.c.history),3)

    def test_shared_edges_allowed(self):
        self.assertTrue(self.c.apply(self.slot())['accepted'])
        command=self.slot(); command['x']=10.5
        self.assertTrue(self.c.apply(command)['accepted'])

    def test_boundary_road_and_core_collisions(self):
        for x,y in [(-1,15),(8,self.road_y),(24,26.5),(12,4)]:
            command=self.slot(); command.update(x=x,y=y)
            self.assertFalse(self.c.apply(command)['accepted'])

    def test_road_removal_cannot_strand_slot(self):
        self.c.apply(self.slot())
        result=self.c.apply({'type':'remove','id':'object_1'})
        self.assertFalse(result['accepted'])
        self.assertEqual(len(self.c.items),2)

    def test_move_collision_and_valid_move(self):
        self.c.apply(self.slot())
        self.assertTrue(self.c.apply(dict(type='move',id='object_2',x=16,y=self.road_y+5.75))['accepted'])
        self.assertFalse(self.c.apply(dict(type='move',id='object_2',x=16,y=self.road_y))['accepted'])
        self.assertEqual(self.c.items[-1]['x'],16)

    def test_disconnected_aisle_rejected_for_slots(self):
        self.c.apply(dict(type='place',kind='road',x=9,y=19,length=12,width=6))
        result=self.c.apply(dict(type='place',kind='slot',template='parallel',x=9,y=23.25))
        self.assertFalse(result['accepted'])
        self.assertIn('entry_exit',result['reason'])

    def test_road_dimensions_and_nan(self):
        self.assertFalse(self.c.apply(dict(type='place',kind='road',x=20,y=20,length=10,width=4))['accepted'])
        self.assertFalse(self.c.apply(dict(type='place',kind='road',x=float('nan'),y=20,length=10,width=6))['accepted'])

    def test_all_slot_types_and_grid_resolutions(self):
        import math
        for resolution in (0.1,0.25,0.5):
            for template in self.templates:
                with self.subTest(resolution=resolution,template=template):
                    c=Controller(self.layout,self.templates,self.validator,resolution)
                    c.apply(self.layout['starter_actions'][0])
                    t=self.templates[template]
                    half_depth=(abs(math.sin(math.radians(t['angle'])))*5.5+abs(math.cos(math.radians(t['angle'])))*2.5)/2
                    # Round upward so a snapped slot does not intrude into the road.
                    y=math.ceil((self.road_y+3+half_depth)/resolution-1e-8)*resolution
                    result=c.apply(dict(type='place',kind='slot',template=template,x=8,y=y))
                    self.assertTrue(result['accepted'],result['reason'])
                    self.assertEqual(dimensions(self.layout,resolution)['columns'],round(48/resolution))

    def test_parallel_and_angled_default_grid(self):
        for template,y in [('parallel',self.road_y+4.25),('angled',self.road_y+6)]:
            c=Controller(self.layout,self.templates,self.validator)
            c.apply(self.layout['starter_actions'][0])
            self.assertTrue(c.apply(dict(type='place',kind='slot',template=template,x=8,y=y))['accepted'])

    def test_90_requires_six_metre_aisle(self):
        self.c.apply({'type':'reset'})
        self.c.apply(dict(type='place',kind='road',x=24,y=self.road_y,length=48,width=3.5))
        result=self.c.apply(dict(type='place',kind='slot',template='perpendicular',x=8,y=self.road_y+4.5))
        self.assertFalse(result['accepted'])

    def test_35_metre_road_accepts_experimental_angled_and_parallel(self):
        for template,y in [('parallel',self.road_y+3),('angled',self.road_y+4.75)]:
            c=Controller(self.layout,self.templates,self.validator)
            self.assertTrue(c.apply(dict(type='place',kind='road',x=24,y=self.road_y,length=48,width=3.5))['accepted'])
            result=c.apply(dict(type='place',kind='slot',template=template,x=8,y=y))
            self.assertTrue(result['accepted'],result['reason'])

    def test_quarter_turn_slot_next_to_connected_vertical_road(self):
        self.assertTrue(self.c.apply(dict(type='place',kind='road',x=18,y=21,length=18,width=6,rotation=90))['accepted'])
        result=self.c.apply(dict(type='place',kind='slot',template='perpendicular',x=12.25,y=18,rotation=90))
        self.assertTrue(result['accepted'],result['reason'])

    def test_slot_without_any_road_is_rejected(self):
        self.c.apply({'type':'reset'})
        result=self.c.apply(self.slot())
        self.assertFalse(result['accepted'])
        self.assertIn('adjacent_aisle',result['reason'])

    def test_preview_and_commit_snap_identically_without_preview_actions(self):
        for resolution in (0.1,0.25,0.5):
            c=Controller(self.layout,self.templates,self.validator,resolution)
            c.apply(self.layout['starter_actions'][0])
            command=dict(type='place',kind='road',x=8.137,y=19.137,length=8,width=3.5)
            before=deepcopy((c.items,c.history))
            preview=c.propose(command)
            self.assertTrue(preview['accepted'],preview['reason'])
            self.assertEqual((c.items,c.history),before)
            for axis in ('x','y'):
                value=preview['proposal'][axis]/resolution
                self.assertAlmostEqual(value,round(value))
            event=c.apply(command)
            self.assertTrue(event['accepted'])
            self.assertEqual(c.items[-1],preview['proposal'])

    def test_no_road_overlap_or_crossing_exception(self):
        for command in [self.layout['starter_actions'][0],
                        dict(type='place',kind='road',x=18,y=15,length=30,width=6,rotation=90)]:
            before=deepcopy(self.c.items)
            preview=self.c.propose(command)
            self.assertFalse(preview['accepted'])
            self.assertIn('collision',preview['reason'])
            self.assertFalse(self.c.apply(command)['accepted'])
            self.assertEqual(self.c.items,before)

    def test_move_preview_excludes_self_but_detects_other_objects(self):
        self.c.apply(self.slot())
        self.assertTrue(self.c.propose(dict(type='move',id='object_2',x=8.01,y=14.76))['accepted'])
        before=deepcopy((self.c.items,self.c.history))
        preview=self.c.propose(dict(type='move',id='object_2',x=24.01,y=26.49))
        self.assertFalse(preview['accepted'])
        self.assertIn('core_1',preview['reason'])
        self.assertEqual((self.c.items,self.c.history),before)

    def test_off_grid_object_cannot_bypass_validation(self):
        item=self.c._item(dict(type='place',kind='road',x=8,y=19,length=8,width=3.5),'test')
        item['x']+=0.01
        self.assertIn('snap_to_grid',self.validator.validate([item],self.layout))

    def test_preview_rechecks_current_state_at_commit(self):
        command=self.slot()
        self.assertTrue(self.c.propose(command)['accepted'])
        self.c.apply(command)
        self.assertFalse(self.c.apply(command)['accepted'])

    def test_budget_counts_rejections(self):
        self.c.max_actions=3
        self.c.apply(self.slot())
        self.c.apply(self.slot())
        with self.assertRaises(ValueError):
            self.c.apply({'type':'reset'})
        self.assertEqual(len(self.c.history),3)

    def test_seed_reproduces_case_and_varies_gates(self):
        self.assertEqual(generate(42),generate(42))
        signatures={tuple(g['point'][1] for g in generate(s)['gates']) for s in range(20)}
        self.assertGreater(len(signatures),1)

    def test_grid_conservatively_covers_rotated_footprint(self):
        item=dict(x=6,y=6,length=5.5,width=2.5,angle=45)
        for res in (0.1,0.25,0.5):
            cells=list(occupied_cells(item,self.layout,res))
            self.assertGreaterEqual(len(cells)*res*res,13.75)
        a=polygon(dict(x=1,y=1,length=2,width=2,angle=0))
        b=polygon(dict(x=3,y=1,length=2,width=2,angle=0))
        self.assertFalse(overlap(a,b))

    def test_json_roundtrip_keeps_every_replay_frame(self):
        self.c.apply(self.slot()); self.c.apply(self.slot())
        with tempfile.TemporaryDirectory() as folder:
            repo=Repository(folder)
            record=dict(schema_version=1,layout=self.layout,history=self.c.history,final_items=self.c.items)
            name=repo.save(record)
            restored=repo.load(name)
            self.assertEqual(record,restored)
            self.assertEqual(restored['history'][-1]['after'],restored['final_items'])
            with self.assertRaises(ValueError): repo.load('../main.py')

    def test_reset_and_invalid_identifier(self):
        self.assertFalse(self.c.apply(dict(type='remove',id='missing'))['accepted'])
        self.assertTrue(self.c.apply({'type':'reset'})['accepted'])
        self.assertEqual(self.c.items,[])


if __name__=='__main__':
    unittest.main()
