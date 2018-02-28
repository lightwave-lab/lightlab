''' Some utility functions for printing to stdout used in the project
'''

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import time
from matplotlib.backends.backend_pdf import PdfPages
import scipy.io as sio
import pickle
import gzip
import lightlab.util.gitpath as gitpath
from lightlab import logger
import jsonpickle
from lightlab.laboratory import Hashable

# for serializing np.ndarrays
import msgpack
import msgpack_numpy
msgpack_numpy.patch()

try:
    projectDir = Path(gitpath.root())
except IOError as e:
    # git repo not found, logging that.
    logger.warning(e)
    projectDir = Path(os.getcwd())
    logger.warning("Default projectDir='{}'".format(projectDir))
if not os.access(projectDir, 7):
    logger.warning("Cannot write to this projectDir({}).".format(projectDir))

# Monitor files
monitorDir = projectDir / 'progress-monitor'
# Data files
dataHome = projectDir / 'data'
fileDir = dataHome  # Set this in your experiment


def printWait(*args):
    ''' Prints your message followed by ``...``

        This displays immediately, but
            * your next print will show up on the same line

        Args:
            \*args (Tuple(str)): Strings that will be written
    '''
    msg = ''
    for a in args:
        msg += str(a)
    print(msg + "... ", end='')
    sys.stdout.flush()


def printProgress(*args):
    ''' Deletes current line and writes.

    This is used for updating iterating values so to not produce a ton of output

    Args:
        *args (str, Tuple(str)): Arguments that will be written
    '''
    msg = ''
    for a in args:
        msg += str(a)
    sys.stdout.write('\b' * 1000)
    sys.stdout.flush()
    sys.stdout.write(msg)
    sys.stdout.write('\n')


class ProgressWriter(object):
    ''' Writes progress to an html file for long sweeps. Including timestamps. Has an init and an update method

        You can then open this file to the internet by running a HTTP server.

        To setup a continuously running server::

            screen -S sweepProgressServer
            (Enter)
            cd /home/atait/Documents/calibration-instrumentation/sweepMonitorServer/
            python3 -m http.server 8050
            (Ctrl-a, d)

        To then access from a web browser::
            http://lightwave-lab-olympias.princeton.edu:8050

        Todo:
            Have this class launch its own process server upon init
            Make it so you can specify actuator names
    '''
    progFileDefault = monitorDir / 'sweep.html'
    tFmt = '%a, %d %b %Y %H:%M:%S'

    def __init__(self, name, swpSize, runServer=True, stdoutPrint=False, **kwargs):
        '''
            Args:
                name (str): name to be displayed
                swpSize (tuple): size of each dimension of the sweep
        '''
        self.name = name

        if np.isscalar(swpSize):
            swpSize = [swpSize]
        self.size = np.array(swpSize)
        self.currentPnt = np.zeros_like(self.size)

        self.totalSize = np.prod(self.size)
        self.ofTotal = 0
        self.completed = False

        self.serving = runServer
        self.printing = stdoutPrint

        self.startTime = time.time()  # In seconds since the epoch

        if self.serving:
            print('See sweep progress online at')
            # print(getUrl())
            monitorDir.mkdir(exist_ok=True)
            fp = Path(ProgressWriter.progFileDefault)
            fp.touch()
            self.filePath = fp.resolve()
            self.__writeHtml()

        if self.printing:
            print(self.name)
            prntStr = ''
            for iterDim, dimSize in enumerate(self.size):
                prntStr += 'Dim-' + str(iterDim) + '...'
            print(prntStr)
            self.__writeStdio()

    def __tag(self, bodytext, autorefresh=False):
        ''' Do the HTML tags '''
        if not hasattr(self, '__tagHead') or self.__tagHead is None:
            t = '<!DOCTYPE html>\n'
            t += '<html>\n'
            t += '<head>\n'
            t += '<title>'
            t += 'Sweep Progress Monitor'
            t += '</title>\n'
            if autorefresh:
                t += '<meta http-equiv="refresh" content="5" />\n'  # Autorefresh every 5 seconds
            t += '<body>\n'
            t += '<h1>' + self.name + '</h1>\n'
            t += '<hr \>\n'
            self.__tagHead = t
        if not hasattr(self, '__tagFoot') or self.__tagFoot is None:
            t = '</body>\n'
            t += '</html>\n'
            self.__tagFoot = t
        return self.__tagHead + bodytext + self.__tagFoot

    def __writeStdioEnd(self):
        # display.clear_output(wait=True)
        print('Sweep completed!')

    def __writeHtmlEnd(self):
        self.__tagHead = None
        body = '<h2>Sweep completed!</h2>\n'
        body += ptag('At ' + ProgressWriter.tims(time.time()))
        htmlText = self.__tag(body, autorefresh=False)
        with self.filePath.open('w') as fx:
            fx.write(htmlText)

    def __writeStdio(self):
        prntStr = ''
        for iterDim, dimSize in enumerate(self.size):
            of = (self.currentPnt[iterDim] + 1, dimSize)
            prntStr += '/'.join((str(v) for v in of)) + '...'
        print(prntStr)

    def __writeHtml(self):
        # Write lines for progress in each dimension
        body = ''
        for i, p in enumerate(self.currentPnt):
            dimStr = i * 'sub-' + 'dimension[' + str(i) + '] : '
            dimStr += str(p + 1) + ' of ' + str(self.size[i])
            body += ptag(dimStr)
        body += '<hr \>\n'

        # Calculating timing
        currentTime = time.time()
        tSinceStart = currentTime - self.startTime
        completeRatio = (self.ofTotal + 1) / self.totalSize
        endTime = self.startTime + tSinceStart / completeRatio

        body += ptag('(Start Time)           ' +
                     ProgressWriter.tims(self.startTime))
        body += ptag('(Latest Update)        ' +
                     ProgressWriter.tims(currentTime))
        body += ptag('(Expected Completion)  ' + ProgressWriter.tims(endTime))

        # Say where the files are hosted
        body += ptag('This monitor service is hosted in the directory:')
        body += ptag(str(monitorDir))

        # Write to html file
        if self.serving:
            htmlText = self.__tag(body, autorefresh=True)
            with self.filePath.open('w') as fx:
                fx.write(htmlText)

    def update(self, steps=1):
        if self.completed:
            raise Exception(
                'This sweep has supposedly completed. Make a new object to go again')
        for i in range(steps):
            self.__updateOneInternal()
        if not self.completed:
            if self.serving:
                self.__writeHtml()
            if self.printing:
                self.__writeStdio()
        else:
            if self.serving:
                self.__writeHtmlEnd()
            if self.printing:
                self.__writeStdioEnd()

    def __updateOneInternal(self):
        for i in range(len(self.size)):
            if self.currentPnt[-i - 1] < self.size[-i - 1] - 1:
                self.currentPnt[-i - 1] += 1
                break
            else:
                self.currentPnt[-i - 1] = 0
        self.ofTotal += 1
        if self.ofTotal == self.totalSize:
            self.completed = True

    @classmethod
    def tims(cls, epochTime):
        return time.strftime(cls.tFmt, time.localtime(epochTime)) + '\n'

def ptag(s):
    return '<p>' + s + '</p>\n'



# File functions. You must set the fileDir first

def _makeFileExist(filename):
    ''' If the file doesn't exist, touch it

        Returns:
            (Path): the fully resolved path to file
    '''
    p = fileDir / filename
    os.makedirs(fileDir, mode=0o775, exist_ok=True)
    p.touch()
    rp = p.resolve()
    logger.debug("Saving to file: {}".format(rp))
    return rp


def savePickle(filename, dataTuple):
    ''' Uses pickle

        Todo: timestamping would be cool
    '''
    rp = _makeFileExist(filename)
    with rp.open('wb') as fx:
        pickle.dump(dataTuple, fx)


def loadPickle(filename):
    ''' Uses pickle '''
    p = fileDir / filename
    rp = p.resolve()
    print(rp)
    with rp.open('rb') as fx:
        return pickle.load(fx)


class HardwareReference(object):
    def __init__(self, klassname):
        self.klassname = klassname

class SerializedNumpy(object):
    def __init__(self, arrayVersion):
        self.encoded = msgpack.packb(arrayVersion, default=msgpack_numpy.encode)

    @classmethod
    def deserialize(self, bytesVersion):
        return msgpack.unpackb(bytesVersion, object_hook=msgpack_numpy.decode)

class JSONpickleable(Hashable):
    ''' Produces human readable json files. Inherits _toJSON from Hashable
        Automatically strips attributes beginning with __.

        Attributes:
            notPickled (set): names of attributes that will be guaranteed to exist in instances.
                They will not go into the pickled
                Good for references to things like hardware instruments that you should re-init when reloading.


        See the test_JSONpickleable for much more detail
    '''
    notPickled = set()
    is_npArray = set()

    def __getstate__(self):
        '''
        This method removes all variables in ``notPickled`` during
        serialization.
        '''
        state = super().__getstate__()
        allNotPickled = self.__class__.notPickled
        for base in self.__class__.__bases__:
            try:
                theirNotPickled = getattr(base, 'notPickled')
                allNotPickled = allNotPickled.union(theirNotPickled)
            except AttributeError:
                pass

        keys_to_delete = set()
        for key, val in state.items():
            if isinstance(key, str):
                if key in allNotPickled:
                    keys_to_delete.add(key)
                elif (val.__class__.__name__ == 'VISAObject' or
                    any(base.__name__ == 'VISAObject' for base in val.__class__.__bases__)):
                    klassname = val.__class__.__name__
                    logger.warning('Not pickling {} = {}.'.format(key, klassname))
                    state[key] = HardwareReference('Reference to a ' + klassname)
                elif isinstance(val, np.ndarray):
                    state[key] = SerializedNumpy(val)
        for key in keys_to_delete:
            del state[key]
        return state

    def __setstate__(self, state):
        for key, val in state.items():
            if isinstance(val, HardwareReference):
                state[key] = None
            elif isinstance(val, SerializedNumpy):
                state[key] = SerializedNumpy.deserialize(val.encoded)

        for a in self.notPickled:
            state[a] = None

        super().__setstate__(state)

    @classmethod
    def _fromJSONcheck(cls, json_string):
        ''' Converts to object which is returned

            Also checks if the class is the right type and its attributes are correct
        '''
        json_state = jsonpickle.json.decode(json_string)
        context = jsonpickle.unpickler.Unpickler(backend=jsonpickle.json, safe=True, keys=True)
        try:
            restored_object = context.restore(json_state, reset=True)
        except AttributeError as err:
            newm = err.args[0] + '\n' + 'This is that strange jsonpickle error trying to get aDict.__name__. You might be trying to pickle a function.'
            err.args = (newm,) + err.args[1:]
            raise

        if not isinstance(restored_object, cls): # This is likely to happen if lightlab has been reloaded
            if type(restored_object).__name__ != cls.__name__: # This is not ok
                raise TypeError('Loaded class is different than intended.\n' +
                    'Got {}, needed {}.'.format(type(restored_object).__name__))

        for a in cls.notPickled:
            setattr(restored_object, a, None)

        for key, val in restored_object.__dict__.items():
            if isinstance(val, HardwareReference):
                setattr(restored_object, key, None)
            elif isinstance(val, SerializedNumpy):
                setattr(restored_object, key, SerializedNumpy.deserialize(val.encoded))

        return restored_object

    def copy(self):
        ''' This will throw out hardware references and anything starting with __

            Good test for what will be saved
        '''
        return self._fromJSONcheck(self._toJSON())

    def save(self, filename):
        if filename[-4:] != '.json':
            filename += '.json'
        with open(filename, 'w') as f:
            f.write(self._toJSON())

    @classmethod
    def load(cls, filename):
        if filename[-4:] != '.json':
            filename += '.json'
        with open(filename, 'r') as f:
            frozen = f.read()
        return cls._fromJSONcheck(frozen)

    def __str__(self):
        return self._toJSON()


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


class ChannelError(Exception):
    pass


class RangeError(Exception):
    pass
