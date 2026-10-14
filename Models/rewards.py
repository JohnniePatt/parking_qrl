"""Experimental reward coefficients shared by future RL and QRL learners."""


def calculate(event, config):
    counts=event.get('vehicle_counts',{})
    before=counts.get('before_passed',0)
    after=counts.get('after_passed',0)
    terms=dict(valid_slots=(after-before)*config['per_valid_slot'],
               invalid_action=0.0 if event['accepted'] else config['invalid_action'],
               step_cost=config['step_cost'])
    return float(sum(terms.values())),terms
