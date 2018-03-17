from ..visa_connection import VISAObject
from lightlab import logger


class VISAInstrumentDriver(VISAObject):
    """Generic (but not abstract) class for an instrument
    Initialize using the literal visa address

    Contains a visa communication object

    This might be the place to handle message session opening/closing
        release() should have an effect on both the message session and the lockout manager
    """

    def __init__(self, name='Default Driver', address=None, **kwargs):
        self.name = name
        if 'tempSess' not in kwargs.keys():
            kwargs['tempSess'] = True
        super().__init__(address, **kwargs)
        self.__started = False

    def startup(self):
        logger.debug("{}startup method empty".format(self.__class__.__name__))

    def open(self):
        super().open()
        if not self.__started:
            self.startup()
            self.__started = True


DefaultDriver = VISAInstrumentDriver

# Instrument = VISAInstrumentDriver
# USBinstrumentDriver = Instrument
# GpibInstrumentDriver = VISAInstrumentDriver
# GPIBinstrument = VISAInstrumentDriver
# TCPIPinstrument = TCPIPinstrumentDriver
# USBinstrument = USBinstrumentDriver

from .Advantest_Q8221_PM import Advantest_Q8221_PM
from .Agilent_83712B_clock import Agilent_83712B_clock
from .Agilent_N5183A_VG import Agilent_N5183A_VG
from .Agilent_N5222A_NA import Agilent_N5222A_NA
from .Anritsu_MP1763B_PPG import Anritsu_MP1763B_PPG
from .Apex_AP2440A_OSA import Apex_AP2440A_OSA
from .Arduino_Instrument import Arduino_Instrument
from .current_source import CurrentSources
from .current_source import NI_PCI_6723
from .HP_8116A_FG import HP_8116A_FG
from .HP_8152A_PM import HP_8152A_PM
from .HP_8156A_VA import HP_8156A_VA
from .ILX_7900B_LS import ILX_7900B_LS
from .Keithley_2400_SM import Keithley_2400_SM, Keithley_2400_SM_noRamp
from .RandS_SMBV100A_VG import RandS_SMBV100A_VG
from .Tektronix_Oscopes import *
from .Tektronix_RSA6120B_RFSA import Tektronix_RSA6120B_RFSA
