# prologix patch, to be inserted somewhere in visa_bases
import socket
from contextlib import contextmanager
import time
import re
from .driver_base import InstrumentSessionBase


class PrologixResourceManager(object):
    '''Controls a Prologix GPIB-ETHERNET Controller v1.2
    manual: http://prologix.biz/downloads/PrologixGpibEthernetManual.pdf


    Basic usage:

    .. code-block:: python

        p = PrologixResourceManager('lightwave-lab-prologix1.princeton.edu')

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

        p = PrologixResourceManager('lightwave-lab-prologix1.princeton.edu')

        with p.connected():
            p.startup()
            p.send('++addr 23')  # talks to address 23
            p.send('command value')  # sends the command and does not expect to read anything
            p.query('command')  # sends a command but reads stuff back

    If we try to send a message without the decorator, then we should connect and disconnect right before.

    .. code-block:: python

        p = PrologixResourceManager('lightwave-lab-prologix1.princeton.edu')

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
            ip_address (str): hostname or ip address of the controller
            timeout (float): timeout in seconds for establishing socket
                connection to controller, default 2.
        """
        self.timeout = timeout
        self.ip_address = ip_address

    def _send(self, socket, value):
        encoded_value = ('%s\n' % value).encode('ascii')
        sent = socket.sendall(encoded_value)
        return sent

    def _recv(self, socket, msg_length=2048):
        received_value = socket.recv(msg_length)
        return received_value.decode('ascii')

    def connect(self):
        ''' Connects to the controller via socket and leaves the connection open.
        If already connected, does nothing.

        Returns:
            socket object.
        '''
        if self._socket is None:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
            try:
                s.settimeout(self.timeout)
                s.connect((self.ip_address, self.port))
            except socket.error:
                s.close()
                del s
                print('Cannot connect to Prologix GPIB Controller.')
                raise
            else:
                self._socket = s
            return self._socket
        else:
            return self._socket

    def disconnect(self):
        ''' If connected, disconnects and kills the socket.'''
        if self._socket is not None:
            self._socket.close()
            self._socket = None

    @contextmanager
    def connected(self):
        ''' Context manager for ensuring that the socket is connected while
        sending and receiving commands to controller.
        This is safe to use everywhere, even if the socket is previously connected.
        It can also be nested.
        This is useful to bundle multiple commands that you desired to be
        executed together in a single socket connection, for example:

        .. code-block:: python

            def query(self, query_msg, msg_length=2048):
                with self.connected():
                    self._send(self._socket, query_msg)
                    recv = self._recv(self._socket, msg_length)
                return recv

        '''
        previously_connected = (self._socket is not None)
        self.connect()
        try:
            yield self
        finally:
            if not previously_connected:
                self.disconnect()

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

    def send(self, value):
        ''' Sends an ASCII string to the controller via socket. Auto-connects if necessary.

        Args:
            value (str): value to be sent
        '''
        with self.connected():
            sent = self._send(self._socket, value)
        return sent

    def recv(self, msg_length=2048):
        ''' Receives an ASCII string from the controller via socket. Auto-connects if necessary.

        Args:
            msg_length (int): maximum message length.
        '''
        with self.connected():
            recv = self._recv(self._socket, msg_length)
        return recv

    def query(self, query_msg, msg_length=2048):
        ''' Sends a query and receives a string from the controller. Autoconnects if necessary.

        Args:
            query_msg (str): query message.
            msg_length (int): maximum message length.
        '''
        with self.connected():
            self._send(self._socket, query_msg)
            recv = self._recv(self._socket, msg_length)
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
            return f'{self.gpib_pad:d}'
        else:
            return f'{self.gpib_pad:d} {self.gpib_sad:d}'

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
        return

    def write(self, writeStr):
        with self._prologix_rm.connected() as pconn:
            pconn.send('++addr {}'.format(self._prologix_gpib_addr_formatted()))
            pconn.send(self._prologix_escape_characters(writeStr))

    def query(self, queryStr, withTimeout=None):
        '''Read the unmodified string sent from the instrument to the
           computer.
        '''
        retStr = self.query_raw_binary(queryStr, withTimeout)
        return retStr.rstrip()

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

        if withTimeout is None:
            withTimeout = self.timeout

        # checking if message is available in small increments
        currenttime = time.time()
        expirationtime = currenttime + withTimeout
        while time.time() < expirationtime:
            # self.timeout = newTimeout
            status_byte = self.spoll()
            # MAV indicates that the message is available
            MAV = (status_byte >> 4) & 1
            if MAV:
                retStr = self._prologix_rm.query('++read eoi')
                return retStr.rstrip()
            # ask for the message in small increments
            time.sleep(0.1)

        raise RuntimeError('Query timed out')

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
