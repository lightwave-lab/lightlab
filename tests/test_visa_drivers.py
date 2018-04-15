''' Tests whether all the visa drivers included in lightlab are properly
coded. All tests should be safe to run locally.'''

import pytest
from mock import patch
from lightlab.equipment import lab_instruments
from lightlab.equipment.lab_instruments import VISAInstrumentDriver
import inspect

classes = []  # All classes that inherit VISAInstrumentDriver
for name, obj in inspect.getmembers(lab_instruments):
    if inspect.isclass(obj) and issubclass(obj, VISAInstrumentDriver):
        classes.append(obj)

class OpenError(RuntimeError):
    pass


@pytest.mark.parametrize("instrum", classes)
def test_instantiate_instrum(instrum):
    ''' Instatiates instruments and asserts that .open should not be called
    '''
    def open_error(self):
        raise OpenError("self.open() function being called upon initialization.")
    with patch.object(instrum, 'open', open_error):
        obj = instrum()
    with pytest.raises((RuntimeError, AttributeError)):
        obj.open()


from lightlab.equipment.lab_instruments import NI_PCI_6723, ILX_7900B_LS
from lightlab.equipment.abstract_drivers import MultiChannelSource
def test_instrums_withChannels():
    cs = NI_PCI_6723(name='a CS', address='NULL', elChans=[1, 2])
    assert cs.elChans == [1, 2]
    ls = ILX_7900B_LS(name='a LS', address='NULL', dfbChans=[1, 2])
    assert ls.dfbChans == [1, 2]
