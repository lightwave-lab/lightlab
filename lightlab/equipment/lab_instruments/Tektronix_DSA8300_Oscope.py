from . import VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import TekScopeAbstract
from lightlab.laboratory.instruments import Oscilloscope

import numpy as np


class Tektronix_DSA8300_Oscope(VISAInstrumentDriver, TekScopeAbstract):
    ''' Sampling scope.
        See abstract driver for description

        `Manual <http://www.tek.com/download?n=975655&f=190886&u=http%3A%2F%2Fdownload.tek.com%2Fsecure%2FDifferential-Channel-Alignment-Application-Online-Help.pdf%3Fnvb%3D20170404035703%26amp%3Bnva%3D20170404041203%26amp%3Btoken%3D0ccdfecc3859114d89c36>`__

        Usage: :any:`/ipynbs/Hardware/Oscilloscope.ipynb`

    '''
    instrument_category = Oscilloscope

    totalChans = 8
    _recLenParam = 'HORIZONTAL:MAIN:RECORDLENGTH'
    _clearBeforeAcquire = True
    _measurementSourceParam = 'SOURCE1:WFM'
    _runModeParam = 'ACQUIRE:STOPAFTER:MODE'
    _runModeSingleShot = 'CONDITION'
    _yScaleParam = 'YSCALE'

    def __init__(self, name='The DSA scope', address=None, **kwargs):
        VISAInstrumentDriver.__init__(self, name=name, address=address, **kwargs)
        TekScopeAbstract.__init__(self)

    def _setupSingleShot(self, isSampling, forcing=False):
        ''' Additional DSA things needed to put it in the right mode.
            If it is not sampling, the trigger source should always be external
        '''
        super()._setupSingleShot(isSampling, forcing)
        self.setConfigParam('ACQUIRE:STOPAFTER:CONDITION',
                            'ACQWFMS' if isSampling else'AVGCOMP',
                            forceHardware=forcing)
        if isSampling:
            self.setConfigParam('ACQUIRE:STOPAFTER:COUNT', '1', forceHardware=forcing)
        if not isSampling:
            self.setConfigParam('TRIGGER:SOURCE', 'EXTDIRECT', forceHardware=forcing)

    def histogramStats(self, chan, nWfms=3, untriggered=False):
        ''' Samples for a bunch of waveforms. Instead of sending all of that data,
            It uses the scope histogram. It returns the percentage within a given sigma width

            Returns:
                (float): standard deviation in volts
                (ndarray): proportion of points within [1, 2, 3] stddevs of mean
        '''
        # Configuration
        self.setConfigParam('HIS:BOXP', '0, 0, 99.9, 99.9')
        self.setConfigParam('HIS:ENAB', '1')
        self.setConfigParam('HIS:MOD', 'VERTICAL')
        self.setConfigParam('HIS:SOU', chan)

        forcing = True
        self._setupSingleShot(isSampling=True, forcing=forcing)
        self.setConfigParam('ACQUIRE:STOPAFTER:COUNT', nWfms, forceHardware=forcing)

        # Gathering
        with self.tempConfig('TRIGGER:SOURCE',
                             'FREERUN' if untriggered else 'EXTDIRECT'):
            self._triggerAcquire()

        # Transfer data
        stdDev = self.query('HIS:STAT:STD?')
        sigmaStats = np.zeros(3)
        for iSigma in range(3):
            sigmaStats[iSigma] = self.query('HIS:STAT:SIGMA{}?'.format(iSigma + 1))
        return stdDev, sigmaStats
