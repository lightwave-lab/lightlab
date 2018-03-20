

class AbstractDriver(object):
    ''' Something that is an AbstractDriver assumes the real one has ``write`` and ``query``.
        This basically checks that. Other functionality might come here later.
    '''
    def __init__(self, *args, **kwargs):
        for driver_method in ['write', 'query']:
            if driver_method not in dir(type(self)):
                raise TypeError(str(type(self)) + ' is abstract'
                    'and cannot be initialized without having write and query')
        super().__init__(*args, **kwargs)


from .configurable import *
from .electrical_sources import *
from .power_meters import *
from .TekScopeAbstract import *
