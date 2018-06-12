from . import VISAInstrumentDriver
from lightlab.laboratory.instruments import VariableAttenuator

import numpy as np
import time


class HP_8157A_VA(VISAInstrumentDriver):
    ''' HP8157A variable attenuator

        `Manual <https://literature.cdn.keysight.com/litweb/pdf/08157-90012.pdf?id=1859520>`__

        Usage: :any:`/ipynbs/Hardware/VariableAttenuator.ipynb`

    '''
    instrument_category = VariableAttenuator
    safeSleepTime = 1  # Time it takes to settle
    __attenDB = None
    __wvl = None
    __cal = None

    def __init__(self, name='The VOA on the Minerva bench', address=None, **kwargs):
        VISAInstrumentDriver.__init__(self, name=name, address=address, **kwargs)

    def startup(self):
        self.on()

    def on(self):
        self.write('D 0')  # enable #D1

    def off(self):
        self.write('D 1')  # disable

    def setAtten(self, val, isLin=True):
        ''' Simple method instead of property access '''
        if isLin:
            self.attenLin = val
        else:
            self.attenDB = val

    @property
    def attenDB(self):
        if self.__attenDB is None:
            self.__attenDB = float(self.query("ATT?"))
        return self.__attenDB

    @property
    def wavelength(self):
        if self.__wvl is None:
            self.__wvl = float(self.query("WVL?")) * 1e9
        return self.__wvl

    @property
    def calibration(self):
        '''Calibration compensates for the insertion loss of the instruments.'''
        if self.__cal is None:
            self.__cal = float(self.query("CAL?"))
        return self.__cal

    @attenDB.setter
    def attenDB(self, newAttenDB):
        if newAttenDB < 0:
            newAttenDB = 0
        elif newAttenDB > 60:
            newAttenDB = 60
        self.__attenDB = newAttenDB
        self.sendToHardware()

    @property
    def attenLin(self):
        return 10 ** (-self.attenDB / 10)

    @attenLin.setter
    def attenLin(self, newAttenLin):
        newAttenLin = max(newAttenLin, 1e-6)
        self.attenDB = -10 * np.log10(newAttenLin)

    def sendToHardware(self, sleepTime=None):
        if sleepTime is None:
            sleepTime = self.safeSleepTime
        self.write('ATT ' + str(self.attenDB) + 'DB')
        time.sleep(sleepTime)  # Let it settle

    @calibration.setter
    def calibration(self, cal_factor, sleepTime=None):   # cal_factor is in dB
        if sleepTime is None:
            sleepTime = self.safeSleepTime
        self.write('CAL ' + str(cal_factor) + 'DB')
        time.sleep(sleepTime)  # Let it settle

    @wavelength.setter
    def wavelength(self, wl, sleepTime=None):   # wl can be in m, mm, um, or nm. here we choose nm.
        if sleepTime is None:
            sleepTime = self.safeSleepTime
        self. write('WVL' + str(wl) + 'NM')
        time.sleep(sleepTime)
