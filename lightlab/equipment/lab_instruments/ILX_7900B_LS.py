from . import VISAInstrumentDriver
from lightlab.laboratory.instruments import LaserSource

import numpy as np
import time

from lightlab.util.io import ChannelError
from lightlab.util.data import Spectrum
from lightlab.equipment.abstract_drivers import Configurable
from lightlab import visalogger as logger


class ILX_Module(Configurable):
    def __init__(self, channel, bank, **kwargs):
        kwargs['interveningSpace'] = kwargs.pop('interveningSpace', True)
        kwargs['precedingColon'] = kwargs.pop('precedingColon', False)
        kwargs['headerIsOptional'] = kwargs.pop('headerIsOptional', True)
        super().__init__(**kwargs)
        self._hardwareinit = True
        self.channel = channel
        self.bank = bank

    def write(self, writeStr):
        self.bank.write('CH ' + str(self.channel))
        self.bank.write(writeStr)

    def query(self, queryStr):
        self.bank.write('CH ' + str(self.channel))
        return self.bank.query(queryStr)



class ILX_7900B_LS(VISAInstrumentDriver):
    '''
        Class for the laser banks (ILX 7900B laser source). This provides the illusion that all 16 lasers are one system.
        Channels are zero-indexed (i.e. 0,1,2...15) based on wavelength order
        NOTE: 'modules' are used to refer to the index of DFB module within a given bank


        TODO:
            Deprecate stateDict, as in NI_PCI_6723 vs. CurrentSources

            Use Configurable so it doesn't have to be getting from hardware all the time

            The overarching problem is that multiple users are likely
            to be using this one at the same time, different channels of course.
            Currently only one user can be using it at a time.

                * This class could be singleton, so that only one exists, and/or...

                * It could have a special property in that lockouts occur on a channel basis
    '''
    instrument_category = LaserSource
    maxChannel = 8

    # Time it takes to equilibrate on different changes, in seconds
    sleepOn = {}
    # sleepOn['enable'] = 3
    # sleepOn['wavelength'] = 30
    # sleepOn['level'] = 5
    sleepOn['OUT'] = 0  # remember to change back
    sleepOn['WAVE'] = 0  # remember to change back
    sleepOn['LEVEL'] = 0  # remember to change back

    powerRange = np.array([-20, 13])

    def __init__(self, name='The laser source', address=None, useChans=None, **kwargs):
        kwargs['tempSess'] = kwargs.pop('tempSess', False)
        VISAInstrumentDriver.__init__(self, name=name, address=address, **kwargs)

        # Handle channels
        if 'dfbChans' in kwargs.keys():
            useChans = kwargs.pop('dfbChans')
        if useChans is None:
            logger.warning('No useChans specified for ILX_7900B_LS')
            useChans = list()
        # MultiChannelConfigurable.__init__(self, useChans=useChans)
        self.useChans = useChans
        # Check that the requested channels are available to be blocked out
        if self.maxChannel is not None:
            if any(ch > self.maxChannel - 1 for ch in self.useChans):
                raise ChannelError('Requested channel is more than there are available')

        self.ilxModules = []
        for chan in self.useChans:
            self.ilxModules.append(ILX_Module(channel=chan+1, bank=self))


    def startup(self):
        self.close()  # For temporary serial access

    @property
    def dfbChans(self):
        ''' Returns the blocked out channels as a list '''
        return self.useChans

    def setConfigArray(self, tokenStr, newValArr):
        ''' Compares old values to new. If there is a change, iterate over modules

            This does not touch the lasers that have not been reserved during initialization

            Args:
                tokenStr (str): 'OUT', 'WAVE', 'LEVEL'
                newValArr (array): values
        '''
        if len(newValArr) != len(self.ilxModules):
            raise ChannelError('Wrong number of channels in array. ' +
                               'Got {}, '.format(len(newValArr)) +
                               'Expected {}.'.format(len(self.useChans)))
        wroteToHardware = False
        for module, val in zip(self.ilxModules, newValArr):
            wroteToHardware = module.setConfigParam(tokenStr, val) or wroteToHardware
        if wroteToHardware:
            print('DFB settling for', self.sleepOn[tokenStr], 'seconds.')
            time.sleep(self.sleepOn[tokenStr])
            print('done.')
        return wroteToHardware

    def getConfigArray(self, tokenStr):
        '''
            Args:
                tokenStr (str): 'OUT', 'WAVE', 'LEVEL'
        '''
        retVals = []
        for module in self.ilxModules:
            retVals.append(module.getConfigParam(tokenStr))
        retArr = np.array(retVals)
        return retArr

    def getDict(self, tokenStr):
        stateArr = self.getConfigArr(tokenStr)
        dictOfStates = dict()
        for ch in self.useChans:
            virtualIndex = self.useChans.index(ch)
            dictOfStates[ch] = stateArr[virtualIndex]
        return dictOfStates

    def setDict(self, tokenStr, newValDict):
        ''' Takes a dictionary corresponding to 'wls', 'powers', or 'enableState' and turns
            it into an array that is stored in the order of blocked out channels. Unspecified
            values are taken from the current setting
        '''
        for chan in newValDict.keys():
            if chan not in self.useChans:
                raise ChannelError('Channel index not blocked out. ' +
                                    'Requested {}, '.format(chan) +
                                    'Available {}.'.format(self.useChans))
        setArrayBuilder = self.getConfigArray(tokenStr)
        for iCh, chan in enumerate(self.useChans):
            if chan in newValDict.keys():
                setArrayBuilder[iCh] = newValDict[chan]
        return self.setConfigArray(tokenStr, setArrayBuilder)

    # Module-level parameter setters and getters.
    @property
    def enableState(self):
        return self.getConfigArray('OUT')

    @enableState.setter
    def enableState(self, newState):
        ''' Updates lasers to newState
        '''
        self.setConfigArray('OUT', newState)

    def setChannelEnable(self, chanEnableDict):
        """Sets a number of channel values and updates hardware
        param: chanEnableDict: A dictionary specifying some {channel: enabled}
        """
        self.setDict('OUT', chanEnableDict)

    def getChannelEnable(self):
        return self.getDict('OUT')

    @property
    def wls(self):
        ''' wls is in nanometers '''
        return self.getConfigArray('WAVE')

    @wls.setter
    def wls(self, newWls):
        self.setConfigArray('WAVE', newWls)

    def setChannelWls(self, chanWavelengthDict):
        """Sets a number of channel wavelengths and updates hardware
        param: chanEnableDict: A dictionary specifying some {channel: wavelength}
        """
        self.setDict('WAVE')

    def getChannelWls(self):
        return self.getDict('WAVE')

    @property
    def powers(self):
        ''' powers is in dBm '''
        return self.getConfigArray('LEVEL')

    @powers.setter
    def powers(self, newPowers):
        self.setConfigArray('LEVEL', newPowers)

    def setChannelPowers(self, chanPowerDict):
        ''' Sets a number of channel power powers (in dBm) and updates hardware
        param: chanPowerDict: A dictionary specifying some {channel: wavelength}
        '''
        self.setDict('LEVEL')

    def getChannelPowers(self):
        return self.getDict('LEVEL')

    def getAsSpectrum(self):
        ''' Gives a spectrum of power vs. wavelength which just has the wavelengths present
            and blocked out by this bank

            Returns:
                (Spectrum)
        '''
        absc = self.wls
        ordi = np.array(self.enableState, dtype=float) * self.powers
        return Spectrum(absc, ordi, inDbm=True)

    @property
    def wlRanges(self):
        ''' wavelength tuples in (nm, nm) '''
        minArr = self.getConfigArray('WAVEMIN')
        maxArr = self.getConfigArray('WAVEMAX')
        return tuple(zip(minArr, maxArr))

    @property
    def moduleIds(self):
        ''' list of module ID strings '''
        return list(self.getConfigArray('*IDN'))

    def off(self):
        self.allOnOff(False)

    def allOnOff(self, allOn=False):
        if allOn:
            self.enableState = np.ones(len(self.useChans))
        else:
            self.enableState = np.zeros(len(self.useChans))


class ILX_7900B_LS_old(VISAInstrumentDriver):
    '''
        Class for the laser banks (ILX 7900B laser source). This provides the illusion that all 16 lasers are one system.
        Channels are zero-indexed (i.e. 0,1,2...15) based on wavelength order
        NOTE: 'modules' are used to refer to the index of DFB module within a given bank


        TODO:
            Deprecate stateDict, as in NI_PCI_6723 vs. CurrentSources

            Use Configurable so it doesn't have to be getting from hardware all the time

            The overarching problem is that multiple users are likely
            to be using this one at the same time, different channels of course.
            Currently only one user can be using it at a time.

                * This class could be singleton, so that only one exists, and/or...

                * It could have a special property in that lockouts occur on a channel basis
    '''
    instrument_category = LaserSource
    ordering_left = [1, 2, 3, 4, 5, 6, 7, 8]  # left bank
    ordering_right = [10, 9, 11, 12, 13, 14, 15, 16]  # right bank
    fullChannelNums = np.size(ordering_left)
    # numModulesPerBank = [len(m) for m in ordering] # indexed by which bank. There are 2 banks

    # Time it takes to equilibrate on different changes, in seconds
    sleepOn = {}
    sleepOn['enable'] = 3
    sleepOn['wavelength'] = 30
    sleepOn['level'] = 5

    powerRange = np.array([-20, 13])

    def __init__(self, name='The laser source', address=None, useChans=[1], **kwargs):
        kwargs['tempSess'] = kwargs.pop('tempSess', False)
        if 'dfbChans' in kwargs.keys():
            useChans = kwargs.pop('dfbChans')
        super().__init__(name=name, address=address, **kwargs)
        self.bankInstruments = VISAInstrumentDriver('DFB bank', address)


        useChans, stateDict = useChans, kwargs.pop("stateDict", None)
        if useChans is None and stateDict is None:
            raise Exception(
                'Must specify either useChans or stateDict when initializing laser sources')
        if stateDict is None:
            self.useChans = list(useChans)
            self.stateDict = dict([ch, -1] for ch in self.useChans)
        else:
            self.useChans = list(stateDict.keys())
            self.stateDict = stateDict
        # if any(ch > self.fullChannelNums - 1 for ch in self.useChans):
        #     raise Exception('Requested channel is more than there are available')
        if not set(self.ordering_left).isdisjoint(self.useChans):
            self.ordering = self.ordering_left
        elif not set(self.ordering_left).isdisjoint(self.useChans):
            self.ordering = self.ordering_right

    def startup(self):
        self.close()  # For temporary serial access

    # Module-level parameter setters and getters.
    # TODO: generalize this into parameter structures using a dictionary-based parameter names and communication tokens.
    # I.e. setChanParameter(self, token, chanValDict) --> returns None
    # getChanParameter(self, token, chanValSet) --> returns dict  [chanValSet
    # as in set([1,3,4])]

    @property
    def enableState(self):
        return self.moduleIterate('OUT')

    @enableState.setter
    def enableState(self, newState):
        ''' Updates lasers to newState
        '''
        newState = np.array(newState)
        if len(newState) != len(self.useChans):
            raise ChannelError('Wrong number of channels. ' +
                                  'Requested ' + str(len(newState)) +
                                  ', Expecting ' + str(len(self.useChans)))
        # enforce valueBounds
        enforcedState = newState
        enforcedState = [1 if s != 0 else 0 for s in enforcedState]
        if np.any(newState != enforcedState):
            logger.warning('Unexpected enable state value. ' +
                           'Requested = {}. '.format(newState) +
                           'Expected values = 0 or 1.')
        self.stateDict = dict(zip(self.useChans, enforcedState))

        # Refresh and sleep only if different
        oldState = self.moduleIterate('OUT')  # Get from hardware: takes some time
        if np.any(oldState != newState):
            self.moduleIterate('OUT', enforcedState)
            print('DFB settling for', self.sleepOn['enable'], 'seconds.')
            time.sleep(self.sleepOn['enable'])
            print('done.')

    def setChannelEnable(self, chanEnableDict):
        """Sets a number of channel values and updates hardware
        param: chanEnableDict: A dictionary specifying some {channel: enabled}
        """
        # check to see if this is different
        doUpdate = False
        for k, v in chanEnableDict.items():
            if self.stateDict[k] != v:
                doUpdate = True
        if doUpdate:
            self.enableState = self.parseDictionary(chanEnableDict, setArrayType='enableState')

    def getChannelEnable(self):
        return dict((ch, self.enableState[self.useChans.index(ch)]) for ch in self.useChans)

    @property
    def dfbChans(self):
        ''' Returns the blocked out channels as a list '''
        return self.useChans

    @property
    def wls(self):
        ''' wls is in nanometers '''
        return self.moduleIterate('WAVE')

    @wls.setter
    def wls(self, newWls):
        # Refresh and sleep only if different
        oldWls = self.moduleIterate('WAVE')  # Get from hardware: takes some time
        if np.any(oldWls != newWls):
            self.moduleIterate('WAVE', newWls)
            print('DFB settling for', self.sleepOn['wavelength'], 'seconds.')
            time.sleep(self.sleepOn['wavelength'])
            print('done.')

    def setChannelWls(self, chanWavelengthDict):
        """Sets a number of channel wavelengths and updates hardware
        param: chanEnableDict: A dictionary specifying some {channel: wavelength}
        """
        self.wls = self.parseDictionary(chanWavelengthDict, setArrayType='wls')

    def getChannelWls(self):
        return dict((ch, self.wls[self.useChans.index(ch)]) for ch in self.useChans)

    @property
    def powers(self):
        ''' powers is in dBm '''
        return self.moduleIterate('LEVEL')

    @powers.setter
    def powers(self, newPowers):
        # Refresh and sleep only if different
        oldPowers = self.moduleIterate('LEVEL')  # Get from hardware: takes some time
        if np.any(oldPowers != newPowers):
            self.moduleIterate('LEVEL', newPowers)
            print('DFB settling for', self.sleepOn['level'], 'seconds.')
            time.sleep(self.sleepOn['level'])
            print('done.')

    def setChannelPowers(self, chanPowerDict):
        ''' Sets a number of channel power powers (in dBm) and updates hardware
        param: chanPowerDict: A dictionary specifying some {channel: wavelength}
        '''
        self.powers = self.parseDictionary(chanPowerDict, setArrayType='powers')

    def getChannelPowers(self):
        return dict((ch, self.powers[self.useChans.index(ch)]) for ch in self.useChans)

    def getAsSpectrum(self):
        ''' Gives a spectrum of power vs. wavelength which just has the wavelengths present
            and blocked out by this bank

            Returns:
                (Spectrum)
        '''
        absc = self.wls
        ordi = np.array(self.enableState, dtype=float) * self.powers
        return Spectrum(absc, ordi, inDbm=True)

    @property
    def wlRanges(self):
        ''' wavelength tuples in (nm, nm) '''
        minArr = self.moduleIterate('WAVEMIN')
        maxArr = self.moduleIterate('WAVEMAX')
        return tuple(zip(minArr, maxArr))

    @wlRanges.setter
    def wlRanges(self, *args):
        print('Warning. wlRanges of the DFB modules is not settable. Ignoring this command')

    @property
    def moduleIds(self):
        ''' list of module ID strings '''
        return list(self.moduleIterate('*IDN'))

    @moduleIds.setter
    def moduleIds(self, *args):
        print('Warning. moduleIds of the DFB modules is not settable. Ignoring this command')

    def parseDictionary(self, chanValDict, setArrayType=None):
        ''' Takes a dictionary corresponding to 'wls', 'powers', or 'enableState' and turns
            it into an array that is stored in the order of blocked out channels. Unspecified
            values are taken from the current setting
        '''
        if type(chanValDict) is not dict:
            raise TypeError('The argument must be a dictionary')
        if setArrayType is None:
            setArrayType = 'wls'
        if setArrayType == 'enableState':
            setArrayBuilder = self.enableState
        elif setArrayType == 'wls':
            setArrayBuilder = self.wls
        elif setArrayType == 'powers':
            setArrayBuilder = self.powers
        else:
            raise TypeError('Not a valid setArrayType. Got ' + str(setArrayType) +
                            '. Need enableState, wls, or powers')
        for chan in chanValDict.keys():
            if chan not in self.useChans:
                raise ChannelError('Channel index not blocked out. ' +
                                      'Requested ' + str(chan) +
                                      ', Available ' + str(self.useChans))
        for iCh, chan in enumerate(self.useChans):
            if chan in chanValDict.keys():
                setArrayBuilder[iCh] = chanValDict[chan]
        return setArrayBuilder

    def moduleIterate(self, attrStr, virtualSetVals=None):
        ''' Iterates over modules in a virtual way sending the attribute
        If virtualSetVals=None, it performs a query by appending '?' and returns this in a virtual array
        This does not touch the lasers that have not been reserved during initialization
        '''
        if virtualSetVals is not None:
            isQuerying = False
            virtualRetVals = None
            if len(virtualSetVals) != len(self.useChans):
                raise Exception(
                    'moduleIterate does not yet support subset-module indexing. Use the full array... or you could implement that')
        else:
            isQuerying = True
            virtualRetVals = np.zeros(len(self.useChans))
        for iModule in range(len(self.ordering)):  # iterate over modules
            orderedChan = self.ordering[iModule] - 1  # get rid of 1-indexing
            if orderedChan in self.useChans:  # only enter for modules that have been reserved
                virtualChan = self.useChans.index(orderedChan)
                self.bankInstruments.write('CH ' + str(iModule + 1))
                if isQuerying:
                    retStr = self.bankInstruments.query(attrStr + '?')
                    virtualRetVals[virtualChan] = float(retStr)
                else:
                    self.bankInstruments.write(attrStr + ' ' + str(virtualSetVals[virtualChan]))
        return virtualRetVals

    def off(self):
        """Turn all voltages to zero, but maintain the session
        """
        self.enableState = np.zeros(len(self.useChans))

    def allOnOff(self, allOn=False):
        if allOn:
            self.enableState = np.ones(len(self.useChans))
        else:
            self.enableState = np.zeros(len(self.useChans))

    # Override some messaging methods to account for the fact that there's two GPIB laser banks
    def write(self, writeStr):
        print('Warning: Write not performed because bank was not specified.')
        print('    Instead, call write like this <this>.bankInstruments.write(writeStr)')

    def query(self, queryStr):
        print('Warning: Query not performed because bank was not specified.')
        print('    Instead, call query like this <this>.bankInstruments.query(queryStr)')

    def instrID(self):
        return self.bankInstruments.instrID()

    def close(self):
        # for b in self.bankInstruments:
        #     b.close()
        self.bankInstruments.close()
