import logging


logging.basicConfig()
logging.captureWarnings(True)
openalert_logger = logging.getLogger('OpenAlert')


def configure_logging(args, conf):
    # configure logging from config file if provided
    if 'logging' in conf:
        # load new logging config
        logging.config.dictConfig(conf['logging'])
    if args.debug:
        openalert_logger.info("Note: In debug mode, alerts will be logged to console but NOT actually sent.")
