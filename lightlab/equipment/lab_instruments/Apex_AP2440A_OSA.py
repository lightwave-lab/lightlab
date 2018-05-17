from . import VISAInstrumentDriver
from lightlab.laboratory.instruments import OpticalSpectrumAnalyzer

import numpy as np
from lightlab.util.data import Spectrum
import pyvisa
import time
from lightlab import visalogger as logger
import socket
from contextlib import closing
WIDEST_WLRANGE = [1505.765, 1572.418]


def check_socket(host, port):
    # learned from https://stackoverflow.com/questions/19196105/python-how-to-check-if-a-network-port-is-open-on-linux
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        if sock.connect_ex((host, port)) == 0:  # pylint: disable=no-member
            logger.debug("%s:%s socket is open", host, port)
            port_open = True  # Port is open
        else:
            port_open = False  # Port is closed
    return port_open


class Apex_AP2440A_OSA(VISAInstrumentDriver):
    """Class for the OSA

        Basic functionality includes setting/getting wavelength range and sweeping
        Other functionality is for controlling TLS: on/off, wavelength (not implemented)

        The primary function is spectrum, which returns a Spectrum object

        Usage: :ref:`/ipynbs/Hardware/OpticalSpectrumAnalyzer.ipynb`

    """
    instrument_category = OpticalSpectrumAnalyzer
    __wlRange = None

    def __init__(self, name='The OSA', address=None, **kwargs):
        # def __init__(self, host='128.112.48.148', port=6500):
        """The TCPIP address can change if it renews the lease with DNS
        This has only happened once in the past. To initialize the optical spectrum analyzer,
        we need to set the host address, and the port.
        """
        kwargs['tempSess'] = kwargs.pop('tempSess', True)
        super().__init__(name=name, address=address, **kwargs)

    def startup(self):
        ''' Checks if it is alive, sets up standard OSA parameters
        '''
        self.instrID()
        self.write('SPTRACESWP0')
        # x-axis mode to wavelength
        # resolution to 0.80
        # others?

    def open(self):
        if self.address is None:
            raise RuntimeError("Attempting to open connection to unknown address.")
        # Check if ip port is open
        address_array = self.address.split("::")  # should be something like ['TCPIP0', 'xxx.xxx.xxx.xxx', '6501', 'SOCKET']
        if address_array[0] == 'TCPIP0':
            port_open = check_socket(address_array[1], int(address_array[2]))
        if not port_open:
            raise RuntimeError('The VISA port is not reachable. Instrument offline.')
        super().open()
        # special features for communicating with the OSA
        self.mbSession.set_visa_attribute(
            pyvisa.constants.VI_ATTR_TERMCHAR_EN, pyvisa.constants.VI_TRUE)
        self.mbSession.set_visa_attribute(
            pyvisa.constants.VI_ATTR_IO_PROT, pyvisa.constants.VI_PROT_4882_STRS)
        self.mbSession.write_termination = '\n'
        self.timeout = 25000
        self.mbSession.clear()

    def write(self, writeStr):
        ''' The APEX does not deal with write; you have to query to clear the buffer '''
        self.query(writeStr)
        time.sleep(0.2)

    def instrID(self):
        """Overloads the super function because the OSA does not respond to *IDN?
        Instead sends a simple command and waits for a confirmed return
        """
        try:
            self.write('SPSWPMSK?')
        except pyvisa.VisaIOError as err:
            print('OSA communication test failed. Sent: \'SPSWPMSK?\'')
            raise err
        return 'Apex AP2440A'

    def getWLrangeFromHardware(self):
        theRange = [0] * 2
        retStr = self.query('SPSTOPWL?')
        parsed = retStr.split('_')[-1]  # this removes the 'STRT_WL_'
        parsed = parsed[:-2]  # this removes the 'nm'
        theRange[0] = float(parsed)
        retStr = self.query('SPSTRTWL?')
        parsed = retStr.split('_')[-1]  # this removes the 'STRT_WL_'
        parsed = parsed[:-2]  # this removes the 'nm'
        theRange[1] = float(parsed)
        return theRange

    @property
    def wlRange(self):
        if self.__wlRange is None:
            self.__wlRange = self.getWLrangeFromHardware()
        return self.__wlRange

    @wlRange.setter
    def wlRange(self, newRange):
        """Assigns a new range to the wlRange property AND tells the OSA to update its range
        :param wlRange: a 2-element array of the form [start WL, end WL]
        :type wlRange: array of double

        This can be assigned using the typical notation, such as
        >>> osaInst.wlRange = [1550, 1551.3]

        It can also be accessed as normal, such as
        >>> x = osaInst.wlRange
        """
        newRangeClipped = np.clip(newRange, a_min=1505.765, a_max=1572.418)
        if np.any(newRange != newRangeClipped):
            print('Warning: Requested OSA wlRange out of range. Got', newRange)
        self.write('SPSTRTWL' + str(np.max(newRangeClipped)))
        self.write('SPSTOPWL' + str(np.min(newRangeClipped)))
        self.__wlRange = newRangeClipped

    def triggerAcquire(self):
        """Performs a sweep and reads the data
        Returns an array of dBm values as doubles
        :rtype: array
        """
        logger.debug('The OSA is sweeping')
        self.write('SPTRACESWP0')  # activate trace 0
        self.write('SPSWP1')  # Initiates a sweep
        # self.write('*WAI') # Bus and entire program stall until sweep completes.
        logger.debug('Done')

    def transferData(self):
        """ Performs a sweep and reads the data

            Gets the data of the sweep from the spectrum analyzer

            Returns:
                (ndarray, ndarray): wavelength in nm, power in dBm
        """
        self.open()
        self.mbSession.clear()
        try:
            # retStr = self.query('SPDATAD0')
            powerData = self.mbSession.query_ascii_values('SPDATAD0', separator=' ')
            # powerData = self.mbSession.query('SPDATAD0')
        except pyvisa.VisaIOError as e:
            self.close()
            raise e
        self.close()

        dataLen = int(powerData[0])
        powerData = np.array(powerData[1:])
        wavelengthData = np.linspace(self.wlRange[1], self.wlRange[0], dataLen)

        return wavelengthData[::-1], powerData[::-1]

    def spectrum(self, avgCnt=1):
        """Take a new sweep and return the new data. This is the primary user function of this class
        """
        for i in range(avgCnt):
            self.triggerAcquire()
            nm, dbm = self.transferData()
            if self.mbSession is not None:
                self.mbSession.close()
                raise Exception('data transfer did not close OSA session. Very bad.')
            if i is 0:
                dbmAvg = dbm / avgCnt
            else:
                dbmAvg = dbmAvg + dbm / avgCnt
        return Spectrum(nm, dbmAvg, inDbm=True)

    # TLS access methods currently not implemented

    @property
    def tlsEnable(self):
        retStr = self.query('TLSON?')
        # do some parsing
        return int(retStr) == 1

    @tlsEnable.setter
    def tlsEnable(self, newState=None):
        """newState can be 0/1 or true/false
        if newState is -1 or None: do nothing
        Returns the current on/off state as boolean, read from the OSA
        """
        if newState and newState != -1:
            if isinstance(newState, bool):
                newState = (newState != 0)
            writeVal = '1' if newState else '0'
            self.write('TLSON ' + writeVal)

    @property
    def tlsWl(self):
        retStr = self.query('TLSwl?')
        # do some parsing
        return float(retStr)

    @tlsWl.setter
    def tlsWl(self, newState=None):
        """newState is a float in units of nm
        """
        if newState:
            self.write('TLSwl ' + str(newState))
