from ..visa_drivers import VISAInstrumentDriver

class Temp_SM(VISAInstrumentDriver):
    ''' Please rename.

        Current sources using DAC and voltage meters using ADC

        Supports multi-channel.

        Todo:
            To be implemented
    '''
    def __init__(self):
        pass

    def setCurrent(self, currDict):
        ''' Since multi-channel, takes a dictionary.

            Args:
                currDict (dict): dictionary of currents, keyed by channel number/name

            Returns:
                None
        '''
        pass

    def measVoltage(self, subset=None):
        ''' Since multi-channel, returns a dictionary, keyed by channel number/name

            Args:
                subset (set): keys of the channels to measure. If None, measures all.
            Returns:
                (dict): voltage values that are measured
        '''
        pass
