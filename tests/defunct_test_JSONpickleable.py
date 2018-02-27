''' Pretty advanced saving and loading

    Complicated linkages within members are maintained

    Attributes starting with __ are not there at all

    Some attributes are not picked, but still exist as None
        They can be specified in ``notPickled`` or if they are a subclass of VISAObject

    Remember that loading does not call __init__, so watch out for side effects.
        This is the primary reason that VISAObjects are not allowed
        because they all have side effects in the real world
'''
import pytest
from lightlab.util.io import JSONpickleable
from lightlab.equipment.lab_instruments.visa_connection import VISAObject
import numpy as np
from lightlab.util.data import Spectrum

INSTANTIATION_COUNTER = 0

class SomeVirtualizedExperiment(JSONpickleable):
    notPickled = ['hwRef']

    def __init__(self, name=None):
        self.name = name
        self.__hidden = 'set within object'

        # This is an example of a side effect
        global INSTANTIATION_COUNTER
        INSTANTIATION_COUNTER += 1

    @property
    def hidden(self):
        return self.__hidden
#
    @hidden.setter
    def hidden(self, newVal):
        self.__hidden = newVal


class SomeInstrument(VISAObject):
    pass


class Port(object):
    pass


def bar(s):
    return s + 42

bar2 = lambda s: s + 42


class SomethingWithHardStuff(JSONpickleable):
    def __init__(self):
        self.x = np.array([]) # empty
        self.y = np.array(1) # scalar
        self.z = np.random.rand(5,5) # 2D
        self.someFuncs = (bar, bar2)
        self.aSpectrum = Spectrum([1,2], [3,4])


def test_JSONpickleable():
    portA = Port()
    portB = Port()
    portA.connectedTo = portB
    portB.connectedTo = portA

    subExp = SomeVirtualizedExperiment('Cousin IT')
    assert INSTANTIATION_COUNTER == 1
    subExp.hwRef = 10
    subExp.port = portB
    subExp.sneakyHwRef = SomeInstrument()

    exp = SomeVirtualizedExperiment('Uncle Tommy')
    assert INSTANTIATION_COUNTER == 2
    exp.hwRef = 20
    exp.sneakyHwRef = VISAObject()
    exp.port = portA
    exp.memberExp = subExp
    exp.hidden = 'Now it has been set'


    loadedExp = exp.copy() # does the same thing as save/load
    assert loadedExp is not exp
    assert loadedExp.name == exp.name

    # __init__ is not called again
    assert INSTANTIATION_COUNTER == 2

    # Complicated linkages within members are maintained
    newA = loadedExp.port
    assert newA is not portA
    newB = newA.connectedTo
    assert newA is newB.connectedTo

    # Some attributes were not pickled, but still exist as None
    assert loadedExp.hwRef is None
    assert loadedExp.sneakyHwRef is None
    assert loadedExp.memberExp.hwRef is None
    assert loadedExp.memberExp.sneakyHwRef is None

    # Attributes starting with __ are not there at all
    with pytest.raises(AttributeError):
        _ = loadedExp.hidden


    ##### Pickling tough stuff
    foo = SomethingWithHardStuff()

    loadedFoo = foo.copy()

    for attr in ['x', 'y', 'z']:
        if not np.all(getattr(foo, attr) == getattr(loadedFoo, attr)):
            print(attr)
            assert False
    for iFun in range(len(foo.someFuncs)):
        assert loadedFoo.someFunc[iFun](2) == foo.someFunc[iFun](2)
    assert loadedFoo.aSpectrum == foo.aSpectrum




