import lightlab.instruments as i
from lightlab.instruments.state import InstrumentException
import pytest
import time

def test_currentTune():
    # Init Instruments
    installed = i.getInstalled()
    assert 'CurrentSources' in installed

    available = i.getAvailable()
    assert 'CurrentSources' in available

    channels = (0, 1, 2)

    with pytest.raises(InstrumentException):
        i.reserveCurrentChan(channels, "bad token")

    token = i.reserveCurrentChan(channels)


    # Reserve Bad Channels
    with pytest.raises(InstrumentException):
        i.reserveCurrentChan([17], token)

    # Double-Reserve Channels
    with pytest.raises(InstrumentException):
        i.reserveCurrentChan(channels)

    badDict = dict()
    badDict[3] = 1

    goodDict = dict()
    goodDict[2] = 1
    goodDict[1] = 1

    # Try to set un-reserved Channel
    with pytest.raises(InstrumentException):
        i.setCurrentChanTuning(badDict, token)

    # Good tuning
    i.setCurrentChanTuning(goodDict, token)

    goodDict[1] = 0
    goodDict[2] = 0

    time.sleep(1)

    # Turn Off Currents
    i.setCurrentChanTuning(goodDict, token)

    # Unreserve Token
    i.unReserveCurrentChan(token)

    # Should not be able to set channels
    with pytest.raises(InstrumentException):
        i.setCurrentChanTuning(goodDict, token)


    # Done!