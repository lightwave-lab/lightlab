from . import VISAInstrumentDriver

import numpy as np
from lightlab.util.data import Spectrum
import pyvisa as visa
import time
import logging
import struct
WIDEST_WLRANGE = [1516, 1565]

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

from functools import wraps
def patch_startup(func):
    @wraps(func)
    def new_func(self, *args, **kwargs):
        func(self, *args, **kwargs)
        with self.connected():
            self.send('++eot_enable 1')  # Append user defined character when EOI detected
            self.send('++eot_char 10')  # Append \n (ASCII 10) when EOI is detected
    return new_func

class Aragon_BOSA_400 (VISAInstrumentDriver):

    __apps = np.array(['BOSA', 'TLS', 'CA', 'MAIN'])
    __wlRange = None
    __currApp = None
    __avg = np.array(['4', '8', '12', '32', 'CONT'])
    __sMode = np.array(['HR', 'HS'])
    __CAmeasurement = np.array(['IL', 'RL', 'IL&RL'])
    __CAPolarization = np.array(['1', '2', 'INDEP', 'SIMUL'])
    MAGIC_TIMEOUT = 30

    def __init__(self, name='BOSA 400 OSA', address=None, **kwargs):
        """Initializes a fake VISA connection to the OSA.
        """
        kwargs['tempSess'] = kwargs.pop('tempSess', True)
        VISAInstrumentDriver.__init__(self, name=name, address=address, **kwargs)
        self.interface = self._session_object
        if address:
            using_prologix = address.startswith('prologix://')
            if using_prologix:
                old_startup = self.interface._prologix_rm.startup
                self.interface._prologix_rm.startup = patch_startup(old_startup)

    def stop(self):
        self.__currApp = str(self.ask('INST:STAT:MODE?'))
        if (self.__currApp == 'TLS'):
            self.write('SENS:SWITCH OFF')
        else:
            self.write('INST:STAT:RUN 0')

    def start(self):
        self.__currApp = str(self.ask('INST:STAT:MODE?'))
        if (self.__currApp == 'TLS'):
            self.write('SENS:SWITCH ON')
        else:
            self.write('INST:STAT:RUN 1')

    def startup(self):
        print(self.ask('*IDN?'))
        self.__currApp = str(self.ask('INST:STAT:MODE?'))
        print('Current application is ' + self.__currApp + '.')
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
        data = self.query(command)
        return data

    def application(self, app=None):
        if app is not None and app in self.__apps:
            try:
                if app != 'MAIN':
                    if self.__currApp != 'MAIN':
                        self.application('MAIN')
                    self.write('INST:STAT:MODE ' + str(app))
                    time.sleep(1)
                    self.start()
                    time.sleep(4)
                    if (str(app) == 'TLS'):
                        time.sleep(25)
                else:
                    self.stop()
                    self.write('INST:STAT:MODE ' + str(app))
            except Exception as e:
                self.__currApp = None
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
        newRangeClipped = np.clip(newRange, a_min=1516, a_max=1565)
        if np.any(newRange != newRangeClipped):
            print('Warning: Requested OSA wlRange out of range. Got', newRange)
        self.write("SENS:WAV:STAR " + str(np.min(newRangeClipped)) + " NM")
        self.write("SENS:WAV:STOP " + str(np.max(newRangeClipped)) + " NM")
        self.__wlRange = self.getWLrangeFromHardware()
        time.sleep(15)

    def ask_TRACE_ASCII(self):

        """ writes and reads data"""

        data = ""
        self.write("FORM ASCII")
        self.write("TRAC?")
        data = self.read_TRACE_ASCII()
        data = self.query("TRAC?", withTimeout)
#         data = self.query("IDN?")
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

    def spectrum(self, form='REAL'):
        x=list()
        y=list()
        if(form=='ASCII'):
            data = self.ask_TRACE_ASCII()
#             data = self.ask_TRACE_ASCII()
#             for i in range(0,len(data),2):
#                 x.append(data[i])
#                 y.append(data[i+1])
        elif(form=='REAL'):
            data = self.ask_TRACE_REAL()
            for i in range(0,len(data),1):
                x.append(data[i][0])
                y.append(data[i][1])
        else:
            log.exception("Please choose form 'REAL' or 'ASCII'")
#         return Spectrum(x, y, inDbm=True)
        return data

    def CAParam(self, avgCount='CONT', sMode='HR', noiseZero=False):
        if self.__currApp == 'CA' and avgCount in self.__avg and sMode in self.__sMode:
            try:
                self.write('SENS:AVER:COUN '+avgCount)
                self.write('SENS:AVER:STAT ON')
                self.write('SENS:WAV:SMOD '+sMode)
                if noiseZero:
                    self.write('SENS:NOIS')
            except Exception as e:
                log.exception("Could not set CA parameter")
                print(e)
                raise e
        else:
            log.exception("\nFor average count, please choose from ['4','8','12','32','CONT']\nFor speed mode, please choose from ['HR','HS']")

    def CAInput(self, meas='IL', pol='1'):
        if meas in self.__CAmeasurement and pol in self.__CAPolarization:
            try:
                self.write('INP:SPAR '+meas)
                self.write('INP:POL '+pol)
            except Exception as e:
                log.exception("Could not set input parameters to CA")
                print(e)
                raise e
        else:
            print("\nFor measurement type, please choose from ['IL', 'RL', 'IL&RL']\nFor polarization, please choose from ['1', '2', 'INDEP', 'SIMUL']")

    def TLSwavelength(self, waveLength=None):
        if waveLength is not None and self.__currApp == 'TLS':
            try:
                self.write('SENS:SWITCH ON')
                self.write('SENS:WAV:STAT '+str(waveLength)+' NM')
            except Exception as e:
                log.exception("Could not set the wavelength for TLS")
                print(e)
                raise e
        else:
            print("Please specify the wavelength and choose application TLS")