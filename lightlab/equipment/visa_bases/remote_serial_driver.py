# zmq
import time
import zmq

import numpy as np
from IPython.display import clear_output
import serial

import sys
import os

from datetime import datetime


class ZMQclient():
    '''
        Generic class for a serial driver interfaced with a "server" machine (e.g.  RPi), while the user issues commands from a "client" machine (e.g. laboratory instrumentation server), using ZMQ for client-server communication

        User <--> [Client] <--ZMQ--> [Server] <--Serial--> Instrument

        - This class provides the utilities that will spawn a zmq process on the server and relay commands from the client
        - SSH password needs to be input during function call if passwordless connection is not setup
    '''

    def __init__(self, 
                name=None,
                # Server SSH settings
                server_user=None, # Username for login on the server
                server_address=None, # IP address of the server
                server_filename='~/tmp/server.py', # script name to save to remote
                # ZMQ settings
                zmq_port=5556, # TCP socket that zmq will use to relay commands
                zmq_timeout=30, # timeout for server <--> client communication
                # Serial equipment settings
                serial_port="/dev/ttyACM0", # Serial port the instrument is connected to on the server (e.g. COM0, "/dev/ttyACM0", etc.)
                serial_baud=115200, # serial baud rate
                serial_timeout=5, # timeout for server <--> instrument communication
                # Server session setting
                tmux_session_name='zmq', # by default will concatenate this with zmq_port #
                separator='___' # separator between command header and command
            ):

        # Server settings
        self.server_user = server_user
        self.server_address = server_address
        self.server_filename = server_filename      
        self.tmux_session_name = tmux_session_name 
        self.separator = separator 

        # zmq settings
        self.zmq_port = zmq_port
        self.zmq_timeout = zmq_timeout

        # Serial settings
        self.serial_port = serial_port
        self.serial_baud = serial_baud
        self.serial_timeout = serial_timeout

        # If the ZMQ server is not already up, start it
        # if not self.ping():
            # First destroy any identically-named tmux sessions
        print("Spawning server")
        self.create_server()

    def create_server(self):
        '''
        Spawns the server process on the server machine
        The process is composed of a tmux session + this python script
        '''
        # Upload the server code on the server
        from fabric import Connection
        from patchwork.files import exists

        with Connection(f'{self.server_user}@{self.server_address}') as c:
            if not exists(c, "./tmp"):
               c.run("mkdir ./tmp")
            c.put(__file__, './tmp/serial_server.py')
            c.run(f"tmux new -d -s {self.tmux_session_name}_{self.zmq_port}")
            c.run(f"tmux send-keys -t {self.tmux_session_name}_{self.zmq_port}.0 \"python ~/tmp/serial_server.py {self.zmq_port} {self.zmq_timeout} {self.serial_port} {self.serial_baud} {self.serial_timeout} {self.separator}\" ENTER")
            # c.run(f"tmux send-keys -t zeromq.0 \"python ~/tmp/serial_server.py {self.zmq_port} {self.zmq_timeout} {self.serial_port} {self.serial_baud} {self.serial_timeout} > ./tmp/serial_server.log\" ENTER")

    def request(self, command, header=2):
        ''' General-purpose Request-Reply with client
        
            Args:
                command (str): command to execute on server
            Returns:
                (str): output of the command on server side
        '''
        # Establish connection
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://{0}:{1}".format(self.server_address, self.zmq_port))

        try:
            # Send command
            socket.send(str.encode(f"{header}{self.separator}{command}"))
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

    def write(self, command):
        ''' Wrapper around request for commands that don't require a response from the equipment
        Request has a custom timeout, whereas write has short timeout (implemented on server)
        
            Args:
                command (str): command to execute on the server
            Returns:
                (bool): 1 if the command successfully executed
        '''
        try:
            reply_str = self.request(command, header=3)
            return 1
        except:
            return 0

    def ping(self):
        ''' True (1) if specified server is already active
        '''
        try:
            reply_str = self.request('', header=1)
            return 1
        except:
            return 0

    def terminate(self):
        ''' Shuts down the specified server (if any)
            True if successful
        '''
        try:
            reply_str = self.request('', header=0)
            return 1
        except:
            return 0


class ZMQserver():
    '''
        Actual class implementing the ZMQ server, to be executed on the remote machine
        Receives messages from the ZMQ client, and forwards them to the Serial instrument
    '''
    def __init__(self, 
                # ZMQ settings
                zmq_port=5556, # TCP socket that zmq will use to relay commands
                zmq_timeout=10, # timeout for server <--> client communication
                # Serial equipment settings
                serial_port="/dev/ttyACM0", # Serial port the instrument is connected to on the server (e.g. COM0, "/dev/ttyACM0", etc.)
                serial_baud=115200, # serial baud rate
                serial_timeout=2, # timeout for server <--> instrument communication
                separator='___',
            ):

        self.zmq_port = zmq_port
        self.zmq_timeout = zmq_timeout
        self.serial_port = serial_port
        self.serial_baud = serial_baud
        self.serial_timeout = serial_timeout
        self.separator = separator

        context = zmq.Context()
        socket = context.socket(zmq.REP)
        # socket.setsockopt(zmq.LINGER, zmq_timeout)
        socket.bind(f"tcp://*:{zmq_port}")
        # Run server
        self.run(socket)
        # Clean exit if "run" function is interrupted and returns
        socket.close()
        context.destroy()
        # os.system('tmux kill-session -t $(tmux display-message -p \'#S\')')

    def serial_request(self, cmd, timeout):
        cmd += "\n"
        print(f"Serial command {cmd}")
        with serial.Serial(self.serial_port, self.serial_baud, timeout=timeout) as ser:
            ser.write(cmd.encode())
            recv = ser.readlines()
            recv_list = []
            for recvi in recv:
                recv_list.append(recvi.decode())
        return recv_list[1]

    def run(self, socket):
        ''' 
        Run the zeromq server on the host machine

        Dedicated commands:
        0 - terminate
        1 - ping
        2 - "request" w/ self.serial_timeout
        3 - "write" w/ short (1ms) serial timeout
        '''  

        print(f"Starting server with zmq socket {self.zmq_port}")        
        try:
            while True:

                # Receive client request
                full_cmd = socket.recv().decode().split(self.separator)

                cmd_header = int(full_cmd[0])
                cmd = full_cmd[1]

                try:
                    # Parse command
                    # TERMINATE
                    if cmd_header == 0:
                        print("Server received termination command from client")
                        socket.send(str.encode('1'))
                        # Exit loop to trigger graceful exit
                        return
                    # PING
                    elif cmd_header == 1:
                        print("Server ping'ed by client")
                        output = '1'
                    # REQUEST
                    elif cmd_header == 2:
                        print("Received request (header 2) command: %s" % cmd)
                        output = self.serial_request(cmd, self.serial_timeout)
                    # WRITE
                    elif cmd_header == 3:
                        print("Received write (header 3) command: %s" % cmd)
                        self.serial_request(cmd, 1E-3)
                        output = '1'
                    else:
                        print(f"Received (non-implemented) command header {cmd_header} with command {cmd}. Server still running.")
                        output = '0'

                    #  Send reply back to client
                    socket.send(str.encode(output))

                # If manuel interruption, clean exit
                except KeyboardInterrupt:
                    print("Server manually stopped")
                    return
                # If communication error
                except Exception as e:
                    print("Communication error from zmq server to client")
                    print(e)
                    return

        # If server fails for any other reason (including KeyboardInterrupt)
        except Exception as e:
            # Exit to clean exit command
            return



"""
Code to be executed on the server
"""
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Process zmq server info')
    parser.add_argument('zmq_port', type=str, help='Port number for the zmq socket')
    parser.add_argument('zmq_timeout', type=str, help='Timeout for the zmq socket')
    parser.add_argument('serial_port', type=str, help='Port address for the serial connection')
    parser.add_argument('serial_baud', type=str, help='Baud rate for the serial connection')
    parser.add_argument('serial_timeout', type=str, help='Timeout for the serial connection')
    parser.add_argument('separator', type=str, help='Separation character between command header and command')
    args = parser.parse_args()

    server = ZMQserver(zmq_port=int(args.zmq_port),
                        zmq_timeout=float(args.zmq_timeout),
                        # Serial equipment settings
                        serial_port=str(args.serial_port),
                        serial_baud=int(args.serial_baud), 
                        serial_timeout=float(args.serial_timeout),
                        separator=str(args.separator)
                        )