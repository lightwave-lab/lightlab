import lightlab.instruments as i
from lightlab.instruments.state import InstrumentException
import pytest

def test_spectrum():
    # Init Instruments
    installed = i.getInstalled()
    assert 'OSA' in installed

    available = i.getAvailable()
    assert 'OSA' in available

    # Test without wavelength
    i.spectrum()

    # Test with wavelength
    wlRange = [1533, 1550]
    nm, dbm = i.spectrum(wlRange)
    assert nm[0] == wlRange[0]
    assert nm[-1] == wlRange[-1]

    # Test with invalid avgCnt
    with pytest.raises(ArithmeticError):
        i.spectrum(wlRange, -5)


#def test_tls():
#    # Init Instruments
#    installed = i.getInstalled()
#    assert 'OSA' in installed
#
#    available = i.getAvailable()
#    assert 'OSA' in available
#
#    # Run with nothing
#    i.tlsToggle()
#
#    # Make sure it's off
#    i.tlsToggle(False)
