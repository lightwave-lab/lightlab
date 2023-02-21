from lightlab.util.io import ChannelError
from lightlab import visalogger as logger
import numpy as np

from . import AbstractDriver
from .configurable import Configurable


class ConfigModule(Configurable):
    ''' A module that has an associated channel and keeps track of parameters
        within that channel. Updates only when changed or with ``forceHardware``.
        It communicates with a bank instrument of which it is a part.
        When it writes to hardware, it selects itself by first sending
        ``'CH 2'`` (if it were initialized with channel 2)
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
        ''' Writes a selector message that contains
            its prefix and its channel number
        '''
        self.bank.write('{} {}'.format(self.selectPrefix, self.channel))

    def write(self, writeStr):
        ''' Regular write in the enclosing bank, except preceded by select self
        '''
        self.__selectSelf()
        self.bank.write(writeStr)

    def query(self, queryStr):
        ''' Regular query in the enclosing bank, except preceded by select self
        '''
        self.__selectSelf()
        return self.bank.query(queryStr)


class MultiModuleConfigurable(AbstractDriver):
    ''' Keeps track of a list of ``Configurable`` objects,
        each associated with a channel number.
        Provides array and dict setting/getting.

        Parameter values are cached just like in ``Configurable``.
        That means hardware access is lazy: No write/queries are performed
        unless a parameter is not yet known, or if the value changes.

        When the module classes are ``ConfigModule``, then
        this supports multi-channel instruments where channels
        are selectable. This is used in cases where,
        for example, querying the wavelength
        of channel 2 would take these messages::

            self.write('CH 2')
            wl = self.query('WAVE')
    '''
    maxChannel = None

    def __init__(self, useChans=None, configModule_klass=Configurable, **kwargs):
        '''
            Args:
                useChans (list(int)): integers that indicate channel number.
                Used to key dictionaries and write select messages.
                configModule_klass (type): class that members will be initialized as.
                When ``Configurable``, this object is basically a container; however,
                when ``ConfigModule``, there is special behavior for multi-channel instruments.
        '''
        if useChans is None:
            logger.warning('No useChans specified for MultiModuleConfigurable')
            useChans = list()
        self.useChans = useChans
        # Check that the requested channels are available to be blocked out
        if self.maxChannel is not None:
            if any(ch > self.maxChannel - 1 for ch in self.useChans):
                raise ChannelError('Requested channel is more than there are available')

        self.modules = []
        for chan in self.useChans:
            self.modules.append(configModule_klass(channel=chan, bank=self))
        super().__init__(**kwargs)

    def getConfigArray(self, cStr):
        ''' Iterate over modules getting the parameter at each

            Args:
                cStr (str): parameter name

            Returns:
                (np.ndarray): values for all modules,
                ordered based on the ordering of ``useChans``
        '''
        retVals = []
        for module in self.modules:
            retVals.append(module.getConfigParam(cStr))
        retArr = np.array(retVals)
        return retArr

    def setConfigArray(self, cStr, newValArr, forceHardware=False):
        ''' Iterate over modules setting the parameter to
            the corresponding array value.

            Values for *ALL* channels must be specified. To only change some,
            use the dictionary-based setter: ``setConfigDict``

            Args:
                cStr (str): parameter name
                newValArr (np.ndarray, list): values in same ordering as useChans
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
            moduleWroteToHardware = module.setConfigParam(cStr, val, forceHardware=forceHardware)
            bankWroteToHardware = bankWroteToHardware or moduleWroteToHardware
        return bankWroteToHardware

    def getConfigDict(self, cStr):
        '''
            Args:
                cStr (str): parameter name

            Returns:
                (dict): parameter on all the channels, keyed by channel number
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
                newValDict (array): dict keyed by channel number
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
        return self.setConfigArray(cStr, setArrayBuilder, forceHardware=forceHardware)

    @property
    def moduleIds(self):
        ''' list of module ID strings '''
        return list(self.getConfigArray('*IDN'))
