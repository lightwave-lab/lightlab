# prologix patch, to be inserted somewhere in visa_bases
import socket
import time
import re
from lightlab import visalogger as logger
from .driver_base import InstrumentSessionBase, TCPSocketConnection


class PrologixResourceManager(TCPSocketConnection):
    '''Controls a Prologix GPIB-ETHERNET Controller v1.2
    manual: http://prologix.biz/downloads/PrologixGpibEthernetManual.pdf


    Basic usage:

    .. code-block:: python

        p = PrologixResourceManager('prologix.school.edu')

        p.connect()  # connects to socket and leaves it open
        p.startup()  # configures prologix to communicate via gpib
        p.send('++addr 23')  # talks to address 23
        p.send('command value')  # sends the command and does not expect to read anything
        p.query('command')  # sends a command but reads stuff back, this might hang if buffer is empty
        p.disconnect()

    The problem with the above is that if there is any error with startup, send or
    query, the disconnect method will not be called. So we coded a decorator called ``connected``,
    to be used as such:

    .. code-block:: python

        p = PrologixResourceManager('prologix.school.edu')

        with p.connected():
            p.startup()
            p.send('++addr 23')  # talks to address 23
            p.send('command value')  # sends the command and does not expect to read anything
            p.query('command')  # sends a command but reads stuff back

    If we try to send a message without the decorator, then we should connect and disconnect right before.

    .. code-block:: python

        p = PrologixResourceManager('prologix.school.edu')

        p.send('++addr 23')  # opens and close socket automatically

    .. warning::

        If a second socket is opened from the same computer while the first was online,
        the first socket will stop responding and Prologix will send data to the just-opened socket.

    .. todo:: Make this class a singleton to mitigate the issue above.

    '''

    # TODO: make this class a singleton:
    # https://howto.lintel.in/python-__new__-magic-method-explained/

    port = 1234  #: port that the Prologix GPIB-Ethernet controller listens to.
    _socket = None

    def __init__(self, ip_address, timeout=2):
        """
        Args:
            ip_address (str): hostname or ip address of the Prologix controller
            timeout (float): timeout in seconds for establishing socket
                connection to socket server, default 2.
        """
        self.timeout = timeout
        self.ip_address = ip_address
        super().__init__(ip_address, self.port, timeout=timeout, termination='\n')

    def startup(self):
        ''' Sends the startup configuration to the controller.
            Just in case it was misconfigured.
        '''
        with self.connected():
            self.send('++auto 0')  # do not read-after-write
            self.send('++mode 1')  # controller mode
            self.send('++read_tmo_ms 2000')  # timeout in ms
            self.send('++eos 0')  # append CR+LF after every GPIB
            self.send('++savecfg 0')  # Disable saving of configuration parameters in EPROM

    def query(self, query_msg, msg_length=2048):
        ''' Sends a query and receives a string from the controller. Auto-connects if necessary.

        Args:
            query_msg (str): query message.
            msg_length (int): maximum message length. If the received
                message does not contain a '\n', it triggers another
                socket recv command with the same message length.
        '''
        with self.connected():
            recv = ""
            try:
                n_read = 0
                self._send(self._socket, query_msg)
                recv = self._recv(self._socket, msg_length)
                n_read += 1
#                 print(n_read, end=' ')
                while not recv.endswith('\n'):
                    recv += self._recv(self._socket, msg_length)
                    n_read += 1
#                     print(n_read, end=' ')
            except:
#                 print(recv)
                print(n_read)
        return recv


def _is_valid_hostname(hostname):
    '''Validates whether a hostname is valis. abc.example.com'''
    # from https://stackoverflow.com/questions/2532053/validate-a-hostname-string
    if hostname[-1] == ".":
        # strip exactly one dot from the right, if present
        hostname = hostname[:-1]
    if len(hostname) > 253:
        return False

    labels = hostname.split(".")

    # the TLD must be not all-numeric
    if re.match(r"[0-9]+$", labels[-1]):
        return False

    allowed = re.compile(r"(?!-)[a-z0-9-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(label) for label in labels)


def _is_valid_ip_address(ip_address):
    '''Validates whether it is a true ip address, like 10.34.134.13'''
    try:
        return socket.gethostbyname(ip_address) == ip_address
    except (socket.gaierror, UnicodeError):
        return False
    return False


def _validate_hostname(hostname):
    if _is_valid_hostname(hostname) or _is_valid_ip_address(hostname):
        return True
    else:
        return False


def _sanitize_address(address):
    '''Takes in an address of the form 'prologix://prologix_ip_address/gpib_primary_address[:gpib_secondary_address]'
    and returns prologix_ip_address, gpib_primary_address, gpib_secondary_address.
    If secondary address is not given, gpib_secondary_address = None'''
    if address.startswith('prologix://'):
        _, address = address.split('prologix://', maxsplit=1)
        ip_address, gpib_address = address.split('/', maxsplit=1)
        if not _validate_hostname(ip_address):
            raise RuntimeError("invalid ip address: '{}'".format(ip_address))
        try:
            if ':' in gpib_address:
                gpib_pad, gpib_sad = gpib_address.split(':', maxsplit=1)
                gpib_pad, gpib_sad = int(gpib_pad), int(gpib_sad)
            else:
                gpib_pad, gpib_sad = int(gpib_address), None
        except ValueError:
            raise RuntimeError(
                "invalid gpib format '{}', should be like '10[:0]'".format(gpib_address))
    else:
        raise RuntimeError('invalid address: {}'.format(address))
    return ip_address, gpib_pad, gpib_sad


class PrologixGPIBObject(InstrumentSessionBase):

    def __init__(self, address=None, tempSess=False):
        '''
            Args:
                tempSess (bool): If True, the session is opened and closed every time there is a command
                address (str): The full visa address in the form:
                    prologix://prologix_ip_address/gpib_primary_address:gpib_secondary_address
        '''

        if type(address) != str:
            raise RuntimeError("Invalid address: {}".format(address))

        self.tempSess = tempSess
        self.address = address
        self.ip_address, self.gpib_pad, self.gpib_sad = _sanitize_address(address)
        self._prologix_rm = PrologixResourceManager(self.ip_address)
        self._open_retries = 0
        self.__timeout = 2  # 2 seconds is the default

    def _prologix_gpib_addr_formatted(self):
        if self.gpib_sad is None:
            return '{:d}'.format(self.gpib_pad)
        else:
            return '{:d} {:d}'.format(self.gpib_pad, self.gpib_sad)

    def _prologix_escape_characters(self, string):
        '''Escapes ESC, +, \n, \r characters with ESC. Refer to Prologix Manual.'''
        def escape(string, char):
            return string.replace(char, chr(17) + char)

        string = escape(string, chr(17))  # this must come first
        string = escape(string, '+')
        string = escape(string, '\n')
        string = escape(string, '\r')
        return string

    def spoll(self):
        '''Return status byte of the instrument.'''

        gpib_addr = self._prologix_gpib_addr_formatted()
        spoll = self._prologix_rm.query('++spoll {}'.format(gpib_addr))
        status_byte = int(spoll.rstrip())
        return status_byte

    def LLO(self):
        '''This command disables front panel operation of the currently addressed instrument.'''
        self._prologix_rm.send('++llo')

    def LOC(self):
        '''This command enables front panel operation of the currently addressed instrument.'''
        self._prologix_rm.send('++loc')

    @property
    def termination(self):
        r'''Termination GPIB character. Valid options: '\\r\\n', '\\r', '\\n', ''. '''
        eos = int(self._prologix_rm.query('++eos').rstrip())
        if eos == 0:
            return '\r\n'
        elif eos == 1:
            return '\r'
        elif eos == 2:
            return '\n'
        elif eos == 3:
            return ''
        else:
            raise RuntimeError('unknown termination.')

    @termination.setter
    def termination(self, value):
        eos = None
        if value == '\r\n':
            eos = 0
        elif value == '\r':
            eos = 1
        elif value == '\n':
            eos = 2
        elif value == '':
            eos = 3
        else:
            print("Invalid termination: {}".format(repr(value)))
        if eos is not None:
            self._prologix_rm.send('++eos {}'.format(eos))

    def open(self):
        ''' Open connection with instrument.
        If ``tempSess`` is set to False, please remember to close after use.
        '''
        if not self.tempSess:
            self._prologix_rm.connect()
        with self._prologix_rm.connected() as pconn:
            pconn.startup()

    def close(self):
        ''' Closes the connection with the instrument.
        Side effect: disconnects prologix socket controller'''
        self._prologix_rm.disconnect()

    def write(self, writeStr):
        with self._prologix_rm.connected() as pconn:
            pconn.send('++addr {}'.format(self._prologix_gpib_addr_formatted()))
            pconn.send(self._prologix_escape_characters(writeStr))
    
#     def read(self, withTimeout=None):
#         logger.debug('%s - Q - %s', self.address, queryStr)
#         retStr = self.query_raw_binary(queryStr, withTimeout)
#         logger.debug('Query Read - %s', repr(retStr))
#         return retStr.rstrip()
        

    def query(self, queryStr, withTimeout=None):
        '''Read the unmodified string sent from the instrument to the
           computer.
        '''
        logger.debug('%s - Q - %s', self.address, queryStr)
        retStr = self.query_raw_binary(queryStr, withTimeout)
        logger.debug('Query Read - %s', repr(retStr))
        return retStr.rstrip()

    def wait(self, bigMsTimeout=10000):
        self.query('*OPC?', withTimeout=bigMsTimeout)

    def clear(self):
        '''This command sends the Selected Device Clear (SDC) message to the currently specified GPIB address.'''
        with self._prologix_rm.connected() as pconn:
            pconn.send('++addr {}'.format(self._prologix_gpib_addr_formatted()))
            pconn.send('++clr')
            
    def query_raw_binary(self, queryStr, withTimeout=None):
        '''Read the unmodified string sent from the instrument to the
           computer. In contrast to query(), no termination characters
           are stripped. Also no decoding.'''

        with self._prologix_rm.connected() as pconn:
            pconn.send('++addr {}'.format(self._prologix_gpib_addr_formatted()))
            pconn.send(self._prologix_escape_characters(queryStr))

        if withTimeout is not None:
            logger.warn("withTimeout option is deprecated: no effect")
        
        # TODO guard against socket error and throw nice error message
        retStr = self._prologix_rm.query('++read eoi')
        return retStr.rstrip()

        ## WARNING
        # The code below is for instruments that implement the message available
        # assert bit in the STATUS BYTE. Not all instruments implement it.
        # So it is best to deactivate it here for now.
        # That means that if you query something and the instrument doesn't send anything,
        # you will receive a cryptic socket timeout error.

        # if withTimeout is None:
        #     withTimeout = self.timeout

        # # checking if message is available in small increments
        # currenttime = time.time()
        # expirationtime = currenttime + withTimeout
        # while time.time() < expirationtime:
        #     # self.timeout = newTimeout
        #     status_byte = self.spoll()
        #     # MAV indicates that the message is available
        #     MAV = (status_byte >> 4) & 1
        #     if MAV == 1:
        #         retStr = self._prologix_rm.query('++read eoi')
        #         return retStr.rstrip()
        #     # ask for the message in small increments
        #     time.sleep(0.1)

        # raise RuntimeError('Query timed out')

    @property
    def timeout(self):
        ''' This timeout is between the user and the instrument.
            For example, if we did a sweep that should take ~10 seconds
            but ends up taking longer, you can set the timeout to 20 seconds.
        '''
        return self.__timeout

    @timeout.setter
    def timeout(self, newTimeout):
        if newTimeout < 0:
            raise ValueError("Timeouts cannot be negative")
        self.__timeout = newTimeout
