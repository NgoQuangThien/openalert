import os
import yaml


def read_yaml(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            yamlContent = os.path.expandvars(f.read())
            data = yaml.load(yamlContent, Loader=yaml.FullLoader)
    except FileNotFoundError:
        raise Exception(f'File {path} not found')
    except yaml.YAMLError:
        raise Exception(f"'{path}' is not valid YAML.")
    except Exception as e:
        raise Exception(f'Error reading file {path}: {e}')

    return data
