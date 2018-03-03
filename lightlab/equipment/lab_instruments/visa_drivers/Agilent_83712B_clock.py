from ..visa_drivers import VISAInstrumentDriver
from ..configure.configurable import Configurable


class Agilent_83712B_clock(VISAInstrumentDriver, Configurable):
    """
    """
    # def __init__(self, address=19, hostname='andromeda'): # Add GPIB address and hostname to Clock
    #     super().__init__('The clock on the PPG', address, hostNS[hostname])
    # id string:HEWLETT-PACKARD,83712B,US37101574,REV  10.0
    def __init__(self, name='The clock on PPG', address=None, **kwargs):
        VISAInstrumentDriver.__init__(self, name=name, address=address, **kwargs)
        Configurable.__init__(self)

    def startup(self):
        self.on()

    def on(self, turnOn=True):
        onStr = 'ON' if turnOn else 'OFF'
        self.setConfigParam('OUTP:STATE', onStr)

    @property
    def frequency(self):
        return float(self.getConfigParam('FREQ'))

    @frequency.setter
    def frequency(self, newFreq):
        self.setConfigParam('FREQ', newFreq)
