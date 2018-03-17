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

    # TODO: send config params in a delayed fashion (only when necessary)
    def __init__(self, name=None, address=None, **kwargs):
        '''
            Args:
                sourceMode (str): UNUSED NOW, \'mwpwerohm\' or \'milliamps\'
                hostID (str): There are three different hosts in the lab, \'andromeda'\, \'corinna'\,\'olympias'\
                protectionVoltage : The unit of compliance voltage is Volt.
        '''

        # visaAddress = address
        VISAInstrumentDriver.__init__(
            self, name=name, address=address, **kwargs)
        Configurable.__init__(self, headerIsOptional=False,
                              verboseIsOptional=False)
        sourceMode = kwargs.pop("sourceMode", 'mwperohm')
        protectionVoltage = kwargs.pop("protectionVoltage", 4)
        protectionCurrent = kwargs.pop("protectionCurrent", 200E-3)
        currStep = kwargs.pop("currStep", 1.0E-3)
        voltStep = kwargs.pop("voltStep", 0.1)
        if sourceMode not in ['mwperohm', 'milliamps']:
            raise ValueError(
                'sourceMode must be \'mwpwerohm\' or \'milliamps\'')
        self.sourceMode = sourceMode
        self.currStep = currStep
        self.voltStep = voltStep
        self.protectionVoltage = protectionVoltage
        self.protectionCurrent = protectionCurrent
        self.latestCurrentVal = None
        self.latestVoltageVal = None
        # self.setConfigParam('SOURCE:FUNC', 'CURR')
        # self.setConfigParam('SOURCE:CURR:MODE', 'FIXED')
        # self.setConfigParam('VOLT:PROT', self.protectionVoltage)
        # self.setConfigParam('RES:MODE', 'MAN')  # Manual resistance ranging
        # self._configCurrent(0)

    def startup(self):
        self.write('*RST')

    def setPort(self, port):
        if port == 'Front':
            self.write(':ROUT:TERM FRON')
        elif port == 'Rear':
            self.write(':ROUT:TERM REAR')

    def setVoltageMode(self, protectionCurrent=0.05):
        # TODO: make proper automata flowchart for this.
        self.enable(False)
        self.function_mode = 'voltage'
        self.setConfigParam('SOURCE:FUNC', 'VOLT')
        self.setConfigParam('SOURCE:VOLT:MODE', 'FIXED')
        self.setConfigParam('SENSE:FUNCTION:OFF:ALL')
        self.setConfigParam('SENSE:FUNCTION:ON', '"CURR"')
        self.setConfigParam('SENSE:CURR:RANGE:AUTO', 'ON')
        self.setProtectionCurrent(protectionCurrent)
        self.setConfigParam('RES:MODE', 'MAN')  # Manual resistance ranging
        self._configVoltage(0)

    def setCurrentMode(self, protectionVoltage=1):
        # TODO: make proper automata flowchart for this.
        self.enable(False)
        self.function_mode = 'current'
        self.setConfigParam('SOURCE:FUNC', 'CURR')
        self.setConfigParam('SOURCE:CURR:MODE', 'FIXED')
        self.setConfigParam('SENSE:FUNCTION:OFF:ALL')
        self.setConfigParam('SENSE:FUNCTION:ON', '"VOLT"')
        self.setConfigParam('SENSE:VOLT:RANGE:AUTO', 'ON')
        self.setProtectionVoltage(protectionVoltage)
        self.setConfigParam('RES:MODE', 'MAN')  # Manual resistance ranging
        self._configCurrent(0)

    def _configCurrent(self, currAmps, autoOn=False, time_delay=0.0):
        currAmps = float(currAmps)
        np.clip(currAmps, a_min=1e-6, a_max=1.)
        if currAmps != 0:
            needRange = 10 ** np.ceil(np.log10(abs(currAmps)))
            self.setConfigParam('SOURCE:CURR:RANGE', needRange)
        self.setConfigParam('SOURCE:CURR', currAmps)
        self.latestCurrentVal = currAmps
        if autoOn:
            self.enable(True)
        time.sleep(time_delay)

    def _configVoltage(self, volt, autoOn=False, time_delay=0.0):
        if volt != 0:
            needRange = 10 ** np.ceil(np.log10(np.abs(volt)))
            self.setConfigParam('SOURCE:VOLT:RANGE', needRange)
        self.setConfigParam('SOURCE:VOLT', volt)
        self.latestVoltageVal = volt
        if autoOn:
            self.enable(True)
        time.sleep(time_delay)

    def setCurrent(self, currAmps, autoOn=False):
        ''' This leaves the output on indefinitely '''
        if self.latestCurrentVal is None:
            self.latestCurrentVal = 0.
        currTemp = self.latestCurrentVal

        if self.enable() & (abs(currTemp - currAmps) > self.currStep):
            for curr in np.linspace(currTemp, currAmps, 1 + abs(currTemp - currAmps) / self.currStep):
                self._configCurrent(curr)
        else:
            self._configCurrent(currAmps)

    def setVoltage(self, volt, autoOn=False):
        if self.latestVoltageVal is None:
            self.latestVoltageVal = 0
        voltTemp = self.latestVoltageVal

        if self.enable() & (abs(voltTemp - volt) > self.voltStep):
            for volt in np.linspace(voltTemp, volt, 1 + abs(voltTemp - volt) / self.voltStep):
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
                  self.latestCurrentVal * 1e-3, 'mW into the load.')
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
                  self.latestVoltageVal * 1e-3, 'mW into the load.')
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

