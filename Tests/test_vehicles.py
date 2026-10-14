from copy import deepcopy
import math
from pathlib import Path
import unittest
from shapely.geometry import Polygon,box
from shapely.ops import unary_union
from Arrange_tools.vehicles import advance,footprint,minimum_radius,validate
from Arrange_tools.Policies.turnings import Auditor
from Arrange_tools.Policies.validator import Validator
from Arrange_tools.geometries import polygon
from Arrange_tools.controller import Controller
from Layouts.repository import load
from Layouts.generator import generate
from Models.rewards import calculate
from Models.environment import Environment

ROOT=Path(__file__).resolve().parents[1]


class VehicleTests(unittest.TestCase):
    def setUp(self):
        self.profile=load(ROOT/'Arrange_tools/vehicle.json')
        self.templates=load(ROOT/'Arrange_tools/Slot_layouts/slots.json')['templates']
        self.policies=load(ROOT/'Arrange_tools/policies.json')
        self.layout=generate(42)
        self.validator=Validator(self.policies,self.templates)
        self.c=Controller(self.layout,self.templates,self.validator)
        self.c.apply(self.layout['starter_actions'][0])
        self.c.apply(dict(type='place',kind='slot',template='perpendicular',x=20,y=14.75,rotation=0))

    def test_bicycle_motion_and_reversibility(self):
        r=minimum_radius(self.profile)
        end=advance((0,0,0),r*math.pi/2,1/r)
        self.assertAlmostEqual(end[0],r);self.assertAlmostEqual(end[1],r)
        back=advance(end,-r*math.pi/2,1/r)
        for value in back:self.assertAlmostEqual(value,0)

    def test_rear_axle_body_offset_and_invalid_profiles(self):
        body=Polygon(footprint((0,0,0),self.profile))
        self.assertAlmostEqual(body.bounds[0],-.9)
        self.assertAlmostEqual(body.bounds[2],3.6)
        for key,value in [('wheelbase',0),('max_steering_degrees',90),('sample_distance',0)]:
            profile={**self.profile,key:value}
            with self.assertRaises(ValueError):validate(profile)

    def test_passed_path_is_kinematic_and_stays_in_drivable_region(self):
        report=self.validator.audit(self.c.items,self.layout,.25)
        self.assertEqual(report['passed'],1)
        witness=report['slots'][0]
        self.assertEqual(witness['parking_mode'],'reverse_in')
        slot=self.c.items[-1]
        allowed=unary_union([Polygon(polygon(self.c.items[0])),Polygon(polygon(slot)).buffer(.26,join_style=2)])
        self.assertTrue(Polygon(polygon(slot)).covers(Polygon(witness['entry_path'][-1]['footprint'])))
        for path in (witness['entry_path'],witness['exit_path']):
            for previous,current in zip(path,path[1:]):
                start=(previous['x'],previous['y'],math.radians(previous['heading']))
                k,ds=current['curvature'],current['travel_distance']
                self.assertLessEqual(abs(k),1/minimum_radius(self.profile)+1e-9)
                endpoint=advance(start,ds,k)
                self.assertAlmostEqual(endpoint[0],current['x'])
                self.assertAlmostEqual(endpoint[1],current['y'])
                # Independent dense samples, including segment interiors.
                for fraction in (0,.2,.4,.6,.8,1):
                    car=Polygon(footprint(advance(start,ds*fraction,k),self.profile))
                    self.assertTrue(allowed.covers(car))
                    self.assertTrue(box(0,0,48,30).covers(car))

    def test_oversize_vehicle_is_failed_not_unknown(self):
        profile={**self.profile,'width':2.6}
        report=Auditor(profile,self.templates).audit(self.c.items,self.layout,.25)
        self.assertEqual(report['failed'],1)
        self.assertEqual(report['slots'][0]['reason'],'vehicle_does_not_fit_stall')

    def test_narrow_gate_is_failed(self):
        layout=deepcopy(self.layout);layout['gates'][0]['width']=1.5
        report=self.validator.audit(self.c.items,layout,.25)
        self.assertEqual(report['failed'],1)
        self.assertEqual(report['slots'][0]['reason'],'gate_too_narrow_for_vehicle')

    def test_blocked_aisle_never_reports_passed(self):
        layout=deepcopy(self.layout)
        layout['obstacles'].append(dict(id='barrier',kind='column',x=12,y=9,length=1,width=6,angle=0))
        report=self.validator.audit(self.c.items,layout,.25)
        self.assertEqual(report['passed'],0)
        self.assertEqual(report['unknown'],1)

    def test_parallel_runs_maneuver_search(self):
        self.c.apply({'type':'reset'})
        self.c.apply(self.layout['starter_actions'][0])
        self.c.apply(dict(type='place',kind='slot',template='parallel',x=20,y=13.25,rotation=0))
        report=self.validator.audit(self.c.items,self.layout,.25)
        self.assertEqual(report['slots'][0]['status'],'passed')
        self.assertNotEqual(report['slots'][0]['reason'],'parking_template_not_supported')
        self.assertGreater(report['slots'][0]['attempts'],2)

    def test_parallel_with_turn_to_south_exit(self):
        layout={**self.layout,'obstacles':[],'gates':[
            dict(role='entry',side='west',point=[0,9],width=6),
            dict(role='exit',side='south',point=[30,30],width=6)]}
        def item(id,kind,x,y,length,width,angle=0,template=None):
            return dict(id=id,kind=kind,x=x,y=y,length=length,width=width,
                        angle=angle,rotation=0,template=template)
        items=[item('a','road',16.5,9,33,6),item('b','road',30,21,18,6,90),
               item('s','slot',20,13.25,5.5,2.5,0,'parallel')]
        witness=self.validator.audit(items,layout,.25)['slots'][0]
        self.assertEqual(witness['status'],'passed')
        self.assertGreater(witness['exit_path'][-1]['y'],25)
        self.assertTrue(any(abs(p['curvature'])>0 for p in witness['exit_path']))
        for path in (witness['entry_path'],witness['exit_path']):
            for previous,current in zip(path,path[1:]):
                expected=advance((previous['x'],previous['y'],math.radians(previous['heading'])),
                                 current['travel_distance'],current['curvature'])
                self.assertAlmostEqual(expected[0],current['x'])
                self.assertAlmostEqual(expected[1],current['y'])

    def test_angled_approach_at_east_boundary_and_blocker(self):
        self.c.apply({'type':'reset'});self.c.apply(self.layout['starter_actions'][0])
        event=self.c.apply(dict(type='place',kind='slot',template='angled',x=44.75,y=15,rotation=0))
        self.assertTrue(event['accepted'])
        witness=self.validator.audit(self.c.items,self.layout,.25)['slots'][0]
        self.assertEqual(witness['status'],'passed')
        self.assertEqual(witness['parking_mode'],'forward_in')
        slot=self.c.items[-1]
        # The diagonal approach must not make obstacles in the apron traversable.
        blocked=deepcopy(self.layout)
        pose=next(p for p in witness['entry_path'] if p['y']>11 and p['y']<12)
        blocked['obstacles'].append(dict(id='apron_block',kind='column',x=pose['x'],y=pose['y'],length=4,width=4,angle=0))
        result=self.validator.audit(self.c.items,blocked,.25)
        self.assertEqual(result['passed'],0)
        for path in (witness['entry_path'],witness['exit_path']):
            for previous,current in zip(path,path[1:]):
                start=(previous['x'],previous['y'],math.radians(previous['heading']))
                endpoint=advance(start,current['travel_distance'],current['curvature'])
                self.assertAlmostEqual(endpoint[0],current['x'])
                self.assertAlmostEqual(endpoint[1],current['y'])
                for fraction in (0,.25,.5,.75,1):
                    body=Polygon(footprint(advance(start,current['travel_distance']*fraction,current['curvature']),self.profile))
                    self.assertTrue(box(0,0,48,30).covers(body))

    def test_cache_returns_copies_and_changes_with_geometry(self):
        before=deepcopy((self.c.items,self.c.history))
        report=self.validator.audit(self.c.items,self.layout,.25)
        report['slots'].clear()
        self.assertEqual(len(self.validator.audit(self.c.items,self.layout,.25)['slots']),1)
        self.assertEqual((self.c.items,self.c.history),before)
        self.c.apply({'type':'reset'})
        self.assertEqual(self.validator.audit(self.c.items,self.layout,.25)['passed'],0)

    def test_zero_reward_for_geometry_slots_without_vehicle_pass(self):
        event=dict(before=[],after=[{'kind':'slot'}],accepted=True,
                   vehicle_counts={'before_passed':0,'after_passed':0})
        reward,terms=calculate(event,{'per_valid_slot':1,'invalid_action':-1,'step_cost':-.01})
        self.assertEqual(reward,-.01);self.assertEqual(terms['valid_slots'],0)

    def test_reward_penalizes_loss_of_previously_verified_access(self):
        event=dict(before=[],after=[],accepted=True,vehicle_counts={'before_passed':3,'after_passed':1})
        reward,_=calculate(event,{'per_valid_slot':1,'invalid_action':-1,'step_cost':-.01})
        self.assertEqual(reward,-2.01)

    def test_environment_does_not_reward_oversize_car(self):
        config=load(ROOT/'Models/config.json')
        v=Validator(self.policies,self.templates,{**self.profile,'width':2.6})
        env=Environment(self.layout,self.templates,v,config)
        env.reset(options={'start_with_road':True})
        mask=env.action_masks()
        index=next(i for i,a in enumerate(env.actions) if a['type']=='place_row' and mask[i])
        _,reward,_,_,info=env.step(index)
        self.assertGreater(info['total_slots'],0)
        self.assertEqual(info['vehicle_passed'],0)
        self.assertGreater(info['vehicle_failed'],0)
        self.assertEqual(reward,-.01)

    def test_45_degree_checks_are_repeatable(self):
        self.c.apply({'type':'reset'});self.c.apply(self.layout['starter_actions'][0])
        self.c.apply(dict(type='place',kind='slot',template='angled',x=20,y=15,rotation=0))
        first=self.validator.audit(self.c.items,self.layout,.25)
        second=Auditor(self.profile,self.templates).audit(self.c.items,self.layout,.25)
        self.assertEqual(first,second)
        self.assertEqual(first['passed'],1)
