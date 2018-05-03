from .visa_object import VISAObject
from lightlab import logger
import inspect


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

    def __call__(cls, *args, **kwargs):
        r'''
            All \*args go to the driver.
            name and address go to both.
            kwargs go priority to driver bases, otherwise to Instrument.

            This occurs at initialization time of an object
        '''
        if (cls.instrument_category is not None and
                not kwargs.pop('directInit', False)):
            name = kwargs.pop('name', None)
            address = kwargs.pop('address', None)

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

            driver_obj = type.__call__(cls, *args,
                                       name=name, address=address,
                                       **driver_kwargs)
            instrument_obj = type.__call__(cls.instrument_category,
                                           name=name, address=address,
                                           driver_object=driver_obj,
                                           driver_kwargs=driver_kwargs,
                                           **instrument_kwargs)
            return instrument_obj
        else:
            return type.__call__(cls, *args, **kwargs)


class VISAInstrumentDriver(VISAObject, metaclass=DriverMeta):
    ''' Generic (but not abstract) class for an instrument.
        Initialize using the literal visa address

        Contains a visa communication object.
    '''
    instrument_category = None

    def __init__(self, name='Default Driver', address=None, directInit=False, **kwargs):  # pylint: disable=unused-argument
        self.name = name
        if 'tempSess' not in kwargs.keys():
            kwargs['tempSess'] = True
        super().__init__(address=address, **kwargs)
        self.__started = False

    def startup(self):
        logger.debug("%s.startup method empty", self.__class__.__name__)

    def open(self):
        super().open()
        if not self.__started:
            self.__started = True
            self.startup()
            super().open()


DefaultDriver = VISAInstrumentDriver
