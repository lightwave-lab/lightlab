from . import VISAInstrumentDriver

import numpy as np
from lightlab.util.data import Spectrum
import visa
import time
import logging
import struct
WIDEST_WLRANGE = [1525, 1565]

# create logger
log = logging.getLogger(__name__)

if(len(log.handlers) == 0): # check if the logger already exists
    # create logger
    log.setLevel(logging.INFO)
    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # add formatter to ch
    ch.setFormatter(formatter)
    # add ch to logger
    log.addHandler(ch)

class Aragon_BOSA_400 (VISAInstrumentDriver):

    __apps = np.array(['BOSA', 'TLS', 'CA', 'MAIN'])
    __wlRange = None
    MAGIC_TIMEOUT = 30

    def __init__(self, name='BOSA 400 OSA', address=None, **kwargs):
        VISAInstrumentDriver.__init__(self, name=name, address=address, **kwargs)
        self.interface = visa.ResourceManager().open_resource(address)

    def __del__(self):
        try:
            self.interface.close()
        except Exception as e:
            logger.warning("Could not close instrument correctly: exception %r", e.message)

    def startup(self):
        print(self.ask('*IDN?'))
        print('Please choose application from["BOSA", "TLS", "CA", "MAIN"]')

    def write(self, command=None):
        if command is not None:
            log.debug("Sending command '" + command + "' using GPIB interface...")
            try:
                self.interface.write(command)
            except Exception as e:
                log.exception("Could not send data, command %r",command)
                print(e)
                raise e

    def read(self):
        log.debug("Reading data using GPIB interface...")
        while(1):
            try:
                message = self.interface.read()
                if(message!=''):
                    break
            except Exception as e:
                log.exception("Could not read data")
                print(e)
                raise e
        log.debug("All data readed!")
        log.debug("Data received: " + message)
        return message

    def ask(self, command):

        """ writes and reads data"""

        data = ""
        self.write(command)
        data = self.read()
        return data

    def application(self, app=None):
        if app is not None and app in self.__apps:
            try:
                if app != 'MAIN':
                    self.write('INST:STAT:MODE ' + str(app))
                    self.write('INST:STAT:RUN 1')
                else:
                    self.write('INST:STAT:RUN 0')
                    self.write('INST:STAT:MODE ' + str(app))
            except Exception as e:
                log.exception("Could not choose the application")
                print(e)
                raise e

    def getWLrangeFromHardware(self):
        theRange = [0] * 2
        theRange[0] = float(self.ask("SENS:WAV:STOP?"))
        theRange[1] = float(self.ask("SENS:WAV:STAR?"))
        return theRange

    @property
    def wlRange(self):
        if self.__wlRange is None:
            self.__wlRange = self.getWLrangeFromHardware()
        return self.__wlRange

    @wlRange.setter
    def wlRange(self, newRange):
        newRangeClipped = np.clip(newRange, a_min=1525, a_max=1565)
        if np.any(newRange != newRangeClipped):
            print('Warning: Requested OSA wlRange out of range. Got', newRange)
        self.write("SENS:WAV:CENT " + str((np.max(newRangeClipped)+np.min(newRangeClipped))/2) + " NM")
        self.write("SENS:WAV:SPAN " + str(np.max(newRangeClipped)-np.min(newRangeClipped)) + " NM")
        self.__wlRange = self.getWLrangeFromHardware()

    def ask_TRACE_ASCII(self):

        """ writes and reads data"""

        data = ""
        self.write("FORM ASCII")
        self.write("TRAC?")
        data = self.read_TRACE_ASCII()
        return data

    def ask_TRACE_REAL(self):
        data = ""
        self.write("FORM REAL")
        NumPoints = int(self.ask("TRACE:DATA:COUNT?"))
        self.write("TRAC?")
        data = self.read_TRACE_REAL_GPIB(NumPoints)
        return data

    def read_TRACE_ASCII(self):

        """ read something from device"""

        log.debug("Reading data using GPIB interface...")
        while(1):
            try:
                Byte_data = self.interface.read_ascii_values(converter='f', separator=',', container=list,delay=None)
                if((Byte_data != '')):
                    break
            except Exception as e:
                log.exception("Could not read data")
                print(e)
                raise e
        return Byte_data

    def read_TRACE_REAL_GPIB(self,numPoints):

        """ read something from device"""
        log.debug("Reading data using GPIB interface...")
        while(1):
            try:
                msgLength = int(numPoints*2*8)
                Byte_data = self.interface.read_bytes(msgLength, chunk_size=None, break_on_termchar=False)
                c, r = 2, int(numPoints)
                Trace= [[0 for x in range(c)] for x in range(r)]
                for x in range(0,int(numPoints)):
                   Trace[x][0]=struct.unpack('d', Byte_data[(x)*16:(x)*16+8])
                   Trace[x][1] = struct.unpack('d', Byte_data[(x) * 16+8:(x+1) * 16 ])
                if((Byte_data != '')):
                    break
            except Exception as e:
                log.exception("Could not read data")
                print(e)
                raise e
        return Trace

    def spectrum(self, form):
        x=list()
        y=list()
        if(form=='REAL'):
            data = self.ask_TRACE_ASCII()
            for i in range(0,len(data),2):
                x.append(data[i])
                y.append(data[i+1])
        elif(form=='ASCII'):
            data = self.ask_TRACE_REAL()
            for i in range(0,len(data),1):
                x.append(data[i][0])
                y.append(data[i][1])
        else:
            log.exception("Please choose form 'REAL' or 'ASCII'")
        return Spectrum(x, y, inDbm=True)
