import numpy as np
from lightlab.util.data import Waveform
from .Tektronix_DPO4034_Oscope import Tektronix_DPO4034_Oscope
import pyvisa
from lightlab import visalogger as logger


class Tektronix_DPO4032_Oscope(Tektronix_DPO4034_Oscope):
    '''
    Manual: https://www.imperial.ac.uk/media/imperial-college/research-centres-and-groups/centre-for-bio-inspired-technology/7293027.PDF
    '''
    totalChans = 2
    _recLenParam = 'HORIZONTAL:RECORDLENGTH'

    def timebaseConfig(self, avgCnt=None, duration=None):
        ''' Timebase and acquisition configure

            Args:
                avgCnt (int): averaging done by the scope
                duration (float): time, in seconds, for data to be acquired

            Returns:
                (dict) The present values of all settings above
        '''
        self.setConfigParam('HORIZONTAL:MAIN:SAMPLERATE', 2.5e9)

        if avgCnt is not None and avgCnt > 1:
            self.setConfigParam('ACQUIRE:NUMAVG', avgCnt, forceHardware=True)
        if duration is not None:
            self.setConfigParam('HORIZONTAL:MAIN:SCALE', duration / 10)
            self.setConfigParam(self._recLenParam, 10 * int(duration * 2.5e9))
            self.setConfigParam('DATA:START', 1)
            self.setConfigParam('DATA:STOP', int(duration * 2.5e9))

        presentSettings = dict()
        presentSettings['avgCnt'] = self.getConfigParam('ACQUIRE:NUMAVG', forceHardware=True)
        presentSettings['duration'] = self.getConfigParam(
            'HORIZONTAL:MAIN:SCALE', forceHardware=True)
        # presentSettings['position'] = self.getConfigParam('HORIZONTAL:MAIN:POSITION', forceHardware=True)
        presentSettings['nPts'] = self.getConfigParam(self._recLenParam, forceHardware=True)
        return presentSettings

    def __scaleData(self, voltRaw):
        ''' Scale to second and voltage units.

            DSA and DPO are very annoying about treating ymult and yscale differently.
            TDS uses ymult not yscale

            Args:
                voltRaw (ndarray): what is returned from ``__transferData``

            Returns:
                (ndarray): time in seconds, centered at t=0 regardless of timebase position
                (ndarray): voltage in volts

            Notes:
                The formula for real voltage should be (Y - YOFF) * YSCALE + YZERO.
                The Y represents the position of the sampled point on-screen,
                YZERO, the reference voltage, YOFF, the offset position, and
                YSCALE, the conversion factor between position and voltage.
        '''
        get = lambda param: float(self.getConfigParam('WFMOUTPRE:' + param, forceHardware=True))
        voltage = (np.array(voltRaw) - get('YOFF')) \
            * get(self._yScaleParam) \
            + get('YZERO')

        sample_rate = float(self.getConfigParam('HORIZONTAL:MAIN:SAMPLERATE', forceHardware=True))
        # time = np.linspace(-1, 1, len(voltage)) / 2 * timeDivision * 10
        time = np.arange(len(voltage)) / sample_rate
        time -= np.mean(time)

        return time, voltage

    def acquire(self, chans=None, timeout=None, **kwargs):
        ''' Get waveforms from the scope.

            If chans is None, it won't actually trigger, but it will configure.

            If unspecified, the kwargs will be derived from the previous state of the scope.
            This is useful if you want to play with it in lab while working with this code too.

            Args:
                chans (list): which channels to record at the same time and return
                avgCnt (int): number of averages. special behavior when it is 1
                duration (float): window width in seconds
                position (float): trigger delay
                nPts (int): number of sample points
                timeout (float): time to wait for averaging to complete in seconds
                    If it is more than a minute, it will do a test first


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

        isSampling = kwargs.get('avgCnt', 0) == 1
        self._setupSingleShot(isSampling)
        self._triggerAcquire(timeout=timeout)
        wfms = [None] * len(chans)
        for i, c in enumerate(chans):
            vRaw = self.__transferData(c)
            t, v = self.__scaleData(vRaw)
            # Optical modules might produce 'W' instead of 'V'
            unit = self.__getUnit()
            wfms[i] = Waveform(t, v, unit=unit)

        return wfms

    def __getUnit(self):
        ''' Gets the unit of the waveform as a string.

            Normally, this will be '"V"', which can be converted to 'V'
        '''

        yunit_query = self.getConfigParam('WFMOUTPRE:YUNIT', forceHardware=True)
        return yunit_query.replace('"', '')

    def __transferData(self, chan):
        ''' Returns the raw data pulled from the scope as time (seconds) and voltage (Volts)
            Args:
                chan (int): one channel at a time

            Returns:
                :mod:`data.Waveform`: a time, voltage paired signal

            Todo:
                Make this binary transfer to go even faster
        '''
        chStr = 'CH' + str(chan)
        self.setConfigParam('DATA:ENCDG', 'ASCII')
        self.setConfigParam('DATA:SOURCE', chStr)
        self.open()
        try:
            voltRaw = self.mbSession.query_ascii_values('CURV?')
        except pyvisa.VisaIOError as err:
            logger.error('Problem during query_ascii_values(\'CURV?\')')
            try:
                self.close()
            except pyvisa.VisaIOError:
                logger.error('Failed to close! %s', self.address)
            raise err
        self.close()
        return voltRaw
