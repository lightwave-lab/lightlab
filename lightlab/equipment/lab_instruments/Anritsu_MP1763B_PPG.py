from . import VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import Configurable
from lightlab.laboratory.instruments import PulsePatternGenerator
import warnings
import numpy as np
import matplotlib.pyplot as plt


class Anritsu_MP1763B_PPG(VISAInstrumentDriver, Configurable):
    ''' ANRITSU MP1761A PulsePatternGenerator
        The PPG MP1763B at Alex's bench, which also support MP1761A (by Hsuan-Tung 07/27/2017)

        Manual?

        Usage: :any:`/ipynbs/Hardware/PulsePatternGenerator.ipynb`

    '''
    instrument_category = PulsePatternGenerator
    storedPattern = None

    def __init__(self, name='The PPG', address=None, **kwargs):
        VISAInstrumentDriver.__init__(self, name=name, address=address, **kwargs)
        Configurable.__init__(self, headerIsOptional=False, precedingColon=False)

    def startup(self):
        self.on()
        self.setConfigParam('PTS', 1)  # set to data pattern mode
        # set to negative because only data-bar works
        self.setConfigParam('LGC', 1)

    def setPrbs(self, length):
        ''' Generates a PRBS '''
        bits = np.random.randint(0, 2, length)
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
        # print(bitArray)

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
            except ValueError:
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

    # defining function bitsequence, that takes delays and transfer them into a sequence we want.

    def bitseq(self, chpulses, clockfreq, ext=0, addplot=False, mult=1, res=5):
        '''
        bitseq: Takes in dictionary 'chpulses', clock freq 'clockfreq', and opt.
        parameter 'ext.' Also includes plotting parameters (see below).
        chdelays: a dictionary in which keys are channel delays, and values
        contain a list of tuple pairs. Each pair contains pulse times (rising
        edges) and their duration (in ns).
        clockfreq: set the current clock frequency, in GHz
        ext: a continuous value from 0 to 1 which extends the pattern length,
        resulting in different synchronization between adjacent time windows.
        0 -- will result in maximum similarity between time  windows, plus or
        minus variabilities resulting from delay lines. This is ideal when
        only approximate timings are required, since channels IDs can be
        shuffled by time scrolling through the same PPG pattern.
        1 -- will result in minimum similarity between adjacent time windows,
        at the cost of a larger total PPG pattern length. Anything beyond this
        value is not useful. Values between 0 and 1 will trade-off pattern length
        with window similarity.
        addplot: Adds a plot to visualize the output of the PPG along all channels.
        mult: graphing parameter - how many multiples of pattern length to display in time
        res: graphing parameter - how many sampling points per pattern bit
        Author: Mitchell A. Nahmias, Feb. 2018
        '''

        delays = sorted(chpulses.keys())
        # timeWindow = min(np.diff(delays))
        ChNum = len(chpulses)
        totalTime = np.mean(np.diff(delays)) * ChNum * (1 + ext)

        # bitLength = int(np.round(timeWindow*clockfreq))
        totalBitLength = int(np.round(totalTime * clockfreq))

        pattern = np.zeros(totalBitLength, dtype=int)
        warningFlag = False

        for delay in chpulses:
            for pulses in chpulses[delay]:

                pulsePos = pulses[0]
                pulseWidth = pulses[1]

                if not warningFlag and pulseWidth < 2 / clockfreq:
                    warnings.warn(
                        'Pulse width(s) may be too short. Consider increasing the clock rate.')
                    warningFlag = True

                # for X active channels, apply a [delay(X) - delay(X-i)] time offset

                # Note: Given N channels, the synchronized pulses appear at time window N. Therefore, the minimum
                # delay channel (D=0) outputs the (P=N) set of pulses, the second min. delay channel (D=1)
                # outputs the (P=N-1) set of pulses, etc.
                # As a result, each pulse receives an inverse channel delay: K - current_delay + pulsePosition, for some K.
                # We set K to max(delay) since that sets the last channel [max(delay)] at the beginning of the pattern.

                pIndex = int(np.round((max(chpulses.keys()) - delay + pulsePos) * clockfreq))
                # add pulse to pattern at correct delay
                pattern[pIndex:pIndex + int(np.round(pulseWidth * clockfreq))] = 1

        # optional plotting function
        if addplot:
            T = np.linspace(0, mult * len(pattern) / clockfreq, mult * res * len(pattern))

            # allows cyclical access to pattern array via any input index
            def circ_time(T, pattern):
                pattern_ind = (np.round(T * clockfreq) % len(pattern)).astype(int)
                return pattern[pattern_ind]

            plt.figure(figsize=(15, 5))
            for d in delays:
                plt.plot(T, circ_time(T - d, pattern), label=str(int(d)) + ' ns')
            plt.xlabel('Time (ns)')
            plt.ylabel('a.u.')
            plt.title('Expected Output')
            plt.legend()

        return pattern
