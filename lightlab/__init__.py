import logging
logger = logging.getLogger('lightlab')
visalogger = logging.getLogger('lightlab.visa')  # This is a child of logger.

# logging levels, increasing in order of severity.
NOTSET = logging.NOTSET
DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL

# inspired from pyvisa
def log_to_screen(level=DEBUG, logger=logger):
    logger.setLevel(level)

    stream_handlers = [handler for handler in logger.handlers if isinstance(handler, logging.StreamHandler)]

    if len(stream_handlers) <= 0:
        ch = logging.StreamHandler()
        logging.addHandler(ch)
    else:
        ch = stream_handlers[0]
    ch.setLevel(level)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s:\n\t%(message)s')
    ch.setFormatter(formatter)

log_to_screen(INFO, logger)
visalogger.setLevel(WARNING)
