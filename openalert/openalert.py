import argparse
import os
import signal
import sys
from config import load_config
from logger import openalert_logger


class OpenAlert(object):
    def parse_args(self, args):
        parser = argparse.ArgumentParser()
        
        parser.add_argument(
            '--config',
            action='store',
            dest='config',
            help='Global config file (default: config.yaml)')
        
        parser.add_argument('--debug', action='store_true', dest='debug', help='Suppresses alerts and prints information instead.')

        self.args = parser.parse_args(args)


    def __init__(self, args):
        self.parse_args(args)
        # print(self.args)
        self.config = load_config(self.args)


    def start(self):
        openalert_logger.info('Starting OpenAlert...')
        openalert_logger.info('OpenAlert is running')
        while True:
            break


def handle_signal(signal, frame):
    openalert_logger.info('SIGINT received, stopping ElastAlert...')
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