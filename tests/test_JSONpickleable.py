''' Pretty advanced saving and loading

    Complicated linkages within members are maintained

    Attributes starting with __ are not there at all

    Some attributes are not picked, but still exist as None
        They can be specified in ``notPickled`` or if they are a subclass of VISAObject

    Remember that loading does not call __init__, so watch out for side effects.
        This is the primary reason that VISAObjects are not allowed
        to be pickled: they all have side effects in the real world.
'''
import pytest
import lightlab.util.io as io
from lightlab.util.io import JSONpickleable
from pathlib import Path
from lightlab.equipment.visa_bases import VISAObject
import numpy as np
from lightlab.util.data import Spectrum
import os
from lightlab import logger

INSTANTIATION_COUNTER = 0
io.fileDir = Path('.').resolve()
filename = 'testJson.json'

# Helper definitions
class SomeInstrument(VISAObject):
    pass


class Port(object):
    connectedTo = None

    def portFun(self, s):
        return s + 1


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

        # self.klass = Port

        self.f_inModule = bar             # regular
        self.f_lambda = bar2              # lambda
        # self.f_bound = self.bar3        # bound method -- will recurse
        self.f_bound = Port().portFun     # bound method
        # self.f_unbound = type(self).bar3  # unbound method (shold work, does not)
        self.f_library = np.ones          # external

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
    loaded = SomethingWithHardStuff.load(hardFile)
    original = SomethingWithHardStuff()

    for arrAttr in ['wArr', 'xArr', 'yArr', 'zArr']:
        if not np.all(getattr(original, arrAttr) == getattr(loaded, arrAttr)):
            logger.error(arrAttr)
            assert False
    assert loaded.aSpectrum == loaded.aSpectrum

    for funAttr in ['f_inModule', 'f_lambda', 'f_bound']:
        assert getattr(original, funAttr)(10) == getattr(loaded, funAttr)(10)
    # assert original.f_unbound(loaded, 10) == loaded.f_unbound(loaded, 10)
    assert np.all(original.f_library(10) == loaded.f_library(10))


