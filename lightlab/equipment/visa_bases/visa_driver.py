from .visa_object import VISAObject
from lightlab import logger

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
            Todo:
                Figure out how to pass any arguments needed by bases into cls() kwargs.
                We might need to inspect the mro.

                What do we do with \*args?

                End goal is to remove that line in Instrument that asks for 'useChans' etc.
        '''
        instName = kwargs.pop('name', None)
        instAddress = kwargs.pop('address', None)
        # Basically, can we put kwargs in here and get out everything that doesn't get sucked up
        driver_obj = type.__call__(cls, *args, name=instName, address=instAddress)
        if cls.instrument_category is not None:
            instrument_obj = type.__call__(cls.instrument_category, *args,
                                           name=instName, address=instAddress,
                                           driver_object=driver_obj, **kwargs)
            return instrument_obj
        else:
            return driver_obj

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

