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


def check_socket(host, port):
    # learned from https://stackoverflow.com/questions/19196105/python-how-to-check-if-a-network-port-is-open-on-linux
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        if sock.connect_ex((host, port)) == 0:  # pylint: disable=no-member
            logger.debug("%s:%s socket is open", host, port)
            port_open = True  # Port is open
        else:
            port_open = False  # Port is closed
    return port_open


class Lakeshore_Model336(VISAInstrumentDriver):
    """Docs

    """
    _tcpsocket = None
    MAGIC_TIMEOUT = 30

    def __init__(self, name='Cryocontroller', address=None, **kwargs):
        """Initializes a fake VISA connection to the Lakeshore.
        """
        kwargs['tempSess'] = kwargs.pop('tempSess', True)
        super().__init__(name=name, address=address, **kwargs)
        self.reinstantiate_session(address, kwargs['tempSess'])

    def reinstantiate_session(self, address, tempSess):
        if address is not None:
            # should be something like ['TCPIP0', 'xxx.xxx.xxx.xxx', '6501', 'SOCKET']
            address_array = address #address.split("::")
            self._tcpsocket = TCPSocketConnection(ip_address=address_array[1],
                                                  port=int(address_array[2]),
                                                  timeout=self.MAGIC_TIMEOUT)

    def startup(self):
        ''' Checks if it is alive
        '''
        with self._tcpsocket.connected():
            self.instrID()

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
        try:
            print(self.query('*IDN?'))
        except socket.error:
            logger.error('Lakeshore communication test failed. Sent: \'*IDN?\'')
            raise

    def reset(self):
        self.write('*RST')

#     def setHeaterRange(self, output, range_val):
#         outputs = [1,2,3,4]
#         range_vals_12 = [0,1,2,3]
#         range_vals_34 = [0,1]
#         if output not in outputs:
#             raise ValueError('output is {}, but must be integer 1, 2, 3, or 4'.format(output))
#         elif (output == 1 or output == 2) and (range_val not in range_vals_12):
#             raise ValueError('range_val is {}, but for outputs 1 and 2, it must be integer 0 (off), 1, (low) 2 (medium), or 3 (high)'.format(range_val))
#         elif (output == 3 or output == 4) and (range_val not in range_vals_34):
#             raise ValueError('range_val is {}, but for outputs 3 and 4, it must be integer 0 (off), or 1, (on)'.format(range_val))
#         else:
#             print('RANGE {},{}\r\n'.format(output, range_val))
#             return self.write('RANGE {},{}\r\n'.format(output, range_val))

    def getHeaterRange(self, output):
        outputs = [1,2,3,4]
        if output not in outputs:
            raise ValueError('output is {} but must be integer 1, 2, 3, or 4'.format(output))
        else:
            return self.query('RANGE? {0}'.format(output))

    def analogOutParamQuery(self, output):
        outputs = [3,4]
        if output not in outputs:
            raise ValueError('output is {} but must be integer 3, or 4'.format(output))
        else:
            return self.query('ANALOG? {0}'.format(output))

    def getHeaterOutputQuery(self, output):
        outputs = [1,2]
        if output not in outputs:
            raise ValueError('output is {} but must be integer 1, or 2'.format(output))
        else:
            return self.query('HTR? {}'.format(output))

    def heaterSetup(self, output):
        outputs = [1,2]
        if output not in outputs:
            raise ValueError('output is {} but must be integer 1, or 2'.format(output))
        else:
            return self.query('HTRSET? {}'.format(output))

    def heaterSet(self, output, resistance, maxcurrent, maxcurrentuser, currentPower):
        outputs = [1,2]
        resistance = [1,2]
        maxcurrent = [0,1,2,3,4]
        currentPower = [1,2]


        if output not in outputs:
             raise ValueError('output is {} but must be integer 1, or 2'.format(output))
        elif resistance not in resistance:
            raise ValueError('resistance is {} but must be integer 1, or 2'.format(output))
        elif resistance not in resistance:
            raise ValueError('resistance is {} but must be integer 0, 1, 2, 3, or 4'.format(output))
        elif currentPower not in currentPower:
            raise ValueError('resistance is {} but must be integer 1, or 2'.format(output))
        elif (maxcurrent != 0):
            maxcurrentuser = 0
        elif (maxcurrent == 0):
            maxcurrentuser = maxcurrentuser
        else:
             return self.query('HTRSET {} {} {} {} {}'.format(output, resistance, maxcurrent, maxcurrentuser, currentPower))

    def heaterStatus(self, output):
        outputs = [1,2]
        if output not in outputs:
            raise ValueError('output is {} but must be integer 1, or 2'.format(output))
        else:
            return self.query('HTRST? {}'.format(output))

    def getOutputMode(self, output):
        outputs = [1,2,3,4]
        if output not in outputs:
            raise ValueError('output is {} but must be integer 1, 2, 3, or 4'.format(output))
        else:
            return self.query('OUTMODE? {}'.format(output))

    def getAnalogOutData(self, output):
        outputs = [3,4]
        if output not in outputs:
            raise ValueError('output is {} but must be integer 3, or 4'.format(output))
        else:
            return self.query('AOUT? {}'.format(output))

    def getCelciusReading(self, output):
        outputs = ["A","B","C","D"]
        if output not in outputs:
            raise ValueError('output is {} but must be A, B, C, D'.format(output))
        else:
            return self.query('CRDG? {}'.format(output))

    def tempLimitQuery(self, output):
        outputs = ["A","B","C","D"]
        if output not in outputs:
            raise ValueError('output is {} but must be A, B, C, D'.format(output))
        else:
            return self.query('TLIMIT? {}'.format(output))

        #page 130,,  data points curve?



    def warmupSupply(self, output):
        outputs = [3,4]
        if output not in outputs:
            raise ValueError('output is {} but must be integer 3, or 4'.format(output))
        else:
            return self.query('WARMUP? {}'.format(output))

    def junctionTempQuery(self):
        self.query('TEMP?')