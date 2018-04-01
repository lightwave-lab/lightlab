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
from lightlab import logger

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

    @hidden.setter
    def hidden(self, newVal):
        self.__hidden = newVal

def test_Simple():
    original = SomeVirtualizedExperiment('myName')
    copied = original.copy()
    assert original.name == copied.name


def genExp():
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
    return exp


def validate(loaded):
    ''' loaded is something either copied or loaded from exp

        Checks that behavior of pickling is correct
    '''
    oldExp = genExp()
    assert loaded is not oldExp
    assert loaded.name == oldExp.name

    # Complicated linkages within members are maintained
    newA = loaded.port
    assert newA is not oldExp.port
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
    global INSTANTIATION_COUNTER
    INSTANTIATION_COUNTER = 0
    loadedExp = genExp().copy() # does the same thing as save/load
    assert INSTANTIATION_COUNTER == 2
    validate(loadedExp)
    # __init__ is not called again


@pytest.fixture(scope='module')
def expJSONfile():
    genExp().save(filename)
    yield filename
    os.remove(filename)


def test_JSONpickleableWithFile(expJSONfile):
    global INSTANTIATION_COUNTER
    INSTANTIATION_COUNTER = 0
    loadedExp = SomeVirtualizedExperiment.load(expJSONfile)
    assert INSTANTIATION_COUNTER == 0  # __init__ is not called again
    validate(loadedExp)


'''
    =========== Harder =============
'''


# Functions and arrays are usually hard to pickle
def bar(s):
    return s + 42

bar2 = lambda s: s + 43


class SomethingWithHardStuff(JSONpickleable):
    def __init__(self):
        self.name = 'myName'
        self.wArr = np.array([])           # empty
        self.xArr = np.array(1)            # scalar
        self.yArr = np.linspace(0, 1, 10)  # 1D
        self.zArr = np.zeros((5,5))    # 2D

        self.vFun = bar              # regular
        self.wFun = bar2             # lambda
        self.xFun = self.bar3        # bound method
        self.yFun = type(self).bar3  # unbound method
        self.zFun = np.ones      # out of scope

        self.aSpectrum = Spectrum([1,2], [3,4])

    def bar3(self, s):
        return s + 44


@pytest.fixture(scope='module')
def hardFile():
    filename = 'hardJSON.json'
    SomethingWithHardStuff().save(filename)
    yield filename
    os.remove(filename)


def test_JSONpickleableHard(hardFile):
    import pdb; pdb.set_trace()
    loaded = SomethingWithHardStuff.load(hardFile)
    original = SomethingWithHardStuff()

    for arrAttr in ['wArr', 'xArr', 'yArr', 'zArr']:
        if not np.all(getattr(original, arrAttr) == getattr(loaded, arrAttr)):
            logger.error(arrAttr)
            assert False
    for funAttr in ['vFun', 'wFun', 'xFun']:
        assert getattr(original, funAttr)(10) == getattr(loaded, funAttr)(10)
    logger.warning(original.yFun(original, 10))
    assert original.yFun(original, 10) == loaded.yFun(loaded, 10)
    assert np.all(original.zFun(10) == loaded.zFun(10))
    assert loaded.aSpectrum == loaded.aSpectrum


