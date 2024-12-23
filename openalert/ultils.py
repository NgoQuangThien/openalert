import os
import yaml
from datetime import datetime, timezone


def read_yaml(path) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        yaml_content = os.path.expandvars(f.read())
        return yaml.load(yaml_content, Loader=yaml.FullLoader)


def interval_to_seconds(interval: str) -> int:
    if interval.endswith('s'):
        return int(interval[:-1])
    elif interval.endswith('m'):
        return int(interval[:-1]) * 60
    elif interval.endswith('h'):
        return int(interval[:-1]) * 60 * 60
    else:
        return 0

def ts_now():
    now = datetime.now(timezone.utc)
    return now.isoformat()


def get_nested_value(data, field_path):
    parts = field_path.split('.')
    val = data
    for p in parts:
        if p in val:
            val = val[p]
        else:
            return None
    return val
