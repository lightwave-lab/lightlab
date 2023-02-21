from . import VISAInstrumentDriver
from lightlab.laboratory.instruments import VariableAttenuator

import numpy as np
import time


class HP_8156A_VA(VISAInstrumentDriver):
    ''' HP8156A variable attenuator

        `Manual <https://www.artisantg.com/info/ATGt6b5s.pdf>`__

        Usage: :any:`/ipynbs/Hardware/VariableAttenuator.ipynb`

    '''
    instrument_category = VariableAttenuator
    safeSleepTime = 1  # Time it takes to settle
    __attenDB = None

    def __init__(self, name='The VOA on the GC bench', address=None, **kwargs):
        VISAInstrumentDriver.__init__(self, name=name, address=address, **kwargs)

    def startup(self):
        self.on()

    def on(self):
        self.write(':OUTPUT:STATE 1')  # enable

    def off(self):
        self.write(':OUTPUT:STATE 0')  # disable

    def setAtten(self, val, isLin=True):
        ''' Simple method instead of property access '''
        if isLin:
            self.attenLin = val
        else:
            self.attenDB = val

    @property
    def attenDB(self):
        if self.__attenDB is None:
            self.__attenDB = float(self.query(":INPUT:ATTENUATION?"))
        return self.__attenDB

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
        self.write('INP:ATT ' + str(self.attenDB) + 'DB')
        time.sleep(sleepTime)  # Let it settle

    @property
    def wavelength(self):
        raise NotImplementedError('please implement me!')

    @property
    def calibration(self):
        raise NotImplementedError('please implement me!')
