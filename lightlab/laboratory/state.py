'''
This module contains classes responsible to maintain a record of the current state of the lab.
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


def timestamp_string():
    return str(datetime.now().isoformat())


json = jsonpickle.json
_filename = Path("/home/jupyter/labstate.json")
try:
    with open(_filename, 'r'):
        pass
except Exception:
    new_filename = 'test_{}.json'.format(timestamp_string())
    logger.warning(f"{_filename} not available. Fallback to local {new_filename}.")
    _filename = new_filename


def hash_sha256(string):
    ''' Returns the hash of string encoded via the SHA-256 algorithm from hashlib'''
    return hashlib.sha256(string.encode()).hexdigest()


class LabState(Hashable):
    __version__ = 0
    __sha256__ = None
    __user__ = None
    __datetime__ = None
    __filename__ = None
    hosts = None
    benches = None
    connections = None

    @property
    def instruments(self):
        instruments = list()
        for benchanme, bench in self.benches.items():
            instruments.extend(bench.instruments)
        for hostname, host in self.hosts.items():
            instruments.extend(host.instruments)

        return instruments

    @property
    def instruments_dict(self):
        instruments_dict = dict()
        for instrument in self.instruments:
            instruments_dict[instrument.name] = instrument
        return instruments_dict

    def __init__(self, filename=_filename):
        super().__init__(hosts=dict(), benches=dict(),
                         connections=list(), filename=filename)

    def updateHost(self, *hosts):
        for host in hosts:
            self.hosts[host.name] = host

    def updateBench(self, *benches):
        for bench in benches:
            self.benches[bench.name] = bench

    def deleteInstrumentFromName(self, name, force=False):
        matching_instruments = list(filter(lambda x: x.name == name,
                                           self.instruments))
        delete = False
        if len(matching_instruments) == 1:
            delete = True
        elif len(matching_instruments) > 1:
            if force:
                logger.error("Found multiple instruments named {}.\n Doing nothing.".format(name))
            else:
                logger.warning("Found multiple instruments named {}.\n Deleting all.".format(name))
                delete = True
        else:
            logger.info("No instrument named {} found".format(name))
        if delete:
            for instr_obj in matching_instruments:
                raise RuntimeError(instr_obj.__bench)
                instr_obj.bench = None
                instr_obj.host = None
                del instr_obj


    def insertInstrument(self, instrument):
        # TODO test if bench and/or host are in lab
        inserted = False
        if instrument.bench is not None:
            instrument.bench.addInstrument(instrument)
            inserted = True
        if instrument.host is not None:
            instrument.host.addInstrument(instrument)
            inserted = True
        if not inserted:
            logger.error("host or bench variables must be assigned.")

    def insertDevice(self, device):
        # TODO test if bench is in lab
        if device.bench is not None:
            device.bench.addDevice(device)
        else:
            logger.error("bench variable must be assigned.")

    def updateConnections(self, *connections):
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
        devices = list()
        for bench in self.benches.values():
            devices.extend(bench.devices)
        return devices

    @property
    def devices_dict(self):
        return {device.name: device for device in self.devices}

    def findBenchFromInstrument(self, instrument):
        for benchname, bench in self.benches.items():
            if instrument in bench.instruments:
                return bench
        return None

    def findBenchFromDevice(self, device):
        for benchname, bench in self.benches.items():
            if device in bench.devices:
                return bench
        return None

    def findHostFromInstrument(self, instrument):
        for hostname, host in self.hosts.items():
            if instrument in host.instruments:
                return host
        return None

    @classmethod
    def loadState(cls, filename=_filename):
        with open(filename, 'r') as file:
            frozen_json = file.read()
        json_state = json.decode(frozen_json)

        user = json_state.pop("__user__")
        datetime = json_state.pop("__datetime__")

        # Check integrity of stored version
        sha256 = json_state.pop("__sha256__")
        jsonpickle.set_encoder_options('json', sort_keys=True, indent=4)
        if sha256 != hash_sha256(json.encode(json_state)):
            raise RuntimeError("Labstate is corrupted. {} vs {}.".format(
                sha256, hash_sha256(json.encode(json_state))))

        # Compare versions of file vs. class
        version = json_state.pop("__version__")
        if version < cls.__version__:
            raise RuntimeWarning("Loading older version of Labstate.")
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
        if self.__filename__ is None:
            return _filename
        else:
            return self.__filename__

    @filename.setter
    def filename(self, fname):
        self.__filename__ = fname

    def saveState(self, fname=None, save_backup=True):
        if fname is None:
            fname = self.filename
        try:
            loaded_lab = LabState.loadState(fname)
        except FileNotFoundError:
            logger.debug(f"File not found: {fname}. Saving for the first time.")
            self._saveState(fname, save_backup)
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
        if fname is None:
            fname = self.filename
        filepath = Path(fname).resolve()

        # it is good to backup this file in caseit exists
        if save_backup:
            if filepath.exists():
                # gets folder/filename.* and transforms into folder/filename_{timestamp}.json
                filepath_backup = Path(filepath).with_name("{}_{}.json".format(filepath.stem, timestamp_string()))
                logger.debug(f"Backup {filepath} to {filepath_backup}")
                shutil.copy2(filepath, filepath_backup)

        # save to filepath, overwriting
        filepath.touch()
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
    try:
        module.lab = module.LabState.loadState()
    except JSONDecodeError as e:
        logger.error("JSONDecodeError: {}".format(e))
        module.lab = module.LabState()


class _Sneaky(object):

    def __init__(self, name):
        self.module = sys.modules[name]
        sys.modules[name] = self
        self.initializing = True

    def __getattr__(self, name):
        # call module.__init__ after import introspection is done
        if self.initializing and not name[:2] == '__' == name[-2:]:
            self.initializing = False
            __init__(self.module)
        return getattr(self.module, name)


_Sneaky(__name__)
lab = None
