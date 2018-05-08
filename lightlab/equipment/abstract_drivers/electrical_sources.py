import numpy as np

from lightlab.util.io import ChannelError, RangeError
from lightlab import logger


class MultiModalSource(object):
    ''' Checks modes for sources with multiple ways to specify.

        Also checks ranges

        Default class constants come from NI PCI source array
    '''
    supportedModes = {'milliamp', 'amp', 'mwperohm', 'wattperohm', 'volt', 'baseunit'}
    baseUnitBounds = [0, 1]  # Scaled voltage
    baseToVoltCoef = 10  # This ends up setting the volt bounds
    v2maCoef = 4  # current (milliamps) = v2maCoef * voltage (volts)
    exceptOnRangeError = False  # If False, it will constrain it and print a warning

    @classmethod
    def enforceRange(cls, val, mode):
        ''' Returns clipped value. Raises RangeError
        '''
        bnds = [cls.baseUnit2val(vBnd, mode) for vBnd in cls.baseUnitBounds]
        enforcedValue = np.clip(val, *bnds)
        if enforcedValue != val:
            logger.warning('Warning: value out of range was constrained.\n'
                           'Requested %s.'
                           'Allowed range is %s in %s s.', val, bnds, mode)
            if cls.exceptOnRangeError:
                if val < min(bnds):
                    violation_direction = 'low'
                elif val > max(bnds):
                    violation_direction = 'high'
                else:
                    violation_direction = None
                raise RangeError('Current sources requested out of range.', violation_direction)
        return enforcedValue

    @classmethod
    def _checkMode(cls, mode):
        ''' Returns mode in lower case
        '''
        if mode not in cls.supportedModes:
            raise TypeError('Invalid mode: ' + str(mode) + '. Valid: ' + str(cls.supportedModes))
        else:
            return mode.lower()

    @classmethod
    def val2baseUnit(cls, value, mode):
        """Converts to the voltage value that will be applied at the PCI board
        Depends on the current mode state of the instance

            Args:
                value (float or dict)
        """
        mode = cls._checkMode(mode)
        valueWasDict = isinstance(value, dict)
        if not valueWasDict:
            value = {-1: value}
        baseVal = dict()
        for ch, vEl in value.items():
            if mode == 'baseunit':
                baseVal[ch] = vEl
            if mode == 'volt':
                baseVal[ch] = vEl / cls.baseToVoltCoef
            elif mode == 'milliamp':
                baseVal[ch] = cls.val2baseUnit(vEl, 'volt') / cls.v2maCoef
            elif mode == 'amp':
                baseVal[ch] = cls.val2baseUnit(vEl, 'milliamp') * 1e3
            elif mode == 'wattperohm':
                baseVal[ch] = np.sign(vEl) * np.sqrt(abs(cls.val2baseUnit(vEl, 'amp')))
            elif mode == 'mwperohm':
                baseVal[ch] = cls.val2baseUnit(vEl, 'wattperohm') / 1e3
        if valueWasDict:
            return baseVal
        else:
            return baseVal[-1]

    @classmethod
    def baseUnit2val(cls, baseVal, mode):
        """Converts the voltage value that will be applied at the PCI board back into the units of th instance
        This is useful for bounds checking

            Args:
                baseVal (float or dict)
        """
        mode = cls._checkMode(mode)
        baseValWasDict = isinstance(baseVal, dict)
        if not baseValWasDict:
            baseVal = {-1: baseVal}
        value = dict()
        for ch, bvEl in baseVal.items():
            if mode == 'baseunit':
                value[ch] = bvEl
            elif mode == 'volt':
                value[ch] = bvEl * cls.baseToVoltCoef
            elif mode == 'milliamp':
                value[ch] = cls.baseUnit2val(bvEl, 'volt') * cls.v2maCoef
            elif mode == 'amp':
                value[ch] = cls.baseUnit2val(bvEl, 'milliamp') * 1e-3
            elif mode == 'wattperohm':
                value[ch] = np.sign(bvEl) * (cls.baseUnit2val(bvEl, 'amp')) ** 2
            elif mode == 'mwperohm':
                value[ch] = cls.baseUnit2val(bvEl, 'wattperohm') * 1e3
        if baseValWasDict:
            return value
        else:
            return value[-1]


class MultiChannelSource(object):
    """ This thing basically holds a dict state and provides some critical methods

        There is no mode

        Checks for channel compliance. Handles range exceptions
    """
    maxChannel = None  # number of dimensions that the current sources are expecting

    def __init__(self, useChans=None, **kwargs):
        if useChans is None:
            logger.warning('No useChans specified for MultichannelSource')
            useChans = list()
        self.useChans = useChans
        self.stateDict = dict([ch, 0] for ch in self.useChans)

        # Check that the requested channels are available to be blocked out
        if self.maxChannel is not None:
            if any(ch > self.maxChannel - 1 for ch in self.useChans):
                raise ChannelError(
                    'Requested channel is more than there are available')
        super().__init__(**kwargs)

    @property
    def elChans(self):
        ''' Returns the blocked out channels as a list '''
        return self.useChans

    def setChannelTuning(self, chanValDict):
        ''' Sets a number of channel values and updates hardware

            Args:
                chanValDict (dict): A dictionary specifying {channel: value}
                waitTime (float): time in ms to wait after writing, default (None) is defined in the class

            Returns:
                (bool): was there a change in value
        '''
        if type(chanValDict) is not dict:
            raise TypeError(
                'The argument for setChannelTuning must be a dictionary')

        # Check channels
        for chan in chanValDict.keys():
            if chan not in self.stateDict.keys():
                raise ChannelError('Channel index not blocked out. ' +
                                   'Requested ' + str(chan) +
                                   ', Available ' + str(self.stateDict.keys()))

        # Change our *internal* state
        self.stateDict.update(chanValDict)

    def getChannelTuning(self):
        ''' The inverse of setChannelTuning

            Args:
                mode (str): units of the value in ('mwperohm', 'milliamp', 'volt')

            Returns:
                (dict): the full state of blocked out channels in units determined by mode argument
        '''
        return self.stateDict.copy()

    def off(self, *setArgs):
        """Turn all voltages to zero, but maintain the session
        """
        self.setChannelTuning(dict([ch, 0] for ch in self.stateDict.keys()), *setArgs)
