''' Works with DualInstrument and context setting
'''

import pytest
from lightlab.laboratory.virtualization import DualInstrument, Virtualizable
from lightlab.laboratory.instruments import Instrument


class HammerInterface(Instrument):
    essentialMethods = Instrument.essentialMethods + \
        ['nail']

class HammerImplementation

class VirtualHammer


def test_contextual():
    pass
