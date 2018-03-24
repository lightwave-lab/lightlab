from lightlab import logger
from contextlib import contextmanager


''' Module-wide variable
    If virtualOnly is True, any ``with`` statements using asReal
    will just skip the block

    When not using a context manager, it will
    eventually give you VirtualizationErrors
'''
virtualOnly = False


class VirtualizationError(RuntimeError):
    pass


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
    def __init__(self, virtual_function=None,
                 hardware_function=None, doc=None):
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

            The naming for DualFunction and DualMethod are backwards.
            Will break notebooks when changed.
    '''
    def __init__(self, dualInstrument=None, virtual_function=None,
                 hardware_function=None, doc=None):
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
    ''' Virtualizable means that it can switch between two states,
        usually corresponding
        to a real-life situation and a virtual/simulated situation.

        The attribute synced refers to other Virtualizables whose states
        will be synchronized with this one
    '''
    _virtual = None
    synced = None

    def __init__(self, *args, **kwargs):
        try:
            super().__init__(*args, **kwargs)
        except TypeError:
            super().__init__()
        self.synced = list()

    def synchronize(self, *newVirtualizables):
        ''' Adds another object that this one will put in the same virtual
            state as itself.

            Args:

                newVirtualizables (\*args): Other virtualizable things
        '''
        for virtualObject in newVirtualizables:
            if virtualObject is None or virtualObject in self.synced:
                continue
            if not issubclass(type(virtualObject), Virtualizable):
                raise TypeError('virtualObject of type '
                                + str(type(virtualObject))
                                + ' is not a Virtualizable subclass')
            self.synced.append(virtualObject)

    @property
    def virtual(self):
        if self._virtual is None:
            raise VirtualizationError('Virtual context unknown.'
                                      'Please refer to method asVirtual().')
        else:
            return self._virtual

    @virtual.setter
    def virtual(self, toVirtual):
        ''' An alternative to context managing.
        '''
        global virtualOnly
        if virtualOnly and not toVirtual:
            toVirtual = None
        self._virtual = toVirtual
        for sub in self.synced:
            sub.virtual = toVirtual

    @contextmanager
    def asVirtual(self):
        old_value = self._virtual
        self.virtual = True
        old_subvalues = list()
        for iSub, sub in enumerate(self.synced):
            old_subvalues.append(sub._virtual)
            sub.virtual = True
        try:
            yield self
        finally:
            self.virtual = old_value
            for iSub, sub in enumerate(self.synced):
                sub.virtual = old_subvalues[iSub]

    @contextmanager
    def asReal(self):
        ''' If virtualOnly is True, it will skip the block without error
        '''
        global virtualOnly
        if virtualOnly:
            try:
                yield self
            except VirtualizationError:
                pass
            finally:
                return

        old_value = self._virtual
        self.virtual = False
        old_subvalues = list()
        for iSub, sub in enumerate(self.synced):
            old_subvalues.append(sub._virtual)
            sub.virtual = False
        try:
            yield self
        finally:
            self.virtual = old_value
            for iSub, sub in enumerate(self.synced):
                sub.virtual = old_subvalues[iSub]


class VirtualInstrument(object):
    ''' Just a placeholder for future functionality '''
    @contextmanager
    def asVirtual(self):
        ''' do nothing '''
        yield self


class DualInstrument(Virtualizable):
    ''' Holds a real instrument and a virtual instrument.
        Feeds through __getattribute__ and __setattr__: very powerful.
        It basically appears as one or the other instrument, as determined
        by whether it is in virtual or real mode.

        This is especially useful if you have an instrument
        stored in the JSON labstate,
        and would then like to virtualize it in your notebook.
        In that case, it does not reinitialize the driver.


        isinstance() and __class__ will tell you the underlying instrument type
        type() will give you the DualInstrument subclass::

            dual = DualInstrument(realOne, virtOne)
            with dual.asReal():
                isinstance(dual, type(realOne))  # True
            isinstance(dual, type(realOne))  # False
    '''
    real_obj = None
    virt_obj = None

    def __init__(self, real_obj=None, virt_obj=None):
        '''
            Args:

                real_obj (Instrument): the real reference
                virt_obj (VirtualInstrument): the virtual reference
        '''
        self.real_obj = real_obj
        self.virt_obj = virt_obj
        if real_obj is not None and virt_obj is not None:
            violated = []
            allowed = real_obj.essentialMethods + real_obj.essentialProperties
            for attr in dir(type(virt_obj)):
                if attr not in allowed and attr[:2] != '__':
                    violated.append(attr)
            if len(violated) > 0:
                logger.warning('Virtual instrument ({}) violates the \
                                interface of the real one ({})'.format(
                                    type(virt_obj).__name__,
                                    type(real_obj).__name__))
                logger.warning('Got: ' + ', '.join(violated))
                logger.warning('Allowed: ' + ', '.join(allowed))
        self.synced = []

    @Virtualizable.virtual.setter
    def virtual(self, toVirtual):
        ''' An alternative to context managing.
            Note that hardware_warmup will not be called,
            so it is not recommended to be called directly.
        '''
        global virtualOnly
        if virtualOnly and not toVirtual:
            toVirtual = None
        if toVirtual == True and self.virt_obj is None:
            raise VirtualizationError('No virtual object specified in',
                                      type(self.real_obj))
        elif toVirtual == False and self.real_obj is None:
            raise VirtualizationError('No real object specified in',
                                      type(self.virt_obj))
        self._virtual = toVirtual
        for sub in self.synced:
            sub.virtual = toVirtual

    @contextmanager
    def asReal(self):
        ''' Wraps making self.virtual to False.
            Also does hardware warmup and cooldown
        '''
        global virtualOnly
        if virtualOnly:
            try:
                yield self
            except VirtualizationError:
                pass
            finally:
                return

        with super().asReal():
            try:
                self.hardware_warmup()
                for sub in self.synced:
                    sub.hardware_warmup()
                yield self
            finally:
                self.hardware_cooldown()
                for sub in self.synced:
                    sub.hardware_cooldown()

    def __getattribute__(self, att):
        if att in (list(DualInstrument.__dict__.keys()) +
                   list(Virtualizable.__dict__.keys())):
            return object.__getattribute__(self, att)
        elif self._virtual is None:
            raise VirtualizationError('Virtual context unknown.'
                                      'Please refer to method asVirtual().'
                                      '\nAttribute was ' + att + ' in ' + str(self))
        else:
            if self._virtual:
                wrappedObj = object.__getattribute__(self, 'virt_obj')
            else:
                wrappedObj = object.__getattribute__(self, 'real_obj')
            return getattr(wrappedObj, att)

    def __setattr__(self, att, newV):
        if att in (list(DualInstrument.__dict__.keys()) +
                   list(Virtualizable.__dict__.keys())):
            return object.__setattr__(self, att, newV)
        elif self._virtual is None:
            raise VirtualizationError(
                'Virtual context unknown.'
                'Please refer to method asVirtual().'
                '\nAttribute was ' + att + ' in ' + str(self))
        else:
            if self._virtual:
                wrappedObj = object.__getattribute__(self, 'virt_obj')
            else:
                wrappedObj = object.__getattribute__(self, 'real_obj')
            return setattr(wrappedObj, att, newV)

    def __dir__(self):
        return super().__dir__() + dir(self.virt_obj) + dir(self.real_obj)

    @classmethod
    def fromInstrument(cls, hwOnlyInstr, *args, **kwargs):
        ''' Gives a new dual instrument that has all the same
            properties and references.


            The instrument base of hwOnlyInstr must be the same instrument
            base of this class
        '''
        if hwOnlyInstr is not None and not isinstance(hwOnlyInstr, cls.real_klass):
            raise TypeError(
                'The fromInstrument (' + hwOnlyInstr.__class__.__name__ + ')'
                ' is not an instance of the expected Instrument class'
                ' (' + cls.real_klass.__name__ + ')')
        newObj = cls(*args, **kwargs)
        newObj.real_obj = hwOnlyInstr
        return newObj
