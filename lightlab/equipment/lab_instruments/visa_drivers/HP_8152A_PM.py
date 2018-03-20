from . import VISAInstrumentDriver
from lightlab.util import io


class HP_8152A_PM(VISAInstrumentDriver):
    """ HP8152A power meter

        `Manual <http://www.lightwavestore.com/product_datasheet/OTI-OPM-L-030C_pdf4.pdf>`_
    """
    overrideReadDoublingCheck = False  # This weird thing that happens sometimes is dealt with automatically unless this is True
    # def __init__(self, address=18, hostID='andromeda'):
    #     super().__init__('The power meter', address, hostNS[hostID])

    def __init__(self, name='The power meter', address=None, **kwargs):
        super().__init__(name=name, address=address, **kwargs)
        # self.selectedChan = int(self.query('CH?'))

    def startup(self):
        self.close()
        self.write('T1')  # single shot mode to make sure averaging occurs correctly
        # TODO: allow a rapid continuous mode that just spits out numbers

    def open(self):
        super().open()
        self.mbSession.write_termination = ''
        self.mbSession.clear()

    @staticmethod
    def proccessWeirdRead(readString):
        ''' we assume that the values encountered are negative and have two digits before and after decimal point

            Returns:
                (float): the dB value
        '''
        # is there a negative sign?
        unsignStrArr = readString.split('-')
        minus = len(unsignStrArr) > 1
        try:
            decSplit = unsignStrArr[-1].split('.')
            onesHundredthsStrs = [decSplit[0], decSplit[-1]]
        except ValueError:
            raise ValueError('Power meter did not find a decimal point in return string')
        # There are now several options for when we expect two digits
        # there is an ambiguity when there are two digits, so we assume they are both intended
        onesHundredthsVals = [0] * 2
        for i, s in enumerate(onesHundredthsStrs):
            if len(s) in [1, 2]:
                onesHundredthsVals[i] = float(s)
            elif len(s) in [3, 4]:  # at least one has been repeated, so skip the middle (3) or seconds (4)
                onesHundredthsVals[i] = float(s[::2])
            else:
                raise ValueError('Too many digits one one side of the decimal point')
        # reconstitute from floats
        val = onesHundredthsVals[0] + .01 * onesHundredthsVals[1]
        if minus:
            val *= -1
        return val

    def query(self, *args, **kwargs):
        retRaw = super().query(*args, **kwargs)
        return retRaw

        # Check for this weird thing where characters are printed twice

    def powerDbm(self, channel=1):
        """Returns detected optical power in dB on the specified channel
        :param: channel: Power Meter channel (1 or 2)
        :type: channel: int
        :rtype: double
        """
        if channel not in range(1, 4):
            raise io.ChannelError('Not a valid PowerMeter channel. Use 1(A), 2(B), or 3(A/B)')
        for trial in range(10):  # Sometimes it gets out of range, so we have to try a few times
            self.write('CH' + str(channel))
            powStr = self.query('TRG')
            if self.overrideReadDoublingCheck:
                v = self.proccessWeirdRead(powStr)
            else:
                v = float(powStr)
            if abs(v) < 999:  # check if it's reasonable
                self.selectedChan = channel
                return v
        else:
            raise Exception('Power meter values are unreasonable')

    def powerLin(self, channel=1):
        return 10 ** (self.powerDbm(channel) / 10)
