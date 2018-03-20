from . import VISAInstrumentDriver
from lightlab.util.io import ChannelError


class Advantest_Q8221_PM(VISAInstrumentDriver):
    """ Q8221 Optical Multi-power Meter
    """

    def __init__(self, name='The power meter', address=None, **kwargs):
        super().__init__(name=name, address=address, **kwargs)
        # self.selectedChan = int(self.query('CH?'))

        # TODO: Read manual and set the channels to DBM and default channel to A
        # Default read: "DBA-054.8686E+00\r\n"
        # query("CH1"): "DBB-054.8686E+00\r\n"

    def open(self):
        super().open()
        self.mbSession.write_termination = ''
        self.mbSession.clear()

    def query(self, *args, **kwargs):
        retRaw = super().query(*args, **kwargs)
        return retRaw

    def powerDbm(self, channel=1):
        """Returns detected optical power in dB on the specified channel
        :param: channel: Power Meter channel (1 or 2)
        :type: channel: int
        :rtype: double
        """
        if channel not in range(1, 4):
            raise ChannelError(
                'Not a valid PowerMeter channel. Use 1(A), 2(B), or 3(A/B)')
        # Sometimes it gets out of range, so we have to try a few times
        self.write('CH' + str(channel))
        powStr = self.query('CH' + str(channel))
        return float(powStr[3:])

        # for trial in range(10):
        #     self.write('CH' + str(channel))
        #     # powStr = self.query('TRG')
        #     powStr = self.query('CH' + str(channel))
        #     return float(powStr[3:])

        # else:
        #     raise Exception('Power meter values are unreasonable')

    def powerLin(self, channel=1):
        return 10 ** (self.powerDbm(channel) / 10)


