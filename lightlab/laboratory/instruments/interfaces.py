''' This module defines the essential interfaces for each kind of instrument
'''
from .bases import Instrument


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
        'setProtectionCurrent',
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


class NICurrentSource(Instrument):
    essentialMethods = Instrument.essentialMethods + \
        ['setChannelTuning',
        'getChannelTuning',
        'off']
    # Must init with `useChans` somehow

class CurrentSource(Instrument):
    essentialMethods = Instrument.essentialMethods + \
        ['setChannelTuning',
        'getChannelTuning',
        'off']
    # Must init with `useChans` somehow


class FunctionGenerator(Instrument):
    essentialMethods = Instrument.essentialMethods + \
        ['frequency',
        'waveform',
        'amplAndOffs',
        'amplitudeRange', # This should be a class attribute, not a method
        'duty']


class LaserSource(Instrument):
    essentialMethods = Instrument.essentialMethods + \
        ['setChannelEnable',
        'getChannelEnable',
        'setChannelWls',
        'getChannelWls',
        'setChannelPowers',
        'getChannelPowers',
        'getAsSpectrum',
        'off']
    essentialProperties = Instrument.essentialProperties + \
        ['enableState',
        'wls',
        'powers']


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


