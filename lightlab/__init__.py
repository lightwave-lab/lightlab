import logging
logger = logging.getLogger('lightlab')


# inspired from pyvisa
def log_to_screen(level=logging.DEBUG):
    logger.setLevel(level)

    stream_handlers = [handler for handler in logger.handlers if isinstance(handler, logging.StreamHandler)]

    if len(stream_handlers) <= 0:
        ch = logging.StreamHandler()
    else:
        ch = stream_handlers[0]
    ch.setLevel(level)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    if len(stream_handlers) == 0:
        logger.addHandler(ch)


# logging levels, increasing in order of severity.
NOTSET = logging.NOTSET
DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL

log_to_screen(logging.INFO)
