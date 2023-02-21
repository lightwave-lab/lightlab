from . import AbstractDriver
from lightlab.util.io import ChannelError


# pylint: disable=no-member
class PowerMeterAbstract(AbstractDriver):
    '''
        For the `HP_8152A <http://www.lightwavestore.com/product_datasheet/OTI-OPM-L-030C_pdf4.pdf>`__
        and the `Advantest_Q8221 <https://www.advantest.com/documents/11348/146687/pdf_mn_EQ7761_PROGRAMMING_GUIDE.pdf>`__
    '''
    channelDescriptions = {1: 'A', 2: 'B', 3: 'A/B'}

    def validateChannel(self, channel):
        ''' Raises an error with info if not a valid channel
        '''
        if channel not in self.channelDescriptions.keys():
            raise ChannelError(
                'Not a valid PowerMeter channel. Use ' + ' '.join(
                    ('{} ({})'.format(k, v)
                     for k, v in self.channelDescriptions)))

    def powerLin(self, channel=1):
        return 10 ** (self.powerDbm(channel) / 10)

# pylint: enable=no-member
