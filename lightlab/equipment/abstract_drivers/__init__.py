
class AbstractDriver():
    ''' Something that is an AbstractDriver assumes the real one has ``write`` and ``query``.
        This basically checks that. Other functionality might come here later.
    '''
    pass

class DriverRequiresQuery(type):
    def __init__(cls, name, bases, dct):
        if AbstractDriver not in bases:
            for driver_method in ['query']:
                if driver_method not in dir(cls):
                    raise TypeError(cls.__name__ + ' must implement query '
                                    'since it inherits from an AbstractDriver')
        super().__init__(name, bases, dct)


def concreteRequires(*attrs):
    class MetaWithRequirements(type):
        def __init__(cls, name, bases, dct):
            if AbstractDriver not in bases:
                for driver_method in attrs:
                    if driver_method not in dir(cls):
                        raise TypeError(cls.__name__ + ' must implement {} '.format(driver_method) + \
                                        'since it inherits from an AbstractDriver')
            super().__init__(name, bases, dct)
    return MetaWithRequirements


from .configurable import *
from .electrical_sources import *
from .power_meters import *
from .TekScopeAbstract import *
