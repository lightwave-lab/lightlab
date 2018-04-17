''' This module defines the essential interfaces for each kind of instrument
'''

from .bases import Instrument
from lightlab.util.data import Spectrum


class PowerMeter(Instrument):
    essentialMethods = Instrument.essentialMethods + \
        ['powerDbm',
         'powerLin']


class SourceMeter(Instrument):
    essentialMethods = Instrument.essentialMethods + \
        ['setCurrent',
         'getCurrent',
         'measVoltage',
         'setProtectionVoltage',
         'protectionVoltage',
         'setProtectionCurrent',
         'protectionCurrent',
         'enable']

    def hardware_warmup(self):
        self.enable(True)

    def hardware_cooldown(self):
        self.enable(False)


class Keithley(SourceMeter):
    essentialMethods = SourceMeter.essentialMethods + \
        ['setPort',
         'setCurrentMode',
         'setVoltageMode',
         'setVoltage',
         'getVoltage',
         'measCurrent']


class VectorGenerator(Instrument):
    essentialMethods = Instrument.essentialMethods + \
        ['amplitude',
         'frequency',
         'enable',
         'modulationEnable',
         'addNoise',
         'setPattern',
         'digiMod',
         'carrierMod',
         'listEnable']


class Clock(Instrument):
    essentialMethods = Instrument.essentialMethods + \
        ['enable',
         'frequency']
    optionalAttributes = Instrument.optionalAttributes + \
        ['amplitude',
         'sweepSetup',
         'sweepEnable']


class NICurrentSource(Instrument):
    essentialMethods = Instrument.essentialMethods + \
        ['setChannelTuning',
         'getChannelTuning',
         'off']


class CurrentSource(Instrument):
    essentialMethods = Instrument.essentialMethods + \
        ['setChannelTuning',
         'getChannelTuning',
         'off']


class FunctionGenerator(Instrument):
    essentialMethods = Instrument.essentialMethods + \
        ['frequency',
         'waveform',
         'amplAndOffs',
         'amplitudeRange',  # This should be a class attribute, not a method
         'duty']


class LaserSource(Instrument):
    essentialMethods = Instrument.essentialMethods + \
        ['setChannelEnable',
         'getChannelEnable',
         'setChannelWls',
         'getChannelWls',
         'setChannelPowers',
         'getChannelPowers',
         'off',
         'allOn']
    essentialProperties = Instrument.essentialProperties + \
        ['enableState',
         'wls',
         'powers']
    optionalAttributes = ['wlRanges', 'allOff']

    def getAsSpectrum(self):
        ''' Gives a spectrum of power vs. wavelength,
            which has the wavelengths present as an abscissa,
            and their powers as ordinate (-120dBm if disabled)

            It starts in dBm, but you can change
            to linear with the Spectrum.lin method

            Returns:
                (Spectrum): The WDM spectrum of the present outputs
        '''
        absc = self.wls
        ordi = self.powers
        for iCh, ena in enumerate(self.enableState):
            if ena == 0:
                ordi[iCh] = -120
        return Spectrum(absc, ordi, inDbm=True)



class OpticalSpectrumAnalyzer(Instrument):
    essentialMethods = Instrument.essentialMethods + \
        ['spectrum']
    essentialProperties = Instrument.essentialProperties + \
        ['wlRange']


class Oscilloscope(Instrument):
    essentialMethods = Instrument.essentialMethods + \
        ['acquire',
         'wfmDb',
         'run']
    optionalAttributes = Instrument.optionalAttributes + \
        ['histogramStats']

    def hardware_cooldown(self):
        ''' Keep it running continuously in case you are in lab and want to watch
        '''
        self.run()


class DSAOscilloscope(Oscilloscope):
    essentialMethods = Oscilloscope.essentialMethods + \
        ['histogramStats']


class PulsePatternGenerator(Instrument):
    essentialMethods = Instrument.essentialMethods + \
        ['setPrbs',
         'setPattern',
         'getPattern',
         'on',
         'syncSource',
         'amplAndOffs']


class RFSpectrumAnalyzer(Instrument):
    essentialMethods = Instrument.essentialMethods + \
        ['getMeasurements',
         'setMeasurement',
         'run',
         'sgramInit',
         'sgramTransfer',
         'spectrum']


class VariableAttenuator(Instrument):
    essentialMethods = Instrument.essentialMethods + \
        ['on',
         'off']
    essentialProperties = Instrument.essentialProperties + \
        ['attenDB',
         'attenLin']


class NetworkAnalyzer(Instrument):
    essentialMethods = Instrument.essentialMethods + \
        ['amplitude',
         'frequency',
         'enable',
         'run',
         'sweepSetup',
         'sweepEnable',
         'triggerSetup',
         'getSwpDuration',
         'measurementSetup',
         'spectrum',
         'multiSpectra']


class ArduinoInstrument(Instrument):
    essentialMethods = Instrument.essentialMethods + \
        ['write',
         'query']
