''' Some utility functions for printing to stdout used in the project

    Also contains web-based progress monitoring
'''
import sys
import numpy as np
import time
import socket
from pathlib import Path

from .paths import projectDir, monitorDir


def printWait(*args):
    r''' Prints your message followed by ``...``

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
    __tagHead = None
    __tagFoot = None

    def __init__(self, name, swpSize, runServer=True, stdoutPrint=False, **kwargs):  # pylint: disable=unused-argument
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
            print(self.getUrl())
            monitorDir.mkdir(exist_ok=True)  # pylint: disable=no-member
            fp = Path(ProgressWriter.progFileDefault)  # pylint: disable=no-member
            fp.touch()
            self.filePath = fp.resolve()
            self.__writeHtml()

        if self.printing:
            print(self.name)
            prntStr = ''
            for iterDim, _ in enumerate(self.size):
                prntStr += 'Dim-' + str(iterDim) + '...'
            print(prntStr)
            self.__writeStdio()

    @staticmethod
    def getUrl():
        ''' URL where the progress monitor will be hosted
        '''
        prefix = 'http://'
        host = socket.getfqdn().lower()
        try:
            with open(projectDir / '.monitorhostport', 'r') as fx:
                port = int(fx.readline())
        except FileNotFoundError:
            port = 'null'
        return prefix + host + ':' + str(port)

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
            t += r'<hr \>\\n'
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
        self.__tagFoot = None
        body = '<h2>Sweep completed!</h2>\n'
        body += ptag('At ' + ProgressWriter.tims(time.time()))
        htmlText = self.__tag(body, autorefresh=False)
        with self.filePath.open('w') as fx:  # pylint: disable=no-member
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
        body += r'<hr \>\\n'

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
            with self.filePath.open('w') as fx:  # pylint: disable=no-member
                fx.write(htmlText)

    def update(self, steps=1):
        if self.completed:
            raise Exception(
                'This sweep has supposedly completed. Make a new object to go again')
        for _ in range(steps):
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
