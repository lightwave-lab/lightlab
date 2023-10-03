from . import VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import PowerMeterAbstract
from lightlab.laboratory.instruments import PowerMeter


class Thorlabs_PM5020(VISAInstrumentDriver):
    ''' PM5020 Power Meter

    '''

    def __init__(self, name='Red Power Meter', address=None, **kwargs):
        VISAInstrumentDriver.__init__(self, name=name, address=address, **kwargs)
    
    def set_dbm(self, channel=1):
        self._set_unit(channel, "DBM")

    def set_watt(self, channel=1):
        self._set_unit(channel, "W")

    def _set_unit(self, channel, unit):
        """Sets dBm as the unit"""
        self.write(f"SENS{channel}:POW:UNIT {unit}")
        unit = self.query(f"SENS{channel}:POW:UNIT?")
        
    def getPowerDbm(self, channel=1):
        self.set_dbm(channel)
        return float(self.query(f"MEAS{channel}?"))
        
        
