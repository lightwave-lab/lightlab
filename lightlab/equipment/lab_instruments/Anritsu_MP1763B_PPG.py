from . import VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import Configurable
from lightlab.laboratory.instruments import PulsePatternGenerator

import numpy as np

class Anritsu_MP1763B_PPG(VISAInstrumentDriver, Configurable):
    ''' ANRITSU MP1761A PulsePatternGenerator
        The PPG MP1763B at Alex's bench, which also support MP1761A (by Hsuan-Tung 07/27/2017)
    '''
    instrument_category = PulsePatternGenerator
    storedPattern = None

    def __init__(self, name='The PPG', address=None, **kwargs):
        VISAInstrumentDriver.__init__(
            self, name=name, address=address, **kwargs)
        Configurable.__init__(
            self, headerIsOptional=False, precedingColon=False)

    def startup(self):
        self.on()
        self.setConfigParam('PTS', 1)  # set to data pattern mode
        # set to negative because only data-bar works
        self.setConfigParam('LGC', 1)

    def setPrbs(self, length):
        ''' Generates a PRBS '''
        bits = np.random.randint(0, 2, length)
        print(bits)
        self.setPattern(bits)

    def setPattern(self, bitArray):
        ''' Data bitArray for the PPG to output.

            Args:
                bitArray (ndarray): array that is boolean or binary 1/0
        '''
        bitArray = np.array(bitArray, dtype=bool)
        bitArray = np.array(bitArray, dtype=int)
        # pad to multiple of 16
        pad = np.zeros(-len(bitArray) % 16, dtype=int)
        bitArrayPadded = np.concatenate((bitArray, pad))
        nBytes = int(np.ceil(len(bitArrayPadded) / 8))

        byteMat = np.reshape(bitArrayPadded, (nBytes, 8))
        pStr = ''
        intList = [None] * nBytes
        for i, bt in enumerate(byteMat):
            intVal = np.sum(bt * 2 ** np.arange(8))
            pStr += chr(intVal)
            # Switch to other endian
            if i % 2 == 0:
                ind = i + 1
            else:
                ind = i - 1
            intList[ind] = intVal
        byteList = bytes(intList)

        self.setConfigParam('PTS', 1)  # We only care to set data patterns
        # self.setConfigParam('DLN', 8*nBytes, forceHardware=True)
        self.setConfigParam('DLN', len(bitArray), forceHardware=True)
        preamble = 'WRT {}, 0'.format(nBytes)
        self.write(preamble)
        self.open()
        self.mbSession.write_raw(byteList)
        self.close()
        # self.write(pStr)

        self.storedPattern = bitArray
        print(bitArray)

    def getPattern(self):
        ''' Inverts the setPattern method, so you can swap several patterns around on the fly.
            Does not communicate with the hardware as of now.
        '''
        if self.storedPattern is None:
            raise NotImplementedError(
                'Can not read pattern from PPG. Set it first using this instance.')
        return self.storedPattern

    def on(self, turnOn=True):
        self.setConfigParam('OON', 1 if turnOn else 0)

    def syncSource(self, src=None):
        ''' Output synchronizer is locked to pattern or not?

            Args:
                src (str): either 'fixed', 'variable' or 'clock64'. If None, leaves it

            Returns:
                (str): the set value as a string token
        '''
        tokens = ['clock64', 'fixed', 'variable']
        if src is not None:
            try:
                iTok = tokens.index(src)
            except ValueError as e:
                raise ValueError(
                    src + ' is not a valid sync source: ' + str(tokens))
            self.setConfigParam('SOP', iTok)
        return tokens[int(self.getConfigParam('SOP'))]

    def amplAndOffs(self, amplOffs=None):
        ''' Amplitude and offset setting/getting

            Args:
                amplOffs (tuple(float)): new amplitude and offset in volts
                If either is None, returns but does not set

            Returns:
                (tuple(float)): amplitude and offset, read from hardware if specified as None
        '''
        if amplOffs is None:
            amplOffs = (None, None)
        if np.isscalar(amplOffs):
            raise ValueError('amplOffs must be a tuple. ' +
                             'You can specify one element as None if you don\'t want to set it')
        amplitude, offset = amplOffs
        if amplitude is not None:
            self.setConfigParam('DAP', amplitude)
        if offset is not None:
            self.setConfigParam('DOS', offset)
        ampl = float(self.getConfigParam('DAP'))
        offs = float(self.getConfigParam('DOS'))
        return (ampl, offs)
