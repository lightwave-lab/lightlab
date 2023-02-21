from . import VISAInstrumentDriver
from lightlab.laboratory.instruments import LaserSource

import numpy as np
import time

from lightlab.equipment.abstract_drivers import ConfigModule, MultiModuleConfigurable
from lightlab.util.data import Spectrum
from lightlab import logger


class ILX_Module(ConfigModule):
    ''' Handles 0 to 1 indexing
    '''
    def __init__(self, channel, **kwargs):
        kwargs['precedingColon'] = kwargs.pop('precedingColon', False)
        super().__init__(channel=channel + 1, **kwargs)


class ILX_7900B_LS(VISAInstrumentDriver, MultiModuleConfigurable):
    '''
        The laser banks (ILX 7900B laser source).
        Provides array-based and dict-based setters/getters for
            * whether laser is on or off (``enableState``)
            * tunable wavelength output (``wls``)
            * output power in dBm (``powers``)

        Setting/getting logic is implemented in ``MultiModuleConfigurable``,
        which treats the channels as independent ``ConfigModules``'s. This means
        that hardware communication is lazy -- parameter values are cached,
        and messages are only sent when they are unknown or when they change.

        `Manual <http://assets.newport.com/webDocuments-EN/images/70032605_FOM-79800F_IX.PDF>`_

        Usage: :ref:`/ipynbs/Hardware/LaserSources-ILX.ipynb`

        Todo:
            Multiple users at the same time is desirable. We are close.
            Non blocked-out channels are never touched, but there are still two issues
                * Fundamental: VISA access with two python processes could collide
                * Inconvenience: Have to create two different labstate instruments
                    with different ``useChans`` for what is actually
                    one instrument -- maybe a slice method?
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
        MultiModuleConfigurable.__init__(self, useChans=useChans, configModule_klass=ILX_Module)

    def startup(self):
        self.close()  # For temporary serial access

    @property
    def dfbChans(self):
        ''' Returns the blocked out channels as a list

            Currently, this is not an essentialProperty, so you
            have to access like::

                ch = LS.driver.dfbChans

            Returns:
                (list): channel numbers, 0-indexed
        '''
        return self.useChans

    def setConfigArray(self, cStr, newValArr, forceHardware=False):
        ''' When any configuration is set, there is an equilibration time.

            This adds sleep functionality, only when there is a change,
            for an amount determined by the ``sleepOn`` class attribute.
        '''
        wroteToHardware = super().setConfigArray(cStr, newValArr, forceHardware=forceHardware)
        if wroteToHardware:
            print('DFB settling for', self.sleepOn[cStr], 'seconds.')
            time.sleep(self.sleepOn[cStr])
            print('done.')

    # Module-level parameter setters and getters.
    @property
    def enableState(self):
        '''
            Returns:
                (np.ndarray): enable states ordered like useChans
        '''
        return self.getConfigArray('OUT')

    @enableState.setter
    def enableState(self, newState):
        ''' Are lasers on or off? Provides range check.

            Args:
                newState (list, np.ndarray): enable values which must be 0 or 1
        '''

        for ena in newState:
            if ena not in [0, 1]:
                raise ValueError('Laser states can only be 0 or 1. ' +
                                 'Got {}'.format(newState))
        self.setConfigArray('OUT', newState)

    def setChannelEnable(self, chanEnableDict):
        ''' Sets only some channel values with dict keyed by useChans,
            e.g. ``chanEnableDict={0: 1, 2: 0}``

            Args:
                chanEnableDict (dict): A dictionary keyed by channel with values 0 or 1
        '''
        self.setConfigDict('OUT', chanEnableDict)

    def getChannelEnable(self):
        '''
            Returns:
                (dict): all channel enable states, keyed by useChans
        '''
        return self.getConfigDict('OUT')

    @property
    def wls(self):
        '''
            Returns:
                (np.ndarray): laser wavelengths in nanometers ordered like useChans
        '''
        return self.getConfigArray('WAVE')

    @wls.setter
    def wls(self, newWls):
        ''' Laser wavelengths. Provides range check.

            Args:
                newWls (list, np.ndarray): wavelengths in nanometers
        '''
        for iCh, wl in enumerate(newWls):
            wlRanges = self.wlRanges[iCh]
            if wl < wlRanges[0]:
                logger.warning('Wavelength out of range was constrained:\n' +
                               'Requested: {:.2f}nm '.format(wl) +
                               'Minimum: {:.2f}nm.'.format(wlRanges[0]))
                newWls[iCh] = wlRanges[0]
            if wl > wlRanges[1]:
                logger.warning('Wavelength out of range was constrained:\n' +
                               'Requested: {:.2f}nm '.format(wl) +
                               'Maximum: {:.2f}nm.'.format(wlRanges[1]))
                newWls[iCh] = wlRanges[1]
        self.setConfigArray('WAVE', newWls)

    def setChannelWls(self, chanWavelengthDict):
        ''' Sets only some channel values with dict keyed by useChans,
            e.g. ``chanWavelengthDict={0: 1550.5, 2: 1551}``

            Args:
                chanWavelengthDict (dict): A dictionary keyed by channel with nanometer values
        '''
        self.setConfigDict('WAVE', chanWavelengthDict)

    def getChannelWls(self):
        '''
            Returns:
                (dict): all channel wavelengths, keyed by useChans
        '''
        return self.getConfigDict('WAVE')

    @property
    def powers(self):
        ''' Laser powers

            Returns:
                (np.ndarray): laser output powers in dBm, ordered like useChans
        '''
        return self.getConfigArray('LEVEL')

    @powers.setter
    def powers(self, newPowers):
        ''' Laser powers. Provides range check.

            Args:
                newPowers (list, np.ndarray): power in dBm
        '''
        for iCh, level in enumerate(newPowers):
            if level < self.powerRange[0]:
                logger.warning('Power out of range was constrained:\n' +
                               'Requested: {:.2f}dBm '.format(level) +
                               'Minimum: {:.2f}dBm.'.format(self.powerRange[0]))
                newPowers[iCh] = self.powerRange[0]
            if level > self.powerRange[1]:
                logger.warning('Power out of range was constrained:\n' +
                               'Requested: {:.2f}dBm '.format(level) +
                               'Maximum: {:.2f}dBm.'.format(self.powerRange[1]))
                newPowers[iCh] = self.powerRange[1]
        self.setConfigArray('LEVEL', newPowers)

    def setChannelPowers(self, chanPowerDict):
        ''' Sets only some channel values with dict keyed by useChans,
            e.g. ``chanPowerDict={0: 13, 2: -10}``

            Args:
                chanPowerDict (dict): A dictionary keyed by channel with dBm values
        '''
        self.setConfigDict('LEVEL', chanPowerDict)

    def getChannelPowers(self):
        '''
            Returns:
                (dict): all channel powers, keyed by useChans
        '''
        return self.getConfigDict('LEVEL')

    @property
    def wlRanges(self):
        '''
            Min/max wavelengths than can be covered by each channl.
            Wavelengths in nm.

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
        ordi = self.powers.copy()
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
