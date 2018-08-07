# prologix patch, to be inserted somewhere in visa_bases
import socket
from contextlib import contextmanager


class PrologixResourceManager(object):
    '''Controls a Prologix GPIB-ETHERNET Controller v1.2
    manual: http://prologix.biz/downloads/PrologixGpibEthernetManual.pdf'''

    port = 1234
    _socket = None

    def __init__(self, ip_address, timeout=5):
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
        if self._socket is None:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
            try:
                s.settimeout(self.timeout)
                s.connect((self.ip_address, self.port))
            except socket.error:
                s.close()
                del s
                raise
            else:
                self._socket = s
            return self._socket
        else:
            return self._socket

    def disconnect(self):
        if self._socket is not None:
            self._socket.close()
            self._socket = None

    @contextmanager
    def connected(self):
        previously_connected = (self._socket is not None)
        self.connect()
        try:
            yield self
        finally:
            if not previously_connected:
                self.disconnect()

    def startup(self):
        with self.connected():
            self.send('++auto 0')  # do not read-after-write
            self.send('++mode 1')  # controller mode
            self.send('++read_tmo_ms 2000')  # timeout in ms
            self.send('++eos 0')  # append CR+LF after every GPIB

    def send(self, value):
        if self._socket is not None:
            sent = self._send(self._socket, value)
        else:
            with self.connected():
                sent = self._send(self._socket, value)
        return sent

    def recv(self, msg_length=1024):
        if self._socket is not None:
            recv = self._recv(self._socket, msg_length)
        else:
            with self.connected():
                recv = self._recv(self._socket, msg_length)
        return recv

    def query(self, query_msg, msg_length=2048):
        if self._socket is not None:
            self._send(self._socket, query_msg)
            recv = self._recv(self._socket, msg_length)
        else:
            with self.connected():
                self._send(self._socket, query_msg)
                recv = self._recv(self._socket, msg_length)
        return recv


import re
import socket


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
    except socket.gaierror:
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
            raise RuntimeError('invalid ip address: {}'.format(ip_address))
        try:
            if ':' in gpib_address:
                gpib_pad, gpib_sad = gpib_address.split(':', maxsplit=1)
                gpib_pad, gpib_sad = int(gpib_pad), int(gpib_sad)
            else:
                gpib_pad, gpib_sad = int(gpib_address), None
        except ValueError:
            raise RuntimeError(
                'invalid gpib format {}, should be like 10[:0]'.format(gpib_address))
    else:
        raise RuntimeError('invalid address: {}'.format(address))
    return ip_address, gpib_pad, gpib_sad


class PrologixGPIBObject(object):

    def __init__(self, address=None, tempSess=False):
        '''
            Args:
                tempSess (bool): If True, the session is opened and closed every time there is a command
                address (str): The full visa address in the form:
                    prologix://prologix_ip_address/gpib_primary_address:gpib_secondary_address
        '''

        self.tempSess = tempSess
        self.address = address
        self.ip_address, self.gpib_pad, self.gpib_sad = _sanitize_address(address)
        self._prologix_rm = PrologixResourceManager(self.ip_address)
        self._open_retries = 0
        self.__timeout = None

    def _prologix_gpib_addr_formatted(self):
        if self.gpib_sad is None:
            return f'{self.gpib_pad:d}'
        else:
            return f'{self.gpib_pad:d} {self.gpib_sad:d}'

    def _prologix_escape_characters(self, string):
        # TODO: escape characters according to prologix manual. + ESC etc.
        return string

    def open(self):
        '''Open connection with instrument.'''
        # we need to connect to the prologix_rm
        if not self.tempSess:
            self._prologix_rm.connect()
        else:
            with self._prologix_rm.connected() as pconn:
                pconn.startup()

    def close(self):
        self._prologix_rm.disconnect()
        return

    def write(self, writeStr):
        with self._prologix_rm.connected() as pconn:
            pconn.send('++addr {}'.format(self._prologix_gpib_addr_formatted()))
            pconn.send(self._prologix_escape_characters(writeStr))

    def query(self, queryStr, withTimeout=None):
        # Todo: implement withTimeout
        with self._prologix_rm.connected() as pconn:
            pconn.send('++addr {}'.format(self._prologix_gpib_addr_formatted()))
            pconn.send(self._prologix_escape_characters(queryStr))
            retStr = pconn.query('++read eoi')
        return retStr.rstrip()

    def instrID(self):
        r"""Returns the \*IDN? string"""
        return self.query('*IDN?')
