import lightlab.calibrate as cal
import lightlab.util.data as data
import numpy as np
import pytest

''' This is a control test. It has two mirrored models of a microring filter bank.
    One model is used as a simulator, the other as a controller.
    The controller takes a command, tunes the simulator, and the output is observed.

    What is tested:
    - The ability of the Mrrs and FilterBank classes to invert (i.e. control)
        via cal.FilterBank.setPeakWl()
    - Peak wavelength picking from spectra
        via data.findResonanceFeatures()
    - Tune/measure interface of a "hidden" virtual device
        via cal.FilterBank.setDictTuning() and cal.FilterBank.measureSpectrum()
'''

def controlError(vBank, cBank, target):
    ''' Returns a scalar error representing accuracy of controlling to target wavelengths.
        :param vBank: the virtual FilterBank that is serving as the actual device/simulator
        :param cBank: the control FilterBank that generates the control rule, given
        :param target: an array of target wavelengths where we want the resonances
    '''
    cBank.setPeakWl(target)
    vBank.setDictTuning(cBank.getDictTuning()) # move that over to the virtual
    virtSpect = vBank.measureSpectrum()[0]
    # Use peak picking to pull out resonance locations
    res = virtSpect.findResonanceFeatures(expectedCnt=cBank.nEl, isPeak=True)
    wlsAbs = np.sort([r.lam for r in res])
    tAbs = cBank.bias.debiasWavelength(target)
    diff = wlsAbs - tAbs
    err = data.rms(diff)
    return err

def test_mrrController():
    # Initialize a model of a virtual FilterBank
    nRings = 4
    virtBank = cal.FilterBank.default(nRings)
    # Change some of the thermal properties
    virtBank.thrm.coefs += .5 * np.eye(nRings, k=1) + .1 * np.eye(nRings, k=2)
    virtBank.thrm.coefs += .3 * np.eye(nRings, k=-1) + .2 * np.eye(nRings, k=-2)
    # Copy its properties to a controller. Guarantees perfect calibration.
    # (In real life this is cheating)
    ctrlBank = virtBank.copy() # a model used as a controller
    ctrlBankBad = cal.FilterBank.default(nRings) # an improperly calibrated controller

    # Set up a wavelength control trial
    allowedError = .1
    nTrials = 100
    targets = 1.0 * np.random.rand(nTrials, nRings)
    errorGood = np.zeros(nTrials)
    errorBad = np.zeros(nTrials)

    for i,t in enumerate(targets):
        errorGood[i] = controlError(virtBank, ctrlBank, t)
        errorBad[i] = controlError(virtBank, ctrlBankBad, t)

    # Check that the good controller always works,
    # and the bad controller sometimes fails
    assert all(errorGood < allowedError)
    assert any(errorBad > allowedError)

    # Done!
