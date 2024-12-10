import argparse
import os
import signal
import sys
from logger import logger
from config import load_config



class OpenAlert(object):
    def parse_args(self, args):
        parser = argparse.ArgumentParser()
        
        parser.add_argument(
            '--config',
            action='store',
            dest='config',
            default="config.yaml",
            help='Global config file (default: config.yaml)')
        
        parser.add_argument('--debug', action='store_true', dest='debug', help='Suppresses alerts and prints information instead.')

        self.args = parser.parse_args(args)


    def __init__(self, args):
        self.parse_args(args)
        self.config = load_config(self.args)


    def start(self):
        logger.info('Starting OpenAlert...')
        logger.info('OpenAlert is running')
        while True:
            break


def handle_signal(signal, frame):
    logger.info('SIGINT received, stopping ElastAlert...')
    # use os._exit to exit immediately and avoid someone catching SystemExit
    os._exit(0)


def main(args=None):
    signal.signal(signal.SIGINT, handle_signal)
    if not args:
        args = sys.argv[1:]

    module = OpenAlert(args)
    module.start()


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))