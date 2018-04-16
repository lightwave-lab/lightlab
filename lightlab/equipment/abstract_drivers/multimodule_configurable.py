from lightlab.util.io import ChannelError

import numpy as np

from . import AbstractDriver
from .configurable import Configurable


class ConfigModule(Configurable):
    ''' A module that has an associated channel and keeps track of parameters
        within that channel. Updates only when changed or with ``forceHardware``.
        It communicates with a bank instrument of which it is a part.
        When it writes to hardware, it selects itself by first sending
        "'CH 2'" (if it were initialized with channel 2)
    '''
    selectPrefix = 'CH'

    def __init__(self, channel, bank, **kwargs):
        '''
            Args:
                channel (int): its channel that will be written before writing/querying
                bank (MultiModuleConfigurable): enclosing bank
        '''
        kwargs['interveningSpace'] = kwargs.pop('interveningSpace', True)
        kwargs['headerIsOptional'] = kwargs.pop('headerIsOptional', True)
        self.channel = channel
        self.bank = bank
        super().__init__(**kwargs)
        self._hardwareinit = True  # prevent Configurable from trying to write headers

    def __selectSelf(self):
        self.bank.write('{} {}'.format(self.selectPrefix, self.channel))

    def write(self, writeStr):
        self.__selectSelf()
        self.bank.write(writeStr)

    def query(self, queryStr):
        self.__selectSelf()
        return self.bank.query(queryStr)


class MultiModuleConfigurable(AbstractDriver):
    ''' Keeps track of multiple channels within an instrument
        when those channels are somewhat independent.

        It provides array and dict setting/getting.

        Primary advantage is that no write/queries are performed
        if there is no change in the value.
    '''
    maxChannel = None

    def __init__(self, useChans, configurableKlass=Configurable, **kwargs):
        self.useChans = useChans
        # Check that the requested channels are available to be blocked out
        if self.maxChannel is not None:
            if any(ch > self.maxChannel - 1 for ch in self.useChans):
                raise ChannelError('Requested channel is more than there are available')

        self.modules = []
        for chan in self.useChans:
            self.modules.append(configurableKlass(channel=chan, bank=self))
        super().__init__(**kwargs)

    def getConfigArray(self, cStr):
        '''
            Args:
                cStr (str): parameter name
        '''
        retVals = []
        for module in self.modules:
            retVals.append(module.getConfigParam(cStr))
        retArr = np.array(retVals)
        return retArr

    def setConfigArray(self, cStr, newValArr, forceHardware=False):
        ''' Iterate over modules setting the parameter to the corresponding array value

            Args:
                cStr (str): parameter name
                newValArr (array): values
                forceHardware (bool): guarantees sending to hardware

            Returns:
                (bool): did any require hardware write?
        '''
        if len(newValArr) != len(self.modules):
            raise ChannelError('Wrong number of channels in array. ' +
                               'Got {}, '.format(len(newValArr)) +
                               'Expected {}.'.format(len(self.useChans)))
        bankWroteToHardware = False
        for module, val in zip(self.modules, newValArr):
            moduleWroteToHardware = module.setConfigParam(cStr, val, forceHardware)
            bankWroteToHardware = bankWroteToHardware or moduleWroteToHardware
        return bankWroteToHardware

    def getConfigDict(self, cStr):
        '''
            Args:
                cStr (str): parameter name
        '''
        stateArr = self.getConfigArray(cStr)
        dictOfStates = dict()
        for ch in self.useChans:
            virtualIndex = self.useChans.index(ch)
            dictOfStates[ch] = stateArr[virtualIndex]
        return dictOfStates

    def setConfigDict(self, cStr, newValDict, forceHardware=False):
        '''
            Args:
                cStr (str): parameter name
                newValDict (array): dict keyed by channel
                forceHardware (bool): guarantees sending to hardware

            Returns:
                (bool): did any require hardware write?
        '''
        for chan in newValDict.keys():
            if chan not in self.useChans:
                raise ChannelError('Channel index not blocked out. ' +
                                    'Requested {}, '.format(chan) +
                                    'Available {}.'.format(self.useChans))
        setArrayBuilder = self.getConfigArray(cStr)
        for iCh, chan in enumerate(self.useChans):
            if chan in newValDict.keys():
                setArrayBuilder[iCh] = newValDict[chan]
        return self.setConfigArray(cStr, setArrayBuilder, forceHardware)


    @property
    def moduleIds(self):
        ''' list of module ID strings '''
        return list(self.getConfigArray('*IDN'))

