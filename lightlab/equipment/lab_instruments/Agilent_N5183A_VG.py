from . import VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import Configurable
from lightlab.laboratory.instruments import Clock

from lightlab import logger


class Agilent_N5183A_VG(VISAInstrumentDriver, Configurable):
    ''' Agilent N5183A Vector Generator

        `Manual <http://www.manualsbase.com/manual/608672/portable_generator/agilent_technologies/n5183a_mxg/>`__

        Usage: :any:`/ipynbs/Hardware/Clock.ipynb`

        Todo:
            Clock interface does not see sweepSetup and sweepEnable
    '''
    instrument_category = Clock

    def __init__(self, name='The 40GHz clock', address=None, **kwargs):
        VISAInstrumentDriver.__init__(self, name=name, address=address, **kwargs)
        Configurable.__init__(self)

    def amplitude(self, amp=None):
        ''' Amplitude is in dBm

            Args:
                amp (float): If None, only gets

            Returns:
                (float): output power amplitude
        '''
        if amp is not None:
            if amp > 15:
                print('Warning: Agilent N5183 ony goes up to +15dBm, given {}dBm.'.format(amp))
                amp = 15
            if amp < -20:
                print('Warning: Agilent N5183 ony goes down to -20dBm, given {}dBm.'.format(amp))
                amp = -20
            self.setConfigParam('POW:AMPL', '{} dBm'.format(amp))
        retStr = self.getConfigParam('POW:AMPL')
        return float(retStr.split(' ')[0])

    def frequency(self, freq=None):
        ''' Frequency is in Hertz

            **Setting the frequency takes you out of sweep mode automatically**

            Args:
                freq (float): If None, only gets

            Returns:
                (float): center frequency
        '''
        if freq is not None:
            if freq > 40e9:
                logger.warning('Agilent N5183 ony goes up to 40GHz, given %s GHz.', freq / 1e9)
                freq = 40e9
            if self.sweepEnable():
                logger.warning(
                    'Agilent N5183 was sweeping when you set frequency, moving to CW mode')
            self.setConfigParam('FREQ:CW', freq)  # Setting this automatically brings to CW mode
            # So we need to update this object's internal state too
            self.sweepEnable(False)
        return self.getConfigParam('FREQ:CW')

    def enable(self, enaState=None):
        ''' Enabler for the output

            Args:
                enaState (bool): If None, only gets

            Returns:
                (bool): is RF output enabled
        '''
        if enaState is not None:
            self.setConfigParam('OUTP:STAT', 'ON' if enaState else 'OFF')
        retStr = self.getConfigParam('OUTP:STAT')
        return retStr in [True, 'ON', 1, '1']

    def sweepSetup(self, startFreq, stopFreq, nPts=100, dwell=0.1):
        ''' Configure sweep. See instrument for constraints; they are not checked here.

            **Does not auto-enable. You must also call :meth:`sweepEnable`**

            Args:
                startFreq (float): lower frequency in Hz
                stopFreq (float): upper frequency in Hz
                nPts (int): number of points
                dwell (float): time in seconds to wait at each sweep point

            Returns:
                None
        '''
        self.setConfigParam('LIST:TYPE', 'STEP')
        self.setConfigParam('FREQ:STAR', startFreq)
        self.setConfigParam('FREQ:STOP', stopFreq)
        self.setConfigParam('SWE:POIN', nPts)
        self.setConfigParam('SWE:DWEL', dwell)

    def sweepEnable(self, swpState=None):
        ''' Switches between sweeping (True) and CW (False) modes

            Args:
                swpState (bool): If None, only gets, doesn't set.

            Returns:
                (bool): is the output sweeping
        '''
        if swpState is not None:
            self.setConfigParam('FREQ:MODE', 'LIST' if swpState else 'CW')
        return self.getConfigParam('FREQ:MODE') == 'LIST'
