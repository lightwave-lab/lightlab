from ..visa_drivers import VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import TDS, DSA, DPO

class Tektronix_TDS6154C_Oscope(VISAInstrumentDriver, TDS):
    ''' See abstract driver for description

        `Manual <http://www.tek.com/sites/tek.com/files/media/media/resources/55W_14873_9.pdf>`_
    '''
    totalChans = 4
    def __init__(self, name='Real time scope', address=None, **kwargs):
        super().__init__(name=name, address=address, **kwargs)


class Tektronix_CSA8000_CAS(VISAInstrumentDriver, DSA):
    ''' Not necessarily tested with the new abstract driver
    '''
    totalChans = 8
    def __init__(self, name='Communication analyzer scope', address=None, **kwargs):
        super().__init__(name=name, address=address, **kwargs)


class Tektronix_DSA8300_Oscope(VISAInstrumentDriver, DSA):
    ''' See abstract driver for description

        `Manual <http://www.tek.com/download?n=975655&f=190886&u=http%3A%2F%2Fdownload.tek.com%2Fsecure%2FDifferential-Channel-Alignment-Application-Online-Help.pdf%3Fnvb%3D20170404035703%26amp%3Bnva%3D20170404041203%26amp%3Btoken%3D0ccdfecc3859114d89c36>`_
    '''
    totalChans = 8
    def __init__(self, name='Sampling scope', address=None, **kwargs):
        super().__init__(name=name, address=address, **kwargs)


class Tektronix_DPO4032_Oscope(VISAInstrumentDriver, DPO):
    ''' See abstract driver for description

        `Manual <http://websrv.mece.ualberta.ca/electrowiki/images/8/8b/MSO4054_Programmer_Manual.pdf>`_
    '''
    totalChans = 2
    def __init__(self, name='Slow DPO scope with 2 channels', address=None, **kwargs):
        super().__init__(name=name, address=address, **kwargs)


class Tektronix_DPO4034_Oscope(VISAInstrumentDriver, DPO):
    ''' See abstract driver for description

        `Manual <http://websrv.mece.ualberta.ca/electrowiki/images/8/8b/MSO4054_Programmer_Manual.pdf>`_
    '''
    totalChans = 4
    def __init__(self, name='Slow DPO scope with 4 channels', address=None, **kwargs):
        super().__init__(name=name, address=address, **kwargs)
