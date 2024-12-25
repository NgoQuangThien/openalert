import argparse
import json
import os
import re

from opensearch_client import OpenSearchClient
from config import load_config


# Regex pattern
name_schema = r'^cmccs-([a-zA-Z0-9_.]+)-([a-zA-Z0-9_.]+)-([a-zA-Z0-9_.]+)$'


def create_template(client, index, template):
    match_name = re.match(name_schema, index)
    if match_name:
        template['template']['mappings']['properties']['datastream_type']['value'] = match_name.group(1)
        template['template']['mappings']['properties']['datastream_dataset']['value'] = match_name.group(2)
        template['template']['mappings']['properties']['datastream_namespace']['value'] = match_name.group(3)

    try:
        response = client.indices.put_index_template(name=index, body=template)
        print("Template created successfully:", response)
    except Exception as e:
        print(e)


def main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--config',
        action='store',
        dest='config',
        help='Global config file (default: config.yaml)')
    args = parser.parse_args(args)

    config = load_config(args.config, "config-schema.json")
    opensearch_client = OpenSearchClient(config)
    index = config['opensearch']['writeBack']
    template_path = os.path.join(os.path.dirname(__file__), 'opensearch_templates/datastream-template.json')
    with open(template_path, 'r') as file:
        template = json.load(file)

    create_template(opensearch_client, index, template)


if __name__ == '__main__':
    main()
