from . import VISAInstrumentDriver
from lightlab.laboratory.instruments import CurrentSource

import numpy as np
import time
import visa as pyvisa
from lightlab.util import io
from lightlab import visalogger as logger


class CurrentSources(VISAInstrumentDriver):
    """Class for controlling NI-DAQ PCI board, wrapped by Labview, wrapped by TCPIP
        This uses a Labview listener working with TCPIP on the GC bench computer (andromeda)
        Interface to this module is meant to look like a TCPIP server

        Specify a sourceMode when you initialize this class: volt, milliAmp, mWperOhm

        As of 12/16/16,
            the hardware configuration is:
                PCI board hardware - 32 voltage outputs (-10V to 10V), followed by...
                V2I converter - maps 10V to 40mA -- from Grandalytics

            the software configuration is:
                Labview DAQ listener is hard coded for the first 12 channels only (of 32)
                same for Labview TCPIP listener
    """
    instrument_category = CurrentSource

    voltBounds = [0, 10]  # in volts, artificially constrain this if you want to be safe
    v2maCoef = 4  # current (milliamps) = v2maCoef * voltage (volts)
    fullChannelNums = 32  # number of dimensions that the current sources are expecting
    targetPort = 16022  # TCPIP server port; charge of an electron (Coulombs)
    waitMsOnWrite = 500 # Time to settle after tuning
    __tuneState = None
    ''' Initialize a client connection over TCPIP

            You must specify either useChans or stateDict, but not both.

            Args:
                useChans (list): the actual hard channels to use 1-12: unordered, will correspond to this object's virtual channels 0-(n-1)
                stateDict (dict): pass by reference for tuning state dictionary
                sourceMode (str): the type of units used for driving the NI-PCI board. The options are (not case sensitive):
                    * 'volt' = raw voltage: range [-10, 10]
                    * 'milliAmp' = takes into account the V2I factor: range [0, 40]
                    * 'mWperOhm' = more than just scaling, this lets you set the power over a load, (assuming constant resistance): range [0, 1.6]
    '''

    # super().__init__('The current drivers', hostNS[hostname], CurrentSources.targetPort, tempSess=True)

    # The above is the old versioin of initialization, and the below is the new version!
    def __init__(self, name='The current source', address=None, **kwargs):
        logger.warning('This class to be deprecated. Use NI_PCI_6723.')
        logger.warning('Backwards incompatibilities:\n' +
            'No stateDict argument in __init__\n' +
            'No tuneState property. Use setChannelTuning and getChannelTuning')

        self.useChans = kwargs.pop("useChans", None)
        self.stateDict = kwargs.pop("stateDict", None)
        # sourceMode = kwargs.pop("sourceMode", None)
        super().__init__(name=name, address=address, tempSess=True, **kwargs)

        useChans, stateDict = self.useChans, self.stateDict
        if useChans is None and stateDict is None:
            # raise Exception('Must specify either useChans or stateDict when initializing current sources')
            useChans = list()
        if stateDict is None:
            self.channels = list(useChans)
            self.stateDict = dict([ch, 0] for ch in self.channels)
        else:
            self.channels = list(stateDict.keys())
            logger.warning('stateDict will be deprecated as a kwarg here')
            self.stateDict = stateDict
        if any(ch > CurrentSources.fullChannelNums - 1 for ch in self.channels):
            raise Exception(
                'Requested channel is more than there are available')
        self.__tuneState = np.zeros(len(self.channels))
        # self.mode = sourceMode.lower()
        # if self.mode not in ['volt', 'milliamp', 'mwperohm']:
        #     raise Exception(
        #         sourceMode + ' is not a valid driver mode (volt, milliamp, WperKOhm)')
        # self.close()  # For temporary server access

    def startup(self):
        self.off()

    def open(self):
        super().open()
        self.mbSession.write_termination = '\r\n'
        self.mbSession.set_visa_attribute(
            pyvisa.constants.VI_ATTR_TERMCHAR_EN, pyvisa.constants.VI_TRUE)
        # use the faster protocol
        self.mbSession.set_visa_attribute(
            pyvisa.constants.VI_ATTR_IO_PROT, pyvisa.constants.VI_PROT_4882_STRS)

    def instrID(self):
        return 'Current Source'

    def tcpTest(self, num=2):
        print('x = ' + str(num))
        # self.open()
        ret = self.query('Test: ' + str(num) + ' ' + str(num + .5))
        # self.close()
        retNum = [0] * len(ret.split())
        for i, s in enumerate(ret.split(' ')):
            retNum[i] = float(s) + .01
        print('[x+1, x+1.5] = ' + str(retNum))

    @property
    def tuneState(self):
        logger.warning('CurrentSources.tuneState getting/setting will be deprecated. Use dictionaries')
        return self.__tuneState

    @tuneState.setter
    def tuneState(self, newState):
        logger.warning('CurrentSources.tuneState getting/setting will be deprecated. Use dictionaries')
        newState = np.array(newState)
        if len(newState) != len(self.channels):
            raise io.ChannelError('Wrong number of channels. ' +
                                  'Requested ' + str(len(newState)) +
                                  ', Expecting ' + str(len(self.channels)))
        # enforce voltBounds
        bnds = [self.volt2val(vBnd) for vBnd in CurrentSources.voltBounds]
        enforcedState = np.clip(newState, *bnds)
        if (newState != enforcedState).any():
            print('Warning: value out of range was constrained.',
                  'Requested', newState,
                  '. Allowed range is', bnds, 'in', self.mode + 's.')
            raise io.RangeError('Current sources requested out of range.')

        if np.all(enforcedState == self.__tuneState):
            self.wake()
        else:
            self.__tuneState = enforcedState
            self.stateDict = dict(zip(self.channels, self.__tuneState))
            self.sendToHardware()

    def getChannelTuning(self, mode='mwperohm'):
        self.mode = mode
        chanValDict = dict()
        for iCh, chan in enumerate(self.channels):
            chanValDict[chan] = self.tuneState[iCh]
        return chanValDict

    def setChannelTuning(self, chanValDict, mode='mwperohm'):
        """Sets a number of channel values and updates hardware
        param: chanValDict: A dictionary specifying {channel: voltage}
        """
        self.mode = mode
        if type(chanValDict) is not dict:
            raise TypeError(
                'The argument for setChannelTuning must be a dictionary')
        tempState = self.tuneState.copy()
        for chan in chanValDict.keys():
            if chan not in self.channels:
                raise io.ChannelError('Channel index not blocked out. ' +
                                      'Requested ' + str(chan) +
                                      ', Available ' + str(self.channels))
        for iCh, chan in enumerate(self.channels):
            if chan in chanValDict.keys():
                tempState[iCh] = chanValDict[chan]
        self.tuneState = tempState

    @property
    def elChans(self):
        return list(self.getChannelTuning().keys())

    @property
    def useChans(self):
        ''' Backwards compatibility '''
        logger.warning('Deprecation warning. Use "elChans" instead of "useChans"')
        return self.elChans

    def wake(self):
        ''' Don't change the value but make sure it doesn't go to sleep after inactivity.

            Good for long sweeps
        '''
        self.sendToHardware(waitTime=0)

    def sendToHardware(self, waitTime=None):
        """Updates current drivers with the present value of tuneState
        Converts it to a raw voltage, depending on the mode of the driver

            Args:
                waitTime (float): time in ms to wait after writing, default (None) is defined in the class
        """
        # First get a complete array in terms of voltage needed by the NI-PCI card
        fullVoltageState = np.zeros(self.fullChannelNums)
        fullVoltageState[self.channels] = self.val2volt(self.tuneState)
        # Then write a TCPIP packet
        writeStr = 'Set:'
        for v in fullVoltageState:
            writeStr += ' ' + str(v)
        # self.open()
        retStr = self.query(writeStr)
        # self.close()
        if retStr != 'ACK':
            raise Exception(
                'Current driver is angry. Message: \"' + retStr + '\"')
        if waitTime is None:
            waitTime = CurrentSources.waitMsOnWrite
        logger.debug('Current settling for %s ms', waitTime)
        time.sleep(waitTime / 1000)

    def val2volt(self, value):
        """Converts to the voltage value that will be applied at the PCI board
        Depends on the current mode state of the instance
        """
        if self.mode == 'volt':
            setVoltage = value
        elif self.mode == 'milliamp':
            setVoltage = value / CurrentSources.v2maCoef
        elif self.mode == 'mwperohm':  # TODO I think this formula is in the wrong units
            setVoltage = np.sqrt(value * 1e3) / CurrentSources.v2maCoef
        return setVoltage

    def volt2val(self, volt):
        """Converts the voltage value that will be applied at the PCI board back into the units of th instance
        This is useful for bounds checking
        """
        if self.mode == 'volt':
            setValue = volt
        elif self.mode == 'milliamp':
            setValue = volt * CurrentSources.v2maCoef
        elif self.mode == 'mwperohm':
            setValue = (volt * CurrentSources.v2maCoef) ** 2 / 1e3
        return setValue

    def off(self):
        """Turn all voltages to zero, but maintain the session
        """
        self.mode = 'volt'
        self.tuneState = np.zeros(len(self.channels))

    def close(self):
        ''' Make sure not to simply call self.write(). That will cause call to this function if in tempSess '''
        if self.mbSession is not None:
            try:
                self.mbSession.write('close')
            except Exception as err:
                print(
                    'Error, cannot communicate with current sources, or session was closed prematurely')
        super().close()

