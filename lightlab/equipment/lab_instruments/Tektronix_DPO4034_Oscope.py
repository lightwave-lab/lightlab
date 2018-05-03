from . import VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import TekScopeAbstract
from lightlab.laboratory.instruments import Oscilloscope


class Tektronix_DPO4034_Oscope(VISAInstrumentDriver, TekScopeAbstract):
    ''' Slow DPO scope. See abstract driver for description

        `Manual <http://websrv.mece.ualberta.ca/electrowiki/images/8/8b/MSO4054_Programmer_Manual.pdf>`__

        Usage: :any:`/ipynbs/Hardware/Oscilloscope.ipynb`

    '''
    instrument_category = Oscilloscope

    totalChans = 4
    _recLenParam = 'HORIZONTAL:RECORDLENGTH'
    _clearBeforeAcquire = False
    _measurementSourceParam = 'SOURCE1'
    _runModeParam = 'ACQUIRE:STOPAFTER'
    _runModeSingleShot = 'SEQUENCE'
    _yScaleParam = 'YMULT'

    def __init__(self, name='The DPO scope', address=None, **kwargs):
        VISAInstrumentDriver.__init__(self, name=name, address=address, **kwargs)
        TekScopeAbstract.__init__(self)

    def wfmDb(self):  # pylint: disable=arguments-differ
        print('wfmDb is not working yet with DPOs')
