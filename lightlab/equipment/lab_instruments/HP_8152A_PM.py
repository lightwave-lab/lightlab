from . import VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import PowerMeterAbstract
from lightlab.laboratory.instruments import PowerMeter


class HP_8152A_PM(VISAInstrumentDriver, PowerMeterAbstract):
    ''' HP8152A power meter

        `Manual <http://www.lightwavestore.com/product_datasheet/OTI-OPM-L-030C_pdf4.pdf>`__

        Usage: :any:`/ipynbs/Hardware/PowerMeter.ipynb`

        Todo:
            Maybe allow a rapid continuous mode that just spits out numbers ('T0')
    '''
    instrument_category = PowerMeter
    channelDescriptions = {1: 'A', 2: 'B', 3: 'A/B'}
    doReadDoubleCheck = False

    def __init__(self, name='The HP power meter', address=None, **kwargs):
        VISAInstrumentDriver.__init__(self, name=name, address=address, **kwargs)

    def startup(self):
        self.close()
        self.write('T1')  # single shot mode to make sure averaging occurs correctly

    def open(self):
        super().open()
        self.mbSession.write_termination = ''
        self.mbSession.clear()

    @staticmethod
    def proccessWeirdRead(readString):
        ''' The HP 8152 *sometimes* sends double characters.
            This tries to fix it based on reasonable value ranges.

            We assume that the values encountered have a decimal point
            and have two digits before and after the decimal point

            Arg:
                readString (str): what is read from query('TRG')

            Returns:
                (str): checked string
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
        return str(val)

    def query(self, *args, **kwargs):  # pylint: disable=arguments-differ
        ''' Conditionally check for read character doubling
        '''
        retRaw = super().query(*args, **kwargs)  # pylint: disable=arguments-differ
        if self.doReadDoubleCheck:
            return self.proccessWeirdRead(retRaw)
        else:
            return retRaw

    def powerDbm(self, channel=1):
        ''' The detected optical power in dB on the specified channel

            Args:
                channel (int): Power Meter channel

            Returns:
                (double): Power in dB or dBm
        '''
        self.validateChannel(channel)
        trial = 0
        while trial < 10:  # Sometimes it gets out of range, so we have to try a few times
            self.write('CH' + str(channel))
            powStr = self.query('TRG')
            v = float(powStr)
            if abs(v) < 999:  # check if it's reasonable
                break
            else:
                # continue
                trial += 1
        else:
            raise Exception('Power meter values are unreasonable.'
                            ' Got {}'.format(v))
        return v
