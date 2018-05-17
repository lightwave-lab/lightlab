from lightlab import visalogger as logger

from . import VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import Configurable
from lightlab.laboratory.instruments import RFSpectrumAnalyzer
from lightlab.util.data import Spectrum, Spectrogram
import numpy as np


class Tektronix_RSA6120B_RFSA(VISAInstrumentDriver, Configurable):
    ''' TEKTRONIX RSA6120B, RF spectrum analyzer

        `Manual <http://www.giakova.com/siti/GIAKOVA/img/upload/Prodotti/file_1/RSA5000_MANUALE.pdf>`_

        Usage: TODO

        Fairly simple class for getting RF spectra.
        The RSA6120 has a lot of advanced functionality, like spectrograms, which could be implemented later.
    '''
    instrument_category = RFSpectrumAnalyzer

    def __init__(self, name='The RF spectrum analyzer', address=None, **kwargs):
        VISAInstrumentDriver.__init__(self, name=name, address=address, **kwargs)
        Configurable.__init__(self)

    def startup(self):
        # Turn off the measurements that are not supported by this class
        for am in self.getMeasurements():
            if am not in ['SPEC', 'SGR']:
                self.setConfigParam('DISP:GEN:MEAS:DEL', am, forceHardware=True)

    def getMeasurements(self):
        '''

            Returns:
                (list[str]): tokens of currently active measurements
        '''
        actWinStr = self.getConfigParam('DISP:WIND:ACT:MEAS', forceHardware=True)
        activeWindows = []
        for aws in actWinStr.split(','):
            activeWindows.append(aws.strip('" '))
        return activeWindows

    def setMeasurement(self, measType='SPEC', append=False):
        ''' Turns on a measurement type

            If append is False, turns off all measurements except for the one specified

            See manual for other measurement types.
        '''
        if not append:
            for am in self.getMeasurements():
                if am != measType:
                    self.setConfigParam('DISP:GEN:MEAS:DEL', am, forceHardware=True)
        if measType not in self.getMeasurements():
            self.setConfigParam('DISP:GEN:MEAS:NEW', measType, forceHardware=True)

    def run(self, doRun=True):
        ''' Continuous run

            After transferring spectra remotely, the acquisition stops going continuously.
            Call this when you want to run the display live. Useful for debugging when you are in lab.
        '''
        self.setConfigParam('INIT:CONT', 1 if doRun else 0, forceHardware=True)
        if doRun:
            self.write('INIT:RES')

    def sgramInit(self, freqReso=None, freqRange=None):
        self.setMeasurement('SGR')
        self.setConfigParam('SGR:TIME:STAR:DIV', 0, forceHardware=True)
        self.setConfigParam('SGR:TIME:PER:DIV', 0, forceHardware=True)
        if freqReso is not None:
            self.setConfigParam('SGR:BAND:RESOLUTION', freqReso, forceHardware=True)
        if freqRange is not None:
            freqRange = np.sort(freqRange)
            self.setConfigParam('SGR:FREQ:START', freqRange[0], forceHardware=True)
            self.setConfigParam('SGR:FREQ:STOP', freqRange[1], forceHardware=True)
        self.run(True)

    def sgramTransfer(self, duration=1., nLines=100):
        ''' Transfers data that has already been taken. Typical usage::

                self.sgramInit()
                ... << some activity >>
                self.run(False)
                self.spectrogram()

            Currently only supports free running mode, so time is approximate.
            The accuracy of timing and consistency of timing between lines is not guaranteed.
        '''
        if 'SGR' not in self.getMeasurements():
            raise Exception(
                'Spectrogram is not being recorded. Did you forget to call sgramInit()?')

        # def qg(subParam):
            # for Quick Get '''
            # return float(self.getConfigParam('SGR:' + subParam, forceHardware=True))

        # Create data structure with proper size
        trialLine = self.__sgramLines([0])[0]
        nFreqs = len(trialLine)

        # HOW MANY LINES

        # Which lines are we actually taking from the equipment
        estTimePerLine = 15.8e-6 * nFreqs

        # self.getConfigParam('SGR:TIME:SPEC:PERL', forceHardware=True)
        # self.setConfigParam('SGR:TIME:STAR:DIV', 0, forceHardware=True)
        # self.setConfigParam('SGR:TIME:PER:DIV', 0, forceHardware=True)
        # estTimePerLine = self.getConfigParam('SGR:TIME:PER:DIV', forceHardware=true)

        downsample = int(duration / estTimePerLine / nLines)
        if downsample < 1:
            nLines = int(duration / estTimePerLine)
            print('Warning: line density too high. You will get {} lines.'.format(nLines))
            downsample = 1
        lineNos = np.arange(nLines, dtype=int) * downsample

        # lineNos = np.arange(0,101,1)
        # nLines = len(lineNos)

        sgramMat = np.zeros((nLines, nFreqs))

        # Transfer data
        logger.debug('Preparing to transfer spectrogram of shape %s...', sgramMat.shape)
        self.__sgramLines(lineNos, container=sgramMat, debugEvery=100)
        logger.debug('Transfer complete.')

        # Scaling
        fStart = float(self.getConfigParam('SGR:FREQ:START', forceHardware=True))
        fStop = float(self.getConfigParam('SGR:FREQ:STOP', forceHardware=True))
        fBasis = np.linspace(fStart, fStop, nFreqs)
        tBasis = np.linspace(0, duration, nLines)

        # Put this in some kind of 2-D measured function structure.
        gram = Spectrogram([fBasis, tBasis], sgramMat)

        return gram

    def __sgramLines(self, lineNos, container=None, debugEvery=None):
        if container is None:
            container = [None] * len(lineNos)
        VISAInstrumentDriver.open(self)
        for i, lno in enumerate(lineNos):
            if debugEvery is not None and i % debugEvery == 0:
                logger.debug('Transferring %s / %s', lno, lineNos[-1])
            self.mbSession.write('TRAC:SGR:SEL:LINE {}'.format(lno))
            for _ in range(2):  # Sometimes the query just fails so we try again
                rawLine = self.mbSession.query_binary_values('FETCH:SGR?')
                if len(rawLine) > 0:
                    break
            else:
                logger.debug('Ran out of data on line %s', lno)
                continue
            try:
                container[i] = rawLine
            except ValueError as err:
                print('Error when putting data into container')
                print('len(rawLine) =', len(rawLine))
                print('type(container) =', type(container))
                if type(container) == np.ndarray:
                    print('np.shape(container) =', np.shape(container))
                else:
                    print('len(container) =', len(container))
                VISAInstrumentDriver.close(self)
                raise err
        VISAInstrumentDriver.close(self)
        return container

    def spectrum(self, freqReso=None, freqRange=None, typAvg='none', nAvg=None):
        ''' Acquires and transfers a spectrum.

            Unspecified or None parameters will take on values used in previous calls,
            with the exception of typAvg -- you must explicitly ask to average each time.

            Args:
                freqReso (float, None): frequency resolution (typical = 1e3 to 10e6)
                freqRange (array-like[float], None): 2-element frequency range
                typAvg (str): type of averaging (of ['none', 'average', 'maxhold', 'minhold', 'avglog'])
                nAvg (int, None): number of averages, if averaging

            Returns:
                (lightlab.util.data.Spectrum): power spectrum in dBm vs. Hz
        '''
        # Initialize measurement
        self.setMeasurement('SPEC', append=True)

        # Setup
        if freqReso is not None:
            self.setConfigParam('SPEC:BAND:RESOLUTION', freqReso)
        if freqRange is not None:
            freqRange = np.sort(freqRange)
            self.setConfigParam('SPEC:FREQ:START', freqRange[0])
            self.setConfigParam('SPEC:FREQ:STOP', freqRange[1])
        self.__setupMultiSpectrum(typAvg, nAvg)

        # Single trigger and data transfer
        VISAInstrumentDriver.open(self)
        dbmRaw = self.mbSession.query_binary_values('READ:SPEC:TRACE1?')
        VISAInstrumentDriver.close(self)

        # Scaling
        freqRangeActual = np.zeros(2, dtype=float)
        freqRangeActual[0] = float(self.getConfigParam('SPEC:FREQ:START', forceHardware=True))
        freqRangeActual[1] = float(self.getConfigParam('SPEC:FREQ:STOP', forceHardware=True))
        fBasis = np.linspace(*freqRangeActual, len(dbmRaw))
        return Spectrum(fBasis, dbmRaw, inDbm=True)

    def __setupMultiSpectrum(self, typAvg='average', nAvg=None):
        ''' When this is called, stored data is reset, but no new data is acquired

            Args:
                typAvg (str): 'none' turns off averaging. Others are ['average', 'maxhold', 'minhold', 'avglog']
                nAvg (int): number of averages
        '''
        typAvg = typAvg.upper()
        if typAvg in ['AVERAGE', 'AVGLOG']:
            if nAvg is not None:
                self.setConfigParam('TRACE1:SPEC:AVER:COUN', nAvg)
            self.write('TRACE1:SPEC:AVER:RESET')
        elif typAvg in ['MAXHOLD', 'MINHOLD']:
            if nAvg is not None:
                self.setConfigParam('TRACE1:SPEC:COUN', nAvg)
            self.write('TRACE1:SPEC:COUN:RESET')
            self.write('TRACE1:SPEC:COUN:ENABLE')
        elif typAvg != 'NONE':
            raise Exception(typAvg + ' is not a valid type of averaging')
        self.setConfigParam('TRACE1:SPEC:FUNC', typAvg)
