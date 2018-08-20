from . import VISAInstrumentDriver
from lightlab.equipment.visa_bases.driver_base import TCPSocketConnection
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
    _tcpsocket = None
    __wlRange = None
    MAGIC_TIMEOUT = 30

    def __init__(self, name='The OSA', address=None, **kwargs):
        """Initializes a fake VISA connection to the OSA.
        """
        kwargs['tempSess'] = kwargs.pop('tempSess', True)
        super().__init__(name=name, address=address, **kwargs)
        self.reinstantiate_session(address, kwargs['tempSess'])

    def reinstantiate_session(self, address, tempSess):
        if address is not None:
            # should be something like ['TCPIP0', 'xxx.xxx.xxx.xxx', '6501', 'SOCKET']
            address_array = address.split("::")
            self._tcpsocket = TCPSocketConnection(ip_address=address_array[1],
                                                  port=int(address_array[2]),
                                                  timeout=self.MAGIC_TIMEOUT)

    def startup(self):
        ''' Checks if it is alive, sets up standard OSA parameters
        '''
        with self._tcpsocket.connected():
            self.instrID()
            self.write('SPTRACESWP0', 'SP_SWEEP_TRACE_0')  # select trace 0
            self.write('SPXUNT1', 'SP_WAVELENGTH')  # x-axis mode to wavelength
            self.write('SPLINSC1', 'SP_LOG')  # y-axis to log scale
            self.write('SPSWPRES0', 'SP_RESOLUTION_100MHz')  # resolution to 0.80 pm

        # others?

    def open(self):
        if self.address is None:
            raise RuntimeError("Attempting to open connection to unknown address.")
        try:
            self._tcpsocket.connect()
        except socket.error:
            self._tcpsocket.disconnect()
            raise

    def close(self):
        self._tcpsocket.disconnect()

    def _query(self, queryStr):
        with self._tcpsocket.connected() as s:
            s.send(queryStr)

            i = 0
            old_timeout = s.timeout
            s.timeout = self.MAGIC_TIMEOUT
            received_msg = ''
            while i < 1024:  # avoid infinite loop
                recv_str = s.recv(1024)
                received_msg += recv_str
                if recv_str.endswith('\n'):
                    break
                s.timeout = 1
                i += 1
            s.timeout = old_timeout
            return received_msg.rstrip()

    def query(self, queryStr, expected_talker=None):
        ret = self._query(queryStr)
        if expected_talker is not None:
            if ret != expected_talker:
                log_function = logger.warning
            else:
                log_function = logger.debug
            log_function("'%s' returned '%s', expected '%s'", queryStr, ret, str(expected_talker))
        else:
            logger.debug("'%s' returned '%s'", queryStr, ret)
        return ret

    def write(self, writeStr, expected_talker=None):
        ''' The APEX does not deal with write; you have to query to clear the buffer '''
        self.query(writeStr, expected_talker)
        time.sleep(0.2)

    def instrID(self):
        """Overloads the super function because the OSA does not respond to *IDN?
        Instead sends a simple command and waits for a confirmed return
        """
        try:
            self.write('SPSWPMSK?')
        except socket.error:
            logger.error('OSA communication test failed. Sent: \'SPSWPMSK?\'')
            raise
        else:
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

        retStr = self._query('SPDATAD0')
        powerData = pyvisa.util.from_ascii_block(retStr,
                                                 converter='f',
                                                 separator=' ',
                                                 container=list)

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
