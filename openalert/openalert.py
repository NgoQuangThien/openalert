import argparse
import json
import os
import signal
import sys
import time

from config import load_config
from logger import openalert_logger, configure_logging
from loader import RulesLoader, ExceptionsLoader
from executor import Executor


WORK_DIR = os.path.dirname(__file__)
RULES_SCHEMA_PATH = os.path.join(WORK_DIR, 'schema/rule-schema.json')
EXCEPTIONS_SCHEMA_PATH = os.path.join(WORK_DIR, 'schema/exception-schema.json')


class OpenAlert(object):
    def __init__(self, config):
        # Initializing attributes
        self.running = False
        self.debug = config.get("debug", False)

        if self.debug:
            openalert_logger.info("DEBUG mode: ON. Alerts will be logged to console but NOT actually sent.")

        # Preparing folders
        self.rules_folder = config['rule']['rulesFolder']
        self.exceptions_folder = config['rule']['exceptionsFolder']

        openalert_logger.info('Begin loading rules and exceptions...')

        # Load rules and exceptions
        self.rules, self.disabled_rules, self.exceptions = self._load_resources()

        # Executor setup
        self.executor = Executor(self.rules, self.disabled_rules, self.exceptions, config)


    def _load_resources(self):
        """Helper method to load rules and exceptions using respective loaders."""
        rules_loader = RulesLoader(self.rules_folder, RULES_SCHEMA_PATH)
        rules, disabled_rules = rules_loader.load_all()

        exceptions_loader = ExceptionsLoader(self.exceptions_folder, EXCEPTIONS_SCHEMA_PATH)
        exceptions = exceptions_loader.load_all()

        return rules, disabled_rules, exceptions


    def start(self):
        self.executor.start()
        self.running = True
        openalert_logger.info('OpenAlert is running')

        while self.running:
            time.sleep(1)
            continue


    def handle_signal(self, signal, frame):
        openalert_logger.info('SIGINT received, stopping OpenAlert...')
        self.stop()
        # use os._exit to exit immediately and avoid someone catching SystemExit
        os._exit(0)


    def stop(self):
        openalert_logger.info('OpenAlert is shutting down')
        self.executor.stop()
        self.running = False


def main(args=None):
    if not args:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--config',
        action='store',
        dest='config',
        help='Global config file (default: config.yaml)')
    parser.add_argument('--debug',
                        action='store_true',
                        dest='debug',
                        help='Suppresses alerts and prints information instead (default: False)')
    args = parser.parse_args(args)

    config = load_config(args.config, "config-schema.json")
    if args.debug:
        config["debug"] = True

    configure_logging(config)
    openalert_logger.info('Configuration successfully loaded')
    openalert_logger.info('Starting OpenAlert...')

    open_alert = OpenAlert(config)
    signal.signal(signal.SIGINT, open_alert.handle_signal)
    open_alert.start()


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
