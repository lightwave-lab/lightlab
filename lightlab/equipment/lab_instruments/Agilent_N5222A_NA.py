from . import VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import Configurable
from lightlab.laboratory.instruments import NetworkAnalyzer

import numpy as np
import time
from lightlab.util.data import Spectrum, FunctionBundle
import matplotlib.pyplot as plt
from IPython import display


class Agilent_N5222A_NA(VISAInstrumentDriver, Configurable):

    ''' Agilent PNA N5222A , RF network analyzer

        `Manual <http://na.support.keysight.com/pna/help/PNAHelp9_90.pdf>`_

        WARNING: The address is the same as the slow function generator, so don't use both on andromeda at the same time.

        Steep learning curve.

        Usage: :any:`/ipynbs/Hardware/NetworkAnalyzer.ipynb`

        Todo:
            All the RF equipment is reusing __enaBlock. Make this a method of Configurable.

            When setting up general, you have to setup sweep before setting CW frequency,
            or else the CW freq becomes the start frequency. Why? See hack in sweepSetup.
    '''
    instrument_category = NetworkAnalyzer

    def __init__(self, name='The network analyzer', address=None, **kwargs):
        VISAInstrumentDriver.__init__(self, name=name, address=address, **kwargs)
        Configurable.__init__(self, headerIsOptional=False)
        self.chanNum = 1
        self.traceNum = 1
        self.auxTrigNum = 1
        self.swpRange = None

    def startup(self):
        self.measurementSetup('S21')

    def amplitude(self, amp=None):
        ''' Amplitude is in dBm

            Args:
                amp (float): If None, only gets

            Returns:
                (float): output power amplitude
        '''
        if amp is not None:
            if amp > 30:
                print('Warning: PNA ony goes up to +30dBm, given {}dBm.'.format(amp))
                amp = 30
            if amp < -30:
                print('Warning: R&S ony goes down to -30dBm, given {}dBm.'.format(amp))
                amp = -30
            self.setConfigParam('SOUR:POW', amp)
        return self.getConfigParam('SOUR:POW')

    def frequency(self, freq=None):
        ''' Frequency is in Hertz

            **Setting the frequency takes you out of sweep mode automatically**


            Args:
                freq (float): If None, only gets

            Returns:
                (float): center frequency
        '''
        if freq is not None:
            if freq > 26e9:
                print('Warning: Agilent N5183 ony goes up to 40GHz, given {}GHz.'.format(freq / 1e9))
                freq = 26e9
            if freq == self.getConfigParam('SENS:FREQ:CW'):
                return freq
            if self.sweepEnable():
                print('Warning: Agilent N5183 was sweeping when you set frequency, moving to CW mode')
                # So we need to update this object's internal state too
                self.sweepEnable(False)
            # Setting this automatically brings to CW mode
            self.setConfigParam('SENS:FREQ:CW', freq)
        return self.getConfigParam('SENS:FREQ:CW')

    def enable(self, enaState=None):
        ''' Enabler for the entire output

            Args:
                enaState (bool): If None, only gets

            Returns:
                (bool): is RF output enabled
        '''
        return self.__enaBlock('OUTP:STAT', enaState)

    def run(self):
        self.setConfigParam('SENS:SWE:MODE', 'CONT')

    def sweepSetup(self, startFreq, stopFreq, nPts=None, dwell=None, ifBandwidth=None):
        ''' Configure sweep. See instrument for constraints; they are not checked here.

            **Does not auto-enable. You must also call :meth:`sweepEnable`**

            Args:
                startFreq (float): lower frequency in Hz
                stopFreq (float): upper frequency in Hz
                nPts (int): number of points
                dwell (float): time in seconds to wait at each sweep point. Default is minimum.

            Returns:
                None
        '''
        self.swpRange = [startFreq, stopFreq]

        if nPts is not None:
            self.setConfigParam('SENS:SWE:POIN', nPts)
        if dwell is not None:
            self.setConfigParam('SENS:SWE:DWEL', dwell)
        if ifBandwidth is not None:
            self.setConfigParam('SENS:IF:FREQ', ifBandwidth)

        self.getSwpDuration(forceHardware=True)

    def sweepEnable(self, swpState=None):
        ''' Switches between sweeping (True) and CW (False) modes

            Args:
                swpState (bool): If None, only gets, doesn't set.

            Returns:
                (bool): is the output sweeping
        '''
        if swpState is not None:
            self.setConfigParam('SENS:SWE:TYPE', 'LIN' if swpState else 'CW')
            if self.swpRange is not None:
                self.setConfigParam('SENS:FREQ:STAR', self.swpRange[0], forceHardware=True)  # Hack
                self.setConfigParam('SENS:FREQ:STOP', self.swpRange[1], forceHardware=True)  # Hack
        return self.getConfigParam('SENS:SWE:TYPE') == 'LIN'

    def normalize(self):
        pass

    def triggerSetup(self, useAux=None, handshake=None, isSlave=False):
        prefix = 'TRIG:CHAN{}:AUX{}'.format(self.chanNum, self.auxTrigNum)
        self.setConfigParam(prefix + ':INT', 'SWE')
        self.setConfigParam(prefix + ':POS', 'BEF')
        self.setConfigParam('TRIG:SOUR', 'EXT' if isSlave else 'IMM')
        self.__enaBlock(prefix + ':HAND', handshake)
        return self.__enaBlock(prefix, useAux)

    def getSwpDuration(self, forceHardware=False):
        return float(self.getConfigParam('SENS:SWE:TIME', forceHardware=forceHardware))

    def measurementSetup(self, measType='S21', chanNum=None):
        if chanNum is None:
            chanNum = self.chanNum
        traceNum = chanNum
        # First let's see the measurements already on this channel
        retStr = self.query('CALC{}:PAR:CAT:EXT?'.format(chanNum)).strip('"')
        if retStr == 'NO CATALOG':
            activeMeasTypes = []
            activeMeasNames = []
        else:
            activeMeasTypes = retStr.split(',')[1::2]
            activeMeasNames = retStr.split(',')[::2]

        newMeasName = 'ANT{}_{}'.format(chanNum, measType)
        if len(activeMeasTypes) == 1 and measType == activeMeasTypes[0] and newMeasName == activeMeasNames[0]:
            # It is already set up
            changed = False
        else:
            # Clear them
            for mName in activeMeasNames:
                self.write("CALC{}:PAR:DEL '{}'".format(chanNum, mName))
            # make a new measurement
            self.setConfigParam("CALC{}:PAR:EXT".format(chanNum), "'{}', '{}'".format(
                newMeasName, measType), forceHardware=True)
            self.setConfigParam('DISP:WIND:TRACE{}:FEED'.format(traceNum),
                                "'{}'".format(newMeasName), forceHardware=True)
            changed = True
        self.setConfigParam('CALC{}:PAR:MNUM'.format(self.chanNum),
                            self.chanNum, forceHardware=changed)
        # self.setConfigParam('CALC{}:PAR:SEL'.format(self.chanNum), self.chanNum, forceHardware=changed)
        # wait for changes to take effect
        # This could be improved by something like *OPC? corresponding to the end
        # of the first sweep
        time.sleep(self.getSwpDuration())

    def spectrum(self):
        # raise NotImplementedError('not working')
        # self.setConfigParam('SENS:SWE:GRO:COUN', nGroups)
        self.setConfigParam('SENS:SWE:MODE', 'HOLD')
        self.write('SENS:SWE:MODE SING')
        self.query('*OPC?')

        self.setConfigParam('FORM', 'ASC')
        self.open()
        dbm = self.mbSession.query_ascii_values('CALC{}:DATA? FDATA'.format(self.chanNum))
        self.close()

        fStart = float(self.getConfigParam('SENS:FREQ:STAR'))
        fStop = float(self.getConfigParam('SENS:FREQ:STOP'))
        freqs = np.linspace(fStart, fStop, len(dbm))
#       return freqs, dbm
        return Spectrum(freqs, dbm)

    # fixme: get this out of here.
    def multiSpectra(self, nSpect=1, livePlot=False):
        bund = FunctionBundle()
        for iSpect in range(nSpect):
            s = self.spectrum()
            bund.addDim(s)
            if livePlot:
                s.simplePlot()
                display.clear_output()
                display.display(plt.gcf())
            else:
                print('Took spectrum {} of {}'.format(iSpect + 1, nSpect))
        print('done.')
        return bund

    def __enaBlock(self, param, enaState=None, forceHardware=False):
        ''' Enable wrapper that transitions from bool to whatever the equipment might put out.

            Args:
                param (str): the configuration string
                enaState (bool, None): If None, does not set; only gets
                forceHardware (bool): feeds through to setConfigParam

            Returns:
                (bool): is this parameter enabled
        '''
        wordMap = {True: 'ON', False: 'OFF'}
        trueWords = [True, 1, '1', 'ON']
        if enaState is not None:
            self.setConfigParam(param, wordMap[enaState], forceHardware=forceHardware)
        return self.getConfigParam(param, forceHardware=forceHardware) in trueWords
