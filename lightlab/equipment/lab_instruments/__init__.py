from lightlab import logger, DEBUG

debug_mode = logger

def debug(*args):
    '''Debug printing. If debugOn is true, it will print a bunch of useful stuff
    '''
    if logger.level == DEBUG:
        logger.debug(args)


debugWait = debug

from .configure import *
from .visa_connection import *
from .visa_drivers import *
