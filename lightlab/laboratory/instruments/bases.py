''' This module provides an interface for instruments, hosts and benches in the lab.
'''

import os
import platform
from uuid import getnode as get_mac  # https://stackoverflow.com/questions/159137/getting-mac-address
from contextlib import contextmanager

from lightlab.laboratory import Node, typed_property, TypedList
from lightlab.equipment.visa_bases import VISAObject, DefaultDriver
from lightlab.util.data import mangle

from lightlab import logger
import pyvisa


class Host(Node):
    """ Computer host, from which GPIB/VISA commands are issued.
    """
    name = None
    hostname = None
    mac_address = None
    os = "linux-ubuntu"  # linux-ubuntu, linux-centos, windows, mac etc.

    __cached_list_resources_info = None
    __cached_gpib_instrument_list = None

    def __init__(self, name='Unnamed Host', hostname=None, **kwargs):
        if hostname is None:
            logger.warning("Hostname not set. isLive and list_resources not functional.")

        self.hostname = hostname
        self.name = name
        super().__init__(**kwargs)

    @property
    def instruments(self):
        from lightlab.laboratory.state import lab
        return TypedList(Instrument, *list(filter(lambda x: x.host == self, lab.instruments)), read_only=True)

    def __contains__(self, item):
        instrument_search = item in self.instruments
        if not instrument_search:
            logger.info("%s not found in %s's instruments.", item, self)
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

    def _visa_prefix(self):
        ''' The prefix necessary for connecting to remote visa servers.

        Ex. 'visa://remote-server.university.edu/'

            Returns:
                (str)
        '''
        return 'visa://{}/'.format(self.hostname)

    def gpib_port_to_address(self, port, board=0):
        '''
            Args:
                port (int): The port on the GPIB bus of this host
                board (int): For hosts with multiple GPIB busses

            Returns:
                (str): the address that can be used in an initializer
        '''
        localSerialStr = 'GPIB{}::{}::INSTR'.format(board, port)
        return self._visa_prefix() + localSerialStr

    def list_resources_info(self, use_cached=True):
        """ Executes a query to the NI Visa Resource manager and
        returns a list of instruments connected to it.

        Args:
            use_cached (bool): query only if not cached, default True

        Returns:
            list: list of `pyvisa.highlevel.ResourceInfo` named tuples.

        """
        if self.__cached_list_resources_info is None:
            use_cached = False
        if use_cached:
            return self.__cached_list_resources_info
        else:
            list_query = self._visa_prefix() + "?*::INSTR"
            rm = pyvisa.ResourceManager()
            logger.debug("Caching resource list in %s", self)
            self.__cached_list_resources_info = rm.list_resources_info(
                query=list_query)
            return self.__cached_list_resources_info

    def list_gpib_resources_info(self, use_cached=True):
        """ Like :meth:`list_resources_info`, but only returns gpib
        resources.

        Args:
            use_cached (bool): query only if not cached, default True.

        Returns:
            (list): list of ``pyvisa.highlevel.ResourceInfo`` named tuples.

        """
        return {resource_name: resource
                for resource_name, resource in self.list_resources_info(use_cached=use_cached).items()
                if resource.interface_type == pyvisa.constants.InterfaceType.gpib}

    def get_all_gpib_id(self, use_cached=True):
        """ Queries the host for all connected GPIB instruments, and
        queries their identities with ``instrID()``.

        Warning: This might cause your instrument to lock into remote mode.

        Args:
            use_cached (bool): query only if not cached, default True

        Returns:
            dict: dictionary with gpib addresses as keys and \
                identity strings as values.
        """
        gpib_resources = self.list_gpib_resources_info(use_cached=use_cached)
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
        """ Finds a gpib address using :meth:`get_all_gpib_id`, given
        an identity string.

        Args:
            id_string_search (str): identity string
            use_cached (bool): query only if not cached, default True

        Returns:
            str: address if found.

        Raises:
            NotFoundError: If the instrument is not found.

        """
        gpib_ids = self.get_all_gpib_id(use_cached=use_cached)
        for gpib_address, id_string in gpib_ids.items():
            if id_string_search == id_string:
                logger.info("Found %s in %s.", id_string_search, gpib_address)
                return gpib_address
        logger.warning("%s not found in %s", id_string_search, self)
        raise NotFoundError(
            "{} not found in {}".format(id_string_search, self))

    def addInstrument(self, *instruments):
        r""" Adds an instrument to lab.instruments if it is not already present.

        Args:
            \*instruments (Instrument): instruments

        """
        from lightlab.laboratory.state import lab
        for instrument in instruments:
            if instrument not in lab.instruments:
                lab.instruments.append(instrument)
            instrument.host = self

    def removeInstrument(self, *instruments):
        r""" Disconnects the instrument from the host

        Args:
            \*instruments (Instrument): instruments

        Todo:
            Remove all connections
        """
        for instrument in instruments:
            if type(instrument) is str:
                logger.warning('Cannot remove by name string. Use the object')
            instrument.host = None

    def checkInstrumentsLive(self):
        """ Checks whether all instruments are "live".

        Instrument status is checked with the :meth:`Instrument.isLive` method

        Returns:
            (bool): True if all instruments are live, False otherwise


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


class LocalHost(Host):

    def __init__(self, name=None):
        if name is None:
            name = 'localhost'
        super().__init__(name=name, hostname=platform.node())
        mac = get_mac()
        # converts 90520734586583 to 52:54:00:3A:D6:D7
        self.mac_address = ':'.join(("%012X" % mac)[i:i + 2] for i in range(0, 12, 2))
        self.os = platform.system()

    def _visa_prefix(self):
        ''' How the visa server is specified. If this is a local host,
        then there is no visa:// prefix

            Returns:
                (str)
        '''
        return ''

    def isLive(self):
        return True


class Bench(Node):
    """ Represents an experiment bench for the purpose of facilitating
    its location in lab.
    """
    name = None

    def __init__(self, name, *args, **kwargs):
        self.name = name
        super().__init__(*args, **kwargs)

    def __contains__(self, item):

        if isinstance(item, Instrument):
            instrument_search = item in self.instruments
            if not instrument_search:
                logger.info("%s not found in %s's instruments.", item, self)
            return instrument_search
        elif isinstance(item, Device):
            device_search = item in self.devices
            if not device_search:
                logger.info("%s not found in %s's devices.", item, self)
            return device_search
        else:
            logger.debug("%s is neither an Instrument nor a Device", item)
            return False

    @property
    def instruments(self):
        from lightlab.laboratory.state import lab
        return TypedList(Instrument, *list(filter(lambda x: x.bench == self, lab.instruments)), read_only=True)

    @property
    def devices(self):
        from lightlab.laboratory.state import lab
        return TypedList(Device, *list(filter(lambda x: x.bench == self, lab.devices)))

    def addInstrument(self, *instruments):
        r""" Adds an instrument to lab.instruments if it is not already
        present and connects to the host.

        Args:
            \*instruments (Instrument): instruments

        """
        from lightlab.laboratory.state import lab
        for instrument in instruments:
            if instrument not in lab.instruments:
                lab.instruments.append(instrument)
            instrument.bench = self

    def removeInstrument(self, *instruments):
        r""" Detaches the instrument from the bench.

        Args:
            \*instruments (Instrument): instruments

        Todo:
            Remove all connections
        """
        for instrument in instruments:
            if type(instrument) is str:
                raise TypeError('Cannot remove by name string. Use the object')
            instrument.bench = None

    def addDevice(self, *devices):
        r""" Adds a device to lab.devices if it is not already present
        and places it in the bench.

        Args:
            \*devices (Device): devices

        """
        from lightlab.laboratory.state import lab
        for device in devices:
            if not isinstance(device, Device):
                raise TypeError(f"{device} is not an instance of Device.")
            if device not in lab.devices:
                lab.devices.append(device)
            device.bench = self

    def removeDevice(self, *devices):
        r""" Detaches the device from the bench.

        Args:
            \*devices (Device): devices

        Todo:
            Remove all connections
        """
        # TODO Remove all connections
        for device in devices:
            if type(device) is str:
                raise TypeError('Cannot remove by name string. Use the object')
            device.bench = None

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

        Driver feedthrough
            Methods, properties, and even regular attributes
            that are in :py:data:`essential_attributes` of the class
            will get/set/call through to the driver object.

        Do not instantiate directly
            Calling a **VISAInstrumentDriver** class will return an **Instrument** object

        Short example::

            osa = Apex_AP2440A_OSA(name='foo', address='NULL')
            osa.spectrum()

        Long example
            :ref:`/ipynbs/Others/labSetup.ipynb`

        Detailed testing
            :py:func:`~tests.test_abstractDrivers.test_driver_init`
    """
    _driver_class = None
    __driver_object = None
    #: Complete Visa address of the instrument (e.g. :literal:`visa\://hostname/GPIB0::1::INSTR`)
    address = None

    _id_string = None
    _name = None
    _bench = None
    _host = None
    ports = None  #: list(str) Port names of instruments. To be used with labstate connections.

    essentialMethods = ['startup']  #: list of methods to be fed through the driver
    essentialProperties = []  #: list of properties to be fed through the driver
    optionalAttributes = []  #: list of optional attributes to be fed through the driver

    def __init__(self, name="Unnamed Instrument", id_string=None, address=None, **kwargs):
        self.bench = kwargs.pop("bench", None)
        self.host = kwargs.pop("host", None)
        self.ports = kwargs.pop("ports", dict())

        self.__driver_object = kwargs.pop("driver_object", None)
        if self.__driver_object is not None:
            self._driver_class = type(self.__driver_object)
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
        errorText = f"'{str(self)}' has no attribute '{attrName}'"
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

        # This was put here to match normal behavior while trying to
        # set obj.__mangled_variable = 'something'
        try:
            return self.__dict__[mangle(attrName, self.__class__.__name__)]
        except KeyError:
            raise AttributeError(errorText)

    def __setattr__(self, attrName, newVal):
        if attrName in self.essentialProperties \
                + self.essentialMethods \
                + self.implementedOptionals:
            setattr(self.driver, attrName, newVal)
        else:
            if attrName == 'address':  # Reinitialize the driver
                if self.__driver_object is not None:
                    self.__driver_object.close()
                    self.__driver_object.address = newVal
            super().__setattr__(mangle(attrName, self.__class__.__name__), newVal)

    def __delattr__(self, attrName):
        if attrName in self.essentialProperties + self.essentialMethods:  # or methods
            self.driver.__delattr__(attrName)
        else:
            try:
                del self.__dict__[mangle(attrName, self.__class__.__name__)]
            except KeyError:
                super().__delattr__(attrName)

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
        (from :mod:`lightlab.equipment.lab_instruments`)

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
        """ Alias of :meth:`driver_object`."""
        return self.driver_object

    bench = typed_property(Bench, "_bench")
    host = typed_property(Host, "_host")

    @property
    def name(self):
        """ (property) Instrument name (can only set during initialization) """
        return self._name

    @property
    def id_string(self):
        """
            The id_string should match the value returned by
            ``self.driver.instrID()``, and is checked by the command
            ``self.isLive()`` in order to authenticate that the intrument
            in that address is the intended one.
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
        lines.append("id_string: {}".format(self.id_string))
        if not self.id_string:
            lines.append("The id_string should match the value returned by"
                         " self.driver.instrID(), and is checked by the command"
                         " self.isLive() in order to authenticate that the intrument"
                         " in that address is the intended one.")
        lines.append("driver_class: {}".format(self.driver_class.__name__))
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
        """ Attempts VISA connection to instrument, and checks whether
            :meth:`~lightlab.equipment.visa_bases.visa_object.instrID`
            matches :data:`id_string`.

            Produces a warning if it is live but the id_string is wrong.

            Returns:
                (bool): True if "live", False otherwise.
        """
        try:
            driver = self.driver_object
            query_id = driver.instrID()
            logger.info("Found %s in %s.", self.name, self.address)
            if self.id_string is not None:
                if self.id_string == query_id:
                    logger.info("id_string of %s is accurate", self.name)
                    return True
                else:
                    logger.warning("%s: %s, expected %s", self.address,
                                   query_id, self.id_string)
                    return False
            else:
                logger.debug("Cannot authenticate %s in %s.",
                             self.name, self.address)
                return True
        except pyvisa.VisaIOError as err:
            logger.warning(err)
            return False

    def connectHost(self, new_host):
        """ Sets/changes instrument's host.

            Equivalent to ``self.host = new_host``
        """
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


class Device(Node):
    """ Represents a device in lab.
        Only useful for documenting the experiment.

        Todo:
            Add equality function
    """

    name = None  #: device name
    ports = None  #: list(str) port names
    _bench = None

    def __init__(self, name, **kwargs):
        self.name = name
        self.ports = kwargs.pop("ports", list())
        self.bench = kwargs.pop("bench", None)
        super().__init__(**kwargs)

    bench = typed_property(Bench, '_bench')

    def __str__(self):
        return "Device {}".format(self.name)

    def display(self):
        """ Displays the device's info table in a nice format."""
        lines = ["{}".format(self)]
        lines.append("Bench: {}".format(self.bench))
        lines.append("=====")
        lines.append("Ports")
        lines.append("=====")
        if len(self.ports) > 0:
            lines.extend(["   {}".format(str(port)) for port in self.ports])
        else:
            lines.append("   No ports.")
        lines.append("***")
        print("\n".join(lines))
