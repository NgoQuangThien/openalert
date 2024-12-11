import logging
import logging.config
from ultils import read_yaml
from logger import openalert_logger, configure_logging


# Required global (config.yaml) configuration options
required_globals = frozenset(['opensearch_hosts', 'writeback_index', 'run_every', 'buffer_time'])

def load_config(args):
    config_file = args.config
    if config_file:
        config = read_yaml(config_file)
    else:
        config = read_yaml('config.yaml')

    # init logging from config and set log levels according to command line options
    configure_logging(args, config)
    
    # Make sure we have all required globals
    # print(frozenset(list(config.keys())))
    if required_globals - frozenset(list(config.keys())):
        raise Exception('%s must contain %s' % (config_file, ', '.join(required_globals - frozenset(list(config.keys())))))

    return config
