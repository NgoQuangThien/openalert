import os
import yaml


def read_yaml(path) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        yaml_content = os.path.expandvars(f.read())
        return yaml.load(yaml_content, Loader=yaml.FullLoader)

