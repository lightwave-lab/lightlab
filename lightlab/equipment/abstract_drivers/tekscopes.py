import numpy as np
from pathlib import Path

from lightlab import logger
from lightlab.util.data import Waveform, FunctionBundle
from lightlab.equipment.lab_instruments.configure import Configurable

class TekScopeAbstract(Configurable):
    ''' Redo this doctring

    General class for either scope
    Communication is slightly different for the type of scope, but user doesn't care
    Note: this will not setup or adjust unless explicitly told to

    TEKTRONIX,DPO4034:
        Slow scope with 4 channels [http://websrv.mece.ualberta.ca/electrowiki/images/8/8b/MSO4054_Programmer_Manual.pdf]

    TEKTRONIX,DPO4032:
        Slow scope with 2 channels [http://websrv.mece.ualberta.ca/electrowiki/images/8/8b/MSO4054_Programmer_Manual.pdf]

    TEKTRONIX,DSA8300:
        Fast scope with optical and RF channels [http://www.tek.com/download?n=975655&f=190886&u=http%3A%2F%2Fdownload.tek.com%2Fsecure%2FDifferential-Channel-Alignment-Application-Online-Help.pdf%3Fnvb%3D20170404035703%26amp%3Bnva%3D20170404041203%26amp%3Btoken%3D0ccdfecc3859114d89c36]

    TEKTRONIX,TDS6154C:
        Scope with optical and RF channels [http://www.tek.com/sites/tek.com/files/media/media/resources/55W_14873_9.pdf]

        Todo:
            These behave differently. Be more explicit about sample mode::

                timebaseConfig(avgCnt=1)
                acquire([1])

                acquire([1], avgCnt=1)

            Does DPO support sample mode at all?

    '''
    # This should be overloaded by the particular driver
    totalChans = None

    # These should be overloaded by an abstract subclass
    recLenParam = None
    clearBeforeAcquire = None
    measurementSourceParam = None
    runModeParam = None
    runModeSingleShot = None

    def __init__(self, *args, **kwargs):
        if not isinstance(self, VISAInstrumentDriver):
            raise TypeError(str(type(self)) + ' is abstract and cannot be initialized')
        super().__init__(*args, **kwargs)

    def startup(self):
        # Make sure sampling and data transferring are in a consistent state
        initNpts = self.getConfigParam(self.recLenParam)
        self.acquire(nPts=initNpts)

    def timebaseConfig(self, avgCnt=None, duration=None, position=None, nPts=None):
        ''' Timebase and acquisition configure

            Args:
                avgCnt (int): averaging done by the scope
                duration (float): time, in seconds, for data to be acquired
                position (float): trigger delay
                nPts (int): number of samples taken

            Returns:
                (dict) The present values of all settings above
        '''
        if avgCnt is not None and avgCnt > 1:
            self.setConfigParam('ACQUIRE:NUMAVG', avgCnt, forceHardware=True)
        if duration is not None:
            self.setConfigParam('HORIZONTAL:MAIN:SCALE', duration/10)
        if position is not None:
            self.setConfigParam('HORIZONTAL:MAIN:POSITION', position)
        if nPts is not None:
            self.setConfigParam(self.recLenParam, nPts)
            self.setConfigParam('DATA:START', 1)
            self.setConfigParam('DATA:STOP', nPts)

        presentSettings = dict()
        presentSettings['avgCnt'] = self.getConfigParam('ACQUIRE:NUMAVG')
        presentSettings['duration'] = self.getConfigParam('HORIZONTAL:MAIN:SCALE')
        presentSettings['position'] = self.getConfigParam('HORIZONTAL:MAIN:POSITION')
        presentSettings['nPts'] = self.getConfigParam(self.recLenParam)
        return presentSettings

    def acquire(self, chans=None, **kwargs):
        ''' Get waveforms from the scope.

            If chans is None, it won't actually trigger, but it will configure.

            If unspecified, the kwargs will be derived from the previous state of the scope.
            This is useful if you want to play with it in lab while working with this code too.

            Args:
                chans (list): which channels to record at the same time and return

            Returns:
                list[Waveform]: recorded signals
        '''
        self.timebaseConfig(**kwargs)
        if chans is None:
            return

        for c in chans:
            if c > self.totalChans:
                raise Exception('Received channel: ' + str(c) +
                    '. Max channels of this scope is ' + str(self.totalChans))

        # Channel select
        for ich in range(1, 1 + self.totalChans):
            thisState = 1 if ich in chans else 0
            self.setConfigParam('SELECT:CH' + str(ich), thisState)

        isSampling = kwargs.get(avgCnt, 0) == 1
        self.__setupSingleShot(isSampling)
        self.__triggerAcquire()
        wfms = [None] * len(chans)
        for i, c in enumerate(chans):
            vRaw = self.__transferData(c)
            t, v = self.__scaleData(vRaw)
            wfms[i] = Waveform(t, v)

        return wfms

    def __setupSingleShot(self, isSampling, forcing=False):
        ''' Set up a single shot acquisition.

                Not running continuous, and
                acquire mode set SAMPLE/AVERAGE

            Subclasses usually have additional settings to set here.

            Args:
                isSampling (bool): is it in sampling (True) or averaging (False) mode
                forcing (bool): if False, trusts that no manual changes were made, except to run continuous/RUNSTOP

            Todo:
                Missing DPO trigger source setting.
                Should we force it when averaging?
                Probably not because it could be CH1, CH2, AUX.
        '''
        self.run(False)
        self.setConfigParam('ACQUIRE:MODE',
                            'SAMPLE' if isSampling else 'AVERAGE',
                            forceHardware=forcing)

    def __triggerAcquire(self):
        ''' Sends a signal to the scope to wait for a trigger event. Waits until acquisition completes
        '''
        if self.clearBeforeAcquire:
            self.write('ACQUIRE:DATA:CLEAR') # clear out average history
        self.write('ACQUIRE:STATE 1') # activate the trigger listener
        self.wait(30000) # Bus and entire program stall until acquisition completes. Maximum of 30 seconds

    def __transferData(self, chan):
        ''' Returns the raw data pulled from the scope as time (seconds) and voltage (Volts)
            Args:
                chan (int): one channel at a time

            Returns:
                :py:mod:`data.Waveform`: a time, voltage paired signal

            Todo:
                Make this binary transfer to go even faster
        '''
        chStr = 'CH' + str(chan)
        self.setConfigParam('DATA:ENCDG', 'ASCII')
        self.setConfigParam('DATA:SOURCE', chStr)
        VISAObject.open(self)
        try:
            voltRaw = self.mbSession.query_ascii_values('CURV?')
        except pyvisa.VisaIOError as err:
            logger.error('Problem during query_ascii_values(\'CURV?\')')
            try:
                VISAObject.close(self)
            except:
                logger.error('Failed to close!', self.address)
                pass
            raise err
        VISAObject.close(self)
        return voltRaw

    def __scaleData(self, voltRaw):
        ''' Scale to second and voltage units.

            DSA and DPO are very annoying about treating ymult and yscale differently.
            TDS uses ymult not yscale

            Args:
                voltRaw (ndarray): what is returned from ``__transferData``

            Returns:
                (ndarray): time in seconds, centered at t=0 regardless of timebase position
                (ndarray): voltage in volts
        '''
        get = lambda param: float(self.getConfigParam('WFMOUTPRE:' + param, forceHardware=True))
        voltage = (np.array(voltRaw) - get('YZERO')) \
                  * get(self.yScaleParam) \
                  + get('YOFF')

        timeDivision = float(self.getConfigParam('HORIZONTAL:MAIN:SCALE'))
        time = np.linspace(-1, 1, len(voltage))/2 *  timeDivision * 10

        return time, voltage

    def wfmDb(self, chan, nWfms, untriggered=False):
        ''' Transfers a bundle of waveforms representing a signal database. Sample mode only.

            Configuration such as position, duration are unchanged, so use an acquire(None, ...) call to set them up

            Args:
                chan (int): currently this only works with one channel at a time
                nWfms (int): how many waveforms to acquire through sampling
                untriggered (bool): if false, temporarily puts scope in free run mode

            Returns:
                (FunctionBundle(Waveform)): all waveforms acquired
        '''
        bundle = FunctionBundle()
        with self.tempConfig('TRIGGER:SOURCE',
                'FREERUN' if untriggered else 'EXTDIRECT'):
            for _ in range(nWfms):
                bundle.addDim(self.acquire([chan], avgCnt=1)[0]) # avgCnt=1 sets it to sample mode
        return bundle

    def run(self, continuousRun=True):
        ''' Sets the scope to continuous run mode, so you can look at it in lab,
            or to single-shot mode, so that data can be acquired

            Args:
                continuousRun (bool)
        '''
        self.setConfigParam(self.runModeParam,
                            'RUNSTOP' if continuousRun else self.runModeSingleShot,
                            forceHardware=True)
        if continuousRun:
            self.setConfigParam('ACQUIRE:STATE', 1, forceHardware=True)

    def autoAdjust(self, chans):
        ''' Adjusts offsets and scaling so that waveforms are not clipped '''
        self.saveConfig(dest='+autoAdjTemp', subgroup=':MEASUREMENT')

        for c in chans:
            chStr = 'CH' + str(c)

            # Set up measurements
            measMenu = ':MEASUREMENT:MEAS'
            measTypes = ['PK2PK', 'MEAN']
            for iMeas, typeMeas in enumerate(measTypes):
                self.setConfigParam(measMenu + str(iMeas+1)
                    + self.measurementSourceParam, chStr)
                self.setConfigParam(measMenu + str(iMeas+1)
                    + ':TYPE', typeMeas)
                self.setConfigParam(measMenu + str(iMeas+1)
                    + ':STATE', 1)

            self.timebaseConfig(avgCnt=1)
            for iTrial in range(100):
                # Acquire new data
                self.acquire(chans=[c])

                # Put measurements into meas
                meas = dict()
                for iMeas, typeMeas in enumerate(measTypes):
                    meas[typeMeas] = float(self.query(measMenu + str(iMeas+1) + ':VALUE?'))

                span = 1 * self.getConfigParam(chStr + ':SCALE')
                span = float(span)
                offs = self.getConfigParam(chStr + ':OFFSET')
                offs = float(offs)
                newSpan = None
                newOffs = None


                # Check if scale is correct within the tolerance
                if meas['PK2PK'] < 0.7 * span:
                    newSpan = meas['PK2PK'] / 0.75
                elif meas['PK2PK'] > 0.8 * span:
                    newSpan = 2 * span
                if newSpan < 0.1 or newSpan > 100:
                    raise Exception('Scope channel ' + chStr + ' could not be adjusted.')

                # Check if offset is correct within the tolerance
                if abs(meas['mean']) > 0.05 * span:
                    newOffs = offs - meas['mean']

                # If we didn't set the new variables, then we're good to go
                if newSpan is not None and newOffs is not None:
                    break

                # Adjust settings
                self.setConfigParam(chStr + ':SCALE', newSpan / 10)
                self.setConfigParam(chStr + ':OFFSET', newOffs)

        self.loadConfig(source='+autoAdjTemp', subgroup=':MEASUREMENT')
        self.config.pop('autoAdjTemp')


class Tek_DSA(TekScopeAbstract):
    recLenParam = 'MAIN:RECORDLENGTH'
    clearBeforeAcquire = True
    measurementSourceParam = 'SOURCE1:WFM'
    runModeParam = 'ACQUIRE:STOPAFTER:MODE'
    runModeSingleShot = 'CONDITION'
    yScaleParam = 'YSCALE'

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


class Tek_TDS(Tek_DSA):
    ''' Very similar to the DSA '''
    recLenParam = 'HORIZONTAL:RECORDLENGTH'
    yScaleParam = 'YMULT'

    def histogramStats(self, *args, **kwargs):
        raise NotImplementedError('histogramStats has not been verified with TDS scopes')


class Tek_DPO(TekScopeAbstract):
    recLenParam = 'HORIZONTAL:RECORDLENGTH'
    clearBeforeAcquire = False
    measurementSourceParam = 'SOURCE1'
    runModeParam = 'ACQUIRE:STOPAFTER'
    runModeSingleShot = 'SEQUENCE'
    yScaleParam = 'YMULT'


