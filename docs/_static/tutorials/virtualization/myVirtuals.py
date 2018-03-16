from lightlab.laboratory.virtualization import VirtualInstrument, DualInstrument
from lightlab.laboratory.instruments import Keithley  # the hardware instrument class

class VirtualKeithley(VirtualInstrument):
    def __init__(self, viResistiveRef):
        self.viResistiveRef = viResistiveRef
        self.__appliedVoltage = 0  # state

    def setVoltage(self, volts):
        self.__appliedVoltage = volts

    def measCurrent(self):
        return self.viResistiveRef.ivResponse(self.__appliedVoltage)


class DualKeithley(DualInstrument):
    real_klass = Keithley
    virt_klass = VirtualKeithley

    def __init__(self, *args, viResistiveRef=None, **kwargs):
        super().__init__(
            real_obj=self.real_klass(*args, **kwargs),
            virt_obj=self.virt_klass(viResistiveRef))

    def hardware_warmup(self):
        self.enable(True)

    def hardware_cooldown(self):
        self.enable(False)
