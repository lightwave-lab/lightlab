from lightlab.equipment.visa_bases import ZMQSerial_driver

import numpy as np
from IPython.display import clear_output
import serial

baud = 115200
port = "/dev/ttyACM0"
timeout = 2

x = "x"
y = "y"
z = "z"


class MDT693B_OLPC(ZMQSerial_driver):
    ''' A MDT693B - 3-Channel, Open-Loop Piezo Controller 

    Uses the remote serial interface

        `Manual: <https://www.thorlabs.com/thorproduct.cfm?partnumber=MDT693B>`__

        Usage: : TODO

    '''

    def __init__(self, name=None, server_user=None, server_address=None, **kwargs):
        '''
            Args:
                currStep (float): amount to step if ramping in current mode. Default (None) is no ramp
                voltStep (float): amount to step if ramping in voltage mode. Default (None) is no ramp
                rampStepTime (float): time to wait on each ramp step point
        '''
        ZMQSerial_driver.__init__(self, name=name, server_user=server_user, server_address=server_address, **kwargs)


# # send command and return the controller's response
# def command(cmd):
#     cmd += "\n"
#     with serial.Serial(port, baud, timeout=timeout) as ser:
#         ser.write(cmd.encode())
#         recv = ser.readlines()
#         recv_list = []
#         for recvi in recv:
#             recv_list.append(recvi.decode())
#     return recv_list[1]

# def get_volt(axis):
#     cmd = "{}voltage?\n".format(axis)
#     with serial.Serial(port, baud, timeout=timeout) as ser:
#         ser.write(cmd.encode())
#         recv = ser.readlines()
#         recv_list = []
#         for recvi in recv:
#             recv_list.append(recvi.decode())
#     volt = float(recv_list[1].strip('[]\r> '))
#     return volt

# def set_volt(axis, volt):
#     cmd = "{}voltage={}\n".format(axis, volt)
#     with serial.Serial(port, baud, timeout=timeout) as ser:
#         ser.write(cmd.encode())
#     return

# def increase(axis, dv):
#     with serial.Serial(port, baud, timeout=timeout) as ser:
#         cmd = "{}voltage?\n".format(axis)
#         ser.write(cmd.encode())
#         recv = ser.readline().decode()
#         volt = float(recv.strip('[]\r> '))
#         cmd = "{}voltage={}\n".format(axis, volt+dv)
#         ser.write(cmd.encode())
#     return 


"""
Example use
"""
if __name__ == '__main__':
    stage = MDT693B_OLPC(name='stage', server_address='128.112.50.75', server_user='pi')