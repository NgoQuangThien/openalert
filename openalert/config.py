import logging
import logging.config
from ultils import read_yaml
from logger import logger


# Required global (config.yaml) configuration options
required_globals = frozenset(['run_every', 'opensearch_hosts', 'writeback_index', 'buffer_time'])

def load_config(args, defaults=None, overrides=None):
    config_file = args.config
    if config_file:
        config = read_yaml(config_file)
    else:
        try:
            config = read_yaml('config.yaml')
        except FileNotFoundError:
            raise Exception('No --config or config.yaml found')
    
    # init logging from config and set log levels according to command line options
    configure_logging(args, config)
    
    for key, value in (iter(defaults.items()) if defaults is not None else []):
        if key not in config:
            config[key] = value

    for key, value in (iter(overrides.items()) if overrides is not None else []):
        config[key] = value
    
    # Make sure we have all required globals
    print(frozenset(list(config.keys())))
    if required_globals - frozenset(list(config.keys())):
        raise Exception('%s must contain %s' % (config_file, ', '.join(required_globals - frozenset(list(config.keys())))))

    
    return config


def configure_logging(args, conf):
    # configure logging from config file if provided
    if 'logging' in conf:
        # load new logging config
        logging.config.dictConfig(conf['logging'])

    if args.debug:
        logger.info(
            """Note: In debug mode, alerts will be logged to console but NOT actually sent.
            To send them but remain verbose, use --verbose instead."""
        )
    