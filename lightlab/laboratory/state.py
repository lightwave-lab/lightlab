'''
This module contains classes responsible to maintain a record of the
current state of the lab.

Users typically just have to import the variable :data:`~lightlab.laboratory.state.lab`.

Warning:
    **Developers**: do not import :data:`lab` anywhere inside the
    `lightlab` package. This will cause the deserialization of the
    JSON file before the definition of the classes of the objects
    serialized. If you want to make use of the variable lab, import
    it like this:

    .. code-block:: python

        import lightlab.laboratory.state as labstate

        # developer code
        device = function_that_returns_device()
        bench = labstate.lab.findBenchFromInstrument(device)

'''
from lightlab.laboratory import Hashable, TypedList
from lightlab.laboratory.instruments import Host, LocalHost, Bench, Instrument, Device
import hashlib
import jsonpickle
import sys
from lightlab import logger, config
import getpass
from datetime import datetime
from json import JSONDecodeError
from pathlib import Path
import shutil
import os


def timestamp_string():
    """ Returns timestamp in iso format (e.g. 2018-03-25T18:30:55.328389)"""
    return str(datetime.now().isoformat())


json = jsonpickle.json
# _filename = Path("/home/jupyter/labstate.json")
_filename = os.path.expanduser(config.get_config_param(
    'labstate.filepath'))  # resolve '~' to home folder


try:
    _filename = Path(_filename).resolve()  # resolve symlinks if any
    can_write = True
    if not os.path.isfile(_filename):
        # file does not exist

        # try to make directory
        os.makedirs(_filename.parent, exist_ok=True)

        # check if directory is writable
        can_write = os.access(_filename.parent, os.W_OK)

    else:
        # file exists
        # can open? if not, error!
        with open(_filename, 'r'):
            pass
        # can write? warning
        can_write = os.access(_filename, os.W_OK)
    if can_write:
        _filename.touch()  # this empty file will trigger a warning the first time labstate is loaded
    else:
        logger.warning("Write permission to existing %s denied. "
                       "You will not be able to use lab.saveState().", _filename)
except OSError as error:
    if isinstance(error, FileNotFoundError):
        logger.warning("%s was not found.", _filename)
    if isinstance(error, PermissionError):
        logger.warning("You don't have permission to read/access %s.", _filename)
    new_filename = 'labstate-local.json'
    logger.warning(f"{_filename} not available. Fallback to local {new_filename}.")
    _filename = Path(new_filename)


def hash_sha256(string):
    ''' Returns the hash of string encoded via the SHA-256 algorithm from hashlib'''
    return hashlib.sha256(string.encode()).hexdigest()


class LabState(Hashable):
    """ Represents the set of objects and connections present in lab,
    with the ability to safely save and load to and from a ``.json`` file.
    """
    __version__ = 2
    __sha256__ = None
    __user__ = None
    __datetime__ = None
    __filename__ = None
    #: list(:class:`~lightlab.laboratory.instruments.bases.Host`) list of hosts
    hosts = None
    #: list(:class:`~lightlab.laboratory.instruments.bases.Bench`) list of benches
    benches = None
    #: list(dict(str -> str)) list of connections
    connections = None
    #: list(:class:`~lightlab.laboratory.instruments.bases.Device`) list of devices
    devices = None
    #: list(:class:`~lightlab.laboratory.instruments.bases.Instrument`) list of instruments
    instruments = None

    @property
    def instruments_dict(self):  # TODO DEPRECATE
        """ Dictionary of instruments, concatenated from ``lab.instruments``.
        """
        return self.instruments.dict

    def __init__(self, filename=None):
        self.hosts = TypedList(Host)
        self.benches = TypedList(Bench)
        self.connections = list()
        self.devices = TypedList(Device)
        self.instruments = TypedList(Instrument)
        if filename is None:
            filename = _filename
        self.filename = filename
        super().__init__()

    def updateHost(self, *hosts):
        """ Updates hosts in the hosts list.

        Checks the number of instrumentation_servers.
        There should be exactly one.

        Args:
            *(Host): hosts

        Raises:
            RuntimeError: Raised if duplicate names are found.
            TypeError: Raised if host is not of type :class:`~lightlab.laboratory.instruments.bases.Host`


        """
        localhost_name = None
        old_hostnames = []
        for old_host in self.hosts.values():
            old_hostnames.append(old_host.name)
            if isinstance(old_host, LocalHost):
                if localhost_name is not None:
                    logger.warning('Duplicate localhost found in lab.hosts')
                localhost_name = old_host.name
        for new_host in hosts:
            # Updating localhost
            if (isinstance(new_host, LocalHost) and localhost_name is not None):
                # Check for localhost clash
                if new_host.name != localhost_name:
                    logger.warning('Localhost is already present: ' +
                                   f'{localhost_name}\n' +
                                   f'Not updating host {new_host.name}!')
                    continue
                else:
                    localhost_name = new_host.name
            # Will an update happen?
            if new_host.name in old_hostnames:
                logger.info(f'Overwriting host: {new_host.name}')
                # Will it end up removing the localhost?
                if (new_host.name == localhost_name and
                        not isinstance(new_host, LocalHost)):
                    localhost_name = None
            self.hosts[new_host.name] = new_host
        if localhost_name is None:
            logger.warning('Localhost not yet present')

    def updateBench(self, *benches):
        """ Updates benches in the benches list.

        Args:
            *(Bench): benches

        Raises:
            RuntimeError: Raised if duplicate names are found.
            TypeError: Raised if bench is not of type :class:`~lightlab.laboratory.instruments.bases.Bench`


        """
        for bench in benches:
            self.benches[bench.name] = bench

    def deleteInstrumentFromName(self, name):
        """ Deletes an instrument by their name.

        Example:

        .. code-block:: python

            lab.deleteInstrumentFromName("Keithley2")

        Args:
            name (str): Instrument name

        """
        matching_instruments = list(filter(lambda x: x.name == name,
                                           self.instruments))
        assert len(matching_instruments) == 1
        del self.instruments[name]

    def insertInstrument(self, instrument):
        """ Inserts instrument in labstate.

        Args:
            instrument (Instrument): instrument
                to insert.
        Raises:
            RuntimeError: Raised if duplicate names are found.
            TypeError: Raised if instrument is not of type :class:`~lightlab.laboratory.instruments.bases.Instrument`

        """
        self.instruments.append(instrument)
        if instrument.bench and instrument.bench not in self.benches:
            logger.warning(f"Insterting *new* bench {instrument.bench.name}")
            self.benches.append(instrument.bench)
        if instrument.host and instrument.host not in self.hosts:
            logger.warning(f"Inserting *new* host {instrument.host.name}")
            self.hosts.append(instrument.host)

    def insertDevice(self, device):
        """ Inserts device in labstate.

        Args:
            device (Device): device to insert.

        Raises:
            RuntimeError: Raised if duplicate names are found.
            TypeError: Raised if device is not of type :class:`~lightlab.laboratory.instruments.bases.Device`

        """
        self.devices.append(device)
        if device.bench and device.bench not in self.benches:
            logger.warning(f"Insterting *new* bench {device.bench.name}")
            self.benches.append(device.bench)

    def updateConnections(self, *connections):
        """ Updates connections between instruments and devices.

        A connection is a tuple with a pair of one-entry dictionaries, as such:

        .. code-block:: python

            conn = ({instr1: port1}, {instr2: port2})

        The code assumes that there can only be one connection per port.
        This method performs the following action:

            1. verifies that `port` is one of `instr.ports`. Otherwise raises
                a ``RuntimeError``.
            2. deletes any connection in ``lab.connections`` that has
                either ``{instr1: port1}`` or ``{instr1: port1}``, and
                logs the deleted connection as a warning.
            3. adds new connection

        Args:
            connections (tuple(dict)): connection to update
        """

        # Verify if ports are valid, otherwise do nothing.
        for connection in connections:
            for k1, v1 in connection.items():
                if v1 not in k1.ports:
                    logger.error("Port '%s' is not in '%s: %s'", v1, k1, k1.ports)
                    raise RuntimeError("Port '{}' is not in '{}: {}'".format(v1, k1, k1.ports))

        # Remove old conflicting connections
        def check_if_port_is_not_connected(connection, k1, v1):
            for k2, v2 in connection.items():
                if (k1, v1) == (k2, v2):
                    logger.warning("Deleting existing connection %s.", connection)
                    return False
            return True
        for connection in connections:
            for k1, v1 in connection.items():
                connectioncheck2 = lambda connection: check_if_port_is_not_connected(
                    connection, k1, v1)
                self.connections[:] = [x for x in self.connections if connectioncheck2(x)]

        # Add new connections
        for connection in connections:
            if connection not in self.connections:
                self.connections.append(connection)
            else:
                logger.warning("Connection already exists: %s", connection)
        return True

    @property
    def devices_dict(self):
        """ Dictionary of devices, concatenated from ``lab.devices``.

            Access with ``devices_dict[device.name]``

            Todo:

                Logs a warning if duplicate is found.
        """
        return self.devices.dict

    # TODO Deprecate
    def findBenchFromInstrument(self, instrument):
        """ Returns the bench that contains the instrument.

        This obviously assumes that one instrument can only be present
        in one bench.
        """
        return instrument.bench

    def findBenchFromDevice(self, device):
        """ Returns the bench that contains the device.

        This obviously assumes that one device can only be present
        in one bench.
        """
        return device.bench

    def findHostFromInstrument(self, instrument):
        """ Returns the host that contains the instrument.

        This obviously assumes that one instrument can only be present
        in one host.
        """
        return instrument.host

    @classmethod
    def loadState(cls, filename=None, validateHash=True):
        """ Loads a :class:`LabState` object from a file.

        It loads and instantiates a copy of every object serialized
        with ``lab.saveState(filename)``. The objects are saved with
        :mod:`jsonpickle`, and must be hashable and contain no
        C-object references. For convenience, lab objects are inherited
        from `:class:`lightlab.laboratory.Hashable`.

        By default, the sha256 hash is verified at import time to prevent
        instantiating objects from a corrupted file.

        A file version is also compared to the code version. If a new
        version of this class is present, but your ``json`` file is older,
        a ``RuntimeWarning`` is issued.

        Todo:
            When importing older ``json`` files, know what to do to
            upgrade it without bugs.

        Args:
            filename (str or Path): file to load from.
            validateHash (bool): whether to check the hash, default True.

        Raises:
            RuntimeWarning: if file version is older than lightlab.
            RuntimeError: if file version is newer than lightlab.
            JSONDecodeError: if there is any problem decoding the .json file.
            JSONDecodeError: if the hash file inside the .json file does not
                match the computed hash during import.
            OSError: if there is any problem loading the file.

        """
        if filename is None:
            filename = _filename

        with open(filename, 'r') as file:
            frozen_json = file.read()
        json_state = json.decode(frozen_json)

        user = json_state.pop("__user__")
        datetime_json = json_state.pop("__datetime__")

        # Check integrity of stored version
        sha256 = json_state.pop("__sha256__")
        jsonpickle.set_encoder_options('json', sort_keys=True, indent=4)
        if validateHash and sha256 != hash_sha256(json.encode(json_state)):
            raise JSONDecodeError("Labstate is corrupted. expected: {} vs actual: {}.".format(
                sha256, hash_sha256(json.encode(json_state))), str(filename), 0)

        # Compare versions of file vs. class
        version = json_state.pop("__version__")
        if version < cls.__version__:
            logger.warning("Loading older version of Labstate.")
        elif version > cls.__version__:
            raise RuntimeError(
                "Stored Labstate version is newer than current software. Update package lightlab.")

        context = jsonpickle.unpickler.Unpickler(backend=json, safe=True, keys=True)

        restored_object = context.restore(json_state, reset=True)
        restored_object.__sha256__ = sha256
        restored_object.__version__ = version
        restored_object.filename = filename
        restored_object.__user__ = user
        restored_object.__datetime__ = datetime_json

        try:
            for i in range(version, cls.__version__):
                logger.warning(f"Attempting patch {i} -> {cls.__version__}")
                restored_object = patch_labstate(i, restored_object)
        except NotImplementedError as e:
            logger.exception(e)

        return restored_object

    def __toJSON(self):
        """Returns unencoded JSON dict"""
        context = jsonpickle.pickler.Pickler(unpicklable=True, warn=True, keys=True)
        json_state = context.flatten(self, reset=True)

        jsonpickle.set_encoder_options('json', sort_keys=True, indent=4)

        # Add version and hash of dictionary json_state
        json_state["__version__"] = self.__version__
        json_state["__sha256__"] = hash_sha256(json.encode(json_state))

        # Add user and datetime information afterwards
        json_state["__user__"] = getpass.getuser()
        dt = datetime.now()
        json_state["__datetime__"] = dt.strftime("%A, %d. %B %Y %I:%M%p")

        return json_state

    def _toJSON(self):
        """Returns encoded JSON dict"""

        return json.encode(self.__toJSON())

    # filename need not be serialized
    @property
    def filename(self):
        """ Filename used to serialize labstate."""
        if self.__filename__ is None:
            return _filename
        else:
            return self.__filename__

    @filename.setter
    def filename(self, fname):
        self.__filename__ = fname

    def saveState(self, fname=None, save_backup=True):
        """ Saves the current lab, together with all its dependencies,
        to a JSON file.

        But first, it checks whether the file has the same hash as the
        previously loaded one. If file is not found, skip this check.

        If the labstate was created from scratch, save with ``_saveState()``.

        Args:
            fname (str or Path): file path to save
            save_backup (bool): saves a backup just in case, defaults to True.

        Raises:
            OSError: if there is any problem saving the file.
        """
        if fname is None:
            fname = self.filename
        try:
            loaded_lab = LabState.loadState(fname)
        except FileNotFoundError:
            logger.debug(f"File not found: {fname}. Saving for the first time.")
            self._saveState(fname, save_backup=False)
            return
        except JSONDecodeError:
            if os.stat(fname).st_size == 0:
                logger.warning("%s is empty. Saving for the first time.", _filename)
                self._saveState(fname, save_backup=False)
                return
            else:
                raise

        if not self.__sha256__:
            logger.debug("Attempting to compare fabricated labstate vs. preloaded one.")
            self.__sha256__ = self.__toJSON()["__sha256__"]
            logger.debug("self.__sha256__: %s", self.__sha256__)

        if loaded_lab == self:
            logger.debug("Detected no changes in labstate. Nothing to do.")
            return

        if loaded_lab.__sha256__ == self.__sha256__:
            self._saveState(fname, save_backup)
        else:
            logger.error(
                "%s's hash does not match with the one loaded in memory. Aborting save.", fname)

    def _saveState(self, fname=None, save_backup=True):
        """ Saves the file without checking hash """
        if fname is None:
            fname = self.filename
        filepath = Path(fname).resolve()

        # it is good to backup this file in caseit exists
        if save_backup:
            if filepath.exists():  # pylint: disable=no-member
                # gets folder/filename.* and transforms into folder/filename_{timestamp}.json
                filepath_backup = Path(filepath).with_name(
                    "{}_{}.json".format(filepath.stem, timestamp_string()))
                logger.debug(f"Backup {filepath} to {filepath_backup}")
                shutil.copy2(filepath, filepath_backup)

        # save to filepath, overwriting
        filepath.touch()  # pylint: disable=no-member
        with open(filepath, 'w') as file:
            json_state = self.__toJSON()
            file.write(json.encode(json_state))
            self.__sha256__ = json_state["__sha256__"]
            logger.debug("%s's sha: %s", fname, json_state["__sha256__"])


def init_module(module):
    # do something that imports this module again
    empty_lab = False
    try:
        module.lab = module.LabState.loadState(_filename)
    except (OSError) as e:
        logger.error("%s: %s.", e.__class__.__name__, e)
        empty_lab = True
    except JSONDecodeError as e:
        if os.stat(_filename).st_size == 0:
            logger.warning("%s is empty.", _filename)
        else:
            logger.error("%s: %s is corrupted. %s.", e.__class__.__name__, _filename, e)
        empty_lab = True

    if empty_lab:
        logger.warning("Starting fresh new LabState(). "
                       "Save for the first time with lab._saveState()")
        module.lab = module.LabState()


# Lazy loading tip from https://stackoverflow.com/questions/1462986/lazy-module-variables-can-it-be-done
# The problem is that instantiating the variable lab causes some modules
# that depend on this module to be imported, creating a cyclical dependence.
# The solution is to instantiate the variable lab only when it is truly called.

class _Sneaky(object):
    """ Lazy loading of state.lab. """

    def __init__(self, name):
        self.module = sys.modules[name]
        sys.modules[name] = self
        self.initializing = True

    def __getattribute__(self, name):
        if name in ["initializing", "module"]:
            return super().__getattribute__(name)

        # call module.__init__ only after import introspection is done
        # e.g. if we need module.lab
        if self.initializing and name == "lab":
            self.initializing = False
            self.module.init_module(self.module)
        return getattr(self.module, name)

    def __setattr__(self, name, value):
        if name in ["initializing", "module"]:
            return super().__setattr__(name, value)
        return setattr(self.module, name, value)


_Sneaky(__name__)
lab = None  # This actually helps with the linting and debugging. No side effect.


def patch_labstate(from_version, old_lab):
    """ This takes the loaded JSON version of labstate (old_lab) and
    applies a patch to the current version of labstate. """
    if from_version == 1:
        assert old_lab.__version__ == from_version

        # In labstate version 1, instruments are stored in lists called
        # in lab.benches[x].instruments and/or lab.hosts[x].instruments,
        # with potential name duplicates

        # We need to transport them into a single list that will reside
        # lab.instruments, with no name duplicates.

        old_benches = old_lab.benches
        old_hosts = old_lab.hosts
        old_connections = old_lab.connections
        instruments = TypedList(Instrument)
        benches = TypedList(Bench)
        devices = TypedList(Device)
        hosts = TypedList(Host)

        for old_bench in old_benches.values():
            # restarting new bench afresh (only name matters so far)
            new_bench = Bench(name=old_bench.name)
            benches.append(new_bench)

            # bench.instruments is now a property descriptor,
            # can't access directly. Need to use __dict__
            # here we move bench.instruments into a global instruments

            for instrument in old_bench.__dict__['instruments']:
                instrument.bench = new_bench
                # if there is a duplicate name, update instrument
                if instrument.name in instruments.dict.keys():
                    instruments[instrument.name].__dict__.update(instrument.__dict__)
                else:
                    instruments.append(instrument)

            # same for devices
            for device in old_bench.__dict__['devices']:
                device.bench = new_bench
                if device.name in devices.dict.keys():
                    devices[device.name].__dict__.update(device.__dict__)
                else:
                    devices.append(device)

        # Same code as above
        for old_host in old_hosts.values():
            new_host = Host(name=old_host.name,
                            mac_address=old_host.mac_address,
                            hostname=old_host.hostname,
                            os=old_host.os)
            hosts.append(new_host)
            for instrument in old_host.__dict__['instruments']:
                instrument.host = new_host
                if instrument.name in instruments.dict.keys():
                    instruments[instrument.name].__dict__.update(instrument.__dict__)
                else:
                    instruments.append(instrument)

        # instantiating new labstate from scratch.
        patched_lab = LabState()
        patched_lab.instruments.extend(instruments)
        patched_lab.benches.extend(benches)
        patched_lab.devices.extend(devices)
        patched_lab.hosts.extend(hosts)
        patched_lab.hosts['cassander'] = LocalHost(name='cassander')
        patched_lab.connections = old_connections

        patched_lab.__sha256__ = old_lab.__sha256__
        patched_lab.__version__ = LabState.__version__
        patched_lab.filename = old_lab.filename
        patched_lab.__user__ = old_lab.__user__
        patched_lab.__datetime__ = old_lab.__datetime__
        return patched_lab

    raise NotImplementedError("Patch not found")
