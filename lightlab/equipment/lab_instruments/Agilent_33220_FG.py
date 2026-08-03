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
        '''
        Available tokens are (with optional part in brackets):
        'dc', 'sin[usoid]', 'squ[are]', 'ramp', 'puls[e]', 'nois[e]', 'user'
        '''
        tokens = {'dc', 'sinusoid', 'ramp', 'square', 'pulse', 'noise', 'user'}
        
        if newWave is not None:
            user_wave = newWave.lower()
            matched_tok = None
            
            for tok in tokens:
                # FIX: Check if the full hardware token starts with your input
                if tok.startswith(user_wave):
                    matched_tok = tok
                    break
                    
            if matched_tok is not None:
                self.write(f'FUNC {matched_tok.upper()}')
            else:
                raise ValueError(f"{newWave} is not a valid waveform: {tokens}")
                
        # Also fixed the f-string return format here
        return f'waveform set to {newWave}'

    def setArbitraryWaveform(self, wfm, name='VOLATILE'):
        ''' Arbitrary waveform

            Upload data to volatile memory
            
            Args:
                wfm: array of floats between -1 and 1
                name: The pointer name for the buffer
        '''
        if len(wfm) > 65536:
            raise ValueError("Waveform exceeds 64K points maximum.")

        # Scale -1.0 to 1.0 floats to 14-bit DAC integers (-8191 to +8191)
        wfm_int = (np.clip(wfm, -1.0, 1.0) * 8191).astype(int)
        str_data = ",".join(map(str, wfm_int))
        
        # Write to volatile memory
        self.write(f'DATA:DAC VOLATILE, {str_data}')
        
        # # Select this buffer as the one 'FUNC USER' will use
        # self.write(f'FUNC:USER {name}')
        
        # # Switch instrument output to arbitrary mode
        # self.waveform('user')
        
    def saveToNonVolatile(self, slot_name):
        ''' 
        
        Save to nonvolatile memory (max 12 characters)

        '''
        self.write(f'DATA:COPY {slot_name}, VOLATILE')

    def loadFromNonVolatile(self, slot_name):
        ''' 
        
        Selects a waveform stored in non-volatile memory for output. 
        
        '''
        self.write(f'FUNC:USER {slot_name}')
        self.waveform('user')

    def listStoredWaveforms(self):
        '''
        
        Returns a name list of all user-defined waveforms in non-volatile memory (string).
        
        '''

        raw_catalog = self.query('DATA:CATalog?')
        
        clean_list = [name.strip('"') for name in raw_catalog.split(',')]
        
        return [name for name in clean_list if name]
        
    def getArbitraryWaveform(self, name='VOLATILE', num_points=None):
        '''
        
        Retrieves wfm currently stored in instrument
        Retrieves the wfm points currently stored in the instrument.
        
        '''

        if num_points is None:
            num_points = int(self.query(f"DATA:ATTRibute:POINts? {name}"))
            
        raw_data = self.query(f"DATA:VALue? {name}, 1, {num_points}")
        
        wfm = np.fromstring(raw_data, sep=',')
        
        return wfm

    
    # --- Triggering & Synchronization ---

    def configureSync(self, enable=True):
        ''' 
        
        Enables/Disables the Sync BNC port. 
        In ARB mode, this outputs a pulse at the start of the waveform 
        to trigger your Oscilloscope.
        
        '''
        
        state = 'ON' if enable else 'OFF'
        self.write(f'OUTP:SYNC {state}')

    def setBurstMode(self, cycles=1, enabled=True):
        ''' 
        
        Sets the AWG to play the waveform N times per trigger 
        rather than looping infinitely.
        
        '''
        if enabled:
            self.write('BURSt:STATe OFF')
            self.write(f'BURSt:NCYC {cycles}')
            self.write('BURSt:STATe ON')
        else:
            self.write('BURSt:STATe OFF')
            
    def setTrigSource(self, source='BUS'):
        self.write(f'TRIGger:SOURce {source}')

    def setOutTrigSourceSlope(self, slope='POSitive'):
        self.write('OUTPut:TRIGger ON')
        self.write(f'OUTPut:TRIGger:SLOPE {slope}')
        
    def setInTrigSourceSlope(self, slope='POSitive'):
        self.write(f'TRIGger:SLOPE {slope}')  
        
    def triggerEnable(self):
        self.write('*TRG')
        return 'triggered'
        
    def amplAndOffs(self, amplOffs=None):
        '''
        Amplitude and offset setting/getting

        Only uses the data-bar because the other one is broken

        Args:
            amplOffs (tuple(float)): new amplitude (p2p) and offset in volts
            If either is None, returns but does not set

        Returns:
            (tuple(float)): amplitude and offset, read from hardware if specified as None
            
        '''
        if amplOffs is None:
            amplOffs = (None, None)
        if np.isscalar(amplOffs):
            raise ValueError('amplOffs must be a tuple.')
            
        amplitude, offset = amplOffs
        
        # 1. Handle Offset via raw SCPI write
        if offset is not None:
            # VOLTage:OFFSet is the full SCPI specification
            self.write(f'VOLTage:OFFSet {offset}')
            
        # 2. Handle Amplitude via raw SCPI write
        if amplitude is not None:
            amplitude = np.clip(amplitude, *self.amplitudeRange)
            # VOLTage is the standard SCPI spec
            self.write(f'VOLTage {amplitude}')
            
        # 3. Read back live data from hardware using query strings
        ampl = float(self.query('VOLTage?'))
        offs = float(self.query('VOLTage:OFFSet?'))
        
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
