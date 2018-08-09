from functools import wraps
from .prologix_gpib import PrologixGPIBObject
from .visa_object import VISAObject


class InstrumentIOError(RuntimeError):
    pass


class InstrumentSession(object):
    ''' An abstraction class between instrument drivers and actual
    instruments'''

    session_object = None

    def get_session_object(self):
        address = self.address
        if address is not None and address.startswith('prologix://'):
            if type(self.session_object) != PrologixGPIBObject:
                self.session_object = PrologixGPIBObject(address=address, tempSess=self.tempSess)
        else:
            if type(self.session_object) != VISAObject:
                self.session_object = VISAObject(address=address, tempSess=self.tempSess)
        return self.session_object

    def make_method(method_name):
        def real_method(self, *args, **kwargs):
            so = self.get_session_object()
            f = getattr(so, method_name)
            return f(*args, **kwargs)
        return real_method

    def make_property(property_name):
        def get_property(self):
            return getattr(self.get_session_object(), property_name)

        def set_property(self, value):
            setattr(self.get_session_object(), property_name, value)

        def del_property(self):
            delattr(self.get_session_object(), property_name)

        return property(get_property, set_property, del_property, property_name)

    def __init__(self, address=None, tempSess=False):
        self.address = address
        self.tempSess = tempSess
        super().__init__()

    spoll = make_method('spoll')
    LLO = make_method('LLO')
    LOC = make_method('LOC')
    open = make_method('open')
    close = make_method('close')
    write = make_method('write')
    query = make_method('query')
    clear = make_method('clear')
    query_raw_binary = make_method('query_raw_binary')
    instrID = make_method('instrID')
    timeout = make_property('timeout')
    termination = make_property('termination')
