''' What's the deal with Drivers, AbstractDrivers, Instruments,
    VirtualInstruments, and DualInstruments? ``lightlab`` has a lot
    of power in virtualization. It is not just a bag of drivers.

    Virtualization allows as-rigorous-as-possible and as-true-to-life-as-possible
    dev/debug of complex experimental procedures. It allows for unit-testing.
    It catches many errors at compile-time, instead of run-time.

    We strongly recommend learning and using these features,
    but they can get complicated.

    This test is documentation by example for all these features.
    It covers
        * writing Instrument interfaces and implementations.
        * explanation of what is meant by "reality" vs. "virtual reality"
        * simple simulation and virtualization.
        * complex procedure dualization
'''

import pytest
from contextlib import contextmanager

from lightlab.laboratory.instruments import Instrument
from lightlab.equipment.visa_bases import IncompleteClass, VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import AbstractDriver
from lightlab.laboratory.virtualization import VirtualInstrument, DualInstrument, Virtualizable


''' TESTING FRAMEWORK

    These module variables are "real life" outside of the library.
    They can be seen only by the testing framework
    and modified only by the low-level drivers.
'''
NAIL = 0

''' Some condition that must be active when actually recording,
    but we would like it to be on as little as possible.

    For example, a Keithley enable switch: Leaving the current
    on indefinitely can wear out devices.

    In this case, we should put hammers down unless actively hammering.
    They are heavy.
'''
IN_HAND = False

@contextmanager
def checkHits(N=1):
    ''' Put "reality" in a consistent beginning state.
        Check at end that NAIL has hit (which involves picking up first)
        and that the hammer was put down afterwards
    '''
    global NAIL, IN_HAND
    NAIL = 0
    IN_HAND = False
    yield  # user code runs
    assert NAIL == N
    assert not IN_HAND


''' INSTRUMENT INTERFACES

    They declare in an abstract way what it means to be a hammer.
    This is enforced. A driver claiming to be a Hammer must implement the essentials
'''
class Hammer(Instrument):
    essentialMethods = Instrument.essentialMethods + ['hit', 'pickUp', 'putDown']

    def hardware_warmup(self):
        self.pickUp()

    def hardware_cooldown(self):
        self.putDown()

class ClawHammer(Hammer):
    essentialMethods = Hammer.essentialMethods + ['pull']

def test_badDriver():
    with pytest.raises(IncompleteClass):
        class SAE_9312(VISAInstrumentDriver):  # This is a wrench!
            instrument_category = Hammer
            def tighten(self): pass


''' ABSTRACT DRIVER

    There is one driver per instrument model, but they are often similar.
    Copied code is very difficult to maintain,
    so we use 1. abstraction and/or 2. inheritance.

    HammerImplementation is just shared code
    and should never be instantiated on its own.
'''
class HammerImplementation(AbstractDriver):
    # def __init__(self, **kwargs):
    #     assert hasattr(self, 'open')
    #     super().__init__(**kwargs)

    def hit(self):
        global NAIL
        if IN_HAND:
            NAIL += 1

    def pickUp(self):
        global IN_HAND
        IN_HAND = True

    def putDown(self):
        global IN_HAND
        IN_HAND = False


''' DRIVERS

    They are the only things that get to touch the module variables.
'''
class Picard_0811(VISAInstrumentDriver, HammerImplementation):
    instrument_category = Hammer

# class Stanley_51_624(Picard_0811):  # This class declaration works, but it is conceptually misleading
class Stanley_51_624(VISAInstrumentDriver, HammerImplementation):
    ''' Stanley_51_624 is not at all a Picard_0811, so it should not inherit it.
        That's why there are abstract drivers.
    '''
    instrument_category = ClawHammer

    def pull(self):
        global NAIL
        if IN_HAND:
            NAIL -= 1

''' This is almost the same thing, so it is conceptually ok to inherit from the other driver '''
class Picard_0812(Picard_0811): pass

def test_realLife():
    ''' This is a straightforward way to hit a nail
    '''
    inst = Stanley_51_624(address='Hand')
    with checkHits(1):
        inst.pickUp()
        inst.hit()
        inst.putDown()
    # Same thing but with context management
    with checkHits(1):
        with inst.warmedUp():
            inst.hit()


''' SIMULATION

    VirtualNail is just a simulator. VirtualHammer is special
    because it is meant to appear to other code as an actual Hammer (same interface, same behavior)

    In this case, state is held in the simulator because the system is hysteretic.
    It is often instead possible to keep state in the virtual instrument.
    Avoid maintaining extraneous/redundant state like the plague.
'''
class VirtualNail(object):
    state = 0

class VirtualHammer(VirtualInstrument):
    def __init__(self, viReference):
        self.viReference = viReference

    def hit(self):
        ''' The virtual instrument is allowed to know what goes on inside the simulator.
        '''
        self.viReference.state += 1

    def pull(self):
        self.viReference.state -= 1

@contextmanager
def checkVirtualHits(virtualNail, N=1):
    ''' Put "virtual reality" in a consistent beginning state.

        There is no mention of IN_HAND because we don't care about modeling it.
    '''
    virtualNail.state = 0
    yield  # user code runs
    assert virtualNail.state == N


def test_simulator():
    viDevice = VirtualNail()
    inst = VirtualHammer(viDevice)
    with checkVirtualHits(viDevice, 1):
        inst.hit()


''' VIRTUALIZATION

    Making a correspondance between virtual reality and reality
'''
def test_dualized():
    viDevice = VirtualNail()
    viInst = VirtualHammer(viDevice)
    hwInst = Stanley_51_624(address='Hand')
    dual = DualInstrument(real_obj=hwInst, virt_obj=viInst)

    with checkVirtualHits(viDevice, 1):
        with dual.asVirtual():
            dual.hit()  # Notice how the user code is exactly the same

    with checkHits(1):
        with dual.asReal():
            dual.hit()  # Notice how the user code is exactly the same


''' SYNCHRONIZATION

    Real experiments involve multiple instruments and complex sequences of actions
'''
def complicatedProcedure_resultingIn3hits(hammer1, hammer2):
    hammer1.hit()
    hammer2.hit()
    hammer2.hit()
    hammer2.pull()
    hammer1.hit()

def test_dualWeilding():
    viDevice = VirtualNail()

    hw1 = Picard_0812(address='Left hand')
    vi1 = VirtualHammer(viDevice)
    dual1 = DualInstrument(real_obj=hw1, virt_obj=vi1)

    hw2 = Stanley_51_624(address='Right hand')
    vi2 = VirtualHammer(viDevice)
    dual2 = DualInstrument(real_obj=hw2, virt_obj=vi2)

    master = Virtualizable()
    master.synchronize(dual1, dual2)

    with checkVirtualHits(viDevice, 3):
        with master.asVirtual():
            complicatedProcedure_resultingIn3hits(dual1, dual2)
    with checkHits(3):
        with master.asReal():
            complicatedProcedure_resultingIn3hits(dual1, dual2)

