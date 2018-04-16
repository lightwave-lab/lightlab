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
from lightlab.equipment.lab_instruments import ILX_7900B_LS
import lightlab
from lightlab.util.io import ChannelError


class LS_MessageSender(ILX_7900B_LS):
    writeBuffer = None

    def __init__(self, **kwargs):
        self.writeBuffer = []
        super().__init__(**kwargs)

    def open(self): pass

    def write(self, string):
        self.writeBuffer.append(string)
        print(string)

    def query(self, string):
        ''' Argument "string" is ignored '''
        return '0'
        # raise NotImplementedError('Sender has no query')


def test_laser():
    LS = LS_MessageSender(name='foo', address='NULL', useChans=[0, 2, 1], directInit=True)
    LS.setChannelEnable({2: 1})
    with pytest.raises(ChannelError):
        LS.setChannelEnable({3: 1})
    # with pytest.raises(ChannelError):
    #     LS.moduleIterate('enableState', [0])
    # with pytest.raises(ChannelError):
    #     LS.moduleIterate('enableState', [0, 0, 0, 0])

    print(LS.writeBuffer)


from lightlab import logger, log_to_screen, DEBUG

if __name__ == '__main__':
    ''' Call with python or ipython instead of py.test to see output
    '''
    log_to_screen(DEBUG)
    test_laser()

