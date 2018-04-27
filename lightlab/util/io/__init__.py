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
        return fileDir
    else:
        return (fileDir / childFile).resolve()

from .saveload import (printAvailableFiles,  # noqa
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

