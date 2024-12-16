import os

from ultils import read_yaml
from jsonschema import validate


# Required global (config.yaml) configuration options
required_globals = frozenset(['opensearch_hosts', 'writeback_index', 'run_every', 'buffer_time'])


def load_config(config_file: str, schema_file: str) -> dict:
    if config_file:
        try:
            config = read_yaml(config_file)
        except Exception as e:
            raise Exception(f'Error reading config file: {e}')
    else:
        config = read_yaml(os.path.join(os.path.dirname(__file__), 'config.yaml'))

    schema = read_yaml(os.path.join(os.path.dirname(__file__), fr"schema/{schema_file}"))

    try:
        validate(config, schema)
    except Exception as e:
        raise Exception(f'Error validating config: {e}')

    return config


## conf = Config()
# print(conf.load_config("config.yaml", r"D:\DEV\Python\openalert\openalert\schema\config-schema.json"))