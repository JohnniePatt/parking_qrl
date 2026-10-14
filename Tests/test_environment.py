from copy import deepcopy
from pathlib import Path
import unittest
import numpy as np
from gymnasium.utils.env_checker import check_env
from Arrange_tools.Policies.validator import Validator
from Layouts.generator import generate
from Layouts.repository import load
from Models.environment import Environment

ROOT=Path(__file__).resolve().parents[1]


class EnvironmentTests(unittest.TestCase):
    def setUp(self):
        templates=load(ROOT/'Arrange_tools/Slot_layouts/slots.json')['templates']
        policies=load(ROOT/'Arrange_tools/policies.json')
        self.config=load(ROOT/'Models/config.json')
        self.e=Environment(generate(42),templates,Validator(policies,templates),self.config)

    def road_index(self):
        return next(i for i,a in enumerate(self.e.actions) if a.get('kind')=='road' and a.get('y')==9 and a.get('width')==6)

    def test_gymnasium_contract(self):
        check_env(self.e,skip_render_check=True)

    def test_no_remaining_placement_actions_ends_episode(self):
        from gymnasium import spaces
        self.e.actions=[self.e.actions[0],self.e.actions[self.road_index()]]
        self.e.action_space=spaces.Discrete(2)
        self.e.reset()
        _,_,terminated,truncated,info=self.e.step(1)
        self.assertTrue(terminated)
        self.assertFalse(truncated)
        self.assertTrue(info['episode_finished'])
        self.assertFalse(self.e.action_masks().any())
        self.assertEqual(info['actions'],1)

    def test_empty_reset_and_repeatability(self):
        obs,info=self.e.reset(seed=42)
        self.assertTrue(self.e.observation_space.contains(obs))
        self.assertEqual(len(self.e.controller.items),0)
        self.assertEqual(info['actions'],0)
        self.assertEqual(obs['grid'][1:3].sum(),0)
        self.e.step(self.road_index())
        again,_=self.e.reset(seed=42)
        np.testing.assert_array_equal(obs['grid'],again['grid'])

    def test_mask_preview_and_rewards(self):
        self.e.reset(seed=42)
        before=deepcopy(self.e.controller.history)
        mask=self.e.action_masks()
        self.assertEqual(before,self.e.controller.history)
        self.assertFalse(any(mask[i] for i,a in enumerate(self.e.actions) if a['type']=='place_row'))
        _,reward,_,_,_=self.e.step(self.road_index())
        self.assertEqual(reward,-.01)
        mask=self.e.action_masks()
        row=next(i for i,a in enumerate(self.e.actions) if mask[i] and a['type']=='place_row')
        _,reward,_,_,info=self.e.step(row)
        self.assertAlmostEqual(reward,info['total_slots']-.01)
        self.assertGreater(info['total_slots'],0)
        self.assertFalse(self.e.action_masks()[row])
        before=deepcopy(self.e.controller.items)
        _,reward,_,_,_=self.e.step(row)
        self.assertEqual(reward,-1.01)
        self.assertEqual(before,self.e.controller.items)

    def test_budget_is_truncation_and_finish_is_termination(self):
        self.e.config['max_actions']=1
        self.e.reset()
        _,_,terminated,truncated,_=self.e.step(self.road_index())
        self.assertFalse(terminated);self.assertTrue(truncated)
        self.assertFalse(self.e.action_masks().any())
        with self.assertRaises(RuntimeError): self.e.step(0)
        self.e.reset()
        _,_,terminated,truncated,_=self.e.step(0)
        self.assertTrue(terminated);self.assertFalse(truncated)

    def test_observation_and_masks_are_copies(self):
        self.e.reset()
        observation=self.e.observation();observation['grid'][:]=0
        self.assertGreater(self.e.observation()['grid'].sum(),0)
        mask=self.e.action_masks();mask[:]=False
        self.assertTrue(self.e.action_masks().any())

    def test_replay_snapshot_preserves_rows_rewards_and_initial_state(self):
        self.e.reset(options={'start_with_road':True})
        self.assertEqual(len(self.e.controller.history),0)
        self.assertEqual(len(self.e.initial_items),1)
        mask=self.e.action_masks()
        row=next(i for i,a in enumerate(self.e.actions) if mask[i] and a['type']=='place_row')
        self.e.step(row)
        record=self.e.snapshot()
        self.assertEqual(record['history'][-1]['after'],record['final_items'])
        self.assertIn('reward',record['history'][-1])
        self.assertEqual(record['source'],'environment_test')

    def test_action_indices_stay_fixed_across_gate_seeds(self):
        other=Environment(generate(10),self.e.templates,self.e.validator,self.config)
        self.assertEqual(other.actions,self.e.actions)

    def test_out_of_catalogue_action_does_not_change_state(self):
        self.e.reset()
        with self.assertRaises(ValueError):self.e.step(self.e.action_space.n)
        self.assertEqual(len(self.e.controller.history),0)
