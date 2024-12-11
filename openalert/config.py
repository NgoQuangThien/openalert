import logging
import logging.config
from ultils import read_yaml
from logger import configure_logging
import loaders


# Required global (config.yaml) configuration options
required_globals = frozenset(['opensearch_hosts', 'writeback_index', 'run_every', 'buffer_time'])

# Used to map the names of rule loaders to their classes
loader_mapping = {
    'file': loaders.RuleFilesLoader,
}

def load_config(args):
    config_file = args.config
    if config_file:
        config = read_yaml(config_file)
    else:
        config = read_yaml('config.yaml')

    # init logging from config and set log levels according to command line options
    configure_logging(args, config)
    
    # Make sure we have all required globals
    if required_globals - frozenset(list(config.keys())):
        raise Exception('%s must contain %s' % (config_file, ', '.join(required_globals - frozenset(list(config.keys())))))

    config.setdefault('max_query_size', 10000)
    config.setdefault('disable_rules_on_error', True)
    config.setdefault('rules_loader', 'file')

    # Initialise the rule loader and load each rule configuration
    rules_loader_class = loader_mapping.get(config['rules_loader'])
    rules_loader = rules_loader_class(config)
    print(rules_loader)

    # Make sure we have all the required globals for the loader
    # Make sure we have all required globals
    if rules_loader.required_globals - frozenset(list(config.keys())):
        raise Exception('%s must contain %s' % (config_file, ', '.join(rules_loader.required_globals - frozenset(list(config.keys())))))

    return config
