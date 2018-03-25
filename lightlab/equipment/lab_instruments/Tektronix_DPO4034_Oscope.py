from . import VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import TekScopeAbstract
from lightlab.laboratory.instruments import Oscilloscope

class Tektronix_DPO4034_Oscope(VISAInstrumentDriver, TekScopeAbstract):
    ''' Slow DPO scope.
        See abstract driver for description

        `Manual <http://websrv.mece.ualberta.ca/electrowiki/images/8/8b/MSO4054_Programmer_Manual.pdf>`__
    '''
    instrument_category = Oscilloscope

    totalChans = 4
    _recLenParam = 'HORIZONTAL:RECORDLENGTH'
    _clearBeforeAcquire = False
    _measurementSourceParam = 'SOURCE1'
    _runModeParam = 'ACQUIRE:STOPAFTER'
    _runModeSingleShot = 'SEQUENCE'
    _yScaleParam = 'YMULT'

    def wfmDb(self, chan, nWfms, untriggered=False):
        print('wfmDb is not working yet with DPOs')
