from . import VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import Configurable
from lightlab.laboratory.instruments import PatternGenerator

import numpy as np
import time
from lightlab import visalogger as logger


class Tektronix_PPG3202(VISAInstrumentDriver, Configurable):

    ''' Python driver for Tektronix PPG 3202
    '''

    instrument_category = PatternGenerator
    __ClockDivider = np.array([1, 2, 4, 8, 16])
    __channels = np.array([1, 2])
    __patternType = np.array(['PRBS', 'DATA'])
    __waitTime = 0        # May be needed to prevent Timeout error

    def __init__(self, name='Pattern Generator', address=None, **kwargs):
        VISAInstrumentDriver.__init__(self, name=name, address=address, **kwargs)
        Configurable.__init__(self)

    def __setVoltage(self, chan=None, amp=None, offset=None):
        ''' Set the voltage on the specified channel
        '''
        if amp is not None and chan in self.__channels:
            time.sleep(self.__waitTime)
            cmd = str(':VOLT' + str(chan) + ':POS ' + str(amp) + 'V')
            self.setConfigParam(cmd, None, True)
        if offset is not None:
            time.sleep(self.__waitTime)
            cmd = str(':VOLT' + str(chan) + ':POS:OFFS ' + str(offset) + 'V')
            self.setConfigParam(cmd, None, True)

    def __setPatternType(self, chan=None, ptype=None):
        ''' Set the data pattern on the specified channel. Type can only be 'PRBS'
            or 'DATA'
        '''
        if ptype is not None and chan in self.__channels:
            if ptype not in self.__patternType:
                logger.exception('Wrong Pattern Type!')
            else:
                time.sleep(self.__waitTime)
                cmd = str(':DIG' + str(chan) + ':PATT:TYPE ' + str(ptype))
                self.setConfigParam(cmd, None, True)

    def setDataRate(self, rate=None):
        ''' Set the data rate of the PPG. Data rate can only be in the range of
            1.5 Gb/s to 32 Gb/s
        '''
        if rate is not None:
            if rate < 1.5 or rate > 32:
                logger.exception('Invalid Data Rate!')
            else:
                time.sleep(self.__waitTime)
                cmd = str(':FREQ ' + str(rate) + 'e9')
                self.setConfigParam(cmd, None, True)

    def setMainParam(self, chan=None, amp=None, offset=None, ptype=None):
        ''' One function to set all parameters on the main window
        '''
        if chan is None:
            logger.exception('Please Specify Channel Number!')
        else:
            self.__setVoltage(chan, amp, offset)
            self.__setPatternType(chan, ptype)

    def setClockDivider(self, div=None):
        if div is not None:
            if (div in self.__ClockDivider):
                time.sleep(self.__waitTime)
                cmd = str(':OUTP:CLOC:DIV ' + str(div))
                self.setConfigParam(cmd, None, True)
            else:
                logger.exception('Wrong Clock Divider Value!')

    def setDataMemory(self, chan=None, startAddr=None, bit=None, data=None):
        if chan is not None and chan in self.__channels:
            time.sleep(self.__waitTime)
            cmd = str(':DIG' + str(chan) + ':PATT:DATA ' + str(startAddr) + ',' + str(bit) + ',' + str(data))
            self.setConfigParam(cmd, None, True)
        else:
            logger.exception('Please choose Channel 1 or 2!')

    def setHexDataMemory(self, chan=None, startAddr=None, bit=None, Hdata=None):
        if chan is not None and chan in self.__channels:
            time.sleep(self.__waitTime)
            cmd = str(':DIG' + str(chan) + ':PATT:HDAT ' + str(startAddr) + ',' + str(bit) + ',' + str(Hdata))
            self.setConfigParam(cmd, None, True)
        else:
            logger.exception('Please choose Channel 1 or 2!')

    def channelOn(self, chan=None):
        if chan is not None and chan in self.__channels:
            time.sleep(self.__waitTime)
            cmd = str(':OUTP' + str(chan) + ' ON')
            self.setConfigParam(cmd, None, True)
        else:
            logger.exception('Please choose Channel 1 or 2!')

    def channelOff(self, chan=None):
        if chan is not None and chan in self.__channels:
            time.sleep(self.__waitTime)
            cmd = str(':OUTP' + str(chan) + ' OFF')
            self.setConfigParam(cmd, None, True)
        else:
            logger.exception('Please choose Channel 1 or 2!')


    def getAmplitude(self, chan=None):
        if chan is not None and chan in self.__channels:
            return self.query(':VOLT' + str(chan) + ':POS?')

    def getOffset(self, chan=None):
        if chan is not None and chan in self.__channels:
            return self.query(':VOLT' + str(chan) + ':POS:OFFS?')

    def getDataRate(self):
        return self.query(':FREQ?')

    def getPatternType(self, chan=None):
        if chan is not None and chan in self.__channels:
            return self.query(':DIG' + str(chan) + ':PATT:TYPE?')

    def getClockDivider(self):
        return self.query(':OUTP:CLOC:DIV?')
