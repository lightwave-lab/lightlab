from .visa_object import VISAObject
from lightlab import logger
import inspect

class DriverMeta(type):
    '''
        Todo:
            Make this play nice with other metaclasses, such as MetaWithRequirements
    '''
    def __init__(cls, name, bases, dct):
        ''' Checks that it satisfies the API of its Instrument
        '''
        if cls.instrument_category is not None:
            inst_klass = cls.instrument_category
            for essential in inst_klass.essentialMethods + inst_klass.essentialProperties:
                if essential not in dir(cls):
                    raise TypeError(cls.__name__ + ' does not implement {}, '.format(essential) + \
                                    'which is essential to its category of {}'.format(inst_klass.__name__))
        super().__init__(name, bases, dct)

    def __call__(cls, *args, **kwargs):
        '''
            All \*args go to the driver.
            name and address go to both.
            kwargs go priority to driver bases, otherwise to Instrument

        '''
        if cls.instrument_category is not None:
            name = kwargs.pop('name', None)
            address = kwargs.pop('address', None)

            # Split the kwargs into those needed by
            # 1) driver and its bases and 2) the leftovers
            def getArgs(klass):
                if klass is object:
                    return []
                initArgs = inspect.getargspec(klass.__init__)[0]
                for base_klass in klass.__bases__:
                    initArgs.extend(getArgs(base_klass))
                return initArgs
            driver_initArgNames = getArgs(cls)
            driver_kwargs = dict()
            instrument_kwargs = dict()
            for k, v in kwargs.items():
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

class VISAInstrumentDriver(VISAObject):
    """Generic (but not abstract) class for an instrument
    Initialize using the literal visa address

    Contains a visa communication object

    This might be the place to handle message session opening/closing
        release() should have an effect on both the message session and the lockout manager
    """
    instrument_category = None

    def __init__(self, name='Default Driver', address=None, **kwargs):
        self.name = name
        if 'tempSess' not in kwargs.keys():
            kwargs['tempSess'] = True
        super().__init__(address, **kwargs)
        self.__started = False

    def startup(self):
        logger.debug("{}startup method empty".format(self.__class__.__name__))

    def open(self):
        super().open()
        if not self.__started:
            self.startup()
            self.__started = True


DefaultDriver = VISAInstrumentDriver

