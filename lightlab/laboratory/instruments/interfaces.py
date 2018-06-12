''' This module defines the essential interfaces for each kind of instrument.

    Todo:
        Document every interface.
'''

from .bases import Instrument


class PowerMeter(Instrument):
    ''' Usage: :ref:`/ipynbs/Hardware/PowerMeter.ipynb` '''
    essentialMethods = Instrument.essentialMethods + \
        ['powerDbm',
         'powerLin']


class SourceMeter(Instrument):
    ''' Usage: :ref:`/ipynbs/Hardware/Keithley.ipynb` '''
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
    ''' Usage: :ref:`/ipynbs/Hardware/Keithley.ipynb` '''
    essentialMethods = SourceMeter.essentialMethods + \
        ['setPort',
         'setCurrentMode',
         'setVoltageMode',
         'setVoltage',
         'getVoltage',
         'measCurrent']


class VectorGenerator(Instrument):
    ''' Todo:
            Usage example
    '''
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
    ''' Usage: :ref:`/ipynbs/Hardware/Clock.ipynb` '''
    essentialMethods = Instrument.essentialMethods + \
        ['enable',
         'frequency']
    optionalAttributes = Instrument.optionalAttributes + \
        ['amplitude',
         'sweepSetup',
         'sweepEnable']


class NICurrentSource(Instrument):
    ''' Usage: :ref:`/ipynbs/Hardware/CurrentSources-NI.ipynb` '''
    essentialMethods = Instrument.essentialMethods + \
        ['setChannelTuning',
         'getChannelTuning',
         'off']


class CurrentSource(Instrument):
    ''' Deprecated/Future '''
    essentialMethods = Instrument.essentialMethods + \
        ['setChannelTuning',
         'getChannelTuning',
         'off']


class FunctionGenerator(Instrument):
    ''' Usage: :ref:`/ipynbs/Hardware/FunctionGenerator.ipynb` '''
    essentialMethods = Instrument.essentialMethods + \
        ['frequency',
         'waveform',
         'amplAndOffs',
         'amplitudeRange',  # This should be a class attribute, not a method
         'duty',
         'enable']
    optionalAttributes = Instrument.optionalAttributes + \
        ['setArbitraryWaveform']


class LaserSource(Instrument):
    ''' Usage: :ref:`/ipynbs/Hardware/LaserSources-ILX.ipynb` '''
    essentialMethods = Instrument.essentialMethods + \
        ['setChannelEnable',
         'getChannelEnable',
         'setChannelWls',
         'getChannelWls',
         'setChannelPowers',
         'getChannelPowers',
         'getAsSpectrum',
         'off',
         'allOn']
    essentialProperties = Instrument.essentialProperties + \
        ['enableState',
         'wls',
         'powers']
    optionalAttributes = ['wlRanges', 'allOff']


class OpticalSpectrumAnalyzer(Instrument):
    ''' Usage: :ref:`/ipynbs/Hardware/OpticalSpectrumAnalyzer.ipynb` '''
    essentialMethods = Instrument.essentialMethods + \
        ['spectrum']
    essentialProperties = Instrument.essentialProperties + \
        ['wlRange']


class Oscilloscope(Instrument):
    ''' Usage: :ref:`/ipynbs/Hardware/Oscilloscope.ipynb` '''
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
    ''' Usage: :ref:`/ipynbs/Hardware/Oscilloscope.ipynb` '''
    essentialMethods = Oscilloscope.essentialMethods + \
        ['histogramStats']


class PulsePatternGenerator(Instrument):
    ''' Usage: :ref:`/ipynbs/Hardware/PulsePatternGenerator.ipynb` '''
    essentialMethods = Instrument.essentialMethods + \
        ['setPrbs',
         'setPattern',
         'getPattern',
         'on',
         'syncSource',
         'amplAndOffs']


class RFSpectrumAnalyzer(Instrument):
    ''' Usage: TODO '''
    essentialMethods = Instrument.essentialMethods + \
        ['getMeasurements',
         'setMeasurement',
         'run',
         'sgramInit',
         'sgramTransfer',
         'spectrum']


class VariableAttenuator(Instrument):
    ''' Usage: :ref:`/ipynbs/Hardware/VariableAttenuator.ipynb` '''
    essentialMethods = Instrument.essentialMethods + \
        ['on',
         'off']
    essentialProperties = Instrument.essentialProperties + \
        ['attenDB',
         'attenLin',
         'wavelength',
         'calibration']


class NetworkAnalyzer(Instrument):
    ''' Usage: :ref:`/ipynbs/Hardware/NetworkAnalyzer.ipynb` '''
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
    ''' Usage: TODO '''
    essentialMethods = Instrument.essentialMethods + \
        ['write',
         'query']
