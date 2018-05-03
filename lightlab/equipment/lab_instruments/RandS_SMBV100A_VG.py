from . import VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import Configurable
from lightlab.laboratory.instruments import VectorGenerator

import numpy as np


class RandS_SMBV100A_VG(VISAInstrumentDriver, Configurable):
    ''' Rohde and Schwartz SMBV100A

        `Manual <https://cdn.rohde-schwarz.com/pws/dl_downloads/dl_common_library/dl_manuals/gb_1/s/smbv/SMBV100A_OperatingManual_en_16.pdf>`_

        Usage: TODO

        This is a complicated class even though it is implementing about 1 percent of what the R&S can do.
        The philosophy is that there are several blocks that work independently.

        1. Baseband digital modulation; accessed with :meth:`digiMod`
        2. Artificial Gaussian noise; accessed with :meth:`addNoise`
        3. RF carrier wave; accessed with :meth:`amplitude`, :meth:`frequency`, and :meth:`carrierMod`

        There are also global switches

        1. All RF outputs; switched with :meth:`enable`
        2. All modulations; switched with :meth:`modulationEnable`
    '''
    instrument_category = VectorGenerator

    def __init__(self, name='The Rohde and Schwartz', address=None, **kwargs):
        VISAInstrumentDriver.__init__(self, name=name, address=address, **kwargs)
        Configurable.__init__(self)

    def amplitude(self, amp=None):
        ''' Amplitude is in dBm

            Args:
                amp (float): If None, only gets

            Returns:
                (float): output power amplitude
        '''
        if amp is not None:
            if amp > 30:
                print('Warning: R&S ony goes up to +30dBm, given {}dBm.'.format(amp))
                amp = 15
            if amp < -145:
                print('Warning: R&S ony goes down to -145dBm, given {}dBm.'.format(amp))
                amp = -145
            self.setConfigParam('POW', amp)
        return self.getConfigParam('POW')

    def frequency(self, freq=None):
        ''' Frequency is in Hertz. This does not take you out of list mode, if you are in it

            Args:
                freq (float): If None, only gets

            Returns:
                (float): center frequency
        '''
        if freq is not None:
            self.setConfigParam('FREQ', freq)
        return self.getConfigParam('FREQ')

    def enable(self, enaState=None):
        ''' Enabler for the entire output

            Args:
                enaState (bool): If None, only gets

            Returns:
                (bool): is RF output enabled
        '''
        return self.__enaBlock('OUTP:STAT', enaState)

    def modulationEnable(self, enaState=None):
        ''' Enabler for all modulation: data, noise, carrier

            If this is False, yet device is enabled overall. Output will be a sinusoid

            This is a global modulation switch, so::

                modulationEnable(False)

            is equivalent to::

                carrierMod(False)
                addNoise(False)
                digiMod(False)

            Args:
                enaState (bool): If None, only gets

            Returns:
                (bool): is global modulation enabled
        '''
        return self.__enaBlock('MOD:STAT', enaState)

    def __iqMod(self, enaState=None):
        ''' Enabler for IQ modulations: data and noise (not carrier)

            Args:
                enaState (bool): If None, only gets

            Returns:
                (bool): is IQ modulation enabled
        '''
        return self.__enaBlock('IQ:STAT', enaState, forceHardware=True)

    def addNoise(self, enaState=True, bandwidth=None, cnRatio=None):
        ''' Enabler for additive white gaussian noise modulations

            Args:
                enaState (bool, None): If None, only sets parameters; does not change enable state
                bandwidth (float): noise bandwidth in Hertz (typical = 1e6)
                cnRatio (float): carrier-to-noise ratio in dB (typical = 10)

            Returns:
                (bool): is noise enabled
        '''
        self.setConfigParam('AWGN:MODE', 'ADD')
        if bandwidth is not None:
            self.setConfigParam('AWGN:BWID', bandwidth)
        if cnRatio is not None:
            self.setConfigParam('AWGN:CNR', cnRatio)
        return self.__enaBlock('AWGN:STAT', enaState)

    def setPattern(self, bitArray):
        ''' Data pattern for digital modulation

            Args:
                bitArray (ndarray): array that is boolean or binary 1/0
        '''
        self.setConfigParam('BB:DM:SOUR', 'PATT')
        bitArray = np.array(bitArray, dtype=int)
        onesAndZeros = ''.join([str(b) for b in bitArray])
        pStr = '#B' + onesAndZeros + ',' + str(len(bitArray))
        self.setConfigParam('BB:DM:PATT', pStr)

    def digiMod(self, enaState=True, symbRate=None, amExtinct=None):
        ''' Enabler for baseband data modulation

            Data is derived from pattern.

            Args:
                enaState (bool, None): if False, noise and RF modulations persist. If None, sets parameters but no state change
                symbRate (float): bit rate in Symbols/s (typical = 3e6)
                amExtinct (float): on/off ratio for AM, in percentage (0-100). 100 is full extinction

            Returns:
                (bool): is digital modulation enabled

            Todo:
                From DM, only AM implemented right now. Further possibilities for formatting are endless

                Possibility for arbitrary IQ waveform saving/loading in the :BB:ARB menu
        '''
        if symbRate is not None:
            self.setConfigParam('BB:DM:SRAT', symbRate)
        if amExtinct is not None:
            self.setConfigParam('BB:DM:ASK:DEPT', amExtinct)
        if enaState is not None:
            if self.addNoise(None):
                self.setConfigParam('AWGN:MODE', 'ADD' if enaState else 'ONLY')
            else:
                self.__iqMod(enaState)
        return self.__iqMod() and self.getConfigParam('AWGN:MODE') == 'ADD'

    def carrierMod(self, enaState=True, typMod=None, deviation=None, modFreq=None):
        ''' Enabler for modulations of the RF carrier

            Args:
                enaState (bool, None): if False, noise and data modulations persist. If None, sets parameters but no state change
                typMod (str): what kind of modulation (of ['am', 'pm', 'fm']). Cannot be None when enaState is True
                deviation (float, None): amplitude of the modulation, typMod dependent
                modFreq (float, None): frequency of the modulation in Hertz (typical = 100e3)

            Returns:
                (bool): is carrier modulation of typMod enabled

            There are three kinds of modulation, and they affect the interpretation of ``deviation``.
                * ``typMod='am'``: depth (0--100) percent
                * ``typMod='pm'``: phase (0--50) radians
                * ``typMod='fm'``: frequency (0--16e6) Hertz

            Only one type of modulation can be present at a time. ``enaState`` causes these effects:
                * True: this type is enabled, other types are disabled
                * False: all types are disabled
                * None: sets parameters of this type, whether or not it is the one enabled
        '''
        allMods = ['AM', 'PM', 'FM']
        # Type checking
        if typMod is None:
            if enaState is None:
                raise Exception('Nothing to do here for parameter setting typMod=None')
            elif enaState:
                raise Exception('Modulation type must be selected with typMod= to enable')
            else:
                typMod = allMods[0]  # Could be any since they are all deactivated later
        typMod = typMod.upper()
        if typMod not in allMods:
            raise Exception(typMod + ' is not a valid kind of carrier modulation: am, fm, or pm')
        # Generic parameter setup
        self.setConfigParam(typMod + ':SOUR', 'INT')
        if typMod in ['PM', 'FM']:
            self.setConfigParam(typMod + ':MODE', 'HDEV')
        # Specifiable parameter setup
        if deviation is not None:
            self.setConfigParam(typMod, deviation)
        if modFreq is not None:
            self.setConfigParam('LFO:FREQ', modFreq)
        # If turning this type on, turn off the other types
        if enaState is not None:
            for mod in allMods:
                if mod != typMod:
                    self.__enaBlock(mod + ':STAT', False)
        # Enabling
        return self.__enaBlock(typMod + ':STAT', enaState)

    def listEnable(self, enaState=True, freqs=None, amps=None, isSlave=False, dwell=None):
        ''' Sets up list mode.

            If isSlave is True, dwell has no effect. Put the trigger signal into the **INST TRIG** port.
            If isSlave is False, it steps automatically every dwell time.

            If both freqs and amps are None, do nothing to list data.
            If one is None, get a constant value from the frequency/amplitude methods.
            If either is a scalar, it will become a constant list, taking on the necessary length.
            If both are non-scalars, they must be the same length.

            Args:
                enaState (bool): on or off
                freqs (list): list data for frequency, in Hz
                amps (list): list data for power, in dBm
                isSlave (bool): Step through the list every time **INST TRIG** sees an edge (True), or every dwell time (False)
                dwell (float): time to wait at each point, if untriggered
        '''
        if enaState:
            # This will be automatically disabled, so we want to keep our config state accurate
            self.carrierMod(False)
        self.setConfigParam('FREQ:MODE', 'LIST' if enaState else 'CW')
        if isSlave is not None:
            self.setConfigParam('LIST:MODE', 'STEP' if isSlave else 'AUTO')
            self.setConfigParam('LIST:TRIG:SOUR', 'EXT' if isSlave else 'AUTO')
        if dwell is not None:
            self.setConfigParam('LIST:DWELL', dwell)

        if freqs is not None or amps is not None:
            if freqs is None:
                freqs = self.frequency()
            if amps is None:
                amps = self.amplitude()
            if np.isscalar(amps) and np.isscalar(freqs):
                amps = [amps]
                freqs = [freqs]
            elif np.isscalar(amps):
                amps = amps * np.ones(len(freqs))
            elif np.isscalar(freqs):
                freqs = freqs * np.ones(len(amps))
            else:
                if len(amps) != len(freqs):
                    raise ValueError(
                        'amps and freqs must have equal lengths, or one/both can be scalars or None')
            self.setConfigParam('LIST:FREQ', ', '.join([str(int(f)) for f in freqs]))
            self.setConfigParam('LIST:POW', ', '.join([str(int(a)) for a in amps]))

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
