from . import VISAInstrumentDriver
from lightlab.laboratory.instruments import LaserSource

import numpy as np
import time

from lightlab.equipment.abstract_drivers import ConfigModule, MultiModuleConfigurable
from lightlab.util.data import Spectrum
from lightlab import visalogger as logger


class ILX_Module(ConfigModule):
    ''' Handles 0 to 1 indexing
    '''
    def __init__(self, channel, **kwargs):
        kwargs['precedingColon'] = kwargs.pop('precedingColon', False)
        super().__init__(channel=channel + 1, **kwargs)


class ILX_7900B_LS(VISAInstrumentDriver, MultiModuleConfigurable):
    '''
        The laser banks (ILX 7900B laser source).

        `Manual <http://assets.newport.com/webDocuments-EN/images/70032605_FOM-79800F_IX.PDF>`_

        TODO:
            The overarching problem is that multiple users are likely
            to be using this one at the same time, different channels of course.
            Currently only one user can be using it at a time.

                * This class could be singleton, so that only one exists, and/or...

                * It could have a special property in that lockouts occur on a channel basis
    '''
    instrument_category = LaserSource
    maxChannel = 8

    # Time it takes to equilibrate on different changes, in seconds
    sleepOn = dict(OUT=3, WAVE=30, LEVEL=5)

    powerRange = np.array([-20, 13])

    def __init__(self, name='The laser source', address=None, useChans=None, **kwargs):
        kwargs['tempSess'] = kwargs.pop('tempSess', False)
        if 'dfbChans' in kwargs.keys():
            useChans = kwargs.pop('dfbChans')
        if useChans is None:
            logger.warning('No useChans specified for ILX_7900B_LS')
            useChans = list()
        VISAInstrumentDriver.__init__(self, name=name, address=address, **kwargs)
        MultiModuleConfigurable.__init__(self, useChans=useChans, configurableKlass=ILX_Module)

    def startup(self):
        self.close()  # For temporary serial access

    @property
    def dfbChans(self):
        ''' Returns the blocked out channels as a list '''
        return self.useChans

    def setConfigArray(self, cStr, newValArr, forceHardware=False):
        ''' Adds sleep functionality when there is a change
        '''
        wroteToHardware = super().setConfigArray(cStr, newValArr, forceHardware=forceHardware)
        if wroteToHardware:
            print('DFB settling for', self.sleepOn[cStr], 'seconds.')
            time.sleep(self.sleepOn[cStr])
            print('done.')

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
        ''' Sets a number of channel values and updates hardware

            Args:
                chanEnableDict (dict): A dictionary specifying some {channel: enabled}
        '''
        self.setConfigDict('OUT', chanEnableDict)

    def getChannelEnable(self):
        return self.getConfigDict('OUT')

    @property
    def wls(self):
        ''' wls is in nanometers '''
        return self.getConfigArray('WAVE')

    @wls.setter
    def wls(self, newWls):
        self.setConfigArray('WAVE', newWls)

    def setChannelWls(self, chanWavelengthDict):
        self.setConfigDict('WAVE', chanWavelengthDict)

    def getChannelWls(self):
        return self.getConfigDict('WAVE')

    @property
    def powers(self):
        ''' powers is in dBm '''
        return self.getConfigArray('LEVEL')

    @powers.setter
    def powers(self, newPowers):
        self.setConfigArray('LEVEL', newPowers)

    def setChannelPowers(self, chanPowerDict):
        self.setConfigDict('LEVEL', chanPowerDict)

    def getChannelPowers(self):
        return self.getConfigDict('LEVEL')

    @property
    def wlRanges(self):
        ''' wavelength tuples in (nm, nm)

            Returns:
                (list(tuple)): maximum ranges starting from lower wavelength
        '''
        minArr = self.getConfigArray('WAVEMIN')
        maxArr = self.getConfigArray('WAVEMAX')
        return tuple(zip(minArr, maxArr))

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

    def allOff(self):
        self.off()

    def allOn(self):
        self.enableState = np.ones(len(self.useChans))

    def off(self):
        self.enableState = np.zeros(len(self.useChans))
