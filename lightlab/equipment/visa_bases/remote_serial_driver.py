# zmq
import time
import zmq

import numpy as np
from IPython.display import clear_output
import serial

import sys
import os


class ZMQSerial_driver():
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
                server_OS_type='debian', # debian (Ubuntu, Raspbian, etc.), ...
                # ZMQ settings
                zmq_port=5556, # TCP socket that zmq will use to relay commands
                zmq_timeout=30, # timeout for server <--> client communication
                # Serial equipment settings
                serial_port="/dev/ttyACM0", # Serial port the instrument is connected to on the server (e.g. COM0, "/dev/ttyACM0", etc.)
                serial_baud=115200, # serial baud rate
                serial_timeout=5, # timeout for server <--> instrument communication
            ):

        # Server settings
        self.server_user = server_user
        self.server_address = server_address
        self.server_filename = server_filename      
        self.server_OS_type = server_OS_type  

        # zmq settings
        self.zmq_port = zmq_port
        self.zmq_timeout = zmq_timeout

        # Serial settings
        self.serial_port = serial_port
        self.serial_baud = serial_baud
        self.serial_timeout = serial_timeout

        # If the ZMQ server is not already up, start it
        if not self.ping_server():
            self.spawn_server(server_user, server_address, server_OS_type)

    def ping_server(self):
        '''
        Returns whether the ZMQ server is already running on the server
        '''
        return False # self.request(self, 'ping')

    def spawn_server(self, server_user, server_address, server_OS_type):
        '''
        Spawns the server process on the server machine
        '''
        # Upload the server code on the server
        # try:
        # From https://stackoverflow.com/questions/20499074/run-local-python-script-on-remote-server
        # Connect to remote host
        # import paramiko
        # client = paramiko.SSHClient()
        # client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        # TODO: figure out key situation. For now, just request password:
        # import getpass
        # server_password = getpass.getpass()
        # client.connect(hostname=server_address,
        #                     username=server_user,
        #                     password=server_password)
        # Setup sftp connection and transmit this script
        # sftp = client.open_sftp()
        # try:
        #     sftp.stat('./tmp')
        # except FileNotFoundError:
        #     sftp.mkdir('./tmp')
        # sftp.put(__file__, './tmp/serial_server.py', confirm=False)
        # sftp.close()
        # Run the transmitted script remotely without args and show its output.
        # SSHClient.exec_command() returns the tuple (stdin,stdout,stderr)
        # client.exec_command('tmux new-session -s zeromq',  get_pty=True)
        # stdout = client.exec_command(f'tmux new-session -s -d \"zeromq\" python ~/tmp/serial_server.py {self.zmq_port} {self.zmq_timeout} {self.serial_port} {self.serial_baud} {self.serial_timeout} > ~/tmp/serial_server.log')[1]
        # # client.exec_command('tmux detach')
        # client.close()
        # sys.exit(0)

        from fabric import Connection
        from patchwork.files import exists

        with Connection(f'{server_user}@{server_address}') as c:
            if not exists(c, "./tmp"):
               c.run("mkdir ./tmp")
            c.put(__file__, './tmp/serial_server.py')
            c.run("tmux new -d -s zeromq")
            c.run(f"tmux send-keys -t zeromq.0 \"python ~/tmp/serial_server.py {self.zmq_port} {self.zmq_timeout} {self.serial_port} {self.serial_baud} {self.serial_timeout} > ~/tmp/serial_server.log\" ENTER")

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


class ZMQserver():
    '''
        Actual class implementing the ZMQ server, to be executed on the remote machine
        Receives messages from the ZMQ client, and forwards them to the Serial instrument
    '''
    def __init__(self, 
                # ZMQ settings
                zmq_port=5556, # TCP socket that zmq will use to relay commands
                zmq_timeout=30, # timeout for server <--> client communication
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

        print("Creating zmq")
        context = zmq.Context()
        socket = context.socket(zmq.REP)
        socket.bind(f"tcp://*:{zmq_port}")
        # Run server
        self.run(socket)
        # Clean exit if "run" function is interrupted and returns
        socket.close()
        context.destroy()

    def command(self, cmd):
        cmd += "\n"
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

        print("Starting server")        
        try:    
            while True:
                print("In loop")
                cmd = self.zmq_port.recv()
                print("Received command: %s" % cmd)
                
                try:
                    # Execute command
                    cmd += "\n"
                    output = self.command(cmd)
                    #  Send reply back to client
                    socket.send(str.encode(output))
                # If manuel interruption, clean exit
                except KeyboardInterrupt:
                    print("Server manually stopped")
                    return
                # If communication error
                except Exception as e:
                    print("Communication error!")
                    os.system('tmux kill-session -t $(tmux display-message -p \'#S\')')
                    print(e)

        # If server fails for any other reason (including KeyboardInterrupt)
        except Exception as e:
            # Exit to clean exit command
            print(e)
            print("Server exiting; shutting down tmux session")
            os.system('tmux kill-session -t $(tmux display-message -p \'#S\')')
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

    server = ZMQserver(zmq_port=args.zmq_port,
                        zmq_timeout=args.zmq_timeout,
                        # Serial equipment settings
                        serial_port=args.serial_port,
                        serial_baud=args.serial_baud, 
                        serial_timeout=args.serial_timeout)