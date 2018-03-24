from . import VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import Configurable
from lightlab.laboratory.instruments import Clock

class Agilent_83712B_clock(VISAInstrumentDriver, Configurable):
    '''
        Where is manual?
    '''
    instrument_category = Clock

    def __init__(self, name='The clock on PPG', address=None, **kwargs):
        super().__init__(name=name, address=address, **kwargs)

    def startup(self):
        self.enable(True)

    def enable(self, enaState=None):
        if enaState is not None:
            self.setConfigParam('OUTP:STATE', 'ON' if enaState else 'OFF')
        retStr = self.getConfigParam('OUTP:STAT')
        return retStr in [True, 'ON', 1, '1']

    @property
    def frequency(self):
        return float(self.getConfigParam('FREQ'))

    @frequency.setter
    def frequency(self, newFreq):
        self.setConfigParam('FREQ', newFreq)