import os
import yaml
import logging


logging.basicConfig()
logging.captureWarnings(True)
elastalert_logger = logging.getLogger('openalert')


def read_yaml(path):
    with open(path) as f:
        yamlContent = os.path.expandvars(f.read())
        return yaml.load(yamlContent, Loader=yaml.FullLoader)
