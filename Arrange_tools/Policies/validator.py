from Arrange_tools.Policies import collisions, dimensions, accesses, snapping
from Arrange_tools.geometries import polygon


class Validator:
    def __init__(self, policies, templates):
        self.policies, self.templates = policies, templates

    def prepare(self, item, resolution):
        item = snapping.prepare(item, resolution)
        item['polygon'] = polygon(item)
        return item

    def validate(self, items, layout, resolution=0.25):
        # Changed objects are appended by Controller; report the existing blocker first.
        for item in reversed(items):
            issue = snapping.check(item, resolution)
            if issue:
                return issue
            issue = dimensions.check(item, self.policies, self.templates)
            if issue:
                return issue
            issue = collisions.check(item, [i for i in items if i['id'] != item['id']], layout)
            if issue:
                return issue
        return accesses.check(items, layout, self.templates, resolution)
