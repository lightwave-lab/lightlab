from . import VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import TekScopeAbstract


class Tektronix_DSA8300_Oscope(VISAInstrumentDriver, TekScopeAbstract):
    ''' Sampling scope.
        See abstract driver for description

        `Manual <http://www.tek.com/download?n=975655&f=190886&u=http%3A%2F%2Fdownload.tek.com%2Fsecure%2FDifferential-Channel-Alignment-Application-Online-Help.pdf%3Fnvb%3D20170404035703%26amp%3Bnva%3D20170404041203%26amp%3Btoken%3D0ccdfecc3859114d89c36>`__
    '''
    totalChans = 8
    __recLenParam = 'MAIN:RECORDLENGTH'
    __clearBeforeAcquire = True
    __measurementSourceParam = 'SOURCE1:WFM'
    __runModeParam = 'ACQUIRE:STOPAFTER:MODE'
    __runModeSingleShot = 'CONDITION'
    __yScaleParam = 'YSCALE'

    def __setupSingleShot(self, isSampling, forcing=False):
        ''' Additional DSA things needed to put it in the right mode.
            If it is not sampling, the trigger source should always be external
        '''
        super().__setupSingleShot(isSampling, forcing)
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
        self.setConfigParam('HIS:ENAB', '')
        self.setConfigParam('HIS:MOD', 'VERTICAL')
        self.setConfigParam('HIS:SOU', chan)

        forcing = True
        self.__setupSingleShot(isSampling=True, forcing=forcing)
        self.setConfigParam('ACQUIRE:STOPAFTER:COUNT', nWfms, forceHardware=forcing)

        # Gathering
        with self.tempConfig('TRIGGER:SOURCE',
                'FREERUN' if untriggered else 'EXTDIRECT'):
            self.__triggerAcquire()

        # Transfer data
        stdDev = self.query('HIS:STAT:STD?')
        sigmaStats = np.zeros(3)
        for iSigma in range(3):
            sigmaStats[iSigma] = self.query('HIS:STAT:SIGMA{}?'.format(iSigma+1))
        return stdDev, sigmaStats


Tektronix_CSA8000_CAS = Tektronix_DSA8300_Oscope
''' Communication analyzer scope
    @LightwaveLab: Is this different from the DSA?
    Maybe the DSA was the old one that got retired, but they are actually the same...

    Not necessarily tested with the new abstract driver
'''


class Tektronix_TDS6154C_Oscope(VISAInstrumentDriver, TekScopeAbstract):
    ''' Real time scope.
        See abstract driver for description.

        `Manual <http://www.tek.com/sites/tek.com/files/media/media/resources/55W_14873_9.pdf>`__
    '''
    totalChans = 4
    # Similar to the DSA, except
    __recLenParam = 'HORIZONTAL:RECORDLENGTH'  # this is different from DSA
    __clearBeforeAcquire = True
    __measurementSourceParam = 'SOURCE1:WFM'
    __runModeParam = 'ACQUIRE:STOPAFTER:MODE'
    __runModeSingleShot = 'CONDITION'
    __yScaleParam = 'YMULT'                    # this is different from DSA

    def __setupSingleShot(self, isSampling, forcing=False):
        ''' Additional DSA things needed to put it in the right mode.
            If it is not sampling, the trigger source should always be external
        '''
        super().__setupSingleShot(isSampling, forcing)
        self.setConfigParam('ACQUIRE:STOPAFTER:CONDITION',
                            'ACQWFMS' if isSampling else'AVGCOMP',
                            forceHardware=forcing)
        if isSampling:
            self.setConfigParam('ACQUIRE:STOPAFTER:COUNT', '1', forceHardware=forcing)
        if not isSampling:
            self.setConfigParam('TRIGGER:SOURCE', 'EXTDIRECT', forceHardware=forcing)


class Tektronix_DPO4034_Oscope(VISAInstrumentDriver, TekScopeAbstract):
    ''' Slow DPO scope.
        See abstract driver for description

        `Manual <http://websrv.mece.ualberta.ca/electrowiki/images/8/8b/MSO4054_Programmer_Manual.pdf>`__
    '''
    totalChans = 4
    __recLenParam = 'HORIZONTAL:RECORDLENGTH'
    __clearBeforeAcquire = False
    __measurementSourceParam = 'SOURCE1'
    __runModeParam = 'ACQUIRE:STOPAFTER'
    __runModeSingleShot = 'SEQUENCE'
    __yScaleParam = 'YMULT'


class Tektronix_DPO4032_Oscope(Tektronix_DPO4034_Oscope):
    totalChans = 2


