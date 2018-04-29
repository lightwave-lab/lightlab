''' What's the deal with Drivers, AbstractDrivers, Instruments,
    VirtualInstruments, and DualInstruments? ``lightlab`` has a lot
    of power in virtualization. It is not just a bag of drivers.

    Virtualization allows as-rigorous-as-possible and as-true-to-life-as-possible
    dev/debug of complex experimental procedures. It allows for unit-testing.
    It catches many errors at compile-time, instead of run-time.

    We strongly recommend learning and using these features,
    but they are complicated, necessarily.

    This test is documentation by example.
    It covers
        * writing ``Instrument`` abstract interfaces
        * writing concrete implementations and abstract implementations
        * explanation of what is meant by "reality" vs. "virtual reality"
        * simple simulation, virtualization, and dual-ization
        * unit-testing a complex experimental procedure

    Along with commentary about the rationale for setting it up this way.

    Attributes:
        NAIL (int): global variable representing real life outside of the classes and tests
'''

import pytest
from contextlib import contextmanager

from lightlab.laboratory.instruments import Instrument
from lightlab.equipment.visa_bases import IncompleteClass, VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import AbstractDriver
from lightlab.laboratory.virtualization import VirtualInstrument, DualInstrument, Virtualizable, VirtualizationError


''' TESTING FRAMEWORK

    These module variables are, for the sake of this test,
    an emulation of "reality" outside of the library.

    They can be seen only by the testing framework
    and modified only by the low-level drivers.
'''
NAIL = 0

#: Some condition that must be active when acting,
#: but we would like it to be on as little as possible.

#: A real example is a Keithley enable switch:
#: Leaving the current on indefinitely can wear out devices.

#: In this case, we should put hammers down unless actively hammering.
#: They are heavy.
IN_HAND = False

@contextmanager
def checkHits(N=1):
    ''' Put "reality" in a consistent beginning state.
        Check at end that ``NAIL`` has hit (which involves picking up first)
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
    ''' An Instrument interface that defines essential methods
    '''
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

    ``HammerImplementation`` is really just shared code
    and should never be instantiated on its own.
'''
class HammerImplementation(AbstractDriver):
    ''' An abstraction of how some real Hammers are implemented
    '''
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
    When you instantiate a driver, you get the abstract Instrument class.
    This greatly eases lab state management
'''
class Picard_0811(VISAInstrumentDriver, HammerImplementation):
    ''' One type of Hammer '''
    instrument_category = Hammer

# class Stanley_51_624(Picard_0811):  # This class declaration works, but it is conceptually misleading
class Stanley_51_624(VISAInstrumentDriver, HammerImplementation):
    ''' Another type of hammer

        Stanley_51_624 is not at all a Picard_0811, so it should not inherit it.
        That's why there are abstract drivers.
    '''
    instrument_category = ClawHammer

    def pull(self):
        global NAIL
        if IN_HAND:
            NAIL -= 1

class Picard_0812(Picard_0811):
    ''' This is almost the same thing, so it is conceptually ok to inherit from the other driver '''
    pass

def test_specialInitialization():
    ''' When a :py:class:`~lightlab.equipment.visa_bases.VISAInstrumentDriver`
        is initialized, it should return an :py:class:`~lightlab.laboratory.instruments.Instrument`.
    '''
    hammer = Picard_0811(address='Hand')
    assert type(hammer) is Hammer

def test_realLife():
    ''' This is a straightforward way to hit a nail
    '''
    hammer = Picard_0811(address='Hand')
    with checkHits(1):
        hammer.pickUp()
        hammer.hit()
        hammer.putDown()
    # Same thing but with context management
    with checkHits(1):
        with hammer.warmedUp():
            hammer.hit()


''' SIMULATION

    VirtualNail is just a simulator. VirtualHammer is special
    because it is meant to appear to other code as an actual Hammer (same interface, same behavior).
    This is not enforced, but there are warnings if it does not.

    In this case, state is held in the simulator because the system is hysteretic.
    It is often instead possible to keep state in the virtual instrument.
    Avoid maintaining extraneous/redundant state like the plague.

    The VirtualInstrument is allowed to know what goes on inside the simulator,
    i.e. by calling viReference.state. A user procedure should not be directly
    accessing a simulation because that does not correspond to real life.
    This is not enforced.
'''
class VirtualNail(object):
    ''' A simulation of a nail
    '''
    state = 0

class VirtualHammer(VirtualInstrument):
    ''' A virtual instrument with the same interface as its real counterpart.
        It is tied to a simulator, in this case :py:class:`VirtualNail`.
    '''
    def __init__(self, viReference):
        self.viReference = viReference

    def hit(self):
        self.viReference.state += 1

    def pull(self):
        self.viReference.state -= 1

# Testing framework
@contextmanager
def checkVirtualHits(virtualNail, N=1):
    ''' Put "virtual reality" in a consistent beginning state.

        There is no mention of IN_HAND because we don't care about modeling it.
    '''
    virtualNail.state = 0
    yield  # user code runs
    assert virtualNail.state == N

def test_simulator():
    ''' Straightforward hitting a simulated nail
    '''
    viDevice = VirtualNail()
    inst = VirtualHammer(viDevice)
    with checkVirtualHits(viDevice, 1):
        inst.hit()


''' VIRTUALIZATION

    Making a correspondance between virtual reality and reality
'''
def test_dualized():
    ''' Tie together a real hammer with a virtual hammer.
        Run the same simple procedure on both.
    '''
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


''' PROCEDURES and SYNCHRONIZATION

    Real experiments involve multiple instruments - they must be synced up -
    and complex sequences of actions. Those procedures can now be unit-tested.

    What this means is that every procedure can be tested so changes don't
    break them. This is an alternative to setting up/striking a bunch of different
    experiments to make sure it still works every time a number gets changed.

    It is of course only as good as your simulator can correspond to reality.
'''
def complicatedProcedure_resultingIn3hits(hammer1, hammer2):
    ''' Two hammers hitting one nail. hammer2 must be a ClawHammer '''
    hammer1.hit()
    hammer2.hit()
    hammer2.hit()
    hammer2.pull()
    hammer1.hit()

def test_dualWeilding():
    ''' Tie together two virtual-real pairs, and synchronize the
        virtual state of the two together.

        Repeat a complex procedure in virtual and real
    '''
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

    with pytest.raises(VirtualizationError):
        complicatedProcedure_resultingIn3hits(dual1, dual2)

