import numpy as np
from pathlib import Path

from lightlab import logger
from lightlab.util.data import Waveform, FunctionBundle
from lightlab.equipment.configure import Configurable, TekConfig

class DPO403X(Configurable):
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
            Reading SET? is very time consuming. Need to examine default file, if it exists, to only get the parameters of interest. Then query

    '''
    totalChans = None # This should be overloaded by the particular driver

    recLenParam = 'HORIZONTAL:RECORDLENGTH' # For DSA ':MAIN:RECORDLENGTH'
    clearBeforeAcquire = False # DSA true
    measurementSourceParam = 'SOURCE1' # DSA + ':WFM'

    def __init__(self, *args, **kwargs):
        if not isinstance(self, VISAInstrumentDriver):
            raise TypeError('DPO403X is abstract and cannot be initialized')
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
            self.setConfigParam(':SELECT:CH' + str(ich), thisState)

        self.__setupSingleShot()
        self.__triggerAcquire()
        wfms = [None] * len(chans)
        for i, c in enumerate(chans):
            vRaw = self.__transferData(c)
            t, v = self.__scaleData(vRaw)
            wfms[i] = Waveform(t, v)

        return wfms

    def __setupSingleShot(self):
        ''' Set up a single shot acquisition
        '''
        self.setConfigParam(':ACQUIRE:STOPAFTER:MODE', 'CONDITION', forceHardware=True) # True in case someone changed it in lab
        forcing = False # False means we trust that no one made manual changes
        if avgCnt is None or avgCnt > 1: # For average mode
            # Configure trigger if averaging
            self.setConfigParam(':TRIGGER:SOURCE', 'EXTDIRECT', forceHardware=forcing)
            self.setConfigParam(':ACQUIRE:MODE', 'AVERAGE', forceHardware=forcing)
            if self.dpo:
                self.setConfigParam(':ACQUIRE:STOPAFTER', 'SEQUENCE', forceHardware=forcing)
            else:
                self.setConfigParam(':ACQUIRE:STOPAFTER:CONDITION', 'AVGCOMP', forceHardware=forcing)
        else: # For sample mode
            if self.dpo:
                self.setConfigParam(':ACQUIRE:STOPAFTER', 'SEQUENCE', forceHardware=forcing)
            else:
                self.setConfigParam(':ACQUIRE:STOPAFTER:CONDITION', 'ACQWFMS', forceHardware=forcing)
                self.setConfigParam(':ACQUIRE:STOPAFTER:COUNT', '1', forceHardware=forcing)
            self.setConfigParam(':ACQUIRE:MODE', 'SAMPLE', forceHardware=forcing)

    def __triggerAcquire(self):
        ''' Sends a signal to the scope to wait for a trigger event. Waits until acquisition complete
        '''
        if self.clearBeforeAcquire:
            self.write(':ACQUIRE:DATA:CLEAR') # clear out average history
        self.write(':ACQUIRE:STATE 1') # activate the trigger listener
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
        self.setConfigParam(':DATA:ENCDG', 'ASCII')
        self.setConfigParam(':DATA:SOURCE', chStr)
        VISAObject.open(self)
        try:
            voltRaw = self.mbSession.query_ascii_values('CURV?')
        except pyvisa.VisaIOError as err:
            print('Problem during query_ascii_values(\'CURV?\')')
            try:
                VISAObject.close(self)
            except:
                print('Failed to close!', self.address)
                pass
            raise err
        VISAObject.close(self)

    def __scaleData(self, voltRaw):
        '''
            Args:
                voltRaw (ndarray): what is returned from ``__transferData``

            Returns:
                (ndarray): time in seconds
                (ndarray): voltage in volts
        '''
        # Scale to voltage units
        # DSA and DPO are very annoying about treating ymult and yscale differently
        # TDS uses ymult not yscale
        wfmInfoParams = {'YMULT', 'YZERO', 'YOFF'}
        if self.dpo:
            wfmInfoParams.add('YMULT')
        else:
            wfmInfoParams.add('YSCALE')
        wfmInfo = dict()
        for p in wfmInfoParams:
            wfmInfo[p] = float(self.getConfigParam('WFMOUTPRE:' + p))
        if self.dpo:
            yScActual = wfmInfo['YMULT']
        else:
            yScActual = wfmInfo['YSCALE']

        voltage = (np.array(voltRaw) - wfmInfo['YOFF']) * yScActual + wfmInfo['YZERO']

        timeScale = float(self.getConfigParam(':HORIZONTAL:MAIN:SCALE'))
        time = np.linspace(-1, 1, len(voltage))/2 *  timeScale * 10

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
        origTrigSrc = self.getConfigParam(':TRIGGER:SOURCE')
        self.setConfigParam(':TRIGGER:SOURCE', 'FREERUN' if untriggered else 'EXTDIRECT')
        # origAvgCnt = self.getConfigParam(':ACQUIRE:NUMAVG', forceHardware=True)
        bundle = FunctionBundle()
        for _ in range(nWfms):
            bundle.addDim(self.acquire([chan], avgCnt=1)[0]) # avgCnt=1 sets it to sample mode
        self.setConfigParam(':TRIGGER:SOURCE', origTrigSrc)
        return bundle

    def run(self):
        ''' Sets the scope to continuous run mode, so you can look at it in lab '''
        if self.dpo:
            self.setConfigParam(':ACQUIRE:STOPAFTER', 'RUNSTOP', forceHardware=True)
        else:
            self.setConfigParam(':ACQUIRE:STOPAFTER:MODE', 'RUNSTOP', forceHardware=True)
        self.setConfigParam(':ACQUIRE:STATE', 1, forceHardware=True)

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

    def generateDefaults(cls, filename=None, overwrite=False):
        ''' Generates a new default file. This takes a while

            Todo:
                Move this to the Configurable interface
        '''
        if filename is None:
            filename = self.instrID()
        if Path(filename).exists() and not overwrite:
            logger.warning(self.instrID() + ': Default already exists. \
                           Do overwrite if you really want.')
            return

        try:
            allConfig = TekConfig.fromSETresponse(self.query('SET?'))
            allSetCmds = allConfig.getList('', asCmd=True)
        except pyvisa.VisaIOError as e: # SET timed out. You are done.
            logger.error(self.instrID() + ': timed out on \'SET?\'. \
                         Try resetting with \'*RST\'.')
            raise e

        cfgBuild = TekConfig()
        oldTimeout = self.timeout
        self.timeout = 1000
        for cmd in allSetCmds:
            if cmd[0][-1]  != '&': # handle the sibling subdir token
                cStr = cmd[0]
            else:
                cStr = cmd[0][:-2]
            try:
                val = self.query(cStr + '?', withTimeout=1000)
                cfgBuild.set(cStr, val)
                logger.debug(cStr, '<--', val)
            except pyvisa.VisaIOError as e:
                logger.debug(cStr, 'X -- skipping')
        self.timeout = oldTimeout

        cfgBuild.save(filename)
        logger.debug('New default saved to', filename)
