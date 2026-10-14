from copy import deepcopy
import unittest
from main import Application


class ResumeTests(unittest.TestCase):
    def record(self,app):
        c=app.controller
        return dict(schema_version=1,source='manual_tools',layout=deepcopy(c.layout),
                    resolution=c.resolution,max_actions=c.max_actions,
                    history=deepcopy(c.history),final_items=deepcopy(c.items))

    def test_resume_preserves_existing_work_and_accepts_next_row(self):
        original=Application()
        record=self.record(original)
        target=Application()
        state=target.restore_session(record)
        self.assertEqual(state['items'],original.state()['items'])
        self.assertEqual(state['history'],original.state()['history'])
        event=target.action(dict(type='place_row',template='perpendicular',row_length=15,x=8,y=14.75,rotation=0))['event']
        self.assertTrue(event['accepted'],event['reason'])
        self.assertEqual(event['step'],2)

    def test_invalid_resume_leaves_current_session_untouched(self):
        app=Application()
        before=deepcopy(app.state())
        record=self.record(app)
        record['final_items'].append(deepcopy(record['final_items'][0]))
        with self.assertRaises(ValueError):app.restore_session(record)
        self.assertEqual(app.state(),before)

    def test_legacy_one_way_migration_preserves_invalid_direction_for_editing(self):
        app=Application()
        app.action(dict(type='place',kind='slot',template='parallel',x=20,y=13.25,rotation=0))
        record=self.record(app)
        road,slot=record['final_items']
        road.update(width=3.5,angle=180,rotation=180)
        slot['y']=12
        from Arrange_tools.geometries import polygon
        for item in (road,slot):item['polygon']=polygon(item)
        record['history'][-1]['after']=deepcopy(record['final_items'])
        record['policies']={'version':3}
        restored=Application()
        state=restored.restore_session(record)
        self.assertIsNotNone(state['migration_notice'])
        self.assertEqual(state['items'],record['final_items'])
        record['policies']['version']=4
        with self.assertRaises(ValueError):Application().restore_session(record)

    def test_runtime_advertises_row_and_environment_support(self):
        state=Application().state()
        self.assertIn('place_row',state['capabilities'])
        self.assertIn('environment',state['capabilities'])
