from . import VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import Configurable
from lightlab.laboratory.instruments import Keithley

import numpy as np
import time
from lightlab import logger


class SR830(VISAInstrumentDriver, Configurable):
    ''' A SR830 driver.
        `Manual: https://www.thinksrs.com/downloads/pdfs/manuals/SR830m.pdf
        Based on https://github.com/LabGUI/LabGUI/blob/master/LabDrivers/SR830.py
        Capable of performing homodyne measurements, including sourcing.
        The names of settings and variables is made to match the labels on the instrument 
        e.g. phase is an output that can be set or read. To read phase in the readout, I use "theta" as labelled on the instrument
    '''

    def __init__(self, name=None, address=None, **kwargs):
        '''
        '''
        VISAInstrumentDriver.__init__(self, name=name, address=address, **kwargs)
        Configurable.__init__(self, headerIsOptional=False, verboseIsOptional=False)
        
    # Readouts (inputs)
    
    def getX(self):
        return self.getConfigParam('OUTP?1')
    
    def getY(self):
        return self.getConfigParam('OUTP?2')
    
    def getR(self):
        return self.getConfigParam('OUTP?3')
    
    def getTheta(self):
        return self.getConfigParam('OUTP?4')
    
    def getAUX1(self):
        return self.getConfigParam('OAUX?1')
    
    def getAUX2(self):
        return self.getConfigParam('OAUX?2')
    
    def getAUX3(self):
        return self.getConfigParam('OAUX?3')
    
    def getAUX4(self):
        return self.getConfigParam('OAUX?4')
    
    # Outputs (and reading them)
    
    def setFreq(self, freq):
        self.setConfigParam('FREQ ', freq)
    
    def getFreq(self):
        return self.getConfigParam('FREQ?')
    
    def setAmpl(self, amplitude):
        self.setConfigParam('SLVL ', amplitude)
        
    def getAmpl(self):
        return self.getConfigParam('SLVL?')
    
    def setPhase(self, phase):
        self.setConfigParam('PHAS ', phase)
        
    def getPhase(self):
        return self.getConfigParam('PHAS?')
    
    # Settings
    
    def setScale(self, scale):
        self.setConfigParam('SENS ', scale)
        
    def setRefInternal(self, boolean):
        """
           Whether the internal reference or an external one is used 
        """
        if boolean == True:
            self.setConfigParam('FMOD 1')
        else:
            self.setConfigParam('FMOD 0')
            
    def setHarm(self, harm):
        self.setConfigParam('HARM ', harm)