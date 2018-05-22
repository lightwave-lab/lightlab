from . import VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import Configurable
from lightlab.laboratory.instruments import FunctionGenerator

import numpy as np
import time
from pyvisa import VisaIOError
from lightlab import visalogger as logger
from . import BuggyHardware


class HP_8116A_FG(VISAInstrumentDriver, Configurable):
    '''
        Function Generator

        `Manual <http://www.nousnexus.com/Manuals/Agilent_HP_8116A_manual.pdf>`__

        Usage: :any:`/ipynbs/Hardware/FunctionGenerator.ipynb`

    '''
    instrument_category = FunctionGenerator

    amplitudeRange = (.01, 10)

    def __init__(self, name='The slow synth (FUNCTION GENERATOR)', address=None, **kwargs):
        VISAInstrumentDriver.__init__(self, name=name, address=address, **kwargs)
        Configurable.__init__(self, precedingColon=False, interveningSpace=False)

    def startup(self):
        self.write('D0')  # enable output

    def instrID(self):
        logger.warning('Function generator GPIB is broken, so cannot ensure if live')
        return 'Function generator, HP 8116A'

    def _getHardwareConfig(self, cStrList):
        raise BuggyHardware(
            'Synth GPIB is broken so values can\'t be read from hardware')

    def _setHardwareConfig(self, subgroup=''):
        super()._setHardwareConfig(subgroup)
        time.sleep(.2)

    def enable(self, enaState=None):  # pylint: disable=unused-argument
        raise BuggyHardware('This old synth can\'t be enabled remotely')

    def frequency(self, newFreq=None):
        sciUnits = ['MZ', 'HZ', 'KHZ', 'MHZ']

        def toMultiplier(sciOrder):
            return 10 ** (3 * (sciOrder - 1))

        if newFreq is not None:
            sciOrder = int(np.ceil(np.log10(newFreq) / 3))
            logger.debug('sciOrder = %s', sciOrder)
            sciUnit = sciUnits[sciOrder]
            logger.debug('sciUnit = %s', sciUnit)
            sciFreq = newFreq / toMultiplier(sciOrder)
            self.setConfigParam('FRQ', '{} {}'.format(sciFreq, sciUnit))

        retSciStr = self.getConfigParam('FRQ')
        retSciElements = retSciStr.split(' ')
        sciFreq = float(retSciElements[0])
        sciUnit = retSciElements[1]
        realFreq = sciFreq * toMultiplier(sciUnits.index(sciUnit))
        return realFreq

    def waveform(self, newWave=None):
        ''' Available tokens are 'dc', 'sine', 'triangle', 'square', 'pulse'
        '''
        tokens = ['dc', 'sine', 'triangle', 'square', 'pulse']
        if newWave is not None:
            try:
                iTok = tokens.index(newWave)
            except ValueError:
                raise ValueError(
                    newWave + ' is not a valid sync source: ' + str(tokens))
            self.setConfigParam('W', iTok)
        return tokens[int(self.getConfigParam('W'))]

    def amplAndOffs(self, amplOffs=None):
        ''' Amplitude and offset setting/getting

            Only uses the data-bar because the other one is broken

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
        amplitude = np.clip(amplitude, *self.amplitudeRange)

        if amplitude is not None:
            self.setConfigParam('AMP', '{} V'.format(amplitude))
        try:
            ampl = float(self.getConfigParam('AMP').split(' ')[0])
        except VisaIOError:
            logger.error('unable to get the amplitude')
            ampl = None
        if offset is not None:
            self.setConfigParam('OFS', '{} V'.format(offset))
        try:
            offs = float(self.getConfigParam('OFS').split(' ')[0])
        except VisaIOError:
            logger.error('unable to get the offset')
            offs = None
        return (ampl, offs)

    def duty(self, duty=None):
        ''' duty is in percentage '''
        if duty is not None:
            self.setConfigParam('DTY', '{} %'.format(duty))

        return self.getConfigParam('DTY')
