import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import scipy.io as sio
import pickle
import gzip
import numpy as np

from . import _getFileDir


# File functions. You must set the fileDir first
def _makeFileExist(filename):
    ''' If the file doesn't exist, touch it

        Returns:
            (Path): the fully resolved path to file
    '''
    rp = _getFileDir(filename)
    os.makedirs(_getFileDir(), mode=0o775, exist_ok=True)
    rp.touch()
    print("Saving to file: {}".format(rp))
    return rp


def pprintFileDir(*, generate=False):
    ''' Prints the contents of io.fileDir.
        If the file can be loaded by this module,
        it gives the command to do so.

        Returns:
            A sorted list of files
    '''

    if generate:
        os.makedirs(_getFileDir(), mode=0o775, exist_ok=True)

    maxStrLen = 0
    for child in _getFileDir().iterdir():
        maxStrLen = max(maxStrLen, len(child.name))
    # Print directories
    for child in _getFileDir().iterdir():
        if child.name in ['.', '..', '.DS_Store']:
            continue
        if child.is_dir():
            print(child.name.rjust(maxStrLen), '** directory')
    # Print files
    childrenFiles = []
    for child in _getFileDir().iterdir():
        if child.name in ['.', '..', '.DS_Store']:
            continue
        if child.is_file():
            childrenFiles.append(child)
    childNames = list(map(lambda x: x.name, childrenFiles))
    sortedChildren = [x for _, x in sorted(zip(childNames, childrenFiles))]
    for child in sortedChildren:
        justified = child.name.rjust(maxStrLen) + '   '
        if child.name.endswith('.pkl'):
            print(justified, f'io.loadPickle(\'{child.stem}\')')
        elif child.name.endswith('.gz'):
            print(justified, f'io.loadPickleGzip(\'{child.stem}\')')
        elif child.name.endswith('.mat'):
            print(justified, f'io.loadMat(\'{child.stem}\')')
        else:
            print(justified)
    return sortedChildren


def _endingWith(filerootname, suffix):
    ''' Makes sure input string ends with the suffix '''
    froot = str(filerootname)
    if suffix[0] != '.':
        suffix = f'.{suffix}'
    if froot.endswith(suffix):
        return froot
    else:
        return froot + suffix


def savePickle(filename, dataTuple):
    ''' Uses pickle

        Args:
            filename (str, Path): file to write to
            dataTuple (tuple): tuple containing almost anything
    '''
    rp = _makeFileExist(_endingWith(filename, suffix='.pkl'))
    with rp.open('wb') as fx:
        pickle.dump(dataTuple, fx)


def loadPickle(filename):
    ''' Uses pickle '''
    rp = _getFileDir(_endingWith(filename, suffix='.pkl'))
    with rp.open('rb') as fx:
        return pickle.load(fx)


def savePickleGzip(filename, dataTuple):
    ''' Uses pickle

        Args:
            filename (str, Path): file to write to
            dataTuple (tuple): tuple containing almost anything
    '''
    filename = str(filename)

    # If user indicated .gz extension, then skip .pkl.gz extension addition
    if filename.endswith('.gz'):
        pklfilename = filename
    else:
        pklfilename = _endingWith(filename, suffix='.pkl')
    rp = _makeFileExist(_endingWith(pklfilename, suffix='.gz'))
    with gzip.open(rp, 'wb') as fx:
        pickle.dump(dataTuple, fx)


def loadPickleGzip(filename):
    ''' Uses pickle and then gzips the file.

        If it is named file.abc.gz, loads as file.abc.gz
        If it is named file.abc, loads as file.abc.pkl
    '''
    filename = str(filename)

    if filename.endswith('.gz'):
        pklfilename = filename
    else:
        pklfilename = _endingWith(filename, suffix='.pkl')
    rp = _getFileDir(_endingWith(pklfilename, suffix='.gz'))
    with gzip.open(rp, 'rb') as fx:
        return pickle.load(fx)


def saveMat(filename, dataDict):
    ''' dataDict has keys as names you would like to appear in matlab,
        values are numpy arrays, N-D arrays, or matrices.
    '''
    rp = _makeFileExist(_endingWith(filename, suffix='.mat'))
    sio.savemat(str(rp), dataDict)


def loadMat(filename):
    ''' returns a dictionary of data. This should perfectly invert saveMat.
        Matlab files only store matrices. This auto-squeezes 1-dimensional matrices to arrays.
        Be careful if you are tyring to load a 1-d numpy matrix as an actual numpy matrix
    '''
    rp = _getFileDir(_endingWith(filename, suffix='.mat'))
    data = sio.loadmat(str(rp))
    for k, v in data.items():
        data[k] = np.squeeze(v)
    return data


def saveFigure(filename, figHandle=None):
    ''' if None, uses the gcf() '''
    rp = _makeFileExist(_endingWith(filename, suffix='.pdf'))
    if figHandle is None:
        figHandle = plt.gcf()
    figHandle.tight_layout()
    pp = PdfPages(str(rp))
    pp.savefig(figHandle)
    pp.close()
