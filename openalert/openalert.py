import argparse
import os
import signal
import sys

from config import load_config
from logger import openalert_logger, configure_logging


class OpenAlert(object):
    def __init__(self, config):
        self.conf = config
        self.debug = config.get("debug")


    def start(self):
        openalert_logger.info('OpenAlert is running')
        while True:
            break


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
    # open_alert.start()


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
