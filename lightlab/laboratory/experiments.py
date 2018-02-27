'''
This module contains tokens for experiments that use devices and instruments.
This is useful to keep track of what is connected to what.
'''
import numpy as np
from lightlab import logger
import lightlab.laboratory.state as labstate
from contextlib import contextmanager
from lightlab.util.data import Spectrum, argFlatten, Waveform


virtualOnly = False


class DualFunction(object):
    """ This class implements a descriptor for a function whose behavior depends
        on an instance's variable. This was inspired by core python's property
        descriptor.

        Example usage:

        .. code-block:: python

            @DualFunction
            def measure(self, *args, **kwargs):
                # use a model to simulate outputs based on args and kwargs and self.
                return simulated_output

            @measure.hardware
            def measure(self, *args, **kwargs):
                # collect data from hardware using args and kwargs and self.
                return output


        The "virtual" function will be called if ``self.virtual`` equals True,
        otherwise the hardware decorated function will be called instead.

    """

    def __init__(self, virtual_function=None, hardware_function=None, doc=None):
        self.virtual_function = virtual_function
        self.hardware_function = hardware_function
        if doc is None and virtual_function is not None:
            doc = virtual_function.__doc__
        self.__doc__ = doc

    def __get__(self, experiment_obj, obj_type=None):
        if experiment_obj is None:
            return self

        def wrapper(*args, **kwargs):
            if experiment_obj.virtual:
                return self.virtual_function(experiment_obj, *args, **kwargs)
            else:
                return self.hardware_function(experiment_obj, *args, **kwargs)
        return wrapper

    def hardware(self, func):
        self.hardware_function = func
        return self

    def virtual(self, func):
        self.virtual_function = func
        return self


class DualMethod(object):
    ''' This differs from DualFunction because it exists outside
        of the object instance. Instead it takes the object when initializing.

        It uses __call__ instead of __get__ because it is its own object
    '''
    def __init__(self, dualInstrument=None, virtual_function=None, hardware_function=None, doc=None):
        self.dualInstrument = dualInstrument
        self.virtual_function = virtual_function
        self.hardware_function = hardware_function
        if doc is None and virtual_function is not None:
            doc = virtual_function.__doc__
        self.__doc__ = doc

    def __call__(self, *args, **kwargs):
        if self.dualInstrument.virtual:
            return self.virtual_function(*args, **kwargs)
        else:
            return self.hardware_function(*args, **kwargs)


class Virtualizable(object):
    def __init__(self, *args, **kwargs):
        try:
            super().__init__(*args, **kwargs)
        except TypeError:
            super().__init__()
        self._virtual = None
        self.synced = list()  # These are put in the same virtual state as this one

    def hardware_warmup(self):
        pass

    def global_hardware_warmup(self):
        try:
            self.instruments
        except AttributeError:
            return
        else:
            for instrument in self.instruments:
                instrument.startup()

    def hardware_cooldown(self):
        pass

    def synchronize(self, *newVirtualizables):
        ''' Adds an experiment that this one will put in the same virtual state as itself.

            Args:
                newExp (Experiment)
        '''
        # if not issubclass(type(newExp), Experiment):
        #     raise TypeError(str(newExp) + ' of type ' + str(type(newExp)) + ' must be an Experiment (sub)class.')
        for virtualObject in argFlatten(*newVirtualizables):
            try:
                virtualObject._virtual
            except AttributeError:
                raise TypeError('virtualObject of type {} is not a Virtualizable subclass'.format(type(virtualObject)))
            self.synced.append(virtualObject)


    @property
    def virtual(self):
        if self._virtual is None:
            raise VirtualizationError("Virtual context unknown. Please refer to method asVirtual().")
        else:
            return self._virtual

    @contextmanager
    def asVirtual(self):
        old_value = self._virtual
        self._virtual = True
        old_subvalues = dict()
        for iSub, sub in enumerate(self.synced):
            old_subvalues[iSub] = sub._virtual
            sub._virtual = True
        try:
            yield self
        finally:
            self._virtual = old_value
            for iSub, sub in enumerate(self.synced):
                sub._virtual = old_subvalues[iSub]

    @contextmanager
    def asReal(self):
        global virtualOnly
        if virtualOnly:
            try:
                yield self
            except VirtualizationError:
                pass
            finally:
                return

        old_value = self._virtual
        self._virtual = False
        old_subvalues = dict()
        for iSub, sub in enumerate(self.synced):
            old_subvalues[iSub] = sub._virtual
            sub._virtual = False
        try:
            self.global_hardware_warmup()
            self.hardware_warmup()
            for sub in self.synced:
                # sub.global_hardware_warmup()
                sub.hardware_warmup()
            yield self
        finally:
            self.hardware_cooldown()
            self._virtual = old_value
            for iSub, sub in enumerate(self.synced):
                sub.hardware_cooldown()
                sub._virtual = old_subvalues[iSub]


class Experiment(Virtualizable):
    """ Experiment class

    Usage:

    .. code-block:: python

        experiment = Experiment()
        with experiment.asVirtual():
            experiment.measure()


        with obj as foo:
            foo.something()

        # this is equivalent to

        foo = obj.__enter__()
        foo.something()
        obj.__exit__()

    """

    instruments = None
    instruments_requirements = None
    devices = None
    validate_exprs = None
    connections = None
    _valid = None
    _lab = None

    @property
    def lab(self):
        if self._lab is None:
            return labstate.lab
        else:
            return self._lab

    @lab.setter
    def lab(self, value):
        if self._lab is None:  # Only set once
            self._lab = value

    def is_valid(self, reset=True):
        if reset:
            self._valid = None
        if self._valid is None:
            self._valid = self.validate()
            # Only print info is it is validated now.
            if self._valid:
                logger.info("{} was just verified and it is live.".format(self))
            else:
                logger.info("{} was just verified and it is offline.".format(self))
        return self._valid

    valid = property(is_valid)

    def __init__(self, instruments=None, devices=None, **kwargs):
        super().__init__(**kwargs)
        if instruments is not None:
            self.instruments = instruments
        else:
            self.instruments = list()
        self.instruments_requirements = list()
        if devices is not None:
            self.devices = devices
        else:
            self.devices = list()
        self.validate_exprs = list()
        self.connections = list()


        self.name = kwargs.pop("name", None)
        self.startup(**kwargs)

    def startup(self):
        raise NotImplementedError()

    def asReal(self):
        if not self.valid:
            raise RuntimeError("Experiment is offline.")
        return super().asReal()

    def registerInstrument(self, instrument, host=None, bench=None):
        if host is None and bench is None:
            raise ValueError("host and bench argument are empty.")

        if host is not None:
            def host_in_lab(host=host):
                expr = host == self.lab.hosts[host.name]
                if not expr:
                    logger.warning("{} not in lab.hosts".format(host))
                return expr

            self.validate_exprs.append(host_in_lab)

        if bench is not None:
            def bench_in_lab(bench=bench):
                expr = bench == self.lab.benches[bench.name]
                if not expr:
                    logger.warning("{} not in lab.benches".format(bench))
                return expr

            self.validate_exprs.append(bench_in_lab)

        def instrument_hooked(instrument=instrument, host=host, bench=bench):
            and_expr = True
            if host is not None:
                expr = (instrument in host)
                if not expr:
                    logger.warning("{} not in {}".format(instrument, host))
                and_expr = and_expr and expr

            if bench is not None:
                expr = (instrument in bench)
                if not expr:
                    logger.warning("{} not in {}".format(instrument, bench))
                and_expr = and_expr and expr
            return and_expr

        self.validate_exprs.append(instrument_hooked)
        self.instruments.append(instrument)
        self.instruments_requirements.append((instrument, host, bench))

    def registerInstruments(self, *instruments, host=None, bench=None):
        for instrument in instruments:
            self.registerInstrument(instrument, host=host, bench=bench)

    def registerConnection(self, connection):
        return self.registerConnections(connection)

    def registerConnections(self, *connections):
        for connection in connections:
            if connection not in self.connections:
                self.connections.append(connection)
            else:
                logger.warning("Connection already exists: %s", connection)

            def connection_present(connection=connection, connections=self.lab.connections):
                if connection in connections:
                    return True
                else:
                    logger.error("Connection {} is not compatible with lab".format(connection))
                    return False
            self.validate_exprs.append(connection_present)

    def validate(self):
        valid = True
        for expr in self.validate_exprs:
            eval_expr = expr()
            valid *= eval_expr
        return valid

    def _enforceConnections(self):
        logger.warning("Updating connections in lab.")
        self.lab.updateConnections(*self.connections)

    def lock(self, key):
        pass

    def unlock(self):
        pass

    def __str__(self):
        try:
            if self.name is not None:
                return "Experiment {}".format(self.name)
        finally:
            return "Experiment {}".format(self.__class__.__name__)

    def display(self):
        lines = ["{}".format(self)]
        if self.valid:
            lines.append("Experiment is online!")
        else:
            lines.append("Experiment is offline.")
        lines.append("===========")
        lines.append("Expected Instruments")
        lines.append("===========")
        if len(self.instruments_requirements) > 0:
            lines.extend(["   {} in ({}, {})".format(str(instrument), str(host), str(bench))
                          for instrument, host, bench
                          in self.instruments_requirements])
        else:
            lines.append("   No instruments.")
        lines.append("=======")
        lines.append("Expected Connections")
        lines.append("=======")
        if len(self.connections) > 0:
            for connection in self.connections:
                connection_items = list(connection.items())
                from_dev, from_port = tuple(connection_items[0])
                to_dev, to_port = tuple(connection_items[1])

                lines.append("   {}/{} <-> {}/{}".format(str(from_dev), str(from_port),
                                                         str(to_dev), str(to_port)))
        else:
            lines.append("   No connections.")
        lines.append("***")
        print("\n".join(lines))


class MasterExperiment(Experiment):
    ''' Does nothing except hold sub experiments to synchronize them

        Required because you cannot startup an Experiment base object
    '''
    def startup(self):
        pass

class VirtualizationError(RuntimeError):
    pass


#### Some common ones
from lightlab.util.io import ChannelError


## Predominantly sources

from lightlab.equipment.abstract_instruments import ElectricalSource, MultiModalSource
from lightlab.equipment.lab_instruments import NI_PCI_SourceCard

class VirtualNICurrentSource(Experiment, ElectricalSource, MultiModalSource):
    ''' Mirrors the CurrentSource class.
        This one actually stores a state inside, in contrast to VirtualMrrsSource

        It only supports NI_PCI_SourceCard for now
    '''
    exceptOnRangeError = False

    def startup(self, useChans=None, hwSrcRef=None):
        '''
            Args:
                useChans (list): if not specified, it has to get it from hwSrcRef
                hwSrcRef (CurrentSource): Hardware driver object, initialized

            Todo:
                Don't wire it explicitly to "setDictTuning"
        '''
        # Figure out channels
        if useChans is None and hwSrcRef is None:
            raise ValueError('Must specify channels somehow in useChans or hwSrcRef')
        if hwSrcRef is not None:
            if useChans is None:
                useChans = list(hwSrcRef.stateDict.keys())
            elif set(useChans) != set(self.stateDict.keys()):
                raise ChannelError('Conflict in channels in useChans and hwSrcRef')
        ElectricalSource.__init__(self, useChans)

        # Type check
        if hwSrcRef is not None:
            for att in ('setChannelTuning', 'getChannelTuning'):
                if not hasattr(hwSrcRef, att):
                    raise AttributeError('{} must provide {}'.format(hwSrcRef, att))
        self.hwSrcRef = hwSrcRef

    def hardware_warmup(self):
        if self.hwSrcRef is None:
            raise VirtualizationError('No hardware reference has been specified')

    @DualFunction
    def setChannelTuning(self, chanValDict, mode):
        '''
        '''
        # Check range and convert to base units
        chanBaseDict = dict()
        for ch, val in chanValDict.items():
            enforced = self.enforceRange(val, mode)
            chanBaseDict[ch] = self.val2baseUnit(enforced, mode)

        # Change the state
        ElectricalSource.setChannelTuning(self, chanBaseDict)

    @setChannelTuning.hardware
    def setChannelTuning(self, chanValDict, mode):
        return self.hwSrcRef.setChannelTuning(chanValDict, mode)

    @DualFunction
    def getChannelTuning(self, mode):
        baseDict = ElectricalSource.getChannelTuning(self)
        return self.baseUnit2val(baseDict, mode)

    @getChannelTuning.hardware
    def getChannelTuning(self, mode):
        return self.hwSrcRef.getChannelTuning(mode)

    def off(self):
        ElectricalSource.off(self, 'volt')


class VirtualMrrsSource(Experiment):
    ''' This only works with an underlying CalModules.Mrrs or Devices.Mrrs class
        that provides a setDictTuning method and a elChans attribute

        To the outside, this presents CurrentSource methods setChannelTuning(val, mode)
    '''
    def startup(self, tunableDevices, hwRef=None):
        '''
            Args:
                tunableDevices (list): things that have a setDictTuning method

            Todo:
                Don't wire it explicitly to "setDictTuning"
        '''
        self.tunableDevices = tunableDevices
        self.hwRef = hwRef
        # Check no repeated channels

        self.allElChans = []
        for d in self.tunableDevices:
            self.allElChans.extend(d.elChans)
        if len(set(self.allElChans)) < len(self.allElChans):
            raise ChannelError('Electrical channel blocked out by multiple devices')

    def hardware_warmup(self):
        if self.hwRef is None:
            raise VirtualizationError('No hardware reference has been specified')
        # Make our internal representation reflect the hardware's
        fullHwState = self.hwRef.stateDict
        # with self.asVirtual():
        #     self.setChannelTuning(fullHwState)

    @DualFunction
    def setChannelTuning(self, currDict, mode='mwperohm'):
        for elChan, elVal in currDict.items():
            if elChan not in self.allElChans:
                raise ChannelError('Channel ' + str(elChan) + ' not blocked out.')
            for d in self.tunableDevices:
                if elChan in d.elChans:
                    d.setDictTuning({elChan: elVal})

    @setChannelTuning.hardware
    def setChannelTuning(self, currDict, mode='mwperohm'):
        # with self.asVirtual():
        #     self.setChannelTuning(currDict)
        self.hwRef.setChannelTuning(currDict, mode)

    @DualFunction
    def off(self):
        for d in self.tunableDevices:
            offDict = dict((ch, 0.) for ch in d.elChans)
            d.setDictTuning(offDict)

    @off.hardware
    def off(self):
        # with self.asVirtual():
        #     self.off()
        self.hwRef.off()




