'''
This module provides an interface for instruments in the lab and virtual ones.
'''
from lightlab.laboratory import Node
from lightlab.laboratory.devices import Device
import lightlab.laboratory.state as labstate
from lightlab.equipment.lab_instruments import VISAObject, DefaultDriver
from .experiments import DualMethod, Virtualizable

from lightlab import logger
import os
import pyvisa


class Host(Node):
    """ Class storing information about computer hosts, from which GPIB commands
    are issued."""
    name = None
    mac_address = None
    hostname = None
    os = "linux-ubuntu"  # linux-ubuntu, linux-centos, windows, mac etc.
    instruments = None

    __cached_list_resources_info = None
    __cached_gpib_instrument_list = None

    def __init__(self, instruments=None, *args, **kwargs):
        if instruments is None:
            instruments = list()
        super().__init__(instruments=instruments, *args, **kwargs)

    def __contains__(self, item):
        instrument_search = item in self.instruments
        if not instrument_search:
            logger.info("{} not found in {}'s instruments.".format(item, self))
        return instrument_search

    def isLive(self):
        ''' Pings the system and returns if it is alive.
        '''
        logger.debug("Pinging %s...", self.hostname)
        response = os.system("ping -c 1 {}".format(self.hostname))
        if response != 0:
            logger.warning("%s is not reachable via ping.", self)
        return response == 0

    def list_resources_info(self, use_cached=True, is_local=False):
        if self.__cached_list_resources_info is None:
            use_cached = False
        if use_cached:
            return self.__cached_list_resources_info
        else:
            if is_local:
                list_query = "?*::INSTR"
            else:
                list_query = "visa://" + self.hostname + "/?*::INSTR"
            rm = pyvisa.ResourceManager()
            logger.debug("Caching resource list in %s", self)
            self.__cached_list_resources_info = rm.list_resources_info(
                query=list_query)
            return self.__cached_list_resources_info

    def list_gpib_resources_info(self, use_cached=True, is_local=False):
        return {resource_name: resource
                for resource_name, resource in self.list_resources_info(use_cached=use_cached, is_local=is_local).items()
                if resource.interface_type == pyvisa.constants.InterfaceType.gpib}

    def get_all_gpib_id(self, use_cached=True, is_local=False):
        gpib_resources = self.list_gpib_resources_info(use_cached=use_cached, is_local=is_local)
        if self.__cached_gpib_instrument_list is None:
            use_cached = False
        if use_cached:
            return self.__cached_gpib_instrument_list
        else:
            gpib_instrument_list = dict()
            logger.debug("Caching GPIB instrument list in %s", self)
            for gpib_address in gpib_resources.keys():
                visa_object = VISAObject(gpib_address, tempSess=True)
                try:
                    instr_id = visa_object.instrID()
                    gpib_instrument_list[gpib_address] = instr_id
                except pyvisa.VisaIOError as err:
                    logger.error(err)
            self.__cached_gpib_instrument_list = gpib_instrument_list
            return gpib_instrument_list

    def findGpibAddressById(self, id_string_search, use_cached=True):
        gpib_ids = self.get_all_gpib_id(use_cached=use_cached)
        for gpib_address, id_string in gpib_ids.items():
            if id_string_search == id_string:
                logger.info("Found %s in %s.", id_string_search, gpib_address)
                return gpib_address
        logger.warning("{} not found in {}".format(id_string_search, self))
        raise NotFoundError(
            "{} not found in {}".format(id_string_search, self))

    def addInstrument(self, *instruments):
        for instrument in instruments:
            if instrument not in self.instruments:
                self.instruments.append(instrument)

    def removeInstrument(self, *instruments):
        for instrument in instruments:
            try:
                self.instruments.remove(instrument)
                instrument._host = None
            except ValueError as err:
                logger.warn("%s not currently connectd to %s",
                            instrument, self)

    def checkInstrumentsLive(self):
        all_live = True
        for instrument in self.instruments:
            if instrument.isLive():
                logger.info("%s is live.", instrument)
            else:
                all_live = False
        return all_live

    def __str__(self):
        return "Host {}".format(self.name)


class Bench(Node):
    """ Class storing information about benches, for the purpose of
    facilitating location in lab. """
    name = None
    devices = None
    instruments = None

    def __contains__(self, item):

        if isinstance(item, Instrument):
            instrument_search = item in self.instruments
            if not instrument_search:
                logger.info("{} not found in {}'s instruments.".format(item, self))
            return instrument_search
        elif isinstance(item, Device):
            device_search = item in self.devices
            if not device_search:
                logger.info("{} not found in {}'s devices.".format(item, self))
            return device_search
        else:
            logger.debug("{} is neither an Instrument nor a Device".format(item))
            return False

    def __init__(self, name, devices=None,
                 instruments=None, *args, **kwargs):

        self.name = name
        if devices is None:
            devices = list()
        self.devices = devices
        if instruments is None:
            instruments = list()
        self.instruments = instruments
        super().__init__(*args, **kwargs)

    def addInstrument(self, *instruments):
        for instrument in instruments:
            if instrument not in self.instruments:
                self.instruments.append(instrument)

    def removeInstrument(self, *instruments):
        # TODO Remove all connections
        for instrument in instruments:
            try:
                self.instruments.remove(instrument)
                instrument._bench = None
            except ValueError as err:
                logger.warn("%s not currently placed in %s", instrument, self)

    def addDevice(self, *devices):
        for device in devices:
            if device not in self.devices:
                self.devices.append(device)

    def removeDevice(self, *devices):
        # TODO Remove all connections
        for device in devices:
            try:
                self.devices.remove(device)
            except ValueError as err:
                logger.warn("%s not currently placed in %s", device, self)

    def display(self):
        # Print benches table
        lines = ["{}".format(self)]
        lines.append("===========")
        lines.append("Instruments")
        lines.append("===========")
        if len(self.instruments) > 0:
            lines.extend(["   {} ({})".format(str(instrument), str(instrument.host)) for instrument in self.instruments])
        else:
            lines.append("   No instruments.")
        lines.append("=======")
        lines.append("Devices")
        lines.append("=======")
        if len(self.devices) > 0:
            lines.extend(["   {}".format(str(device)) for device in self.devices])
        else:
            lines.append("   No devices.")
        lines.append("***")
        print("\n".join(lines))

    def __str__(self):
        return "Bench {}".format(self.name)


def callablePublicMethodsDir(obj):
    directory = dir(obj)
    iHidden = []
    for i, attr in enumerate(directory):
        if attr[0] == '_':
            iHidden.append(i)
    for i in iHidden[::-1]:
        del directory[i]
    return directory


#TODO add instrument equality function
class Instrument(Node):
    """ Class storing information about instruments, for the purpose of
    facilitating verifying whether it is connected to the correct devices. """
    _driver_class = None
    __driver_object = None
    address = None

    _id_string = None
    _name = None
    __bench = None
    __host = None
    ports = None

    essentialMethods = []

    def __init__(self, name="Unnamed Instrument", id_string=None, address=None, **kwargs):
        self.__bench = kwargs.pop("bench", None)
        self.__host = kwargs.pop("host", None)
        self.ports = kwargs.pop("ports", dict())
        self.address = address

        self._driver_class = kwargs.pop("driver_class", None)
        if self._driver_class is None:
            self._driver_class = kwargs.pop("_driver_class", None)
        self.__driver_object = kwargs.pop("driver_object", None)
        if self._driver_class is not None and self.__driver_object is not None:
            assert isinstance(self.__driver_object, self._driver_class)

        # make methods for feedthrough
        for funName in type(self).essentialMethods:
            if type(self.driver) is not DefaultDriver:
                try:
                    driverMethod = getattr(self.driver, funName)
                except AttributeError as err:
                    newm = err.args[0] + '\nDriver does not implement ' + funName
                    newm += '\nIt does do ' + str(callablePublicMethodsDir(self.driver))
                    err.args = (newm,) + err.args[1:]
                    raise err
                setattr(self, funName, driverMethod)
            else:
                setattr(self, funName, raiseAnException('Driver not present. Cannot use asReal'))

        super().__init__(_name=name,
                         _id_string=id_string, **kwargs)

    @property
    def driver_object(self):
        if self.__driver_object is None:
            kwargs = dict()
            for kwarg in ["useChans", "stateDict", "sourceMode"]:
                try:
                    kwargs[kwarg] = getattr(self, kwarg)
                except AttributeError:
                    pass
            driver_class = self.driver_class
            self.__driver_object = driver_class(
                name=self.name, address=self.address, **kwargs)
        return self.__driver_object

    def startup(self):
        return self.driver_object.startup()

    @property
    def driver_class(self):
        if self._driver_class is None:
            logger.warning("Using default driver for %s.", self)
            return DefaultDriver
        else:
            return self._driver_class

    @property
    def bench(self):
        if self.__bench is None:
            self.__bench = labstate.lab.findBenchFromInstrument(self)
        return self.__bench

    @bench.setter
    def bench(self, new_bench):
        if self.bench is not None:
            self.bench.removeInstrument(self)
        if new_bench is not None:
            new_bench.addInstrument(self)
        self.__bench = new_bench

    @property
    def host(self):
        if self.__host is None:
            self.__host = labstate.lab.findHostFromInstrument(self)
        return self.__host

    @host.setter
    def host(self, new_host):
        if self.host is not None:
            self.host.removeInstrument(self)
        if new_host is not None:
            new_host.addInstrument(self)
        self.__host = new_host

    @property
    def name(self):
        return self._name

    @property
    def id_string(self):
        return self._id_string

    def __str__(self):
        return "{}".format(self.name)

    def display(self):
        # Print benches table
        lines = ["{}".format(self)]
        lines.append("Bench: {}".format(self.bench))
        lines.append("Host: {}".format(self.host))
        lines.append("address: {}".format(self.address))
        lines.append("=====")
        lines.append("Ports")
        lines.append("=====")
        if len(self.ports) > 0:
            lines.extend(["   {}".format(str(port)) for port in self.ports])
        else:
            lines.append("   No ports.")
        lines.append("***")
        print("\n".join(lines))

    def isLive(self):
        try:
            driver = self.driver_object
            if self.id_string is not None:
                query_id = driver.instrID()
                if self.id_string == query_id:
                    logger.info("Found %s in %s.", self.name, self.address)
                    return True
                else:
                    logger.warn("%s: %s, expected %s", self.address,
                                query_id, self.id_string)
                    return False
            else:
                logger.debug("Cannot authenticate %s in %s.",
                             self.name, self.address)
                return True
        except Exception as err:
            logger.warning(err)
            return False

    def connectHost(self, host):
        # if gpib_address is None:
        #     if self.gpib_address is None:
        #         self.gpib_address = self.findAddressById(host)
        # else:
        #     logger.info("Manually locating %s in %s", self, gpib_address)
        #     self.gpib_address = gpib_address
        self.host = host

    @property
    def driver(self):
        return self.driver_object

    # @classmethod
    # def fromGpibAddress(cls, gpib_address):
    #     visa_object = VISAObject(gpib_address, tempSess=True)
    #     # TODO untreated error when there is no device with that address!
    #     id_string = visa_object.instrID()
    #     return cls(id_string, gpib_address=gpib_address)


class NotFoundError(RuntimeError):
    pass


def raiseAnException(text):
    ''' Returns a function that just raises a NotImplementedError with the specified text

        Sometimes it is good to have a method exist and be unspecified, even if it cannot be called.
        That's when you would use this.
    '''
    def notImp(*args, **kwargs):
        raise NotImplementedError(text)
    return notImp


class DualInstrument(Virtualizable):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not isinstance(self, Instrument):
            raise TypeError('Something that is a DualInstrument must also inherit Instrument from elsewhere.\n'
                + 'Class ' + self.__class__.__name__ + ', which inherits: \n'
                + '\n'.join(bas.__name__ for bas in self.__class__.mro()[1:]))

        # figure out all the callables in hardware version
        # if not implemented by type(self), set virtual version ot notImp
        for funName in self.essentialMethods:
            hwMethod = getattr(self, funName)
            try:
                virtualMethod = getattr(self, 'v_' + funName)
            except AttributeError:
                virtualMethod = raiseAnException('Virtual version not specified: v_' + funName)
            dualizedMethod = DualMethod(self, virtual_function=virtualMethod, hardware_function=hwMethod)
            setattr(self, funName, dualizedMethod)

    @classmethod
    def fromInstrument(cls, hwOnlyInstr, **kwargs):
        ''' Gives a new dual instrument that has all the same properties and references.
            This is especially useful if you have an instrument stored in the JSON labstate,
            and would then like to virtualize it in your notebook.

            Does not reinitialize the driver. Keeps the same one.

            The instrument base of hwOnlyInstr must be the same instrument base of this class
        '''
        instrumentBaseClass = None
        for bas in cls.__bases__:
            if issubclass(bas, Instrument):
                instrumentBaseClass = bas
                break
        else:
            raise TypeError('This DualInstrument subclass, {}, does not inherit from an Instrument class'.format(cls.__name__))
        if not isinstance(hwOnlyInstr, instrumentBaseClass):
            raise TypeError('The fromInstrument ({}) is not an instance of the expected Instrument class ({})'.format(hwOnlyInstr.__class__.__name__, instrumentBaseClass.__name__))

        for attr in ['driver_class', 'driver_object', 'address', 'id_string', 'name', 'bench', 'host', 'ports']:
            kwargs[attr] = getattr(hwOnlyInstr, attr)
        return cls(**kwargs)

    def asReal(self):
        assert self.driver is not None
        return super().asReal()


# Aliases
# TODO VERIFY CODE BELOW


class PowerMeter(Instrument):
    essentialMethods = ['powerDbm', 'powerLin']


class SourceMeter(Instrument):
    essentialMethods = [
        'setCurrent',
        'getCurrent',
        'measVoltage',
        'setProtectionVoltage',
        'setProtectionCurrent',
        'enable']


class Keithley(SourceMeter):
    essentialMethods = SourceMeter.essentialMethods + \
        ['setPort',
        'setCurrentMode',
        'setVoltageMode',
        'getCurrent',
        'getVoltage',
        'setVoltage',
        'measCurrent']


class VectorGenerator(Instrument):
    def amplitude(self, amp=None):
        return self.driver.amplitude(amp)

    def frequency(self, freq=None):
        return self.driver.frequency(freq)

    def enable(self, enaState=None):
        return self.driver.enable(enaState)

    def modulationEnable(self, enaState=None):
        return self.driver.modulationEnable(enaState)

    def addNoise(self, enaState=True, bandwidth=None, cnRatio=None):
        return self.driver.addNoise(enaState,bandwidth,cnRatio)

    def setPattern(self, bitArray):
        return self.driver.setPattern(bitArray)

    def digiMod(self, enaState=True, symbRate=None, amExtinct=None):
        return self.driver.digiMod(enaState,symbRate,amExtinct)

    def carrierMod(self, enaState=True, typMod=None, deviation=None, modFreq=None):
        return self.driver.carrierMod(enaState,typMod,deviation,modFreq)

    def listEnable(self, enaState=True, freqs=None, amps=None, isSlave=False, dwell=None):
        return self.driver.listEnable(enaState,freqs,amps,isSlave,dwell)

    def sweepSetup(self, startFreq, stopFreq, nPts=100, dwell=0.1):
        return self.driver.sweepSetup(startFreq,stopFreq,nPts,dwell)

    def sweepEnable(self, swpState=None):
        return self.driver.sweepEnable(swpState)


class Clock(Instrument):
    def on(self, turnOn=True):
        return self.driver.on(turnOn=turnOn)

    @property
    def frequency(self):
        return self.driver.frequency

    @frequency.setter
    def frequency(self, newFreq):
        self.driver.frequency = newFreq


class CommunicationAnalyzerScope(Instrument):
    def autoAdjust(self, chans):
        return self.driver.autoAdjust(chans)

    def acquire(self, chans=None, avgCnt=None, duration=None, position=None, nPts=None):
        return self.driver.acquire(chans,avgCnt,duration,position,nPts)

    def wfmDb(self, chan, nWfms, untriggered=False):
        return self.driver.wfmDb(chan, nWfms, untriggered)

    def run(self):
        return self.driver.run()

    @classmethod
    def generateDefaults(cls, isDPO, overwrite=False):
        return self.driver.generateDefaults(isDPO,overwrite)



class CurrentSource(Instrument):
    essentialMethods = ['setChannelTuning', 'getChannelTuning', 'off']
    # Must init with `useChans` somehow


from lightlab.equipment.abstract_instruments import ElectricalSource, MultiModalSource
class NICurrentSource(CurrentSource, ElectricalSource, MultiModalSource):
    def __init__(self, *args, useChans, **kwargs):
        super().__init__(*args, useChans=useChans, **kwargs)


class DigitalPhosphorScope(Instrument):
    def autoAdjust(self, chans):
        return self.driver.autoAdjust(chans)

    def acquire(self, chans=None, avgCnt=None, duration=None, position=None, nPts=None):
        return self.driver.acquire(chans,avgCnt,duration,position,nPts)

    def wfmDb(self, chan, nWfms, untriggered=False):
        return self.driver.wfmDb(chan, nWfms, untriggered)

    def run(self):
        return self.driver.run()

    @classmethod
    def generateDefaults(cls, isDPO, overwrite=False):
        return self.driver.generateDefaults(isDPO,overwrite)


class FunctionGenerator(Instrument):
    def instrID(self):
        return self.driver.instrID()

    def frequency(self, newFreq=None):
        return self.driver.frequency(newFreq)

    def waveform(self, newWave=None):
        return self.driver.waveform(newWave)

    def amplAndOffs(self, amplOffs=None):
        return self.driver.amplAndOffs(amplOffs)

    def duty(self, duty=None):
        return self.driver.duty(duty)


class LaserSource(Instrument):
    essentialMethods = ['setChannelEnable',
        'setChannelWls',
        'setChannelPowers',
        'getAsSpectrum',
        'off']


class OpticalSpectrumAnalyzer(Instrument):
    essentialMethods = ['wlRange', 'spectrum']


class Oscilloscope(Instrument):
    essentialMethods = ['acquire', 'wfmDb', 'run']


class PulsePatternGenerator(Instrument):
    def setPrbs(self, length):
        return self.driver.setPrbs(length)

    def setPattern(self, bitArray):
        return self.driver.setPattern(bitArray)

    def getPattern(self):
        return self.driver.getPattern()

    def on(self, turnOn=True):
        return self.driver.on(turnOn)

    def syncSource(self, src=None):
        return self.driver.syncSource(src)

    def amplAndOffs(self, amplOffs=None):
        return self.driver.amplAndOffs(amplOffs)


class RFSpectrumAnalyzer(Instrument):
    def getMeasurements(self):
        return self.driver.getMeasurements()

    def setMeasurement(self, measType='SPEC', append=False):
        return self.driver.setMeasurement(measType,append)

    def run(self, doRun=True):
        return self.driver.run(doRun)

    def sgramInit(self, freqReso=None, freqRange=None):
        return self.driver.sgramInit(freqReso,freqRange)

    def sgramTransfer(self, duration=1., nLines=100):
        return self.driver.sgramTransfer(duration,nLines)

    def spectrum(self, freqReso=None, freqRange=None, typAvg='none', nAvg=None):
        return self.driver.spectrum(freqReso,freqRange,typAvg,nAvg)


class VariableAttenuator(Instrument):
    essentialMethods = ['on', 'off', 'attenDB', 'attenLin']


class NetworkAnalyzer(Instrument):
    def amplitude(self, amp=None):
        return self.driver.amplitude(amp)

    def frequency(self, freq=None):
        return self.driver.frequency(freq)

    def enable(self, enaState=None):
        return self.driver.enable(enaState)

    def run(self):
        return self.driver.run()

    def sweepSetup(self, startFreq, stopFreq, nPts=None, dwell=None, ifBandwidth=None):
        return self.driver.sweepSetup(startFreq,stopFreq,nPts,dwell,ifBandwidth)

    def sweepEnable(self, swpState=None):
        return self.driver.sweepEnable(swpState)

    def triggerSetup(self, useAux=None, handshake=None, isSlave=False):
        return self.driver.triggerSetup(useAux,handshake,isSlave)

    def getSwpDuration(self, forceHardware=False):
        return self.driver.getSwpDuration(forceHardware)

    def measurementSetup(self, measType='S21', chanNum=None):
        return self.driver.measurementSetup(measType,chanNum)

    def spectrum(self):
        return self.driver.spectrum()

    def multiSpectra(self, nSpect=1, livePlot=False):
        return self.driver.multiSpectra(nSpect,livePlot)


class ArduinoInstrument(Instrument):
    def write(self, writeStr):
        return self.driver.write(writeStr)

    def query(self):
        return self.driver.query()


class TempSourceMeter(Instrument):
    def setCurrent(self, currDict):
        return self.driver.setCurrent(currDict)

    def measVoltage(self, subset=None):
        return self.driver.measVoltage(subset)
