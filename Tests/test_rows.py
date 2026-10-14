from copy import deepcopy
import math
import unittest
import test_tools


class RowTests(unittest.TestCase):
    setUp=test_tools.ToolsTests.setUp
    slot=test_tools.ToolsTests.slot
    def row(self,**kwargs):
        command=dict(type='place_row',template='perpendicular',x=8,y=14.75,row_length=15,rotation=0)
        command.update(kwargs)
        return command

    def test_row_is_one_action_and_preview_is_read_only(self):
        preview=self.c.propose(self.row())
        self.assertTrue(preview['accepted'],preview['reason'])
        self.assertEqual(len(preview['proposals']),6)
        self.assertEqual(len(self.c.history),1)
        event=self.c.apply(self.row())
        self.assertTrue(event['accepted'])
        self.assertEqual(len(self.c.history),2)
        self.assertEqual(sum(i['kind']=='slot' for i in self.c.items),6)
        self.assertEqual(event['proposals'],preview['proposals'])

    def test_row_collision_rolls_back_entire_action(self):
        self.c.apply(self.slot())
        before=deepcopy(self.c.items)
        event=self.c.apply(self.row())
        self.assertFalse(event['accepted'])
        self.assertEqual(self.c.items,before)
        self.assertEqual(event['before'],event['after'])

    def test_partial_row_outside_boundary_does_not_place_any_slot(self):
        event=self.c.apply(self.row(x=44))
        self.assertFalse(event['accepted'])
        self.assertEqual(len(self.c.items),1)

    def test_angled_rows_all_grids(self):
        from Arrange_tools.controller import Controller
        for resolution in (.1,.25,.5):
            c=Controller(self.layout,self.templates,self.validator,resolution)
            c.apply(self.layout['starter_actions'][0])
            y=math.ceil((12+4/math.sqrt(2))/resolution-1e-8)*resolution
            result=c.apply(self.row(template='angled',y=y))
            self.assertTrue(result['accepted'],result['reason'])
            self.assertEqual(len({i['id'] for i in c.items}),len(c.items))
            for item in result['proposals']:
                self.assertAlmostEqual(item['x']/resolution,round(item['x']/resolution))

    def test_row_invalid_template_or_length(self):
        for command in [self.row(template='parallel'),self.row(row_length=1),self.row(row_length=float('nan'))]:
            self.assertFalse(self.c.apply(command)['accepted'])

    def test_initial_state_does_not_reuse_ids_or_bypass_collisions(self):
        from Arrange_tools.controller import Controller
        c=Controller(self.layout,self.templates,self.validator)
        c.initialize(self.layout['starter_actions'])
        self.assertEqual(len(c.history),0)
        self.assertFalse(c.apply(self.layout['starter_actions'][0])['accepted'])
        self.assertTrue(c.apply(dict(type='place',kind='road',x=8,y=20,length=8,width=6))['accepted'])
        self.assertEqual(len({i['id'] for i in c.items}),len(c.items))
