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


# This imports all of the modules in this folder
# As well as all their member classes that are VISAInstrumentDrivers
import importlib
import pkgutil

for _, modname, _ in pkgutil.walk_packages(path=__path__,
                                                  prefix=__name__ + '.'):
    _temp = importlib.import_module(modname)
    for k, v in _temp.__dict__.items():
        try:
            mro = v.mro()
        except AttributeError:
            continue
        if VISAInstrumentDriver in mro:
            globals()[k] = v
