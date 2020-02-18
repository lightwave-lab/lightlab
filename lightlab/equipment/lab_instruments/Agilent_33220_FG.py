from . import VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import Configurable
from lightlab.laboratory.instruments import FunctionGenerator

import numpy as np
# from lightlab import visalogger as logger


class Agilent_33220_FG(VISAInstrumentDriver, Configurable):
    '''
        Function Generator

        `Manual <http://ecelabs.njit.edu/student_resources/33220_user_guide.pdf>`_

        Usage: :any:`/ipynbs/Hardware/FunctionGenerator.ipynb`

    '''
    instrument_category = FunctionGenerator

    amplitudeRange = (.01, 10)

    def __init__(self, name='Agilent synth', address=None, **kwargs):
        VISAInstrumentDriver.__init__(self, name=name, address=address, **kwargs)
        Configurable.__init__(self, precedingColon=False)

    def startup(self):
        pass
        # self.write('D0')  # enable output

    def enable(self, enaState=None):
        wordMap = {True: 'ON', False: 'OFF'}
        trueWords = [True, 1, '1', 'ON']
        if enaState is not None:
            self.setConfigParam('OUTP', wordMap[enaState])
        return self.getConfigParam('OUTP') in trueWords

    def frequency(self, newFreq=None):
        if newFreq is not None:
            self.setConfigParam('FREQ', newFreq)
        return self.getConfigParam('FREQ')

    def waveform(self, newWave=None):
        ''' Available tokens are (with optional part in brackets):
            'dc', 'sin[usoid]', 'squ[are]', 'ramp', 'puls[e]', 'nois[e]', 'user'
        '''
        tokens = {'dc', 'sin', 'ramp', 'squ', 'puls', 'nois', 'user'}
        if newWave is not None:
            for tok in tokens:
                if newWave.lower().startswith(tok):
                    self.setConfigParam('FUNC', tok.upper())
                    break
            else:
                raise ValueError(newWave + ' is not a valid waveform: ' + str(tokens))
        return self.getConfigParam('FUNC').lower()

    def setArbitraryWaveform(self, wfm):
        ''' Arbitrary waveform

            Todo:
                implement
        '''
        raise NotImplementedError('Todo')

    def amplAndOffs(self, amplOffs=None):
        ''' Amplitude and offset setting/getting

            Only uses the data-bar because the other one is broken

            Args:
                amplOffs (tuple(float)): new amplitude (p2p) and offset in volts
                If either is None, returns but does not set

            Returns:
                (tuple(float)): amplitude and offset, read from hardware if specified as None

            Critical:
                Offset control is not working. Some sort of dictionary conflict in 'VOLT'
        '''
        if amplOffs is None:
            amplOffs = (None, None)
        if np.isscalar(amplOffs):
            raise ValueError('amplOffs must be a tuple. ' +
                             'You can specify one element as None if you don\'t want to set it')
        amplitude, offset = amplOffs

        if offset is not None:
            self.setConfigParam('VOLT:OFFS', offset)
        offs = self.getConfigParam('VOLT:OFFS')

        if amplitude is not None:
            amplitude = np.clip(amplitude, *self.amplitudeRange)
            self.setConfigParam('VOLT', amplitude)
        ampl = self.getConfigParam('VOLT')
        return (ampl, offs)

    def duty(self, duty=None):
        ''' duty is in percentage. For ramp waveforms, duty is the percent of
            time spent rising.

            Critical:
                Again, this is having dpath troubles.
        '''
        if self.waveform() == 'squ':
            if duty is not None:
                self.setConfigParam('FUNC:SQU:DCYCLE', duty)
            return self.getConfigParam('FUNC:SQU:DCYCLE')
        elif self.waveform() == 'ramp':
            if duty is not None:
                self.setConfigParam('FUNC:RAMP:SYMMETRY', duty)
            return self.getConfigParam('FUNC:RAMP:SYMMETRY')
        else:
            raise ValueError('Duty cycles are not supported with the currently selected '
                             'type of waveform ({})'.format(self.waveform()))
