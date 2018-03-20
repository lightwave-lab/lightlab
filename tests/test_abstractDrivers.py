''' Make a Configurable subclass called MessagePasser

    The MessagePasser acting as a driver writes to a buffer,
    instead of a pyvisa.mbSession.

    The buffer is read by another MessagePasser (acting as the instrument)

    This is not really an intended use for message passing between objects in code,
    but hey it shows that Configurable does a good job emulating how a real-life
    configurable instrument works.
'''
import pytest
from lightlab.equipment.abstract_drivers import Configurable, AbstractDriver, DriverRequiresQuery
import lightlab

from lightlab import logger, log_to_screen, DEBUG

if __name__ == '__main__':
    log_to_screen(DEBUG)
    test_configurable()

def test_metaclass_init():
    ''' Catches incomplete API at class time, not instantiation time, not runtime
    '''
    class ARealDriver(Configurable):
        def query():
            pass
        def write():
            pass
    class AnAbstractDriver(Configurable, AbstractDriver):
        pass
    with pytest.raises(TypeError):
        class NotARealDriver(Configurable):
            pass

def test_configurable():
    class MessagePasser(Configurable):
        other = None
        _writeBuffer = None

        def __init__(self, **kwargs):
            self._writeBuffer = []
            kwargs['headerIsOptional'] = False
            super().__init__(**kwargs)

        def write(self, string):
            self.other._writeBuffer.append(string)

        def query(self, string):
            ''' Argument "string" is ignored '''
            ret = self._writeBuffer[0]
            self._writeBuffer = self._writeBuffer[1:]
            return ret


    alice = MessagePasser()
    bob = MessagePasser()
    alice.other = bob
    bob.other = alice

    alice.setConfigParam('foo', 1) # int
    bob.getConfigParam('foo')
    bob.getConfigParam('foo') # does not attempt to read from buffer, which is empty
    with pytest.raises(IndexError):
        bob.getConfigParam('foo', forceHardware=True)
    alice.setConfigParam('bar', 2.5) # float
    bob.getConfigParam('bar')
    bob.setConfigParam('baz:zaz', 'bang') # str
    alice.getConfigParam('baz:zaz')

    for cmd in ['foo', 'bar', 'baz:zaz']:
        assert alice.getConfigParam(cmd) \
               == bob.getConfigParam(cmd)
    assert sorted(alice.config['live'].getList(asCmd=False)) \
           == sorted(bob.config['live'].getList(asCmd=False))

    alice.setConfigParam('spam', 2.2)
    bob.getConfigParam('spam')
    alice.setConfigParam('spam', 2.3)
    bob.getConfigParam('spam')
    with pytest.raises(AssertionError): # Because bob only read the first one
        assert alice.getConfigParam('spam') \
               == bob.getConfigParam('spam')
    bob.getConfigParam('spam', forceHardware=True)
    assert alice.getConfigParam('spam') \
           == bob.getConfigParam('spam')

from lightlab.equipment.visa_bases import VISAInstrumentDriver, DriverMeta
from lightlab.equipment.lab_instruments import HP_8152A_PM
from lightlab.laboratory.instruments import PowerMeter
def test_driver_init():
    # Catches incomplete API at class time
    with pytest.raises(TypeError):
        class Delinquent_PM(VISAInstrumentDriver, metaclass=DriverMeta):
            instrument_category = PowerMeter
            def powerLin(self): pass
            # def powerDbm(self): pass

    # Old style still works
    pm = PowerMeter(name='a PM', address='NULL', _driver_class=HP_8152A_PM, extra='foolio')
    assert pm.__class__ == PowerMeter  # not SourceMeter or HP_8152A_PM
    assert pm._driver_class == HP_8152A_PM
    # New style
    pm = HP_8152A_PM(name='a PM', address='NULL', extra='foolio')
    assert pm.__class__ == PowerMeter  # not SourceMeter or HP_8152A_PM
    assert pm._driver_class == HP_8152A_PM
