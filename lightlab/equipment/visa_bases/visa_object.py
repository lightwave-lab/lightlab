import visa as pyvisa
import time
from lightlab import visalogger as logger

OPEN_RETRIES = 5


class VISAObject(object):
    '''
        Abstract class for something that communicates via messages
        (GPIB/USB/Serial/TCPIP/etc.). It handles message-based sessions
        in a way that provides a notion of object permanence to the
        connection with a particular address.

        It acts like a ``pyvisa`` message-based session, but it is
        not a subclass; it is a wrapper. It only contains one (at at time).
        That means VISAObject can offer extra opening, closing,
        session management, and error reporting features.
    '''
    def __init__(self, address=None, tempSess=False):
        '''
            Args:
                tempSess (bool): If True, the session is opened and closed every time there is a command
                address (str): The full visa address
        '''
        self.tempSess = tempSess
        self.resMan = None
        self.address = address
        self.mbSession = None
        self._open_retries = 0
        self.__timeout = None

    def open(self):
        '''
            Open connection with 5 retries.
        '''
        if self.mbSession is not None:
            return
        if self.address is None:
            raise RuntimeError("Attempting to open connection to unknown address.")
        if self.resMan is None:
            self.resMan = pyvisa.ResourceManager()
        try:
            self.mbSession = self.resMan.open_resource(self.address)
            if not self.tempSess:
                logger.debug('Opened %s', self.address)
        except pyvisa.VisaIOError as err:
            logger.warning('There was a problem opening the VISA %s... Error code: %s',
                           self.address, err.error_code)
            if self._open_retries < OPEN_RETRIES:
                self._open_retries += 1
                time.sleep(0.5 * self._open_retries)
                logger.warning('Trying again... (try = %s/%s)', self._open_retries, OPEN_RETRIES)
                self.open()
            else:
                logger.error(err)
                raise err
        else:
            if self._open_retries != 0:
                logger.warning('Found it!')
            self._open_retries = 0

    def close(self):
        if self.mbSession is None:
            return
        try:
            self.mbSession.close()
        except pyvisa.VisaIOError as err:
            logger.error('There was a problem closing the VISA %s', self.address)
            raise err
        self.mbSession = None
        if not self.tempSess:
            logger.debug('Closed %s', self.address)

    def write(self, writeStr):
        try:
            self.open()
            try:
                self.mbSession.write(writeStr)
            except Exception as err:
                logger.error('Problem writing to %s', self.address)
                raise err
            logger.debug('%s - W - %s', self.address, writeStr)
        finally:
            if self.tempSess:
                self.close()

    def query(self, queryStr, withTimeout=None):
        retStr = None
        try:
            self.open()
            logger.debug('%s - Q - %s', self.address, queryStr)
            toutOrig = self.timeout
            try:
                if withTimeout is not None:
                    self.timeout = withTimeout
                retStr = self.mbSession.query(queryStr)
                if withTimeout is not None:
                    self.timeout = toutOrig
            except Exception as err:
                logger.error('Problem querying to %s', self.address)
                # self.close()
                raise err
            retStr = retStr.rstrip()
            logger.debug('Query Read - %s', retStr)
        finally:
            if self.tempSess:
                self.close()
        return retStr

    def instrID(self):
        r"""Returns the \*IDN? string"""
        return self.query('*IDN?')

    @property
    def timeout(self):
        if self.__timeout is None:
            if self.mbSession is None:
                try:
                    self.open()
                    self.__timeout = self.mbSession.get_visa_attribute(
                        pyvisa.constants.VI_ATTR_TMO_VALUE)  # None means default
                finally:
                    if self.tempSess:
                        self.close()
            else:
                self.__timeout = self.mbSession.get_visa_attribute(
                    pyvisa.constants.VI_ATTR_TMO_VALUE)  # None means default
        return self.__timeout

    @timeout.setter
    def timeout(self, newTimeout):
        if self.mbSession is None:
            raise Exception(
                'This mbSession is None. Perhaps you are setting timeout when the session is closed temporarily')
        self.mbSession.set_visa_attribute(
            pyvisa.constants.VI_ATTR_TMO_VALUE, newTimeout)
        self.__timeout = newTimeout

    def reset(self):
        r"""Writes \*RST"""
        self.write('*RST')

    def wait(self, bigMsTimeout=10000):
        self.query('*OPC?', withTimeout=bigMsTimeout)
