from . import VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import Configurable
from lightlab.laboratory.instruments import FunctionGenerator

import numpy as np
import time
from pyvisa import VisaIOError
from lightlab import visalogger as logger

VOLTAGE_MODE = 0
CURRENT_MODE = 1
DISABLED = 0
ENABLED = 1

class Keithley_2400_SM_v2(VISAInstrumentDriver, Configurable):
    ''' A Keithley 2400 driver.

        `Manual: <http://research.physics.illinois.edu/bezryadin/labprotocol/Keithley2400Manual.pdf>`__

        Usage: :any:`/ipynbs/Hardware/Keithley.ipynb`

        Capable of sourcing current and measuring voltage, such as a Keithley

        Also provides interface methods for measuring resistance and measuring power
    '''

    def __init__(self, name='Keithley 2400 SMU', address=None, **kwargs):
        VISAInstrumentDriver.__init__(self, name=name, address=address, **kwargs)
        Configurable.__init__(self, headerIsOptional=False, verboseIsOptional=False)
        self.mode = VOLTAGE_MODE
        self.activity = ENABLED
        self.enable(False)
        self.setVoltageMode()

    def startup(self):
        self.write('*RST')

    def useRearPort(self, use=True):
        if use:
            self.write("ROUT:TERM FRON")
        else:
            self.write("ROUT:TERM REAR")

    def __setSourceMode(self, isCurrentSource):
        if isCurrentSource:
            sourceStr, meterStr = ('CURR', 'VOLT')
            self.mode = CURRENT_MODE
        else:
            sourceStr, meterStr = ('VOLT', 'CURR')
            self.mode = VOLTAGE_MODE
        self.write(f'SOURCE:FUNC {sourceStr}')
        self.write('SOURCE:{}:MODE FIXED'.format(sourceStr))
        self.write('SENSE:FUNCTION:OFF:ALL')
        self.write('SENSE:FUNCTION "{}"'.format(meterStr))
        self.write('SENSE:{}:RANGE:AUTO ON'.format(meterStr))
        self.write('RES:MODE MAN')  # Manual resistance ranging

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
        if currAmps >= 0:
            currAmps = np.clip(currAmps, a_min=1e-9, a_max=1.)
        else:
            currAmps = np.clip(currAmps, a_min=-1, a_max=-1e-9)
        if currAmps != 0:
            needRange = 10 ** np.ceil(np.log10(abs(currAmps)))
            self.write(f'SOURCE:CURR:RANGE {needRange}')
        self.write(f'SOURCE:CURR {currAmps}')
        self._latestCurrentVal = currAmps

    def _configVoltage(self, voltVolts):
        voltVolts = float(voltVolts)
        if voltVolts != 0:
            needRange = 10 ** np.ceil(np.log10(np.abs(voltVolts)))
            self.write(f'SOURCE:VOLT:RANGE {needRange}')
        self.write(f'SOURCE:VOLT {voltVolts}')
        self._latestVoltageVal = voltVolts

    def setCurrent(self, currAmps):
        self._configCurrent(currAmps)

    def setVoltage(self, voltVolts):
        self._configVoltage(voltVolts)

    def getCurrent(self):
        return float(self.query('SOURCE:CURR?'))

    def getVoltage(self):
        return float(self.query('SOURCE:VOLT?'))

    def setProtectionVoltage(self, protectionVoltage):
        self.write(f'VOLT:PROT {protectionVoltage}')

    def setProtectionCurrent(self, protectionCurrent):
        self.write(f'CURR:PROT {protectionCurrent}')

    def measVoltage(self):
        return float(self.query('MEASURE:VOLT?').split(",")[0]) 

    def measCurrent(self):
        return float(self.query('MEASURE:CURR?').split(",")[1])

    def enable(self, activity=True):
        self.write(f'OUTP:STATE {1 if activity else 0}')
        self.activity = ENABLED if activity else DISABLED
