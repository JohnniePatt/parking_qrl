"""Immutable snapshots with embedded layout, policies and action history."""
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4


class Repository:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def save(self, record):
        prefix='environment_' if record.get('source')=='environment_test' else 'manual_'
        name = prefix + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '_' + uuid4().hex[:8]+'.json'
        path = self.root/name
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
        return name

    def list(self):
        return sorted([str(p.relative_to(self.root)) for p in self.root.rglob('*.json') if p.name not in ('manifest.json','metrics.json')], reverse=True)

    def load(self, name):
        if name not in self.list():
            raise ValueError('Unknown saved output')
        path = (self.root/name).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError('Invalid output path')
        record = json.loads(path.read_text(encoding='utf-8'))
        if record.get('schema_version') != 1 or not isinstance(record.get('history'),list):
            raise ValueError('Unsupported output schema')
        return record
