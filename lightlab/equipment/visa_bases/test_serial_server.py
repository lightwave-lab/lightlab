# zmq
import time
import zmq

import numpy as np
from IPython.display import clear_output
import serial

import sys
import os


import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('J312pi',
                    username='pi',
                    password='lightwavelab')
# Setup sftp connection and transmit this script
sftp = client.open_sftp()
sftp.put(__file__, '/tmp/serial_server.py')
sftp.close()
# Run the transmitted script remotely without args and show its output.
# SSHClient.exec_command() returns the tuple (stdin,stdout,stderr)
stdout = client.exec_command('python /tmp/serial_server.py')[1]
for line in stdout:
    # Process each line in the remote output
    print line
client.close()
sys.exit(0)
