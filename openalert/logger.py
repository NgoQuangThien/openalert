import logging
import os
import sys


logging.basicConfig()
logging.captureWarnings(True)
openalert_logger = logging.getLogger('OpenAlert')
openalert_logger.setLevel(logging.DEBUG)
openalert_logger.propagate = False


def configure_logging(conf):
    log_folder = os.path.join(os.path.dirname(__file__), 'log')
    if not os.path.exists(log_folder):
        os.makedirs(log_folder)

    # configure logging from config file if provided
    console_format ='%(asctime)s [%(levelname)+8s] %(message)s'
    file_format = '%(asctime)s [%(levelname)s] %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logging.Formatter(console_format, datefmt=date_format))

    file_handler = logging.FileHandler(fr"{log_folder}/openalert.log", mode="a", encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(file_format, datefmt=date_format))

    if 'logging' in conf:
        if conf['logging']['handlers']['console']['stream'] == 'stdout':
            console_handler.stream = sys.stdout
        elif conf['logging']['handlers']['console']['stream'] == 'stderr':
            console_handler.stream = sys.stderr
        console_handler.setLevel(conf['logging']['handlers']['console']['level'])

        if 'path' in conf['logging']['handlers']['file']:
            file_handler = logging.FileHandler(conf['logging']['handlers']['file']['path'], mode="a", encoding="utf-8")
        file_handler.setLevel(conf['logging']['handlers']['file']['level'])
        file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s %(message)s',
                                                        datefmt=date_format))
        # Need code to process keepFiles in config


    openalert_logger.addHandler(console_handler)
    openalert_logger.addHandler(file_handler)
