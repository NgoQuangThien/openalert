import argparse
import json
import os
import signal
import sys
import time

from config import load_config
from logger import openalert_logger, configure_logging
from loader import RulesLoader, ExceptionsLoader
from rule import RuleManager
from executor import Executor
from opensearch_client import OpenSearchClient


work_dir = os.path.dirname(__file__)


class OpenAlert(object):
    def __init__(self, config):
        self.running = False
        self.conf = config
        self.debug = config.get("debug")

        if self.debug:
            openalert_logger.info("In debug mode, alerts will be logged to console but NOT actually sent.")

        self.writeBackIndex = config['opensearch']['writeBack']
        self.client = OpenSearchClient(config)

        openalert_logger.info('Testing OpenSearch connection...')

        # if self.client.ping():
        #     openalert_logger.info('OpenSearch connection successful')
        # else:
        #     openalert_logger.error('OpenSearch connection failed')
        #     raise Exception('OpenSearch connection failed')

        self.rulesFolder = config['rule']['rulesFolder']
        self.exceptionsFolder = config['rule']['exceptionsFolder']
        self.maxSignals = config['rule']['maxSignals']
        self.interval = config['rule']['schedule']['interval']
        self.bufferTime = config['rule']['schedule']['bufferTime']

        openalert_logger.info('Begin loading rules and exceptions...')
        self.rules, self.disabled_rules = RulesLoader(self.rulesFolder,
                                                      os.path.join(work_dir,'schema/rule-schema.json')).load_all()
        self.exceptions = ExceptionsLoader(self.exceptionsFolder,
                                           os.path.join(work_dir, 'schema/exception-schema.json')).load_all()

        executor = Executor(self.rules, self.disabled_rules, self.exceptions)
        executor.start()

        self.running = True


    def start(self):
        openalert_logger.info('OpenAlert is running')
        while self.running:
            time.sleep(1)
            continue


    def stop(self):
        self.running = False
        openalert_logger.info('OpenAlert is shutting down')


def handle_signal(signal, frame):
    openalert_logger.info('SIGINT received, stopping OpenAlert...')
    # use os._exit to exit immediately and avoid someone catching SystemExit
    os._exit(0)


def main(args=None):
    signal.signal(signal.SIGINT, handle_signal)
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
    open_alert.start()


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
