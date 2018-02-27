from ..visa_drivers import VISAInstrumentDriver

class Arduino_Instrument(VISAInstrumentDriver):
    ''' Read/write interface for an arduino. Could make use of TCPIP or maybe USB

        Todo:
            To be implemented.
    '''
    def __init__(self, arg=None):
        # super().__init__()
        self.arg = arg

    def write(self, writeStr):
        pass

    def query(self):
        return 'hey'
