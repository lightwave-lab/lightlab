import numpy as np
from lightlab import logger
from contextlib import contextmanager
from lightlab.util.data import argFlatten


''' Module-wide variable
    If virtualOnly is True, any ``with`` statements using asReal will just skip the block
    When not using a context manager, it will eventually give you VirtualizationErrors
'''
virtualOnly = False


class VirtualizationError(RuntimeError):
    pass


class Virtualizable(object):
    ''' Virtualizable means that it can switch between two states, usually corresponding
        to a real-life situation and a virtual/simulated situation.
    '''
    def __init__(self, *args, **kwargs):
        try:
            super().__init__(*args, **kwargs)
        except TypeError:
            super().__init__()
        self._virtual = None
        self.synced = list()  # These are put in the same virtual state as this one

    def global_hardware_warmup(self):
        pass

    def hardware_warmup(self):
        ''' Be warned that this only works when using the context manager
        '''
        pass

    def hardware_cooldown(self):
        ''' Be warned that this only works when using the context manager
        '''
        pass

    def synchronize(self, *newVirtualizables):
        ''' Adds another object that this one will put in the same virtual state as itself.

            Args:
                newVirtualizables (*args, tuples, lists): Other virtualizable things
        '''
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

    @virtual.setter
    def virtual(self, toVirtual):
        ''' An alternative to context managing. Note that hardware_warmup will not be called
        '''
        global virtualOnly
        if virtualOnly and not toVirtual:
            toVirtual = None
        self._virtual = toVirtual
        for iSub, sub in enumerate(self.synced):
            sub._virtual = toVirtual

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
                sub.hardware_warmup()
            yield self
        finally:
            self.hardware_cooldown()
            self._virtual = old_value
            for iSub, sub in enumerate(self.synced):
                sub.hardware_cooldown()
                sub._virtual = old_subvalues[iSub]


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

        Todo:
            The naming for DualFunction and DualMethod are backwards. Will break notebooks when changed.
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


class VirtualInstrument(object):
    ''' Just a placeholder for future functionality '''
    pass
    # _virtual = True  # this is weird. shouldn't be here. If you are trying to do virtual switching, you should be using a DualInstrument


class DualInstrument(Virtualizable):
    ''' Holds a real instrument and a virtual instrument.
        Feeds through __getattribute__ and __setattr__: very powerful.
        It basically appears as one or the other instrument, as determined
        by whether it is in virtual or real mode.

        isinstance() and .__class__ will tell you the underlying instrument type
        type() will give you the DualInstrument subclass::

            dual = DualInstrument(realOne, virtOne)
            with dual.asReal():
                isinstance(dual, type(realOne))  # True
            isinstance(dual, type(realOne))  # False

        Subclassing:

            A typical subclass might look like this::

                class DualSourceMeter(DualInstrument):
                    realKlass = SourceMeter
                    virtKlass = VirtualSourceMeter

                    def __init__(self, *args, viResistiveRef=None, **kwargs):
                        super().__init__(real=self.realKlass(*args, **kwargs),
                            virt=self.virtKlass(viResistiveRef))

            Notice that realKlass and virtKlass are the major points.
            The __init__ *args and **kwargs are passed to the *hardware* initializer,
            while the explicit ones go the the virtual instrument initializer.
    '''
    realKlass = None
    virtKlass = None
    _virtual = None
    real = None
    virt = None
    synced = None

    def __init__(self, real=None, virt=None):
        self._virtual = None
        self.real = real
        self.virt = virt
        self.synced = []

    def __getattribute__(self, att):
        if att in DualInstrument.__dict__.keys():
            return object.__getattribute__(self, att)
        elif self._virtual is None:
            raise VirtualizationError('Virtual context unknown. Please refer to method asVirtual().\nAttribute was ' + att + ' in ' + str(self))
        else:
            if self._virtual:
                wrappedObj = object.__getattribute__(self, 'virt')
            else:
                wrappedObj = object.__getattribute__(self, 'real')
            return getattr(wrappedObj, att)

    def __setattr__(self, att, newV):
        if att in DualInstrument.__dict__.keys():
            return object.__setattr__(self, att, newV)
        elif self._virtual is None:
            raise VirtualizationError('Virtual context unknown. Please refer to method asVirtual().\nAttribute was ' + att + ' in ' + str(self))
        else:
            if self._virtual:
                wrappedObj = object.__getattribute__(self, 'virt')
            else:
                wrappedObj = object.__getattribute__(self, 'real')
            return setattr(wrappedObj, att, newV)

    def __dir__(self):
        return super().__dir__() + dir(self.virt) + dir(self.real)

    @classmethod
    def fromInstrument(cls, hwOnlyInstr, *args, **kwargs):
        ''' Gives a new dual instrument that has all the same properties and references.
            This is especially useful if you have an instrument stored in the JSON labstate,
            and would then like to virtualize it in your notebook.

            Does not reinitialize the driver. Keeps the same one.

            The instrument base of hwOnlyInstr must be the same instrument base of this class
        '''
        if not isinstance(hwOnlyInstr, cls.realKlass):
            raise TypeError('The fromInstrument ({}) is not an instance of the expected Instrument class ({})'.format(hwOnlyInstr.__class__.__name__, cls.realKlass.__name__))
        newObj = cls(*args, **kwargs)
        newObj.real = hwOnlyInstr
        return newObj

