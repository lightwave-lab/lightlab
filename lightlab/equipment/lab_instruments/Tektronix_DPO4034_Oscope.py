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
    __recLenParam = 'HORIZONTAL:RECORDLENGTH'
    __clearBeforeAcquire = False
    __measurementSourceParam = 'SOURCE1'
    __runModeParam = 'ACQUIRE:STOPAFTER'
    __runModeSingleShot = 'SEQUENCE'
    __yScaleParam = 'YMULT'
