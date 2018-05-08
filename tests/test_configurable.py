''' Make a Configurable subclass called MessagePasser

    The MessagePasser acting as a driver writes to a buffer,
    instead of a pyvisa.mbSession.

    The buffer is read by another MessagePasser (acting as the instrument)

    This is not really an intended use for message passing between objects in code,
    but hey it shows that Configurable does a good job emulating how a real-life
    configurable instrument works.
'''
import pytest
from lightlab.equipment.abstract_drivers import Configurable, AbstractDriver


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


def test_configurable():
    ''' Conditional write/query to hardware
    '''
    alice = MessagePasser()
    bob = MessagePasser()
    alice.other = bob
    bob.other = alice

    alice.setConfigParam('foo', 1)
    # 'foo': 1 has been placed on bob's buffer
    bob.getConfigParam('foo')
    # The buffer is now empty
    bob.getConfigParam('foo')  # does not attempt to read from buffer
    with pytest.raises(IndexError):
        bob.getConfigParam('foo', forceHardware=True)

    alice.setConfigParam('spam', 2.2)
    bob.getConfigParam('spam')
    alice.setConfigParam('spam', 2.3)
    bob.getConfigParam('spam')  # does not attempt to read from buffer
    with pytest.raises(AssertionError):  # Because bob only read the first one
        assert alice.getConfigParam('spam') \
            == bob.getConfigParam('spam')

    bob.getConfigParam('spam', forceHardware=True)
    assert alice.getConfigParam('spam') \
        == bob.getConfigParam('spam')


def test_type_detection():
    alice = MessagePasser()
    bob = MessagePasser()
    alice.other = bob
    bob.other = alice

    alice.setConfigParam('foo', 1)  # int
    bob.getConfigParam('foo')
    alice.setConfigParam('bar', 2.5)  # float
    bob.getConfigParam('bar')
    bob.setConfigParam('baz:zaz', 'bang')  # str (sending reverse direction)
    alice.getConfigParam('baz:zaz')

    for cmd in ['foo', 'bar', 'baz:zaz']:
        assert alice.getConfigParam(cmd) \
            == bob.getConfigParam(cmd)
    assert sorted(alice.config['live'].getList(asCmd=False)) \
        == sorted(bob.config['live'].getList(asCmd=False))

def test_init_config():
    alice = MessagePasser()
    bob = MessagePasser()
    alice.other = bob
    bob.other = alice

    alice.setConfigParam('foo', 1)
    alice.setConfigParam('foo', 2)
    assert alice.config['init'].get('foo', asCmd=False) == 1
    assert alice.config['live'].get('foo', asCmd=False) == 2

    # Now bob comes along. There are currently two in the buffer.
    bob.getConfigParam('foo')
    bob.getConfigParam('foo', forceHardware=True)
    assert bob.config['init'].get('foo', asCmd=False) == 1
    assert bob.config['live'].get('foo', asCmd=False) == 2

