import os
import yaml


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
