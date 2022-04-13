from . import VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import Configurable
from lightlab.laboratory.instruments import FunctionGenerator

import numpy as np
import time
from pyvisa import VisaIOError
from lightlab import visalogger as logger
from . import BuggyHardware


class HP_83712B_CWG(VISAInstrumentDriver, Configurable):
    '''
        Synthesized Continuous Wave Generator

        `Manual <https://www.keysight.com/us/en/product/83712B/synthesized-cw-generator-10-mhz-to-20-ghz.html>`__

        Usage: :any:`/ipynbs/Hardware/FunctionGenerator.ipynb`

    '''

    def __init__(self, name='Continuous Wave Generator', address=None, **kwargs):
        VISAInstrumentDriver.__init__(self, name=name, address=address, **kwargs)
        Configurable.__init__(self, precedingColon=False, interveningSpace=False)

    def startup(self):
        self.write('*RST')

    def get_frequency(self):
        return(self.query("FREQ?"))

    def set_frequency(self, frequency):
        self.write(f"FREQ {frequency}")
