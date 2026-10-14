"""The only mutation boundary for placement. Validation is injected by main.py."""
from copy import deepcopy
from datetime import datetime, timezone
import math
from time import perf_counter


class Controller:
    def __init__(self, layout, templates, validator, resolution=0.25, max_actions=200):
        self.layout = deepcopy(layout)
        self.templates, self.validator = templates, validator
        self.resolution, self.max_actions = resolution, max_actions
        self.items, self.history = [], []
        self.started = perf_counter()

    def _item(self, command, object_id):
        kind = command.get('kind', 'slot')
        rotation = float(command.get('rotation', 0))
        if rotation not in (0,90,180,270):
            raise ValueError('Rotation must be 0, 90, 180 or 270')
        if kind == 'slot':
            template_id = command.get('template', 'perpendicular')
            if template_id not in self.templates:
                raise ValueError('Unknown slot template')
            t = self.templates[template_id]
            length, width, angle = t['length'], t['width'], t['angle']+rotation
        elif kind == 'road':
            template_id = None
            length, width, angle = float(command.get('length', 12)), float(command.get('width', 6)), rotation
        else:
            raise ValueError('Unknown object kind')
        x, y = float(command['x']), float(command['y'])
        if not all(math.isfinite(v) for v in (x,y,length,width,angle)):
            raise ValueError('Coordinates and dimensions must be finite')
        item = dict(id=object_id, kind=kind, template=template_id, x=x,
                    y=y, length=length, width=width, angle=angle, rotation=rotation)
        return self.validator.prepare(item, self.resolution)

    def _propose(self, command):
        candidate = deepcopy(self.items)
        reason = None
        try:
            action = command.get('type')
            if action == 'place':
                candidate.append(self._item(command, 'object_' + str(len(self.history)+1)))
            elif action in ('move','remove'):
                target = next((i for i in candidate if i['id']==command.get('id')), None)
                if target is None:
                    raise ValueError('Object not found')
                candidate.remove(target)
                if action == 'move':
                    candidate.append(self._item({**target, **command, 'rotation': command.get('rotation',target['rotation'])}, target['id']))
            elif action == 'reset':
                candidate = []
            else:
                raise ValueError('Unknown action')
            reason = self.validator.validate(candidate, self.layout, self.resolution)
        except (ValueError, TypeError, KeyError) as exc:
            reason = str(exc)
        return candidate, reason

    def propose(self, command):
        """Read-only drag preview through the exact same preparation and policies."""
        candidate, reason = self._propose(command)
        if len(self.history) >= self.max_actions:
            reason = 'Action limit reached; save or start a new session'
        proposal = self._placement(candidate, command)
        return dict(accepted=reason is None, reason=reason, proposal=proposal)

    def _placement(self, candidate, command):
        if command.get('type') not in ('place','move'):
            return None
        object_id = command.get('id') if command['type']=='move' else 'object_'+str(len(self.history)+1)
        return next((i for i in candidate if i['id']==object_id),None)

    def apply(self, command):
        if len(self.history) >= self.max_actions:
            raise ValueError('Action limit reached; save or start a new session')
        before = deepcopy(self.items)
        candidate, reason = self._propose(command)
        if not reason:
            self.items = candidate
        event = dict(step=len(self.history)+1, timestamp=datetime.now(timezone.utc).isoformat(),
                     elapsed_seconds=round(perf_counter()-self.started,6), command=deepcopy(command),
                     accepted=reason is None, reason=reason, proposal=deepcopy(self._placement(candidate,command)),
                     before=before, after=deepcopy(self.items))
        self.history.append(event)
        return event
