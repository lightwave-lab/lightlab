#!/usr/bin/env python
# coding:utf-8

# Created on Fri Feb 24

__author__ = "Thomas Ferreira de Lima"
__copyright__ = "Copyright 2020, Lightwave Lab, Princeton University"
__credits__ = ""
__license__ = ""
__version__ = "0.0.1"
__maintainer__ = ""
__email__ = "tlima@princeton.edu"
__status__ = "developping"

import pyvisa
import numpy as np
import struct
from contextlib import contextmanager

def ieee488_2_conversion(dac_in, trigger_len):
    mk1 = b'\xc0' #struct.pack('<H',int('11000000', base = 2))[0]
    mk0 = b'\x00'

    byte_to_send = b''
    for ind, val in enumerate(dac_in):
        byte_val = struct.pack('<f', val)
        if ind < trigger_len:
            b = byte_val + mk1
        else:
            b = byte_val + mk0
        byte_to_send += b

    byte_len = len(byte_to_send)
    preamble_str = '#{0:d}{1:d}'.format(len(str(byte_len)),byte_len)
    return bytes(preamble_str, 'ascii')+byte_to_send

class AWG_7122:
    rm = None
    address = None

    def __init__(self, address):
        self.rm = pyvisa.ResourceManager()
        self.address = address

    @contextmanager
    def connected(self):
        resource = self.rm.open_resource(self.address)
        try:
            yield resource
        finally:
            resource.close()

    def print_idn(self):
        with self.connected() as tek_awg:
            return tek_awg.query('*IDN?')

    def upload_waveform(self, wfm_name, np_array):
        dac_in = np_array
        ieee488_2_in = ieee488_2_conversion(dac_in, 1)
        with self.connected() as tek_awg:
            tek_awg.write('WLIST:WAVEFORM:DELETE "{:s}"'.format(wfm_name))
            tek_awg.write('WLIST:WAVEFORM:NEW "{1:s}",{0:d},REAL'.format(len(dac_in), wfm_name))
            tek_awg.write_raw('WLISt:WAVeform:DATA "{0:s}",'.format(wfm_name).encode('utf-8') + ieee488_2_in)

    def set_waveform(self, wfm_name, channel):
        with self.connected() as tek_awg:
            tek_awg.write('SOURCE{:d}:WAVeform "{:s}"'.format(channel, wfm_name))

    def set_sampling_rate(self, samp_rate_MHz):
        with self.connected() as tek_awg:
            tek_awg.write('SOURCE1:FREQUENCY {0:d}MHZ'.format(samp_rate_MHz))
            tek_awg.write('SOURCE2:FREQUENCY {0:d}MHZ'.format(samp_rate_MHz))


    def turn_on(self, channel):
        with self.connected() as tek_awg:
            tek_awg.write('OUTPUT{:d}:STATE 1'.format(channel))

    def turn_off(self, channel):
        with self.connected() as tek_awg:
            tek_awg.write('OUTPUT{:d}:STATE 0'.format(channel))

    def run(self):
        with self.connected() as tek_awg:
            tek_awg.write('AWGControl:RUN')

    def stop(self):
        with self.connected() as tek_awg:
            tek_awg.write('AWGControl:STOP')