import numpy as np
import time

from . import VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import Configurable

class Keithley_2400_SM(VISAInstrumentDriver, Configurable):
    ''' A Keithley 2400 driver.

        Manual: http://research.physics.illinois.edu/bezryadin/labprotocol/Keithley2400Manual.pdf

        Capable of sourcing current and measuring voltage, such as a Keithley

        Also provides interface methods for measuring resistance and measuring power

        Todo:
            Lots. This is currently limited only to set current, measure voltage, single-shot
    '''
    autoDisable = None  # in seconds. NOT IMPLEMENTED
    function_mode = None
    _latestCurrentVal = 0
    _latestVoltageVal = 0

    def __init__(self, name=None, address=None, **kwargs):
        '''
            Args:
                hostID (str): There are three different hosts in the lab, \'andromeda'\, \'corinna'\,\'olympias'\
                protectionVoltage : The unit of compliance voltage is Volt.
        '''
        super().__init__(name=name, address=address,
                         headerIsOptional=False, verboseIsOptional=False,
                         **kwargs)

        self.protectionVoltage = kwargs.pop("protectionVoltage", 4)
        self.protectionCurrent = kwargs.pop("protectionCurrent", 200E-3)

        self.currStep = kwargs.pop("currStep", 1.0E-3)
        self.voltStep = kwargs.pop("voltStep", 0.1)

    def startup(self):
        self.write('*RST')

    def setPort(self, port):
        if port == 'Front':
            self.setConfigParam('ROUT:TERM', 'FRON')
        elif port == 'Rear':
            self.setConfigParam('ROUT:TERM', 'REAR')

    def __setSourceMode(self, isCurrentSource):
        # TODO: make proper automata flowchart for this.
        if isCurrentSource:
            sourceStr, meterStr = ('CURR', 'VOLT')
        else:
            sourceStr, meterStr = ('VOLT', 'CURR')
        self.setConfigParam('SOURCE:FUNC', sourceStr)
        self.setConfigParam('SOURCE:{}:MODE'.format(sourceStr), 'FIXED')
        self.setConfigParam('SENSE:FUNCTION:OFF:ALL')
        self.setConfigParam('SENSE:FUNCTION:ON', '"CURR"')
        self.setConfigParam('SENSE:{}:RANGE:AUTO'.format(meterStr), 'ON')
        self.setConfigParam('RES:MODE', 'MAN')  # Manual resistance ranging

    def setVoltageMode(self, protectionCurrent=0.05):
        self.__setSourceMode(isCurrentSource=False)
        self.function_mode = 'voltage'
        self.setProtectionCurrent(protectionCurrent)
        self._configVoltage(0)

    def setCurrentMode(self, protectionVoltage=1):
        self.__setSourceMode(isCurrentSource=True)
        self.function_mode = 'current'
        self.setProtectionVoltage(protectionVoltage)
        self._configCurrent(0)

    def _configCurrent(self, currAmps, autoOn=False, time_delay=0.0):
        currAmps = float(currAmps)
        np.clip(currAmps, a_min=1e-6, a_max=1.)
        if currAmps != 0:
            needRange = 10 ** np.ceil(np.log10(abs(currAmps)))
            self.setConfigParam('SOURCE:CURR:RANGE', needRange)
        self.setConfigParam('SOURCE:CURR', currAmps)
        self._latestCurrentVal = currAmps
        if autoOn:
            self.enable(True)
        time.sleep(time_delay)

    def _configVoltage(self, volt, autoOn=False, time_delay=0.0):
        if volt != 0:
            needRange = 10 ** np.ceil(np.log10(np.abs(volt)))
            self.setConfigParam('SOURCE:VOLT:RANGE', needRange)
        self.setConfigParam('SOURCE:VOLT', volt)
        self._latestVoltageVal = volt
        if autoOn:
            self.enable(True)
        time.sleep(time_delay)

    def setCurrent(self, currAmps):
        ''' This leaves the output on indefinitely '''
        currTemp = self._latestCurrentVal
        if (self.enable() \
                and self.currStep is not None \
                and abs(currTemp - currAmps) > self.currStep):
            for curr in np.linspace(currTemp, currAmps, 1 + abs(currTemp - currAmps) / self.currStep)[1:]:
                self._configCurrent(curr)
        else:
            self._configCurrent(currAmps)

    def setVoltage(self, volt):
        voltTemp = self._latestVoltageVal
        if (self.enable() \
                and self.voltStep is not None \
                and abs(voltTemp - volt) > self.voltStep):
            for volt in np.linspace(voltTemp, volt, 1 + abs(voltTemp - volt) / self.voltStep)[1:]:
                self._configVoltage(volt)
        else:
            self._configVoltage(volt)

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

    def setProtectionVoltage(self, protectionVoltage, autoOn=False):
        self.protectionVoltage = protectionVoltage
        self.setConfigParam('VOLT:PROT', self.protectionVoltage)

    def setProtectionCurrent(self, protectionCurrent, autoOn=False):
        self.protectionCurrent = protectionCurrent
        self.setConfigParam('CURR:PROT', self.protectionCurrent)

    def measVoltage(self, autoOff=False):
        retStr = self.query('MEASURE:VOLT?')
        v = float(retStr.split(',')[0])  # first number is voltage always
        if autoOff:
            self.enable(False)
        if v >= self.protectionVoltage:
            print('Warning: Keithley compliance voltage of',
                  self.protectionVoltage, 'reached.')
            print('Warning: You are sourcing', v *
                  self._latestCurrentVal * 1e-3, 'mW into the load.')
        return v

    def measCurrent(self, autoOff=False):
        retStr = self.query('MEASURE:CURR?')
        i = float(retStr.split(',')[1])  # second number is current always
        if autoOff:
            self.enable(False)
        if i >= self.protectionCurrent:
            print('Warning: Keithley compliance current of',
                  self.protectionCurrent, 'reached.')
            print('Warning: You are sourcing', i *
                  self._latestVoltageVal * 1e-3, 'mW into the load.')
        return i

    def enable(self, newState=None):
        ''' get/set enable state
        '''
        if newState is False:
            if (self.function_mode == 'current'):
                self.setCurrent(0)
            elif (self.function_mode == 'voltage'):
                self.setVoltage(0)
        if newState is not None:
            self.setConfigParam('OUTP:STATE', 1 if newState else 0)
        retVal = self.getConfigParam('OUTP:STATE', forceHardware=True)
        return retVal in ['ON', 1, '1']


class Keithley_2400_SM_noRamp(Keithley_2400_SM):
    ''' Same except with no ramping. You see what you get
    '''
    def setCurrent(self, *args, **kwargs):
        return self._configCurrent(*args, **kwargs)

    def setVoltage(self, *args, **kwargs):
        return self._configVoltage(*args, **kwargs)

