import math
import unittest
from Arrange_tools.Policies.traffics import permits
from Arrange_tools.Policies.accesses import reachable_roads,directed_connection


class TrafficTests(unittest.TestCase):
    def setUp(self):
        self.road=dict(id='r',kind='road',x=10,y=5,length=20,width=3.5,angle=0)
        self.slot=dict(x=15,y=8)
        self.profile=dict(length=4.5,rear_overhang=.9)

    def test_one_way_forbids_opposite_transit(self):
        self.assertTrue(permits((5,5,0),.25,[self.road],self.slot,self.profile))
        self.assertFalse(permits((5,5,math.pi),.25,[self.road],self.slot,self.profile))
        self.assertFalse(permits((5,5,0),-.25,[self.road],self.slot,self.profile))

    def test_reverse_parking_is_local_and_faces_traffic(self):
        self.assertTrue(permits((14,5,0),-.25,[self.road],self.slot,self.profile))
        self.assertFalse(permits((14,5,math.pi),.25,[self.road],self.slot,self.profile))

    def test_rotated_direction_and_two_way(self):
        road={**self.road,'angle':180}
        self.assertFalse(permits((5,5,0),.25,[road],self.slot,self.profile))
        self.assertTrue(permits((5,5,math.pi),.25,[road],self.slot,self.profile))
        self.assertTrue(permits((5,5,math.pi),.25,[{**self.road,'width':6}],self.slot,self.profile))

    def test_gate_and_network_direction(self):
        entry=dict(side='west',point=[0,5]);exit=dict(side='east',point=[20,5])
        self.assertEqual(reachable_roads([self.road],entry),{'r'})
        self.assertEqual(reachable_roads([self.road],exit,True),{'r'})
        reversed_road={**self.road,'angle':180}
        self.assertEqual(reachable_roads([reversed_road],entry),set())
        self.assertEqual(reachable_roads([reversed_road],exit,True),set())
        next_road={**self.road,'id':'b','x':30}
        self.assertTrue(directed_connection(self.road,next_road))
        self.assertFalse(directed_connection(next_road,self.road))
