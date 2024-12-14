import os
import yaml


def read_yaml(path) -> dict:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            yaml_content = os.path.expandvars(f.read())
            data = yaml.load(yaml_content, Loader=yaml.FullLoader)
    except Exception as e:
        raise Exception(f'Error reading file {path}: {e}')

    return data
