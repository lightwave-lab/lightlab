'''
This module contains tokens for experiments that use devices and instruments.
This is useful to keep track of what is connected to what.
'''
from lightlab import logger
import lightlab.laboratory.state as labstate
from lightlab.laboratory.virtualization import Virtualizable
from contextlib import contextmanager


class Experiment(Virtualizable):
    """ Experiment base class.

    This class is intended to be inherited by the user.

    Usage:

    .. code-block:: python

        experiment = Experiment()
        with experiment.asVirtual():
            experiment.measure()  # measure is a DualFunction


        # Quick tutorial on decorators:
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
    name = None

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
                logger.info("%s was just verified and it is live.", self)
            else:
                logger.info("%s was just verified and it is offline.", self)
        return self._valid

    valid = property(is_valid)

    def __init__(self, instruments=None, devices=None, **kwargs):
        super().__init__()
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

    def global_hardware_warmup(self):
        try:
            self.instruments
        except AttributeError:
            return
        else:
            for instrument in self.instruments:
                instrument.startup()

    def hardware_warmup(self):
        pass

    def hardware_cooldown(self):
        pass

    @contextmanager
    def asReal(self):
        ''' Wraps making self.virtual to False.
            Also does hardware warmup and cooldown
        '''
        if not self.valid:
            raise RuntimeError("Experiment is offline.")
        with super().asReal():
            try:
                self.global_hardware_warmup()
                self.hardware_warmup()
                for sub in self.synced:
                    sub.hardware_warmup()
                yield self
            finally:
                self.hardware_cooldown()
                for sub in self.synced:
                    sub.hardware_cooldown()

    def registerInstrument(self, instrument, host=None, bench=None):
        if host is None and bench is None:
            raise ValueError("host and bench argument are empty.")

        if host is not None:
            def host_in_lab(host=host):
                expr = host == self.lab.hosts[host.name]
                if not expr:
                    logger.warning("{} not in lab.hosts %s", host)
                return expr

            self.validate_exprs.append(host_in_lab)

        if bench is not None:
            def bench_in_lab(bench=bench):
                expr = bench == self.lab.benches[bench.name]
                if not expr:
                    logger.warning("{} not in lab.benches %s", bench)
                return expr

            self.validate_exprs.append(bench_in_lab)

        def instrument_hooked(instrument=instrument, host=host, bench=bench):
            and_expr = True
            if host is not None:
                expr = (instrument in host)
                if not expr:
                    logger.warning("{} not in {} %s", (instrument, host))
                and_expr = and_expr and expr

            if bench is not None:
                expr = (instrument in bench)
                if not expr:
                    logger.warning("{} not in {} %s", (instrument, bench))
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
                    logger.error("Connection {} is not compatible with lab %s", connection)
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
        if self.name is not None:
            return "Experiment {}".format(self.name)
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


class MasterExperiment(Virtualizable):
    ''' Does nothing except hold sub experiments to synchronize them.
        This is purely a naming thing.
    '''
    pass
