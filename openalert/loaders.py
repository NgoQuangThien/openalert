import os
import yaml
import jsonschema


# load rules schema
def load_rule_schema():
    schema_path = os.path.join(os.path.dirname(__file__), 'rule-schema.json')
    with open(schema_path) as schema_file:
        schema_yml = yaml.load(schema_file, Loader=yaml.FullLoader)
    return jsonschema.Draft7Validator(schema_yml)


class RuleLoader:
    pass


class RuleFilesLoader(RuleLoader):
    def __init__(self, rule_files):
        pass