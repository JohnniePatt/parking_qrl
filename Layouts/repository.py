import json
from pathlib import Path


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path, layout):
    Path(path).write_text(json.dumps(layout, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
