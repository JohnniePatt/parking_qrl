"""Composition root: connects UI, tools, policies, model scaffolds and storage."""
import argparse
from copy import deepcopy
from pathlib import Path
from Arrange_tools.controller import Controller
from Arrange_tools.Policies.validator import Validator
from Arrange_tools.grid import dimensions, occupied_cells
from Layouts.generator import generate
from Layouts.repository import load, save
from Outputs.repository import Repository
from UI.server import serve

ROOT = Path(__file__).resolve().parent


class Application:
    def __init__(self):
        self.policies = load(ROOT/'Arrange_tools/policies.json')
        self.templates = load(ROOT/'Arrange_tools/Slot_layouts/slots.json')['templates']
        self.validator = Validator(self.policies, self.templates)
        self.outputs = Repository(ROOT/'Outputs')
        self.controller = None
        self.new_session({'seed':42, 'resolution':0.25, 'max_actions':200})

    def new_session(self, data):
        seed = int(data.get('seed',42))
        resolution = float(data.get('resolution',0.25))
        limit = int(data.get('max_actions',200))
        if not 1 <= limit <= 10000:
            raise ValueError('Action limit must be 1–10000')
        layout = generate(seed)
        dimensions(layout,resolution)
        controller = Controller(layout,self.templates,self.validator,resolution,limit)
        for command in layout['starter_actions']:
            result = controller.apply(command)
            if not result['accepted']:
                raise ValueError('Starter layout is invalid: '+result['reason'])
        save(ROOT/'Layouts'/('rectangle_'+str(seed)+'.json'), layout)
        self.controller = controller
        return self.state()

    def state(self):
        c = self.controller
        slots = [i for i in c.items if i['kind']=='slot']
        return dict(layout=c.layout, items=c.items, history=c.history, templates=self.templates,
                    grid=dimensions(c.layout,c.resolution), max_actions=c.max_actions,
                    metrics=dict(total_slots=len(slots), roads=sum(i['kind']=='road' for i in c.items),
                                 slot_area=round(sum(i['length']*i['width'] for i in slots),2),
                                 utilization=round(100*sum(i['length']*i['width'] for i in slots)/(c.layout['width']*c.layout['height']),2),
                                 rejected=sum(not e['accepted'] for e in c.history), actions=len(c.history)),
                    models={'Model_RL':'not_implemented','Model_QRL':'not_implemented'},
                    limitations=['Experimental dimensions', 'Topological access only', 'Swept path not implemented'])

    def action(self,data):
        event = self.controller.apply(data)
        return {'event':event,'state':self.state()}

    def save_output(self):
        c = self.controller
        return {'name':self.outputs.save(dict(schema_version=1, source='manual_tools', model=None,
                    layout=deepcopy(c.layout), resolution=c.resolution,max_actions=c.max_actions,
                    policies=deepcopy(self.policies),templates=deepcopy(self.templates),
                    history=deepcopy(c.history), initial_items=[], final_items=deepcopy(c.items),
                    metrics=self.state()['metrics'], limitations=self.state()['limitations']))}

    def route(self, method, path, data):
        if method=='GET' and path=='/api/state':
            return self.state()
        if method=='GET' and path=='/api/outputs':
            return {'files':self.outputs.list()}
        if method=='GET' and path=='/api/layouts':
            return {'files':[p.name for p in sorted((ROOT/'Layouts').glob('*.json'))]}
        if method=='POST' and path=='/api/session':
            return self.new_session(data)
        if method=='POST' and path=='/api/action':
            return self.action(data)
        if method=='POST' and path=='/api/propose':
            return self.controller.propose(data)
        if method=='POST' and path=='/api/save':
            return self.save_output()
        if method=='POST' and path=='/api/preview':
            return self.outputs.load(data['name'])
        if method=='GET' and path=='/api/grid':
            c = self.controller
            # Sparse channels keep road/slot/obstacle information separate.
            return {kind:sorted({cell for item in items for cell in occupied_cells(item,c.layout,c.resolution)})
                    for kind,items in [('obstacles',c.layout['obstacles']),
                                       ('roads',[i for i in c.items if i['kind']=='road']),
                                       ('slots',[i for i in c.items if i['kind']=='slot'])]}
        if method=='POST' and path=='/api/run':
            raise ValueError('RL/QRL training is not implemented in phase 1')
        raise ValueError('Unknown API route')


if __name__=='__main__':
    parser = argparse.ArgumentParser(description='Parking layout research tools')
    parser.add_argument('--port',type=int,default=8000)
    args = parser.parse_args()
    serve(Application(),ROOT/'UI',args.port)
