from . import VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import Configurable, ConfigProperty
from lightlab.laboratory.instruments import Clock

class Agilent_83712B_clock(VISAInstrumentDriver, Configurable):
    '''
        Where is manual?

        Usage: :any:`/ipynbs/Hardware/Clock.ipynb`
    '''
    instrument_category = Clock

    frequency = ConfigProperty('FREQ', typeCast=float, limits=[10e6, 20e9])

    def __init__(self, name='The clock on PPG', address=None, **kwargs):
        VISAInstrumentDriver.__init__(self, name=name, address=address, **kwargs)
        Configurable.__init__(self)

    def startup(self):
        self.enable(True)

    def enable(self, enaState=None):
        if enaState is not None:
            self.setConfigParam('OUTP:STATE', 'ON' if enaState else 'OFF')
        retStr = self.getConfigParam('OUTP:STATE')
        return retStr in [True, 'ON', 1, '1']
