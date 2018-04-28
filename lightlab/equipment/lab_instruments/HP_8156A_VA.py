from . import VISAInstrumentDriver
from lightlab.laboratory.instruments import VariableAttenuator
from lightlab.equipment.abstract_drivers import Configurable, ConfigProperty, ConfigEnableProperty

import numpy as np

class HP_8156A_VA(VISAInstrumentDriver, Configurable):
    ''' HP8156A variable attenuator

        `Manual <https://www.artisantg.com/info/ATGt6b5s.pdf>`__

        Usage: :any:`/ipynbs/Hardware/VariableAttenuator.ipynb`

    '''
    instrument_category = VariableAttenuator
    sleepOnChange = 1  # Time it takes to settle

    attenDB = ConfigProperty('INP:ATT', typeCast=float, limits=[0, 60])
    enable = ConfigEnableProperty('OUTP:STAT')

    def __init__(self, name='The VOA on the GC bench', address=None, **kwargs):
        VISAInstrumentDriver.__init__(self, name=name, address=address, **kwargs)
        Configurable.__init__(precedingColon=True, headerIsOptional=False)

    def startup(self):
        self.on()

    def on(self):
        self.enable = True

    def off(self):
        self.enable = False

    def setAtten(self, val, isLin=True):
        ''' Simple method instead of property access '''
        if isLin:
            self.attenLin = val
        else:
            self.attenDB = val

    @property
    def attenLin(self):
        return 10 ** (-self.attenDB / 10)

    @attenLin.setter
    def attenLin(self, newAttenLin):
        newAttenLin = max(newAttenLin, 1e-6)
        self.attenDB = -10 * np.log10(newAttenLin)

