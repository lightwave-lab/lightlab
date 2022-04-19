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
            ):

        # Server settings
        self.server_user = server_user
        self.server_address = server_address
        self.server_filename = server_filename      
        self.tmux_session_name = tmux_session_name  

        # zmq settings
        self.zmq_port = zmq_port
        self.zmq_timeout = zmq_timeout

        # Serial settings
        self.serial_port = serial_port
        self.serial_baud = serial_baud
        self.serial_timeout = serial_timeout

        # If the ZMQ server is not already up, start it
        if not self.ping_server():
            # First destroy any identically-named tmux sessions
            print("Spawning server")
            self.spawn_server(server_user, server_address, tmux_session_name)


    def ping_server(self):
        '''
        Returns whether the requested ZMQ server is already running on the server
        '''
        return True # self.request(self, 'ping')

    def spawn_server(self, server_user, server_address, tmux_session_name):
        '''
        Spawns the server process on the server machine
        '''
        # Upload the server code on the server
        from fabric import Connection
        from patchwork.files import exists

        with Connection(f'{server_user}@{server_address}') as c:
            if not exists(c, "./tmp"):
               c.run("mkdir ./tmp")
            c.put(__file__, './tmp/serial_server.py')
            c.run("tmux new -d -s zeromq")
            c.run(f"tmux send-keys -t zeromq.0 \"python ~/tmp/serial_server.py {self.zmq_port} {self.zmq_timeout} {self.serial_port} {self.serial_baud} {self.serial_timeout}\" ENTER")
            # c.run(f"tmux send-keys -t zeromq.0 \"python ~/tmp/serial_server.py {self.zmq_port} {self.zmq_timeout} {self.serial_port} {self.serial_baud} {self.serial_timeout} > ./tmp/serial_server.log\" ENTER")

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
        socket.connect("tcp://{0}:{1}".format(self.server_address, self.zmq_port))

        try:
            # Send command
            socket.send(str.encode(command))
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
        The difference between request and write is implemented on the server
        
            Args:
                command (str): command to execute on the server
            Returns:
                (bool): True if the command successfully executed
        '''
        try:
            self.request(command)
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
                serial_timeout=5, # timeout for server <--> instrument communication
            ):

        self.zmq_port = zmq_port
        self.zmq_timeout = zmq_timeout
        self.serial_port = serial_port
        self.serial_baud = serial_baud
        self.serial_timeout = serial_timeout

        context = zmq.Context()
        socket = context.socket(zmq.REP)
        socket.setsockopt(zmq.LINGER, zmq_timeout)
        socket.bind(f"tcp://*:{zmq_port}")
        # Run server
        print("running server")
        self.run(socket)
        print("not running server anymore")
        # Clean exit if "run" function is interrupted and returns
        socket.close()
        context.destroy()
        # os.system('tmux kill-session -t $(tmux display-message -p \'#S\')')

    def serial_command(self, cmd):
        cmd += "\n"
        print(f"Serial command {cmd}")
        with serial.Serial(self.serial_port, self.serial_baud, timeout=self.serial_timeout) as ser:
            ser.write(cmd.encode())
            recv = ser.readlines()
            recv_list = []
            for recvi in recv:
                recv_list.append(recvi.decode())
        return recv_list[1]

    def run(self, socket):
        ''' 
        Start running the zeromq server on the host machine
        '''  

        print(f"Starting server with zmq socket {self.zmq_port}")        
        try:
            while True:
                cmd = socket.recv().decode()
                print("Received command: %s" % cmd)
                
                try:
                    # Execute command
                    output = self.serial_command(cmd)
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
            print(e)
            print("Server exiting")
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
    args = parser.parse_args()

    server = ZMQserver(zmq_port=int(args.zmq_port),
                        zmq_timeout=float(args.zmq_timeout),
                        # Serial equipment settings
                        serial_port=str(args.serial_port),
                        serial_baud=int(args.serial_baud), 
                        serial_timeout=float(args.serial_timeout))