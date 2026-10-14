"""Prevent train/evaluation leakage when different seeds produce identical layouts."""
import json
from Layouts.generator import generate


def geometry_key(layout):
    return json.dumps({key:layout[key] for key in ('width','height','gates','obstacles')},sort_keys=True)


def validate_split(config):
    training={geometry_key(generate(seed)) for seed in config['training_seeds']}
    tests=[geometry_key(generate(seed)) for seed in config['test_seeds']]
    if training.intersection(tests):
        raise ValueError('Train/test seeds generate overlapping layout geometry')
    if len(tests)!=len(set(tests)):
        raise ValueError('Test seeds generate duplicate layouts')
