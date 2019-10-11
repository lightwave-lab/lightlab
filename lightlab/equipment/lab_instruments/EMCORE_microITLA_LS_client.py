#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 10 11:16:12 2019

@author: pi

Create a pseudo-driver that sends NEC commands to server for execution
"""

import zmq

class EMCORE_microITLA_LS():
    '''
        Single EMCORE microITLA laser source
        Provides array-based and dict-based setters/getters for
            * whether laser is on or off (``enableState``)
            * tunable wavelength output (``wls``)
            * output power in dBm (``powers``)s
            
        Args

        The client must be in the same local network as the server
        "Bank" behaviour is handled at the server level

        Usage: :ref: make ipybn example
    '''
    #instrument_category = LaserSource

    # Time it takes to equilibrate on different changes, in seconds
    #sleepOn = dict(OUT=3, WAVE=30, LEVEL=5)

    #powerRange = np.array([-20, 13])

    def __init__(self, serial_number=None, address='lightwave-lab-raspberry1.ee.princeton.edu', **kwargs):
            self.serial_number = serial_number
            self.address = address
            
    def request(self, command):
        ''' General-purpose Request-Reply with client
        
            Args:
                command (str): command to execute on server

            Returns:
                (str): output of the command on server side
        '''
        # Establish connection
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://{0}:5555".format(self.address))
        
        try:
            # Encrypt the serialnumber/command/arguments pair in a single string
            request_string = self.serial_number + str("___") + command
            # Send command, formatted as [SerialNumber, command]
            socket.send(str.encode(request_string))
            # Wait for and return response
            reply = socket.recv()
            reply_str = reply.decode()
        except: 
            reply_str = "Communication failed"
            pass
        
        # Clean communication exit
        socket.close()
        context.destroy()
        return reply_str
    
    def get_serial_number(self):
        return self.request("get_serial_number")
    
    def itla_on(self):
        return self.request("itla_on")
    
    def itla_off(self):
        return self.request("itla_off")
                        
    def ask_device_ready(self):
        return self.request("ask_device_ready")

    def set_output_power(self, pow_dbm):
        return self.request("set_output_power___{0}".format(pow_dbm))

    def set_first_channel_frequency(self, frequency_GHz):
        return self.request("set_first_channel_frequency___{0}".format(frequency_GHz))

    def set_ftf_frequency(self, frequency_MHz):
        return self.request("set_ftf_frequency___{0}".format(frequency_MHz))

    # UNTESTED
    #def set_channel(self, channel_num, ftf):
    #    return self.request("set_channel___{0}___{1}".format(channel_num, ftf))

    def get_output_power(self):
        return self.request("get_output_power")

    def get_first_channel_frequency(self):
        return self.request("get_first_channel_frequency")

    def get_channel_frequency(self):
        return self.request("get_channel_frequency")

    def get_ftf_frequency(self):
        return self.request("get_ftf_frequency")

    def get_device_type(self):
        return self.request("get_device_type")

    def get_manufacturer(self):
        return self.request("get_manufacturer")

    def get_manufactured_date(self):
        return self.request("get_manufactured_date")

    def get_io_capabilities(self):
        return self.request("get_io_capabilities")

    def get_device_errors(self):
        return self.request("get_device_errors")

    def get_module_monitors(self):
        return self.request("get_module_monitors")

    def get_power_capabilities(self):
        return self.request("get_power_capabilities")

    def get_grid_capabilities(self):
        return self.request("get_grid_capabilities")

    def get_ftf_capabilities(self):
        return self.request("get_ftf_capabilities")

    def get_frequency_capabilities(self):
        return self.request("get_frequency_capabilities")

    def port_close(self):
        return self.request("port_close")

   
if __name__ == '__main__':
    laser1 = EMCORE_microITLA_LS('CRTME2F008')
    laser2 = EMCORE_microITLA_LS('CRTMD5N01Q')
    laser3 = EMCORE_microITLA_LS('CRTMDCA01C')
    laser4 = EMCORE_microITLA_LS('CRTMD7B01H')
    laser5 = EMCORE_microITLA_LS('CRTME2F00D')
    laser6 = EMCORE_microITLA_LS('CRTME18008')
    laser7 = EMCORE_microITLA_LS('CRTME1H00D')
    laser8 = EMCORE_microITLA_LS('CRTME2A013')
    laser9 = EMCORE_microITLA_LS('CRTME2F008')
    laser10 = EMCORE_microITLA_LS('CRTME2600E')
    print(laser1.get_serial_number())
    print(laser2.get_serial_number())
    print(laser3.get_serial_number())
    print(laser4.get_serial_number())
    print(laser5.get_serial_number())
    print(laser6.get_serial_number())
    print(laser7.get_serial_number())
    print(laser8.get_serial_number())
    print(laser9.get_serial_number())
    print(laser10.get_serial_number())
    print(laser1.set_first_channel_frequency(193475))
    print(laser2.set_first_channel_frequency(193475))
    print(laser3.set_first_channel_frequency(193475))
    print(laser4.set_first_channel_frequency(193475))
    print(laser3.set_first_channel_frequency(193475))
    print(laser4.set_first_channel_frequency(193475))
    print(laser7.set_first_channel_frequency(193475))
    print(laser8.set_first_channel_frequency(193475))