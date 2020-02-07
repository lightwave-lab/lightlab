from lightlab import visalogger
import inspect

from .driver_base import InstrumentSessionBase
from .prologix_gpib import PrologixGPIBObject
from .visa_object import VISAObject


class InstrumentIOError(RuntimeError):
    pass


class _AttrGetter(object):
    # see
    # https://stackoverflow.com/questions/28861064/super-object-has-no-attribute-getattr-in-python3

    def __getattr__(self, name):
        raise AttributeError("'{}' has no attribute '{}'".format(str(self), name))


_InstrumentSessionBase_methods = list(name for name, _ in inspect.getmembers(
    InstrumentSessionBase, lambda o: inspect.isfunction(o) or isinstance(o, property)))


class InstrumentSession(_AttrGetter):
    ''' This class is the interface between the higher levels of lightlab instruments
    and the driver controlling the GPIB line. Its methods are specialized into
    either PrologixGPIBObject or VISAObject.

    This was mainly done because the Prologix GPIB Ethernet controller
    is not VISA compatible and does not provide a VISA interface.

    If the address starts with 'prologix://', it will use PrologixGPIBObject's methods,
    otherwise it will use VISAObject's methods (relying on pyvisa).

    .. warning:: Since this is a wrapper class to either :py:class:`PrologixGPIBObject`
    or :py:class:`VISAObject`, avoid using super() in overloaded methods.
    (see `this <https://stackoverflow.com/questions/12047847/super-object-not-calling-getattr>`_)

    '''

    _session_object = None

    def reinstantiate_session(self, address, tempSess):
        if address is not None and address.startswith('prologix://'):
            self._session_object = PrologixGPIBObject(address=address, tempSess=tempSess)
        else:
            self._session_object = VISAObject(address=address, tempSess=tempSess)

    def __init__(self, address=None, tempSess=False):
        self.reinstantiate_session(address, tempSess)
        self.tempSess = tempSess
        self.address = address

    def open(self):
        return self._session_object.open()

    def close(self):
        return self._session_object.close()

    def __getattr__(self, name):
        if name in ('_session_object'):
            return super().__getattr__(name)
        else:
            try:
                return_attr = getattr(self._session_object, name)
            except AttributeError:
                return_attr = super().__getattr__(name)  # pylint: disable=assignment-from-no-return
            else:
                if name not in _InstrumentSessionBase_methods:
                    visalogger.warning("Access to %s.%s will be deprecated soon. "
                                       "Please include it in InstrumentSessionBase. "
                                       "", type(self._session_object).__name__, name)

            return return_attr

    def __dir__(self):
        return set(super().__dir__() + list(_InstrumentSessionBase_methods))

    def __setattr__(self, name, value):
        if name in ('_session_object'):
            super().__setattr__(name, value)
        elif name in ('address'):
            super().__setattr__(name, value)
            if self._session_object is not None and self._session_object.address != value:
                tempSess = self._session_object.tempSess
                self.reinstantiate_session(address=value, tempSess=tempSess)
        elif hasattr(self._session_object, name):
            setattr(self._session_object, name, value)
            # also change in local dictionary if possible
            if name in self.__dict__:
                self.__dict__[name] = value
        else:
            super().__setattr__(name, value)


class IncompleteClass(Exception):
    pass


class DriverMeta(type):
    '''
        Driver initializer returns an instrument in ``instrument_category``,
        not an instance of the Driver itself, unless
            * ``instrument_category`` is None
            * ``directInit=True`` is passed in

        Also checks that the API is satistied at compile time,
        providing some early protection against bad drivers, like this:
        :py:func:`~tests.test_virtualization.test_badDriver`.
    '''
    def __init__(cls, name, bases, dct):
        ''' Checks that it satisfies the API of its Instrument.

            This occurs at compile-time
        '''
        if cls.instrument_category is not None:
            inst_klass = cls.instrument_category
            for essential in inst_klass.essentialMethods + inst_klass.essentialProperties:
                if essential not in dir(cls):
                    raise IncompleteClass(cls.__name__ + ' does not implement {}, '.format(essential) +
                                          'which is essential for {}'.format(inst_klass.__name__))
        super().__init__(name, bases, dct)

    def __call__(cls, name=None, address=None, *args, **kwargs):
        r'''
            All \*args go to the driver.
            name and address go to both.
            kwargs go priority to driver bases, otherwise to Instrument.

            This occurs at initialization time of an object
        '''
        if (cls.instrument_category is not None and
                not kwargs.pop('directInit', False)):

            # Split the kwargs into those needed by
            # 1) driver and its bases and 2) the leftovers
            def getArgs(klass):
                if klass is object:
                    return []
                initArgs = inspect.getfullargspec(klass.__init__)[0]
                for base_klass in klass.__bases__:
                    initArgs.extend(getArgs(base_klass))
                return initArgs
            driver_initArgNames = getArgs(cls)
            driver_kwargs = dict()
            instrument_kwargs = dict()
            for k, v in kwargs.items():
                if k in cls.instrument_category.essentialMethods \
                        + cls.instrument_category.essentialProperties \
                        + cls.instrument_category.optionalAttributes:
                    raise ValueError('Essential attribute {} cannot be '.format(k) +
                                     'passed as a kwarg to the initializer of {}.'.format(cls.__name__))
                if k in driver_initArgNames:
                    driver_kwargs[k] = v
                else:
                    instrument_kwargs[k] = v

            driver_obj = type.__call__(cls, name=name, address=address,
                                       *args, **driver_kwargs)
            instrument_obj = type.__call__(cls.instrument_category,
                                           name=name, address=address,
                                           driver_object=driver_obj,
                                           driver_kwargs=driver_kwargs,
                                           **instrument_kwargs)
            return instrument_obj
        else:
            return type.__call__(cls, name=name, address=address, *args, **kwargs)


class VISAInstrumentDriver(InstrumentSession, metaclass=DriverMeta):
    ''' Generic (but not abstract) class for an instrument.
        Initialize using the literal visa address

        Contains a visa communication object.
    '''
    instrument_category = None

    def __init__(self, name='Default Driver', address=None, **kwargs):  # pylint: disable=unused-argument
        self.name = name
        self.address = address
        kwargs.pop('directInit', False)
        if 'tempSess' not in kwargs.keys():
            kwargs['tempSess'] = True
        super().__init__(address=address, **kwargs)
        self.__started = False

    def startup(self):
        visalogger.debug("%s.startup method empty", self.__class__.__name__)

    def open(self):
        super().open()
        if not self.__started:
            self.__started = True
            self.startup()

    def close(self):
        super().close()
        self.__started = False


DefaultDriver = VISAInstrumentDriver
