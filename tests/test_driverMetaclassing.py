''' Driver metaclassing allows two powerful features to connect
    a ``VISAInstrumentDriver`` to an ``Instrument`` with the attribute: ``instrument_category``.

    1. ``Instrument`` is initialized and returned by calling a ``VISAInstrumentDriver`` class,
    as if you were initializing that ``VISAInstrumentDriver`
        * Enables better Instrument/Driver init argument handling
        * Better separation of Instrument-level/Driver-level attribute access
        * Unambiguous pickling of these two levels

    2. Enforces that ``VISAInstrumentDriver``  satisfies
    the interface of its corresponding ``Instrument``.
'''
import pytest
from mock import patch

from lightlab.equipment.visa_bases import VISAInstrumentDriver, IncompleteClass
from lightlab.equipment.lab_instruments import HP_8152A_PM
from lightlab.laboratory.instruments import PowerMeter


def test_bad_driver():
    # Catches incomplete API at class time
    with pytest.raises(IncompleteClass):
        class Delinquent_PM(VISAInstrumentDriver):
            instrument_category = PowerMeter

            def powerLin(self): pass
            # def powerDbm(self): pass

def test_driver_init():
    ''' Initialization can occur via Instrument or VISAInstrumentDriver.
        Both will return an Instrument
    '''
    # Old style still works
    pm_old = PowerMeter(_driver_class=HP_8152A_PM, name='a PM',
                    address='NULL', extra='foolio', tempSess=False)
    # New style (recommended)
    pm_new = HP_8152A_PM(name='a PM', address='NULL', extra='foolio', tempSess=False)
    for pm in [pm_old, pm_new]:
        assert pm.__class__ == PowerMeter  # not SourceMeter or HP_8152A_PM
        assert pm._driver_class == HP_8152A_PM
        assert pm.extra == 'foolio'

    # Old style fails to initialize the driver with correct options
    with pytest.raises(AssertionError):
        assert pm_old.driver.tempSess is False
    assert pm.driver.tempSess is False

    # `tempSess` is a driver-level attribute, not seen at Instrument
    with pytest.raises(AttributeError):
        pm.tempSess
    # `extra` is not in the driver's namespace, so it was kept in Instrument
    with pytest.raises(AttributeError):
        pm.driver.extra


def test_change_of_address():
    ''' Change of address should kill the connection and change driver's address
    '''
    pm = HP_8152A_PM(name='a PM', address='NULL', tempSess=False)

    def open_fake(self):
        self.mbSession = 'opened'

    def close_fake(self):
        self._close_called = True

    with patch.object(HP_8152A_PM, 'open', open_fake), \
            patch.object(HP_8152A_PM, 'close', close_fake):
        driver = pm.driver
        driver.open()
        assert driver.mbSession == 'opened'
        pm.address = 'new_address'
        assert pm.driver is driver
        assert driver._close_called is True
        assert pm.driver.address == pm.address


from lightlab.laboratory.instruments import Oscilloscope


def test_optionals():
    class Driver1(VISAInstrumentDriver):
        instrument_category = Oscilloscope

        def acquire(self): pass

        def run(self): pass

        def wfmDb(self): pass

        def notInInterface(self): pass

    class Driver2(Driver1):

        def histogramStats(self): pass

    d1 = Driver1()
    d2 = Driver2()
    d1.acquire()
    with pytest.raises(AttributeError):
        d1.histogramStats()
    d2.histogramStats()
    with pytest.raises(AttributeError):
        d1.notInInterface()
    d1.driver.notInInterface()
    assert 'histogramStats' not in dir(d1)
    assert 'histogramStats' in dir(d2)
