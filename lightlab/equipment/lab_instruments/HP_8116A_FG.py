from . import VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import Configurable, ConfigProperty, ConfigTokenProperty
from lightlab.laboratory.instruments import FunctionGenerator

import numpy as np
import time
from lightlab import visalogger as logger

class HP_8116A_FG(VISAInstrumentDriver, Configurable):
    '''
        Function Generator

        Manual?

        Usage: :any:`/ipynbs/Hardware/FunctionGenerator.ipynb`

    '''
    instrument_category = FunctionGenerator

    amplitude = ConfigProperty('AMP', typeCheck=float,
                               limits=[0.01, 10], termination='V')
    offset = ConfigProperty('OFS', typeCheck=float,
                            limits=None, termination='V')
    duty = ConfigProperty('DTY', limits=[0, 100], termination='%')
    waveform = ConfigTokenProperty('W', tokens=['dc', 'sine', 'triangle', 'square', 'pulse'])

    def __init__(self, name='The slow synth (FUNCTION GENERATOR)', address=None, **kwargs):
        VISAInstrumentDriver.__init__(self, name=name, address=address, **kwargs)
        Configurable.__init__(self, precedingColon=False, interveningSpace=False)

    def startup(self):
        self.write('D0')  # enable output

    def instrID(self):
        logger.warning('Function generator GPIB is broken, so cannot ensure if live')
        return 'Function generator, HP 8116A'

    def _getHardwareConfig(self, cStrList):
        raise Exception(
            'Function generator GPIB is broken so values can\'t be read from hardware')

    def _setHardwareConfig(self, subgroup=''):
        super()._setHardwareConfig(subgroup)
        time.sleep(.2)

    def frequency(self, newFreq=None):
        sciUnits = ['MZ', 'HZ', 'KHZ', 'MHZ']

        def toMultiplier(sciOrder):
            return 10 ** (3 * (sciOrder - 1))

        if newFreq is not None:
            sciOrder = int(np.ceil(np.log10(newFreq) / 3))
            logger.debug('sciOrder = {}'.format(sciOrder))
            sciUnit = sciUnits[sciOrder]
            logger.debug('sciUnit = {}'.format(sciUnit))
            sciFreq = newFreq / toMultiplier(sciOrder)
            self.setConfigParam('FRQ', '{} {}'.format(sciFreq, sciUnit))

        retSciStr = self.getConfigParam('FRQ')
        retSciElements = retSciStr.split(' ')
        sciFreq = float(retSciElements[0])
        sciUnit = retSciElements[1]
        realFreq = sciFreq * toMultiplier(sciUnits.index(sciUnit))
        return realFreq

