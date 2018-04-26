'''
This module provides an interface for instruments in the lab and virtual ones.
'''
from lightlab.laboratory import Node
from lightlab.laboratory.devices import Device
import lightlab.laboratory.state as labstate
from lightlab.equipment.visa_bases import VISAObject, DefaultDriver

from lightlab import logger
import os
import pyvisa
from contextlib import contextmanager


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
        self.instruments = instruments
        super().__init__(*args, **kwargs)

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
            except ValueError as err:
                logger.warn("%s not currently connected to %s",
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
            if type(instrument) is str:
                logger.warn('Cannot remove by name string. Use the object')
            try:
                self.instruments.remove(instrument)
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
            lines.extend(["   {} ({})".format(str(instrument), str(instrument.host))
                          for instrument in self.instruments])
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


# TODO add instrument equality function
class Instrument(Node):
    """ Class storing information about instruments, for the purpose of
        facilitating verifying whether it is connected to the correct devices.

        Driver feedthrough: methods, properties, and even regular attributes
        that are in ``essentialMethods`` and ``essentialProperties`` of the class
        will get/set/call through to the driver object.
    """
    _driver_class = None
    __driver_object = None
    address = None

    _id_string = None
    _name = None
    __bench = None
    __host = None
    ports = None

    essentialMethods = ['startup']
    essentialProperties = []
    optionalAttributes = []

    def __init__(self, name="Unnamed Instrument", id_string=None, address=None, **kwargs):
        self.__bench = kwargs.pop("bench", None)
        self.__host = kwargs.pop("host", None)
        self.ports = kwargs.pop("ports", dict())

        self.__driver_object = kwargs.pop("driver_object", None)
        if self.__driver_object is not None:
            self._driver_class = type(self.__driver_object)
        # driver_klass = kwargs.get('_driver_class', None)
        # for attrName in self.essentialMethods + self.essentialProperties:
        #     if attrName in kwargs.keys():
        #         raise AttributeError('Ambiguous attributes between Instrument and its driver: ' + attrName)
        #     if driver_klass is not None:
        #         if not hasattr(driver_klass, attrName):
        #             raise AttributeError('Driver class {} does not implement essential attribute {}'.format(driver_klass.__name__, attrName))
        super().__init__(_name=name,
                         _id_string=id_string,
                         address=address, **kwargs)

    def __dir__(self):
        ''' For autocompletion in ipython '''
        return super().__dir__() + self.essentialProperties \
            + self.essentialMethods + self.implementedOptionals

    @property
    def implementedOptionals(self):
        implementedOptionals = list()
        for opAttr in self.optionalAttributes:
            if hasattr(self._driver_class, opAttr):
                implementedOptionals.append(opAttr)
        return implementedOptionals

    # These control feedthroughs to the driver
    def __getattr__(self, attrName):
        errorText = str(self) + ' has no attribute ' + attrName
        if attrName in self.essentialProperties \
                + self.essentialMethods \
                + self.implementedOptionals:
            return getattr(self.driver, attrName)
        # Time to fail
        if attrName in self.optionalAttributes:
            errorText += '\nThis is an optional attribute of {} '.format(type(self).__name__)
            errorText += 'not implemented by this particular driver'
        elif hasattr(self._driver_class, attrName):
            errorText += '\nIt looks like you are trying to access a low-level attribute'
            errorText += '\nUse ".driver.{}" to get it'.format(attrName)
        raise AttributeError(errorText)

    def __setattr__(self, attrName, newVal):
        if attrName in self.essentialProperties + self.essentialMethods:  # or methods
            return setattr(self.driver, attrName, newVal)
        else:
            return super().__setattr__(attrName, newVal)

    def __delattr__(self, attrName):
        if attrName in self.essentialProperties + self.essentialMethods:  # or methods
            return self.driver.__delattr__(attrName)
        else:
            return super().__delattr__(attrName)

    # These control contextual behavior. They are used by DualInstrument
    def hardware_warmup(self):
        pass

    def hardware_cooldown(self):
        pass

    @contextmanager
    def warmedUp(self):
        ''' A context manager that warms up and cools down in a "with" block
        '''
        try:
            self.hardware_warmup()
            yield self
        finally:
            self.hardware_cooldown()

    # These control properties
    @property
    def driver_class(self):
        if self._driver_class is None:
            logger.warning("Using default driver for %s.", self)
            return DefaultDriver
        else:
            return self._driver_class

    @property
    def driver_object(self):
        if self.__driver_object is None:
            try:
                kwargs = self.driver_kwargs
            except AttributeError:  # Fall back to the jank version where we try to guess what is important
                kwargs = dict()
                for kwarg in ["useChans", "elChans", "dfbChans", "stateDict", "sourceMode"]:
                    try:
                        kwargs[kwarg] = getattr(self, kwarg)
                    except AttributeError:
                        pass
            kwargs['directInit'] = True
            self.__driver_object = self.driver_class(  # pylint: disable=not-callable
                name=self.name, address=self.address, **kwargs)
        return self.__driver_object

    @property
    def driver(self):
        return self.driver_object

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
        lines.append("driver_class: {}".format(self.driver_class))
        lines.append("=====")
        lines.append("Ports")
        lines.append("=====")
        if len(self.ports) > 0:
            lines.extend(["   {}".format(str(port)) for port in self.ports])
        else:
            lines.append("   No ports.")
        if hasattr(self, 'driver_kwargs'):
            lines.append("=====")
            lines.append("Driver kwargs")
            lines.append("=====")
            for k, v in self.driver_kwargs.items():
                lines.append("   {} = {}".format(str(k), str(v)))
        lines.append("***")
        print("\n".join(lines))

    def isLive(self):
        try:
            driver = self.driver_object
            query_id = driver.instrID()
            logger.info("Found %s in %s.", self.name, self.address)
            if self.id_string is not None:
                if self.id_string == query_id:
                    logger.info("id_string of %s is accurate", self.name)
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

    # @classmethod
    # def fromGpibAddress(cls, gpib_address):
    #     visa_object = VISAObject(gpib_address, tempSess=True)
    #     # TODO untreated error when there is no device with that address!
    #     id_string = visa_object.instrID()
    #     return cls(id_string, gpib_address=gpib_address)


class NotFoundError(RuntimeError):
    pass



