from . import VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import PowerMeterAbstract
from lightlab.laboratory.instruments import PowerMeter


class Advantest_Q8221_PM(VISAInstrumentDriver, PowerMeterAbstract):
    ''' Q8221 Optical Multi-power Meter

        `Manual <https://www.advantest.com/documents/11348/146687/pdf_mn_EQ7761_PROGRAMMING_GUIDE.pdf>`__

        Usage: :any:`/ipynbs/Hardware/PowerMeter.ipynb`
    '''
    instrument_category = PowerMeter
    channelDescriptions = {1: 'A', 2: 'B', 3: 'A/B'}

    def __init__(self, name='The Advantest power meter', address=None, **kwargs):
        VISAInstrumentDriver.__init__(self, name=name, address=address, **kwargs)

    def startup(self):  # pylint: disable=useless-super-delegation
        '''
        Behaves the same as super.

        Todo:
            Read manual and set the channels to DBM and default channel to A

            * Default read: ``"DBA-054.8686E+00\\r\\n"``
            * query("CH1"): ``"DBB-054.8686E+00\\r\\n"``

        '''
        super().startup()

    def open(self):
        super().open()
        self.mbSession.write_termination = ''
        self.mbSession.clear()

    def powerDbm(self, channel=1):
        ''' The detected optical power in dB on the specified channel

            Args:
                channel (int): Power Meter channel

            Returns:
                (double): Power in dB or dBm
        '''
        self.validateChannel(channel)
        self.write('CH' + str(channel))
        powStr = self.query('CH' + str(channel))
        return float(powStr[3:])
