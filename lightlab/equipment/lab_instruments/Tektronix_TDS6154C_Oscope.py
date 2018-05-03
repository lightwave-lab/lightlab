from . import VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import TekScopeAbstract
from lightlab.laboratory.instruments import Oscilloscope


class Tektronix_TDS6154C_Oscope(VISAInstrumentDriver, TekScopeAbstract):
    ''' Real time scope.
        See abstract driver for description.

        `Manual <http://www.tek.com/sites/tek.com/files/media/media/resources/55W_14873_9.pdf>`__

        Usage: :any:`/ipynbs/Hardware/Oscilloscope.ipynb`

    '''
    instrument_category = Oscilloscope

    totalChans = 4
    # Similar to the DSA, except
    _recLenParam = 'HORIZONTAL:RECORDLENGTH'  # this is different from DSA
    _clearBeforeAcquire = True
    _measurementSourceParam = 'SOURCE1:WFM'
    _runModeParam = 'ACQUIRE:STOPAFTER:MODE'
    _runModeSingleShot = 'CONDITION'
    _yScaleParam = 'YMULT'                    # this is different from DSA

    def __init__(self, name='The TDS scope', address=None, **kwargs):
        VISAInstrumentDriver.__init__(self, name=name, address=address, **kwargs)
        TekScopeAbstract.__init__(self)

    def __setupSingleShot(self, isSampling, forcing=False):
        ''' Additional DSA things needed to put it in the right mode.
            If it is not sampling, the trigger source should always be external
        '''
        super()._setupSingleShot(isSampling, forcing)
        self.setConfigParam('ACQUIRE:STOPAFTER:CONDITION',
                            'ACQWFMS' if isSampling else'AVGCOMP',
                            forceHardware=forcing)
        if isSampling:
            self.setConfigParam('ACQUIRE:STOPAFTER:COUNT', '1', forceHardware=forcing)
        if not isSampling:
            self.setConfigParam('TRIGGER:SOURCE', 'EXTDIRECT', forceHardware=forcing)
