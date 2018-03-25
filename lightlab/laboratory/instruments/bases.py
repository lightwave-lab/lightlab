'''
This module provides an interface for instruments, hosts and benches in the lab.
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
    """ Computer host, from which GPIB/VISA commands are issued.
    """
    name = None  #: Print friendly name of the host
    mac_address = None  #: Mac address of the machine (future use: Wake on Lan)
    hostname = None  #: DNS hostname for connection (e.g. ``lab-pc-2.school.edu``)
    os = "linux-ubuntu"  #: OS: linux-ubuntu, linux-centos, windows, mac etc.
    instruments = None  #: list of instruments controlled by host.

    __cached_list_resources_info = None
    __cached_gpib_instrument_list = None

    def __init__(self, name='Unnamed Host', instruments=None, hostname=None, **kwargs):
        if instruments is None:
            instruments = list()
        self.instruments = instruments
        if hostname is None:
            logger.warning("Hostname not set. isLive and list_resources not functional.")

        self.hostname = hostname
        self.instruments = instruments
        self.name = name
        super().__init__(**kwargs)

    def __contains__(self, item):
        instrument_search = item in self.instruments
        if not instrument_search:
            logger.info("{} not found in {}'s instruments.".format(item, self))
        return instrument_search

    def isLive(self):
        ''' Pings the system and returns if it is alive.
        '''
        if self.hostname is not None:
            logger.debug("Pinging %s...", self.hostname)
            response = os.system("ping -c 1 {}".format(self.hostname))
            if response != 0:
                logger.warning("%s is not reachable via ping.", self)
            return response == 0
        else:
            logger.warning("Hostname not set. Unable to ping.")
            return False

    def list_resources_info(self, use_cached=True, is_local=False):
        """ Executes a query to the NI Visa Resource manager and
        returns a list of instruments connected to it.

        Args:
            use_cached (bool): query only if not cached, default True
            is_local (bool): True if querying local instruments, False
                host is remote.

        Returns:
            list: list of `pyvisa.highlevel.ResourceInfo` named tuples.

        """
        if self.__cached_list_resources_info is None:
            use_cached = False
        if use_cached:
            return self.__cached_list_resources_info
        else:
            if self.hostname is not None:
                if is_local:
                    list_query = "?*::INSTR"
                else:
                    list_query = "visa://" + self.hostname + "/?*::INSTR"
                rm = pyvisa.ResourceManager()
                logger.debug("Caching resource list in %s", self)
                self.__cached_list_resources_info = rm.list_resources_info(
                    query=list_query)
            else:
                logger.warning("Hostname not set. Unable to list resources.")
                self.__cached_list_resources_info = list()
            return self.__cached_list_resources_info

    def list_gpib_resources_info(self, use_cached=True, is_local=False):
        """ Like :py:meth:`list_resources_info`, but only returns gpib
        resources.

        Args:
            use_cached (bool): query only if not cached, default True.
            is_local (bool): True if querying local instruments, False
                host is remote, default False.

        Returns:
            list: list of `pyvisa.highlevel.ResourceInfo` named tuples.

        """
        return {resource_name: resource
                for resource_name, resource in self.list_resources_info(use_cached=use_cached, is_local=is_local).items()
                if resource.interface_type == pyvisa.constants.InterfaceType.gpib}

    def get_all_gpib_id(self, use_cached=True, is_local=False):
        """ Queries the host for all connected GPIB instruments, and
        queries their identities with ``instrID()``.

        Warning: This might cause your instrument to lock into remote mode.

        Args:
            use_cached (bool): query only if not cached, default True
            is_local (bool): True if querying local instruments, False
                host is remote.

        Returns:
            dict: dictionary with gpib addresses as keys and \
                identity strings as values.
        """
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

    def findGpibAddressById(self, id_string_search, use_cached=True, is_local=False):
        """ Finds a gpib address using :py:meth:`get_all_gpib_id`, given
        an identity string.

        Args:
            id_string_search (str): identity string
            use_cached (bool): query only if not cached, default True
            is_local (bool): True if querying local instruments, False
                host is remote.

        Returns:
            str: address if found.

        Raises:
            NotFoundError: If the instrument is not found.

        """
        gpib_ids = self.get_all_gpib_id(use_cached=use_cached, is_local=is_local)
        for gpib_address, id_string in gpib_ids.items():
            if id_string_search == id_string:
                logger.info("Found %s in %s.", id_string_search, gpib_address)
                return gpib_address
        logger.warning("{} not found in {}".format(id_string_search, self))
        raise NotFoundError(
            "{} not found in {}".format(id_string_search, self))

    def addInstrument(self, *instruments):
        """ Adds an instrument to self.instruments if it is not already present.

        Args:
            *instruments (:py:class:`Instrument`): instruments

        """
        for instrument in instruments:
            if not isinstance(instrument, Instrument):
                raise TypeError(f"{instrument} is not an instance of Instrument.")
            if instrument not in self.instruments:
                self.instruments.append(instrument)

    def removeInstrument(self, *instruments):
        """ Removes an instrument from self.instruments.
        Warns the user if the instrument is not already present.

        Args:
            *instruments (:py:class:`Instrument`): instruments

        """
        for instrument in instruments:
            if type(instrument) is str:
                raise TypeError('Cannot remove by name string. Use the object')
            try:
                self.instruments.remove(instrument)
            except ValueError as err:
                logger.warn("%s not currently connected to %s",
                            instrument, self)

    def checkInstrumentsLive(self):
        """ Checks whether all instruments are "live".

        Instrument status is checked with the :py:meth:`Instrument.isLive()` method

        Returns:
            bool: True if all instruments are live, False otherwise


        """
        all_live = True
        for instrument in self.instruments:
            if instrument.isLive():
                logger.info("%s is live.", instrument)
            else:
                all_live = False
        return all_live

    def __str__(self):
        return "Host {}".format(self.name)

    def display(self):
        """ Displays the host's instrument table in a nice format."""
        lines = ["{}".format(self)]
        lines.append("===========")
        lines.append("Instruments")
        lines.append("===========")
        if len(self.instruments) > 0:
            lines.extend(["   {} ({})".format(str(instrument), str(instrument.host))
                          for instrument in self.instruments])
        else:
            lines.append("   No instruments.")
        lines.append("***")
        print("\n".join(lines))


class Bench(Node):
    """ Represents an experiment bench for the purpose of facilitating
    its location in lab.
    """
    name = None  #: Print friendly name of the bench. (Not optional)
    devices = None  #: List of devices placed on bench
    instruments = None  #: List of instruments placed on bench

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
        super().__init__(**kwargs)

    def addInstrument(self, *instruments):
        """ Adds an instrument to self.instruments if it is not already present.

        Args:
            *instruments (:py:class:`Instrument`): instruments

        """
        for instrument in instruments:
            if not isinstance(instrument, Instrument):
                raise TypeError(f"{instrument} is not an instance of Instrument.")
            if instrument not in self.instruments:
                self.instruments.append(instrument)

    def removeInstrument(self, *instruments):
        """ Removes an instrument from self.instruments.
        Warns the user if the instrument is not already present.

        Args:
            *instruments (:py:class:`Instrument`): instruments

        Todo:
            Remove all connections
        """
        for instrument in instruments:
            if type(instrument) is str:
                raise TypeError('Cannot remove by name string. Use the object')
            try:
                self.instruments.remove(instrument)
            except ValueError as err:
                logger.warn("%s not currently placed in %s", instrument, self)

    def addDevice(self, *devices):
        """ Adds a device to self.devices if it is not already present.

        Args:
            *(:py:class:`Device`): devices

        """
        for device in devices:
            if not isinstance(device, Device):
                raise TypeError(f"{device} is not an instance of Device.")
            if device not in self.devices:
                self.devices.append(device)

    def removeDevice(self, *devices):
        """ Removes a device from self.devices.
        Warns the user if the device is not already present.

        Args:
            *(:py:class:`Device`): devices

        Todo:
            Remove all connections
        """
        for device in devices:
            if type(device) is str:
                raise TypeError('Cannot remove by name string. Use the object')
            try:
                self.devices.remove(device)
            except ValueError as err:
                logger.warn("%s not currently placed in %s", device, self)

    def display(self):
        """ Displays the bench's table in a nice format."""
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


class Instrument(Node):
    """ Represents an instrument in lab.

        This class stores information about instruments, for the purpose of
        facilitating verifying whether it is connected to the correct devices.

        Driver feedthrough: methods, properties, and even regular attributes
        that are in ``essentialMethods`` and ``essentialProperties`` of the class
        will get/set/call through to the driver object.

        Todo:
            Add example of instrument instantiation and point to relevant ipynb.
    """
    _driver_class = None
    __driver_object = None
    address = None  #: Complete Visa address of the instrument (e.g. :literal:`visa\://hostname/GPIB0::1::INSTR`)

    _id_string = None
    _name = None
    __bench = None
    __host = None
    ports = None  #: list(str) Port names of instruments. To be used with labstate connections.

    essentialMethods = ['startup']  #: list of methods to be fed through the driver
    essentialProperties = []  #: list of properties to be fed through the driver
    optionalAttributes = []  #: list of optional attributes to be fed through the driver

    def __init__(self, name="Unnamed Instrument", id_string=None, address=None, **kwargs):
        self.__bench = kwargs.pop("bench", None)
        self.__host = kwargs.pop("host", None)
        self.ports = kwargs.pop("ports", list())

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
        self._name = name
        self._id_string = id_string
        self.address = address
        super().__init__(**kwargs)

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
        if attrName in self.essentialProperties + self.essentialMethods:
            return getattr(self.driver, attrName)
        elif attrName in self.implementedOptionals:
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
        """ Called before the beginning of an experiment.

        Typical warmup procedures include RESET gpib commands.
        """
        pass

    def hardware_cooldown(self):
        """ Called after the end of an experiment.

        Typical cooldown procedures include laser turn-off, or orderly
        wind-down of current etc.
        """
        pass

    @contextmanager
    def warmedUp(self):
        ''' A context manager that warms up and cools down in a "with" block

        Usage:

        .. code-block:: python

            with instr.warmedUp() as instr:  # warms up instrument
                instr.doStuff()
                raise Exception("Interrupting experiment")
            # cools down instrument, even in the event of exception

        '''
        try:
            self.hardware_warmup()
            yield self
        finally:
            self.hardware_cooldown()

    # These control properties
    @property
    def driver_class(self):
        """ Class of the actual equipment driver
        (from :py:mod:`lightlab.equipment.lab_instruments`)

        This way the object knows how to instantiate a driver instance
        from the labstate.
        """
        if self._driver_class is None:
            logger.warning("Using default driver for %s.", self)
            return DefaultDriver
        else:
            return self._driver_class

    @property
    def driver_object(self):
        """ Instance of the equipment driver."""
        if self.__driver_object is None:
            try:
                kwargs = self.driver_kwargs
            except AttributeError:  # Fall back to the jank version where we try to guess what is important
                kwargs = dict()
                for kwarg in ["useChans", "stateDict", "sourceMode"]:
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
        """ Alias of :py:meth:`driver_object`."""
        return self.driver_object

    @property
    def bench(self):
        """ (property) Bench in which instrument is placed."""
        if self.__bench is None:
            self.__bench = labstate.lab.findBenchFromInstrument(self)
        return self.__bench

    @bench.setter
    def bench(self, new_bench):
        """ Sets the bench in which instrument is placed."""
        if self.bench is not None:
            self.bench.removeInstrument(self)
        if new_bench is not None:
            new_bench.addInstrument(self)
        self.__bench = new_bench

    @property
    def host(self):
        """ (property) Host in which instrument is placed."""
        if self.__host is None:
            self.__host = labstate.lab.findHostFromInstrument(self)
        return self.__host

    @host.setter
    def host(self, new_host):
        """ Sets the host in which instrument is placed."""
        if self.host is not None:
            self.host.removeInstrument(self)
        if new_host is not None:
            new_host.addInstrument(self)
        self.__host = new_host

    @property
    def name(self):
        """ (property) Instrument name (can only set during initialization) """
        return self._name

    @property
    def id_string(self):
        """ (property) Instrument id string matching
        ``self.driver.instrID()`` (can only set during initialization)
        """
        return self._id_string

    def __str__(self):
        return "{}".format(self.name)

    def display(self):
        """ Displays the instrument's info table in a nice format."""
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
        lines.append("***")
        print("\n".join(lines))

    def isLive(self):
        """ Attempts VISA connection to instrument, and checks whether
        ``instrID()`` matches :py:data:`id_string`.

        Returns:
            (bool): True if "live", false otherwise.
        """
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

    def connectHost(self, new_host):
        """ Sets/changes instrument's host.

        Equivalent to ``self.host = new_host``
        """
        # if gpib_address is None:
        #     if self.gpib_address is None:
        #         self.gpib_address = self.findAddressById(host)
        # else:
        #     logger.info("Manually locating %s in %s", self, gpib_address)
        #     self.gpib_address = gpib_address
        self.host = new_host

    def placeBench(self, new_bench):
        """ Sets/changes instrument's bench.

        Equivalent to ``self.bench = new_bench``
        """
        self.bench = new_bench

    # @classmethod
    # def fromGpibAddress(cls, gpib_address):
    #     visa_object = VISAObject(gpib_address, tempSess=True)
    #     # TODO untreated error when there is no device with that address!
    #     id_string = visa_object.instrID()
    #     return cls(id_string, gpib_address=gpib_address)


class NotFoundError(RuntimeError):
    """ Error thrown when instrument is not found
    """
    pass
