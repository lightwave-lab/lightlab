'''
This module contains classes responsible to maintain a record of the
current state of the lab.

Users typically just have to import the variable :py:data:`lab`.

Warning:
    **Developers**: do not import :py:data:`lab` anywhere inside the
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
from lightlab.laboratory import Hashable
import hashlib
import jsonpickle
import sys
from lightlab import logger
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
_filename = Path("/home/jupyter/labstate.json")
try:
    with open(_filename, 'r'):
        pass
    if not os.access(_filename, os.W_OK):
        logger.warning("Write permission to %s denied. " \
            "You will not be able to use lab.saveState().", _filename)
except OSError as error:
    if isinstance(error, FileNotFoundError):
        logger.warning("%s was not found.", _filename)
    if isinstance(error, PermissionError):
        logger.warning("You don't have permission to read %s.", _filename)
    new_filename = 'labstate-local.json'
    logger.warning(f"{_filename} not available. Fallback to local {new_filename}.")
    _filename = new_filename


def hash_sha256(string):
    ''' Returns the hash of string encoded via the SHA-256 algorithm from hashlib'''
    return hashlib.sha256(string.encode()).hexdigest()


class LabState(Hashable):
    """ Represents the set of objects and connections present in lab,
    with the ability to safely save and load to and from a ``.json`` file.
    """
    __version__ = 1
    __sha256__ = None
    __user__ = None
    __datetime__ = None
    __filename__ = None
    hosts = None  #: list(:py:class:`~lightlab.laboratory.instruments.bases.Host`) list of hosts
    benches = None  #: list(:py:class:`~lightlab.laboratory.instruments.bases.Bench`) list of benches
    connections = None  #: list(dict(str -> str)) list of connections

    @property
    def instruments(self):
        """ List of :py:class:`~lightlab.laboratory.instruments.bases.Instrument`,
        concatenated from ``benches.instruments`` and ``hosts.instruments``.
        """
        instruments = list()
        for _, bench in self.benches.items():
            instruments.extend(bench.instruments)
        for _, host in self.hosts.items():
            instruments.extend(host.instruments)
        unique_instruments = list(set(instruments))
        return unique_instruments  # unique elements

    @property
    def instruments_dict(self):
        """ Dictionary of instruments, concatenated from ``lab.instruments``.

            Access with ``instruments_dict[instr.name]``

            Todo:

                Logs a warning if duplicate is found.
        """
        instruments_dict = dict()
        for instrument in self.instruments:
            instruments_dict[instrument.name] = instrument
        return instruments_dict

    def __init__(self, filename=_filename):
        self.hosts = dict()
        self.benches = dict()
        self.connections = list()
        self.filename = filename
        super().__init__()

    def updateHost(self, *hosts):
        """ Updates hosts in the hosts dictionary.

        Args:
            *(:py:class:`~lightlab.laboratory.instruments.bases.Host`): hosts

        """
        for host in hosts:
            self.hosts[host.name] = host

    def updateBench(self, *benches):
        """ Updates benches in the benches dictionary.

        Args:
            *(:py:class:`~lightlab.laboratory.instruments.bases.Bench`): benches

        """
        for bench in benches:
            self.benches[bench.name] = bench

    def deleteInstrumentFromName(self, name, force=False):
        """ Deletes an instrument by their name.

        It will only delete if only one element is found.

        Example:

        .. code-block:: python

            lab.deleteInstrumentFromName("Keithley2")

        Args:
            name (str): Instrument name
            force (bool, optional): If True, forces deletion even if
                duplicate names are found. Default False.

        """
        matching_instruments = list(filter(lambda x: x.name == name,
                                           self.instruments))
        delete = False
        if len(matching_instruments) == 1:
            delete = True
        elif len(matching_instruments) > 1:
            if not force:
                logger.error("Found multiple instruments named {}.\n Doing nothing.".format(name))
            else:
                logger.warning("Found multiple instruments named {}.\n Deleting all.".format(name))
                delete = True
        else:
            logger.info("No instrument named {} found".format(name))
        if delete:
            for instr_obj in matching_instruments:
                instr_obj.bench = None
                instr_obj.host = None
                del instr_obj

    def insertInstrument(self, instrument):
        """ Inserts instrument in labstate.

        Args:
            instrument (:py:class:`~lightlab.laboratory.instruments.bases.Instrument`): instrument
                to insert. It must have either `bench` or `host` set.
        Raises:
            RuntimeError: Raised if neither `host` nor `bench` are set.

        Todo:
            test if bench and/or host are in lab
        """
        inserted = False
        if instrument.bench is not None:
            instrument.bench.addInstrument(instrument)
            inserted = True
        if instrument.host is not None:
            instrument.host.addInstrument(instrument)
            inserted = True
        if not inserted:
            raise RuntimeError("host or bench variables must be assigned.")

    def insertDevice(self, device):
        """ Inserts device in labstate.

        Args:
            device (:py:class:`~lightlab.laboratory.devices.Device`): device
                to insert. It must have either `bench` or `host` set.

        Raises:
            RuntimeError: Raised if `bench` is not set.

        Todo:
            test if bench is in lab
        """
        # TODO test if bench is in lab
        if device.bench is not None:
            device.bench.addDevice(device)
        else:
            raise RuntimeError("bench variable must be assigned.")

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
                    logger.error("Port '{}' is not in '{}: {}'".format(v1, k1, k1.ports))
                    raise RuntimeError("Port '{}' is not in '{}: {}'".format(v1, k1, k1.ports))

        # Remove old conflicting connections
        def check_if_port_is_not_connected(connection, k1, v1):
            for k2, v2 in connection.items():
                if (k1, v1) == (k2, v2):
                    logger.warning("Deleting existing connection {}.".format(connection))
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
    def devices(self):
        """ List of :py:class:`~lightlab.laboratory.devices.Device` objects
        present in all benches.
        """
        devices = list()
        for bench in self.benches.values():
            devices.extend(bench.devices)
        return devices

    @property
    def devices_dict(self):
        """ Dictionary of devices, concatenated from ``lab.devices``.

            Access with ``devices_dict[device.name]``

            Todo:

                Logs a warning if duplicate is found.
        """
        return {device.name: device for device in self.devices}

    def findBenchFromInstrument(self, instrument):
        """ Returns the bench that contains the instrument.

        This obviously assumes that one instrument can only be present
        in one bench.
        """
        for benchname, bench in self.benches.items():
            if instrument in bench.instruments:
                return bench
        return None

    def findBenchFromDevice(self, device):
        """ Returns the bench that contains the device.

        This obviously assumes that one device can only be present
        in one bench.
        """
        for benchname, bench in self.benches.items():
            if device in bench.devices:
                return bench
        return None

    def findHostFromInstrument(self, instrument):
        """ Returns the host that contains the instrument.

        This obviously assumes that one instrument can only be present
        in one host.
        """
        for hostname, host in self.hosts.items():
            if instrument in host.instruments:
                return host
        return None

    @classmethod
    def loadState(cls, filename=_filename, validateHash=True):
        """ Loads a :py:class:`LabState` object from a file.

        It loads and instantiates a copy of every object serialized
        with ``lab.saveState(filename)``. The objects are saved with
        :py:mod:`jsonpickle`, and must be hashable and contain no
        C-object references. For convenience, lab objects are inherited
        from `:py:class:`lightlab.laboratory.Hashable`.

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
            RuntimeError: if the hash file inside the .json file does not
                match the computed hash during import.
            OSError: if there is any problem loading the file.

        """
        with open(filename, 'r') as file:
            frozen_json = file.read()
        json_state = json.decode(frozen_json)

        user = json_state.pop("__user__")
        datetime = json_state.pop("__datetime__")

        # Check integrity of stored version
        sha256 = json_state.pop("__sha256__")
        jsonpickle.set_encoder_options('json', sort_keys=True, indent=4)
        if validateHash and sha256 != hash_sha256(json.encode(json_state)):
            raise RuntimeError("Labstate is corrupted. {} vs {}.".format(
                sha256, hash_sha256(json.encode(json_state))))

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
        restored_object.filename = filename
        restored_object.__user__ = user
        restored_object.__datetime__ = datetime
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

        if not self.__sha256__:
            logger.debug("Attempting to compare fabricated labstate vs. preloaded one.")
            self.__sha256__ = self.__toJSON()["__sha256__"]
            logger.debug("self.__sha256__: {}".format(self.__sha256__))

        if loaded_lab == self:
            logger.debug("Detected no changes in labstate. Nothing to do.")
            return

        if loaded_lab.__sha256__ == self.__sha256__:
            self._saveState(fname, save_backup)
        else:
            logger.error(
                "{}'s hash does not match with the one loaded in memory. Aborting save.".format(fname))

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
            logger.debug("{}'s sha: {}".format(fname, json_state["__sha256__"]))

# Lazy loading tip from https://stackoverflow.com/questions/1462986/lazy-module-variables-can-it-be-done
# The problem is that instantiating the variable lab causes some modules
# that depend on this variable to be imported, creating a cyclical dependence.
# The solution is to instantiate the variable lab only when it is truly called.


def __init__(module):
    # do something that imports this module again
    empty_lab = False
    try:
        module.lab = module.LabState.loadState(_filename)
    except (OSError) as e:
        logger.error("%s: %s.", e.__class__.__name__, e)
        empty_lab = True
    except (JSONDecodeError) as e:
        logger.error("%s: %s corrupted. %s.", e.__class__.__name__, _filename, e)
        empty_lab = True

    if empty_lab:
        logger.error("Starting fresh new LabState(). " \
            "Save for the first time with lab._saveState()")
        module.lab = module.LabState()


class _Sneaky(object):

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
            __init__(self.module)
        return getattr(self.module, name)


_Sneaky(__name__)
lab = None  # This actually helps with the linting and debugging. No side effect.
