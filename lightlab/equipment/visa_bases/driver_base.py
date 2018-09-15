from abc import ABC, abstractmethod
from contextlib import contextmanager
import socket
import time
from lightlab import visalogger as logger


class InstrumentSessionBase(ABC):
    ''' Base class for Instrument sessions, to be inherited and specialized
    by VISAObject and PrologixGPIBObject'''

    @abstractmethod
    def spoll(self):
        pass

    @abstractmethod
    def LLO(self):
        pass

    @abstractmethod
    def LOC(self):
        pass

    @abstractmethod
    def open(self):
        pass

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def write(self):
        pass

    @abstractmethod
    def query(self):
        pass

    @abstractmethod
    def clear(self):
        pass

    @abstractmethod
    def query_raw_binary(self):
        pass

    def instrID(self):
        r"""Returns the \*IDN? string"""
        return self.query('*IDN?')

    @property
    @abstractmethod
    def timeout(self):
        pass

    @timeout.setter
    @abstractmethod
    def termination(self, newTimeout):
        pass


CR = '\r'
LF = '\n'


class TCPSocketConnection(object):
    ''' Opens a TCP socket connection, much like netcat.

    Usage:
        s = TCPSocketConnection('socket-server.school.edu', 1111)
        s.connect()  # connects to socket and leaves it open
        s.send('command')  # sends the command through the socket
        r = s.recv(1000)  # receives a message of up to 1000 bytes
        s.disconnect()  # shuts down connection
    '''

    port = None  #: socket server's port number
    _socket = None
    _termination = None

    def __init__(self, ip_address, port, timeout=2, termination=LF):
        """
        Args:
            ip_address (str): hostname or ip address of the socket server
            port (int): socket server's port number
            timeout (float): timeout in seconds for establishing socket
                connection to socket server, default 2.
        """
        self.timeout = timeout
        self.port = port
        self.ip_address = ip_address
        self._termination = termination

    def _send(self, socket, value):
        encoded_value = (('%s' % value) + self._termination).encode('ascii')
        sent = socket.sendall(encoded_value)
        return sent

    def _recv(self, socket, msg_length=2048):
        received_value = socket.recv(msg_length)
        return received_value.decode('ascii')

    def connect(self):
        ''' Connects to the socket and leaves the connection open.
        If already connected, does nothing.

        Returns:
            socket object.
        '''
        if self._socket is None:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
            try:
                logger.debug("Attempting new connection (timeout = %s)", str(self.timeout))
                init_time = time.time()
                s.settimeout(self.timeout)
                s.connect((self.ip_address, self.port))
            except socket.error:
                # avoiding shutdown to prevent sending any data to remote socket
                # https://stackoverflow.com/questions/13109899/does-socket-become-unusable-after-connect-fails
                # s.shutdown(socket.SHUT_WR)
                s.close()
                del s
                logger.error('Cannot connect to resource.')
                raise
            else:
                final_time = time.time()
                elapsed_time_ms = 1e3 * (final_time - init_time)
                logger.debug("Connected. Time elapsed: %s msec", '{:.2f}'.format(elapsed_time_ms))
                self._socket = s
            return self._socket
        else:
            return self._socket

    def disconnect(self):
        ''' If connected, disconnects and kills the socket.'''
        if self._socket is not None:
            self._socket.shutdown(socket.SHUT_WR)
            self._socket.close()
            self._socket = None

    @contextmanager
    def connected(self):
        ''' Context manager for ensuring that the socket is connected while
        sending and receiving commands to remote socket.
        This is safe to use everywhere, even if the socket is previously connected.
        It can also be nested.
        This is useful to bundle multiple commands that you desire to be
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
        raise NotImplementedError

    def send(self, value):
        ''' Sends an ASCII string to the socket server. Auto-connects if necessary.

        Args:
            value (str): value to be sent
        '''
        with self.connected():
            sent = self._send(self._socket, value)
        return sent

    def recv(self, msg_length=2048):
        ''' Receives an ASCII string from the socket server. Auto-connects if necessary.

        Args:
            msg_length (int): maximum message length.
        '''
        with self.connected():
            recv = self._recv(self._socket, msg_length)
        return recv

    def query(self, query_msg, msg_length=2048):
        raise NotImplementedError
