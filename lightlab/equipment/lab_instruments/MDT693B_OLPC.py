from lightlab.equipment.visa_bases import ZMQclient

import numpy as np
from IPython.display import clear_output
import serial

baud = 115200
port = "/dev/ttyACM0"
timeout = 2

x = "x"
y = "y"
z = "z"


class MDT693B_OLPC(ZMQclient):
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
        ZMQclient.__init__(self, name=name, server_user=server_user, server_address=server_address, **kwargs)


    def get_volt(self, axis):
        cmd = "{}voltage?".format(axis)
        ans = self.request(cmd)
        return float(ans.strip('[]\r> '))

    def set_volt(self, axis, volt):
        cmd = "{}voltage={}\n".format(axis, volt)
        ans = self.write(cmd)
        return

    def increase(self, axis, dv):
        try:
            volt = self.get_volt(axis)
            self.set_volt(axis, volt+dv)
            return 1
        except:
            return 0


"""
Example use
"""
if __name__ == '__main__':
    import time
    stage = MDT693B_OLPC(name='stage', server_address='128.112.50.75', server_user='pi')
    print(stage.set_volt('x', 12))
    print(stage.get_volt('x'))