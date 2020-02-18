''' Provides a framework for making virtual instruments that present
    the same interface and simulated behavior as the real ones. Allows
    a similar thing with functions, methods, and experiments.

    Dualization is a way of tying together a real instrument with
    its virtual counterpart. This is a powerful way to test procedures
    in a virtual environment before flipping the switch to reality.
    This is documented in :mod:`tests.test_virtualization`.

    Attributes:
        virtualOnly (bool): If virtualOnly is True, any "``with``" statements using asReal
            will just skip the block.
            When not using a context manager (i.e. ``exp.virtual = False``),
            it will eventually produce a ``VirtualizationError``.
'''
from lightlab import logger
from contextlib import contextmanager


virtualOnly = False


class Virtualizable(object):
    ''' Virtualizable means that it can switch between two states,
        usually corresponding
        to a real-life situation and a virtual/simulated situation.

        The attribute synced refers to other Virtualizables whose states
        will be synchronized with this one
    '''
    _virtual = None
    synced = None

    def __init__(self):
        self.synced = list()

    def synchronize(self, *newVirtualizables):
        r''' Adds another object that this one will put in the same virtual
            state as itself.

            Args:
                newVirtualizables (\*args): Other virtualizable things
        '''
        for virtualObject in newVirtualizables:
            if virtualObject is None or virtualObject in self.synced:
                continue
            if not issubclass(type(virtualObject), Virtualizable):
                raise TypeError('virtualObject of type ' +
                                str(type(virtualObject)) +
                                ' is not a Virtualizable subclass')
            self.synced.append(virtualObject)

    def __setAll(self, toVirtual):
        ''' Iterates over all synchronized members

            Returns:
                (list): the previous virtual states
        '''
        old_values = list()
        for sub in ([self] + self.synced):
            old_values.append(sub._virtual)  # pylint: disable=protected-access
            sub._virtual = toVirtual  # pylint: disable=protected-access
        return old_values

    def __restoreAll(self, old_values):
        ''' Iterates over all synchronized members

            Args:
                old_values (list): the previous virtual states
        '''
        for iSub, sub in enumerate([self] + self.synced):
            sub._virtual = old_values[iSub]  # pylint: disable=protected-access

    @property
    def virtual(self):
        ''' Returns the virtual state of this object
        '''
        if self._virtual is None:
            raise VirtualizationError('Virtual context unknown.'
                                      'Please refer to method asVirtual().')
        else:
            return self._virtual

    @virtual.setter
    def virtual(self, toVirtual):
        ''' Setting the property is an alternative to context managing.

            Using this can make code more concise,
            but it does not handle warmups/cooldowns.
            It also does not record the old states.
        '''
        if virtualOnly and not toVirtual:
            toVirtual = None
        self.__setAll(toVirtual)

    @contextmanager
    def asVirtual(self):
        ''' Temporarily puts this and synchronized in a virtual state.
            The state is reset at the end of the with block.

            Example usage:

            .. code-block:: python

                exp = Virtualizable()
                with exp.asVirtual():
                    print(exp.virtual)  # prints True
                print(exp.virtual)  # VirtualizationError
        '''
        old_values = self.__setAll(True)
        try:
            yield self
        finally:
            self.__restoreAll(old_values)

    @contextmanager
    def asReal(self):
        ''' Temporarily puts this and synchronized in a virtual state.
            The state is reset at the end of the with block.

            If ``virtualOnly`` is True, it will skip the block without error

            Example usage:

            .. code-block:: python

                exp = Virtualizable()
                with exp.asVirtual():
                    print(exp.virtual)  # prints False
                print(exp.virtual)  # VirtualizationError
        '''
        if virtualOnly:
            try:
                yield self
            except VirtualizationError:
                pass

        # Set the virtual states
        old_values = self.__setAll(False)

        # Try to call hardware warmup if present
        for sub in ([self] + self.synced):
            try:
                sub.hardware_warmup()
            except AttributeError:
                pass

        try:
            yield self

        finally:
            # Try to call hardware cooldown if present
            for sub in ([self] + self.synced):
                try:
                    sub.hardware_cooldown()
                except AttributeError:
                    pass

            # Restore virtual states
            self.__restoreAll(old_values)


class VirtualInstrument(object):
    ''' Just a placeholder for future functionality '''
    @contextmanager
    def asVirtual(self):
        ''' do nothing '''
        yield self


class DualInstrument(Virtualizable):
    ''' Holds a real instrument and a virtual instrument.
        Feeds through ``__getattribute__`` and ``__setattr__``: very powerful.
        It basically appears as one or the other instrument, as determined
        by whether it is in virtual or real mode.

        This is especially useful if you have an instrument
        stored in the JSON labstate,
        and would then like to virtualize it in your notebook.
        In that case, it does not reinitialize the driver.

        This is documented in :mod:`tests.test_virtualization`.

        ``isinstance()`` and ``.__class__`` will tell you the underlying instrument type
        ``type()`` will give you the ``DualInstrument`` subclass::

            dual = DualInstrument(realOne, virtOne)
            with dual.asReal():
                isinstance(dual, type(realOne))  # True
                dual.meth is realOne.meth  # True
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
            allowed = real_obj.essentialMethods + \
                real_obj.essentialProperties + dir(VirtualInstrument)
            for attr in dir(type(virt_obj)):
                if attr not in allowed \
                        and '__' not in attr:
                    violated.append(attr)
            if len(violated) > 0:
                logger.warning('Virtual instrument ({}) violates '.format(type(virt_obj).__name__) +
                               'interface of the real one ({})'.format(type(real_obj).__name__))
                logger.warning('Got: ' + ', '.join(violated))  # pylint: disable=logging-not-lazy
                # logger.warning('Allowed: ' + ', '.join(filter(lambda x: '__' not in x, allowed)))
        self.synced = []
        super().__init__()

    @Virtualizable.virtual.setter  # pylint: disable=no-member
    def virtual(self, toVirtual):
        ''' An alternative to context managing.
            Note that hardware_warmup will not be called,
            so it is not recommended to be called directly.
        '''
        if virtualOnly and not toVirtual:
            toVirtual = None
        if toVirtual and self.virt_obj is None:
            raise VirtualizationError('No virtual object specified in',
                                      type(self.real_obj))
        elif not toVirtual and self.real_obj is None:
            raise VirtualizationError('No real object specified in',
                                      type(self.virt_obj))
        self._virtual = toVirtual
        for sub in self.synced:
            sub.virtual = toVirtual

    def __getattribute__(self, att):
        ''' Intercepts immediately and routes to ``virt_obj`` or ``real_obj``,
            depending on the virtual state.
        '''
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
        ''' Intercepts immediately and routes to ``virt_obj`` or ``real_obj``,
            depending on the virtual state.
        '''
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
        ''' Facilitates autocompletion in IPython '''
        return super().__dir__() + dir(self.virt_obj) + dir(self.real_obj)


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


class VirtualizationError(RuntimeError):
    pass
