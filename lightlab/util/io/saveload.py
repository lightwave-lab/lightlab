import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import scipy.io as sio
import pickle
import gzip
import numpy as np

from . import _getFileDir
from lightlab import logger


# File functions. You must set the fileDir first
def _makeFileExist(filename):
    ''' If the file doesn't exist, touch it

        Returns:
            (Path): the fully resolved path to file
    '''
    rp = _getFileDir(filename)
    os.makedirs(_getFileDir(), mode=0o775, exist_ok=True)
    rp.touch()
    logger.debug("Saving to file: {}".format(rp))
    return rp


def printAvailableFiles():
    maxStrLen = 0
    for child in _getFileDir().iterdir():
        maxStrLen = max(maxStrLen, len(child.name))
    for child in _getFileDir().iterdir():
        if child.name in ['.', '..', '.DS_Store']:
            continue
        elif child.is_file():
            print(child.name)
        elif child.is_dir():
            print(child.name.ljust(maxStrLen+2, '.'), '(directory)')


def savePickle(filename, dataTuple):
    ''' Uses pickle

        Todo: timestamping would be cool
    '''
    rp = _makeFileExist(filename)
    with rp.open('wb') as fx:
        pickle.dump(dataTuple, fx)


def loadPickle(filename):
    ''' Uses pickle '''
    rp = _getFileDir(filename)
    with rp.open('rb') as fx:
        return pickle.load(fx)


def _gzfilename(filename):
    ''' ensures filename ends with .gz '''
    fname = str(filename)
    if fname.endswith('.gz'):
        return fname
    else:
        return f"{fname}.gz"


def loadPickleGzip(filename):
    ''' Uses pickle and then gzips the file'''
    p = fileDir / _gzfilename(filename)
    rp = p.resolve()
    with gzip.open(rp, 'rb') as fx:
        return pickle.load(fx)


def savePickleGzip(filename, dataTuple):
    ''' Uses pickle

        Todo: timestamping would be cool
    '''
    rp = _makeFileExist(_gzfilename(filename))
    with gzip.open(rp, 'wb') as fx:
        pickle.dump(dataTuple, fx)


def saveMat(filename, dataDict):
    ''' dataDict has keys as names you would like to appear in matlab, values are matrices '''
    if filename[-4:] != '.mat':
        filename += '.mat'
    rp = _makeFileExist(filename)
    sio.savemat(str(rp), dataDict)


def loadMat(filename):
    ''' returns a dictionary of data. This should perfectly invert mysave.
        Matlab files only store matrices. This auto-squeezes 1-dimensional matrices to arrays.
        Be careful if you are tyring to load a 1-d numpy matrix as an actual numpy matrix
    '''
    if filename[-4:] != '.mat':
        filename += '.mat'
    p = fileDir / filename
    rp = p.resolve()
    if not p.exists():
        raise FileNotFoundError(p)
    data = sio.loadmat(str(rp))
    for k, v in data.items():
        data[k] = np.squeeze(v)
    return data


def saveFigure(filename, figHandle=None):
    ''' if None, uses the gcf() '''
    if figHandle is None:
        figHandle = plt.gcf()
    if filename[-4:] != '.pdf':
        filename += '.pdf'
    rp = _makeFileExist(filename)
    print('Full path to figure is', rp)
    figHandle.tight_layout()
    pp = PdfPages(str(rp))
    pp.savefig(figHandle)
    pp.close()
