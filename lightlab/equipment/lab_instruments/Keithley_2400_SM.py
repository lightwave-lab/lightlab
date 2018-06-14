from . import VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import Configurable
from lightlab.laboratory.instruments import Keithley

import numpy as np
import time
from lightlab import logger


class Keithley_2400_SM(VISAInstrumentDriver, Configurable):
    ''' A Keithley 2400 driver.

        `Manual: <http://research.physics.illinois.edu/bezryadin/labprotocol/Keithley2400Manual.pdf>`__

        Usage: :any:`/ipynbs/Hardware/Keithley.ipynb`

        Capable of sourcing current and measuring voltage, such as a Keithley

        Also provides interface methods for measuring resistance and measuring power
    '''
    instrument_category = Keithley
    autoDisable = None  # in seconds. NOT IMPLEMENTED
    _latestCurrentVal = 0
    _latestVoltageVal = 0
    currStep = None
    voltStep = None
    rampStepTime = 0.01  # in seconds.

    def __init__(self, name=None, address=None, **kwargs):
        '''
            Args:
                currStep (float): amount to step if ramping in current mode. Default (None) is no ramp
                voltStep (float): amount to step if ramping in voltage mode. Default (None) is no ramp
                rampStepTime (float): time to wait on each ramp step point
        '''
        self.currStep = kwargs.pop("currStep", None)
        self.voltStep = kwargs.pop("voltStep", None)
        self.rampStepTime = kwargs.pop("rampStepTime", 0.01)
        VISAInstrumentDriver.__init__(self, name=name, address=address, **kwargs)
        Configurable.__init__(self, headerIsOptional=False, verboseIsOptional=False)

    def startup(self):
        self.write('*RST')

    def setPort(self, port):
        if port == 'Front':
            self.setConfigParam('ROUT:TERM', 'FRON')
        elif port == 'Rear':
            self.setConfigParam('ROUT:TERM', 'REAR')

    def __setSourceMode(self, isCurrentSource):
        if isCurrentSource:
            sourceStr, meterStr = ('CURR', 'VOLT')
        else:
            sourceStr, meterStr = ('VOLT', 'CURR')
        self.setConfigParam('SOURCE:FUNC', sourceStr)
        self.setConfigParam('SOURCE:{}:MODE'.format(sourceStr), 'FIXED')
        self.setConfigParam('SENSE:FUNCTION:OFF:ALL')
        self.setConfigParam('SENSE:FUNCTION:ON', '"{}"'.format(meterStr))
        self.setConfigParam('SENSE:{}:RANGE:AUTO'.format(meterStr), 'ON')
        self.setConfigParam('RES:MODE', 'MAN')  # Manual resistance ranging

    def setVoltageMode(self, protectionCurrent=0.05):
        self.enable(False)
        self.__setSourceMode(isCurrentSource=False)
        self.setProtectionCurrent(protectionCurrent)
        self._configVoltage(0)

    def setCurrentMode(self, protectionVoltage=1):
        self.enable(False)
        self.__setSourceMode(isCurrentSource=True)
        self.setProtectionVoltage(protectionVoltage)
        self._configCurrent(0)

    def _configCurrent(self, currAmps):
        currAmps = float(currAmps)
        currAmps = np.clip(currAmps, a_min=1e-6, a_max=1.)
        if currAmps != 0:
            needRange = 10 ** np.ceil(np.log10(abs(currAmps)))
            self.setConfigParam('SOURCE:CURR:RANGE', needRange)
        self.setConfigParam('SOURCE:CURR', currAmps)
        self._latestCurrentVal = currAmps

    def _configVoltage(self, voltVolts):
        voltVolts = float(voltVolts)
        if voltVolts != 0:
            needRange = 10 ** np.ceil(np.log10(np.abs(voltVolts)))
            self.setConfigParam('SOURCE:VOLT:RANGE', needRange)
        self.setConfigParam('SOURCE:VOLT', voltVolts)
        self._latestVoltageVal = voltVolts

    def setCurrent(self, currAmps):
        ''' This leaves the output on indefinitely '''
        currTemp = self._latestCurrentVal
        if not self.enable() or self.currStep is None:
            self._configCurrent(currAmps)
        else:
            nSteps = int(np.floor(abs(currTemp - currAmps) / self.currStep))
            for curr in np.linspace(currTemp, currAmps, 1 + nSteps)[1:]:
                self._configCurrent(curr)
                time.sleep(self.rampStepTime)

    def setVoltage(self, voltVolts):
        voltTemp = self._latestVoltageVal
        if not self.enable() or self.voltStep is None:
            self._configVoltage(voltVolts)
        else:
            nSteps = int(np.floor(abs(voltTemp - voltVolts) / self.voltStep))
            for volt in np.linspace(voltTemp, voltVolts, 1 + nSteps)[1:]:
                self._configVoltage(volt)
                time.sleep(self.rampStepTime)

    def getCurrent(self):
        currGlob = self.getConfigParam('SOURCE:CURR')
        if type(currGlob) is dict:
            currGlob = currGlob['&']
        return currGlob

    def getVoltage(self):
        voltGlob = self.getConfigParam('SOURCE:VOLT')
        if type(voltGlob) is dict:
            voltGlob = voltGlob['&']
        return voltGlob

    def setProtectionVoltage(self, protectionVoltage):
        self.setConfigParam('VOLT:PROT', protectionVoltage)

    def setProtectionCurrent(self, protectionCurrent):
        self.setConfigParam('CURR:PROT', protectionCurrent)

    @property
    def protectionVoltage(self):
        return self.getConfigParam('VOLT:PROT')

    @property
    def protectionCurrent(self):
        return self.getConfigParam('CURR:PROT')

    def measVoltage(self):
        retStr = self.query('MEASURE:VOLT?')
        v = float(retStr.split(',')[0])  # first number is voltage always
        if v >= self.protectionVoltage:
            logger.warning('Keithley compliance voltage of %s reached', self.protectionVoltage)
            logger.warning('You are sourcing %smW into the load.', v * self._latestCurrentVal * 1e-3)
        return v

    def measCurrent(self):
        retStr = self.query('MEASURE:CURR?')
        i = float(retStr.split(',')[1])  # second number is current always
        if i >= self.protectionCurrent:
            logger.warning('Keithley compliance current of %s reached', self.protectionCurrent)
            logger.warning('You are sourcing %smW into the load.', i * self._latestVoltageVal * 1e-3)
        return i

    def enable(self, newState=None):
        ''' get/set enable state
        '''
        if newState is False:
            if self.getConfigParam('SOURCE:FUNC') == 'CURR':
                self.setCurrent(0)
            else:
                self.setVoltage(0)
        if newState is not None:
            self.setConfigParam('OUTP:STATE', 1 if newState else 0)
        retVal = self.getConfigParam('OUTP:STATE', forceHardware=True)
        return retVal in ['ON', 1, '1']
