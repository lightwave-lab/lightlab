from . import VISAInstrumentDriver
from lightlab.laboratory.instruments import ArduinoInstrument


class Arduino_Instrument(VISAInstrumentDriver):
    ''' Read/write interface for an arduino. Could make use of TCPIP or maybe USB

        Usage: TODO

        Todo:
            To be implemented.
    '''
    instrument_category = ArduinoInstrument

    def __init__(self, name='Arduino', **kwargs):
        super().__init__(name=name, **kwargs)

    def write(self, writeStr):
        pass

    def query(self, queryStr, withTimeout=None):
        return 'hey'
