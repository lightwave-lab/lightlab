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
from lightlab.equipment.visa_bases import VISAObject
import numpy as np
from lightlab.util.data import Spectrum
import os

INSTANTIATION_COUNTER = 0
filename = 'testJson.json'

# Helper definitions
class SomeInstrument(VISAObject):
    pass


class Port(object):
    connectedTo = None


class SomeVirtualizedExperiment(JSONpickleable):
    ''' Contains the following examples
            * name: regular attribute
            * hwRef: explicitly not pickled (goes in as None)
            * __hidden: skipped entirely by pickler

        Later, we will also use dynamic assignment to add an undeclared attribute
    '''
    hwRef = None
    __hidden = 'set within object'
    notPickled = ['hwRef']

    def __init__(self, name=None):
        self.name = name

        # This is an example of a side effect
        global INSTANTIATION_COUNTER
        INSTANTIATION_COUNTER += 1

    @property
    def hidden(self):
        return self.__hidden

    @hidden.setter
    def hidden(self, newVal):
        self.__hidden = newVal


# Make exp, the global example of a JSONpickleable object
portA = Port()
portB = Port()
portA.connectedTo = portB
portB.connectedTo = portA

subExp = SomeVirtualizedExperiment('Cousin IT')
# assert INSTANTIATION_COUNTER == 1
subExp.hwRef = 10
subExp.port = portB
subExp.sneakyHwRef = SomeInstrument()

exp = SomeVirtualizedExperiment('Uncle Tommy')
# assert INSTANTIATION_COUNTER == 2
exp.hwRef = 20
exp.sneakyHwRef = VISAObject()
exp.port = portA
exp.memberExp = subExp
exp.hidden = 'Now it has been set'


def validate(loaded):
    ''' loaded is something either copied or loaded from exp

        Checks that behavior of pickling is correct
    '''
    assert loaded is not exp
    assert loaded.name == exp.name

    # Complicated linkages within members are maintained
    newA = loaded.port
    assert newA is not portA
    newB = loaded.memberExp.port
    assert newA is newB.connectedTo

    # Some attributes were not pickled, but still exist as None
    assert loaded.hwRef is None
    assert loaded.sneakyHwRef is None
    assert loaded.memberExp.hwRef is None
    assert loaded.memberExp.sneakyHwRef is None

    # Attributes starting with __ are not there at all
    with pytest.raises(AttributeError):
        _ = loaded.hidden


def test_JSONpickleableWithCopy():
    loadedExp = exp.copy() # does the same thing as save/load
    validate(loadedExp)
    # __init__ is not called again
    assert INSTANTIATION_COUNTER == 2


@pytest.fixture(scope='module')
def expJSONed():
    exp.save(filename)
    yield filename
    os.remove(filename)


def test_JSONpickleableWithFile(expJSONed):
    import pdb; pdb.set_trace()
    loadedExp = SomeVirtualizedExperiment.load(filename)
    validate(loadedExp)
    # __init__ is not called again
    assert INSTANTIATION_COUNTER == 2


'''
    =========== Harder =============
'''


# Functions and arrays are usually hard to pickle
def bar(s):
    return s + 42

bar2 = lambda s: s + 42


class SomethingWithHardStuff(JSONpickleable):
    def __init__(self):
        self.wArr = np.array([])           # empty
        self.xArr = np.array(1)            # scalar
        self.yArr = np.linspace(0, 1, 10)  # 1D
        self.zArr = np.random.rand(5,5)    # 2D
        self.someFuncs = (bar, bar2, self.bar3)
        self.aSpectrum = Spectrum([1,2], [3,4])

    def bar3(self):
        return True


def terrst_JSONpickleableHard():
    ##### Pickling tough stuff
    foo = SomethingWithHardStuff()
    loadedFoo = foo.copy()

    for attr in ['wArr', 'xArr', 'yArr', 'zArr']:
        if not np.all(getattr(foo, attr) == getattr(loadedFoo, attr)):
            print(attr)
            assert False
    for iFun in range(len(foo.someFuncs)):
        assert loadedFoo.someFunc[iFun](2) == foo.someFunc[iFun](2) # this is a problem
    assert loadedFoo.aSpectrum == foo.aSpectrum


