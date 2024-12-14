from ultils import read_yaml
from jsonschema import validate


# Required global (config.yaml) configuration options
required_globals = frozenset(['opensearch_hosts', 'writeback_index', 'run_every', 'buffer_time'])


def load_config(config_file: str, schema_file: str) -> dict:
    config = read_yaml(config_file)
    schema = read_yaml(schema_file)

    try:
        validate(config, schema)
    except Exception as e:
        raise Exception(f'Error validating config: {e}')

    return config


## conf = Config()
# print(conf.load_config("config.yaml", r"D:\DEV\Python\openalert\openalert\schema\config-schema.json"))