''' Functions for filesystem handling
'''
from pathlib import Path
from .paths import (projectDir,  # noqa
                    dataHome,  # noqa
                    monitorDir,  # noqa
                    lightlabDevelopmentDir)  # noqa

fileDir = dataHome  # Set this in your experiment


def _getFileDir(childFile=None):
    ''' This is only used within this package.
        The idea is to create a dynamic link to this changing attribute

        Args:
            childFile (str): Instead of the directory, will return
            the resolved path to this file within the directory
    '''
    if childFile is None:
        return Path(fileDir).resolve()
    else:
        return (Path(fileDir) / childFile).resolve()

from .saveload import (pprintFileDir,  # noqa
                       savePickle,  # noqa
                       loadPickle,  # noqa
                       loadPickleGzip,  # noqa
                       savePickleGzip,  # noqa
                       saveMat,  # noqa
                       loadMat,  # noqa
                       saveFigure)  # noqa
from .progress import printWait, printProgress, ProgressWriter  # noqa
from .errors import ChannelError, RangeError  # noqa
from .jsonpickleable import JSONpickleable  # noqa
