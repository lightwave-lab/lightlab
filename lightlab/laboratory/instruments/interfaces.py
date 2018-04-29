''' This module defines the essential interfaces for each kind of instrument.

    Todo:
        Document every interface.
'''

from .bases import Instrument


class PowerMeter(Instrument):
    ''' Usage: :any:`/ipynbs/Hardware/PowerMeter.ipynb` '''
    essential_attributes = Instrument.essential_attributes + \
        ['powerDbm',
         'powerLin']


class SourceMeter(Instrument):
    ''' Usage: :any:`/ipynbs/Hardware/Keithley.ipynb` '''
    essential_attributes = Instrument.essential_attributes + \
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
    ''' Usage: :any:`/ipynbs/Hardware/Keithley.ipynb` '''
    essential_attributes = SourceMeter.essential_attributes + \
        ['setPort',
         'setCurrentMode',
         'setVoltageMode',
         'setVoltage',
         'getVoltage',
         'measCurrent']


class VectorGenerator(Instrument):
    ''' Usage: TODO '''
    essential_attributes = Instrument.essential_attributes + \
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
    ''' Usage: :any:`/ipynbs/Hardware/Clock.ipynb` '''
    essential_attributes = Instrument.essential_attributes + \
        ['enable',
         'frequency']
    optional_attributes = Instrument.optional_attributes + \
        ['amplitude',
         'sweepSetup',
         'sweepEnable']


class NICurrentSource(Instrument):
    ''' Usage: :ref:`/ipynbs/Hardware/CurrentSources-NI.ipynb` '''
    essential_attributes = Instrument.essential_attributes + \
        ['setChannelTuning',
         'getChannelTuning',
         'off']


class CurrentSource(Instrument):
    ''' Deprecated/Future '''
    essential_attributes = Instrument.essential_attributes + \
        ['setChannelTuning',
         'getChannelTuning',
         'off']


class FunctionGenerator(Instrument):
    ''' Usage: :any:`/ipynbs/Hardware/FunctionGenerator.ipynb` '''
    essential_attributes = Instrument.essential_attributes + \
        ['frequency',
         'waveform',
         'amplAndOffs',
         'amplitudeRange',  # This should be a class attribute, not a method
         'duty']


class LaserSource(Instrument):
    ''' Usage: :any:`/ipynbs/Hardware/LaserSources-ILX.ipynb` '''
    essential_attributes = Instrument.essential_attributes + \
        ['setChannelEnable',
         'getChannelEnable',
         'setChannelWls',
         'getChannelWls',
         'setChannelPowers',
         'getChannelPowers',
         'getAsSpectrum',
         'off',
         'allOn',
         'enableState',
         'wls',
         'powers']
    optional_attributes = ['wlRanges', 'allOff']


class OpticalSpectrumAnalyzer(Instrument):
    ''' Usage: :any:`/ipynbs/Hardware/OpticalSpectrumAnalyzer.ipynb` '''
    essential_attributes = Instrument.essential_attributes + \
        ['spectrum',
         'wlRange']


class Oscilloscope(Instrument):
    ''' Usage: :any:`/ipynbs/Hardware/Oscilloscope.ipynb` '''
    essential_attributes = Instrument.essential_attributes + \
        ['acquire',
         'wfmDb',
         'run']
    optional_attributes = Instrument.optional_attributes + \
        ['histogramStats']

    def hardware_cooldown(self):
        ''' Keep it running continuously in case you are in lab and want to watch
        '''
        self.run()


class DSAOscilloscope(Oscilloscope):
    ''' Usage: :any:`/ipynbs/Hardware/Oscilloscope.ipynb` '''
    essential_attributes = Oscilloscope.essential_attributes + \
        ['histogramStats']


class PulsePatternGenerator(Instrument):
    ''' Usage: :any:`/ipynbs/Hardware/PulsePatternGenerator.ipynb` '''
    essential_attributes = Instrument.essential_attributes + \
        ['setPrbs',
         'setPattern',
         'getPattern',
         'on',
         'syncSource',
         'amplAndOffs']


class RFSpectrumAnalyzer(Instrument):
    ''' Usage: TODO '''
    essential_attributes = Instrument.essential_attributes + \
        ['getMeasurements',
         'setMeasurement',
         'run',
         'sgramInit',
         'sgramTransfer',
         'spectrum']


class VariableAttenuator(Instrument):
    ''' Usage: :any:`/ipynbs/Hardware/VariableAttenuator.ipynb` '''
    essential_attributes = Instrument.essential_attributes + \
        ['on',
         'off',
         'attenDB',
         'attenLin']


class NetworkAnalyzer(Instrument):
    ''' Usage: :any:`/ipynbs/Hardware/NetworkAnalyzer.ipynb` '''
    essential_attributes = Instrument.essential_attributes + \
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
    ''' Usage: TODO '''
    essential_attributes = Instrument.essential_attributes + \
        ['write',
         'query']
